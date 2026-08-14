#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站视频下载器 + 提取工具箱 重构版
功能：
  1. 批量下载视频/音频
  2. 统一列表解析（分P/合集/收藏夹自动识别，支持导出TXT）
  3. 附加工具（AI字幕提取、高清封面下载、批量评论爬取）
  4. 任务队列拖拽排序、状态管理

作者: linali_bdcn
源码: https://github.com/linali-bdcn/spider_bilibili

免责声明:
  本工具仅供个人学习和研究使用，使用者应遵守 B站 用户协议及相关法律法规。
  禁止将本工具用于任何商业用途或侵犯他人权益的行为。
  作者不对任何滥用行为承担法律责任。
"""

import os
import sys
import json
import re
import threading
import time
import urllib.request
from datetime import datetime
from typing import List, Dict

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

APP_TITLE = "B站视频下载器 · 全能工具箱"
APP_VERSION = "4.1.0"
CONFIG_FILE = "bili_downloader_config.json"


# ==================== 提取模块 (字幕/封面/评论) ====================
class ExtraExtractor:
    
    @staticmethod
    def _get_base_info(video_url: str, cookie_str: str) -> dict:
        bv_match = re.search(r'BV([a-zA-Z0-9]+)', video_url)
        if not bv_match: raise Exception("无效的B站视频URL")
        bvid = bv_match.group(0)
        
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"}
        if cookie_str: headers['Cookie'] = cookie_str
        
        resp = requests.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data['code'] != 0: raise Exception(data.get('message'))
        return data['data'], headers, bvid

    @staticmethod
    def extract_subtitle(video_url: str, output_dir: str, output_format: str, cookie_str: str = "", progress_callback=None) -> dict:
        result = {"success": False, "files": [], "message": ""}
        try:
            if progress_callback: progress_callback("正在获取视频信息...")
            v_data, headers, bvid = ExtraExtractor._get_base_info(video_url, cookie_str)
            cid = v_data.get('cid')
            title = re.sub(r'[\\/*?:"<>|]', '_', v_data.get('title', 'subtitle'))
            
            if progress_callback: progress_callback("正在查找字幕...")
            sub_api = f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}"
            sub_data = requests.get(sub_api, headers=headers, timeout=10).json()
            
            subtitles = sub_data.get('data', {}).get('subtitle', {}).get('subtitles') or []
            if not subtitles: return {"success": False, "message": "该视频没有字幕"}
            
            subtitle_url = next((s.get('subtitle_url') or s.get('url') for s in subtitles if s.get('lan') == 'ai'), None)
            if not subtitle_url: subtitle_url = subtitles[0].get('subtitle_url') or subtitles[0].get('url')
            if subtitle_url and subtitle_url.startswith('//'): subtitle_url = 'https:' + subtitle_url
            if not subtitle_url: return {"success": False, "message": "字幕链接为空"}
            
            if progress_callback: progress_callback("正在下载字幕...")
            req = urllib.request.Request(subtitle_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                sub_json = json.loads(resp.read().decode('utf-8'))
                if 'body' in sub_json: sub_json = sub_json['body']
            
            os.makedirs(output_dir, exist_ok=True)
            srt_path = os.path.join(output_dir, f"{title}.srt")
            
            # JSON to SRT
            lines = []
            for idx, item in enumerate(sub_json, 1):
                content = item.get("content", "").strip()
                if not content: continue
                s_h, s_m, s_s = int(item["from"] // 3600), int((item["from"] % 3600) // 60), item["from"] % 60
                e_h, e_m, e_s = int(item["to"] // 3600), int((item["to"] % 3600) // 60), item["to"] % 60
                start = f"{s_h:02d}:{s_m:02d}:{int(s_s):02d},{int((s_s-int(s_s))*1000):03d}"
                end = f"{e_h:02d}:{e_m:02d}:{int(e_s):02d},{int((e_s-int(e_s))*1000):03d}"
                lines.extend([str(idx), f"{start} --> {end}", content, ""])
                
            if not lines: return {"success": False, "message": "字幕转换失败"}
            with open(srt_path, "w", encoding="utf-8") as f: f.write("\n".join(lines))
            result["files"].append(srt_path)
            
            # SRT to TXT
            if output_format in ["txt", "both"]:
                txt_path = os.path.join(output_dir, f"{title}.txt")
                txt_lines = [l.strip() for l in lines if l.strip() and not re.match(r'^\d+$', l.strip()) and '-->' not in l]
                with open(txt_path, "w", encoding="utf-8") as f: f.write("\n".join(txt_lines))
                result["files"].append(txt_path)
                
            result["success"] = True
            result["message"] = "字幕提取成功"
        except Exception as e:
            result["message"] = f"提取失败: {str(e)}"
        return result

    @staticmethod
    def extract_cover(video_url: str, output_dir: str, cookie_str: str = "", progress_callback=None) -> dict:
        try:
            if progress_callback: progress_callback("正在获取视频信息...")
            v_data, headers, _ = ExtraExtractor._get_base_info(video_url, cookie_str)
            pic_url = v_data.get('pic')
            if not pic_url: return {"success": False, "message": "未找到封面链接"}
            
            title = re.sub(r'[\\/*?:"<>|]', '_', v_data.get('title', 'cover'))
            os.makedirs(output_dir, exist_ok=True)
            save_path = os.path.join(output_dir, f"{title}_封面.jpg")
            
            if progress_callback: progress_callback("正在下载封面图像...")
            img_data = requests.get(pic_url, headers=headers, timeout=15).content
            with open(save_path, 'wb') as f: f.write(img_data)
            return {"success": True, "files": [save_path], "message": "封面保存成功"}
        except Exception as e:
            return {"success": False, "message": f"封面获取失败: {str(e)}"}

    @staticmethod
    def extract_comments(video_url: str, output_dir: str, cookie_str: str = "", progress_callback=None) -> dict:
        try:
            if progress_callback: progress_callback("正在获取视频信息...")
            v_data, headers, _ = ExtraExtractor._get_base_info(video_url, cookie_str)
            aid = v_data.get('aid')
            title = re.sub(r'[\\/*?:"<>|]', '_', v_data.get('title', 'comments'))
            
            comments = []
            page = 1
            max_pages = 20  # 为防风控，最多抓取前20页（约400条顶级评论）
            
            while page <= max_pages:
                if progress_callback: progress_callback(f"正在抓取第 {page} 页评论...")
                api = f"https://api.bilibili.com/x/v2/reply?type=1&oid={aid}&pn={page}"
                res_data = requests.get(api, headers=headers, timeout=10).json()
                
                if res_data['code'] != 0: break
                replies = res_data.get('data', {}).get('replies')
                if not replies: break  # 没有更多评论了
                
                for reply in replies:
                    user = reply['member']['uname']
                    content = reply['content']['message'].replace('\n', '  ')
                    likes = reply['like']
                    ctime = datetime.fromtimestamp(reply['ctime']).strftime('%Y-%m-%d %H:%M')
                    comments.append(f"[{ctime}] {user} (赞:{likes}): {content}")
                    
                page += 1
                time.sleep(0.5)  # 接口请求缓冲，防止被屏蔽
                
            if not comments: return {"success": False, "message": "未抓取到任何评论"}
            
            os.makedirs(output_dir, exist_ok=True)
            save_path = os.path.join(output_dir, f"{title}_评论.txt")
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(f"视频：{v_data.get('title')}\n")
                f.write(f"抓取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*60 + "\n\n")
                f.write("\n".join(comments))
                
            return {"success": True, "files": [save_path], "message": f"成功提取 {len(comments)} 条评论"}
        except Exception as e:
            return {"success": False, "message": f"评论获取失败: {str(e)}"}


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
        if self.is_running: return
        self.is_running = True
        self.is_paused = False
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
    
    def pause(self): self.is_paused = True
    def resume(self): self.is_paused = False
    def cancel_current(self): self.cancel_current = True
    
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
            if not self.is_running: break
            
            task = None
            with self._lock:
                for t in self.tasks:
                    if t.status == DownloadTask.STATUS_WAITING:
                        task = t
                        break
            if not task:
                time.sleep(0.5)
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
            if self.cancel_current: task.status = DownloadTask.STATUS_CANCELLED
            else:
                task.status = DownloadTask.STATUS_COMPLETED
                task.progress = 100
            self.app.root.after(0, lambda t=task: self.app._update_task_ui(t))
        except Exception as err:
            task.status = DownloadTask.STATUS_FAILED
            task.error_msg = str(err)
            self.app.root.after(0, lambda t=task: self.app._update_task_ui(t))
            self.app.root.after(0, lambda: self.app._log(f"❌ 下载失败: {task.title[:50]}\n    {str(err)[:200]}"))


# ==================== 主应用类 ====================
class BiliDownloader:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry("900x780")
        self.root.minsize(800, 700)
        
        self.download_path = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        self.mode_var = tk.StringVar(value="best")
        self.cookie_method = tk.StringVar(value="browser")
        self.browser_var = tk.StringVar(value="chrome")
        self.cookie_file_var = tk.StringVar(value="")
        self.sub_format = tk.StringVar(value="both")
        
        self.config = self._load_config()
        self.download_manager = DownloadManager(self)
        
        self._last_ui_update = 0
        self._create_ui()
        self._apply_config()
    
    def _load_config(self):
        default = {
            "download_path": os.path.join(os.path.expanduser("~"), "Downloads"),
            "cookie_method": "browser", "browser": "chrome", "cookie_file": "", "mode": "best"
        }
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    default.update(json.load(f))
        except: pass
        return default
    
    def _save_config(self):
        cfg = {
            "download_path": self.download_path.get(), "cookie_method": self.cookie_method.get(),
            "browser": self.browser_var.get(), "cookie_file": self.cookie_file_var.get(), "mode": self.mode_var.get()
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except: pass
    
    def _apply_config(self):
        self.download_path.set(self.config.get("download_path", ""))
        self.mode_var.set(self.config.get("mode", "best"))
        self.cookie_method.set(self.config.get("cookie_method", "browser"))
        self.browser_var.set(self.config.get("browser", "chrome"))
        self.cookie_file_var.set(self.config.get("cookie_file", ""))
        self._on_cookie_method_change()
    
    def _on_cookie_method_change(self):
        for widget in self.cookie_config_frame.winfo_children(): widget.destroy()
        method = self.cookie_method.get()
        if method == "browser":
            ttk.Label(self.cookie_config_frame, text="浏览器:").pack(side=tk.LEFT, padx=5)
            for text, val in [("Chrome", "chrome"), ("Edge", "edge"), ("Firefox", "firefox")]:
                ttk.Radiobutton(self.cookie_config_frame, text=text, value=val, variable=self.browser_var).pack(side=tk.LEFT, padx=3)
            ttk.Label(self.cookie_config_frame, text="（使用前请关闭浏览器）", foreground="gray").pack(side=tk.LEFT, padx=10)
        elif method == "file":
            frame = ttk.Frame(self.cookie_config_frame)
            frame.pack(fill=tk.X)
            ttk.Label(frame, text="Netscape文件:").pack(side=tk.LEFT)
            ttk.Entry(frame, textvariable=self.cookie_file_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            ttk.Button(frame, text="浏览", command=self._browse_cookie_file).pack(side=tk.LEFT)
        else:
            ttk.Label(self.cookie_config_frame, text="不使用Cookie，高画质将受限", foreground="gray").pack(anchor=tk.W)
    
    def _browse_cookie_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path: self.cookie_file_var.set(path)
    
    def _prepare_cookie_opts(self, opts: dict):
        if self.cookie_method.get() == "browser": opts['cookiesfrombrowser'] = (self.browser_var.get(),)
        elif self.cookie_method.get() == "file" and os.path.exists(self.cookie_file_var.get()):
            opts['cookiefile'] = self.cookie_file_var.get()
            
    def _get_cookie_str_for_requests(self) -> str:
        if self.cookie_method.get() == "file" and os.path.exists(self.cookie_file_var.get()):
            cookies = []
            try:
                with open(self.cookie_file_var.get(), 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split('\t')
                        if len(parts) >= 7: cookies.append(f"{parts[5]}={parts[6]}")
            except: pass
            return "; ".join(cookies)
        return ""
    
    def _get_ydl_opts(self, task):
        opts = {
            'paths': {'home': self.download_path.get()}, 'outtmpl': '%(title)s.%(ext)s',
            'quiet': True, 'no_warnings': True, 'ignoreerrors': False, 'retries': 10,
            'http_headers': {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.bilibili.com/'},
        }
        self._prepare_cookie_opts(opts)
        if task.mode == "audio":
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}]
        elif task.mode == "720": opts['format'] = 'best[height<=720]'
        elif task.mode == "480": opts['format'] = 'best[height<=480]'
        else: opts['format'] = 'bestvideo+bestaudio/best'
        opts['merge_output_format'] = 'mp4'
        return opts
    
    # ---------- UI 搭建 ----------
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
        notebook.add(download_tab, text="📥 视频下载")
        self._build_download_tab(download_tab)
        
        tools_tab = ttk.Frame(notebook)
        notebook.add(tools_tab, text="🧰 字幕/更多提取")
        self._build_tools_tab(tools_tab)
        
        settings_tab = ttk.Frame(notebook)
        notebook.add(settings_tab, text="⚙️ 设置")
        self._build_settings_tab(settings_tab)
    
    def _build_download_tab(self, parent):
        url_frame = ttk.LabelFrame(parent, text="视频链接（每行一个，支持视频/分P/合集/主页）", padding=8)
        url_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        btn_line = ttk.Frame(url_frame)
        btn_line.pack(fill=tk.X, pady=(0,5))
        ttk.Button(btn_line, text="清空", command=lambda: self.url_text.delete("1.0", tk.END), width=8).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btn_line, text="粘贴", command=self._paste_urls, width=8).pack(side=tk.RIGHT, padx=2)
        
        self.url_text = tk.Text(url_frame, height=5, wrap=tk.WORD)
        scroll_y = ttk.Scrollbar(url_frame, orient=tk.VERTICAL, command=self.url_text.yview)
        self.url_text.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.url_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=8)
        
        ttk.Button(action_frame, text="➕ 快速添加队列", command=self._add_to_queue, width=15).pack(side=tk.LEFT, padx=2)
        self.start_btn = ttk.Button(action_frame, text="▶️ 开始下载", command=self._start_download, width=12)
        self.start_btn.pack(side=tk.LEFT, padx=2)
        self.pause_btn = ttk.Button(action_frame, text="⏸️ 暂停", command=self._toggle_pause, state=tk.DISABLED, width=8)
        self.pause_btn.pack(side=tk.LEFT, padx=2)
        self.skip_btn = ttk.Button(action_frame, text="⏭️ 跳过", command=self._skip_current, state=tk.DISABLED, width=8)
        self.skip_btn.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(action_frame, text="🗑️ 清除已完成", command=self._clear_completed, width=12).pack(side=tk.RIGHT, padx=2)
        self.list_btn = ttk.Button(action_frame, text="📑 解析列表 (分P/合集)", command=self._parse_list, width=20)
        self.list_btn.pack(side=tk.RIGHT, padx=10)
        
        mode_frame = ttk.Frame(parent)
        mode_frame.pack(fill=tk.X, pady=2)
        ttk.Label(mode_frame, text="下载模式:").pack(side=tk.LEFT)
        for text, val in [("最佳画质", "best"), ("仅音频", "audio"), ("720P", "720"), ("480P", "480")]:
            ttk.Radiobutton(mode_frame, text=text, value=val, variable=self.mode_var).pack(side=tk.LEFT, padx=8)
    
    def _build_tools_tab(self, parent):
        main = ttk.Frame(parent, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        url_frame = ttk.Frame(main)
        url_frame.pack(fill=tk.X, pady=5)
        ttk.Label(url_frame, text="单视频链接:").pack(side=tk.LEFT)
        self.tool_url_var = tk.StringVar()
        ttk.Entry(url_frame, textvariable=self.tool_url_var, width=60).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(url_frame, text="用下载页链接", command=lambda: self.tool_url_var.set(self.url_text.get("1.0", tk.END).strip().split('\n')[0])).pack(side=tk.LEFT)
        
        tools_frame = ttk.LabelFrame(main, text="🔧 提取工具 (文件将保存到全局下载路径)", padding=10)
        tools_frame.pack(fill=tk.X, pady=10)
        
        # 1. 字幕
        sub_frame = ttk.Frame(tools_frame)
        sub_frame.pack(fill=tk.X, pady=5)
        ttk.Label(sub_frame, text="1. 字幕提取:").pack(side=tk.LEFT, padx=(0, 10))
        for t,v in [("SRT字幕", "srt"), ("纯文本", "txt"), ("全部生成", "both")]:
            ttk.Radiobutton(sub_frame, text=t, value=v, variable=self.sub_format).pack(side=tk.LEFT, padx=5)
        ttk.Button(sub_frame, text="📥 提取字幕", command=lambda: self._trigger_extra("subtitle")).pack(side=tk.LEFT, padx=20)
        
        # 2. 其他提取
        media_frame = ttk.Frame(tools_frame)
        media_frame.pack(fill=tk.X, pady=10)
        ttk.Label(media_frame, text="2. 附加信息:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(media_frame, text="🖼️ 下载高清封面", command=lambda: self._trigger_extra("cover")).pack(side=tk.LEFT, padx=5)
        ttk.Button(media_frame, text="💬 批量下载评论(TXT)", command=lambda: self._trigger_extra("comments")).pack(side=tk.LEFT, padx=5)
        
        # 提取日志
        log_frame = ttk.LabelFrame(main, text="提取工具日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.sub_log = tk.Text(log_frame, height=6, state=tk.DISABLED, wrap=tk.WORD)
        scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.sub_log.yview)
        self.sub_log.configure(yscrollcommand=scroll.set)
        self.sub_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _build_settings_tab(self, parent):
        settings = ttk.Frame(parent, padding=10)
        settings.pack(fill=tk.BOTH, expand=True)
        
        path_frame = ttk.Frame(settings)
        path_frame.pack(fill=tk.X, pady=5)
        ttk.Label(path_frame, text="全局保存路径:").pack(side=tk.LEFT)
        ttk.Entry(path_frame, textvariable=self.download_path).pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="浏览", command=lambda: self.download_path.set(filedialog.askdirectory() or self.download_path.get())).pack(side=tk.LEFT)
        
        cookie_frame = ttk.LabelFrame(settings, text="Cookie 身份授权 (突破清晰度/解析合集必备)", padding=8)
        cookie_frame.pack(fill=tk.X, pady=10)
        for t,v in [("浏览器自动获取(推荐)", "browser"), ("本地Netscape文件", "file"), ("无Cookie(受限)", "none")]:
            ttk.Radiobutton(cookie_frame, text=t, value=v, variable=self.cookie_method, command=self._on_cookie_method_change).pack(anchor=tk.W, pady=2)
        self.cookie_config_frame = ttk.Frame(cookie_frame)
        self.cookie_config_frame.pack(fill=tk.X, pady=5)

        # 关于与免责声明
        about_frame = ttk.LabelFrame(settings, text="关于与免责声明", padding=8)
        about_frame.pack(fill=tk.X, pady=10)
        ttk.Label(about_frame, text="作者: linali_bdcn").pack(anchor=tk.W)
        ttk.Label(about_frame, text="源码: https://github.com/linali-bdcn/spider_bilibili", foreground="blue", cursor="hand2").pack(anchor=tk.W)
        ttk.Label(about_frame, text="本工具仅供个人学习和研究使用，使用者应遵守 B站 用户协议及相关法律法规。", foreground="gray").pack(anchor=tk.W, pady=(5, 0))
        ttk.Label(about_frame, text="禁止将本工具用于任何商业用途或侵犯他人权益的行为。", foreground="gray").pack(anchor=tk.W)
        ttk.Label(about_frame, text="作者不对任何滥用行为承担法律责任。", foreground="gray").pack(anchor=tk.W)

        ttk.Button(settings, text="保存设置", command=self._save_config).pack(pady=10)
    
    def _create_queue_panel(self, parent):
        stats_frame = ttk.Frame(parent)
        stats_frame.pack(fill=tk.X, pady=5)
        self.stats_var = tk.StringVar(value="等待:0 下载中:0 完成:0 失败:0")
        ttk.Label(stats_frame, textvariable=self.stats_var).pack(side=tk.LEFT)
        
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.task_tree = ttk.Treeview(tree_frame, columns=("title", "status", "progress", "url"), show="headings", height=10)
        for col, text, w in [("title","标题",350), ("status","状态",80), ("progress","进度",80), ("url","链接",300)]:
            self.task_tree.heading(col, text=text)
            self.task_tree.column(col, width=w)
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=scroll.set)
        self.task_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
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
        ttk.Label(parent, textvariable=self.status_var).pack(anchor=tk.W, pady=2)
        
        log_frame = ttk.LabelFrame(parent, text="下载日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        self.log_text = tk.Text(log_frame, height=5, state=tk.DISABLED, wrap=tk.WORD)
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    # ---------- 功能函数 ----------
    def _log(self, msg, is_sub=False):
        timestamp = datetime.now().strftime("%H:%M:%S")
        target = self.sub_log if is_sub else self.log_text
        target.config(state=tk.NORMAL)
        target.insert(tk.END, f"[{timestamp}] {msg}\n")
        target.see(tk.END)
        target.config(state=tk.DISABLED)
        
    def _paste_urls(self):
        try:
            clip = self.root.clipboard_get()
            if clip:
                current = self.url_text.get("1.0", tk.END).strip()
                self.url_text.insert(tk.END, ("\n" if current else "") + clip)
        except: pass

    # ---------- 统一列表解析 ----------
    def _parse_list(self):
        text = self.url_text.get("1.0", tk.END).strip()
        if not text: return messagebox.showwarning("提示", "请先输入视频链接")
        url = text.split('\n')[0].strip()
        self.status_var.set("正在解析列表信息...")
        self.list_btn.config(state=tk.DISABLED)
        threading.Thread(target=self._fetch_list_thread, args=(url,), daemon=True).start()

    def _fetch_list_thread(self, url):
        videos = []
        collection_title = "视频列表"
        try:
            bv_match = re.search(r'BV([a-zA-Z0-9]+)', url)
            if bv_match:
                bvid = bv_match.group(0)
                headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.bilibili.com/'}
                cookie_str = self._get_cookie_str_for_requests()
                if cookie_str: headers['Cookie'] = cookie_str
                
                api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
                resp = requests.get(api_url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('code') == 0:
                        v_data = data.get('data', {})
                        collection_title = v_data.get('title', '视频列表')
                        
                        if 'ugc_season' in v_data:
                            ugc_season = v_data['ugc_season']
                            collection_title = ugc_season.get('title', collection_title)
                            idx = 1
                            for sec in ugc_season.get('sections', []):
                                for ep in sec.get('episodes', []):
                                    arc = ep.get('arc', {})
                                    ep_bvid = ep.get('bvid') or arc.get('bvid')
                                    if ep_bvid:
                                        videos.append({'index': idx, 'title': ep.get('title', f'视频{idx}'), 'url': f"https://www.bilibili.com/video/{ep_bvid}", 'duration': arc.get('duration', 0)})
                                        idx += 1
                        else:
                            pages = v_data.get('pages', [])
                            for page in pages:
                                videos.append({'index': page['page'], 'title': page['part'], 'url': f"https://www.bilibili.com/video/{bvid}?p={page['page']}", 'duration': page.get('duration', 0)})
                                
            if not videos:
                opts = {'quiet': True, 'extract_flat': 'in_playlist', 'ignoreerrors': True, 'http_headers': {'User-Agent': 'Mozilla/5.0'}}
                self._prepare_cookie_opts(opts)
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                entries = info.get('entries') if info else None
                if entries:
                    collection_title = info.get('title', '列表')
                    for idx, entry in enumerate(entries):
                        if not entry: continue
                        v_url = entry.get('url') or entry.get('webpage_url')
                        if not v_url and 'id' in entry: v_url = f"https://www.bilibili.com/video/{entry['id']}"
                        if v_url: videos.append({'index': idx+1, 'title': entry.get('title', f'视频{idx+1}'), 'url': v_url, 'duration': entry.get('duration', 0)})

            if videos: self.root.after(0, lambda: self._show_list_window(videos, collection_title))
            else: self.root.after(0, lambda: messagebox.showinfo("提示", "未能识别出视频列表或分P。"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"解析失败:\n{e}"))
        finally:
            self.root.after(0, lambda: self.list_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.status_var.set("✨ 解析完成"))

    def _show_list_window(self, videos, title):
        win = tk.Toplevel(self.root)
        win.title(f"解析结果 - {title[:40]}")
        win.geometry("750x600")
        win.minsize(700, 500)
        win.transient(self.root)
        win.grab_set()
        
        main = ttk.Frame(win, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        btn_action_frame = ttk.Frame(main)
        btn_action_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        ttk.Label(main, text=title[:80], font=("", 10, "bold")).pack(side=tk.TOP, anchor=tk.W)
        ttk.Label(main, text=f"共 {len(videos)} 个视频").pack(side=tk.TOP, anchor=tk.W, pady=(0,5))
        
        btn_frame = ttk.Frame(main)
        btn_frame.pack(side=tk.TOP, fill=tk.X, pady=(0,10))
        
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
            dur_str = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "-"
            item = tree.insert("", tk.END, values=(v['index'], v['title'][:80], dur_str))
            video_data[item] = v
            
        ttk.Button(btn_frame, text="全选", command=lambda: [tree.selection_add(i) for i in tree.get_children()]).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="取消全选", command=lambda: tree.selection_remove(tree.selection())).pack(side=tk.LEFT, padx=3)
        
        def add():
            sel = tree.selection()
            if not sel: return messagebox.showwarning("提示", "请先选择视频", parent=win)
            added = 0
            for item in sel:
                v = video_data[item]
                task = self.download_manager.add_task(v['url'], self.mode_var.get())
                task.title = v['title']
                task.tree_id = self.task_tree.insert("", tk.END, values=(task.title[:50], task.status, "0%", task.url[:80]))
                added += 1
            self._update_stats()
            self._log(f"➕ 添加 {added} 个视频到队列")
            win.destroy()
            if messagebox.askyesno("提示", f"已添加 {added} 个任务，是否立即下载？"): self._start_download()

        def export_txt():
            path = filedialog.asksaveasfilename(parent=win, title="导出列表信息", defaultextension=".txt", initialfile="播放列表导出.txt")
            if not path: return
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"列表: {title}\n")
                    f.write("="*50 + "\n")
                    for v in videos:
                        dur = v['duration']
                        dur_str = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "-"
                        f.write(f"P{v['index']} | {dur_str} | {v['title']} | {v['url']}\n")
                messagebox.showinfo("成功", f"导出成功:\n{path}", parent=win)
            except Exception as e: messagebox.showerror("错误", str(e), parent=win)
            
        ttk.Button(btn_action_frame, text="📥 添加选中到下载队列", command=add, width=22).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_action_frame, text="📄 导出全部信息(TXT)", command=export_txt, width=20).pack(side=tk.LEFT, padx=10)

    # ---------- 工具箱提取逻辑 (字幕/封面/评论) ----------
    def _trigger_extra(self, action_type):
        url = self.tool_url_var.get().strip()
        if not url: return messagebox.showwarning("提示", "请输入视频链接")
        out_dir = self.download_path.get()
        cookie_str = self._get_cookie_str_for_requests()
        
        action_name = {"subtitle": "字幕", "cover": "封面", "comments": "评论"}[action_type]
        self._log(f"🔍 开始提取{action_name}...", True)
        
        def worker():
            cb = lambda msg: self.root.after(0, lambda: self._log(msg, True))
            if action_type == "subtitle":
                res = ExtraExtractor.extract_subtitle(url, out_dir, self.sub_format.get(), cookie_str, cb)
            elif action_type == "cover":
                res = ExtraExtractor.extract_cover(url, out_dir, cookie_str, cb)
            elif action_type == "comments":
                res = ExtraExtractor.extract_comments(url, out_dir, cookie_str, cb)
                
            self.root.after(0, lambda: self._on_extra_done(res))
            
        threading.Thread(target=worker, daemon=True).start()

    def _on_extra_done(self, result):
        if result["success"]:
            self._log(f"✅ {result['message']}", True)
            for f in result.get("files", []): self._log(f"   📄 {os.path.basename(f)}", True)
        else:
            self._log(f"❌ {result['message']}", True)

    # ---------- 队列互动逻辑 ----------
    def _update_stats(self):
        w, d, c, f = self.download_manager.get_stats()
        self.stats_var.set(f"等待:{w} 下载中:{d} 完成:{c} 失败:{f}")
        total = len(self.download_manager.tasks)
        self.total_progress['value'] = (c + f) * 100 / total if total > 0 else 0
        
    def _update_task_ui(self, task):
        now = time.time()
        if now - self._last_ui_update < 0.1 and task.status == DownloadTask.STATUS_DOWNLOADING: return
        self._last_ui_update = now
        if task.tree_id:
            try: self.task_tree.item(task.tree_id, values=(task.title[:50], task.status, f"{task.progress}%", task.url[:80]))
            except: pass
        self._update_stats()
        if task.status == DownloadTask.STATUS_DOWNLOADING: self.current_progress['value'] = task.progress

    def _on_all_completed(self):
        if self.start_btn: self.start_btn.config(state=tk.NORMAL)
        if self.pause_btn: self.pause_btn.config(state=tk.DISABLED, text="⏸️ 暂停")
        if self.skip_btn: self.skip_btn.config(state=tk.DISABLED)
        self.current_progress['value'] = 0
        _,_,c,f = self.download_manager.get_stats()
        self.status_var.set(f"✅ 全部完成！成功:{c} 失败:{f}")
        
    def _add_to_queue(self):
        text = self.url_text.get("1.0", tk.END).strip()
        urls = [line.strip() for line in text.split('\n') if line.strip().startswith(('http://','https://'))]
        if not urls: return messagebox.showwarning("提示", "没有有效链接")
        tasks = self.download_manager.add_tasks(urls, self.mode_var.get())
        for task in tasks: task.tree_id = self.task_tree.insert("", tk.END, values=(task.title, task.status, "0%", task.url[:80]))
        self.url_text.delete("1.0", tk.END)
        self._update_stats()

    def _start_download(self):
        if not any(t.status == DownloadTask.STATUS_WAITING for t in self.download_manager.tasks):
            return messagebox.showwarning("提示", "没有等待下载的任务")
        self.download_manager.start()
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.skip_btn.config(state=tk.NORMAL)
        self.status_var.set("🚀 开始下载")

    def _toggle_pause(self):
        if self.download_manager.is_paused:
            self.download_manager.resume()
            self.pause_btn.config(text="⏸️ 暂停")
        else:
            self.download_manager.pause()
            self.pause_btn.config(text="▶️ 继续")
            
    def _skip_current(self):
        if self.download_manager.current_task:
            self.download_manager.cancel_current = True
            self.status_var.set("⏭️ 跳过当前任务")

    def _clear_completed(self):
        for task in self.download_manager.tasks[:]:
            if task.status in (DownloadTask.STATUS_COMPLETED, DownloadTask.STATUS_FAILED, DownloadTask.STATUS_CANCELLED):
                if task.tree_id:
                    try: self.task_tree.delete(task.tree_id)
                    except: pass
        self.download_manager.clear_completed()
        self._update_stats()

    def _remove_selected(self):
        with self.download_manager._lock:
            for item in self.task_tree.selection():
                for task in self.download_manager.tasks:
                    if task.tree_id == item and task.status == DownloadTask.STATUS_DOWNLOADING:
                        return messagebox.showwarning("提示", "无法删除正在下载的任务，请使用跳过按钮")
            for item in self.task_tree.selection():
                task_to_remove = next((t for t in self.download_manager.tasks if t.tree_id == item), None)
                if task_to_remove: self.download_manager.tasks.remove(task_to_remove)
                try: self.task_tree.delete(item)
                except: pass
        self._update_stats()
        
    def _move_task_up(self):
        for item in self.task_tree.selection():
            idx = self.task_tree.index(item)
            if idx > 0: self.task_tree.move(item, "", idx - 1)
        self._sync_tasks_order()

    def _move_task_down(self):
        for item in reversed(self.task_tree.selection()):
            idx = self.task_tree.index(item)
            if idx < len(self.task_tree.get_children()) - 1: self.task_tree.move(item, "", idx + 1)
        self._sync_tasks_order()
        
    def _move_task_top(self):
        for item in reversed(self.task_tree.selection()):
            self.task_tree.move(item, "", 0)
        self._sync_tasks_order()

    def _sync_tasks_order(self):
        new_tasks = []
        with self.download_manager._lock:
            for item in self.task_tree.get_children():
                task = next((t for t in self.download_manager.tasks if t.tree_id == item), None)
                if task: new_tasks.append(task)
            for task in self.download_manager.tasks:
                if task not in new_tasks: new_tasks.append(task)
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
            if item not in self.task_tree.selection(): self.task_tree.selection_set(item)
            self.task_menu.tk_popup(event.x_root, event.y_root)

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
    
    def _on_close(self):
        self._save_config()
        self.download_manager.is_running = False
        self.root.destroy()

if __name__ == "__main__":
    app = BiliDownloader()
    app.run()