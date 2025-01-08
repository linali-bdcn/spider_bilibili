def categorize_video_quality(video_urls):
    # 创建质量字典
    quality_dict = {
        "1080p高清": None,  # 通常对应 100047/100046 且带宽最大
        "720p高清": None,  # 通常对应 100110/100109 且带宽较大
        "480p清晰": None,  # 通常对应 100077/100076
        "360p流畅": None,  # 通常对应 100023
        "240p流畅": None,  # 通常对应 100022
        "144p流畅": None  # 带宽最小的版本
    }

    for url in video_urls:
        try:
            # 提取质量编号
            quality_num_start = url.find("-1-") + 3
            quality_num_end = url.find(".m4s")
            if quality_num_start >= 3 and quality_num_end != -1:  # 确保找到了有效的位置
                quality_num = url[quality_num_start:quality_num_end]
            else:
                continue

            # 提取带宽值
            bw_start = url.find("bw=") + 3
            if bw_start >= 3:  # 确保找到了 bw=
                bw_end = url.find("&", bw_start)
                if bw_end == -1:  # 如果没有找到 &，可能是URL的最后一个参数
                    bw_end = len(url)
                try:
                    bandwidth = int(url[bw_start:bw_end])
                except ValueError:
                    continue
            else:
                continue

            # 根据质量编号和带宽判断质量级别
            if quality_num in ['100047', '100046'] and bandwidth > 50000:
                quality_dict["1080p高清"] = url
            elif quality_num in ['100110', '100109'] and 25000 <= bandwidth <= 50000:
                quality_dict["720p高清"] = url
            elif quality_num in ['100077', '100076'] or (20000 <= bandwidth < 25000):
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


# 使用函数
if __name__ == "__main__":
    # 这里放入实际的视频URL列表
    video_urls = [
        # 你的实际URL列表
    ]

    quality_dict = categorize_video_quality(video_urls)
    print_quality_dict(quality_dict)


    # 获取特定质量的视频URL
    def get_specific_quality(quality_level):
        return quality_dict.get(quality_level)