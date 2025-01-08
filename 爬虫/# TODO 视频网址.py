# TODO 视频网址
url = "https://www.bilibili.com/video/BV1454y187Er/"  # 替换为目标 URL
cookie = "empty"

headers = {
        "Referer": "https://www.bilibili.com/video/BV1454y187Er/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Cookie" : "empty"
}
import requests

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
