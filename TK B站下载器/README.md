# B站视频下载器 · 全能工具箱

基于 `yt-dlp` 的 B站视频/音频下载工具，附带字幕提取、封面下载、评论爬取等实用功能。GUI 界面由 Tkinter 构建。

## 功能

- **视频/音频下载** — 支持最佳画质、仅音频(MP3)、720P、480P 四种模式
- **列表解析** — 自动识别分P / 合集(UGC Season) / 收藏夹，支持导出 TXT
- **任务队列** — 批量管理，支持暂停/跳过/拖拽排序
- **提取工具箱** — AI 字幕提取(SRT/TXT)、高清封面下载、批量评论爬取
- **Cookie 授权** — 支持浏览器自动获取(Chrome/Edge/Firefox)或 Netscape 文件，突破清晰度限制
- **FFmpeg 自动检测** — 启动时自动识别系统或内置 FFmpeg，无需手动配置环境变量

## 截图

> 待补充

## 依赖

### Python 包

```bash
pip install yt-dlp requests
```

### 系统依赖

| 组件 | 说明 |
|---|---|
| **FFmpeg** | 合并视频音频流、提取 MP3 所必需 |

FFmpeg 获取方式：

- [官网下载](https://ffmpeg.org/download.html) `ffmpeg.exe` 和 `ffprobe.exe`
- 放入项目同级 `ffmpeg/` 目录即可自动识别
- 或自行安装到系统 PATH

## 使用

```bash
python V5.py
```

**发行版（Windows）**：前往 [Releases](https://github.com/linali-bdcn/spider_bilibili/releases) 下载打包好的 zip，解压后双击 `B站视频下载器.exe`，已内置 FFmpeg，开箱即用。

## 自行打包

```bash
# 1. 将 ffmpeg.exe 和 ffprobe.exe 放入项目 ffmpeg/ 目录

# 2. 安装 PyInstaller
pip install pyinstaller

# 3. 打包
pyinstaller --onedir --windowed --name "B站视频下载器" --add-data "ffmpeg;ffmpeg" V5.py
```

产物在 `dist/B站视频下载器/`。

## 免责声明

本工具仅供个人学习和研究使用，使用者应遵守 B站用户协议及相关法律法规。禁止将本工具用于任何商业用途或侵犯他人权益的行为。作者不对任何滥用行为承担法律责任。