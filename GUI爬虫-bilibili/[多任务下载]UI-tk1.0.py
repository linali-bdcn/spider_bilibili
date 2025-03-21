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
current_task_id = None


# 下载线程函数
def download_thread():
    global is_downloading, current_task_id, download_queue

    while download_queue:
        # 获取下一个任务
        task_id = download_queue.pop(0)
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

        except Exception as e:
            # 下载失败
            task_list.item(task_id, values=(url, f"失败: {str(e)[:20]}", ""))
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

    # 添加到任务列表
    for url in urls:
        task_id = task_list.insert("", tk.END, values=(url, "等待中", ""))
        download_queue.append(task_id)

    # 清空输入框
    input_text.delete("1.0", tk.END)

    # 如果没有正在下载的任务，启动下载线程
    if not is_downloading:
        is_downloading = True
        threading.Thread(target=download_thread, daemon=True).start()


# BilibiliDownloader类的修改（添加进度回调）
# 注意：这部分需要修改你的BilibiliDownloader类
"""
在你的BilibiliDownloader类中添加以下代码:

def set_progress_callback(self, callback):
    self.progress_callback = callback

然后在download_file方法中修改:

def download_file(self, url, file_path):
    try:
        response = requests.get(url, headers=self.headers, stream=True)
        response.raise_for_status()

        # 获取文件大小
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # 更新进度
                    if hasattr(self, 'progress_callback') and total_size > 0:
                        progress = int(downloaded * 100 / total_size)
                        self.progress_callback(progress)

        logging.info(f"文件已保存为 {file_path}")
    except requests.exceptions.RequestException as e:
        logging.error(f"下载出错: {e}")
    except Exception as e:
        logging.error(f"保存文件时出错: {e}")
"""

# 按钮
start_button = tk.Button(left_frame, text="添加下载任务", command=add_download_tasks)
start_button.pack(pady=10)


# 清空任务列表按钮
def clear_completed_tasks():
    for item in task_list.get_children():
        status = task_list.item(item, "values")[1]
        if status == "已完成" or status.startswith("失败"):
            task_list.delete(item)


clear_button = tk.Button(right_frame, text="清除已完成任务", command=clear_completed_tasks)
clear_button.pack(pady=5)

# 运行主循环
root.mainloop()