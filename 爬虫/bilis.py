import requests
import re

#url地址,请求头headers
url = "https://www.bilibili.com/video/BV1454y187Er/"  # 替换为目标 URL
cookie = "emtpy" 

headers = {
        # Referer 防盗链 告诉服务器你请求链接是从哪里跳转过来的
        # "Referer": "https://www.bilibili.com/video/BV1454y187Er/",
        "Referer": url,
        # User-Agent 用户代理, 表示浏览器/设备基本身份信息
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Cookie": cookie
}


# 发送请求
response = requests.get(url=url, headers=headers)
html = response.text

# 解析数据: 提取视频标题
title = re.findall('title="(.*?)"', html)[0]
print(title)


url = "https://www.bilibili.com/video/BV1454y187Er/"  # 替换为目标 URL
cookie = "emtpy

通过访问requests‘https://www.bilibili.com/video/BV1rtkiYUEvy/?spm_id_from=333.1007.top_right_bar_window_custom_collection.content.click&vd_source=86fde7c1b0fc380df5d84bf3e669c96e’，也就是"https://www.bilibili.com/video/BV1rtkiYUEvy/"转成txt文件后匹配


"audio": [{
                            "id": 30280,
                            "baseUrl": "https://xy183x240x59x186xy.mcdn.bilivideo.cn:8082/v1/resource/27473545417-1-30280.m4s?agrr=0&build=0&buvid=AC4714D5-9AEB-BDFB-D891-DDB2408AC8B544600infoc&bvc=vod&bw=12766&deadline=1736261849&e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M%3D&f=u_0_0&gen=playurlv2&logo=A0020000&mcdnid=50008807&mid=700258188&nbs=1&nettype=0&og=cos&oi=245054657&orderid=0%2C3&os=mcdn&platform=pc&sign=4a91e5&traceid=trluYhdEAIXFww_0_e_N&uipk=5&uparams=e%2Cuipk%2Cnbs%2Cdeadline%2Cgen%2Cos%2Coi%2Ctrid%2Cmid%2Cplatform%2Cog&upsig=87de8311c48f5b772394110bd8c94135",
                            "base_url": "https://xy183x240x59x186xy.mcdn.bilivideo.cn:8082/v1/resource/27473545417-1-30280.m4s?agrr=0&build=0&buvid=AC4714D5-9AEB-BDFB-D891-DDB2408AC8B544600infoc&bvc=vod&bw=12766&deadline=1736261849&e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M%3D&f=u_0_0&gen=playurlv2&logo=A0020000&mcdnid=50008807&mid=700258188&nbs=1&nettype=0&og=cos&oi=245054657&orderid=0%2C3&os=mcdn&platform=pc&sign=4a91e5&traceid=trluYhdEAIXFww_0_e_N&uipk=5&uparams=e%2Cuipk%2Cnbs%2Cdeadline%2Cgen%2Cos%2Coi%2Ctrid%2Cmid%2Cplatform%2Cog&upsig=87de8311c48f5b772394110bd8c94135",
                            "backupUrl": ["https://xy223x109x235x82xy2409y8c20y8ab1y54yy82xy.mcdn.bilivideo.cn:4483/upgcxcode/17/54/27473545417/27473545417-1-30280.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&uipk=5&nbs=1&deadline=1736261849&gen=playurlv2&os=mcdn&oi=245054657&trid=0000ff0b478270804edbb01bc5057c0fd03cu&mid=700258188&platform=pc&og=cos&upsig=87de8311c48f5b772394110bd8c94135&uparams=e,uipk,nbs,deadline,gen,os,oi,trid,mid,platform,og&mcdnid=50008807&bvc=vod&nettype=0&orderid=0,3&buvid=AC4714D5-9AEB-BDFB-D891-DDB2408AC8B544600infoc&build=0&f=u_0_0&agrr=0&bw=12766&logo=A0020000", "https://upos-sz-mirrorcoso1.bilivideo.com/upgcxcode/17/54/27473545417/27473545417-1-30280.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&uipk=5&nbs=1&deadline=1736261849&gen=playurlv2&os=coso1bv&oi=245054657&trid=ff0b478270804edbb01bc5057c0fd03cu&mid=700258188&platform=pc&og=cos&upsig=e1e1961e1bab6e3efe6ab0e2219b7d9f&uparams=e,uipk,nbs,deadline,gen,os,oi,trid,mid,platform,og&bvc=vod&nettype=0&orderid=1,3&buvid=AC4714D5-9AEB-BDFB-D891-DDB2408AC8B544600infoc&build=0&f=u_0_0&agrr=0&bw=12766&logo=40000000"],
                            "backup_url": ["https://xy223x109x235x82xy2409y8c20y8ab1y54yy82xy.mcdn.bilivideo.cn:4483/upgcxcode/17/54/27473545417/27473545417-1-30280.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&uipk=5&nbs=1&deadline=1736261849&gen=playurlv2&os=mcdn&oi=245054657&trid=0000ff0b478270804edbb01bc5057c0fd03cu&mid=700258188&platform=pc&og=cos&upsig=87de8311c48f5b772394110bd8c94135&uparams=e,uipk,nbs,deadline,gen,os,oi,trid,mid,platform,og&mcdnid=50008807&bvc=vod&nettype=0&orderid=0,3&buvid=AC4714D5-9AEB-BDFB-D891-DDB2408AC8B544600infoc&build=0&f=u_0_0&agrr=0&bw=12766&logo=A0020000", "https://upos-sz-mirrorcoso1.bilivideo.com/upgcxcode/17/54/27473545417/27473545417-1-30280.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&uipk=5&nbs=1&deadline=1736261849&gen=playurlv2&os=coso1bv&oi=245054657&trid=ff0b478270804edbb01bc5057c0fd03cu&mid=700258188&platform=pc&og=cos&upsig=e1e1961e1bab6e3efe6ab0e2219b7d9f&uparams=e,uipk,nbs,deadline,gen,os,oi,trid,mid,platform,og&bvc=vod&nettype=0&orderid=1,3&buvid=AC4714D5-9AEB-BDFB-D891-DDB2408AC8B544600infoc&build=0&f=u_0_0&agrr=0&bw=12766&logo=40000000"],
                            "bandwidth": 102112,
                            "mimeType": "audio/mp4",
                            "mime_type": "audio/mp4",
                            "codecs": "mp4a.40.2",
                            "width": 0,
                            "height": 0,
                            "frameRate": "",
                            "frame_rate": "",
                            "sar": "",
                            "startWithSap": 0,
                            "start_with_sap": 0,
                            "SegmentBase": {
                                "Initialization": "0-817",
                                "indexRange": "818-64149"
                            },
                            "segment_base": {
                                "initialization": "0-817",
                                "index_range": "818-64149"
                            },
                            "codecid": 0
                        }
你需要在其中匹配关于:"baseUrl": "https://xy183x240x59x186xy.mcdn.bilivideo.cn:8082/v1/resource/27473545417-1-30280.m4s?agrr=0&build=0&buvid=AC4714D5-9AEB-BDFB-D891-DDB2408AC8B544600infoc&bvc=vod&bw=12766&deadline=1736261849&e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M%3D&f=u_0_0&gen=playurlv2&logo=A0020000&mcdnid=50008807&mid=700258188&nbs=1&nettype=0&og=cos&oi=245054657&orderid=0%2C3&os=mcdn&platform=pc&sign=4a91e5&traceid=trluYhdEAIXFww_0_e_N&uipk=5&uparams=e%2Cuipk%2Cnbs%2Cdeadline%2Cgen%2Cos%2Coi%2Ctrid%2Cmid%2Cplatform%2Cog&upsig=87de8311c48f5b772394110bd8c94135"字段，特征是"30280.m4s?agrr="。
这是音频的匹配,而视频的是："https://xy112x60x36x220xy.mcdn.bilivideo.cn:8082/v1/resource/27473545417-1-100026.m4s?agrr=0&build=0&buvid=AC4714D5-9AEB-BDFB-D891-DDB2408AC8B544600infoc&bvc=vod&bw=63786&deadline=1736261849&e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M%3D&f=u_0_0&gen=playurlv2&logo=A0020000&mcdnid=50008807&mid=700258188&nbs=1&nettype=0&og=hw&oi=245054657&orderid=0%2C3&os=mcdn&platform=pc&sign=88d738&traceid=trUwLBlswdsttv_0_e_N&uipk=5&uparams=e%2Cuipk%2Cnbs%2Cdeadline%2Cgen%2Cos%2Coi%2Ctrid%2Cmid%2Cplatform%2Cog&upsig=c89059982f5991ec4653d6f7946870af"字段，特征是"100026.m4s?agrr="。
