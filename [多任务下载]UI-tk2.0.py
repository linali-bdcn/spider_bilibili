import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import time
import requests
import re
import os
import subprocess
import webbrowser
import json
from get_url1 import BilibiliDownloader

# -------------------- 全局配置 --------------------
DEFAULT_DOWNLOAD_PATH = r"D:"
CONFIG_FILE = "config.json"
APP_TITLE = "B站视频下载器"
APP_GEOMETRY = "800x500"
VERSION = "1.0.0"
FFMPEG_DOWNLOAD_URL = "https://ffmpeg.org/download.html"
FFMPEG_INSTALL_HELP = (
    "1. 从官网下载FFmpeg\n"
    "2. 解压到任意文件夹\n"
    "3. 将FFmpeg的bin目录添加到系统环境变量PATH中\n"
    "4. 重启应用程序\n\n"
    "详细教程可在网上搜索'FFmpeg安装教程'"
)
DEFAULT_COOKIE = ""

# -------------------- 辅助函数 --------------------
def check_ffmpeg_installed():
    """检查FFmpeg是否已安装"""
    try:
        process = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def open_url(url):
    """打开指定URL"""
    webbrowser.open(url)

def show_message(title, message, parent=None):
    """显示普通信息弹窗"""
    messagebox.showinfo(title, message, parent=parent)

def show_warning(title, message, parent=None):
    """显示警告信息弹窗"""
    messagebox.showwarning(title, message, parent=parent)

def show_error(title, message, parent=None):
    """显示错误信息弹窗"""
    messagebox.showerror(title, message, parent=parent)

def ask_yesno(title, message, parent=None):
    """显示是/否询问弹窗"""
    return messagebox.askyesno(title, message, parent=parent)

def truncate_string(text, max_len=40):
    """截断字符串并添加省略号"""
    return (text[:max_len] + "...") if len(text) > max_len else text

def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE)
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"加载配置文件出错: {e}")
    return config.get("cookie", DEFAULT_COOKIE), config.get("download_path", DEFAULT_DOWNLOAD_PATH)

