import requests
import re
import ast

# 定义URL和cookie
url = "https://www.bilibili.com/video/BV1454y187Er/"
cookie = "F12开发者工具中训找"  # 替换为有效的cookie信息

# 设置请求头
headers = {
    # Referer 防盗链 告诉服务器你请求链接是从哪里跳转过来的
    # "Referer": "https://www.bilibili.com/video/BV1454y187Er/",
    "Referer": url,
    # User-Agent 用户代理, 表示浏览器/设备基本身份信息
    "User-Agent": "string",
    #f12开发者模式中可获取以上信息
    "Cookie": cookie
}



#获取名称
def get_name(html):
    # 用更健壮的正则表达式，考虑到属性可能的空格
    match = re.findall(r'title\s*=\s*"([^"]+)"', html)

    if match:  # 如果找到了匹配项
        title = match[0]
        print("title:", title)
        return title
    else:
        print("无法匹配到标题")
        return None


#获取文件
def get_video(video_url, headers, name):
    video_name = name + ".mp4"  # 合成文件名
    try:
        video_response = requests.get(video_url, headers=headers)
        video_response.raise_for_status()  # 检查请求是否成功

        # 保存视频
        with open(video_name, mode='wb') as v:
            v.write(video_response.content)
        print(f"视频已保存为 {video_name}")
    except requests.exceptions.RequestException as e:
        print(f"视频下载出错: {e}")
    except Exception as e:
        print(f"保存视频文件时出错: {e}")


def get_audio(audio_url, headers, name):
    audio_name = name + ".mp3"  # 合成文件名
    try:
        audio_response = requests.get(audio_url, headers=headers)
        audio_response.raise_for_status()  # 检查请求是否成功

        # 保存音频
        with open(audio_name, mode='wb') as v:
            v.write(audio_response.content)
        print(f"音频已保存为 {audio_name}")
    except requests.exceptions.RequestException as e:
        print(f"音频下载出错: {e}")
    except Exception as e:
        print(f"保存音频文件时出错: {e}")


# 保存链接到文件
def save_f(audio_matches, video_matches, headers, name):
    with open("links.txt", "w", encoding="utf-8") as links_file:
        if audio_matches:
            links_file.write("音频链接:\n")
            for link in audio_matches:
                links_file.write(link + "\n")
        else:
            links_file.write("未找到音频链接。\n")

        if video_matches:
            links_file.write("\n视频链接:\n")
            for link in video_matches:
                links_file.write(link + "\n")
        else:
            links_file.write("\n未找到视频链接。\n")
    print("链接已保存到 links.txt\n正在下载音频和视频文件")

    # 分别下载每个音频和视频文件
    for audio_url in audio_matches:
        get_audio(audio_url, headers, name)

    for video_url in video_matches:
        get_video(video_url, headers, name)

    print("请前往查看已下载文件")

# 获取请求函数
def response(url, headers):
    try:
        # 发起请求
        response = requests.get(url, headers=headers)

        # 检查响应状态
        if response.status_code == 200:
            # 转换响应内容为 UTF-8 编码
            response.encoding = "utf-8"

            # 将结果写入文件
            with open("response.txt", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("内容已保存到 response.txt")
        else:
            print(f"请求失败，状态码: {response.status_code}")
        return response

    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")


if __name__ == "__main__":
    #输入基本信息
    url = str(input("请输入视频url地址:\n>>>"))
    user_Agent = input("请输入用户User-Agent:\n>>>")
    cookie = input("请输入用户Cookie:\n>>>")
    headers = {
        # Referer 防盗链 告诉服务器你请求链接是从哪里跳转过来的
        # "Referer": "https://www.bilibili.com/video/BV1454y187Er/",
        "Referer": url,
        # User-Agent 用户代理, 表示浏览器/设备基本身份信息
        "User-Agent": user_Agent,
        # f12开发者模式中可获取以上信息
        "Cookie": cookie
    }



    #开始请求
    response(url, headers)
    html = response(url, headers).text
    # 读取本地文件内容！！！同样可以不在本地文件中匹配，直接使用得到的response也可以
    with open("response.txt", "r", encoding="utf-8") as file:
        content = file.read()

    # 音频链接匹配（调整正则表达式，以适应实际情况）
    # 如果实际页面中音频链接的baseUrl不同，请调整正则
    audio_pattern = r'"baseUrl":\s*"([^"]*30280\.m4s\?e=[^"]*)"'
    audio_matches = re.findall(audio_pattern, content)

    # 视频链接匹配（调整正则表达式，以适应实际情况）
    video_pattern = r'"baseUrl":\s*"([^"]*100026\.m4s\?e=[^"]*)"'
    video_matches = re.findall(video_pattern, content)

    # 输出调试信息（查看是否匹配到内容）
    print(f"找到音频链接: {len(audio_matches)}")
    print(f"找到视频链接: {len(video_matches)}")
    # 获取标题名称
    title = get_name(html)
    # 视频音频文件下载
    save_f(audio_matches, video_matches, headers, title)
    # 单独调用时需要注意这是个列表
    """
    get_audio(audio_matches, headers, title)
    get_video(video_matches, headers, title)"""
