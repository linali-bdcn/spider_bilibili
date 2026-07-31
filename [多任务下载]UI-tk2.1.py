import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import requests
import re
import os
from ffmpeg_installer import FFmpegInstaller
from fake_useragent import UserAgent

from get_url1 import BilibiliDownloader

# 全局变量
cookie = ""
download_path = r"D:"

# 新增：启动免责声明
def show_disclaimer():
    disclaimer = """【免责声明】
1. 本工具仅用于技术学习交流
2. 禁止下载未授权内容
3. 使用即表示您知晓相关风险"""
    if not messagebox.askyesno("免责声明", disclaimer + "\n\n是否同意继续使用？"):
        root.destroy()

# 主窗口
# 主窗口初始化
root = tk.Tk()
root.title("B站视频下载器 v2.1")
root.geometry("800x500")
root.after(100, show_disclaimer)  # 启动时显示声明

# 新增：全局UA生成器
ua = UserAgent()

# 创建左右分栏
left_frame = tk.Frame(root, width=300)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)

right_frame = tk.Frame(root, width=500)
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

# 左侧输入区域
input_label = tk.Label(left_frame, text="请输入B站视频URL(每行一个):")
input_label.pack(pady=5, anchor="w")

input_text = scrolledtext.ScrolledText(left_frame, width=35, height=10)
input_text.pack(pady=5, fill=tk.BOTH, expand=True)

# 在左侧输入区域添加下载模式选择
mode_frame = tk.Frame(left_frame)
mode_frame.pack(pady=5, fill=tk.X)

mode_label = tk.Label(mode_frame, text="下载模式:")
mode_label.pack(side=tk.LEFT, padx=5)

# 在创建主窗口后添加检查
def check_ffmpeg():
    if download_mode.get() == "merged" and not FFmpegInstaller.is_ffmpeg_installed():
        if FFmpegInstaller.install():
            messagebox.showinfo("成功", "FFmpeg安装完成！")
        else:
            download_mode.set("audio_only")  # 回退到仅音频模式

root.after(1000, check_ffmpeg)  # 延迟1秒检查



# 检查FFmpeg是否已安装
def check_ffmpeg():
    """检查FFmpeg是否已安装"""
    try:
        import subprocess
        process = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if process.returncode == 0:
            return True
        return False
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


# 下载模式选择
download_mode = tk.StringVar(value="audio_only")
mode_options = [
    ("仅音频", "audio_only"),
    ("仅视频", "video_only"),
    ("音视频分离", "separate"),
    ("音视频合并", "merged")
]

# 创建单选按钮框架
radio_frame = tk.Frame(left_frame)
radio_frame.pack(pady=5, fill=tk.X)

# 下载函数
def on_download_mode_change():
    """当用户切换下载模式时的回调函数"""
    selected_mode = download_mode.get()

    # 如果选择合并模式且未安装FFmpeg
    if selected_mode == "merged" and not FFmpegInstaller.is_ffmpeg_installed():
        # 弹出安装确认对话框
        install_now = messagebox.askyesno(
            "需要FFmpeg",
            "音视频合并需要FFmpeg支持，是否立即安装？\n\n"
            "（Windows用户将安装到程序目录，无需管理员权限）",
            parent=root
        )

        if install_now:
            # 执行安装并更新状态
            if FFmpegInstaller.install():
                messagebox.showinfo("成功", "FFmpeg安装完成！", parent=root)
                ffmpeg_label.config(text="FFmpeg状态: 已安装 ✓", fg="green")
            else:
                # 安装失败则自动切换回仅音频模式
                download_mode.set("audio_only")
                messagebox.showwarning(
                    "安装失败",
                    "无法自动安装FFmpeg，已切换为仅音频模式。\n"
                    "您仍可手动安装FFmpeg后重新选择合并模式。",
                    parent=root
                )
        else:
            # 用户取消安装，回退到仅音频模式
            download_mode.set("audio_only")

