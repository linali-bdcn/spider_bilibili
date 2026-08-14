"""下载页 UI — URL 输入 + 模式选择 + 操作按钮。"""

import tkinter as tk
from tkinter import ttk


class DownloadTab:
    """下载标签页。"""

    def __init__(self, parent: ttk.Frame, mode_var: tk.StringVar,
                 on_add_queue, on_start, on_pause, on_skip,
                 on_clear, on_parse_list):
        self.frame = parent

        # ---- URL 输入区 ----
        url_frame = ttk.LabelFrame(
            self.frame,
            text="视频链接（每行一个，支持视频/分P/合集/主页）",
            padding=8,
        )
        url_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        btn_line = ttk.Frame(url_frame)
        btn_line.pack(anchor=tk.E, pady=(0, 5))
        ttk.Button(btn_line, text="清空",
                   command=lambda: self.url_text.delete("1.0", tk.END),
                   width=8).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btn_line, text="粘贴",
                   command=self._paste, width=8).pack(side=tk.RIGHT, padx=2)

        self.url_text = tk.Text(url_frame, height=1, wrap=tk.WORD)
        scroll_y = ttk.Scrollbar(url_frame, orient=tk.VERTICAL,
                                 command=self.url_text.yview)
        self.url_text.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.url_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ---- 操作按钮 ----
        action_frame = ttk.Frame(self.frame)
        action_frame.pack(fill=tk.X, pady=8)

        ttk.Button(action_frame, text="快速添加队列", command=on_add_queue,
                   width=15).pack(side=tk.LEFT, padx=2)

        self.start_btn = ttk.Button(action_frame, text="开始下载",
                                    command=on_start, width=12)
        self.start_btn.pack(side=tk.LEFT, padx=2)

        self.pause_btn = ttk.Button(action_frame, text="暂停",
                                    command=on_pause, state=tk.DISABLED, width=8)
        self.pause_btn.pack(side=tk.LEFT, padx=2)

        self.skip_btn = ttk.Button(action_frame, text="跳过",
                                   command=on_skip, state=tk.DISABLED, width=8)
        self.skip_btn.pack(side=tk.LEFT, padx=2)

        ttk.Button(action_frame, text="清除已完成", command=on_clear,
                   width=12).pack(side=tk.RIGHT, padx=2)
        self.list_btn = ttk.Button(action_frame, text="解析列表 (分P/合集)",
                                   command=on_parse_list, width=20)
        self.list_btn.pack(side=tk.RIGHT, padx=10)

        # ---- 下载模式 ----
        mode_frame = ttk.Frame(self.frame)
        mode_frame.pack(fill=tk.X, pady=2)
        ttk.Label(mode_frame, text="下载模式:").pack(side=tk.LEFT)
        for text, val in [("最佳画质", "best"), ("仅音频", "audio"),
                          ("720P", "720"), ("480P", "480")]:
            ttk.Radiobutton(mode_frame, text=text, value=val,
                            variable=mode_var).pack(side=tk.LEFT, padx=8)

    def get_urls(self) -> list:
        """返回文本框中所有有效 URL。"""
        return [
            line.strip()
            for line in self.url_text.get("1.0", tk.END).split("\n")
            if line.strip().startswith(("http://", "https://"))
        ]

    def get_first_url(self) -> str:
        urls = self.get_urls()
        return urls[0] if urls else ""

    def clear_urls(self) -> None:
        self.url_text.delete("1.0", tk.END)

    def _paste(self) -> None:
        try:
            clip = self.url_text.winfo_toplevel().clipboard_get()  # type: ignore
            if clip:
                current = self.url_text.get("1.0", tk.END).strip()
                if current:
                    self.url_text.insert(tk.END, "\n" + clip)
                else:
                    self.url_text.insert(tk.END, clip)
        except Exception:
            pass