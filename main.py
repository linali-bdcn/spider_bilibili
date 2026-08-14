#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站视频下载器 + 提取工具箱
重构版 - 模块化架构

用法: python main.py
"""

import sys
import tkinter as tk
from tkinter import messagebox


def check_dependencies():
    """检查并提示缺失的依赖。"""
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
            f"请先安装以下依赖:\n\npip install {' '.join(missing)}\n\n安装后重新运行程序",
        )
        sys.exit(1)


if __name__ == "__main__":
    check_dependencies()

    from bili_downloader.ui.app import BiliDownloader

    app = BiliDownloader()
    app.run()