# 下载FFmpeg 添加单选按钮
for text, mode in mode_options:
    rb = tk.Radiobutton(
        radio_frame,
        text=text,
        variable=download_mode,
        value=mode,
        command=on_download_mode_change  # 绑定回调
    )
    rb.pack(side=tk.LEFT, padx=5)

    # 如果是合并模式，检查FFmpeg是否可用
    if mode == "merged":
        def check_merged_mode():
            if download_mode.get() == "merged" and not check_ffmpeg():
                messagebox.showwarning(
                    "FFmpeg未安装",
                    "检测到您选择了音视频合并模式，但系统中未安装FFmpeg。\n\n"
                    "请先安装FFmpeg，否则合并功能将无法使用。\n\n"
                    "是否仍要继续使用此模式？",
                    parent=root
                )


        rb.config(command=check_merged_mode)

# 显示FFmpeg安装状态
ffmpeg_frame = tk.Frame(left_frame)
ffmpeg_frame.pack(fill=tk.X, pady=5)

ffmpeg_status = "已安装 ✓" if check_ffmpeg() else "未安装 ✗"
ffmpeg_color = "green" if check_ffmpeg() else "red"

ffmpeg_label = tk.Label(
    ffmpeg_frame,
    text=f"FFmpeg状态: {ffmpeg_status}",
    fg=ffmpeg_color
)
ffmpeg_label.pack(side=tk.LEFT, padx=5)



if not check_ffmpeg():
    def open_ffmpeg_website():
        import webbrowser
        webbrowser.open("https://ffmpeg.org/download.html")


    download_link = tk.Label(
        ffmpeg_frame,
        text="点击下载FFmpeg",
        fg="blue",
        cursor="hand2"
    )
    download_link.pack(side=tk.LEFT, padx=5)
    download_link.bind("<Button-1>", lambda e: open_ffmpeg_website())

    help_link = tk.Label(
        ffmpeg_frame,
        text="安装帮助",
        fg="blue",
        cursor="hand2"
    )
    help_link.pack(side=tk.LEFT, padx=5)
    help_link.bind("<Button-1>", lambda e: messagebox.showinfo(
        "FFmpeg安装帮助",
        "1. 从官网下载FFmpeg\n"
        "2. 解压到任意文件夹\n"
        "3. 将FFmpeg的bin目录添加到系统环境变量PATH中\n"
        "4. 重启应用程序\n\n"
        "详细教程可在网上搜索'FFmpeg安装教程'",
        parent=root
    ))

# 右侧任务列表
task_label = tk.Label(right_frame, text="下载任务列表:")
task_label.pack(pady=5, anchor="w")

# 创建任务列表（使用Treeview）
columns = ("url", "status", "progress")
task_list = ttk.Treeview(right_frame, columns=columns, show="headings", height=15)

# 定义列
task_list.heading("url", text="视频地址")
task_list.heading("status", text="状态")
task_list.heading("progress", text="进度")

# 设置列宽
task_list.column("url", width=300)
task_list.column("status", width=100)
task_list.column("progress", width=100)

task_list.pack(fill=tk.BOTH, expand=True, pady=5)

# 下载队列和状态管理
download_queue = []
is_downloading = False
current_task_id = None


# 获取下载模式的显示文本
def get_mode_display(mode):
    for text, value in mode_options:
        if value == mode:
            return text
    return mode


