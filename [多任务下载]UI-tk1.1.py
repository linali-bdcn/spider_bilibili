import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import requests
import re
import os
from get_url import BilibiliDownloader

# 全局变量
cookie = ""
download_path = r"D:"

# 主窗口
root = tk.Tk()
root.title("B站视频下载器")
root.geometry("800x500")

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
is_paused = False
current_task_id = None
download_thread_obj = None


# 下载线程函数
def download_thread():
    global is_downloading, current_task_id, download_queue, is_paused

    while download_queue:
        # 检查是否暂停
        while is_paused:
            time.sleep(0.5)  # 暂停状态下，定期检查
            if not is_paused:  # 如果恢复了，继续下载
                break

        # 获取下一个任务
        task_id = download_queue[0]  # 只查看，不移除
        current_task_id = task_id
        url = task_list.item(task_id, "values")[0]

        # 更新状态为"下载中"
        task_list.item(task_id, values=(url, "下载中", "0%"))
        root.update_idletasks()

        try:
            # 创建下载器实例并设置进度回调
            downloader = BilibiliDownloader()

            # 自定义进度回调函数
            def progress_callback(percent):
                # 检查是否暂停
                if is_paused:
                    task_list.item(task_id, values=(url, "已暂停", f"{percent}%"))
                else:
                    task_list.item(task_id, values=(url, "下载中", f"{percent}%"))
                root.update_idletasks()

            # 添加进度回调
            downloader.set_progress_callback(progress_callback)

            # 开始下载
            headers = {
                "referer": "https://www.bilibili.com/",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
                "Cookie": cookie
            }

            # 执行下载
            downloader.download_video_and_audio(url, headers)

            # 更新状态为"已完成"
            task_list.item(task_id, values=(url, "已完成", "100%"))

            # 任务完成，从队列中移除
            download_queue.pop(0)

        except Exception as e:
            # 下载失败
            task_list.item(task_id, values=(url, f"失败: {str(e)[:20]}", ""))
            print(f"下载失败: {e}")
            # 从队列中移除失败的任务
            download_queue.pop(0)

    # 所有任务完成
    is_downloading = False
    current_task_id = None


# 添加下载任务
def add_download_tasks():
    global is_downloading, download_thread_obj

    # 获取输入框中的URL（可能有多行）
    urls = input_text.get("1.0", tk.END).strip().split("\n")
    urls = [url.strip() for url in urls if url.strip()]

    if not urls:
        messagebox.showinfo("提示", "请输入至少一个有效的视频URL")
        return

    # 添加到任务列表
    for url in urls:
        task_id = task_list.insert("", tk.END, values=(url, "等待中", ""))
        download_queue.append(task_id)

    # 清空输入框
    input_text.delete("1.0", tk.END)

    # 如果没有正在下载的任务，启动下载线程
    if not is_downloading:
        is_downloading = True
        download_thread_obj = threading.Thread(target=download_thread, daemon=True)
        download_thread_obj.start()


# 暂停/恢复下载
def toggle_pause():
    global is_paused

    if not is_downloading:
        messagebox.showinfo("提示", "当前没有正在进行的下载任务")
        return

    is_paused = not is_paused

    if is_paused:
        pause_resume_button.config(text="恢复下载")
        # 更新当前任务状态
        if current_task_id:
            url = task_list.item(current_task_id, "values")[0]
            progress = task_list.item(current_task_id, "values")[2]
            task_list.item(current_task_id, values=(url, "已暂停", progress))
    else:
        pause_resume_button.config(text="暂停下载")
        # 更新当前任务状态
        if current_task_id:
            url = task_list.item(current_task_id, "values")[0]
            progress = task_list.item(current_task_id, "values")[2]
            task_list.item(current_task_id, values=(url, "下载中", progress))


# 清空任务列表按钮
def clear_completed_tasks():
    for item in task_list.get_children():
        status = task_list.item(item, "values")[1]
        if status == "已完成" or status.startswith("失败"):
            task_list.delete(item)

# 创建按钮区域
button_frame = tk.Frame(left_frame)
button_frame.pack(pady=10, fill=tk.X)

# 添加下载按钮
start_button = tk.Button(button_frame, text="添加下载任务", command=add_download_tasks)
start_button.pack(side=tk.LEFT, padx=5)

# 添加暂停/恢复按钮
pause_resume_button = tk.Button(button_frame, text="暂停下载", command=toggle_pause)
pause_resume_button.pack(side=tk.LEFT, padx=5)

# 添加清除已完成任务按钮
clear_button = tk.Button(right_frame, text="清除已完成任务", command=clear_completed_tasks)
clear_button.pack(pady=5)

# 运行主循环
root.mainloop()