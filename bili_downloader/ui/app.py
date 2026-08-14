"""
BiliDownloader 主窗口 — 组装所有模块，注册事件回调。
"""

import os
import re
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from bili_downloader.config import ConfigStore
from bili_downloader.cookie_provider import CookieProvider
from bili_downloader.bili_api import BiliAPI
from bili_downloader.extra_extractor import (
    extract_subtitle, extract_cover, extract_comments,
)
from bili_downloader.download_manager import DownloadManager, DownloadTask

from bili_downloader.ui.download_tab import DownloadTab
from bili_downloader.ui.tools_tab import ToolsTab
from bili_downloader.ui.settings_tab import SettingsTab
from bili_downloader.ui.queue_panel import QueuePanel
from bili_downloader.ui.list_window import ListWindow
from bili_downloader.ui.log_panel import LogPanel

APP_TITLE = "B站视频下载器 · 全能工具箱"
APP_VERSION = "5.0.0"

# ffmpeg 路径
def _get_project_root():
    """项目根目录，兼容 PyInstaller 打包。"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_PROJECT_ROOT = _get_project_root()
_FFMPEG_DIR = os.path.join(_PROJECT_ROOT, "ffmpeg-7.1.1-essentials_build", "bin")
if os.path.isdir(_FFMPEG_DIR):
    os.environ["PATH"] = _FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")


class BiliDownloader:
    """主应用窗口。"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry("950x820")
        self.root.minsize(850, 700)

        # ---- 核心模块 ----
        self.config = ConfigStore()
        self.cookie_provider = CookieProvider(
            method=self.config.get("cookie_method", "browser"),
            browser=self.config.get("browser", "chrome"),
            cookie_file=self.config.get("cookie_file", ""),
        )
        self.dm = DownloadManager(ydl_opts_builder=self._build_ydl_opts)

        # ---- tkinter 变量 ----
        self.download_path = tk.StringVar(value=self.config.get("download_path"))
        self.mode_var = tk.StringVar(value=self.config.get("mode", "best"))
        self.cookie_method = tk.StringVar(value=self.config.get("cookie_method", "browser"))
        self.browser_var = tk.StringVar(value=self.config.get("browser", "chrome"))
        self.cookie_file_var = tk.StringVar(value=self.config.get("cookie_file", ""))

        # ---- 构建 UI ----
        self._create_ui()

        # ---- 注册 DM 事件 ----
        self._register_dm_events()

        # ---- 启动画面 ----
        self._show_splash()

    # ==================== UI 搭建 ====================

    def _create_ui(self):
        # 三栏垂直分割（从上到下：Tab页 → 任务队列 → 全局日志）
        # 使用 grid 权重实现 7:4:6 固定比例，随窗口自动缩放，无可拖拽边界
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        main_frame.grid_rowconfigure(0, weight=7)
        main_frame.grid_rowconfigure(1, weight=4)
        main_frame.grid_rowconfigure(2, weight=6)
        main_frame.grid_columnconfigure(0, weight=1)

        # ---- 第一栏：tab notebook ----
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, sticky=tk.NSEW, pady=(0, 3))
        notebook = ttk.Notebook(top_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        download_frame = ttk.Frame(notebook)
        notebook.add(download_frame, text="视频下载")
        self.download_tab = DownloadTab(
            download_frame,
            mode_var=self.mode_var,
            on_add_queue=self._on_add_queue,
            on_start=self._on_start,
            on_pause=self._on_toggle_pause,
            on_skip=self._on_skip,
            on_clear=self._on_clear_completed,
            on_parse_list=self._on_parse_list,
        )

        tools_frame = ttk.Frame(notebook)
        notebook.add(tools_frame, text="字幕/更多提取")
        self.tools_tab = ToolsTab(tools_frame, on_extract=self._on_extract)

        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="设置")
        self.settings_tab = SettingsTab(
            settings_frame,
            download_path=self.download_path,
            cookie_method=self.cookie_method,
            browser_var=self.browser_var,
            cookie_file_var=self.cookie_file_var,
            on_cookie_change=self._on_cookie_change,
            on_save=self._on_save_config,
        )

        # ---- 第二栏：任务队列 ----
        mid_frame = ttk.Frame(main_frame)
        mid_frame.grid(row=1, column=0, sticky=tk.NSEW, pady=3)
        self.queue_panel = QueuePanel(
            mid_frame, self.dm, self.root,
            download_path_getter=lambda: self.download_path.get(),
            on_started=self._on_download_started,
            on_paused=self._on_download_paused,
            log_callback=self._log,
        )

        # ---- 第三栏：全局日志面板 ----
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=2, column=0, sticky=tk.NSEW, pady=(3, 0))
        self.log = LogPanel(bottom_frame, _PROJECT_ROOT)

    # ---- 日志快捷方法 ----

    def _log(self, level: str, msg: str):
        if level == "OK":
            self.log.success(msg)
        elif level == "ERR":
            self.log.error(msg)
        else:
            self.log.info(msg)

    # ==================== DM 事件回调 ====================

    def _register_dm_events(self):
        self.dm.on("all_completed", self._on_download_all_finished)

    def _on_download_started(self):
        self.download_tab.pause_btn.configure(state=tk.NORMAL, text="暂停")
        self.download_tab.skip_btn.configure(state=tk.NORMAL)
        self.download_tab.start_btn.configure(state=tk.DISABLED)

    def _on_download_paused(self):
        self.download_tab.start_btn.configure(state=tk.NORMAL)
        self.download_tab.pause_btn.configure(state=tk.DISABLED, text="已暂停")
        self.download_tab.skip_btn.configure(state=tk.DISABLED)

    def _on_download_all_finished(self, waiting, completed, failed):
        self.root.after(0, self._on_download_paused)

    # ==================== 下载控制 ====================

    def _on_add_queue(self):
        urls = self.download_tab.get_urls()
        if not urls:
            messagebox.showwarning("提示", "没有有效链接")
            return
        mode = self.mode_var.get()
        self.dm.add_tasks(urls, mode)
        self.download_tab.clear_urls()
        self.queue_panel._rebuild_rows()
        self.log.info(f"添加 {len(urls)} 个任务到队列")

    def _on_start(self):
        # 暂停后恢复：dm.is_running 仍为 True，只需 resume
        if self.dm.is_running and self.dm.is_paused:
            self.dm.resume()
            self.queue_panel.set_status("继续下载")
            self.log.info("恢复下载")
            return
        if not any(t.status == DownloadTask.STATUS_WAITING for t in self.dm.tasks):
            messagebox.showwarning("提示", "没有等待下载的任务")
            return
        self.dm.start()
        self.queue_panel.set_status("开始下载")
        self.log.info("开始下载队列")

    def _on_toggle_pause(self):
        self.dm.pause()
        self.queue_panel.set_status("已暂停")
        self.log.info("暂停下载")

    def _on_skip(self):
        self.dm.cancel_current()
        self.queue_panel.set_status("跳过当前任务")
        self.log.info("跳过当前任务")

    def _on_clear_completed(self):
        self.dm.clear_completed()
        self.queue_panel._rebuild_rows()
        self.log.info("清除已完成任务")

    # ==================== 列表解析 ====================

    def _on_parse_list(self):
        url = self.download_tab.get_first_url()
        if not url:
            messagebox.showwarning("提示", "请先输入视频链接")
            return

        self.download_tab.list_btn.configure(state=tk.DISABLED)
        self.queue_panel.set_status("正在解析列表信息...")
        self.log.info(f"开始解析列表: {url[:80]}")

        threading.Thread(target=self._parse_list_thread, args=(url,), daemon=True).start()

    def _parse_list_thread(self, url: str):
        try:
            cookie_str = self.cookie_provider.get_requests_cookie()
            api = BiliAPI(lambda: cookie_str)
            result = api.parse_playlist(url)

            if result.videos:
                self.root.after(0, lambda: self._show_list_window(result))
                self.root.after(0, lambda: self.log.info(
                    f"列表解析完成: {result.title}, 共 {len(result.videos)} 个视频"))
            else:
                self.root.after(0, lambda: messagebox.showinfo("提示", "未能识别出视频列表"))
                self.root.after(0, lambda: self.log.warn("列表解析: 未能识别"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"解析失败:\n{e}"))
            self.root.after(0, lambda: self.log.error(f"列表解析失败: {e}"))
        finally:
            self.root.after(0, lambda: self.download_tab.list_btn.configure(state=tk.NORMAL))
            self.root.after(0, lambda: self.queue_panel.set_status("解析完成"))

    def _show_list_window(self, result):
        def on_add(selected_videos):
            mode = self.mode_var.get()
            added = 0
            for v in selected_videos:
                self.dm.add_task(v.url, mode)
                added += 1
            self.queue_panel._rebuild_rows()
            self.log.info(f"从列表添加 {added} 个任务")
            if messagebox.askyesno("提示", f"已添加 {added} 个任务，是否立即下载？"):
                self._on_start()

        ListWindow(self.root, result.videos, result.title, on_add,
                   mode_getter=lambda: self.mode_var.get())

    # ==================== 工具箱提取 ====================

    def _on_extract(self, action_type: str):
        url = self.tools_tab.get_url()
        if not url:
            messagebox.showwarning("提示", "请输入视频链接")
            return

        out_dir = self.download_path.get()
        cookie_str = self.cookie_provider.get_requests_cookie()
        fmt = self.tools_tab.sub_format.get()

        action_names = {"subtitle": "字幕", "cover": "封面", "comments": "评论"}
        name = action_names.get(action_type, action_type)
        self.log.info(f"开始提取{name}: {url[:80]}")

        def worker():
            cb = lambda msg: self.root.after(0, lambda: self.log.info(msg))
            api_getter = lambda u: BiliAPI(lambda: cookie_str).get_video_info(u)

            if action_type == "subtitle":
                res = extract_subtitle(url, out_dir, fmt, cookie_str, cb, api_getter)
            elif action_type == "cover":
                res = extract_cover(url, out_dir, cookie_str, cb, api_getter)
            elif action_type == "comments":
                pages = self.tools_tab.comments_pages.get()
                res = extract_comments(url, out_dir, cookie_str, pages, cb, api_getter)
            else:
                return

            self.root.after(0, lambda: self._on_extract_done(res, name))

        threading.Thread(target=worker, daemon=True).start()

    def _on_extract_done(self, result: dict, name: str):
        if result.get("success"):
            self.log.success(f"提取{name}成功: {result['message']}")
            for fpath in result.get("files", []):
                self.log.info(f"  -> {os.path.basename(fpath)}")
        else:
            msg = result.get("message", "失败")
            self.log.error(f"提取{name}失败: {msg}")

    # ==================== Cookie / 配置 ====================

    def _on_cookie_change(self):
        self.settings_tab.rebuild_cookie_subframe()

    def _on_save_config(self):
        self.config.update({
            "download_path": self.download_path.get(),
            "cookie_method": self.cookie_method.get(),
            "browser": self.browser_var.get(),
            "cookie_file": self.cookie_file_var.get(),
            "mode": self.mode_var.get(),
        })
        self.config.save()
        self.cookie_provider.method = self.cookie_method.get()
        self.cookie_provider.browser = self.browser_var.get()
        self.cookie_provider.cookie_file = self.cookie_file_var.get()
        self.log.info("配置已保存")

    def _build_ydl_opts(self, task: DownloadTask) -> dict:
        opts = {
            "paths": {"home": self.download_path.get()},
            "outtmpl": "%(title)s.%(ext)s",
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": False,
            "retries": 10,
            "http_headers": {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.bilibili.com/",
            },
        }
        self.cookie_provider.apply_to_ydl_opts(opts)

        mode = task.mode
        if mode == "audio":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }]
        elif mode == "720":
            opts["format"] = "best[height<=720]"
        elif mode == "480":
            opts["format"] = "best[height<=480]"
        else:
            opts["format"] = "bestvideo+bestaudio/best"

        opts["merge_output_format"] = "mp4"
        return opts

    # ==================== 启动画面 ====================

    def _show_splash(self):
        splash = tk.Toplevel(self.root)
        splash.title("关于")
        splash.resizable(False, False)
        splash.transient(self.root)

        frame = ttk.Frame(splash, padding=24)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="B站视频下载器 · 全能工具箱",
                  font=("", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(frame, text=f"版本: v{APP_VERSION}",
                  foreground="gray").pack(anchor=tk.W, pady=(4, 12))

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        ttk.Label(frame, text="作者: linali_bdcn").pack(anchor=tk.W)
        ttk.Label(frame, text="源码: https://github.com/linali-bdcn/spider_bilibili",
                  foreground="blue", cursor="hand2").pack(anchor=tk.W, pady=(2, 12))

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        ttk.Label(frame, text="Cookie 获取方式",
                  font=("", 9, "bold")).pack(anchor=tk.W)
        for line in [
            "1. 在 Chrome/Edge 安装插件 Get cookies.txt LOCALLY",
            "2. 打开 B站 并登录账号，点击插件图标 -> Export",
            "3. 将导出的 cookies.txt 文件保存到本地",
            "4. 在软件设置中选择\"本地Netscape文件\"并加载该文件",
            "",
            "字幕提取 / 高画质下载 / 合集解析 均需要有效 Cookie",
            "否则将被 B站 风控拦截，无法获取数据。",
        ]:
            if line:
                ttk.Label(frame, text=line, foreground="gray").pack(anchor=tk.W)

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        ttk.Label(frame, text="免责声明",
                  font=("", 9, "bold")).pack(anchor=tk.W)
        for line in [
            "本工具仅供个人学习和研究使用，",
            "使用者应遵守 B站 用户协议及相关法律法规。",
            "禁止用于商业用途或侵犯他人权益的行为。",
        ]:
            ttk.Label(frame, text=line, foreground="gray").pack(anchor=tk.W)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(16, 0))
        ttk.Button(btn_frame, text="我知道了", command=splash.destroy,
                   width=12).pack()

        splash.update_idletasks()
        w = splash.winfo_reqwidth() + 20
        h = splash.winfo_reqheight() + 10
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        splash.geometry(f"{w}x{h}+{x}+{y}")

        splash.focus_force()
        splash.after(200, lambda: splash.bind(
            "<FocusOut>", lambda e: splash.after(80, splash.destroy)))
        splash.wait_window()

    # ==================== 运行 ====================

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        self.log.info("程序关闭")
        self.dm.stop()
        self._on_save_config()
        self.root.destroy()