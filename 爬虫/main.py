import requests
import re
import ast

# 定义URL和cookie
url = "https://www.bilibili.com/video/BV1FW421R7Wr"
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

url = "https://www.bilibili.com/video/BV1XjpEeWEex"  # 替换为目标 URL
cookie = "buvid3=6C683F82-1AA1-0F66-D454-FFF208DBC1F521812infoc; b_nut=1733677521; _uuid=94DC2C88-CFBB-2F5B-179E-81081897C10D4322334infoc; buvid_fp=879cad39eedf3ef987987fbfaa135ea1; header_theme_version=CLOSE; enable_web_push=DISABLE; rpdid=|(k|k)JkYu|~0J'u~JRJYR||J; buvid4=8BF03D1D-BE06-B817-1BC3-4DD884E7069977190-024052609-S52gkV%2FdQbdiICpKZhS%2FTQ%3D%3D; DedeUserID=700258188; Ded eUserID__ckMd5=a2f0bc6e77c418a7; bp_t_offset_700258188=1019212687281750016; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzY1MjY4NDgsImlhdCI6MTczNjI2NzU4OCwicGx0IjotMX0.vJ65JZw4Y3CsH1xPZp4O3GUJb6XHqw-UvfMsWXIe6NM; bili_ticket_expires=1736526788; SESSDATA=8c7d3622%2C1751819650%2C64988%2A12CjBblP9nDUFGUHSn3VBUCU1hbatpJfwsXoOllyPkEw13Sr-xRm5b97UncHQ4ZSr18L4SVmU0WjZYdnlLd0kzVFplU21VaUhkRGtwZjBjaXN6VVRXemF2Z0Q2NFduNWU3THU5SVpBTlVocjRlZTlQdmVGaUppU0pBS2tKUDRibFZUM0lLVUZRWnh3IIEC; bili_jct=b4aa7aedb351f2a78b858bd1d435b949; b_lsid=FD2B4B10F_1944458C0B0; home_feed_column=5; browser_resolution=1865-956; bmg_af_switch=1; bmg_src_def_domain=i1.hdslb.com; CURRENT_FNVAL=4048; sid=odejg072"
user_Agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
headers = {
        # Referer 防盗链 告诉服务器你请求链接是从哪里跳转过来的
        # "Referer": "https://www.bilibili.com/video/BV1454y187Er/",
        "Referer": url,
        # User-Agent 用户代理, 表示浏览器/设备基本身份信息
        "User-Agent": user_Agent,
        # f12开发者模式中可获取以上信息
        "Cookie": cookie
    }


###################################################################


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


#获取文件优先match_urls方法
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

#定义匹配规则
def match_urls(content):
    # 音频文件的正则表达式
    audio_pattern1 = r'"baseUrl"\s*:\s*"(https://[^"]+?(?:[-_](?:1|nb2|x2)-1-)?30280\.m4s[^"]+)"'
    audio_pattern2 = r'"baseUrl"\s*:\s*"(https://[^"]+?(?:[-_](?:1|nb2|x2)-[13]0(?:0[2-8]|2[7-8])\d)\.m4s[^"]+)"'

    # 视频文件的正则表达式
    video_pattern1 = r'"baseUrl"\s*:\s*"(https://[^"]+?-1-100026\.m4s[^"]+)"'
    video_pattern2 = r'"baseUrl"\s*:\s*"(https://[^"]+?(?:-1-10(?:00|01)\d{2})\.m4s[^"]+)"'

    # 查找所有匹配
    audio_matches = re.findall(audio_pattern1, content)
    video_matches = re.findall(video_pattern2, content)

    return audio_matches, video_matches

# 保存链接到文件
def save_f(audio_matches, video_matches, headers, name):
    with open("links.txt", "w", encoding="utf-8") as links_file:
        links_file.write("音频链接:\n")
        for link in audio_matches:
            links_file.write(link + "\n")

        links_file.write("\n视频链接:\n")
        for link in video_matches:
            links_file.write(link + "\n")

    print("链接已保存到 links.txt\n正在下载音频和视频文件")

    # 下载第一个音频和视频文件
    if audio_matches:
        get_audio(audio_matches[0], headers, name)
    if video_matches:
        get_video(video_matches[0], headers, name)

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
    """url = str(input("请输入视频url地址:\n>>>"))
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
    }"""



    #开始请求
    response(url, headers)
    html = response(url, headers).text
    # 读取本地文件内容！！！同样可以不在本地文件中匹配，直接使用得到的response也可以
    with open("response.txt", "r", encoding="utf-8") as file:
        content = file.read()

    """    # 音频链接匹配（调整正则表达式，以适应实际情况）
    # 如果实际页面中音频链接的baseUrl不同，请调整正则
    audio_pattern1 = r'"baseUrl":\s*"([^"]*30280\.m4s\?e=[^"]*)"'
    audio_pattern2 = r'https://[^/]+/(?:v1/resource|upgcxcode)/.+?(?:_nb2-1-30\d{3}|_x2-1-30\d{3}|-1-30\d{3})\.m4s\?[^"]*'
    audio_pattern3 = r'https://[^/]+/(?:v1/resource|upgcxcode)/.+?(?:[-_](?:1|nb2|x2)-[13]0(?:0[2-8]|2[7-8])\d)\.m4s\?'
    em = re.search(audio_pattern2, content)
    audio_matches = clean_text(em.group(0))
    # 视频链接匹配（调整正则表达式，以适应实际情况）
    video_pattern1 = r'"baseUrl":\s*"([^"]*100026\.m4s\?e=[^"]*)"'
    video_pattern2 = r'https://[^/]+/(?:v1/resource|upgcxcode)/.+?-1-100\d{3}\.m4s\?[^"]*'
    video_pattern3 = r'https://[^/]+/(?:v1/resource|upgcxcode)/.+?(?:-1-10(?:00|01)\d{2})\.m4s\?'
    em = re.search(video_pattern2, content)
    video_matches = em.group(0)"""

    audio_matches, video_matches = match_urls(content)
    # 输出调试信息（查看是否匹配到内容）
    print(f"找到音频链接: {len(audio_matches)}")
    print(f"找到视频链接: {len(video_matches)}")

    # 如果需要查看具体链接
    print("\n音频链接:")
    for url in audio_matches:
        print(url)

    print("\n视频链接:")
    for url in video_matches:
        print(url)

    # 获取标题名称
    title = get_name(html)
    # 视频音频文件下载
    save_f(audio_matches, video_matches, headers, title)
    # 单独调用时需要注意这是个列表
    """
    get_audio(audio_matches, headers, title)
    get_video(video_matches, headers, title)"""
