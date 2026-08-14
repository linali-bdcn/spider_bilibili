"""工具箱页 UI — 字幕/封面/评论提取。"""

import tkinter as tk
from tkinter import ttk


class ToolsTab:
    """工具箱页面板。通过回调通知外部执行提取操作。"""

    def __init__(self, parent: ttk.Frame, on_extract):
        """
        on_extract: callable(action_type: str, video_url: str, output_format: str)
        """
        self.main = ttk.Frame(parent, padding=10)

        # ---- URL 输入 ----
        url_frame = ttk.Frame(self.main)
        url_frame.pack(fill=tk.X, pady=5)
        ttk.Label(url_frame, text="单视频链接:").pack(side=tk.LEFT)
        self.url_var = tk.StringVar()
        ttk.Entry(url_frame, textvariable=self.url_var, width=60).pack(
            side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # ---- 提取工具 ----
        tools_frame = ttk.LabelFrame(
            self.main, text="提取工具 (文件将保存到全局下载路径)", padding=10)
        tools_frame.pack(fill=tk.X, pady=10)

        # 字幕
        sub_frame = ttk.Frame(tools_frame)
        sub_frame.pack(fill=tk.X, pady=5)
        ttk.Label(sub_frame, text="1. 字幕提取:").pack(side=tk.LEFT, padx=(0, 10))
        self.sub_format = tk.StringVar(value="both")
        for t, v in [("SRT字幕", "srt"), ("纯文本", "txt"), ("全部生成", "both")]:
            ttk.Radiobutton(sub_frame, text=t, value=v,
                            variable=self.sub_format).pack(side=tk.LEFT, padx=5)
        ttk.Button(sub_frame, text="提取字幕",
                   command=lambda: on_extract("subtitle")).pack(side=tk.LEFT, padx=20)

        # 封面 & 评论
        media_frame = ttk.Frame(tools_frame)
        media_frame.pack(fill=tk.X, pady=10)
        ttk.Label(media_frame, text="2. 附加信息:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(media_frame, text="下载高清封面",
                   command=lambda: on_extract("cover")).pack(side=tk.LEFT, padx=5)

        # 评论页数控件
        comment_frame = ttk.Frame(tools_frame)
        comment_frame.pack(fill=tk.X, pady=5)
        ttk.Label(comment_frame, text="3. 评论页数:").pack(side=tk.LEFT, padx=(0, 10))
        self.comments_pages = tk.IntVar(value=20)
        ttk.Spinbox(comment_frame, from_=1, to=100, textvariable=self.comments_pages,
                    width=5).pack(side=tk.LEFT, padx=5)
        ttk.Label(comment_frame, text="页 (每页约20条)", foreground="gray").pack(
            side=tk.LEFT, padx=2)
        ttk.Button(comment_frame, text="批量下载评论(TXT)",
                   command=lambda: on_extract("comments")).pack(side=tk.LEFT, padx=10)

        # pack 到父容器
        self.main.pack(fill=tk.BOTH, expand=True)

    def get_url(self) -> str:
        return self.url_var.get().strip()

    def set_url(self, url: str) -> None:
        self.url_var.set(url)