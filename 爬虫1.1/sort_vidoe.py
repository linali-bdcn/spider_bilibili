#categorize_video_quality、print_quality_dict已废除
def categorize_video_quality(video_urls):
    quality_dict = {
        "1080p高清": None,
        "720p高清": None,
        "480p清晰": None,
        "360p流畅": None,
        "240p流畅": None,
        "144p流畅": None
    }

    for url in video_urls:
        try:
            # 提取质量编号
            quality_num_start = url.find("-1-") + 3
            quality_num_end = url.find(".m4s")
            if quality_num_start >= 3 and quality_num_end != -1:
                quality_num = url[quality_num_start:quality_num_end]
            else:
                continue

            # 提取带宽值
            bw_start = url.find("bw=") + 3
            if bw_start >= 3:
                bw_end = url.find("&", bw_start)
                if bw_end == -1:
                    bw_end = len(url)
                try:
                    bandwidth = int(url[bw_start:bw_end])
                except ValueError:
                    continue
            else:
                continue

            # 修改后的判断逻辑
            if quality_num in ['100047', '100046'] and bandwidth > 30000:
                quality_dict["1080p高清"] = url
            elif (quality_num in ['100110', '100109'] and bandwidth > 15000) or bandwidth > 30000:
                quality_dict["720p高清"] = url
            elif quality_num in ['100077', '100076'] or (20000 <= bandwidth < 30000):
                quality_dict["480p清晰"] = url
            elif quality_num == '100023' or (15000 <= bandwidth < 20000):
                quality_dict["360p流畅"] = url
            elif quality_num == '100022' or (10000 <= bandwidth < 15000):
                quality_dict["240p流畅"] = url
            elif bandwidth < 10000:
                quality_dict["144p流畅"] = url

        except Exception as e:
            print(f"处理URL时出错: {e}")
            continue

    return quality_dict


# 使用示例
def print_quality_dict(quality_dict):
    print("\n视频质量分类结果：")
    for quality, url in quality_dict.items():
        if url:
            print(f"\n{quality}:")
            # 为了便于阅读，只打印URL的关键部分
            print(f"质量编号: {url[url.find('-1-') + 3:url.find('.m4s')]}")
            bw_start = url.find("bw=") + 3
            bw_end = url.find("&", bw_start)
            if bw_end == -1:
                bw_end = len(url)
            print(f"带宽: {url[bw_start:bw_end]}")

# 获取特定质量的视频URL
def get_specific_quality(quality_dict,quality_level):
        return quality_dict.get(quality_level)

##############################################################################################

#新匹配规则，这一段才是有用的
def get_highest_quality_url(urls):
    def extract_quality_info(url):
        """提取URL中的品质编号和带宽信息"""
        import re
        # 匹配品质编号
        quality_match = re.search(r'-1-(\d+)\.m4s', url)
        # 匹配带宽参数
        bw_match = re.search(r'bw=(\d+)', url)

        if quality_match and bw_match:
            quality_num = int(quality_match.group(1))
            bandwidth = int(bw_match.group(1))
            return quality_num, bandwidth, url
        return None

    # B站视频质量编号映射
    QUALITY_MAP = {
        100023: '1080P',
        100022: '720P',
        100046: '480P',
        100047: '360P',
        100110: '高品质音频',
        100109: '中等品质音频'
    }

    # 视频流品质优先级
    VIDEO_PRIORITY = {
        100023: 4,  # 1080P
        100022: 3,  # 720P
        100046: 2,  # 480P
        100047: 1  # 360P
    }

    # 带宽阈值（根据实际情况调整）
    BW_THRESHOLD = {
        100023: 15000,  # 1080P至少需要15000的带宽
        100022: 10000,  # 720P至少需要10000的带宽
        100046: 5000,  # 480P至少需要5000的带宽
        100047: 0  # 360P没有带宽要求
    }

    # 过滤有效URL并提取信息
    url_info = []
    for url in urls:
        info = extract_quality_info(url)
        if info:
            url_info.append(info)

    if not url_info:
        print("没有找到有效的URL")
        return None

    # 按品质编号分组并记录最大带宽
    quality_groups = {}
    for quality, bw, url in url_info:
        if quality not in quality_groups or bw > quality_groups[quality][0]:
            quality_groups[quality] = (bw, url)

    # 筛选符合条件的视频流
    valid_streams = []
    for quality, (bw, url) in quality_groups.items():
        if quality in VIDEO_PRIORITY:  # 只处理视频流
            # 检查带宽是否达到阈值
            if bw >= BW_THRESHOLD[quality]:
                # 计算综合得分 (品质优先级 * 2 + 带宽得分)
                bandwidth_score = min(bw / 10000, 5)  # 将带宽映射到0-5的得分
                total_score = VIDEO_PRIORITY[quality] * 2 + bandwidth_score
                valid_streams.append((quality, bw, total_score, url))

    if not valid_streams:
        # 如果没有符合带宽要求的流，选择最低品质
        for quality in reversed(VIDEO_PRIORITY.keys()):
            if quality in quality_groups:
                bw, url = quality_groups[quality]
                print(f"\n未找到符合带宽要求的流，使用最低可用品质:")
                print(f"品质编号: {quality}")
                print(f"品质说明: {QUALITY_MAP.get(quality, '未知品质')}")
                print(f"带宽: {bw} ({bw / 1024:.2f}KB/s)")
                return url
    else:
        # 按综合得分排序，选择得分最高的
        best_stream = max(valid_streams, key=lambda x: x[2])
        quality, bw, score, url = best_stream

        print(f"\n最佳品质信息:")
        print(f"品质编号: {quality}")
        print(f"品质说明: {QUALITY_MAP.get(quality, '未知品质')}")
        print(f"带宽: {bw} ({bw / 1024:.2f}KB/s)")
        print(f"综合得分: {score:.2f}")

        return url

    return None


