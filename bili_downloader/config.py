"""
配置持久化模块 — 负责 JSON 配置文件的读写。
与 UI 无关，可独立测试。
"""

import json
import os
from typing import Any

CONFIG_FILE = "bili_downloader_config.json"

DEFAULT_CONFIG = {
    "download_path": os.path.join(os.path.expanduser("~"), "Downloads"),
    "cookie_method": "browser",
    "browser": "chrome",
    "cookie_file": "",
    "mode": "best",
}


class ConfigStore:
    """线程不安全的轻量配置存储，仅用于 UI 主线程。"""

    def __init__(self, filepath: str = CONFIG_FILE):
        self._filepath = filepath
        self._data: dict = {**DEFAULT_CONFIG}
        self.load()

    def load(self) -> dict:
        try:
            if os.path.exists(self._filepath):
                with open(self._filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self._data.update(loaded)
        except Exception:
            pass
        return self._data

    def save(self) -> None:
        try:
            with open(self._filepath, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def update(self, mapping: dict) -> None:
        self._data.update(mapping)

    def as_dict(self) -> dict:
        return dict(self._data)