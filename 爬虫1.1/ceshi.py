# TODO 视频网址
url = "https://www.bilibili.com/video/BV18k4y117ae/"  # 替换为目标 URL
headers = {
        # Referer 防盗链 告诉服务器你请求链接是从哪里跳转过来的
        # "Referer": "https://www.bilibili.com/video/BV1454y187Er/",
        "Referer": url,
        # User-Agent 用户代理, 表示浏览器/设备基本身份信息
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        # f12开发者模式中可获取以上信息
        "Cookie": "empty"
    }

import requests
import re
def get_video(video_url,headers,name):
    # TODO 通过F12查看视频的地址
    #video_url = 'https://cn-sdjn-cm-02-07.bilivideo.com/upgcxcode/95/29/313072995/313072995-1-30280.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&uipk=5&nbs=1&deadline=1736313758&gen=playurlv2&os=bcache&oi=2028326111&trid=00006cc58711d52947f2a8bb687b6df41e67u&mid=700258188&platform=pc&og=cos&upsig=532237c45bfe6c89f8c53572ee8361ad&uparams=e,uipk,nbs,deadline,gen,os,oi,trid,mid,platform,og&cdnid=6617&bvc=vod&nettype=0&orderid=0,3&buvid=AC4714D5-9AEB-BDFB-D891-DDB2408AC8B544600infoc&build=0&f=u_0_0&agrr=0&bw=23643&logo=80000000'
    video_name = name + ".mp3"#名称合成
    video_response = requests.get(video_url, headers=headers)
    with open(".mp4", mode='wb') as v:
        v.write(video_response.content)

def get_audio(audio_url,headers,name):
    # TODO 通过F12查看音频的地址
    # audio_url = 'https://cn-sdjn-cm-02-07.bilivideo.com/upgcxcode/95/29/313072995/313072995-1-100026.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&uipk=5&nbs=1&deadline=1736313758&gen=playurlv2&os=bcache&oi=2028326111&trid=00006cc58711d52947f2a8bb687b6df41e67u&mid=700258188&platform=pc&og=cos&upsig=73862b5871ff646dec4c4d758f5b77a1&uparams=e,uipk,nbs,deadline,gen,os,oi,trid,mid,platform,og&cdnid=6617&bvc=vod&nettype=0&orderid=0,3&buvid=AC4714D5-9AEB-BDFB-D891-DDB2408AC8B544600infoc&build=0&f=u_0_0&agrr=0&bw=9265&logo=80000000'
    audio_name = name+".mp3"#名称合成
    audio_response = requests.get(audio_url, headers=headers)
    with open("s.mp3", mode='wb') as v:
        v.write(audio_response.content)

def match_url(url):
    # 定义音频和视频的匹配规则
    audio_pattern = r"https:\/\/[\w.-]+\/[\w\/.-]*\/(\d{5})[\w\/.-]*\.m4s"
    video_pattern = r"https:\/\/[\w.-]+\/[\w\/.-]*\/(\d{6})[\w\/.-]*\.m4s"

    # 匹配音频文件链接
    if re.search(audio_pattern, url):
        return "音频文件匹配成功: " + url

    # 匹配视频文件链接
    elif re.search(video_pattern, url):
        return "视频文件匹配成功: " + url

    # 如果都没有匹配成功，返回0
    else:
        return 0

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

if __name__=="__main__":
    response(url, headers)
    html = response(url, headers).text
    match_url(html)
    # 测试匹配函数
    if html != 0:
        print(html)
    for url in url:
        print(match_url(url))