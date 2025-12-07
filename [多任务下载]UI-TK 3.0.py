#!/usr/bin/env python3
"""
B站下载器 - 批量下载版
【新增】支持批量URL下载、下载队列管理
"""

import os
import sys
import threading
import queue  # 【新增】导入队列模块
import json  # 【新增】导入JSON模块
from datetime import datetime  # 【新增】导入时间模块
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ============ 依赖检查 ============
def check_dependencies():
    """检查并提示安装依赖"""
    missing = []
    
    try:
        import yt_dlp
    except ImportError:
        missing.append("yt-dlp")
    
    if missing:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "缺少依赖",
            f"请先安装以下依赖:\n\npip install {' '.join(missing)}\n\n安装后重新运行程序"
        )
        sys.exit(1)
    
    return True

check_dependencies()
import yt_dlp


# 【新增】==================== 下载任务类 ====================
class DownloadTask:
    """下载任务数据类"""
    
    # 任务状态常量
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
        self.tree_id = None  # Treeview中的ID
        self.config = self._load_config() # 加载配置

def _load_config(self):
    """加载配置"""
    config_file = "bili_downloader_config.json"
    default = {
        "download_path": os.path.join(os.path.expanduser("~"), "Downloads"),
        "cookie_source": "none",
        "browser": "chrome",
        "cookie_file": "",
        "mode": "best"
    }
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                default.update(saved)
    except:
        pass
    
    return default

