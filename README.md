简洁的介绍：已实现列表下载功能，音频和低码率视屏下载，同时提供高清码率下载（需自己提供cookie）

此工具分为前段和后端分离式，采用UI和功能模块各自独立运行，提高了效率。

下载类函数：
  get_name(self, html)  
      - 功能：从 HTML 内容中提取视频标题
      - 使用正则表达式匹配 title 标签中的内容
      - 返回提取到的标题，如果没有匹配到则返回 None

  safe_filename(self, filename)
      - 功能：处理文件名使其安全可用
      - 移除文件名中的非法字符（如 /*?:"<>|）
      - 如果文件名超过 255 字符则进行截断
      - 返回处理后的文件名
  
  download_file(self, url, file_path)
      - 功能：下载文件（视频或音频）
      - 使用 requests 库下载指定 URL 的文件
      - 以二进制方式写入到指定路径
      - 支持大文件分块下载

  match_urls(self, content)
      - 功能：从 HTML 内容中匹配音频和视频的下载链接
      - 使用正则表达式分别匹配音频和视频的 URL
      - 返回两个列表，分别包含音频和视频链接

  save_links(self, audio_matches, video_matches, name)
      - 功能：将匹配到的音频和视频链接保存到文件
      - 在指定目录下创建 links.txt 文件
      - 分别保存音频和视频链接

  get_html(self, url)
      - 功能：获取网页的 HTML 内容
      - 发送 GET 请求获取页面内容
      - 设置编码为 utf-8
      - 返回页面的文本内容，如果请求失败则返回 None

  download_video_and_audio(self, url, headers)
      - 功能：主要的下载处理函数
      - 设置请求头和 URL
      - 获取网页内容
      - 提取视频标题
      - 创建保存目录
      - 匹配下载链接
      - 下载音频和视频文件
      - 整个下载过程的协调和控制

主GUI：
    一个简单的窗口直接输入视频链接即可
    目前属于一个简陋版
预计将添加更多功能
