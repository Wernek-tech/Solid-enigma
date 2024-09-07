import imageio_ffmpeg as ffmpeg

def check_ffmpeg():
    try:
        ffmpeg_path = ffmpeg.get_ffmpeg_exe()
        print(f"FFmpeg is located at: {ffmpeg_path}")
    except Exception as e:
        print(f"Error finding FFmpeg: {e}")
        raise