def _save_config(self):
    """保存配置"""
    config = {
        "download_path": self.path_var.get(),
        "cookie_source": self.cookie_source.get(),
        "browser": self.browser_var.get(),
        "cookie_file": self.cookie_file_var.get(),
        "mode": self.mode_var.get()
    }
    
    try:
        with open("bili_downloader_config.json", 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except:
        pass

# 在窗口关闭时保存
def run(self):
    self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    self.root.mainloop()

def _on_close(self):
    self._save_config()
    self.root.destroy()



# 【新增】==================== 下载队列管理器 ====================
class DownloadManager:
    """下载队列管理器"""
    
    def __init__(self, app):
        self.app = app
        self.task_queue = queue.Queue()
        self.tasks = []  # 所有任务列表
        self.current_task = None
        self.is_running = False
        self.is_paused = False
        self.cancel_current = False
        self.worker_thread = None
    
    def add_task(self, url, mode="best"):
        """添加下载任务"""
        task = DownloadTask(url, mode)
        self.tasks.append(task)
        self.task_queue.put(task)
        return task
    
    def add_tasks(self, urls, mode="best"):
        """批量添加任务"""
        tasks = []
        for url in urls:
            url = url.strip()
            if url and url.startswith(('http://', 'https://')):
                task = self.add_task(url, mode)
                tasks.append(task)
        return tasks
    
    def start(self):
        """开始处理队列"""
        if self.is_running:
            return
        
        self.is_running = True
        self.is_paused = False
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
    
    def pause(self):
        """暂停下载"""
        self.is_paused = True
    
    def resume(self):
        """继续下载"""
        self.is_paused = False
    
    def cancel_current_task(self):
        """取消当前任务"""
        self.cancel_current = True
    
    def clear_completed(self):
        """清除已完成的任务"""
        self.tasks = [t for t in self.tasks if t.status not in 
                      (DownloadTask.STATUS_COMPLETED, DownloadTask.STATUS_FAILED, DownloadTask.STATUS_CANCELLED)]
    
    def _worker(self):
        """工作线程"""
        while self.is_running:
            # 检查暂停
            while self.is_paused:
                if not self.is_running:
                    return
                threading.Event().wait(0.5)
            
            try:
                task = self.task_queue.get(timeout=1)
            except queue.Empty:
                self.is_running = False
                self.app.root.after(0, self.app._on_all_completed)
                break
            
            self.current_task = task
            self.cancel_current = False
            self._download_task(task)
            self.current_task = None
    
    def _download_task(self, task):
        """执行单个下载任务"""
        task.status = DownloadTask.STATUS_DOWNLOADING
        self.app.root.after(0, lambda: self.app._update_task_ui(task))
        
        try:
            opts = self.app._get_ydl_opts(task)
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                # 先获取信息
                info = ydl.extract_info(task.url, download=False)
                task.title = info.get('title', '未知标题')
                self.app.root.after(0, lambda: self.app._update_task_ui(task))
                
                # 检查是否取消
                if self.cancel_current:
                    task.status = DownloadTask.STATUS_CANCELLED
                    self.app.root.after(0, lambda: self.app._update_task_ui(task))
                    return
                
                # 下载
                ydl.download([task.url])
            
            task.status = DownloadTask.STATUS_COMPLETED
            task.progress = 100
            self.app.root.after(0, lambda: self.app._update_task_ui(task))
            self.app.root.after(0, lambda: self.app._log(f"✅ 完成: {task.title}"))
            
        except Exception as e:
            task.status = DownloadTask.STATUS_FAILED
            task.error_msg = str(e)
            self.app.root.after(0, lambda: self.app._update_task_ui(task))
            self.app.root.after(0, lambda: self.app._log(f"❌ 失败: {task.url}\n   原因: {str(e)[:50]}"))


# ============ 主程序 ============
class BiliDownloader:
    def __init__(self):
        print("初始化应用...")
        
        self.root = tk.Tk()
        self.root.title("B站视频下载器 - 批量版")
        # 【修改】调整窗口大小以适应新布局
        self.root.geometry("750x600")
        self.root.resizable(True, True)
        
        # 【新增】下载管理器
        self.download_manager = DownloadManager(self)
        
        self._create_ui()
        print("界面创建完成")
    
    def _create_ui(self):
        """创建用户界面"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 【修改】使用 PanedWindow 分割上下区域
        paned = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # ===== 上半部分：输入区域 =====
        top_frame = ttk.Frame(paned)
        paned.add(top_frame, weight=1)
        
        # 【修改】URL输入改为多行文本框
        url_label_frame = ttk.Frame(top_frame)
        url_label_frame.pack(fill=tk.X)
        
        ttk.Label(url_label_frame, text="🔗 视频链接 (每行一个，支持批量):").pack(side=tk.LEFT)
        
        # 【新增】快速操作按钮
        ttk.Button(url_label_frame, text="清空", command=self._clear_urls, width=6).pack(side=tk.RIGHT, padx=2)
        ttk.Button(url_label_frame, text="粘贴", command=self._paste_urls, width=6).pack(side=tk.RIGHT, padx=2)
        
        # 【修改】多行URL输入框
        url_text_frame = ttk.Frame(top_frame)
        url_text_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.url_text = tk.Text(url_text_frame, height=5, wrap=tk.NONE)
        url_scrollbar_y = ttk.Scrollbar(url_text_frame, orient=tk.VERTICAL, command=self.url_text.yview)
        url_scrollbar_x = ttk.Scrollbar(url_text_frame, orient=tk.HORIZONTAL, command=self.url_text.xview)
        self.url_text.configure(yscrollcommand=url_scrollbar_y.set, xscrollcommand=url_scrollbar_x.set)
        
        url_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        url_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.url_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # ===== 设置区域 =====
        settings_frame = ttk.Frame(top_frame)
        settings_frame.pack(fill=tk.X, pady=10)
        
        # 保存路径
        path_frame = ttk.Frame(settings_frame)
        path_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(path_frame, text="📁 保存位置:").pack(side=tk.LEFT)
        
        default_path = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(default_path):
            default_path = os.getcwd()
        
        self.path_var = tk.StringVar(value=default_path)
        ttk.Entry(path_frame, textvariable=self.path_var, width=50).pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="浏览", command=self._browse_path, width=6).pack(side=tk.LEFT)
        ttk.Button(path_frame, text="打开", command=self._open_download_folder, width=6).pack(side=tk.LEFT, padx=5)
        
        # 下载模式
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.pack(fill=tk.X)
        
        ttk.Label(mode_frame, text="📺 下载模式:").pack(side=tk.LEFT)
        
        self.mode_var = tk.StringVar(value="best")
        modes = [
            ("最佳画质", "best"),
            ("仅音频(MP3)", "audio"),
            ("720P", "720"),
            ("480P", "480"),
        ]
        
        for text, value in modes:
            ttk.Radiobutton(mode_frame, text=text, value=value, variable=self.mode_var).pack(side=tk.LEFT, padx=10)
        


        # 【修改】操作按钮区域
        btn_frame = ttk.Frame(settings_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        # 【修改】主要按钮
        self.add_btn = ttk.Button(btn_frame, text="➕ 添加到队列", command=self._add_to_queue, width=15)
        self.add_btn.pack(side=tk.LEFT, padx=5)
        
        self.start_btn = ttk.Button(btn_frame, text="▶️ 开始下载", command=self._start_download, width=12)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        # 【新增】暂停/继续按钮
        self.pause_btn = ttk.Button(btn_frame, text="⏸️ 暂停", command=self._toggle_pause, width=10, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        
        # 【新增】取消当前任务按钮
        self.cancel_btn = ttk.Button(btn_frame, text="⏹️ 跳过当前", command=self._skip_current, width=10, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # 【新增】清除已完成按钮
        self.clear_btn = ttk.Button(btn_frame, text="🗑️ 清除已完成", command=self._clear_completed, width=12)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        # 【新增】查看分P按钮  
        self.parts_btn = ttk.Button(btn_frame, text="📑 查看分P", command=self._show_parts, width=10)
        self.parts_btn.pack(side=tk.LEFT, padx=5)

        # 【新增】查看合集按钮
        self.collection_btn = ttk.Button(btn_frame, text="📚 查看合集", command=self._show_collection, width=10)
        self.collection_btn.pack(side=tk.LEFT, padx=5)
        
        # ===== 下半部分：任务队列 =====
        bottom_frame = ttk.Frame(paned)
        paned.add(bottom_frame, weight=2)
        
        # 【新增】任务队列标签
        queue_label_frame = ttk.Frame(bottom_frame)
        queue_label_frame.pack(fill=tk.X)
        
        ttk.Label(queue_label_frame, text="📋 下载队列:").pack(side=tk.LEFT)
        
        # 【新增】队列统计
        self.stats_var = tk.StringVar(value="等待: 0 | 下载中: 0 | 完成: 0 | 失败: 0")
        ttk.Label(queue_label_frame, textvariable=self.stats_var).pack(side=tk.RIGHT)
        
        # 【新增】任务列表 Treeview
        tree_frame = ttk.Frame(bottom_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        columns = ("title", "status", "progress", "url")
        self.task_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)
        
        # 设置列
        self.task_tree.heading("title", text="标题")
        self.task_tree.heading("status", text="状态")
        self.task_tree.heading("progress", text="进度")
        self.task_tree.heading("url", text="链接")
        
        self.task_tree.column("title", width=250, minwidth=100)
        self.task_tree.column("status", width=80, minwidth=60)
        self.task_tree.column("progress", width=80, minwidth=60)
        self.task_tree.column("url", width=300, minwidth=100)
        
        # 滚动条
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.task_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 【新增】右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="删除选中任务", command=self._remove_selected)
        self.context_menu.add_command(label="复制链接", command=self._copy_url)
        self.task_tree.bind("<Button-3>", self._show_context_menu)
        
        # ===== 进度和状态 =====
        status_frame = ttk.Frame(bottom_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        # 【修改】总体进度条
        ttk.Label(status_frame, text="总进度:").pack(side=tk.LEFT)
        self.total_progress_var = tk.DoubleVar(value=0)
        self.total_progress_bar = ttk.Progressbar(status_frame, variable=self.total_progress_var, maximum=100, length=200)
        self.total_progress_bar.pack(side=tk.LEFT, padx=10)
        
        # 当前任务进度
        ttk.Label(status_frame, text="当前:").pack(side=tk.LEFT, padx=(20, 0))
        self.current_progress_var = tk.DoubleVar(value=0)
        self.current_progress_bar = ttk.Progressbar(status_frame, variable=self.current_progress_var, maximum=100, length=200)
        self.current_progress_bar.pack(side=tk.LEFT, padx=10)
        
        # 状态
        self.status_var = tk.StringVar(value="✨ 准备就绪，请添加下载任务")
        ttk.Label(bottom_frame, textvariable=self.status_var, wraplength=700).pack(anchor=tk.W, pady=5)
        
        # 【新增】Cookies 设置区域
        cookie_frame = ttk.LabelFrame(settings_frame, text="🍪 Cookies 设置（可选，用于高画质/会员视频）", padding=5)
        cookie_frame.pack(fill=tk.X, pady=(10, 0))
        
        cookie_input_frame = ttk.Frame(cookie_frame)
        cookie_input_frame.pack(fill=tk.X)
        
        # Cookies 来源选择
        self.cookie_source = tk.StringVar(value="none")
        
        ttk.Radiobutton(
            cookie_input_frame, 
            text="不使用", 
            value="none", 
            variable=self.cookie_source,
            command=self._on_cookie_source_change
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            cookie_input_frame, 
            text="从浏览器获取", 
            value="browser", 
            variable=self.cookie_source,
            command=self._on_cookie_source_change
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            cookie_input_frame, 
            text="从文件读取", 
            value="file", 
            variable=self.cookie_source,
            command=self._on_cookie_source_change
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            cookie_input_frame, 
            text="手动输入", 
            value="manual", 
            variable=self.cookie_source,
            command=self._on_cookie_source_change
        ).pack(side=tk.LEFT, padx=5)
        
        # 浏览器选择（从浏览器获取时显示）
        self.browser_frame = ttk.Frame(cookie_frame)
        
        ttk.Label(self.browser_frame, text="选择浏览器:").pack(side=tk.LEFT, padx=5)
        self.browser_var = tk.StringVar(value="chrome")
        browsers = [("Chrome", "chrome"), ("Edge", "edge"), ("Firefox", "firefox"), ("Safari", "safari")]
        for text, value in browsers:
            ttk.Radiobutton(self.browser_frame, text=text, value=value, variable=self.browser_var).pack(side=tk.LEFT, padx=3)
        
        # 文件选择（从文件读取时显示）
        self.file_frame = ttk.Frame(cookie_frame)
        
        ttk.Label(self.file_frame, text="Cookies文件:").pack(side=tk.LEFT, padx=5)
        self.cookie_file_var = tk.StringVar()
        ttk.Entry(self.file_frame, textvariable=self.cookie_file_var, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.file_frame, text="浏览", command=self._browse_cookie_file, width=6).pack(side=tk.LEFT)
        
        # 手动输入（手动输入时显示）
        self.manual_frame = ttk.Frame(cookie_frame)
        
        ttk.Label(self.manual_frame, text="Cookie值:").pack(anchor=tk.W, padx=5)
        self.cookie_text = tk.Text(self.manual_frame, height=2, width=60)
        self.cookie_text.pack(fill=tk.X, padx=5, pady=2)
        
        # 帮助提示
        self.cookie_help = ttk.Label(
            cookie_frame, 
            text="💡 提示: 从浏览器获取是最简单的方式，需要先在浏览器中登录B站",
            foreground="gray"
        )
        self.cookie_help.pack(anchor=tk.W, padx=5, pady=5)


        # 日志区域
        log_frame = ttk.LabelFrame(bottom_frame, text="📝 下载日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_frame, height=4, state=tk.DISABLED, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # 【新增】==================== 批量操作方法 ====================
    
    def _clear_urls(self):
        """清空URL输入框"""
        self.url_text.delete("1.0", tk.END)
    
    def _paste_urls(self):
        """从剪贴板粘贴URL"""
        try:
            clipboard = self.root.clipboard_get()
            self.url_text.insert(tk.END, clipboard)
        except:
            pass
    
    def _add_to_queue(self):
        """添加URL到下载队列"""
        text = self.url_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("提示", "请输入至少一个视频链接")
            return
        
        # 分割URL
        urls = [line.strip() for line in text.split('\n') if line.strip()]
        
        # 过滤有效URL
        valid_urls = []
        invalid_count = 0
        for url in urls:
            if url.startswith(('http://', 'https://')):
                valid_urls.append(url)
            else:
                invalid_count += 1
        
        if not valid_urls:
            messagebox.showwarning("提示", "没有有效的视频链接\n链接需以 http:// 或 https:// 开头")
            return
        
        # 添加任务
        mode = self.mode_var.get()
        tasks = self.download_manager.add_tasks(valid_urls, mode)
        
        # 添加到树形列表
        for task in tasks:
            tree_id = self.task_tree.insert("", tk.END, values=(
                task.title,
                task.status,
                f"{task.progress}%",
                task.url
            ))
            task.tree_id = tree_id
        
        # 清空输入框
        self.url_text.delete("1.0", tk.END)
        
        # 更新统计
        self._update_stats()
        
        # 提示
        msg = f"已添加 {len(valid_urls)} 个任务到队列"
        if invalid_count > 0:
            msg += f"\n（忽略了 {invalid_count} 个无效链接）"
        self._log(f"➕ {msg}")
        self.status_var.set(msg)
    
    def _start_download(self):
        """开始下载队列"""
        if self.download_manager.task_queue.empty():
            messagebox.showwarning("提示", "下载队列为空，请先添加任务")
            return
        
        self.download_manager.start()
        self._update_button_states(downloading=True)
        self.status_var.set("🚀 开始下载...")
        self._log("▶️ 开始下载队列")
    
    def _toggle_pause(self):
        """切换暂停/继续"""
        if self.download_manager.is_paused:
            self.download_manager.resume()
            self.pause_btn.config(text="⏸️ 暂停")
            self.status_var.set("▶️ 继续下载...")
            self._log("▶️ 继续下载")
        else:
            self.download_manager.pause()
            self.pause_btn.config(text="▶️ 继续")
            self.status_var.set("⏸️ 已暂停")
            self._log("⏸️ 暂停下载")
    
    def _skip_current(self):
        """跳过当前任务"""
        if self.download_manager.current_task:
            self.download_manager.cancel_current_task()
            self._log("⏭️ 跳过当前任务")
    
    def _clear_completed(self):
        """清除已完成的任务"""
        # 从Treeview中删除
        for task in self.download_manager.tasks[:]:
            if task.status in (DownloadTask.STATUS_COMPLETED, DownloadTask.STATUS_FAILED, DownloadTask.STATUS_CANCELLED):
                if task.tree_id:
                    try:
                        self.task_tree.delete(task.tree_id)
                    except:
                        pass
        
        # 从管理器中清除
        self.download_manager.clear_completed()
        self._update_stats()
        self._log("🗑️ 已清除完成的任务")
    
    def _remove_selected(self):
        """删除选中的任务"""
        selected = self.task_tree.selection()
        if not selected:
            return
        
        for item in selected:
            # 查找对应的任务
            for task in self.download_manager.tasks:
                if task.tree_id == item:
                    # 不能删除正在下载的任务
                    if task.status == DownloadTask.STATUS_DOWNLOADING:
                        messagebox.showwarning("提示", "无法删除正在下载的任务")
                        continue
                    
                    # 从列表中移除
                    self.download_manager.tasks.remove(task)
                    break
            
            self.task_tree.delete(item)
        
        self._update_stats()
    
    def _copy_url(self):
        """复制选中任务的URL"""
        selected = self.task_tree.selection()
        if selected:
            item = selected[0]
            url = self.task_tree.item(item, "values")[3]
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
    
    def _show_context_menu(self, event):
        """显示右键菜单"""
        item = self.task_tree.identify_row(event.y)
        if item:
            self.task_tree.selection_set(item)
            self.context_menu.tk_popup(event.x_root, event.y_root)
    
    def _update_task_ui(self, task):
        """更新任务在UI中的显示"""
        if task.tree_id:
            try:
                self.task_tree.item(task.tree_id, values=(
                    task.title[:40] + "..." if len(task.title) > 40 else task.title,
                    task.status,
                    f"{task.progress}%",
                    task.url
                ))
            except:
                pass
        
        self._update_stats()
        
        # 更新当前进度条
        if task.status == DownloadTask.STATUS_DOWNLOADING:
            self.current_progress_var.set(task.progress)
    
    def _update_stats(self):
        """更新统计信息"""
        waiting = sum(1 for t in self.download_manager.tasks if t.status == DownloadTask.STATUS_WAITING)
        downloading = sum(1 for t in self.download_manager.tasks if t.status == DownloadTask.STATUS_DOWNLOADING)
        completed = sum(1 for t in self.download_manager.tasks if t.status == DownloadTask.STATUS_COMPLETED)
        failed = sum(1 for t in self.download_manager.tasks if t.status in (DownloadTask.STATUS_FAILED, DownloadTask.STATUS_CANCELLED))
        
        self.stats_var.set(f"等待: {waiting} | 下载中: {downloading} | 完成: {completed} | 失败: {failed}")
        
        # 更新总进度
        total = len(self.download_manager.tasks)
        if total > 0:
            done = completed + failed
            self.total_progress_var.set(done * 100 / total)
    
    def _update_button_states(self, downloading=False):
        """更新按钮状态"""
        if downloading:
            self.start_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.NORMAL)
            self.cancel_btn.config(state=tk.NORMAL)
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.DISABLED, text="⏸️ 暂停")
            self.cancel_btn.config(state=tk.DISABLED)
    
    def _on_all_completed(self):
        """所有任务完成回调"""
        self._update_button_states(downloading=False)
        self.current_progress_var.set(0)
        
        completed = sum(1 for t in self.download_manager.tasks if t.status == DownloadTask.STATUS_COMPLETED)
        failed = sum(1 for t in self.download_manager.tasks if t.status in (DownloadTask.STATUS_FAILED, DownloadTask.STATUS_CANCELLED))
        
        self.status_var.set(f"✅ 全部完成！成功: {completed}, 失败: {failed}")
        self._log(f"🎉 下载队列完成！成功: {completed}, 失败: {failed}")
        
        if completed > 0:
            if messagebox.askyesno("下载完成", f"成功下载 {completed} 个视频\n\n是否打开下载目录?"):
                self._open_download_folder()

    # 【新增】==================== 查看分P功能 ====================
    
    def _show_parts(self):
        """查看视频分P信息"""
        # 获取输入的第一个URL
        text = self.url_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("提示", "请先输入视频链接")
            return
        
        # 取第一行URL
        url = text.split('\n')[0].strip()
        if not url.startswith(('http://', 'https://')):
            messagebox.showwarning("提示", "请输入有效的视频链接")
            return
        
        # 显示加载中
        self.status_var.set("🔍 正在获取分P信息...")
        self.parts_btn.config(state=tk.DISABLED)
        
        # 在新线程中获取
        threading.Thread(target=self._fetch_parts, args=(url,), daemon=True).start()
    
    def _fetch_parts(self, url):
        """获取分P信息（子线程）"""
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                info = ydl.extract_info(url, download=False)
            
            # 检查是否有分P（entries）
            entries = info.get('entries', None)
            
            # 【新增】添加Cookie配置
            cookie_opts = self._get_cookie_opts()
            ydl_opts.update(cookie_opts)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            
            if entries:
                # 播放列表/分P视频
                parts = []
                for i, entry in enumerate(entries):
                    parts.append({
                        'index': i + 1,
                        'title': entry.get('title', f'P{i+1}'),
                        'url': entry.get('url') or entry.get('webpage_url') or f"{url}?p={i+1}",
                        'duration': entry.get('duration', 0)
                    })
                self.root.after(0, lambda: self._show_parts_window(parts, info.get('title', '视频')))
            else:
                # 检查B站分P格式
                pages = info.get('pages', None)
                if pages and len(pages) > 1:
                    parts = []
                    bvid = info.get('id', '')
                    for page in pages:
                        parts.append({
                            'index': page.get('page', page.get('index', 0)),
                            'title': page.get('part', page.get('title', f"P{page.get('page', '')}")),
                            'url': f"https://www.bilibili.com/video/{bvid}?p={page.get('page', 1)}",
                            'duration': page.get('duration', 0)
                        })
                    self.root.after(0, lambda: self._show_parts_window(parts, info.get('title', '视频')))
                else:
                    self.root.after(0, lambda: self._no_parts_found())
                    
        except Exception as e:
            self.root.after(0, lambda: self._parts_error(str(e)))
    
    def _show_parts_window(self, parts, video_title):
        """显示分P选择窗口"""
        self.parts_btn.config(state=tk.NORMAL)
        self.status_var.set(f"✨ 找到 {len(parts)} 个分P")
        
        # 创建分P选择窗口
        parts_win = tk.Toplevel(self.root)
        parts_win.title(f"选择分P - {video_title[:30]}")
        parts_win.geometry("550x450")
        parts_win.transient(self.root)
        parts_win.grab_set()
        
        # 主框架
        main_frame = ttk.Frame(parts_win, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text=f"📺 {video_title}", font=("", 11, "bold"))
        title_label.pack(anchor=tk.W, pady=(0, 10))
        
        # 操作按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        def select_all():
            for item in tree.get_children():
                tree.selection_add(item)
        
        def deselect_all():
            tree.selection_remove(tree.selection())
        
        ttk.Button(btn_frame, text="全选", command=select_all, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消全选", command=deselect_all, width=10).pack(side=tk.LEFT, padx=5)
        
        mode_label = ttk.Label(btn_frame, text=f"当前模式: {self._get_mode_display()}")
        mode_label.pack(side=tk.RIGHT, padx=5)
        
        # 分P列表
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("index", "title", "duration")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode=tk.EXTENDED)
        
        tree.heading("index", text="序号")
        tree.heading("title", text="标题")
        tree.heading("duration", text="时长")
        
        tree.column("index", width=50, anchor=tk.CENTER)
        tree.column("title", width=350)
        tree.column("duration", width=80, anchor=tk.CENTER)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 填充数据
        part_data = {}  # 存储分P数据
        for part in parts:
            duration = part['duration']
            if duration:
                mins, secs = divmod(int(duration), 60)
                duration_str = f"{mins}:{secs:02d}"
            else:
                duration_str = "-"
            
            item_id = tree.insert("", tk.END, values=(
                f"P{part['index']}",
                part['title'],
                duration_str
            ))
            part_data[item_id] = part
        
        # 添加下载按钮
        def add_selected_to_queue():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("提示", "请选择要下载的分P", parent=parts_win)
                return
            
            mode = self.mode_var.get()
            added_count = 0
            
            for item_id in selected:
                part = part_data[item_id]
                task = self.download_manager.add_task(part['url'], mode)
                
                # 设置标题
                task.title = f"P{part['index']}: {part['title']}"
                
                # 添加到树形列表
                tree_id = self.task_tree.insert("", tk.END, values=(
                    task.title[:40],
                    task.status,
                    f"{task.progress}%",
                    task.url
                ))
                task.tree_id = tree_id
                added_count += 1
            
            self._update_stats()
            self._log(f"➕ 已添加 {added_count} 个分P到下载队列")
            parts_win.destroy()
            
            # 提示是否立即开始下载
            if messagebox.askyesno("添加成功", f"已添加 {added_count} 个分P\n\n是否立即开始下载?"):
                self._start_download()
        
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            bottom_frame, 
            text="📥 添加选中到下载队列", 
            command=add_selected_to_queue,
            width=25
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            bottom_frame, 
            text="取消", 
            command=parts_win.destroy,
            width=10
        ).pack(side=tk.RIGHT, padx=5)
    
    def _no_parts_found(self):
        """没有找到分P"""
        self.parts_btn.config(state=tk.NORMAL)
        self.status_var.set("✨ 准备就绪")
        messagebox.showinfo("提示", "该视频没有分P，可以直接添加到下载队列")
    
    def _parts_error(self, error):
        """获取分P出错"""
        self.parts_btn.config(state=tk.NORMAL)
        self.status_var.set("❌ 获取分P失败")
        messagebox.showerror("错误", f"获取分P信息失败:\n{error}")
    
    def _get_mode_display(self):
        """获取当前模式的显示文本"""
        mode_map = {
            "best": "最佳画质",
            "audio": "仅音频",
            "720": "720P",
            "480": "480P"
        }
        return mode_map.get(self.mode_var.get(), self.mode_var.get())
    
    # 【新增】==================== Cookies 功能 ====================
    
    def _on_cookie_source_change(self):
        """Cookie来源选项改变"""
        source = self.cookie_source.get()
        
        # 隐藏所有子框架
        self.browser_frame.pack_forget()
        self.file_frame.pack_forget()
        self.manual_frame.pack_forget()
        
        # 根据选择显示对应框架
        if source == "browser":
            self.browser_frame.pack(fill=tk.X, pady=5)
            self.cookie_help.config(text="💡 将自动从选择的浏览器中读取已登录的B站Cookies")
        elif source == "file":
            self.file_frame.pack(fill=tk.X, pady=5)
            self.cookie_help.config(text="💡 支持 Netscape 格式的 cookies.txt 文件")
        elif source == "manual":
            self.manual_frame.pack(fill=tk.X, pady=5)
            self.cookie_help.config(text="💡 在浏览器中按F12，找到请求头中的Cookie值并粘贴")
        else:
            self.cookie_help.config(text="💡 不使用Cookies，只能下载免费视频的普通画质")
    
    def _browse_cookie_file(self):
        """选择Cookie文件"""
        file_path = filedialog.askopenfilename(
            title="选择Cookies文件",
            filetypes=[
                ("Cookie文件", "*.txt"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            self.cookie_file_var.set(file_path)
    
    def _get_cookie_opts(self):
        """获取Cookie相关的yt-dlp配置"""
        source = self.cookie_source.get()
        opts = {}
        
        if source == "browser":
            # 从浏览器获取
            browser = self.browser_var.get()
            opts['cookiesfrombrowser'] = (browser,)
            
        elif source == "file":
            # 从文件读取
            cookie_file = self.cookie_file_var.get().strip()
            if cookie_file and os.path.exists(cookie_file):
                opts['cookiefile'] = cookie_file
            else:
                self._log("⚠️ Cookie文件不存在，将不使用Cookies")
                
        elif source == "manual":
            # 手动输入 - 需要创建临时cookie文件
            cookie_text = self.cookie_text.get("1.0", tk.END).strip()
            if cookie_text:
                opts['http_headers'] = {'Cookie': cookie_text}
        
        return opts
    # 【新增】==================== Cookies 功能 ====================
    
    def _on_cookie_source_change(self):
        """Cookie来源选项改变"""
        source = self.cookie_source.get()
        
        # 隐藏所有子框架
        self.browser_frame.pack_forget()
        self.file_frame.pack_forget()
        self.manual_frame.pack_forget()
        
        # 根据选择显示对应框架
        if source == "browser":
            self.browser_frame.pack(fill=tk.X, pady=5)
            self.cookie_help.config(text="💡 将自动从选择的浏览器中读取已登录的B站Cookies")
        elif source == "file":
            self.file_frame.pack(fill=tk.X, pady=5)
            self.cookie_help.config(text="💡 支持 Netscape 格式的 cookies.txt 文件")
        elif source == "manual":
            self.manual_frame.pack(fill=tk.X, pady=5)
            self.cookie_help.config(text="💡 在浏览器中按F12，找到请求头中的Cookie值并粘贴")
        else:
            self.cookie_help.config(text="💡 不使用Cookies，只能下载免费视频的普通画质")
    
    def _browse_cookie_file(self):
        """选择Cookie文件"""
        file_path = filedialog.askopenfilename(
            title="选择Cookies文件",
            filetypes=[
                ("Cookie文件", "*.txt"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            self.cookie_file_var.set(file_path)
    
    def _get_cookie_opts(self):
        """获取Cookie相关的yt-dlp配置"""
        source = self.cookie_source.get()
        opts = {}
        
        if source == "browser":
            # 从浏览器获取
            browser = self.browser_var.get()
            opts['cookiesfrombrowser'] = (browser,)
            
        elif source == "file":
            # 从文件读取
            cookie_file = self.cookie_file_var.get().strip()
            if cookie_file and os.path.exists(cookie_file):
                opts['cookiefile'] = cookie_file
            else:
                self._log("⚠️ Cookie文件不存在，将不使用Cookies")
                
        elif source == "manual":
            # 手动输入 - 需要创建临时cookie文件
            cookie_text = self.cookie_text.get("1.0", tk.END).strip()
            if cookie_text:
                opts['http_headers'] = {'Cookie': cookie_text}
        
        return opts
    
     # 【新增】==================== 查看合集功能 ====================
    
    def _show_collection(self):
        """查看视频合集/播放列表"""
        text = self.url_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("提示", "请先输入视频链接")
            return
        
        url = text.split('\n')[0].strip()
        if not url.startswith(('http://', 'https://')):
            messagebox.showwarning("提示", "请输入有效的视频链接")
            return
        
        self.status_var.set("🔍 正在获取合集信息...")
        self.collection_btn.config(state=tk.DISABLED)
        
        threading.Thread(target=self._fetch_collection, args=(url,), daemon=True).start()
    
    def _fetch_collection(self, url):
        """获取合集信息（子线程）"""
        try:
            # 使用 extract_flat 快速获取列表信息
            ydl_opts = {
                'quiet': True,
                'extract_flat': 'in_playlist',  # 只提取列表，不下载详情
                'ignoreerrors': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            
            if not info:
                self.root.after(0, lambda: self._collection_error("无法获取视频信息"))
                return
            
            videos = []
            collection_title = info.get('title', '合集')
            
            # 情况1: 有 entries（播放列表/合集）
            if 'entries' in info and info['entries']:
                entries = list(info['entries'])  # 转为列表
                for i, entry in enumerate(entries):
                    if entry:  # 可能有None
                        videos.append({
                            'index': i + 1,
                            'title': entry.get('title', f'视频{i+1}'),
                            'url': entry.get('url') or entry.get('webpage_url', ''),
                            'duration': entry.get('duration', 0),
                            'id': entry.get('id', ''),
                            'uploader': entry.get('uploader', ''),
                        })
            
            # 情况2: B站视频合集（在 related videos 或其他字段中）
            # 尝试从页面获取更多信息
            if not videos:
                # 尝试获取完整信息
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    full_info = ydl.extract_info(url, download=False)
                
                # 检查是否有合集信息
                if full_info:
                    # B站 ugc_season（合集）
                    ugc_season = full_info.get('ugc_season', {})
                    if ugc_season:
                        sections = ugc_season.get('sections', [])
                        for section in sections:
                            episodes = section.get('episodes', [])
                            for ep in episodes:
                                videos.append({
                                    'index': len(videos) + 1,
                                    'title': ep.get('title', ''),
                                    'url': f"https://www.bilibili.com/video/{ep.get('bvid', '')}",
                                    'duration': ep.get('arc', {}).get('duration', 0),
                                    'id': ep.get('bvid', ''),
                                    'uploader': '',
                                })
                        collection_title = ugc_season.get('title', collection_title)
                    
                    # 检查 pages（分P视频，提示用户使用分P功能）
                    pages = full_info.get('pages', [])
                    if pages and len(pages) > 1 and not videos:
                        self.root.after(0, lambda: self._suggest_use_parts())
                        return
            
            if videos:
                self.root.after(0, lambda: self._show_collection_window(videos, collection_title))
            else:
                self.root.after(0, lambda: self._no_collection_found())
                
        except Exception as e:
            self.root.after(0, lambda: self._collection_error(str(e)))
    
    def _show_collection_window(self, videos, collection_title):
        """显示合集选择窗口"""
        self.collection_btn.config(state=tk.NORMAL)
        self.status_var.set(f"✨ 找到 {len(videos)} 个视频")
        
        # 创建窗口
        win = tk.Toplevel(self.root)
        win.title(f"选择视频 - {collection_title[:40]}")
        win.geometry("650x500")
        win.transient(self.root)
        win.grab_set()
        
        main_frame = ttk.Frame(win, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题和统计
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text=f"📚 {collection_title}", font=("", 11, "bold")).pack(side=tk.LEFT)
        ttk.Label(header_frame, text=f"共 {len(videos)} 个视频").pack(side=tk.RIGHT)
        
        # 操作按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        def select_all():
            for item in tree.get_children():
                tree.selection_add(item)
        
        def deselect_all():
            tree.selection_remove(tree.selection())
        
        def select_range():
            """选择范围"""
            range_win = tk.Toplevel(win)
            range_win.title("选择范围")
            range_win.geometry("250x120")
            range_win.transient(win)
            range_win.grab_set()
            
            ttk.Label(range_win, text="从第").pack(side=tk.LEFT, padx=5, pady=20)
            start_var = tk.StringVar(value="1")
            ttk.Entry(range_win, textvariable=start_var, width=5).pack(side=tk.LEFT)
            
            ttk.Label(range_win, text="到第").pack(side=tk.LEFT, padx=5)
            end_var = tk.StringVar(value=str(len(videos)))
            ttk.Entry(range_win, textvariable=end_var, width=5).pack(side=tk.LEFT)
            
            ttk.Label(range_win, text="个").pack(side=tk.LEFT, padx=5)
            
            def apply_range():
                try:
                    start = int(start_var.get()) - 1
                    end = int(end_var.get())
                    items = tree.get_children()
                    deselect_all()
                    for i in range(max(0, start), min(len(items), end)):
                        tree.selection_add(items[i])
                    range_win.destroy()
                except ValueError:
                    messagebox.showwarning("提示", "请输入有效数字", parent=range_win)
            
            ttk.Button(range_win, text="确定", command=apply_range).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(btn_frame, text="全选", command=select_all, width=8).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="取消全选", command=deselect_all, width=10).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="选择范围", command=select_range, width=10).pack(side=tk.LEFT, padx=3)
        
        ttk.Label(btn_frame, text=f"模式: {self._get_mode_display()}").pack(side=tk.RIGHT)
        
        # 视频列表
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("index", "title", "duration", "id")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode=tk.EXTENDED)
        
        tree.heading("index", text="#")
        tree.heading("title", text="标题")
        tree.heading("duration", text="时长")
        tree.heading("id", text="BV号")
        
        tree.column("index", width=40, anchor=tk.CENTER)
        tree.column("title", width=350)
        tree.column("duration", width=70, anchor=tk.CENTER)
        tree.column("id", width=120)
        
        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 填充数据
        video_data = {}
        for video in videos:
            duration = video['duration']
            if duration:
                mins, secs = divmod(int(duration), 60)
                hours, mins = divmod(mins, 60)
                if hours > 0:
                    duration_str = f"{hours}:{mins:02d}:{secs:02d}"
                else:
                    duration_str = f"{mins}:{secs:02d}"
            else:
                duration_str = "-"
            
            item_id = tree.insert("", tk.END, values=(
                video['index'],
                video['title'][:50],
                duration_str,
                video['id']
            ))
            video_data[item_id] = video
        
        # 底部按钮
        def add_selected():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("提示", "请选择要下载的视频", parent=win)
                return
            
            mode = self.mode_var.get()
            added = 0
            
            for item_id in selected:
                video = video_data[item_id]
                if not video['url']:
                    continue
                
                task = self.download_manager.add_task(video['url'], mode)
                task.title = video['title']
                
                tree_id = self.task_tree.insert("", tk.END, values=(
                    task.title[:40],
                    task.status,
                    f"{task.progress}%",
                    task.url
                ))
                task.tree_id = tree_id
                added += 1
            
            self._update_stats()
            self._log(f"➕ 已添加 {added} 个视频到下载队列")
            win.destroy()
            
            if added > 0 and messagebox.askyesno("添加成功", f"已添加 {added} 个视频\n\n是否立即开始下载?"):
                self._start_download()
        
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=10)
        
        # 显示选中数量
        selected_label = ttk.Label(bottom_frame, text="已选择: 0 个")
        selected_label.pack(side=tk.LEFT)
        
        def update_selected_count(event=None):
            count = len(tree.selection())
            selected_label.config(text=f"已选择: {count} 个")
        
        tree.bind("<<TreeviewSelect>>", update_selected_count)
        
        ttk.Button(bottom_frame, text="📥 添加到下载队列", command=add_selected, width=20).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="取消", command=win.destroy, width=10).pack(side=tk.RIGHT, padx=5)
    
    def _no_collection_found(self):
        """没有找到合集"""
        self.collection_btn.config(state=tk.NORMAL)
        self.status_var.set("✨ 准备就绪")
        messagebox.showinfo("提示", "该链接没有找到合集/播放列表\n\n如果是分P视频，请使用「查看分P」功能")
    
    def _suggest_use_parts(self):
        """建议使用分P功能"""
        self.collection_btn.config(state=tk.NORMAL)
        self.status_var.set("✨ 准备就绪")
        messagebox.showinfo("提示", "检测到这是一个分P视频\n\n请使用「查看分P」功能来选择要下载的部分")
    
    def _collection_error(self, error):
        """获取合集出错"""
        self.collection_btn.config(state=tk.NORMAL)
        self.status_var.set("❌ 获取合集失败")
        messagebox.showerror("错误", f"获取合集信息失败:\n{error}")

    
    # ==================== 原有方法（部分修改） ====================
    
    def _browse_path(self):
        """选择保存路径"""
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            self.path_var.set(path)
    
    def _open_download_folder(self):
        """打开下载文件夹"""
        path = self.path_var.get()
        if os.path.exists(path):
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        else:
            messagebox.showwarning("提示", "目录不存在")
    
    def _log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    # 【修改】获取yt-dlp配置 - 添加task参数
    def _get_ydl_opts(self, task):
        """获取 yt-dlp 配置"""
        mode = task.mode
        save_path = self.path_var.get()
        
        os.makedirs(save_path, exist_ok=True)
        
        # 【新增】进度回调绑定到具体任务
        def progress_hook(d):
            if d['status'] == 'downloading':
                percent_str = d.get('_percent_str', '0%').strip().replace('%', '')
                try:
                    percent = float(percent_str)
                    task.progress = int(percent)
                    
                    speed = d.get('_speed_str', 'N/A')
                    eta = d.get('_eta_str', 'N/A')
                    
                    self.root.after(0, lambda: self._update_task_ui(task))
                    self.root.after(0, lambda: self.status_var.set(
                        f"⬇️ {task.title[:30]}... | {percent:.1f}% | 速度: {speed}"
                    ))
                except ValueError:
                    pass
            elif d['status'] == 'finished':
                task.progress = 100
                self.root.after(0, lambda: self._update_task_ui(task))
        
        opts = {
            'paths': {'home': save_path},
            'outtmpl': '%(title)s.%(ext)s',
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }
        # 【新增】添加 Cookie 配置
        cookie_opts = self._get_cookie_opts()
        opts.update(cookie_opts)
        
        # 格式选择
        if mode == "audio":
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]
        elif mode == "720":
            opts['format'] = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
        elif mode == "480":
            opts['format'] = 'bestvideo[height<=480]+bestaudio/best[height<=480]/best'
        else:  # best
            opts['format'] = 'bestvideo+bestaudio/best'
        
        return opts
    
    def run(self):
        """运行应用"""
        print("启动主循环...")
        self.root.mainloop()


# ============ 程序入口 ============
if __name__ == "__main__":
    print("=" * 50)
    print("B站视频下载器 - 批量版 启动中...")
    print("=" * 50)
    
    try:
        app = BiliDownloader()
        app.run()
    except Exception as e:
        print(f"程序出错: {e}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")