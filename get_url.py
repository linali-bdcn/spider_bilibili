import re
import requests
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class BilibiliDownloader:
    def __init__(self):
        self.headers = None  # 请求头
        self.url = None  # 视频 URL
        self.name = None # 视频名称

    def get_name(self, html):
        """
        从 HTML 中提取视频标题
        """
        match = re.findall(r'title\s*=\s*"([^"]+)"', html)
        if match:
            title = match[0]
            logging.info(f"提取到的标题: {title}")
            return title
        else:
            logging.warning("无法匹配到标题")
            return None

    def get_p(self,url):
        """
        从 URL 中提取 分p 参数的值
        :param url: 输入的 URL
        :return: p 参数的值（整数），如果未找到则返回 None
        """
        # 正则表达式匹配 p={数字}
        match = re.search(r'[?&]p=(\d+)', url)
        if match:
            return "【P:"+str(match.group(1))+"】| "  # 返回匹配到的数字并转换为整数
        return None  # 如果未找到，返回 None"""

    def safe_filename(self, filename):
        """
        处理文件名，移除非法字符并截断过长文件名
        """
        filename = re.sub(r'[\\/*?:"<>|]', '', filename)
        if len(filename) > 255:
            filename = filename[:255]
        return filename

    def download_file(self, url, file_path):
        """
        下载文件（视频或音频）并显示进度

        参数:
            url (str): 要下载的文件URL
            file_path (str): 保存文件的本地路径
        """
        try:
            # 发起HTTP请求，使用stream=True参数以流式方式下载大文件
            # 这样可以分块下载文件，而不是一次性加载整个文件到内存
            response = requests.get(url, headers=self.headers, stream=True)
            # 检查请求是否成功，如果状态码不是2xx，将引发异常
            response.raise_for_status()

            # 获取文件总大小（字节数）
            # content-length头包含文件的总字节数，如果不存在则默认为0
            total_size = int(response.headers.get('content-length', 0))
            # 初始化已下载字节计数器
            downloaded = 0

            # 以二进制写入模式打开文件
            with open(file_path, 'wb') as f:
                # 分块下载文件，每块8KB (8192字节)
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # 过滤掉保持连接alive的空块
                        # 将下载的数据块写入文件
                        f.write(chunk)
                        # 更新已下载字节数
                        downloaded += len(chunk)

                        # 计算并更新下载进度
                        # 检查是否设置了进度回调函数且文件大小有效
                        if hasattr(self, 'progress_callback') and total_size > 0:
                            # 计算下载进度百分比
                            progress = int(downloaded * 100 / total_size)
                            # 调用进度回调函数通知界面更新进度
                            self.progress_callback(progress)

            # 下载完成，记录日志
            logging.info(f"文件已成功保存为 {file_path}")
        except requests.exceptions.RequestException as e:
            # 处理网络请求相关错误（如连接失败、超时等）
            logging.error(f"下载出错: {e}")
            # 可能需要在这里重新抛出异常，让上层函数知道下载失败
            raise
        except Exception as e:
            # 处理其他可能的错误（如文件写入权限问题等）
            logging.error(f"保存文件时出错: {e}")
            # 可能需要在这里重新抛出异常，让上层函数知道下载失败
            raise

    def match_urls(self, content):
        """
        从 HTML 内容中匹配音频和视频链接
        """
        audio_pattern = r'"baseUrl"\s*:\s*"(https://[^"]+?(?:[-_](?:1|nb2|x2)-1-)?30280\.m4s[^"]+)"'
        audio_pattern = r'"baseUrl"\s*:\s*"(https://[^"]+?(?:[-_](?:1|nb2|x2)-1-)?30216\.m4s[^"]+)"'
        #audio_pattern = r'"(?:baseUrl|base_url|backupUrl|backup_url)"\s*:\s*"(https?:\/\/[^"]+\.m4s[^"]*)"'
        video_pattern = r'https://[^"]+?/\d+-1-(?:10\d{4})\.m4s[^"]*'

        audio_matches = re.findall(audio_pattern, content)
        video_matches = re.findall(video_pattern, content)

        return audio_matches, video_matches

    def save_links(self, audio_matches, video_matches, name):
        """
        保存匹配到的链接到文件
        """
        links_file_path = os.path.join(name, "links.txt")
        with open(links_file_path, "w", encoding="utf-8") as f:
            f.write("音频链接:\n")
            for link in audio_matches:
                f.write(link + "\n")
            f.write("\n视频链接:\n")
            for link in video_matches:
                f.write(link + "\n")
        logging.info(f"链接已保存到 {links_file_path}")

    def get_html(self, url):
        """
        获取网页内容
        """
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            response.encoding = "utf-8"
            return response.text
        except requests.exceptions.RequestException as e:
            logging.error(f"请求出错: {e}")
            return None
    def save_html(self, name, html):
        """
        保存
        """
        links_file_path = os.path.join(name, "html.txt")  # 保存获取的页面内容纯html
        with open(links_file_path, "w", encoding="utf-8") as f:
            f.write("网页html:\n")
            f.write(html)
    def download_video_and_audio(self, url, headers):
        """
        下载视频和音频
        """
        self.headers = headers
        self.url = url

        logging.info("正在运行…")
        # 获取网页内容
        html = self.get_html(url)

        if not html:
            return

        # 提取标题
        if self.get_p(url):#分批操作
            title = self.get_p(url) + self.get_name(html)
        else:
            title = self.get_name(html)
        if not title:
            return
        title = self.safe_filename(title)

        # 创建保存目录
        os.makedirs(title, exist_ok=True)

        # 匹配链接
        audio_matches, video_matches = self.match_urls(html)
        if not audio_matches and not video_matches:
            logging.warning("未找到音频或视频链接")
            return

        # 保存链接
        self.save_links(audio_matches, video_matches, title)
        self.save_html(title, html)  # 保存网页html

        # 下载音频
        if audio_matches:
            audio_url = audio_matches[0]

            audio_path = os.path.join(title, f"{title}.mp3")
            logging.info("开始下载音频...")
            self.download_file(audio_url, audio_path)

        # 下载视频
        if video_matches:
            video_url = video_matches[0]
            video_path = os.path.join(title, f"{title}.mp4")
            logging.info("开始下载视频...")
            self.download_file(video_url, video_path)

        logging.info("下载完成，请查看文件。")

    def set_progress_callback(self, callback):
        "进度条关于UI的初始设置"
        self.progress_callback = callback


