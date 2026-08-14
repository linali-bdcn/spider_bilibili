"""
任务队列面板 — TreeView + 右键菜单 + 进度条 + 统计栏。
通过 DownloadManager 事件驱动更新。
"""

import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from bili_downloader.download_manager import DownloadManager, DownloadTask


class QueuePanel:
    """任务队列面板。监听 DownloadManager 事件并更新 UI。"""

    def __init__(self, parent: ttk.Frame, dm: DownloadManager, root: tk.Tk,
                 download_path_getter, on_started=None, on_paused=None,
                 log_callback=None):
        """
        download_path_getter: 返回当前下载目录的 callable。
        log_callback: callable(level, msg) 用于写全局日志。
        """
        self._dm = dm
        self._root = root
        self._get_dl_path = download_path_getter
        self._on_started = on_started
        self._on_paused = on_paused
        self._log = log_callback or (lambda l, m: None)

        self.frame = parent

        # ---- TreeView ----
        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("title", "status_line", "type_info"),
            show="headings",
        )
        for col, text, w in [("title", "标题", 350), ("status_line", "状态/进度", 280),
                              ("type_info", "类型/大小", 220)]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=w)

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # ---- 右键菜单 ----
        self.menu = tk.Menu(self._root, tearoff=0)
        self.menu.add_command(label="置顶任务", command=self._move_top)
        self.menu.add_command(label="上移任务", command=self._move_up)
        self.menu.add_command(label="下移任务", command=self._move_down)
        self.menu.add_separator()
        self.menu.add_command(label="打开文件所在文件夹", command=self._open_folder)
        self.menu.add_separator()
        self.menu.add_command(label="删除任务", command=self._remove_selected)
        self.menu.add_command(label="复制链接", command=self._copy_url)
        self.tree.bind("<Button-3>", self._show_menu)

        # ---- 状态 ----
        self.status_var = tk.StringVar(value="准备就绪")
        ttk.Label(self.frame, textvariable=self.status_var).pack(
            anchor=tk.W, pady=2)

        # 注册 DownloadManager 事件
        dm.on("task_update", self._on_task_update)
        dm.on("all_completed", self._on_all_completed)
        dm.on("log", self._on_log)

    # ---- 事件回调 ----

    def _on_task_update(self, task: DownloadTask):
        self._root.after(0, lambda t=task: self._update_row(t))
        # 自动检测下载状态变更，触发按钮状态回调
        has_downloading = any(
            t.status == DownloadTask.STATUS_DOWNLOADING for t in self._dm.tasks
        )
        if has_downloading and self._on_started:
            self._root.after(0, self._on_started)
        elif not has_downloading and self._on_paused:
            self._root.after(0, self._on_paused)

    def _on_all_completed(self, waiting, completed, failed):
        self._root.after(0, lambda: self.status_var.set(
            f"全部完成！成功:{completed - failed} 失败:{failed}"))
        if self._on_paused:
            self._root.after(0, self._on_paused)

    def _on_log(self, msg: str):
        self._log("ERR", msg)

    # ---- UI 刷新 ----

    def _build_values(self, task: DownloadTask):
        """根据任务状态构建三列 values tuple。"""
        title = task.title[:50] if task.title else "获取中..."

        # status_line 逻辑
        if task.status == DownloadTask.STATUS_DOWNLOADING:
            speed_part = f"  [{task.speed_str}]" if task.speed_str else ""
            status_line = f"{task.progress}%{speed_part}"
        elif task.status == DownloadTask.STATUS_COMPLETED:
            status_line = "已完成"
        elif task.status == DownloadTask.STATUS_FAILED:
            status_line = f"失败: {task.error_msg[:40]}"
        else:
            status_line = task.status

        # type_info 逻辑
        parts = [task.format_label]
        if task.size_str:
            parts.append(task.size_str)
        type_info = "  ".join(parts)

        return (title, status_line, type_info)

    def _update_row(self, task: DownloadTask):
        try:
            idx = self._dm.tasks.index(task)
        except ValueError:
            return
        children = self.tree.get_children()
        if idx >= len(children):
            return
        item = children[idx]
        self.tree.item(item, values=self._build_values(task))

    def _rebuild_rows(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for task in self._dm.tasks:
            self.tree.insert("", tk.END, values=self._build_values(task))

    # ---- 右键菜单操作 ----

    def _show_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            if item not in self.tree.selection():
                self.tree.selection_set(item)
            self.menu.tk_popup(event.x_root, event.y_root)

    def _open_folder(self):
        path = self._get_dl_path()
        if path and os.path.isdir(path):
            if os.name == "nt":
                os.startfile(path)
            else:
                subprocess.Popen(["open", path])

    def _remove_selected(self):
        for item in self.tree.selection():
            idx = self.tree.index(item)
            if 0 <= idx < len(self._dm.tasks):
                task = self._dm.tasks[idx]
                if task.status == DownloadTask.STATUS_DOWNLOADING:
                    messagebox.showwarning("提示", "无法删除正在下载的任务")
                    continue
                self._dm.remove_task(task)
        self._rebuild_rows()

    def _move_up(self):
        for item in self.tree.selection():
            idx = self.tree.index(item)
            if idx > 0:
                task = self._dm.tasks[idx]
                self._dm.move_task(task, idx - 1)
        self._rebuild_rows()

    def _move_down(self):
        items = list(self.tree.selection())
        for item in reversed(items):
            idx = self.tree.index(item)
            if idx < len(self._dm.tasks) - 1:
                task = self._dm.tasks[idx]
                self._dm.move_task(task, idx + 1)
        self._rebuild_rows()

    def _move_top(self):
        items = list(self.tree.selection())
        for item in reversed(items):
            idx = self.tree.index(item)
            if idx > 0:
                task = self._dm.tasks[idx]
                self._dm.move_task(task, 0)
        self._rebuild_rows()

    def _copy_url(self):
        sel = self.tree.selection()
        if sel:
            idx = self.tree.index(sel[0])
            if 0 <= idx < len(self._dm.tasks):
                task = self._dm.tasks[idx]
                self._root.clipboard_clear()
                self._root.clipboard_append(task.url)

    # ---- 状态更新 ----

    def set_status(self, msg: str):
        self.status_var.set(msg)