# 下载线程函数
def download_thread():
    global is_downloading, current_task_id, download_queue

    while download_queue:
        # 获取下一个任务
        task_id = download_queue.pop(0)
        current_task_id = task_id
        url = task_list.item(task_id, "values")[0]

        # 获取当前选择的下载模式
        mode = download_mode.get()

        # 更新状态为"下载中"
        task_list.item(task_id, values=(url, f"下载中({get_mode_display(mode)})", "0%"))
        root.update_idletasks()

        try:
            # 创建下载器实例并设置进度回调
            downloader = BilibiliDownloader()

            # 自定义进度回调函数
            def progress_callback(percent):
                task_list.item(task_id, values=(url, f"下载中({get_mode_display(mode)})", f"{percent}%"))
                root.update_idletasks()

            # 添加进度回调
            downloader.set_progress_callback(progress_callback)

            # 开始下载
            headers = {
                "referer": "https://www.bilibili.com/",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
                "Cookie": cookie
            }

            # 执行下载，传入下载模式
            if mode == "merged":
                # 先下载视频和音频
                video_path = downloader.download_video(url, headers)
                audio_path = downloader.download_audio(url, headers)
                
                if video_path and audio_path:
                    # 合并音视频
                    output_path = os.path.join(download_path, f"{downloader.safe_filename(downloader.get_name())}.mp4")
                    if not downloader.merge_media(video_path, audio_path, output_path):
                        task_list.item(task_id, values=(url, "合并失败", ""))
                        return
            else:
                downloader.download_video_and_audio(url, headers, mode)

            # 更新状态为"已完成"
            task_list.item(task_id, values=(url, f"已完成({get_mode_display(mode)})", "100%"))

        except Exception as e:
            # 下载失败
            error_msg = str(e)[:40] + "..." if len(str(e)) > 40 else str(e)
            task_list.item(task_id, values=(url, f"失败: {error_msg}", ""))
            print(f"下载失败: {e}")

    # 所有任务完成
    is_downloading = False
    current_task_id = None

# 添加下载任务
def add_download_tasks():
    global is_downloading

    # 获取输入框中的URL（可能有多行）
    urls = input_text.get("1.0", tk.END).strip().split("\n")
    urls = [url.strip() for url in urls if url.strip()]

    if not urls:
        messagebox.showinfo("提示", "请输入至少一个有效的视频URL")
        return

    # 获取当前选择的下载模式
    current_mode = download_mode.get()

    # 如果选择了合并模式但FFmpeg未安装，提示用户
    if current_mode == "merged" and not check_ffmpeg():
        if not messagebox.askyesno(
            "警告",
            "您选择了音视频合并模式，但系统中未安装FFmpeg，合并功能将无法使用。\n\n"
            "是否继续添加下载任务？\n"
            "（建议切换到其他下载模式或安装FFmpeg后再尝试）",
            parent=root
        ):
            return

    # 添加到任务列表
    for url in urls:
        task_id = task_list.insert("", tk.END, values=(url, f"等待中({get_mode_display(current_mode)})", ""))
        download_queue.append(task_id)

    # 清空输入框
    input_text.delete("1.0", tk.END)

    # 如果没有正在下载的任务，启动下载线程
    if not is_downloading:
        is_downloading = True
        threading.Thread(target=download_thread, daemon=True).start()

# 清空任务列表按钮
def clear_completed_tasks():
    for item in task_list.get_children():
        status = task_list.item(item, "values")[1]
        if status.startswith("已完成") or status.startswith("失败"):
            task_list.delete(item)

