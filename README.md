# B站视频下载器 · 全能工具箱

基于 `yt-dlp` 的 B站视频/音频下载工具，附带字幕提取、封面下载、评论爬取等实用功能。GUI 界面由 Tkinter 构建。

## 功能概述

| 模块 | 说明 |
|---|---|
| **视频下载** | 支持最佳画质、仅音频(MP3)、720P、480P 四种模式 |
| **列表解析** | 自动识别分P / 合集(UGC Season) / 收藏夹，支持导出 TXT |
| **任务队列** | 批量管理，支持暂停/跳过/右键排序(置顶/上移/下移/删除) |
| **提取工具箱** | AI 字幕提取(SRT/TXT)、高清封面下载、批量评论爬取 |
| **Cookie 授权** | 浏览器自动获取 或 Netscape 文件导入，突破清晰度/风控限制 |

## 环境要求

### Python 包

```bash
pip install yt-dlp requests
```

### FFmpeg

视频合并与音频提取所必需。程序启动时自动检测：

1. 项目 `ffmpeg/` 目录下的 `ffmpeg.exe` + `ffprobe.exe`（优先）
2. 系统 PATH 中的 FFmpeg

[FFmpeg 官网下载](https://ffmpeg.org/download.html)

## 快速开始

### 源码运行

```bash
python v5.3.py
```

### 发行版（Windows）

下载打包好的 zip，解压后双击 `B站视频下载器.exe`，已内置 FFmpeg，开箱即用。

## Cookie 配置（重要）

字幕提取、高画质下载、合集解析均需要有效的 B站 Cookie，否则将被风控拦截。

推荐方式：**浏览器插件导出**

1. 在 Chrome/Edge 安装插件 **Get cookies.txt LOCALLY**
2. 打开 B站并登录账号，点击插件图标 → Export
3. 将导出的 `cookies.txt` 保存到本地
4. 在软件 **设置** 页选择 "本地Netscape文件" 并加载该文件

备选方式：**浏览器自动获取**（需先关闭浏览器）

## 自行打包

```bash
# 1. 确保 ffmpeg/ 目录下有 ffmpeg.exe 和 ffprobe.exe

pip install pyinstaller
pyinstaller B站视频下载器.spec
```

产物在 `dist/B站视频下载器/`，分发整个文件夹即可。

## 免责声明

本工具仅供个人学习和研究使用。使用者应遵守 B站用户协议及相关法律法规。禁止用于商业用途或侵犯他人权益的行为。作者不对任何滥用行为承担法律责任。

## 作者

linali_bdcn · [源码仓库](https://github.com/linali-bdcn/spider_bilibili)
