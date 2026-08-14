#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站视频下载器 + 字幕提取工具 重构增强版
功能：
  1. 批量下载视频/音频（支持画质选择、分P下载、播放列表）
  2. AI字幕提取（SRT/纯文本）
  3. Cookie管理（浏览器自动获取 / Netscape文件）
  4. 支持下载任务顺序调整、导出分P列表
依赖：pip install yt-dlp requests
"""

import os
import sys
import json
import re
import threading
import queue
import time
import tempfile
import urllib.request
from datetime import datetime
from typing import Optional, List, Dict, Any

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ==================== 依赖检查 ====================
def check_dependencies():
    missing = []
    try:
        import yt_dlp
    except ImportError:
        missing.append("yt-dlp")
    try:
        import requests
    except ImportError:
        missing.append("requests")
    if missing:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "缺少依赖",
            f"请先安装以下依赖:\n\npip install {' '.join(missing)}\n\n安装后重新运行程序"
        )
        sys.exit(1)

check_dependencies()
import yt_dlp
import requests

APP_TITLE = "B站视频下载器 · 字幕提取工具"
APP_VERSION = "3.1.0"
CONFIG_FILE = "bili_downloader_config.json"


# ==================== 字幕提取模块 ====================
class SubtitleExtractor:
    """B站字幕提取器 - 使用官方API，不依赖yt-dlp"""
    
    @staticmethod
    def seconds_to_srt_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        ms = int((secs - int(secs)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(secs):02d},{ms:03d}"
    
    @staticmethod
    def convert_json_to_srt(subtitle_json: List[Dict], output_path: str) -> bool:
        if not isinstance(subtitle_json, list):
            return False
        lines = []
        for idx, item in enumerate(subtitle_json, 1):
            start = item.get("from", 0)
            end = item.get("to", 0)
            content = item.get("content", "").strip()
            if not content:
                continue
            lines.append(str(idx))
            lines.append(f"{SubtitleExtractor.seconds_to_srt_time(start)} --> {SubtitleExtractor.seconds_to_srt_time(end)}")
            lines.append(content)
            lines.append("")
        if not lines:
            return False
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return True
    
    @staticmethod
    def srt_to_txt(srt_path: str, txt_path: str):
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
        lines = []
        for line in content.splitlines():
            line = line.strip()
            if line and not re.match(r'^\d+$', line) and '-->' not in line:
                lines.append(line)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    
    @staticmethod
    def extract_from_video_url(video_url: str, output_dir: str, output_format: str,
                               cookie_str: str = "", progress_callback=None) -> dict:
        result = {"success": False, "files": [], "message": ""}
        try:
            bv_match = re.search(r'BV([a-zA-Z0-9]+)', video_url)
            if not bv_match:
                result["message"] = "无效的B站视频URL"
                return result
            bvid = bv_match.group(0)
            
            if progress_callback:
                progress_callback("正在获取视频信息...")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.bilibili.com/",
                "Accept": "application/json, text/plain, */*",
            }
            if cookie_str:
                headers['Cookie'] = cookie_str
            
            # 获取cid和标题
            api_view = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
            resp = requests.get(api_view, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data['code'] != 0:
                result["message"] = f"获取视频信息失败: {data.get('message')}"
                return result
            cid = data['data'].get('cid')
            video_title = data['data'].get('title', 'subtitle')
            video_title = re.sub(r'[\\/*?:"<>|]', '_', video_title)
            if not cid:
                result["message"] = "无法获取CID"
                return result
            
            if progress_callback:
                progress_callback("正在查找字幕...")
            
            # 获取字幕列表
            sub_api = f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}"
            resp2 = requests.get(sub_api, headers=headers, timeout=10)
            resp2.raise_for_status()
            sub_data = resp2.json()
            if sub_data['code'] != 0:
                result["message"] = f"字幕API错误: {sub_data.get('message')}"
                return result
            
            subtitle_info = sub_data.get('data', {}).get('subtitle', {})
            subtitles = subtitle_info.get('subtitles') or subtitle_info.get('list') or []
            if not subtitles:
                result["message"] = "该视频没有字幕"
                return result
            
            # 优先AI字幕
            subtitle_url = None
            for sub in subtitles:
                if sub.get('lan') == 'ai':
                    subtitle_url = sub.get('subtitle_url') or sub.get('url')
                    if subtitle_url:
                        break
            if not subtitle_url:
                for sub in subtitles:
                    subtitle_url = sub.get('subtitle_url') or sub.get('url')
                    if subtitle_url:
                        break
            
            if subtitle_url and subtitle_url.startswith('//'):
                subtitle_url = 'https:' + subtitle_url
            
            if not subtitle_url:
                result["message"] = "字幕链接为空"
                return result
            
            if progress_callback:
                progress_callback("正在下载字幕...")
            
            req = urllib.request.Request(subtitle_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp3:
                subtitle_json = json.loads(resp3.read().decode('utf-8'))
                if isinstance(subtitle_json, dict) and 'body' in subtitle_json:
                    subtitle_json = subtitle_json['body']
            
            if not subtitle_json or not isinstance(subtitle_json, list):
                result["message"] = "字幕JSON解析失败"
                return result
            
            os.makedirs(output_dir, exist_ok=True)
            srt_path = os.path.join(output_dir, f"{video_title}.srt")
            if SubtitleExtractor.convert_json_to_srt(subtitle_json, srt_path):
                result["files"].append(srt_path)
                if output_format in ["txt", "both"]:
                    txt_path = os.path.join(output_dir, f"{video_title}.txt")
                    SubtitleExtractor.srt_to_txt(srt_path, txt_path)
                    result["files"].append(txt_path)
                result["success"] = True
                result["message"] = "字幕提取成功"
            else:
                result["message"] = "字幕转换失败"
        except Exception as e:
            result["message"] = f"提取失败: {str(e)}"
        return result


# ==================== 下载任务类 ====================
class DownloadTask:
    STATUS_WAITING = "等待中"
    STATUS_DOWNLOADING = "下载中"
    STATUS_COMPLETED = "已完成"
    STATUS_FAILED = "失败"
    STATUS_CANCELLED = "已取消"
    
    def __init__(self, url, mode="best"):
        self.url = url
        self.mode = mode
        self.status = self.STATUS_WAITING
        self.progress = 0
        self.title = "获取中..."
        self.error_msg = ""
        self.tree_id = None


# ==================== 下载队列管理器 ====================
class DownloadManager:
    def __init__(self, app):
        self.app = app
        self.tasks = []
        self.current_task = None
        self.is_running = False
        self.is_paused = False
        self.cancel_current = False
        self.worker_thread = None
        self._lock = threading.Lock()
    
    def add_task(self, url, mode="best"):
        with self._lock:
            task = DownloadTask(url, mode)
            self.tasks.append(task)
            return task
    
    def add_tasks(self, urls, mode="best"):
        tasks = []
        for url in urls:
            url = url.strip()
            if url and url.startswith(('http://', 'https://')):
                tasks.append(self.add_task(url, mode))
        return tasks
    
    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.is_paused = False
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
    
    def pause(self):
        self.is_paused = True
    
    def resume(self):
        self.is_paused = False
    
    def cancel_current(self):
        self.cancel_current = True
    
    def clear_completed(self):
        with self._lock:
            self.tasks = [t for t in self.tasks if t.status not in 
                          (DownloadTask.STATUS_COMPLETED, DownloadTask.STATUS_FAILED, DownloadTask.STATUS_CANCELLED)]
    
    def get_stats(self):
        with self._lock:
            w = sum(1 for t in self.tasks if t.status == DownloadTask.STATUS_WAITING)
            d = sum(1 for t in self.tasks if t.status == DownloadTask.STATUS_DOWNLOADING)
            c = sum(1 for t in self.tasks if t.status == DownloadTask.STATUS_COMPLETED)
            f = sum(1 for t in self.tasks if t.status in (DownloadTask.STATUS_FAILED, DownloadTask.STATUS_CANCELLED))
            return w, d, c, f
    
    def _worker(self):
        while self.is_running:
            while self.is_paused and self.is_running:
                time.sleep(0.5)
            if not self.is_running:
                break
            
            task = None
            with self._lock:
                for t in self.tasks:
                    if t.status == DownloadTask.STATUS_WAITING:
                        task = t
                        break
                        
            if not task:
                time.sleep(0.5)
                # 再检查一次是否有待处理任务
                with self._lock:
                    if not any(t.status == DownloadTask.STATUS_WAITING for t in self.tasks):
                        self.is_running = False
                        self.app.root.after(0, self.app._on_all_completed)
                        break
                continue

            self.current_task = task
            self.cancel_current = False
            self._download_task(task)
            self.current_task = None
    
    def _download_task(self, task):
        task.status = DownloadTask.STATUS_DOWNLOADING
        self.app.root.after(0, lambda t=task: self.app._update_task_ui(t))
        try:
            opts = self.app._get_ydl_opts(task)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(task.url, download=False)
                task.title = info.get('title', '未知标题')
                self.app.root.after(0, lambda t=task: self.app._update_task_ui(t))
                if self.cancel_current:
                    task.status = DownloadTask.STATUS_CANCELLED
                    self.app.root.after(0, lambda t=task: self.app._update_task_ui(t))
                    return
                ydl.download([task.url])
            if self.cancel_current:
                task.status = DownloadTask.STATUS_CANCELLED
            else:
                task.status = DownloadTask.STATUS_COMPLETED
                task.progress = 100
            self.app.root.after(0, lambda t=task: self.app._update_task_ui(t))
        except Exception as err:
            task.status = DownloadTask.STATUS_FAILED
            task.error_msg = str(err)
            self.app.root.after(0, lambda t=task: self.app._update_task_ui(t))
            error_msg = str(err)[:200]
            self.app.root.after(0, lambda: self.app._log(f"❌ 失败: {task.title[:50]}\n    {error_msg}"))


# ==================== 主应用类 ====================
class BiliDownloader:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry("900x750")
        self.root.minsize(800, 650)
        
        # 配置变量
        self.download_path = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        self.mode_var = tk.StringVar(value="best")
        self.cookie_method = tk.StringVar(value="browser")  # browser, file, none
        self.browser_var = tk.StringVar(value="chrome")
        self.cookie_file_var = tk.StringVar(value="")
        self.sub_format = tk.StringVar(value="both")
        
        # UI组件引用
        self.start_btn = None
        self.pause_btn = None
        self.skip_btn = None
        self.parts_btn = None
        self.collection_btn = None
        
        # 临时Cookie文件列表
        self._temp_cookie_files = []
        
        self.config = self._load_config()
        self.download_manager = DownloadManager(self)
        
        self._last_ui_update = 0
        self._create_ui()
        self._apply_config()
    
    # ---------- 配置管理 ----------
    def _load_config(self):
        default = {
            "download_path": os.path.join(os.path.expanduser("~"), "Downloads"),
            "cookie_method": "browser",
            "browser": "chrome",
            "cookie_file": "",
            "mode": "best"
        }
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    default.update(saved)
        except Exception as e:
            print(f"加载配置失败: {e}")
        return default
    
    def _save_config(self):
        cfg = {
            "download_path": self.download_path.get(),
            "cookie_method": self.cookie_method.get(),
            "browser": self.browser_var.get(),
            "cookie_file": self.cookie_file_var.get(),
            "mode": self.mode_var.get()
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def _apply_config(self):
        self.download_path.set(self.config.get("download_path", ""))
        self.mode_var.set(self.config.get("mode", "best"))
        self.cookie_method.set(self.config.get("cookie_method", "browser"))
        self.browser_var.set(self.config.get("browser", "chrome"))
        self.cookie_file_var.set(self.config.get("cookie_file", ""))
        self._on_cookie_method_change()
    
    # ---------- Cookie 处理 ----------
    def _on_cookie_method_change(self):
        for widget in self.cookie_config_frame.winfo_children():
            widget.destroy()
        method = self.cookie_method.get()
        if method == "browser":
            ttk.Label(self.cookie_config_frame, text="浏览器:").pack(side=tk.LEFT, padx=5)
            browsers = [("Chrome", "chrome"), ("Edge", "edge"), ("Firefox", "firefox")]
            for text, val in browsers:
                ttk.Radiobutton(self.cookie_config_frame, text=text, value=val,
                                variable=self.browser_var).pack(side=tk.LEFT, padx=3)
            ttk.Label(self.cookie_config_frame, text="（使用前请关闭浏览器）", foreground="gray").pack(side=tk.LEFT, padx=10)
        elif method == "file":
            frame = ttk.Frame(self.cookie_config_frame)
            frame.pack(fill=tk.X)
            ttk.Label(frame, text="Netscape格式Cookie文件:").pack(side=tk.LEFT)
            ttk.Entry(frame, textvariable=self.cookie_file_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            ttk.Button(frame, text="浏览", command=self._browse_cookie_file).pack(side=tk.LEFT)
            ttk.Label(self.cookie_config_frame, text="💡 使用浏览器插件导出 Netscape 格式的 cookies.txt", 
                      foreground="gray").pack(anchor=tk.W, pady=2)
        else:
            ttk.Label(self.cookie_config_frame, text="不使用Cookie，部分高画质和合集可能受限", 
                      foreground="gray").pack(anchor=tk.W)
    
    def _browse_cookie_file(self):
        path = filedialog.askopenfilename(
            title="选择Cookie文件", 
            filetypes=[("Netscape cookie files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.cookie_file_var.set(path)
    
    def _prepare_cookie_opts(self, opts: dict):
        method = self.cookie_method.get()
        if method == "browser":
            opts['cookiesfrombrowser'] = (self.browser_var.get(),)
        elif method == "file":
            cookie_file = self.cookie_file_var.get().strip()
            if cookie_file and os.path.exists(cookie_file):
                opts['cookiefile'] = cookie_file
    
    def _get_cookie_str_for_requests(self) -> str:
        method = self.cookie_method.get()
        if method == "file":
            cookie_file = self.cookie_file_var.get().strip()
            if cookie_file and os.path.exists(cookie_file):
                return self._parse_netscape_cookie_file(cookie_file)
        return ""
    
    def _parse_netscape_cookie_file(self, filepath: str) -> str:
        cookies = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        name = parts[5]
                        value = parts[6]
                        if name and value:
                            cookies.append(f"{name}={value}")
        except:
            pass
        return "; ".join(cookies)
    
    # ---------- yt-dlp 配置 ----------
    def _get_ydl_opts(self, task):
        opts = {
            'paths': {'home': self.download_path.get()},
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'retries': 10,
            'fragment_retries': 10,
            'socket_timeout': 30,
            'concurrent_fragment_downloads': 4,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
                'Referer': 'https://www.bilibili.com/',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            },
        }
        self._prepare_cookie_opts(opts)
        
        mode = task.mode
        if mode == "audio":
            opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
            opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}]
        elif mode == "720":
            opts['format'] = 'best[height<=720]'
        elif mode == "480":
            opts['format'] = 'best[height<=480]'
        else:
            opts['format'] = 'bestvideo+bestaudio/best'
        opts['merge_output_format'] = 'mp4'
        return opts
    
    # ---------- UI 创建 ----------
    def _create_ui(self):
        main_paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        top_frame = ttk.Frame(main_paned)
        main_paned.add(top_frame, weight=1)
        self._create_input_panel(top_frame)
        
        bottom_frame = ttk.Frame(main_paned)
        main_paned.add(bottom_frame, weight=2)
        self._create_queue_panel(bottom_frame)
    
    def _create_input_panel(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        download_tab = ttk.Frame(notebook)
        notebook.add(download_tab, text="📥 批量下载")
        self._build_download_tab(download_tab)
        
        subtitle_tab = ttk.Frame(notebook)
        notebook.add(subtitle_tab, text="📝 字幕提取")
        self._build_subtitle_tab(subtitle_tab)
        
        settings_tab = ttk.Frame(notebook)
        notebook.add(settings_tab, text="⚙️ 设置")
        self._build_settings_tab(settings_tab)
    
    def _build_download_tab(self, parent):
        url_frame = ttk.LabelFrame(parent, text="视频链接（每行一个，支持分P和合集链接）", padding=8)
        url_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        btn_line = ttk.Frame(url_frame)
        btn_line.pack(fill=tk.X, pady=(0,5))
        ttk.Button(btn_line, text="清空全部", command=self._clear_urls, width=10).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btn_line, text="粘贴链接", command=self._paste_urls, width=10).pack(side=tk.RIGHT, padx=2)
        
        self.url_text = tk.Text(url_frame, height=6, wrap=tk.WORD)
        scroll_y = ttk.Scrollbar(url_frame, orient=tk.VERTICAL, command=self.url_text.yview)
        self.url_text.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.url_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=8)
        
        ttk.Button(action_frame, text="➕ 添加到队列", command=self._add_to_queue, width=14).pack(side=tk.LEFT, padx=2)
        self.start_btn = ttk.Button(action_frame, text="▶️ 开始下载", command=self._start_download, width=12)
        self.start_btn.pack(side=tk.LEFT, padx=2)
        self.pause_btn = ttk.Button(action_frame, text="⏸️ 暂停", command=self._toggle_pause, state=tk.DISABLED, width=8)
        self.pause_btn.pack(side=tk.LEFT, padx=2)
        self.skip_btn = ttk.Button(action_frame, text="⏭️ 跳过", command=self._skip_current, state=tk.DISABLED, width=8)
        self.skip_btn.pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="🗑️ 清除完成", command=self._clear_completed, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Separator(action_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        self.parts_btn = ttk.Button(action_frame, text="📑 查看分P", command=self._show_parts, width=10)
        self.parts_btn.pack(side=tk.LEFT, padx=2)
        self.collection_btn = ttk.Button(action_frame, text="📚 查看合集", command=self._show_collection, width=10)
        self.collection_btn.pack(side=tk.LEFT, padx=2)
        
        mode_frame = ttk.Frame(parent)
        mode_frame.pack(fill=tk.X, pady=5)
        ttk.Label(mode_frame, text="下载模式:").pack(side=tk.LEFT)
        modes = [("最佳画质", "best"), ("仅音频(MP3)", "audio"), ("720P", "720"), ("480P", "480")]
        for text, val in modes:
            ttk.Radiobutton(mode_frame, text=text, value=val, variable=self.mode_var).pack(side=tk.LEFT, padx=8)
    
    def _build_subtitle_tab(self, parent):
        main = ttk.Frame(parent, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main, text="🎬 B站视频字幕提取（支持AI字幕）", font=("", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(main, text="💡 提示：某些视频需要登录才能获取字幕，请在「设置」中配置Cookie", 
                  foreground="blue").pack(anchor=tk.W, pady=(0,10))
        
        url_frame = ttk.Frame(main)
        url_frame.pack(fill=tk.X, pady=5)
        ttk.Label(url_frame, text="视频链接:").pack(side=tk.LEFT)
        self.sub_url_var = tk.StringVar()
        ttk.Entry(url_frame, textvariable=self.sub_url_var, width=70).pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        ttk.Button(url_frame, text="使用主窗口URL", command=self._use_main_url).pack(side=tk.LEFT)
        
        format_frame = ttk.Frame(main)
        format_frame.pack(fill=tk.X, pady=5)
        ttk.Label(format_frame, text="输出格式:").pack(side=tk.LEFT)
        ttk.Radiobutton(format_frame, text="SRT字幕", value="srt", variable=self.sub_format).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(format_frame, text="纯文本", value="txt", variable=self.sub_format).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(format_frame, text="两者都生成", value="both", variable=self.sub_format).pack(side=tk.LEFT, padx=10)
        
        path_frame = ttk.Frame(main)
        path_frame.pack(fill=tk.X, pady=5)
        ttk.Label(path_frame, text="保存位置:").pack(side=tk.LEFT)
        self.sub_path_var = tk.StringVar(value=self.download_path.get())
        ttk.Entry(path_frame, textvariable=self.sub_path_var, width=60).pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="浏览", command=self._browse_sub_path).pack(side=tk.LEFT)
        
        self.sub_btn = ttk.Button(main, text="📥 提取字幕", command=self._extract_subtitle, width=20)
        self.sub_btn.pack(pady=15)
        
        log_frame = ttk.LabelFrame(main, text="提取日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.sub_log = tk.Text(log_frame, height=8, state=tk.DISABLED, wrap=tk.WORD)
        scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.sub_log.yview)
        self.sub_log.configure(yscrollcommand=scroll.set)
        self.sub_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _build_settings_tab(self, parent):
        settings = ttk.Frame(parent, padding=10)
        settings.pack(fill=tk.BOTH, expand=True)
        
        path_frame = ttk.Frame(settings)
        path_frame.pack(fill=tk.X, pady=5)
        ttk.Label(path_frame, text="下载保存路径:").pack(side=tk.LEFT)
        ttk.Entry(path_frame, textvariable=self.download_path, width=60).pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="浏览", command=self._browse_download_path).pack(side=tk.LEFT)
        
        cookie_frame = ttk.LabelFrame(settings, text="Cookie 设置（用于高画质/合集/字幕）", padding=8)
        cookie_frame.pack(fill=tk.X, pady=10)
        
        methods = [("从浏览器自动获取（推荐）", "browser"), ("使用Netscape文件", "file"), ("不使用Cookie", "none")]
        for text, val in methods:
            ttk.Radiobutton(cookie_frame, text=text, value=val, variable=self.cookie_method,
                            command=self._on_cookie_method_change).pack(anchor=tk.W, padx=5, pady=2)
        
        self.cookie_config_frame = ttk.Frame(cookie_frame)
        self.cookie_config_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(settings, text="说明：从浏览器获取Cookie前请关闭所有浏览器窗口；Netscape文件可用插件导出。", 
                  foreground="gray").pack(anchor=tk.W, pady=5)
        
        ttk.Button(settings, text="保存设置", command=self._save_config).pack(pady=10)
    
    def _create_queue_panel(self, parent):
        stats_frame = ttk.Frame(parent)
        stats_frame.pack(fill=tk.X, pady=5)
        self.stats_var = tk.StringVar(value="等待:0 下载中:0 完成:0 失败:0")
        ttk.Label(stats_frame, textvariable=self.stats_var).pack(side=tk.LEFT)
        
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        columns = ("title", "status", "progress", "url")
        self.task_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12)
        self.task_tree.heading("title", text="视频标题")
        self.task_tree.heading("status", text="状态")
        self.task_tree.heading("progress", text="进度")
        self.task_tree.heading("url", text="链接")
        self.task_tree.column("title", width=350)
        self.task_tree.column("status", width=80)
        self.task_tree.column("progress", width=80)
        self.task_tree.column("url", width=300)
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=scroll.set)
        self.task_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 互动右键菜单
        self.task_menu = tk.Menu(self.root, tearoff=0)
        self.task_menu.add_command(label="置顶任务", command=self._move_task_top)
        self.task_menu.add_command(label="上移任务", command=self._move_task_up)
        self.task_menu.add_command(label="下移任务", command=self._move_task_down)
        self.task_menu.add_separator()
        self.task_menu.add_command(label="删除任务", command=self._remove_selected)
        self.task_menu.add_command(label="复制链接", command=self._copy_url)
        self.task_tree.bind("<Button-3>", self._show_task_menu)
        
        prog_frame = ttk.Frame(parent)
        prog_frame.pack(fill=tk.X, pady=5)
        ttk.Label(prog_frame, text="总进度:").pack(side=tk.LEFT)
        self.total_progress = ttk.Progressbar(prog_frame, maximum=100, length=200)
        self.total_progress.pack(side=tk.LEFT, padx=5)
        ttk.Label(prog_frame, text="当前:").pack(side=tk.LEFT, padx=(20,0))
        self.current_progress = ttk.Progressbar(prog_frame, maximum=100, length=200)
        self.current_progress.pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar(value="✨ 准备就绪")
        ttk.Label(parent, textvariable=self.status_var).pack(anchor=tk.W, pady=3)
        
        log_frame = ttk.LabelFrame(parent, text="下载日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = tk.Text(log_frame, height=6, state=tk.DISABLED, wrap=tk.WORD)
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    # ---------- 辅助方法 ----------
    def _log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _sub_log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.sub_log.config(state=tk.NORMAL)
        self.sub_log.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.sub_log.see(tk.END)
        self.sub_log.config(state=tk.DISABLED)
    
    def _browse_download_path(self):
        p = filedialog.askdirectory(initialdir=self.download_path.get())
        if p:
            self.download_path.set(p)
    
    def _browse_sub_path(self):
        p = filedialog.askdirectory(initialdir=self.sub_path_var.get())
        if p:
            self.sub_path_var.set(p)
    
    def _clear_urls(self):
        self.url_text.delete("1.0", tk.END)
    
    def _paste_urls(self):
        try:
            clip = self.root.clipboard_get()
            if not clip:
                return
            current = self.url_text.get("1.0", tk.END).strip()
            if current:
                self.url_text.insert(tk.END, "\n" + clip)
            else:
                self.url_text.insert(tk.END, clip)
        except:
            pass
    
    def _use_main_url(self):
        text = self.url_text.get("1.0", tk.END).strip()
        if text:
            self.sub_url_var.set(text.split('\n')[0].strip())
        else:
            messagebox.showwarning("提示", "主窗口没有链接")
    
    def _update_stats(self):
        w, d, c, f = self.download_manager.get_stats()
        self.stats_var.set(f"等待:{w} 下载中:{d} 完成:{c} 失败:{f}")
        total = len(self.download_manager.tasks)
        if total > 0:
            self.total_progress['value'] = (c + f) * 100 / total
        else:
            self.total_progress['value'] = 0
    
    def _update_task_ui(self, task):
        now = time.time()
        if now - self._last_ui_update < 0.1 and task.status == DownloadTask.STATUS_DOWNLOADING:
            return
        self._last_ui_update = now
        if task.tree_id:
            try:
                title = task.title[:50] + "..." if len(task.title) > 50 else task.title
                self.task_tree.item(task.tree_id, values=(title, task.status, f"{task.progress}%", task.url[:80]))
            except:
                pass
        self._update_stats()
        if task.status == DownloadTask.STATUS_DOWNLOADING:
            self.current_progress['value'] = task.progress
    
    def _on_all_completed(self):
        if self.start_btn:
            self.start_btn.config(state=tk.NORMAL)
        if self.pause_btn:
            self.pause_btn.config(state=tk.DISABLED, text="⏸️ 暂停")
        if self.skip_btn:
            self.skip_btn.config(state=tk.DISABLED)
        self.current_progress['value'] = 0
        _,_,c,f = self.download_manager.get_stats()
        self.status_var.set(f"✅ 全部完成！成功:{c} 失败:{f}")
        self._log(f"🎉 队列完成 成功:{c} 失败:{f}")
        if c>0 and messagebox.askyesno("完成", f"成功下载{c}个视频，打开下载文件夹？"):
            self._open_folder(self.download_path.get())
    
    def _open_folder(self, path):
        if os.path.exists(path):
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
    
    def _get_mode_display(self):
        m = {"best": "最佳画质", "audio": "仅音频", "720": "720P", "480": "480P"}
        return m.get(self.mode_var.get(), self.mode_var.get())
    
    # ---------- 队列操作 ----------
    def _add_to_queue(self):
        text = self.url_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("提示", "请输入链接")
            return
        urls = [line.strip() for line in text.split('\n') if line.strip().startswith(('http://','https://'))]
        if not urls:
            messagebox.showwarning("提示", "没有有效链接")
            return
        tasks = self.download_manager.add_tasks(urls, self.mode_var.get())
        for task in tasks:
            tid = self.task_tree.insert("", tk.END, values=(task.title, task.status, f"{task.progress}%", task.url[:80]))
            task.tree_id = tid
        self.url_text.delete("1.0", tk.END)
        self._update_stats()
        self._log(f"➕ 添加 {len(tasks)} 个任务")
    
    def _start_download(self):
        has_waiting = any(t.status == DownloadTask.STATUS_WAITING for t in self.download_manager.tasks)
        if not has_waiting:
            messagebox.showwarning("提示", "没有等待下载的任务")
            return
        self.download_manager.start()
        if self.start_btn:
            self.start_btn.config(state=tk.DISABLED)
        if self.pause_btn:
            self.pause_btn.config(state=tk.NORMAL)
        if self.skip_btn:
            self.skip_btn.config(state=tk.NORMAL)
        self.status_var.set("🚀 开始下载")
    
    def _toggle_pause(self):
        if self.download_manager.is_paused:
            self.download_manager.resume()
            if self.pause_btn:
                self.pause_btn.config(text="⏸️ 暂停")
        else:
            self.download_manager.pause()
            if self.pause_btn:
                self.pause_btn.config(text="▶️ 继续")
    
    def _skip_current(self):
        if self.download_manager.current_task:
            self.download_manager.cancel_current = True
            self.status_var.set("⏭️ 跳过当前任务")
    
    def _clear_completed(self):
        for task in self.download_manager.tasks[:]:
            if task.status in (DownloadTask.STATUS_COMPLETED, DownloadTask.STATUS_FAILED, DownloadTask.STATUS_CANCELLED):
                if task.tree_id:
                    try:
                        self.task_tree.delete(task.tree_id)
                    except:
                        pass
        self.download_manager.clear_completed()
        self._update_stats()
    
    def _remove_selected(self):
        with self.download_manager._lock:
            for item in self.task_tree.selection():
                # 防止意外删除正在下载的任务
                for task in self.download_manager.tasks:
                    if task.tree_id == item and task.status == DownloadTask.STATUS_DOWNLOADING:
                        messagebox.showwarning("提示", "无法删除正在下载的任务，请使用上方的【跳过】按钮。")
                        return

            for item in self.task_tree.selection():
                task_to_remove = None
                for task in self.download_manager.tasks:
                    if task.tree_id == item:
                        task_to_remove = task
                        break
                if task_to_remove:
                    self.download_manager.tasks.remove(task_to_remove)
                try:
                    self.task_tree.delete(item)
                except:
                    pass
        self._update_stats()
        
    def _move_task_up(self):
        sel = self.task_tree.selection()
        if not sel: return
        for item in sel:
            idx = self.task_tree.index(item)
            if idx > 0:
                self.task_tree.move(item, "", idx - 1)
        self._sync_tasks_order()

    def _move_task_down(self):
        sel = self.task_tree.selection()
        if not sel: return
        for item in reversed(sel):
            idx = self.task_tree.index(item)
            if idx < len(self.task_tree.get_children()) - 1:
                self.task_tree.move(item, "", idx + 1)
        self._sync_tasks_order()
        
    def _move_task_top(self):
        sel = self.task_tree.selection()
        if not sel: return
        for item in reversed(sel):
            self.task_tree.move(item, "", 0)
        self._sync_tasks_order()

    def _sync_tasks_order(self):
        # 同步界面的排序到底层任务列表
        new_tasks = []
        with self.download_manager._lock:
            for item in self.task_tree.get_children():
                for task in self.download_manager.tasks:
                    if task.tree_id == item:
                        new_tasks.append(task)
                        break
            for task in self.download_manager.tasks:
                if task not in new_tasks:
                    new_tasks.append(task)
            self.download_manager.tasks = new_tasks
    
    def _copy_url(self):
        sel = self.task_tree.selection()
        if sel:
            vals = self.task_tree.item(sel[0], "values")
            if vals and len(vals) >= 4:
                self.root.clipboard_clear()
                self.root.clipboard_append(vals[3])
    
    def _show_task_menu(self, event):
        item = self.task_tree.identify_row(event.y)
        if item:
            # 如果右击的不是已选中的项，则选中它
            if item not in self.task_tree.selection():
                self.task_tree.selection_set(item)
            self.task_menu.tk_popup(event.x_root, event.y_root)
    
    # ---------- 分P功能（使用B站API）----------
    def _show_parts(self):
        text = self.url_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("提示", "请先输入视频链接")
            return
        url = text.split('\n')[0].strip()
        self.status_var.set("正在获取分P信息...")
        self.parts_btn.config(state=tk.DISABLED)
        threading.Thread(target=self._fetch_parts, args=(url,), daemon=True).start()
    
    def _fetch_parts(self, url):
        try:
            bv_match = re.search(r'BV([a-zA-Z0-9]+)', url)
            if not bv_match:
                self.root.after(0, lambda: self._parts_error("无法提取BV号"))
                return
            bvid = bv_match.group(0)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.bilibili.com/',
            }
            cookie_str = self._get_cookie_str_for_requests()
            if cookie_str:
                headers['Cookie'] = cookie_str
            api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
            resp = requests.get(api_url, headers=headers, timeout=10)
            if resp.status_code != 200:
                raise Exception(f"API请求失败: HTTP {resp.status_code}")
            data = resp.json()
            if data['code'] != 0:
                raise Exception(f"API错误: {data.get('message', '未知错误')}")
            pages = data['data'].get('pages', [])
            if not pages or len(pages) <= 1:
                self.root.after(0, self._no_parts_found)
                return
            parts = []
            video_title = data['data'].get('title', '视频')
            for page in pages:
                parts.append({
                    'index': page['page'],
                    'title': page['part'],
                    'url': f"https://www.bilibili.com/video/{bvid}?p={page['page']}",
                    'duration': page.get('duration', 0)
                })
            self.root.after(0, lambda: self._show_parts_window(parts, video_title))
        except Exception as e:
            error_msg = str(e)
            if '412' in error_msg:
                error_msg = "HTTP 412 错误：可能需要登录。请在设置中配置有效的Cookie（建议使用浏览器自动获取）。"
            self.root.after(0, lambda: self._parts_error(error_msg))
    
    def _show_parts_window(self, parts, title):
        self.parts_btn.config(state=tk.NORMAL)
        win = tk.Toplevel(self.root)
        win.title(f"选择分P - {title[:40]}")
        # 【修改点】固定基础窗口大小与最小大小
        win.geometry("750x600")
        win.minsize(700, 500)
        win.transient(self.root)
        win.grab_set()
        
        main = ttk.Frame(win, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        # 【修改点】布局重构：先将底部的操作按钮固定到下方，防止被表格挤出界面
        btn_action_frame = ttk.Frame(main)
        btn_action_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        # 顶部标题栏
        ttk.Label(main, text=title[:80], font=("", 10, "bold")).pack(side=tk.TOP, anchor=tk.W, pady=(0,5))
        
        # 顶部全选等工具栏
        btn_frame = ttk.Frame(main)
        btn_frame.pack(side=tk.TOP, fill=tk.X, pady=(0,10))
        
        # 中间表格容器（填满剩余的所有空间）
        tree_frame = ttk.Frame(main)
        tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        tree = ttk.Treeview(tree_frame, columns=("idx","title","dur"), show="headings", selectmode=tk.EXTENDED)
        tree.heading("idx", text="#")
        tree.heading("title", text="标题")
        tree.heading("dur", text="时长")
        tree.column("idx", width=50)
        tree.column("title", width=450)
        tree.column("dur", width=80)
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        part_data = {}
        for p in parts:
            dur = f"{p['duration']//60}:{p['duration']%60:02d}" if p['duration'] else "-"
            item = tree.insert("", tk.END, values=(p['index'], p['title'][:70], dur))
            part_data[item] = p
        
        ttk.Button(btn_frame, text="全选", command=lambda: self._tree_select_all(tree)).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="取消全选", command=lambda: self._tree_deselect_all(tree)).pack(side=tk.LEFT, padx=3)
        ttk.Label(btn_frame, text=f"下载模式: {self._get_mode_display()}").pack(side=tk.RIGHT)
        
        def add():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("提示", "请选择分P", parent=win)
                return
            mode = self.mode_var.get()
            added = 0
            for item in sel:
                p = part_data[item]
                task = self.download_manager.add_task(p['url'], mode)
                task.title = f"P{p['index']}: {p['title']}"
                tid = self.task_tree.insert("", tk.END, values=(task.title[:50], task.status, "0%", task.url[:80]))
                task.tree_id = tid
                added += 1
            self._update_stats()
            self._log(f"➕ 添加 {added} 个分P")
            win.destroy()
            if messagebox.askyesno("添加成功", f"已添加 {added} 个分P，立即开始下载？"):
                self._start_download()
                
        def export_txt():
            path = filedialog.asksaveasfilename(
                parent=win,
                title="导出分P信息", 
                defaultextension=".txt", 
                filetypes=[("文本文件", "*.txt")],
                initialfile="分P信息导出.txt"
            )
            if not path:
                return
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"视频: {title}\n")
                    f.write("="*50 + "\n")
                    for p in parts:
                        dur = f"{p['duration']//60}:{p['duration']%60:02d}" if p['duration'] else "-"
                        f.write(f"P{p['index']} | {dur} | {p['title']} | {p['url']}\n")
                messagebox.showinfo("成功", f"已成功导出到:\n{path}", parent=win)
            except Exception as e:
                messagebox.showerror("错误", f"导出失败:\n{e}", parent=win)

        ttk.Button(btn_action_frame, text="📥 添加选中到队列", command=add, width=18).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_action_frame, text="📄 导出全部信息(TXT)", command=export_txt, width=20).pack(side=tk.LEFT, padx=10)

    
    def _tree_select_all(self, tree):
        for item in tree.get_children():
            tree.selection_add(item)
    
    def _tree_deselect_all(self, tree):
        tree.selection_remove(tree.selection())
    
    def _no_parts_found(self):
        self.parts_btn.config(state=tk.NORMAL)
        messagebox.showinfo("提示", "该视频没有分P（只有单P）")
    
    def _parts_error(self, err):
        self.parts_btn.config(state=tk.NORMAL)
        messagebox.showerror("错误", f"获取分P失败:\n{err}")
    
    # ---------- 合集功能 ----------
    def _show_collection(self):
        text = self.url_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("提示", "请先输入合集/播放列表链接")
            return
        url = text.split('\n')[0].strip()
        self.status_var.set("正在获取合集信息...")
        self.collection_btn.config(state=tk.DISABLED)
        threading.Thread(target=self._fetch_collection, args=(url,), daemon=True).start()
    
    def _fetch_collection(self, url):
        # 1. 优先尝试使用 B站官方 API 直接解析 UP主合集 (UGC Season)
        try:
            bv_match = re.search(r'BV([a-zA-Z0-9]+)', url)
            if bv_match:
                bvid = bv_match.group(0)
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://www.bilibili.com/',
                }
                cookie_str = self._get_cookie_str_for_requests()
                if cookie_str:
                    headers['Cookie'] = cookie_str
                
                api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
                resp = requests.get(api_url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    # 如果数据中包含 'ugc_season'，说明这是一个标准UP主合集
                    if data.get('code') == 0 and 'ugc_season' in data.get('data', {}):
                        ugc_season = data['data']['ugc_season']
                        collection_title = ugc_season.get('title', 'UP主合集')
                        sections = ugc_season.get('sections', [])
                        
                        videos = []
                        idx = 1
                        for section in sections:
                            for ep in section.get('episodes', []):
                                arc = ep.get('arc', {})
                                bvid_ep = ep.get('bvid') or arc.get('bvid')
                                if not bvid_ep:
                                    continue
                                videos.append({
                                    'index': idx,
                                    'title': ep.get('title', f'视频{idx}'),
                                    'url': f"https://www.bilibili.com/video/{bvid_ep}",
                                    'duration': arc.get('duration', 0)
                                })
                                idx += 1
                                
                        if videos:
                            self.root.after(0, lambda: self._show_collection_window(videos, collection_title))
                            return  # 成功提取，直接返回结束
        except Exception as e:
            print(f"API解析合集失败，尝试回退到yt-dlp: {e}")

        # 2. 如果官方API未命中（比如链接是用户收藏夹、稍后再看、播单、番剧等），回退使用 yt-dlp 兜底
        try:
            # 修改了 extract_flat 参数，提高列表解析成功率
            opts = {'quiet': True, 'extract_flat': 'in_playlist', 'ignoreerrors': True}
            
            method = self.cookie_method.get()
            if method == "browser":
                opts['cookiesfrombrowser'] = (self.browser_var.get(),)
            elif method == "file":
                cf = self.cookie_file_var.get().strip()
                if cf and os.path.exists(cf):
                    opts['cookiefile'] = cf
                    
            opts['http_headers'] = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.bilibili.com/',
            }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            entries = info.get('entries') if info else None
            
            if not entries:
                self.root.after(0, lambda: messagebox.showinfo("提示", "未检测到合集/播放列表。如果是普通多P视频，请使用【查看分P】按钮。"))
                self.root.after(0, lambda: self.collection_btn.config(state=tk.NORMAL))
                return
                
            videos = []
            collection_title = info.get('title', '合集/播放列表')
            for idx, entry in enumerate(entries):
                if not entry:
                    continue
                video_url = entry.get('url') or entry.get('webpage_url')
                if not video_url and 'id' in entry:
                    # 部分列表只会返回id
                    video_url = f"https://www.bilibili.com/video/{entry['id']}"
                if not video_url:
                    continue
                videos.append({
                    'index': idx+1,
                    'title': entry.get('title', f'视频{idx+1}'),
                    'url': video_url,
                    'duration': entry.get('duration', 0)
                })
                
            if videos:
                self.root.after(0, lambda: self._show_collection_window(videos, collection_title))
            else:
                self.root.after(0, lambda: messagebox.showinfo("提示", "未找到有效视频"))
                self.root.after(0, lambda: self.collection_btn.config(state=tk.NORMAL))
                
        except Exception as e:
            error_msg = str(e)
            if '412' in error_msg or 'Sign in' in error_msg:
                error_msg = "可能需要登录拦截。请在【设置】中配置有效的Cookie（建议选择从浏览器自动获取）。"
            self.root.after(0, lambda: messagebox.showerror("错误", f"获取合集失败:\n{error_msg}"))
            self.root.after(0, lambda: self.collection_btn.config(state=tk.NORMAL))
    
    def _show_collection_window(self, videos, title):
            win = tk.Toplevel(self.root)
            win.title(f"选择视频 - {title[:40]}")
            # 【修改点】同样固定合集窗口大小
            win.geometry("750x600")
            win.minsize(700, 500)
            win.transient(self.root)
            win.grab_set()
            
            main = ttk.Frame(win, padding=10)
            main.pack(fill=tk.BOTH, expand=True)
            
            # 优先排布底部按钮栏
            btn_action_frame = ttk.Frame(main)
            btn_action_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
            
            # 顶部信息栏
            ttk.Label(main, text=title[:80], font=("", 10, "bold")).pack(side=tk.TOP, anchor=tk.W)
            ttk.Label(main, text=f"共 {len(videos)} 个视频").pack(side=tk.TOP, anchor=tk.W, pady=(0,5))
            
            # 顶部工具栏
            btn_frame = ttk.Frame(main)
            btn_frame.pack(side=tk.TOP, fill=tk.X, pady=(0,10))
            
            # 中间表格栏
            tree_frame = ttk.Frame(main)
            tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            
            tree = ttk.Treeview(tree_frame, columns=("idx","title","dur"), show="headings", selectmode=tk.EXTENDED)
            tree.heading("idx", text="#")
            tree.heading("title", text="标题")
            tree.heading("dur", text="时长")
            tree.column("idx", width=50)
            tree.column("title", width=450)
            tree.column("dur", width=80)
            scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scroll.set)
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scroll.pack(side=tk.RIGHT, fill=tk.Y)
            
            video_data = {}
            for v in videos:
                dur = v['duration']
                if dur:
                    mins, secs = divmod(int(dur), 60)
                    hours, mins = divmod(mins, 60)
                    dur_str = f"{hours}:{mins:02d}:{secs:02d}" if hours else f"{mins}:{secs:02d}"
                else:
                    dur_str = "-"
                item = tree.insert("", tk.END, values=(v['index'], v['title'][:80], dur_str))
                video_data[item] = v
            
            ttk.Button(btn_frame, text="全选", command=lambda: self._tree_select_all(tree)).pack(side=tk.LEFT, padx=3)
            ttk.Button(btn_frame, text="取消全选", command=lambda: self._tree_deselect_all(tree)).pack(side=tk.LEFT, padx=3)
            ttk.Label(btn_frame, text=f"下载模式: {self._get_mode_display()}").pack(side=tk.RIGHT)
            
            def add():
                sel = tree.selection()
                if not sel:
                    messagebox.showwarning("提示", "请选择视频", parent=win)
                    return
                mode = self.mode_var.get()
                added = 0
                for item in sel:
                    v = video_data[item]
                    task = self.download_manager.add_task(v['url'], mode)
                    task.title = v['title']
                    tid = self.task_tree.insert("", tk.END, values=(task.title[:50], task.status, "0%", task.url[:80]))
                    task.tree_id = tid
                    added += 1
                self._update_stats()
                self._log(f"➕ 添加 {added} 个视频到队列")
                win.destroy()
                if messagebox.askyesno("添加成功", f"已添加 {added} 个视频，立即开始下载？"):
                    self._start_download()
                    
            # 【修改点】新加入的合集信息导出功能
            def export_txt():
                path = filedialog.asksaveasfilename(
                    parent=win,
                    title="导出合集信息", 
                    defaultextension=".txt", 
                    filetypes=[("文本文件", "*.txt")],
                    initialfile="合集信息导出.txt"
                )
                if not path:
                    return
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(f"视频: {title}\n")
                        f.write("="*50 + "\n")
                        for v in videos:
                            dur = v['duration']
                            if dur:
                                # 统一换算为 分钟:秒钟 的格式 (类似 85:31)
                                mins = int(dur) // 60
                                secs = int(dur) % 60
                                dur_str = f"{mins}:{secs:02d}"
                            else:
                                dur_str = "-"
                                
                            f.write(f"P{v['index']} | {dur_str} | {v['title']} | {v['url']}\n")
                    messagebox.showinfo("成功", f"已成功导出到:\n{path}", parent=win)
                except Exception as e:
                    messagebox.showerror("错误", f"导出失败:\n{e}", parent=win)
            
            ttk.Button(btn_action_frame, text="📥 添加选中到队列", command=add, width=18).pack(side=tk.LEFT, padx=10)
            ttk.Button(btn_action_frame, text="📄 导出全部信息(TXT)", command=export_txt, width=20).pack(side=tk.LEFT, padx=10)
            self.collection_btn.config(state=tk.NORMAL)
  
    # ---------- 字幕提取 ----------
    def _extract_subtitle(self):
        url = self.sub_url_var.get().strip()
        if not url:
            messagebox.showwarning("提示", "请输入视频链接")
            return
        out_dir = self.sub_path_var.get().strip() or self.download_path.get()
        fmt = self.sub_format.get()
        cookie_str = self._get_cookie_str_for_requests()
        self.sub_btn.config(state=tk.DISABLED, text="提取中...")
        self._sub_log("🔍 开始提取字幕")
        def progress(msg):
            self.root.after(0, lambda: self._sub_log(msg))
        def do():
            res = SubtitleExtractor.extract_from_video_url(url, out_dir, fmt, cookie_str, progress)
            self.root.after(0, lambda: self._on_extract_done(res))
        threading.Thread(target=do, daemon=True).start()
    
    def _on_extract_done(self, result):
        self.sub_btn.config(state=tk.NORMAL, text="📥 提取字幕")
        if result["success"]:
            self._sub_log(f"✅ {result['message']}")
            for f in result["files"]:
                self._sub_log(f"   📄 {os.path.basename(f)}")
            if messagebox.askyesno("成功", f"字幕保存至:\n{os.path.dirname(result['files'][0])}\n打开文件夹？"):
                self._open_folder(os.path.dirname(result['files'][0]))
        else:
            self._sub_log(f"❌ {result['message']}")
            messagebox.showerror("提取失败", result['message'])
    
    # ---------- 程序运行 ----------
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
    
    def _on_close(self):
        if self.download_manager.is_running:
            if not messagebox.askyesno("确认", "下载进行中，确定退出？"):
                return
        self._save_config()
        for f in self._temp_cookie_files:
            try:
                os.remove(f)
            except:
                pass
        self.download_manager.is_running = False
        self.root.destroy()


if __name__ == "__main__":
    app = BiliDownloader()
    app.run()