# 显示视频分P信息
def show_parts_info(url):
    try:
        downloader = BilibiliDownloader()
        parts_info = downloader.get_p_total(url)

        # 新窗口设置
        parts_win = tk.Toplevel(root)
        parts_win.title("分P选择")
        parts_win.geometry("500x400")

        # 顶部操作栏
        top_frame = tk.Frame(parts_win)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        # 新增：模式显示
        mode_label = tk.Label(top_frame, text=f"当前模式: {download_mode.get()}")
        mode_label.pack(side=tk.RIGHT)

        # 中间复选框区域（使用Canvas实现滚动）
        canvas = tk.Canvas(parts_win)
        scrollbar = tk.Scrollbar(parts_win, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 填充复选框
        check_vars = []
        for p, _, title in parts_info:
            var = tk.BooleanVar()
            check_vars.append(var)
            cb = tk.Checkbutton(scroll_frame, text=f"P{p}: {title}", variable=var)
            cb.pack(anchor="w")

        # 底部确认区域（修复按钮消失问题）
        bottom_frame = tk.Frame(parts_win)
        bottom_frame.pack(fill=tk.X, pady=10)

        def start_download():
            selected = [parts_info[i][1] for i, var in enumerate(check_vars) if var.get()]
            if not selected:
                messagebox.showwarning("提示", "请至少选择一个分P")
                return

            # 添加下载任务逻辑...
            parts_win.destroy()

        tk.Button(bottom_frame, text="确认下载", command=start_download, width=15).pack()

        # 布局滚动组件
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    except Exception as e:
        messagebox.showerror("错误", f"获取分P失败: {str(e)}")


# 显示当前选中任务的分P信息
def show_selected_parts_info():
    selected_items = task_list.selection()
    if not selected_items:
        messagebox.showinfo("提示", "请先选择一个任务")
        return

    # 获取选中项的URL
    task_id = selected_items[0]
    url = task_list.item(task_id, "values")[0]
    show_parts_info(url)


# 暂停/继续下载功能
def pause_resume_download():
    global is_downloading
    if is_downloading:
        # 暂停下载
        is_downloading = False
        pause_resume_button.config(text="继续下载")
        status_label.config(text="状态: 已暂停")
    else:
        # 继续下载
        if download_queue:
            is_downloading = True
            threading.Thread(target=download_thread, daemon=True).start()
            pause_resume_button.config(text="暂停下载")
            status_label.config(text="状态: 下载中")
        else:
            messagebox.showinfo("提示", "没有等待中的下载任务")


# 删除选中的任务
def remove_selected_task():
    selected_items = task_list.selection()
    if not selected_items:
        messagebox.showinfo("提示", "请先选择要删除的任务")
        return

    for item in selected_items:
        # 如果是当前正在下载的任务，不能删除
        if item == current_task_id:
            messagebox.showinfo("提示", "无法删除正在下载的任务")
            continue

        # 如果在下载队列中，需要从队列中移除
        if item in download_queue:
            download_queue.remove(item)

        # 从列表中删除
        task_list.delete(item)


# 创建按钮区域
button_frame = tk.Frame(left_frame)
button_frame.pack(pady=10, fill=tk.X)

# 添加下载按钮
start_button = tk.Button(button_frame, text="添加下载任务", command=add_download_tasks)
start_button.pack(side=tk.LEFT, padx=5)

# 添加查看分P信息按钮
info_button = tk.Button(button_frame, text="查看分P信息", command=show_selected_parts_info)
info_button.pack(side=tk.LEFT, padx=5)

# 添加暂停/继续按钮
pause_resume_button = tk.Button(button_frame, text="暂停下载", command=pause_resume_download)
pause_resume_button.pack(side=tk.LEFT, padx=5)

# 状态栏
status_frame = tk.Frame(left_frame)
status_frame.pack(fill=tk.X, pady=5)

status_label = tk.Label(status_frame, text="状态: 就绪")
status_label.pack(side=tk.LEFT, padx=5)

# 右侧按钮区域
right_button_frame = tk.Frame(right_frame)
right_button_frame.pack(fill=tk.X, pady=5)

# 添加清除已完成任务按钮
clear_button = tk.Button(right_button_frame, text="清除已完成任务", command=clear_completed_tasks)
clear_button.pack(side=tk.LEFT, padx=5)

# 添加删除选中任务按钮
remove_button = tk.Button(right_button_frame, text="删除选中任务", command=remove_selected_task)
remove_button.pack(side=tk.LEFT, padx=5)


# 设置和配置相关功能
def open_settings():
    settings_window = tk.Toplevel(root)
    settings_window.title("设置")
    settings_window.geometry("400x300")
    settings_window.resizable(False, False)

    # 创建设置选项卡
    tab_control = ttk.Notebook(settings_window)

    # 常规设置选项卡
    general_tab = ttk.Frame(tab_control)
    tab_control.add(general_tab, text="常规设置")

    # Cookie设置
    cookie_frame = tk.Frame(general_tab)
    cookie_frame.pack(fill=tk.X, padx=10, pady=10)

    cookie_label = tk.Label(cookie_frame, text="Cookie设置:")
    cookie_label.pack(anchor="w")

    cookie_text = tk.Text(cookie_frame, height=5, width=40)
    cookie_text.pack(fill=tk.X, pady=5)
    cookie_text.insert(tk.END, cookie)

    cookie_help = tk.Label(cookie_frame, text="提示: 登录B站后，F12打开开发者工具，在Network中找到任意请求，复制Cookie值",
                           fg="gray")
    cookie_help.pack(anchor="w")

    # 下载路径设置
    path_frame = tk.Frame(general_tab)
    path_frame.pack(fill=tk.X, padx=10, pady=10)

    path_label = tk.Label(path_frame, text="下载路径:")
    path_label.pack(side=tk.LEFT, padx=5)

    path_entry = tk.Entry(path_frame, width=30)
    path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    path_entry.insert(0, download_path)

    def select_path():
        from tkinter import filedialog
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

    about_title = tk.Label(about_frame, text="B站视频下载器", font=("Arial", 16, "bold"))
    about_title.pack(pady=10)

    about_version = tk.Label(about_frame, text="版本: 1.0.0")
    about_version.pack()

    about_description = tk.Label(about_frame, text="一个简单的B站视频下载工具，支持单视频和分P下载。")
    about_description.pack(pady=10)

    about_copyright = tk.Label(about_frame, text="© 2025 开发者保留所有权利")
    about_copyright.pack(pady=5)

    # 保存设置按钮
    def save_settings():
        global cookie, download_path
        cookie = cookie_text.get("1.0", tk.END).strip()
        download_path = path_entry.get().strip()

        # 这里可以添加保存到配置文件的代码

        messagebox.showinfo("提示", "设置已保存", parent=settings_window)
        settings_window.destroy()

    save_button = tk.Button(settings_window, text="保存设置", command=save_settings)
    save_button.pack(pady=10)

    # 显示选项卡
    tab_control.pack(expand=1, fill="both")


# 添加设置按钮
settings_button = tk.Button(left_frame, text="设置", command=open_settings)
settings_button.pack(side=tk.RIGHT, padx=5, pady=5)


# 检查更新函数
def check_updates():
    # 这里添加检查更新的逻辑
    messagebox.showinfo("检查更新", "当前已是最新版本!")


# 添加菜单栏
menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

# 文件菜单
file_menu = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="文件", menu=file_menu)
file_menu.add_command(label="添加下载任务", command=add_download_tasks)
file_menu.add_command(label="查看分P信息", command=show_selected_parts_info)
file_menu.add_separator()
file_menu.add_command(label="设置", command=open_settings)
file_menu.add_separator()
file_menu.add_command(label="退出", command=root.quit)

