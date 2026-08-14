"""
提取工具模块 — 字幕 / 封面 / 评论提取。
纯数据层，通过 progress_callback 报告进度。
"""

import json
import os
import re
import time
import urllib.request
from datetime import datetime

import requests


def extract_subtitle(video_url: str, output_dir: str, output_format: str,
                     cookie_str: str = "", progress_callback=None,
                     api_getter=None) -> dict:
    """
    提取视频字幕。
    output_format: "srt" | "txt" | "both"
    api_getter: 可选，用于获取视频信息的 API 对象（避免硬依赖 bili_api）。
    """
    result = {"success": False, "files": [], "message": ""}
    try:
        if progress_callback:
            progress_callback("正在获取视频信息...")

        entry, headers = _resolve_video(api_getter, video_url, cookie_str)
        title = _sanitize_filename(entry.title or "subtitle")
        cid = entry.cid
        bvid = entry.bvid

        if progress_callback:
            progress_callback("正在查找字幕...")

        # 诊断：如果 cid 为 0，说明获取视频信息时未解析到正确的 cid
        if not cid:
            if progress_callback:
                progress_callback(f"警告: cid=0, bvid={bvid} - 字幕可能不准确")

        # 使用 player/v2 API（带 cid），确保获取正确分P的字幕
        sub_api = f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}"
        sub_data = requests.get(sub_api, headers=headers, timeout=10).json()

        # 检查 API 是否返回错误
        api_code = sub_data.get("code", -1)
        if api_code != 0:
            err_msg = sub_data.get("message", "未知错误")
            if progress_callback:
                progress_callback(f"player/v2 API 返回错误 (code={api_code}): {err_msg}")

        # B站 API 可能使用 "subtitles" 或 "list" 字段名，同时尝试两者
        sub_info = sub_data.get("data", {}).get("subtitle", {}) or {}
        subtitles = sub_info.get("subtitles") or sub_info.get("list") or []

        if not subtitles:
            if progress_callback:
                progress_callback(
                    f"该视频没有可用字幕\n"
                    f"  bvid={bvid}  cid={cid}\n"
                    f"  如果视频确实有字幕，请确认 Cookie 是否有效（字幕API需要登录态）"
                )
            return {"success": False,
                    "message": "该视频没有字幕，或被风控拦截(字幕API需要有效Cookie)\n"
                               f"调试信息: bvid={bvid} cid={cid}"}

        # 优先 AI 字幕
        subtitle_url = next(
            (s.get("subtitle_url") or s.get("url")
             for s in subtitles if s.get("lan") in ("ai-zh", "ai")),
            None,
        )
        if not subtitle_url:
            subtitle_url = subtitles[0].get("subtitle_url") or subtitles[0].get("url")
        if subtitle_url and subtitle_url.startswith("//"):
            subtitle_url = "https:" + subtitle_url
        if not subtitle_url:
            return {"success": False, "message": "字幕链接为空"}

        if progress_callback:
            progress_callback(f"字幕链接: {subtitle_url[:120]}")

        # 构造视频专用 Referer（CDN 可能校验该字段）
        dl_headers = dict(headers)
        dl_headers["Referer"] = f"https://www.bilibili.com/video/{bvid}"
        dl_headers.setdefault("Origin", "https://www.bilibili.com")

        req = urllib.request.Request(subtitle_url, headers=dl_headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            sub_json = json.loads(resp.read().decode("utf-8"))
            if "body" in sub_json:
                sub_json = sub_json["body"]

        os.makedirs(output_dir, exist_ok=True)
        srt_path = os.path.join(output_dir, f"{title}.srt")
        lines = _json_to_srt(sub_json)

        if not lines:
            return {"success": False, "message": "字幕转换失败"}

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        result["files"].append(srt_path)

        if output_format in ("txt", "both"):
            txt_path = os.path.join(output_dir, f"{title}.txt")
            txt_lines = [
                l.strip() for l in lines
                if l.strip() and not re.match(r"^\d+$", l.strip()) and "-->" not in l
            ]
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(txt_lines))
            result["files"].append(txt_path)

        result["success"] = True
        result["message"] = "字幕提取成功"
    except Exception as e:
        result["message"] = f"提取失败: {e}"
    return result


