"""
Cookie 提供器 — 统一 browser / file / none 三种模式。
同时输出 yt-dlp 格式和 requests 格式的 Cookie。
"""

import os
from typing import Tuple


class CookieProvider:
    """封装 Cookie 获取逻辑，不依赖 UI。"""

    def __init__(self, method: str = "browser", browser: str = "chrome",
                 cookie_file: str = ""):
        self.method = method          # "browser" | "file" | "none"
        self.browser = browser        # "chrome" | "edge" | "firefox"
        self.cookie_file = cookie_file

    # ---- yt-dlp 用 ----
    def apply_to_ydl_opts(self, opts: dict) -> None:
        """将 Cookie 配置写入 yt-dlp opts 字典（原地修改）。"""
        if self.method == "browser":
            opts["cookiesfrombrowser"] = (self.browser,)
        elif self.method == "file" and os.path.exists(self.cookie_file):
            opts["cookiefile"] = self.cookie_file
        # "none" 不写入任何字段

    # ---- requests 用 ----
    def get_requests_cookie(self) -> str:
        """返回可直接放入 headers['Cookie'] 的字符串。"""
        if self.method == "file" and os.path.exists(self.cookie_file):
            return self._parse_netscape_file(self.cookie_file)
        elif self.method == "browser":
            return self._extract_from_browser(self.browser)
        return ""

    # ---- 内部 ----
    @staticmethod
    def _parse_netscape_file(filepath: str) -> str:
        cookies = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split("\t")
                    if len(parts) >= 7:
                        cookies.append(f"{parts[5]}={parts[6]}")
        except Exception:
            pass
        return "; ".join(cookies)

    @staticmethod
    def _extract_from_browser(browser_name: str) -> str:
        try:
            import yt_dlp.cookies
            cj = yt_dlp.cookies.extract_cookies_from_browser(browser_name)
            return "; ".join(
                f"{c.name}={c.value}"
                for c in cj if "bilibili.com" in c.domain
            )
        except Exception:
            return ""