# 操作菜单
action_menu = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="操作", menu=action_menu)
action_menu.add_command(label="暂停/继续下载", command=pause_resume_download)
action_menu.add_command(label="清除已完成任务", command=clear_completed_tasks)
action_menu.add_command(label="删除选中任务", command=remove_selected_task)

# 帮助菜单
help_menu = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="帮助", menu=help_menu)
help_menu.add_command(label="使用说明", command=lambda: messagebox.showinfo("使用说明",
                                                                            "1. 输入B站视频URL\n"
                                                                            "2. 选择下载模式\n"
                                                                            "3. 点击'添加下载任务'或'查看分P信息'\n"
                                                                            "4. 等待下载完成\n\n"
                                                                            "注意: 音视频合并模式需要安装FFmpeg"
                                                                            ))
help_menu.add_command(label="检查更新", command=check_updates)
help_menu.add_separator()
help_menu.add_command(label="关于", command=lambda: messagebox.showinfo("关于",
                                                                        "B站视频下载器 v1.0.0\n"
                                                                        "一个简单的B站视频下载工具\n"
                                                                        "© 2025 开发者保留所有权利"
                                                                        ))


# 添加右键菜单
def show_context_menu(event):
    # 获取选中的项
    selected = task_list.selection()
    if not selected:
        return

    # 创建右键菜单
    context_menu = tk.Menu(root, tearoff=0)
    context_menu.add_command(label="查看分P信息", command=show_selected_parts_info)
    context_menu.add_command(label="删除选中任务", command=remove_selected_task)

    # 显示菜单
    try:
        context_menu.tk_popup(event.x_root, event.y_root)
    finally:
        context_menu.grab_release()


# 绑定右键菜单
task_list.bind("<Button-3>", show_context_menu)


