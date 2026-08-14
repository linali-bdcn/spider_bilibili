# B站视频下载器 + 提取工具箱（v5.0.0）

基于 `yt-dlp` 的 B站视频下载与内容提取工具，提供 Tkinter 图形界面。

## 功能

- **视频下载** — 支持单个视频、多P合集、合集列表，自定义画质/格式
- **字幕提取** — 提取 CC 字幕并保存为 SRT 或 TXT 格式
- **封面提取** — 下载视频封面图片
- **评论抓取** — 抓取视频热门评论
- **Cookie 管理** — 支持三种模式：浏览器自动提取 / 本地文件 / 无 Cookie
- **下载队列** — 暂停/取消/重试，实时进度展示
- **全局日志** — 提取操作日志集中显示

## 环境要求

- Python 3.9+
- ffmpeg（可选，但**强烈建议**，用于合并高清视频的音视频流）

### 关于 ffmpeg

本仓库**不含 ffmpeg**（体积约 260MB，太大不适合放源码库）。程序会自动在
`ffmpeg-7.1.1-essentials_build/bin/` 目录查找 `ffmpeg.exe`。

获取方式（二选一）：

1. **下载含 ffmpeg 的完整发布包** — 前往 [Releases](../../releases) 下载
   `TK-B站下载器-v5.0.0-full.zip`，解压即用。
2. **手动下载 ffmpeg** — 从 [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
   下载 `ffmpeg-release-essentials.zip`，解压后将文件夹重命名为
   `ffmpeg-7.1.1-essentials_build` 放到项目根目录即可（也可只把 `ffmpeg.exe`
   放进 `ffmpeg-7.1.1-essentials_build/bin/`）。

## 安装

```bash
pip install -r requirements.txt
```

## 快速启动

```bash
python main.py
```

或双击 `启动文件.bat`。

## Cookie 配置

程序需要 B站 Cookie 才能下载高清视频和访问会员内容。

**三种模式：**

| 模式 | 说明 |
|------|------|
| 浏览器自动提取 | 从本地浏览器（Chrome/Edge/Firefox）自动读取 B站 Cookie |
| 本地文件 | 从项目根目录 `bilibili_cookies.txt` 读取 Netscape 格式 Cookie |
| 无 Cookie | 不发送 Cookie（部分视频可能受限） |

**获取 Cookie 文件的方法：**

1. 安装浏览器扩展 [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
2. 访问 B站并登录
3. 点击扩展图标，选择 Export → Export As
4. 将导出的文件重命名为 `bilibili_cookies.txt`，放到项目根目录

## 目录结构

```
├── main.py                          # 入口
├── requirements.txt
├── 启动文件.bat
├── bili_downloader/                 # 核心包
│   ├── __init__.py
│   ├── config.py                    # 配置读写
│   ├── cookie_provider.py           # Cookie 获取
│   ├── bili_api.py                  # B站 API 封装
│   ├── extra_extractor.py           # 字幕/封面/评论提取
│   ├── download_manager.py          # 下载引擎（yt-dlp）
│   └── ui/                          # GUI 子包
│       ├── __init__.py
│       ├── app.py                   # 主窗口
│       ├── download_tab.py          # 下载面板
│       ├── tools_tab.py             # 工具面板
│       ├── settings_tab.py          # 设置面板
│       ├── queue_panel.py           # 队列树
│       ├── list_window.py           # 合集列表弹窗
│       └── log_panel.py             # 日志面板
├── docs/
│   └── MAINTENANCE.md               # 维护说明书
└── legacy/                          # 历史单文件版本（V3/V4/V5）
```

## 免责声明

本工具仅供个人学习与交流使用。请遵守 B站用户协议，勿用于商业用途或侵犯他人权益。
