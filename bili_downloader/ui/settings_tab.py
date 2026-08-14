"""设置页 UI — Cookie / 下载路径配置。"""

import os
import tkinter as tk
from tkinter import ttk, filedialog


class SettingsTab:
    """设置页面板。通过 tk.StringVar 与外部双向绑定。"""

    def __init__(self, parent: ttk.Frame, download_path: tk.StringVar,
                 cookie_method: tk.StringVar, browser_var: tk.StringVar,
                 cookie_file_var: tk.StringVar, on_cookie_change,
                 on_save):
        self.frame = ttk.Frame(parent, padding=10)

        # ---- 保存路径 ----
        pf = ttk.Frame(self.frame)
        pf.pack(fill=tk.X, pady=5)
        ttk.Label(pf, text="全局保存路径:").pack(side=tk.LEFT)
        ttk.Entry(pf, textvariable=download_path).pack(
            side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        ttk.Button(pf, text="浏览", command=self._browse_path).pack(side=tk.LEFT)

        # ---- Cookie 配置 ----
        cf = ttk.LabelFrame(self.frame, text="Cookie 身份授权 (突破清晰度/解析合集必备)", padding=8)
        cf.pack(fill=tk.X, pady=10)

        for t, v in [("浏览器自动获取(推荐)", "browser"),
                     ("本地Netscape文件", "file"),
                     ("无Cookie(受限)", "none")]:
            ttk.Radiobutton(cf, text=t, value=v, variable=cookie_method,
                            command=on_cookie_change).pack(anchor=tk.W, pady=2)

        self._cookie_subframe = ttk.Frame(cf)
        self._cookie_subframe.pack(fill=tk.X, pady=5)

        # 保存引用以支持动态切换
        self._download_path = download_path
        self._cookie_method = cookie_method
        self._browser_var = browser_var
        self._cookie_file_var = cookie_file_var
        self._on_cookie_change = on_cookie_change

        # ---- 保存按钮 ----
        ttk.Button(self.frame, text="保存设置", command=on_save).pack(pady=10)

        # 初始构建子面板
        self._rebuild_cookie_subframe()

        # pack 到父容器
        self.frame.pack(fill=tk.BOTH, expand=True)

    def _browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self._download_path.set(path)

    def rebuild_cookie_subframe(self):
        """外部调用，当 cookie_method 改变时更新子面板。"""
        self._rebuild_cookie_subframe()

    def _rebuild_cookie_subframe(self):
        for w in self._cookie_subframe.winfo_children():
            w.destroy()

        method = self._cookie_method.get()
        if method == "browser":
            ttk.Label(self._cookie_subframe, text="浏览器:").pack(side=tk.LEFT, padx=5)
            for text, val in [("Chrome", "chrome"), ("Edge", "edge"), ("Firefox", "firefox")]:
                ttk.Radiobutton(self._cookie_subframe, text=text, value=val,
                                variable=self._browser_var).pack(side=tk.LEFT, padx=3)
            ttk.Label(self._cookie_subframe, text="(使用前请关闭浏览器)",
                      foreground="gray").pack(side=tk.LEFT, padx=10)

        elif method == "file":
            inner = ttk.Frame(self._cookie_subframe)
            inner.pack(fill=tk.X)
            ttk.Label(inner, text="Netscape文件:").pack(side=tk.LEFT)
            ttk.Entry(inner, textvariable=self._cookie_file_var, width=50).pack(
                side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            ttk.Button(inner, text="浏览", command=self._browse_cookie_file).pack(side=tk.LEFT)

        else:  # "none"
            ttk.Label(self._cookie_subframe, text="不使用Cookie，高画质将受限",
                      foreground="gray").pack(anchor=tk.W)

    def _browse_cookie_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            self._cookie_file_var.set(path)