def extract_cover(video_url: str, output_dir: str,
                  cookie_str: str = "", progress_callback=None,
                  api_getter=None) -> dict:
    """下载视频高清封面。"""
    try:
        if progress_callback:
            progress_callback("正在获取视频信息...")

        entry, headers = _resolve_video(api_getter, video_url, cookie_str)
        pic_url = entry.pic
        if not pic_url:
            return {"success": False, "message": "未找到封面链接"}

        title = _sanitize_filename(entry.title or "cover")
        os.makedirs(output_dir, exist_ok=True)
        save_path = os.path.join(output_dir, f"{title}_封面.jpg")

        if progress_callback:
            progress_callback("正在下载封面图像...")

        img_data = requests.get(pic_url, headers=headers, timeout=15).content
        with open(save_path, "wb") as f:
            f.write(img_data)
        return {"success": True, "files": [save_path], "message": "封面保存成功"}
    except Exception as e:
        return {"success": False, "message": f"封面获取失败: {e}"}


def extract_comments(video_url: str, output_dir: str,
                     cookie_str: str = "", max_pages: int = 20,
                     progress_callback=None,
                     api_getter=None) -> dict:
    """批量抓取视频评论。"""
    try:
        if progress_callback:
            progress_callback("正在获取视频信息...")

        entry, headers = _resolve_video(api_getter, video_url, cookie_str)
        aid = entry.aid
        title = _sanitize_filename(entry.title or "comments")

        comments = []
        page = 1

        while page <= max_pages:
            if progress_callback:
                progress_callback(f"正在抓取第 {page} 页评论...")

            api = f"https://api.bilibili.com/x/v2/reply?type=1&oid={aid}&pn={page}"
            res_data = requests.get(api, headers=headers, timeout=10).json()

            if res_data.get("code") != 0:
                break

            replies = res_data.get("data", {}).get("replies")
            if not replies:
                break

            for reply in replies:
                user = reply["member"]["uname"]
                content = reply["content"]["message"].replace("\n", "  ")
                likes = reply["like"]
                ctime = datetime.fromtimestamp(reply["ctime"]).strftime("%Y-%m-%d %H:%M")
                comments.append(f"[{ctime}] {user} (赞:{likes}): {content}")

            page += 1
            time.sleep(0.5)

        if not comments:
            return {"success": False, "message": "未抓取到任何评论"}

        os.makedirs(output_dir, exist_ok=True)
        save_path = os.path.join(output_dir, f"{title}_评论.txt")
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(f"视频：{entry.title}\n")
            f.write(f"抓取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            f.write("\n".join(comments))

        return {"success": True, "files": [save_path],
                "message": f"成功提取 {len(comments)} 条评论"}
    except Exception as e:
        return {"success": False, "message": f"评论获取失败: {e}"}


# ---- 内部辅助 ----

def _sanitize_filename(s: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", s)


def _build_headers(cookie_str: str) -> dict:
    h = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"}
    if cookie_str:
        h["Cookie"] = cookie_str
    return h


def _resolve_video(api_getter, video_url: str, cookie_str: str) -> tuple:
    """
    使用 api_getter 或内联方式获取视频信息。
    返回 (VideoEntry, headers)。
    """
    headers = _build_headers(cookie_str)
    if api_getter:
        entry = api_getter(video_url)
    else:
        from .bili_api import BiliAPI
        api = BiliAPI(lambda: cookie_str)
        entry = api.get_video_info(video_url)
    return entry, headers


def _raw_fetch_view(bvid: str, headers: dict) -> dict:
    """裸调用 view API，用于获取兜底字幕数据。"""
    api = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    resp = requests.get(api, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(data.get("message", "API error"))
    return data["data"]


def _json_to_srt(sub_json: list) -> list:
    lines = []
    for idx, item in enumerate(sub_json, 1):
        content = item.get("content", "").strip()
        if not content:
            continue

        frm = item["from"]
        to_val = item["to"]

        s_h, s_m = int(frm // 3600), int((frm % 3600) // 60)
        s_s = frm % 60
        e_h, e_m = int(to_val // 3600), int((to_val % 3600) // 60)
        e_s = to_val % 60

        start = f"{s_h:02d}:{s_m:02d}:{int(s_s):02d},{int((s_s - int(s_s)) * 1000):03d}"
        end = f"{e_h:02d}:{e_m:02d}:{int(e_s):02d},{int((e_s - int(e_s)) * 1000):03d}"

        lines.extend([str(idx), f"{start} --> {end}", content, ""])
    return lines