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
        下载文件（视频或音频）
        """
        try:
            response = requests.get(url, headers=self.headers, stream=True)
            response.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"文件已保存为 {file_path}")
        except requests.exceptions.RequestException as e:
            logging.error(f"下载出错: {e}")
        except Exception as e:
            logging.error(f"保存文件时出错: {e}")

    def match_urls(self, content):
        """
        从 HTML 内容中匹配音频和视频链接
        """
        audio_pattern = r'"baseUrl"\s*:\s*"(https://[^"]+?(?:[-_](?:1|nb2|x2)-1-)?30280\.m4s[^"]+)"'
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


# 示例用法
if __name__ == "__main__":
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
        "Cookie":"None"
    }
    url = "https://www.bilibili.com/video/BV1MvF5ejEdA/"

    downloader = BilibiliDownloader()
    downloader.download_video_and_audio(url, headers)
