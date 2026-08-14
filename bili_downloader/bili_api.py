"""
B站 API 调用模块 — 视频信息查询 + 列表解析。
纯数据层，不涉及任何 UI。
"""

import re
from typing import List, Optional

import requests

# ---- 数据结构 ----

class VideoEntry:
    """单个视频条目的统一表示。"""
    __slots__ = ("index", "title", "url", "duration", "bvid", "cid", "aid", "pic")

    def __init__(self, index: int = 0, title: str = "", url: str = "",
                 duration: int = 0, bvid: str = "", cid: int = 0,
                 aid: int = 0, pic: str = ""):
        self.index = index
        self.title = title
        self.url = url
        self.duration = duration
        self.bvid = bvid
        self.cid = cid
        self.aid = aid
        self.pic = pic

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "title": self.title,
            "url": self.url,
            "duration": self.duration,
            "bvid": self.bvid,
            "cid": self.cid,
            "aid": self.aid,
            "pic": self.pic,
        }


class PlaylistResult:
    """列表解析结果。"""
    __slots__ = ("title", "videos")

    def __init__(self, title: str = "视频列表", videos: Optional[List[VideoEntry]] = None):
        self.title = title
        self.videos = videos or []


# ---- 内部工具 ----

def _extract_bvid(url: str) -> Optional[str]:
    m = re.search(r"BV[a-zA-Z0-9]+", url)
    return m.group(0) if m else None


def _extract_page(url: str) -> int:
    m = re.search(r"p=(\d+)", url)
    return int(m.group(1)) if m else 1


def _build_headers(cookie_str: str) -> dict:
    h = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"}
    if cookie_str:
        h["Cookie"] = cookie_str
    return h


def _sanitize_filename(s: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", s)


# ---- 公开 API ----

class BiliAPI:
    """B站 API 调用入口。"""

    def __init__(self, cookie_str_getter=None):
        """
        cookie_str_getter: 可调用对象，返回 Cookie 字符串。
        传入 None 时每次调用内部生成。
        """
        self._cookie_getter = cookie_str_getter or (lambda: "")

    # ---------- 单视频信息 ----------

    def get_video_info(self, url: str) -> VideoEntry:
        """根据视频 URL 获取单个视频信息。"""
        bvid = _extract_bvid(url)
        if not bvid:
            raise Exception("无效的B站视频URL")

        page = _extract_page(url)
        headers = _build_headers(self._cookie_getter())
        raw = self._fetch_view_api(bvid, headers)

        pages = raw.get("pages", [])
        entry = VideoEntry(
            index=page,
            title=raw.get("title", bvid),
            url=url,
            bvid=bvid,
            aid=raw.get("aid", 0),
            pic=raw.get("pic", ""),
        )

        if pages:
            if page < 1 or page > len(pages):
                page = 1
            pg = pages[page - 1]
            entry.cid = pg.get("cid", 0)
            entry.duration = pg.get("duration", 0)
            if len(pages) > 1:
                entry.title = f"{entry.title}_P{page}_{pg.get('part', '')}"
        # 如果 pages 为空或 cid 仍为 0，尝试从顶层获取（兼容某些特殊视频类型）
        if not entry.cid:
            entry.cid = raw.get("cid", 0)
        return entry

    # ---------- 列表解析 ----------

    def parse_playlist(self, url: str) -> PlaylistResult:
        """
        解析视频列表（分P / 合集 / 收藏夹）。
        优先使用 B站 API 逐页解析，失败时回退 yt-dlp。
        """
        bvid = _extract_bvid(url)
        headers = _build_headers(self._cookie_getter())

        if bvid:
            try:
                raw = self._fetch_view_api(bvid, headers)
                return self._parse_from_view_api(raw, bvid)
            except Exception:
                pass

        # 回退 yt-dlp 扁平提取
        return self._parse_via_ytdlp(url)

    @staticmethod
    def _fetch_view_api(bvid: str, headers: dict) -> dict:
        api = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        resp = requests.get(api, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(data.get("message", "API 返回异常"))
        return data["data"]

    @staticmethod
    def _parse_from_view_api(raw: dict, bvid: str) -> PlaylistResult:
        """从 view API 的返回数据中提取列表。"""
        title = raw.get("title", "视频列表")
        videos: List[VideoEntry] = []

        # 尝试合集（ugc_season）
        ugc = raw.get("ugc_season")
        if ugc:
            title = ugc.get("title", title)
            idx = 1
            for section in ugc.get("sections", []):
                for ep in section.get("episodes", []):
                    arc = ep.get("arc", {})
                    ep_bvid = ep.get("bvid") or arc.get("bvid")
                    if ep_bvid:
                        videos.append(VideoEntry(
                            index=idx,
                            title=ep.get("title", f"视频{idx}"),
                            url=f"https://www.bilibili.com/video/{ep_bvid}",
                            duration=arc.get("duration", 0),
                            bvid=ep_bvid,
                        ))
                        idx += 1
            return PlaylistResult(title=title, videos=videos)

        # 分P
        pages = raw.get("pages", [])
        for pg in pages:
            videos.append(VideoEntry(
                index=pg.get("page", 0),
                title=pg.get("part", f"P{pg.get('page', 0)}"),
                url=f"https://www.bilibili.com/video/{bvid}?p={pg.get('page', 0)}",
                duration=pg.get("duration", 0),
                bvid=bvid,
                cid=pg.get("cid", 0),
            ))
        return PlaylistResult(title=title, videos=videos)

    def _parse_via_ytdlp(self, url: str) -> PlaylistResult:
        """通过 yt-dlp 的扁平列表提取解析合集/收藏夹。"""
        import yt_dlp
        opts = {
            "quiet": True,
            "extract_flat": "in_playlist",
            "ignoreerrors": True,
            "http_headers": {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.bilibili.com/",
            },
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        entries = info.get("entries") if info else None
        if not entries:
            raise Exception("未能解析出视频列表")

        title = info.get("title", "播放列表")
        videos: List[VideoEntry] = []
        for i, entry in enumerate(entries):
            if not entry:
                continue
            v_url = entry.get("url") or entry.get("webpage_url")
            if not v_url and "id" in entry:
                v_url = f"https://www.bilibili.com/video/{entry['id']}"
            if v_url:
                videos.append(VideoEntry(
                    index=i + 1,
                    title=entry.get("title", f"视频{i+1}"),
                    url=v_url,
                    duration=entry.get("duration") or 0,
                ))

        return PlaylistResult(title=title, videos=videos)