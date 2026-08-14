"""
下载队列管理器 — 纯业务逻辑，事件驱动，不依赖任何 UI 框架。

事件（通过 on() 注册回调）：
  - "task_update"   (task)        任务状态/进度/标题变更
  - "all_completed" (waiting, done, failed)  全部任务结束
  - "log"           (msg: str)    日志消息

所有回调在 worker 线程中调用，UI 层需自行 marshal 到主线程。
"""

import re
import threading
import time
from typing import Callable, List, Optional

import yt_dlp


# ---- 工具函数 ----

def format_bytes(b: int) -> str:
    """将字节数转为可读字符串。"""
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f}{unit}"
        b /= 1024
    return f"{b:.1f}TB"


# mode → 下载类型标签
FORMAT_LABELS = {
    "best": "视频(最佳)",
    "720": "视频(720P)",
    "480": "视频(480P)",
    "audio": "音频(MP3)",
}


# ---- 任务数据类 ----

class DownloadTask:
    STATUS_WAITING = "等待中"
    STATUS_DOWNLOADING = "下载中"
    STATUS_COMPLETED = "已完成"
    STATUS_FAILED = "失败"
    STATUS_CANCELLED = "已取消"

    def __init__(self, url: str, mode: str = "best"):
        self.url = url
        self.mode = mode
        self.status = self.STATUS_WAITING
        self.progress = 0
        self.title = ""
        self.error_msg = ""
        self.speed_str = ""      # "3.2MiB/s"
        self.size_str = ""       # "45.3MB"
        self.format_label = FORMAT_LABELS.get(mode, f"视频({mode})")


# ---- 管理器 ----

