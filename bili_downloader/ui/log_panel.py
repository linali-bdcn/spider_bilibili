"""
统一日志面板 — 记录所有操作的日志，并持久化到 logs/ 目录。
"""

import os
import tkinter as tk
from tkinter import ttk
from datetime import datetime


class LogPanel:
    """全局日志面板。所有模块共用此实例写日志。"""

    def __init__(self, parent: ttk.Frame, project_root: str):
        self._log_dir = os.path.join(project_root, "logs")
        os.makedirs(self._log_dir, exist_ok=True)

        # 本次会话的日志文件
        session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_path = os.path.join(self._log_dir, f"session_{session_ts}.log")

        # ---- UI ----
        frame = ttk.LabelFrame(parent, text="操作日志", padding=5)
        frame.pack(fill=tk.BOTH, expand=True)

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, pady=(0, 3))
        ttk.Label(toolbar, text=f"日志文件: logs/session_{session_ts}.log",
                  foreground="gray").pack(side=tk.LEFT)
        ttk.Button(toolbar, text="清空显示", command=self._clear_display,
                   width=10).pack(side=tk.RIGHT, padx=2)
        ttk.Button(toolbar, text="打开日志目录",
                   command=lambda: os.startfile(self._log_dir) if os.name == "nt" else None,
                   width=12).pack(side=tk.RIGHT, padx=2)

        self._text = tk.Text(frame, height=1, state=tk.DISABLED, wrap=tk.WORD,
                             font=("Consolas", 9))
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self._text.yview)
        self._text.configure(yscrollcommand=scroll.set)
        self._text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 启动日志
        self.info("程序启动")

    # ---- 公开 API ----

    def info(self, msg: str) -> None:
        self._write("INFO", msg)

    def success(self, msg: str) -> None:
        self._write("OK", msg)

    def warn(self, msg: str) -> None:
        self._write("WARN", msg)

    def error(self, msg: str) -> None:
        self._write("ERR", msg)

    # ---- 内部 ----

    def _write(self, level: str, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {msg}"

        # 写入 UI
        self._text.config(state=tk.NORMAL)
        self._text.insert(tk.END, line + "\n")
        self._text.see(tk.END)
        self._text.config(state=tk.DISABLED)

        # 持久化到文件
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def _clear_display(self) -> None:
        self._text.config(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.config(state=tk.DISABLED)