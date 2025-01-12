from moviepy.editor import VideoFileClip, AudioFileClip

def combine_video_audio(video_path, audio_path, output_path):
    # 加载视频和音频文件
    video = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)
    
    # 检查时间
    if abs(video.duration - audio.duration) > 0.1:
        print(f"视频长度 ({video.duration:.2f}秒) 与音频长度 ({audio.duration:.2f}秒) 不匹配！")
        if input("是否要截取较长的文件？(y/n): ").lower() == 'y':
            final_duration = min(video.duration, audio.duration)
            video = video.subclip(0, final_duration)
            audio = audio.subclip(0, final_duration)
        else:
            return
    
    # 合并并导出
    final_video = video.set_audio(audio)
    final_video.write_videofile(output_path)
    
    # 关闭文件
    video.close()
    audio.close()
    final_video.close()