class DownloadManager:
    """下载队列管理器。通过事件回调与外部通信。"""

    def __init__(self, ydl_opts_builder: Callable[[DownloadTask], dict]):
        """
        ydl_opts_builder: 可调用对象，接收 DownloadTask，返回 yt-dlp opts 字典。
        """
        self._ydl_opts_builder = ydl_opts_builder
        self._listeners: dict[str, list] = {}
        self._lock = threading.Lock()

        # 状态
        self.tasks: List[DownloadTask] = []
        self.current_task: Optional[DownloadTask] = None
        self.is_running = False
        self._cancel_event = threading.Event()       # 中止当前下载
        self._cancel_skip = False                    # True=跳过, False=暂停型中止
        self._pause_event = threading.Event()        # 队列暂停

        # worker 线程
        self._worker_thread: Optional[threading.Thread] = None

    # ---- 事件系统 ----

    def on(self, event: str, callback: Callable) -> None:
        """注册事件监听器。"""
        self._listeners.setdefault(event, []).append(callback)

    def _emit(self, event: str, *args) -> None:
        """发射事件（线程安全）。"""
        for cb in self._listeners.get(event, []):
            try:
                cb(*args)
            except Exception:
                pass

    # ---- 队列操作（主线程调用） ----

    @staticmethod
    def _clean_url(url: str) -> str:
        """去掉时间戳参数 t=…，但保留分P参数 p=…"""
        url = re.sub(r'[?&]t=\d+\.?\d*', '', url)
        url = re.sub(r'\?&', '?', url)
        url = re.sub(r'\?$', '', url)
        return url

    def add_task(self, url: str, mode: str = "best") -> DownloadTask:
        url = self._clean_url(url)
        with self._lock:
            task = DownloadTask(url, mode)
            self.tasks.append(task)
            return task

    def add_tasks(self, urls: List[str], mode: str = "best") -> List[DownloadTask]:
        return [self.add_task(u, mode) for u in urls if u.strip().startswith(("http://", "https://"))]

    def remove_task(self, task: DownloadTask) -> bool:
        with self._lock:
            if task.status == DownloadTask.STATUS_DOWNLOADING:
                return False
            try:
                self.tasks.remove(task)
                return True
            except ValueError:
                return False

    def move_task(self, task: DownloadTask, new_index: int) -> None:
        """将任务移动到指定索引位置（数据驱动排序）。"""
        with self._lock:
            try:
                self.tasks.remove(task)
                self.tasks.insert(new_index, task)
            except ValueError:
                pass

    def clear_completed(self) -> None:
        with self._lock:
            self.tasks = [
                t for t in self.tasks
                if t.status not in (
                    DownloadTask.STATUS_COMPLETED,
                    DownloadTask.STATUS_FAILED,
                    DownloadTask.STATUS_CANCELLED,
                )
            ]

    def get_stats(self) -> tuple:
        """返回 (waiting, downloading, completed, failed)。"""
        with self._lock:
            w = sum(1 for t in self.tasks if t.status == DownloadTask.STATUS_WAITING)
            d = sum(1 for t in self.tasks if t.status == DownloadTask.STATUS_DOWNLOADING)
            c = sum(1 for t in self.tasks if t.status == DownloadTask.STATUS_COMPLETED)
            f = sum(1 for t in self.tasks if t.status in (
                DownloadTask.STATUS_FAILED, DownloadTask.STATUS_CANCELLED))
            return w, d, c, f

    # ---- 运行控制（主线程调用） ----

    @property
    def is_paused(self) -> bool:
        return self._pause_event.is_set()

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._pause_event.clear()
        self._cancel_event.clear()
        self._cancel_skip = False
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def pause(self) -> None:
        """暂停：阻止队列取下一个任务，同时中止当前正在下载的任务（保留 .part 供续传）。"""
        self._pause_event.set()
        if self.current_task:
            self._cancel_skip = False      # 暂停型中止 → 任务回退 WAITING
            self._cancel_event.set()

    def resume(self) -> None:
        self._pause_event.clear()
        self._cancel_event.clear()

    def cancel_current(self) -> None:
        """跳过：中止当前下载，任务标记为 CANCELLED。"""
        self._cancel_skip = True           # 跳过型中止 → 任务标记 CANCELLED
        self._cancel_event.set()

    def stop(self) -> None:
        """完全停止（程序退出时调用）。"""
        self.is_running = False
        self._pause_event.clear()
        self._cancel_skip = False
        self._cancel_event.set()           # 确保当前下载被中断

    # ---- Worker 线程 ----

    def _worker(self) -> None:
        while self.is_running:
            # 阻塞等待暂停解除
            if self._pause_event.is_set():
                self._pause_event.wait(0.5)
                continue

            # 取下一个等待中的任务
            task = self._next_waiting()
            if not task:
                time.sleep(0.5)
                if not self._has_waiting():
                    self.is_running = False
                    w, _, c, f = self.get_stats()
                    self._emit("all_completed", w, c, f)
                    break
                continue

            self.current_task = task
            self._download_one(task)
            self.current_task = None

    def _next_waiting(self) -> Optional[DownloadTask]:
        with self._lock:
            for t in self.tasks:
                if t.status == DownloadTask.STATUS_WAITING:
                    return t
        return None

    def _has_waiting(self) -> bool:
        with self._lock:
            return any(t.status == DownloadTask.STATUS_WAITING for t in self.tasks)

    # ---- 单任务下载 ----

    def _download_one(self, task: DownloadTask) -> None:
        self._cancel_event.clear()
        self._cancel_skip = False

        task.status = DownloadTask.STATUS_DOWNLOADING
        self._emit("task_update", task)

        try:
            opts = self._ydl_opts_builder(task)

            # 进度钩子 —— 用 yt-dlp 原生字段计算进度，捕获速度与大小
            progress = {"_last_emit": 0.0}

            def progress_hook(d: dict):
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    if total:
                        task.progress = int(d.get("downloaded_bytes", 0) * 100.0 / total)
                    # 捕获速度与大小
                    task.speed_str = d.get("_speed_str", "")
                    if not task.size_str and total:
                        task.size_str = format_bytes(total)
                    # 节流：每 0.5 秒最多发射一次进度更新
                    now = time.time()
                    if now - progress["_last_emit"] >= 0.5:
                        progress["_last_emit"] = now
                        self._emit("task_update", task)
                elif d.get("status") == "finished":
                    # 下载阶段完成（可能还有后处理），进度推到 100
                    task.progress = 100
                    self._emit("task_update", task)
                if self._cancel_event.is_set():
                    raise yt_dlp.utils.DownloadCancelled("用户取消")

            opts["progress_hooks"] = [progress_hook]

            # 单次 extract_info(download=True) 同时下载 + 获取标题
            # 避免 extract_info(download=False) 后再 download() 导致缓存跳过 hooks
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(task.url, download=True)
                task.title = info.get("title", "未知标题")

            if self._cancel_event.is_set() and self._cancel_skip:
                task.status = DownloadTask.STATUS_CANCELLED
            elif self._cancel_event.is_set():
                # 暂停型中止：回退到 WAITING，yt-dlp 下次自动从 .part 续传
                task.status = DownloadTask.STATUS_WAITING
                task.progress = 0
            else:
                task.status = DownloadTask.STATUS_COMPLETED
                task.progress = 100
            self._emit("task_update", task)

        except yt_dlp.utils.DownloadCancelled:
            if self._cancel_skip:
                task.status = DownloadTask.STATUS_CANCELLED
            else:
                # 暂停型中止：回退到 WAITING，下次恢复时自动续传
                task.status = DownloadTask.STATUS_WAITING
                task.progress = 0
            self._emit("task_update", task)

        except Exception as err:
            task.status = DownloadTask.STATUS_FAILED
            task.error_msg = str(err)
            self._emit("task_update", task)
            self._emit("log", f"[失败] {task.title[:50] if task.title else task.url[:80]}\n    {str(err)[:200]}")