# 示例用法
if __name__ == "__main__":
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
        "Cookie":"buvid4=592A5351-4318-B4D2-8737-FAFC6CADD10004748-023071120-Z%2FAbw9J6z9%2FgOsaYTan8rA%3D%3D; buvid_fp_plain=undefined; is-2022-channel=1; enable_web_push=DISABLE; FEED_LIVE_VERSION=V_WATCHLATER_PIP_WINDOW3; header_theme_version=CLOSE; buvid3=AC4714D5-9AEB-BDFB-D891-DDB2408AC8B544600infoc; b_nut=1728471644; _uuid=C5C14C54-BB5F-CCD3-EC65-DE9D2FF484A145253infoc; rpdid=|(J~RYu|Rk~R0J'u~JJk))mlR; DedeUserID=700258188; DedeUserID__ckMd5=a2f0bc6e77c418a7; LIVE_BUVID=AUTO2617375534686590; enable_feed_channel=DISABLE; hit-dyn-v2=1; PVID=1; fingerprint=49b994572c21d455f503a8d6bdb7136f; buvid_fp=49b994572c21d455f503a8d6bdb7136f; CURRENT_QUALITY=80; home_feed_column=5; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NDA4Mjk4OTksImlhdCI6MTc0MDU3MDYzOSwicGx0IjotMX0.bJV1N0JWd1JowmrVbh7A9wLNuHCQyWcj9uTmvOOjgsU; bili_ticket_expires=1740829839; b_lsid=12C787A2_1954AF5F7D4; browser_resolution=1762-866; bmg_af_switch=1; bmg_src_def_domain=i1.hdslb.com; SESSDATA=080824de%2C1756271397%2Ca4028%2A22CjDGBFQYojbQlioysZu7ew3-UJ_M6tqS6hSOHCDvS01qNBgHO67B05iyha18AJ4kyhcSVkhTXzR6cENvWHRpaF9CdEZrZ2lpVW92M0FPVkEwRXY0ZUs4dWFYenlWT3FzYkJueUZMaW5ldFhES3RRRlVKYjVFRmtJM2tLNXRueVp4NzZzN21BTHFnIIEC; bili_jct=f9a4224386f7a9424efef42cf0e7f622; sid=8643pvcr; bp_t_offset_700258188=1038870997408677888; CURRENT_FNVAL=4048"
    }
    url = "https://www.bilibili.com/video/BV1GXKpetEFZ?t=0.5&p=3"

    downloader = BilibiliDownloader()
    downloader.download_video_and_audio(url, headers)