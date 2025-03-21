import tkinter as tk
from tkinter import ttk
import threading
import time
import requests
import re
from get_url import BilibiliDownloader

# 全局变量，用于存储 URL
url = None
cookie = ""
path = r"D:"

# 主窗口
root = tk.Tk()
root.title("B站视频下载器")
root.geometry("400x200")

# 输入框和标签
input_label = tk.Label(root, text="请输入 [B站视频URL]:")
input_label.pack(pady=10)

input_entry = tk.Entry(root, width=40)
input_entry.pack(pady=10)

# 进度条
progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress.pack(pady=20)
progress.pack_forget()  # 初始隐藏进度条

# 按钮点击事件
def start_progress():
    global url  # 使用全局变量存储 URL
    url = input_entry.get()  # 获取输入框的内容并存储到 url 变量中
    print(f"输入的 URL 是: {url}")  # 打印 URL（调试用）

    # 隐藏输入界面
    input_label.pack_forget()
    input_entry.pack_forget()
    start_button.pack_forget()

    # 显示进度条
    progress.pack(pady=20)

    # 模拟加载进度
    def simulate_loading():
        global url
        for i in range(1, 100):
            progress['value'] = i
            root.update_idletasks()
            time.sleep(0.05)
        download_video(url, cookie)  # 调用下载函数
        reset_interface()

    # 使用线程避免界面卡住
    threading.Thread(target=simulate_loading).start()

# 下载
def download_video(url, cookie):
    print(f"开始下载视频: {url}")
    # 这里可以添加实际的下载逻辑
    """
        主要下载程序
        :param url: 下载视频精确地址
        :param cookie: 需要一个登录后的cookie
        :param user: 已默认
        :return: 
        """

    headers = {
        # Referer 防盗链 告诉服务器你请求链接是从哪里跳转过来的
        # "Referer": "https://www.bilibili.com/video/BV1454y187Er/",
        "referer": "https://www.bilibili.com/video/BV1MvF5ejEdA?spm_id_from=333.788.videopod.episodes&vd_source=86fde7c1b0fc380df5d84bf3e669c96e&p=3",
        # User-Agent 用户代理, 表示浏览器/设备基本身份信息
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
        # f12开发者模式中可获取以上信息
        "Cookie": cookie
    }
    down = BilibiliDownloader()
    down.download_video_and_audio(url, headers) # 主要下载

# 还原函数
def reset_interface():
    # 隐藏进度条
    progress.pack_forget()
    progress['value'] = 0  # 重置进度条

    # 显示输入界面
    input_label.pack(pady=10)
    input_entry.pack(pady=10)
    start_button.pack(pady=10)


# 按钮
start_button = tk.Button(root, text="开始下载", command=start_progress)
start_button.pack(pady=10)

# 运行主循环
root.mainloop()