def save_config(cookie, download_path):
    """保存配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE)
    config = {"cookie": cookie, "download_path": download_path}
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"保存配置文件出错: {e}")

def get_download_mode_display(mode, mode_options):
    """获取下载模式的显示文本"""
    for text, value in mode_options:
        if value == mode:
            return text
    return mode

# -------------------- 主应用程序类 --------------------
class BiliDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(APP_GEOMETRY)

        self.cookie, self.download_path = load_config()

        self.download_queue = []
        self.is_downloading = False
        self.current_task_id = None
        self.download_mode = tk.StringVar(value="audio_only")
        self.mode_options = [
            ("仅音频", "audio_only"),
            ("仅视频", "video_only"),
            ("音视频分离", "separate"),
            ("音视频合并", "merged")
        ]

        self._create_widgets()
        self._check_ffmpeg_on_start()
        self._setup_drag_and_drop()
        self._apply_theme("light") # 默认主题
        self._update_ui_status()

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_widgets(self):
        # 创建菜单栏
        self._create_menu()

        # 创建左右分栏
        left_frame = tk.Frame(self.root, width=300)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)

        right_frame = tk.Frame(self.root, width=500)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._create_left_panel(left_frame)
        self._create_right_panel(right_frame)

    def _create_menu(self):
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        # 文件菜单
        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="添加下载任务", command=self._add_download_tasks)
        file_menu.add_command(label="查看分P信息", command=self._show_selected_parts_info)
        file_menu.add_separator()
        file_menu.add_command(label="设置", command=self._open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        # 操作菜单
        action_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="操作", menu=action_menu)
        action_menu.add_command(label="暂停/继续下载", command=self._pause_resume_download)
        action_menu.add_command(label="清除已完成任务", command=self._clear_completed_tasks)
        action_menu.add_command(label="删除选中任务", command=self._remove_selected_task)

        # 帮助菜单
        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=lambda: show_message("使用说明",
                                                                                "1. 输入B站视频URL\n"
                                                                                "2. 选择下载模式\n"
                                                                                "3. 点击'添加下载任务'或'查看分P信息'\n"
                                                                                "4. 等待下载完成\n\n"
                                                                                "注意: 音视频合并模式需要安装FFmpeg"))
        help_menu.add_command(label="检查更新", command=self._check_updates)
        help_menu.add_separator()
        help_menu.add_command(label="关于", command=lambda: show_message("关于",
                                                                            f"{APP_TITLE} v{VERSION}\n"
                                                                            "一个简单的B站视频下载工具\n"
                                                                            "© 2025 开发者保留所有权利"))

    def _create_left_panel(self, parent):
        # 输入区域
        input_label = tk.Label(parent, text="请输入B站视频URL(每行一个):", anchor="w")
        input_label.pack(pady=5, fill=tk.X)
        self.input_text = scrolledtext.ScrolledText(parent, width=35, height=10)
        self.input_text.pack(pady=5, fill=tk.BOTH, expand=True)

        # 下载模式选择
        mode_frame = tk.Frame(parent)
        mode_frame.pack(pady=5, fill=tk.X)
        mode_label = tk.Label(mode_frame, text="下载模式:", anchor="w")
        mode_label.pack(side=tk.LEFT, padx=5)

        radio_frame = tk.Frame(parent)
        radio_frame.pack(pady=5, fill=tk.X)
        for text, mode in self.mode_options:
            rb = tk.Radiobutton(radio_frame, text=text, variable=self.download_mode, value=mode, command=self._check_merged_mode_selection)
            rb.pack(side=tk.LEFT, padx=5)

        # FFmpeg状态显示
        self.ffmpeg_frame = tk.Frame(parent)
        self.ffmpeg_frame.pack(fill=tk.X, pady=5)
        self._update_ffmpeg_status_label()

        # 按钮区域
        button_frame = tk.Frame(parent)
        button_frame.pack(pady=10, fill=tk.X)
        start_button = tk.Button(button_frame, text="添加下载任务", command=self._add_download_tasks)
        start_button.pack(side=tk.LEFT, padx=5)
        info_button = tk.Button(button_frame, text="查看分P信息", command=self._show_selected_parts_info)
        info_button.pack(side=tk.LEFT, padx=5)
        self.pause_resume_button = tk.Button(button_frame, text="暂停下载", command=self._pause_resume_download)
        self.pause_resume_button.pack(side=tk.LEFT, padx=5)
        settings_button = tk.Button(parent, text="设置", command=self._open_settings, anchor="e")
        settings_button.pack(side=tk.BOTTOM, padx=5, pady=5, fill=tk.X)

        # 状态栏
        self.status_frame = tk.Frame(parent)
        self.status_frame.pack(fill=tk.X, pady=5)
        self.status_label = tk.Label(self.status_frame, text="状态: 就绪", anchor="w")
        self.status_label.pack(side=tk.LEFT, padx=5)

    def _update_ffmpeg_status_label(self):
        is_ffmpeg_installed = check_ffmpeg_installed()
        status_text = "已安装 ✓" if is_ffmpeg_installed else "未安装 ✗"
        status_color = "green" if is_ffmpeg_installed else "red"

        for widget in self.ffmpeg_frame.winfo_children():
            widget.destroy()

        ffmpeg_label = tk.Label(self.ffmpeg_frame, text=f"FFmpeg状态: {status_text}", fg=status_color, anchor="w")
        ffmpeg_label.pack(side=tk.LEFT, padx=5)

        if not is_ffmpeg_installed:
            download_link = tk.Label(self.ffmpeg_frame, text="点击下载FFmpeg", fg="blue", cursor="hand2")
            download_link.pack(side=tk.LEFT, padx=5)
            download_link.bind("<Button-1>", lambda e: open_url(FFMPEG_DOWNLOAD_URL))

            help_link = tk.Label(self.ffmpeg_frame, text="安装帮助", fg="blue", cursor="hand2")
            help_link.pack(side=tk.LEFT, padx=5)
            help_link.bind("<Button-1>", lambda e: show_message("FFmpeg安装帮助", FFMPEG_INSTALL_HELP, parent=self.root))

    def _check_merged_mode_selection(self):
        if self.download_mode.get() == "merged" and not check_ffmpeg_installed():
            show_warning(
                "FFmpeg未安装",
                "检测到您选择了音视频合并模式，但系统中未安装FFmpeg。\n\n"
                "请先安装FFmpeg，否则合并功能将无法使用。\n\n"
                "是否仍要继续使用此模式？",
                parent=self.root
            )

    def _create_right_panel(self, parent):
        # 任务列表
        task_label = tk.Label(parent, text="下载任务列表:", anchor="w")
        task_label.pack(pady=5, fill=tk.X)

        columns = ("url", "status", "progress")
        self.task_list = ttk.Treeview(parent, columns=columns, show="headings", height=15)
        self.task_list.heading("url", text="视频地址")
        self.task_list.heading("status", text="状态")
        self.task_list.heading("progress", text="进度")
        self.task_list.column("url", width=300)
        self.task_list.column("status", width=100)
        self.task_list.column("progress", width=100)
        self.task_list.pack(fill=tk.BOTH, expand=True, pady=5)
        self.task_list.bind("<Button-3>", self._show_context_menu)

        # 底部按钮
        right_button_frame = tk.Frame(parent)
        right_button_frame.pack(fill=tk.X, pady=5)
        clear_button = tk.Button(right_button_frame, text="清除已完成任务", command=self._clear_completed_tasks)
        clear_button.pack(side=tk.LEFT, padx=5)
        remove_button = tk.Button(right_button_frame, text="删除选中任务", command=self._remove_selected_task)
        remove_button.pack(side=tk.LEFT, padx=5)

    def _download_thread(self):
        while self.download_queue:
            task_id = self.download_queue.pop(0)
            self.current_task_id = task_id
            url = self.task_list.item(task_id, "values")[0]
            mode = self.download_mode.get()
            self._update_task_status(task_id, f"下载中({get_download_mode_display(mode, self.mode_options)})", "0%")

            try:
                downloader = BilibiliDownloader()
                downloader.set_progress_callback(lambda p: self._update_task_progress(task_id, p, mode))
                headers = {
                    "referer": "https://www.bilibili.com/",
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",

                }
                downloader.download_video_and_audio(url, headers, mode)
                self._update_task_status(task_id, f"已完成({get_download_mode_display(mode, self.mode_options)})", "100%")
            except Exception as e:
                error_msg = truncate_string(str(e))
                self._update_task_status(task_id, f"失败: {error_msg}", "")
                print(f"下载失败: {e}")
            finally:
                self.current_task_id = None
        self.is_downloading = False

    def _update_task_status(self, task_id, status, progress):
        self.task_list.item(task_id, values=(self.task_list.item(task_id, "values")[0], status, progress))
        self.root.update_idletasks()

    def _update_task_progress(self, task_id, percent, mode):
        self._update_task_status(task_id, f"下载中({get_download_mode_display(mode, self.mode_options)})", f"{percent}%")

    def _add_download_tasks(self):
        urls = [url.strip() for url in self.input_text.get("1.0", tk.END).strip().split("\n") if url.strip()]
        if not urls:
            show_message("提示", "请输入至少一个有效的视频URL")
            return

        current_mode = self.download_mode.get()
        if current_mode == "merged" and not check_ffmpeg_installed():
            if not ask_yesno(
                "警告",
                "您选择了音视频合并模式，但"
                "系统中未安装FFmpeg，合并功能将无法使用。\n\n"
                "是否继续添加下载任务？\n"
                "（建议切换到其他下载模式或安装FFmpeg后再尝试）",
                parent=self.root
            ):
                return

        for url in urls:
            task_id = self.task_list.insert("", tk.END,
                                               values=(url, f"等待中({get_download_mode_display(current_mode, self.mode_options)})", ""))
            self.download_queue.append(task_id)

        self.input_text.delete("1.0", tk.END)

        if not self.is_downloading:
            self.is_downloading = True
            threading.Thread(target=self._download_thread, daemon=True).start()

    def _clear_completed_tasks(self):
        for item in self.task_list.get_children():
            status = self.task_list.item(item, "values")[1]
            if status.startswith("已完成") or status.startswith("失败"):
                self.task_list.delete(item)

    def _show_parts_info(self, url):
        try:
            downloader = BilibiliDownloader()
            headers = {
                "referer": url,
                "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
            }
            downloader.headers = headers
            parts_info = downloader.get_p_total(url)

            if parts_info:
                parts_window = tk.Toplevel(self.root)
                parts_window.title("选择要下载的分P")
                parts_window.geometry("500x400")

                top_frame = tk.Frame(parts_window)
                top_frame.pack(fill=tk.X, padx=10, pady=5)

                checkboxes = []

                def select_all():
                    for var, _ in checkboxes:
                        var.set(True)

                def deselect_all():
                    for var, _ in checkboxes:
                        var.set(False)

                select_all_btn = tk.Button(top_frame, text="全选", command=select_all, width=10)
                select_all_btn.pack(side=tk.LEFT, padx=5)

                deselect_all_btn = tk.Button(top_frame, text="取消全选", command=deselect_all, width=10)
                deselect_all_btn.pack(side=tk.LEFT, padx=5)

                current_mode_label = tk.Label(top_frame, text=f"当前下载模式: {get_download_mode_display(self.download_mode.get(), self.mode_options)}")
                current_mode_label.pack(side=tk.RIGHT, padx=5)

                list_frame = tk.Frame(parts_window)
                list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

                scrollbar = tk.Scrollbar(list_frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

                text_widget = tk.Text(list_frame, yscrollcommand=scrollbar.set, wrap=tk.WORD)
                text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.config(command=text_widget.yview)
                text_widget.config(state=tk.DISABLED)

                for index, part_url, title in parts_info:
                    text_widget.config(state=tk.NORMAL)
                    var = tk.BooleanVar()
                    checkboxes.append((var, part_url))
                    frame = tk.Frame(text_widget)
                    cb = tk.Checkbutton(frame, text=f"P{index}: {title}", variable=var, anchor="w")
                    cb.pack(fill=tk.X, padx=5, pady=2)
                    text_widget.window_create(tk.END, window=frame)
                    text_widget.insert(tk.END, "\n")
                    text_widget.config(state=tk.DISABLED)

                def confirm_selection():
                    selected_urls = [url for var, url in checkboxes if var.get()]
                    if not selected_urls:
                        show_message("提示", "请至少选择一个分P", parent=parts_window)
                        return

                    current_mode = self.download_mode.get()
                    if current_mode == "merged" and not check_ffmpeg_installed():
                        if not ask_yesno(
                                "警告",
                                "您选择了音视频合并模式，但系统中未安装FFmpeg，合并功能将无法使用。\n\n"
                                "是否继续添加下载任务？\n"
                                "（建议切换到其他下载模式或安装FFmpeg后再尝试）",
                                parent=parts_window
                        ):
                            return

                    for sel_url in selected_urls:
                        task_id = self.task_list.insert("", tk.END,
                                                       values=(sel_url, f"等待中({get_download_mode_display(current_mode, self.mode_options)})", ""))
                        self.download_queue.append(task_id)

                    if not self.is_downloading:
                        self.is_downloading = True
                        threading.Thread(target=self._download_thread, daemon=True).start()

                    parts_window.destroy()

                bottom_frame = tk.Frame(parts_window)
                bottom_frame.pack(fill=tk.X, padx=10, pady=10)

                confirm_button = tk.Button(
                    bottom_frame,
                    text="确认下载",
                    command=confirm_selection,
                    height=2,
                    width=20,
                    font=("Arial", 11, "bold")
                )
                confirm_button.pack(pady=10, padx=10, fill=tk.X)

                def on_mousewheel(event):
                    text_widget.yview_scroll(int(-1 * (event.delta / 120)), "units")

                text_widget.bind("<MouseWheel>", on_mousewheel)
                text_widget.bind("<Button-4>", lambda e: text_widget.yview_scroll(-1, "units"))
                text_widget.bind("<Button-5>", lambda e: text_widget.yview_scroll(1, "units"))

            else:
                show_warning("错误", "无法获取视频分P信息")
        except Exception as e:
            show_error("错误", f"获取分P信息时出错: {str(e)}")

    def _show_selected_parts_info(self):
        selected_items = self.task_list.selection()
        if not selected_items:
            show_message("提示", "请先选择一个任务")
            return
        task_id = selected_items[0]
        url = self.task_list.item(task_id, "values")[0]
        self._show_parts_info(url)

    def _pause_resume_download(self):
        if self.is_downloading:
            self.is_downloading = False
            self.pause_resume_button.config(text="继续下载")
            self.status_label.config(text="状态: 已暂停")
        else:
            if self.download_queue:
                self.is_downloading = True
                threading.Thread(target=self._download_thread, daemon=True).start()
                self.pause_resume_button.config(text="暂停下载")
                self.status_label.config(text="状态: 下载中")
            else:
                show_message("提示", "没有等待中的下载任务")

    def _remove_selected_task(self):
        selected_items = self.task_list.selection()
        if not selected_items:
            show_message("提示", "请先选择要删除的任务")
            return

        for item in selected_items:
            if item == self.current_task_id:
                show_message("提示", "无法删除正在下载的任务")
                continue
            if item in self.download_queue:
                self.download_queue.remove(item)
            self.task_list.delete(item)

    def _open_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("设置")
        settings_window.geometry("400x300")
        settings_window.resizable(False, False)

        tab_control = ttk.Notebook(settings_window)

        # 常规设置选项卡
        general_tab = ttk.Frame(tab_control)
        tab_control.add(general_tab, text="常规设置")

        # Cookie设置
        cookie_frame = tk.Frame(general_tab)
        cookie_frame.pack(fill=tk.X, padx=10, pady=10)
        cookie_label = tk.Label(cookie_frame, text="Cookie设置:", anchor="w")
        cookie_label.pack(anchor="w")
        cookie_text = tk.Text(cookie_frame, height=5, width=40)
        cookie_text.pack(fill=tk.X, pady=5)
        cookie_text.insert(tk.END, self.cookie)
        cookie_help = tk.Label(cookie_frame, text="提示: 登录B站后，F12打开开发者工具，在Network中找到任意请求，复制Cookie值", fg="gray", anchor="w")
        cookie_help.pack(anchor="w")

        # 下载路径设置
        path_frame = tk.Frame(general_tab)
        path_frame.pack(fill=tk.X, padx=10, pady=10)
        path_label = tk.Label(path_frame, text="下载路径:", anchor="w")
        path_label.pack(side=tk.LEFT, padx=5)
        path_entry = tk.Entry(path_frame, width=30)
        path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        path_entry.insert(0, self.download_path)

        def select_path():
            folder_path = filedialog.askdirectory()
            if folder_path:
                path_entry.delete(0, tk.END)
                path_entry.insert(0, folder_path)

        path_button = tk.Button(path_frame, text="浏览...", command=select_path)
        path_button.pack(side=tk.LEFT, padx=5)

        # 关于选项卡
        about_tab = ttk.Frame(tab_control)
        tab_control.add(about_tab, text="关于")
        about_frame = tk.Frame(about_tab)
        about_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        about_title = tk.Label(about_frame, text=APP_TITLE, font=("Arial", 16, "bold"))
        about_title.pack(pady=10)
        about_version = tk.Label(about_frame, text=f"版本: {VERSION}")
        about_version.pack()
        about_description = tk.Label(about_frame, text="一个简单的B站视频下载工具，支持单视频和分P下载。")
        about_description.pack(pady=10)
        about_copyright = tk.Label(about_frame, text="© 2025 开发者保留所有权利")
        about_copyright.pack(pady=5)

        # 保存设置按钮
        def save_settings():
            self.cookie = cookie_text.get("1.0", tk.END).strip()
            self.download_path = path_entry.get().strip()
            save_config(self.cookie, self.download_path)
            show_message("提示", "设置已保存", parent=settings_window)
            settings_window.destroy()

        save_button = tk.Button(settings_window, text="保存设置", command=save_settings)
        save_button.pack(pady=10)

        tab_control.pack(expand=1, fill="both")

    def _check_updates(self):
        show_message("检查更新", "当前已是最新版本!")

    def _show_context_menu(self, event):
        selected = self.task_list.selection()
        if not selected:
            return

        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="查看分P信息", command=self._show_selected_parts_info)
        context_menu.add_command(label="删除选中任务", command=self._remove_selected_task)

        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def _update_ui_status(self):
        if self.is_downloading:
            self.status_label.config(text="状态: 下载中")
            self.pause_resume_button.config(text="暂停下载")
        else:
            if self.download_queue:
                self.status_label.config(text="状态: 已暂停")
                self.pause_resume_button.config(text="继续下载")
            else:
                self.status_label.config(text="状态: 就绪")
                self.pause_resume_button.config(text="暂停下载")
        self.root.after(500, self._update_ui_status)

    def _check_ffmpeg_on_start(self):
        if not check_ffmpeg_installed() and self.download_mode.get() == "merged":
            show_warning(
                "FFmpeg未安装",
                "检测到您选择了音视频合并模式，但系统中未安装FFmpeg。\n\n"
                "请先安装FFmpeg，否则合并功能将无法使用。\n\n"
                "已自动切换到'仅音频'模式。",
                parent=self.root
            )
            self.download_mode.set("audio_only")

    def _drop_files(self, event):
        files = event.data
        if files:
            self.input_text.delete("1.0", tk.END)
            for file in files.split():
                file = file.strip('"\'')
                if file.startswith("http"):
                    self.input_text.insert(tk.END, file + "\n")

    def _setup_drag_and_drop(self):
        try:
            from tkinterdnd2 import TkinterDnD, DND_FILES
            self.root.destroy()
            self.root = TkinterDnD.Tk()
            self.root.title(APP_TITLE)
            self.root.geometry(APP_GEOMETRY)
            self._create_widgets() # 重新创建部件
            self.input_text.drop_target_register(DND_FILES)
            self.input_text.dnd_bind('<<Drop>>', self._drop_files)
        except ImportError:
            pass # 忽略拖放功能

    def _apply_theme(self, theme_name):
        style = ttk.Style()
        if theme_name == "light":
            self.root.config(bg="#f0f0f0")
            # 可以配置更多组件的背景色和前景色
        elif theme_name == "dark":
            self.root.config(bg="#333333")
            # 同样配置更多组件
        # 可以添加更多主题

        # 配置ttk样式 (这里只是一个基本示例)
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        style.configure("TNotebook", background="#f0f0f0")
        style.configure("TNotebook.Tab", background="#e0e0e0", padding=[10, 2])
        style.map("TNotebook.Tab", background=[("selected", "#f0f0f0")])

    def _on_closing(self):
        save_config(self.cookie, self.download_path)
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = BiliDownloaderApp(root)
    root.mainloop()