# 定期更新UI状态
def update_ui_status():
    if is_downloading:
        status_label.config(text="状态: 下载中")
        pause_resume_button.config(text="暂停下载")
    else:
        if download_queue:
            status_label.config(text="状态: 已暂停")
            pause_resume_button.config(text="继续下载")
        else:
            status_label.config(text="状态: 就绪")
            pause_resume_button.config(text="暂停下载")

    # 每500毫秒更新一次
    root.after(500, update_ui_status)


# 启动UI状态更新
update_ui_status()


# 启动时检查FFmpeg
def show_ffmpeg_warning():
    if not check_ffmpeg() and download_mode.get() == "merged":
        messagebox.showwarning(
            "FFmpeg未安装",
            "检测到您选择了音视频合并模式，但系统中未安装FFmpeg。\n\n"
            "请先安装FFmpeg，否则合并功能将无法使用。\n\n"
            "已自动切换到'仅音频'模式。",
            parent=root
        )
        download_mode.set("audio_only")  # 自动切换到仅音频模式


# 在主窗口初始化后调用
root.after(1000, show_ffmpeg_warning)

# 拖放支持
def drop_files(event):
    # 获取拖放的文件路径
    files = event.data

    # 处理拖放的URL
    if files:
        # 清空当前输入框
        input_text.delete("1.0", tk.END)

        # 将拖放的URL添加到输入框
        for file in files.split():
            # 移除可能的引号
            file = file.strip('"\'')

            # 如果是URL，添加到输入框
            if file.startswith("http"):
                input_text.insert(tk.END, file + "\n")

# 尝试导入TkinterDnD库来支持拖放
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES

    # 重新初始化根窗口以支持拖放
    root.destroy()
    root = TkinterDnD.Tk()
    root.title("B站视频下载器")
    root.geometry("800x500")

    # 设置拖放目标
    input_text.drop_target_register(DND_FILES)
    input_text.dnd_bind('<<Drop>>', drop_files)

except ImportError:
    # 如果没有TkinterDnD库，忽略拖放功能
    pass

# 应用主题
def apply_theme(theme_name):
    if theme_name == "light":
        # 浅色主题
        root.config(bg="#f0f0f0")
        left_frame.config(bg="#f0f0f0")
        right_frame.config(bg="#f0f0f0")
        # 更多组件样式...
    elif theme_name == "dark":
        # 深色主题
        root.config(bg="#333333")
        left_frame.config(bg="#333333")
        right_frame.config(bg="#333333")
        # 更多组件样式...
    elif theme_name == "blue":
        # 蓝色主题
        root.config(bg="#e6f2ff")
        left_frame.config(bg="#e6f2ff")
        right_frame.config(bg="#e6f2ff")
        # 更多组件样式...

# 默认应用浅色主题
apply_theme("light")

# 创建自定义样式
style = ttk.Style()
style.configure("TButton", padding=6, relief="flat", background="#ccc")
style.configure("TNotebook", background="#f0f0f0")
style.configure("TNotebook.Tab", background="#e0e0e0", padding=[10, 2])
style.map("TNotebook.Tab", background=[("selected", "#f0f0f0")])

# 尝试加载配置文件
def load_config():
    global cookie, download_path
    try:
        import json
        import os

        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

                # 加载Cookie
                if "cookie" in config:
                    cookie = config["cookie"]

                # 加载下载路径
                if "download_path" in config:
                    download_path = config["download_path"]
                    # 检查路径是否存在，不存在则创建
                    if not os.path.exists(download_path):
                        try:
                            os.makedirs(download_path)
                        except:
                            download_path = os.path.expanduser("~/Downloads")
    except Exception as e:
        print(f"加载配置文件出错: {e}")


# 保存配置文件
def save_config():
    try:
        import json
        import os

        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

        config = {
            "cookie": cookie,
            "download_path": download_path
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"保存配置文件出错: {e}")

# 在应用启动时加载配置
load_config()

# 在应用关闭时保存配置
def on_closing():
    save_config()
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_closing)

# 运行主循环
root.mainloop()
