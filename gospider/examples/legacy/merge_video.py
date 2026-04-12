#!/usr/bin/env python3
"""
使用 Python 合并 MP4 视频文件
"""
import os
import subprocess
import sys

output_dir = r"C:\Users\Administrator\spider\gospider\downloads\youku_video"
output_file = os.path.join(output_dir, "封神_祸商_完整版.mp4")

# 获取视频分段文件
video_segments = []
for i in range(4):
    segment = os.path.join(output_dir, f"video_segment_{i:03d}.mp4")
    if os.path.exists(segment):
        video_segments.append(segment)
    else:
        print(f"找不到文件：{segment}")

if not video_segments:
    print("错误：没有找到视频文件！")
    sys.exit(1)

print(f"找到 {len(video_segments)} 个视频分段")
print(f"输出文件：{output_file}")

# 方法 1: 尝试使用 ffmpeg（如果可用）
try:
    # 创建文件列表
    filelist_path = os.path.join(output_dir, "filelist_for_ffmpeg.txt")
    with open(filelist_path, 'w', encoding='utf-8') as f:
        for segment in video_segments:
            # 使用绝对路径
            abs_path = os.path.abspath(segment).replace('\\', '/')
            f.write(f"file '{abs_path}'\n")
    
    # 查找 ffmpeg
    ffmpeg_paths = [
        r"C:\Program Files\Python313\Lib\site-packages\yt_dlp\ffmpeg\ffmpeg.exe",
        r"ffmpeg.exe",
    ]
    
    ffmpeg_exe = None
    for path in ffmpeg_paths:
        if os.path.exists(path):
            ffmpeg_exe = path
            break
    
    if ffmpeg_exe:
        print(f"使用 ffmpeg: {ffmpeg_exe}")
        cmd = [
            ffmpeg_exe,
            "-y",  # 覆盖输出文件
            "-f", "concat",
            "-safe", "0",
            "-i", filelist_path,
            "-c", "copy",
            output_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ 视频合并成功！")
            print(f"输出：{output_file}")
            sys.exit(0)
        else:
            print(f"ffmpeg 失败：{result.stderr}")
    else:
        print("未找到 ffmpeg，使用 Python 简单合并（可能不完美）...")
        
except Exception as e:
    print(f"ffmpeg 合并失败：{e}")

# 方法 2: 简单二进制合并（不推荐，但可以作为备选）
print("\n使用简单二进制合并...")
try:
    with open(output_file, 'wb') as outfile:
        for segment in video_segments:
            print(f"  合并：{os.path.basename(segment)}")
            with open(segment, 'rb') as infile:
                outfile.write(infile.read())
    
    print(f"\n✓ 简单合并完成！")
    print(f"输出：{output_file}")
    print("\n注意：简单合并的视频可能无法正常播放，建议安装 ffmpeg 重新合并")
except Exception as e:
    print(f"合并失败：{e}")
