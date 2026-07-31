import re
from tkinter import messagebox
import requests
import os
import logging
import time
import tkinter as tk
import threading

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class BilibiliDownloader:
    def __init__(self):
        self.url = None  # 视频 URL
        self.headers = None
        self.name = None  # 视频名称
        self.cookies = None # COOKIES yao12
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

    def get_p(self, url, chose):
        """
        从 URL 中提取 p={数字}和视频的总分P数
        :param url: 视频URL
        :param chose: 选择返回类型：1返回当前P号格式化字符串，2返回总P数，3返回当前P号和总P数的元组
        :return: 根据chose参数返回不同格式的结果
        """
        html = self.get_html(url)
        if not html:
            return None

        # 正则表达式匹配 p={数字}
        match = re.search(r'[?&]p=(\d+)', url)  # 获取当前分P的值
        current_p = int(match.group(1)) if match else 1  # 如果没有指定，默认为第1P

        # 匹配pages数组
        pages_match = re.search(r'"pages":\s*(\[.*?\])', html, re.DOTALL)
        if not pages_match:
            return 0 if chose == 1 else (1 if chose == 2 else (1, 1))

        # 计算总P数
        total_p = len(re.findall(r'"page":\s*\d+', pages_match.group(1)))
        if total_p == 0:
            return 0

        if chose == 1:
            # 返回格式化的当前P号字符串
            return f"【P:{current_p}】 "
        elif chose == 2:
            # 返回总P数
            return total_p
        elif chose == 3:
            # 返回当前P号和总P数的元组
            return (current_p, total_p)

        return None  # 如果参数无效，返回None

    def get_p_total(self, url):
        """
        从HTML中直接提取视频所有分P的标题和链接

        :param url: 视频URL
        :return: 包含(分P序号, 分P链接, 分P标题)的三元组列表
        """
        # 获取网页内容
        html = self.get_html(url)
        if not html:
            logging.warning("无法获取视频页面内容")
            return []

        # 从URL中提取BV号
        bv_match = re.search(r'bilibili\.com/video/(BV[^/?]+)', url)
        if not bv_match:
            logging.warning("无法从URL中提取BV号")
            return []

        bv_id = bv_match.group(1)
        base_url = f"https://www.bilibili.com/video/{bv_id}"

        # 使用正则表达式匹配pages数组
        pages_match = re.search(r'"pages"\s*:\s*(\[.*?\])', html, re.DOTALL)
        if not pages_match:
            logging.warning("无法找到分P信息")
            return []

        pages_json = pages_match.group(1)

        # 匹配每个分P的信息
        result = []
        page_pattern = r'"page"\s*:\s*(\d+)[^}]*"part"\s*:\s*"([^"]+)"'
        matches = re.findall(page_pattern, pages_json)

        for page, part in matches:
            p = int(page)
            p_url = f"{base_url}?p={p}"
            title = part.strip()

            # 添加到结果列表
            result.append((p, p_url, title))
            logging.info(f"从HTML中提取到P{p}标题: {title}")

        return result

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
            response = requests.get(url, headers=self.headers, stream=True)
            response.raise_for_status()

            # 获取文件总大小
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            # 以二进制写入模式打开文件
            with open(file_path, 'wb') as f:
                # 分块下载文件，每块8KB
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # 过滤掉空块
                        # 写入数据块
                        f.write(chunk)
                        downloaded += len(chunk)

                        # 更新进度
                        if hasattr(self, 'progress_callback') and total_size > 0:
                            progress = int(downloaded * 100 / total_size)
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
        # 音频匹配模式
        audio_pattern = r'"baseUrl"\s*:\s*"(https://[^"]+?(?:[-_](?:1|nb2|x2)-1-)?30216\.m4s[^"]+)"'

        # 视频匹配模式 - 优先匹配高清视频
        video_patterns = [
            r'"baseUrl"\s*:\s*"(https://[^"]+?(?:[-_](?:1|nb2|x2)-1-)?120\d{3}\.m4s[^"]+)"',  # 高清视频
            r'"baseUrl"\s*:\s*"(https://[^"]+?(?:[-_](?:1|nb2|x2)-1-)?116\d{3}\.m4s[^"]+)"',  # 中等清晰度
            r'"baseUrl"\s*:\s*"(https://[^"]+?(?:[-_](?:1|nb2|x2)-1-)?80\d{3}\.m4s[^"]+)"',  # 标清视频
            r'"baseUrl"\s*:\s*"(https://[^"]+?(?:[-_](?:1|nb2|x2)-1-)?64\d{3}\.m4s[^"]+)"',  # 低清视频
        ]

        audio_matches = re.findall(audio_pattern, content)

        # 尝试按优先级匹配视频链接
        video_matches = []
        for pattern in video_patterns:
            matches = re.findall(pattern, content)
            if matches:
                video_matches = matches
                break

        # 如果上述模式都未匹配，尝试使用旧的匹配模式
        if not video_matches:
            video_pattern = r'"baseUrl"\s*:\s*"(https://[^"]+?/\d+-1-(?:10\d{4})\.m4s[^"]+)"'
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
            print(response, "\n\n\n")
            response.raise_for_status()
            response.encoding = "utf-8"

            return response.text
        except requests.exceptions.RequestException as e:
            logging.error(f"请求出错: {e}")
            return None

    def save_html(self, name, html):
        """
        保存HTML到文件
        """
        links_file_path = os.path.join(name, "html.txt")  # 保存获取的页面内容纯html
        with open(links_file_path, "w", encoding="utf-8") as f:
            f.write("网页html:\n")
            f.write(html)

    def download_video_and_audio(self, url, headers, download_mode="audio_only"):
        """
        下载视频和音频

        参数:
            url (str): 视频URL
            headers (dict): 请求头
            download_mode (str): 下载模式
                - "audio_only": 只下载音频
                - "video_only": 只下载视频
                - "separate": 音视频分别下载
                - "merged": 下载并合并音视频
        """
        self.headers = headers
        self.url = url

        logging.info(f"正在运行，下载模式: {download_mode}...")
        # 获取网页内容
        html = self.get_html(url)

        if not html:
            raise Exception("无法获取网页内容")

        # 提取标题
        title = self.get_name(html)
        if not title:
            raise Exception("无法提取视频标题")
        title = self.safe_filename(title)

        # 获取分P信息
        p_info = self.get_p(url, 3)  # 获取当前P号和总P数
        current_p, total_p = p_info if p_info else (1, 0)

        # 如果存在分P，则获取当前分P的标题作为文件名
        file_title = title
        if total_p > 0:
            # 获取所有分P信息
            parts_info = self.get_p_total(url)
            # 查找当前P的标题
            for p, _, p_title in parts_info:
                if p == current_p:
                    file_title = p_title
                    break
        file_title = self.safe_filename(file_title)
        
        # 创建保存目录 - 只使用主标题作为文件夹名
        os.makedirs(title, exist_ok=True)

        # 匹配链接
        audio_matches, video_matches = self.match_urls(html)
        if not audio_matches and not video_matches:
            logging.warning("未找到音频或视频链接")
            raise Exception("未找到音频或视频链接")

        # 保存链接
        self.save_links(audio_matches, video_matches, title)
        self.save_html(title, html)  # 保存网页html

        # 文件路径
        audio_path = os.path.join(title, f"{file_title}.mp3")
        video_path = os.path.join(title, f"{file_title}.mp4")
        merged_path = os.path.join(title, f"{file_title}_merged.mp4")

        # 根据下载模式执行不同的下载操作
        if download_mode in ["audio_only", "separate", "merged"]:
            # 下载音频
            if audio_matches:
                audio_url = audio_matches[0]
                logging.info(f"开始下载音频... 保存为: {file_title}.mp3")
                self.download_file(audio_url, audio_path)
            else:
                logging.warning("未找到音频链接")
                if download_mode == "merged":
                    raise Exception("未找到音频链接，无法进行合并")

        if download_mode in ["video_only", "separate", "merged"]:
            # 下载视频
            if video_matches:
                video_url = video_matches[0]
                logging.info(f"开始下载视频... 保存为: {file_title}.mp4")
                self.download_file(video_url, video_path)
            else:
                logging.warning("未找到视频链接")
                if download_mode == "merged":
                    raise Exception("未找到视频链接，无法进行合并")

        # 如果是合并模式，执行合并操作
        if download_mode == "merged" and os.path.exists(audio_path) and os.path.exists(video_path):
            logging.info("开始合并音视频...")
            if self.merge_audio_video(audio_path, video_path, merged_path):
                logging.info(f"音视频合并成功: {merged_path}")
                # 可选：删除原始的音频和视频文件
                # os.remove(audio_path)
                # os.remove(video_path)
            else:
                logging.error("音视频合并失败")

        logging.info("下载完成，请查看文件。")

    def merge_audio_video(self, audio_path, video_path, output_path):
        """
        使用FFmpeg合并音频和视频文件

        参数:
            audio_path (str): 音频文件路径
            video_path (str): 视频文件路径
            output_path (str): 输出合并后的文件路径

        返回:
            bool: 合并是否成功
        """
        try:
            # 检查FFmpeg是否安装
            import subprocess
            try:
                subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                logging.error("FFmpeg未安装或无法访问，无法合并音视频")
                raise Exception("FFmpeg未安装，请安装后再使用音视频合并功能")

            # 合并命令
            cmd = [
                'ffmpeg',
                '-i', video_path,  # 视频输入
                '-i', audio_path,  # 音频输入
                '-c:v', 'copy',  # 复制视频编码
                '-c:a', 'aac',  # 使用AAC编码音频
                '-strict', 'experimental',
                '-y',  # 覆盖输出文件
                output_path  # 输出文件
            ]

            # 执行合并
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if process.returncode == 0:
                logging.info(f"音视频合并成功: {output_path}")
                return True
            else:
                error_msg = process.stderr.decode()
                logging.error(f"音视频合并失败: {error_msg}")
                raise Exception(f"音视频合并失败: {error_msg[:50]}...")

        except Exception as e:
            logging.error(f"合并音视频时出错: {e}")
            raise

    def start_download(self, selected_parts, parent_window=None, download_mode="audio_only"):
        """
        批量下载用户选择的分P

        参数:
            selected_parts: 选择的分P列表，每个元素是(p, p_url, title)三元组
            parent_window: 父窗口，用于显示消息框
            download_mode: 下载模式
        """
        # 获取主标题，用于创建文件夹
        if selected_parts:
            # 获取第一个分P的URL来提取主标题
            _, first_url, _ = selected_parts[0]
            html = self.get_html(first_url)
            if html:
                main_title = self.get_name(html)
                if main_title:
                    main_title = self.safe_filename(main_title)
                    # 创建主文件夹
                    os.makedirs(main_title, exist_ok=True)

                    # 为每个选中的分P启动下载线程
                    for p, p_url, p_title in selected_parts:
                        # 使用lambda创建一个闭包来保存当前的p_title值
                        def start_download_with_title(url, title):
                            try:
                                # 获取网页内容
                                html = self.get_html(url)
                                if not html:
                                    logging.error(f"无法获取P{p}的网页内容")
                                    return

                                # 匹配链接
                                audio_matches, video_matches = self.match_urls(html)
                                if not audio_matches and not video_matches:
                                    logging.warning(f"P{p}: 未找到音频或视频链接")
                                    return

                                # 文件名处理
                                safe_title = self.safe_filename(title)
                                audio_path = os.path.join(main_title, f"{safe_title}.mp3")
                                video_path = os.path.join(main_title, f"{safe_title}.mp4")
                                merged_path = os.path.join(main_title, f"{safe_title}_merged.mp4")

                                # 根据下载模式执行不同的下载操作
                                if download_mode in ["audio_only", "separate", "merged"]:
                                    # 下载音频
                                    if audio_matches:
                                        audio_url = audio_matches[0]
                                        logging.info(f"开始下载P{p}音频... 保存为: {safe_title}.mp3")
                                        self.download_file(audio_url, audio_path)
                                    else:
                                        logging.warning(f"P{p}: 未找到音频链接")
                                        if download_mode == "merged":
                                            logging.error(f"P{p}: 无法进行合并，缺少音频")
                                            return

                                if download_mode in ["video_only", "separate", "merged"]:
                                    # 下载视频
                                    if video_matches:
                                        video_url = video_matches[0]
                                        logging.info(f"开始下载P{p}视频... 保存为: {safe_title}.mp4")
                                        self.download_file(video_url, video_path)
                                    else:
                                        logging.warning(f"P{p}: 未找到视频链接")
                                        if download_mode == "merged":
                                            logging.error(f"P{p}: 无法进行合并，缺少视频")
                                            return

                                # 如果是合并模式，执行合并操作
                                if download_mode == "merged" and os.path.exists(audio_path) and os.path.exists(
                                        video_path):
                                    logging.info(f"开始合并P{p}的音视频...")
                                    if self.merge_audio_video(audio_path, video_path, merged_path):
                                        logging.info(f"P{p}: 音视频合并成功: {merged_path}")
                                        # 可选：删除原始的音频和视频文件
                                        # os.remove(audio_path)
                                        # os.remove(video_path)
                                    else:
                                        logging.error(f"P{p}: 音视频合并失败")

                                logging.info(f"P{p}: {title} 下载完成")
                            except Exception as e:
                                logging.error(f"下载P{p}时出错: {e}")

                        # 启动下载线程
                        threading.Thread(target=start_download_with_title, args=(p_url, p_title)).start()
                else:
                    logging.error("无法获取主标题")
                    if parent_window:
                        messagebox.showerror("错误", "无法获取视频主标题", parent=parent_window)
            else:
                logging.error("无法获取网页内容")
                if parent_window:
                    messagebox.showerror("错误", "无法获取视频页面内容", parent=parent_window)
        else:
            logging.warning("没有选择任何分P")
            if parent_window:
                messagebox.showwarning("警告", "没有选择任何分P", parent=parent_window)

    def set_progress_callback(self, callback):
        """
        设置进度回调函数

        参数:
            callback: 进度回调函数，接受一个整数参数表示进度百分比
        """
        self.progress_callback = callback

    def show_parts_window(self, url, parent_window, download_mode="audio_only"):
        """
        弹出窗口，显示所有分P的复选框

        参数:
            url: 视频URL
            parent_window: 父窗口
            download_mode: 下载模式
        """
        parts_info = self.get_p_total(url)

        if not parts_info:
            messagebox.showerror("错误", "未能获取分P信息", parent=parent_window)
            return

        parts_window = tk.Toplevel(parent_window)
        parts_window.title("选择分P下载")
        parts_window.geometry("500x400")

        # 创建滚动框架
        frame = tk.Frame(parts_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建Canvas和Scrollbar
        canvas = tk.Canvas(frame)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        # 配置Canvas
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 存储复选框变量
        check_vars = []

        # 添加分P选项
        for p, p_url, title in parts_info:
            var = tk.BooleanVar()
            check_vars.append((var, p, p_url, title))
            cb = tk.Checkbutton(scrollable_frame, text=f"P{p}: {title}", variable=var)
            cb.pack(anchor="w", padx=5, pady=2)

        # 添加全选/取消全选按钮
        def select_all():
            for var, _, _, _ in check_vars:
                var.set(True)

        def deselect_all():
            for var, _, _, _ in check_vars:
                var.set(False)

        select_buttons_frame = tk.Frame(parts_window)
        select_buttons_frame.pack(fill=tk.X, padx=5, pady=5)

        select_all_btn = tk.Button(select_buttons_frame, text="全选", command=select_all)
        select_all_btn.pack(side=tk.LEFT, padx=5)

        deselect_all_btn = tk.Button(select_buttons_frame, text="取消全选", command=deselect_all)
        deselect_all_btn.pack(side=tk.LEFT, padx=5)

        # 显示当前下载模式
        mode_label = tk.Label(select_buttons_frame, text=f"下载模式: {download_mode}")
        mode_label.pack(side=tk.RIGHT, padx=5)

        # 确认按钮回调函数
        def confirm_selection():
            selected_parts = [(p, p_url, title) for var, p, p_url, title in check_vars if var.get()]
            if selected_parts:
                parts_window.destroy()
                self.start_download(selected_parts, parent_window, download_mode)
            else:
                messagebox.showwarning("提示", "请至少选择一个分P", parent=parts_window)

        # 添加确认按钮
        confirm_button = tk.Button(parts_window, text="开始下载", command=confirm_selection, height=2, width=20)
        confirm_button.pack(pady=10)

        # 绑定鼠标滚轮事件
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<MouseWheel>", on_mousewheel)  # Windows
        canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # Linux
        canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))  # Linux

        # 布局滚动组件
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def check_ffmpeg_installed(self):
        """
        检查FFmpeg是否已安装

        返回:
            bool: FFmpeg是否已安装
        """
        try:
            import subprocess
            process = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return process.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def get_video_info(self, url):
        """
        获取视频基本信息

        参数:
            url: 视频URL

        返回:
            dict: 包含视频信息的字典
        """
        try:
            html = self.get_html(url)
            if not html:
                return {"error": "无法获取网页内容"}

            # 提取标题
            title = self.get_name(html)
            if not title:
                return {"error": "无法提取视频标题"}

            # 获取分P信息
            p_info = self.get_p(url, 3)  # 获取当前P号和总P数
            current_p, total_p = p_info if p_info else (1, 0)

            # 尝试提取UP主信息
            up_match = re.search(r'"owner":\s*{\s*"mid":\s*(\d+),\s*"name":\s*"([^"]+)"', html)
            up_id = up_match.group(1) if up_match else "未知"
            up_name = up_match.group(2) if up_match else "未知"

            # 尝试提取视频时长
            duration_match = re.search(r'"duration":\s*(\d+)', html)
            duration = int(duration_match.group(1)) if duration_match else 0

            # 格式化时长
            minutes, seconds = divmod(duration, 60)
            hours, minutes = divmod(minutes, 60)
            duration_str = f"{hours:02}:{minutes:02}:{seconds:02}" if hours else f"{minutes:02}:{seconds:02}"

            # 尝试提取视频发布日期
            date_match = re.search(r'"pubdate":\s*(\d+)', html)
            publish_timestamp = int(date_match.group(1)) if date_match else 0
            publish_date = time.strftime("%Y-%m-%d",
                                         time.localtime(publish_timestamp)) if publish_timestamp else "未知"

            return {
                "title": title,
                "current_p": current_p,
                "total_p": total_p,
                "up_id": up_id,
                "up_name": up_name,
                "duration": duration_str,
                "publish_date": publish_date
            }
        except Exception as e:
            logging.error(f"获取视频信息时出错: {e}")
            return {"error": f"获取视频信息时出错: {str(e)}"}


# 示例用法
if __name__ == "__main__":

    url = "https://www.bilibili.com/video/BV1cXLGz8EkC?t=7.7"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
        "Referer": url
    }
    downloader = BilibiliDownloader()
    downloader.headers = headers
    downloader.get_html(url)
    # 检查是否安装了FFmpeg
    if downloader.check_ffmpeg_installed():
        print("FFmpeg已安装，可以使用音视频合并功能")
        download_mode = "merged"  # 使用合并模式
    else:
        print("FFmpeg未安装，将使用仅音频模式")
        download_mode = "audio_only"  # 使用仅音频模式

    # 获取视频信息
    info = downloader.get_video_info(url)
    if "error" in info:
        print(f"获取视频信息失败: {info['error']}")
    else:
        print(f"视频标题: {info['title']}")
        print(f"UP主: {info['up_name']} (ID: {info['up_id']})")
        print(f"发布日期: {info['publish_date']}")
        print(f"视频时长: {info['duration']}")
        print(f"当前P: {info['current_p']} / 总P数: {info['total_p']}")

    # 执行下载
    try:
        downloader.download_video_and_audio(url, downloader.headers, download_mode)
        print("下载完成!")
    except Exception as e:
        print(f"下载失败: {e}")