# 使用示例
if __name__ == "__main__":
    urls = [
        # 你的URL列表
    ]

    best_url = get_highest_quality_url(urls)
    if best_url:
        print(f"\n最高品质URL:\n{best_url}")


# 使用函数
if __name__ == "__main__":
    # 这里放入实际的视频URL列表
    video_urls = [
        "https://xy120x233x0x140xy.mcdn.bilivideo.cn:4483/upgcxcode/72/84/25635328472/25635328472-1-100110.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&uipk=5&nbs=1&deadline=1736376509&gen=playurlv2&os=mcdn&oi=2028326106&trid=00007b0b42ed5f144f10b1cce0284fe32478u&mid=0&platform=pc&og=cos&upsig=43047514922b1c938d2782f23b34ceb6&uparams=e,uipk,nbs,deadline,gen,os,oi,trid,mid,platform,og&mcdnid=50017869&bvc=vod&nettype=0&orderid=0,3&buvid=&build=0&f=u_0_0&agrr=1&bw=18378&logo=A0020000",
        "https://xy183x232x113x168xy.mcdn.bilivideo.cn:8082/v1/resource/25635328472-1-100023.m4s?agrr=1&build=0&buvid=&bvc=vod&bw=17996&deadline=1736376509&e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M%3D&f=u_0_0&gen=playurlv2&logo=A0020000&mcdnid=50017869&mid=0&nbs=1&nettype=0&og=cos&oi=2028326106&orderid=0%2C3&os=mcdn&platform=pc&sign=942f14&traceid=trDZRfVQtuptBW_0_e_N&uipk=5&uparams=e%2Cuipk%2Cnbs%2Cdeadline%2Cgen%2Cos%2Coi%2Ctrid%2Cmid%2Cplatform%2Cog&upsig=c00a492ddc4792cf9eb975a97ed314e9",
        "https://xy120x233x0x140xy.mcdn.bilivideo.cn:4483/upgcxcode/72/84/25635328472/25635328472-1-100109.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&uipk=5&nbs=1&deadline=1736376509&gen=playurlv2&os=mcdn&oi=2028326106&trid=00007b0b42ed5f144f10b1cce0284fe32478u&mid=0&platform=pc&og=hw&upsig=0702979cf671adc427b943ec87d7fc24&uparams=e,uipk,nbs,deadline,gen,os,oi,trid,mid,platform,og&mcdnid=50017869&bvc=vod&nettype=0&orderid=0,3&buvid=&build=0&f=u_0_0&agrr=1&bw=13351&logo=A0020000",
        "https://xy120x233x0x140xy.mcdn.bilivideo.cn:4483/upgcxcode/72/84/25635328472/25635328472-1-100046.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&uipk=5&nbs=1&deadline=1736376509&gen=playurlv2&os=mcdn&oi=2028326106&trid=00007b0b42ed5f144f10b1cce0284fe32478u&mid=0&platform=pc&og=hw&upsig=6805c5657db2086c8347f76d74f9fe15&uparams=e,uipk,nbs,deadline,gen,os,oi,trid,mid,platform,og&mcdnid=50017869&bvc=vod&nettype=0&orderid=0,3&buvid=&build=0&f=u_0_0&agrr=1&bw=20791&logo=A0020000",
        "https://xy115x56x242x32xy.mcdn.bilivideo.cn:8082/v1/resource/25635328472-1-100022.m4s?agrr=1&build=0&buvid=&bvc=vod&bw=13086&deadline=1736376509&e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M%3D&f=u_0_0&gen=playurlv2&logo=A0020000&mcdnid=50017869&mid=0&nbs=1&nettype=0&og=cos&oi=2028326106&orderid=0%2C3&os=mcdn&platform=pc&sign=674e45&traceid=trsFHmeOBdmilo_0_e_N&uipk=5&uparams=e%2Cuipk%2Cnbs%2Cdeadline%2Cgen%2Cos%2Coi%2Ctrid%2Cmid%2Cplatform%2Cog&upsig=0428432a9d94ed97812078b8c146509e",
        "https://xy120x233x0x140xy.mcdn.bilivideo.cn:4483/upgcxcode/72/84/25635328472/25635328472-1-100047.m4s?e=ig8euxZM2rNcNbdlhoNvNC8BqJIzNbfqXBvEqxTEto8BTrNvN0GvT90W5JZMkX_YN0MvXg8gNEV4NC8xNEV4N03eN0B5tZlqNxTEto8BTrNvNeZVuJ10Kj_g2UB02J0mN0B5tZlqNCNEto8BTrNvNC7MTX502C8f2jmMQJ6mqF2fka1mqx6gqj0eN0B599M=&uipk=5&nbs=1&deadline=1736376509&gen=playurlv2&os=mcdn&oi=2028326106&trid=00007b0b42ed5f144f10b1cce0284fe32478u&mid=0&platform=pc&og=hw&upsig=d338a7b61c54abefa2b8e61488845047&uparams=e,uipk,nbs,deadline,gen,os,oi,trid,mid,platform,og&mcdnid=50017869&bvc=vod&nettype=0&orderid=0,3&buvid=&build=0&f=u_0_0&agrr=1&bw=35065&logo=A0020000"
    ]

    """quality_dict = categorize_video_quality(video_urls)
    print_quality_dict(quality_dict)
    specific_url = get_specific_quality("240p流畅")
    print(specific_url)"""

    # 使用示例
    best_url = get_highest_quality_url(video_urls)
    print(f"\n最高品质的URL是:\n{best_url}")


