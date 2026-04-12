#!/usr/bin/env python3
"""
快速下载并安装 ffmpeg
"""
import os
import sys
import zipfile
import urllib.request
from pathlib import Path

# 下载链接（使用镜像源）
ffmpeg_url = "https://github.com/GyanD/codexffmpeg/releases/download/8.1/ffmpeg-8.1-full_build.zip"
install_dir = Path(r"C:\ffmpeg")
download_file = Path(r"C:\Users\Administrator\Downloads\ffmpeg.zip")

print("=== FFmpeg 安装器 ===")
print(f"下载链接：{ffmpeg_url}")
print(f"安装目录：{install_dir}")
print("")

# 创建下载目录
download_file.parent.mkdir(parents=True, exist_ok=True)

# 检查是否已下载
if not download_file.exists():
    print("正在下载 ffmpeg...")
    
    def download_progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        percent = min(downloaded * 100 / total_size, 100)
        mb_downloaded = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        print(f"\r  进度：{percent:.1f}% ({mb_downloaded:.1f} MB / {mb_total:.1f} MB)", end="", flush=True)
    
    try:
        urllib.request.urlretrieve(ffmpeg_url, download_file, download_progress)
        print("\n  下载完成！")
    except Exception as e:
        print(f"\n下载失败：{e}")
        print("请检查网络连接后重试")
        sys.exit(1)
else:
    print(f"已存在下载文件：{download_file}")

# 解压
print("\n正在解压 ffmpeg...")
try:
    with zipfile.ZipFile(download_file, 'r') as zip_ref:
        # 获取第一个目录（包含版本号）
        names = zip_ref.namelist()
        base_dir = names[0].split('/')[0]
        
        # 解压到临时目录
        extract_to = Path(r"C:\Users\Administrator\Downloads\ffmpeg_temp")
        extract_to.mkdir(parents=True, exist_ok=True)
        zip_ref.extractall(extract_to)
        print(f"  解压到：{extract_to}")
except Exception as e:
    print(f"解压失败：{e}")
    sys.exit(1)

# 移动到安装目录
print("\n正在安装 ffmpeg...")
try:
    # 删除旧版本
    if install_dir.exists():
        import shutil
        shutil.rmtree(install_dir)
        print(f"  已删除旧版本：{install_dir}")
    
    # 移动新版本
    source_bin = extract_to / base_dir / "bin"
    if source_bin.exists():
        import shutil
        shutil.move(str(source_bin), str(install_dir))
        print(f"  已安装到：{install_dir}")
    
    # 清理临时文件
    if extract_to.exists():
        import shutil
        shutil.rmtree(extract_to)
        print(f"  已清理临时文件")
except Exception as e:
    print(f"安装失败：{e}")
    sys.exit(1)

# 添加到 PATH
print("\n正在添加到系统 PATH...")
try:
    import subprocess
    # 使用 setx 命令添加到用户 PATH
    cmd = f'setx PATH "%PATH%;{install_dir}"'
    subprocess.run(cmd, shell=True, check=True)
    print(f"  已将 {install_dir} 添加到用户 PATH")
    print("  注意：需要重启终端才能生效")
except Exception as e:
    print(f"PATH 设置失败：{e}")
    print(f"  可以手动将 {install_dir} 添加到 PATH")

print("\n=== 安装完成 ===")
print(f"ffmpeg 位置：{install_dir}")
print("")
print("验证安装（需要重启终端）:")
print("  ffmpeg -version")
