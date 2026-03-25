#!/usr/bin/env python
"""
视频下载命令行工具
支持 HLS/DASH 下载、FFmpeg 处理、多平台解析
"""

import sys
import os
import argparse
import json
import logging
from pathlib import Path
from typing import Optional, List


# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyspider.media.hls_downloader import HLSDownloader, DASHDownloader
from pyspider.media.ffmpeg_tools import FFmpegExecutor, FFmpegTools, FFmpegNotFoundError
from pyspider.media.video_parser import UniversalParser, VideoData
from pyspider.cli.dependencies import dependency_report_to_dict
from pyspider.cli.dependencies import run_dependency_doctor as collect_dependency_doctor
from pyspider.cli.dependencies import resolve_ffmpeg_path


def setup_logging(verbose: bool = False):
    """设置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def create_ffmpeg_executor(config_path: Optional[str] = None) -> FFmpegExecutor:
    return FFmpegExecutor(ffmpeg_path=resolve_ffmpeg_path(config_path))


def create_ffmpeg_tools(config_path: Optional[str] = None) -> FFmpegTools:
    ffmpeg_path = resolve_ffmpeg_path(config_path)
    if ffmpeg_path:
        return FFmpegTools(FFmpegExecutor(ffmpeg_path=ffmpeg_path))
    return FFmpegTools()


def log_ffmpeg_dependency_error(logger: logging.Logger, error: FFmpegNotFoundError):
    logger.error("FFmpeg 依赖检查失败：%s", error)
    logger.error(
        "请先执行 `pyspider doctor` 检查环境，"
        "或在配置项 media.ffmpeg_path / 环境变量 FFMPEG_PATH 中指定 FFmpeg 路径。"
    )


def run_dependency_doctor(args):
    return collect_dependency_doctor(config_path=getattr(args, "config", None), redis_url=getattr(args, "redis_url", None))


def resolve_download_url(
    video_data: VideoData,
    requested_quality: Optional[str],
    logger: logging.Logger,
) -> Optional[str]:
    if requested_quality and requested_quality != "best":
        available = [quality.lower() for quality in (video_data.quality_options or [])]
        if available and requested_quality.lower() not in available:
            logger.error(
                "请求的质量不可用：%s，可用选项：%s",
                requested_quality,
                ", ".join(video_data.quality_options),
            )
            return None

    return (
        video_data.m3u8_url
        or video_data.mp4_url
        or video_data.dash_url
        or video_data.download_url
    )


def cmd_download(args):
    """下载视频"""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    parser = UniversalParser()
    
    # 解析视频
    logger.info(f"解析视频：{args.url}")
    video_data = parser.parse(args.url)
    
    if not video_data:
        logger.error("无法解析视频")
        return 1
    
    logger.info(f"✓ 解析成功：{video_data.title}")
    logger.info(f"  平台：{video_data.platform}")
    
    # 确定下载 URL
    download_url = resolve_download_url(video_data, getattr(args, "quality", None), logger)

    if not download_url:
        logger.error("未找到可下载的 URL")
        return 1

    if video_data.m3u8_url and download_url == video_data.m3u8_url:
        logger.info(f"使用 HLS 下载")
    elif video_data.mp4_url and download_url == video_data.mp4_url:
        logger.info(f"使用 MP4 下载")
    elif video_data.dash_url and download_url == video_data.dash_url:
        logger.info(f"使用 DASH 下载")
    else:
        logger.info("使用通用下载地址")
    
    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 下载
    output_name = args.output_name or video_data.video_id
    
    if '.m3u8' in download_url:
        downloader = HLSDownloader(
            output_dir=str(output_dir),
            max_workers=args.workers,
            retry_times=args.retries,
        )
        
        success = downloader.download(download_url, output_name)
        
        if success:
            output_file = output_dir / f"{output_name}.ts"
            logger.info(f"✓ 下载完成：{output_file}")
            
            # 如果需要转换格式
            if args.convert:
                return 0 if convert_video(output_file, args.convert, args) else 1
        
        return 0 if success else 1
    
    elif '.mpd' in download_url:
        downloader = DASHDownloader(
            output_dir=str(output_dir),
            max_workers=args.workers,
        )
        
        success = downloader.download(download_url, output_name)
        if success:
            output_file = output_dir / f"{output_name}.mp4"
            logger.info(f"✓ 下载完成：{output_file}")

            if args.convert:
                return 0 if convert_video(output_file, args.convert, args) else 1

        return 0 if success else 1
    
    else:
        # 直接下载 MP4
        import requests
        try:
            logger.info(f"下载 MP4: {download_url}")
            resp = requests.get(download_url, stream=True, timeout=3600)
            resp.raise_for_status()
            
            output_file = output_dir / f"{output_name}.mp4"
            total = int(resp.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_file, 'wb') as f:
                for chunk in resp.iter_content(8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            percent = downloaded / total * 100
                            print(f"\r进度：{percent:.1f}%", end='', flush=True)
            
            print()
            logger.info(f"✓ 下载完成：{output_file}")

            if args.convert:
                return 0 if convert_video(output_file, args.convert, args) else 1

            return 0
            
        except Exception as e:
            logger.error(f"下载失败：{e}")
            return 1


def cmd_convert(args):
    """转换视频格式"""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        tools = create_ffmpeg_tools(args.config)
        
        logger.info(f"转换视频：{args.input} -> {args.output}")
        
        if args.format in {'mp4', 'avi', 'mkv'}:
            success = tools.convert_format(
                args.input,
                args.output,
                output_format=args.format,
                video_codec=args.video_codec or 'libx264',
                audio_codec=args.audio_codec or 'aac',
                crf=args.crf or 23,
            )
        elif args.format == 'mp3':
            success = tools.extract_audio(
                args.input,
                args.output,
                audio_format='mp3',
                bitrate=args.audio_bitrate or '192k',
            )
        elif args.format == 'gif':
            success = tools.create_gif(
                args.input,
                args.output,
                frame_rate=args.fps or 10,
            )
        else:
            logger.error(f"不支持的格式：{args.format}")
            return 1
        
        if success:
            logger.info(f"✓ 转换完成：{args.output}")
            return 0
        else:
            logger.error("转换失败")
            return 1
            
    except FFmpegNotFoundError as e:
        log_ffmpeg_dependency_error(logger, e)
        return 1


def cmd_info(args):
    """获取视频信息"""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        executor = create_ffmpeg_executor(args.config)
        info = executor.get_video_info(args.input)
        
        if info:
            print(f"\n视频信息:")
            print(f"  文件名：{info.filename}")
            print(f"  时长：{format_duration(info.duration)}")
            print(f"  大小：{info.size / 1024 / 1024:.2f} MB")
            print(f"  格式：{info.format}")
            print(f"  分辨率：{info.resolution[0]}x{info.resolution[1]}")
            print(f"  视频编码：{info.video_codec}")
            print(f"  音频编码：{info.audio_codec}")
            print(f"  比特率：{info.bitrate / 1000:.1f} kbps")
            print(f"  帧率：{info.frame_rate:.2f} fps")
            print(f"  有视频：{info.has_video}")
            print(f"  有音频：{info.has_audio}")
            return 0
        else:
            logger.error("无法获取视频信息")
            return 1
            
    except FFmpegNotFoundError as e:
        log_ffmpeg_dependency_error(logger, e)
        return 1


def cmd_screenshot(args):
    """截取视频截图"""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        tools = create_ffmpeg_tools(args.config)
        
        if args.batch:
            if args.interval <= 0:
                logger.error("截图间隔必须大于 0")
                return 1

            output_dir = args.output_dir or "screenshots"
            screenshots = tools.take_screenshots_batch(
                args.input,
                output_dir,
                interval=args.interval,
                width=args.width,
            )
            if not screenshots:
                logger.error("未生成任何截图")
                return 1

            logger.info(f"截取 {len(screenshots)} 张截图")
            for ss in screenshots:
                logger.info(f"  {ss}")
        else:
            output_file = args.output or 'screenshot.jpg'
            success = tools.take_screenshot(
                args.input,
                output_file,
                timestamp=args.timestamp or '00:00:01',
                width=args.width,
            )
            if success:
                logger.info(f"✓ 截图完成：{output_file}")
                return 0
            else:
                return 1
        
        return 0
        
    except FFmpegNotFoundError as e:
        log_ffmpeg_dependency_error(logger, e)
        return 1


def cmd_merge(args):
    """合并视频"""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        tools = create_ffmpeg_tools(args.config)
        
        # 验证输入文件
        for f in args.inputs:
            if not os.path.exists(f):
                logger.error(f"文件不存在：{f}")
                return 1
        
        logger.info(f"合并 {len(args.inputs)} 个视频...")
        
        success = tools.merge_videos(args.inputs, args.output)
        
        if success:
            logger.info(f"✓ 合并完成：{args.output}")
            return 0
        else:
            return 1
            
    except FFmpegNotFoundError as e:
        log_ffmpeg_dependency_error(logger, e)
        return 1


def cmd_doctor(args):
    """运行环境依赖检查"""
    report = run_dependency_doctor(args)
    if getattr(args, "json", False):
        print(json.dumps(dependency_report_to_dict(report), ensure_ascii=False, indent=2))
        return report.exit_code

    labels = {
        "ok": "OK",
        "warn": "WARN",
        "fail": "FAIL",
        "skip": "SKIP",
    }

    print("Runtime dependency report:")
    for status in report.statuses:
        print(f"[{labels.get(status.level, status.level.upper())}] {status.name}: {status.message}")
    print(f"Summary: {report.summary}")
    return report.exit_code


def cmd_parse(args):
    """解析视频 URL"""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    parser = UniversalParser()
    
    logger.info(f"解析：{args.url}")
    video_data = parser.parse(args.url)
    
    if video_data:
        print(f"\n视频信息:")
        print(f"  平台：{video_data.platform}")
        print(f"  标题：{video_data.title}")
        print(f"  视频 ID: {video_data.video_id}")
        if video_data.duration:
            print(f"  时长：{format_duration(video_data.duration)}")
        if video_data.m3u8_url:
            print(f"  M3U8 URL: {video_data.m3u8_url}")
        if video_data.mp4_url:
            print(f"  MP4 URL: {video_data.mp4_url}")
        if video_data.cover_url:
            print(f"  封面：{video_data.cover_url}")
        if video_data.quality_options:
            print(f"  质量选项：{video_data.quality_options}")
        return 0
    else:
        logger.error("解析失败")
        return 1


def convert_video(input_file: Path, output_format: str, args):
    """转换视频格式"""
    logger = logging.getLogger(__name__)
    
    try:
        tools = create_ffmpeg_tools(getattr(args, "config", None))
        output_file = input_file.with_suffix(f'.{output_format}')
        
        logger.info(f"转换格式：{input_file} -> {output_file}")
        
        if output_format == 'mp4':
            success = tools.convert_format(str(input_file), str(output_file))
        elif output_format == 'mp3':
            success = tools.extract_audio(str(input_file), str(output_file))
        elif output_format == 'gif':
            success = tools.create_gif(str(input_file), str(output_file))
        else:
            logger.error(f"不支持的转换格式：{output_format}")
            return False

        if success:
            logger.info(f"✓ 转换完成：{output_file}")
            return True
        else:
            logger.error(f"转换失败：{output_file}")
            return False
        
    except FFmpegNotFoundError as e:
        log_ffmpeg_dependency_error(logger, e)
        return False
    except Exception as e:
        logger.error(f"转换失败：{e}")
        return False


def format_duration(seconds: float) -> str:
    """格式化时长"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def main():
    parser = argparse.ArgumentParser(
        description='视频下载命令行工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 下载视频
  %(prog)s download https://v.youku.com/v_show/id_X.html
  
  # 下载并转换格式
  %(prog)s download https://v.youku.com/v_show/id_X.html --convert mp4
  
  # 解析视频 URL
  %(prog)s parse https://v.youku.com/v_show/id_X.html
  
  # 获取视频信息
  %(prog)s info video.mp4
  
  # 转换视频格式
  %(prog)s convert input.flv output.mp4
  
  # 截取截图
  %(prog)s screenshot video.mp4 --batch
  
  # 合并视频
  %(prog)s merge video1.mp4 video2.mp4 -o merged.mp4
        """
    )
    
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    parser.add_argument('--config', help='配置文件路径')
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # download 命令
    download_parser = subparsers.add_parser('download', help='下载视频')
    download_parser.add_argument('url', help='视频 URL')
    download_parser.add_argument('-o', '--output-dir', default='downloads', help='输出目录')
    download_parser.add_argument('-n', '--output-name', help='输出文件名')
    download_parser.add_argument('-w', '--workers', type=int, default=10, help='并发数')
    download_parser.add_argument('-r', '--retries', type=int, default=3, help='重试次数')
    download_parser.add_argument('-q', '--quality', choices=['best', '1080p', '720p', '480p'], help='质量')
    download_parser.add_argument('-c', '--convert', choices=['mp4', 'mp3', 'gif'], help='转换格式')
    download_parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    download_parser.set_defaults(func=cmd_download)
    
    # convert 命令
    convert_parser = subparsers.add_parser('convert', help='转换视频格式')
    convert_parser.add_argument('input', help='输入文件')
    convert_parser.add_argument('output', help='输出文件')
    convert_parser.add_argument('-f', '--format', required=True, choices=['mp4', 'mp3', 'gif', 'avi', 'mkv'], help='目标格式')
    convert_parser.add_argument('--video-codec', help='视频编码器')
    convert_parser.add_argument('--audio-codec', help='音频编码器')
    convert_parser.add_argument('--crf', type=int, help='质量因子')
    convert_parser.add_argument('--audio-bitrate', help='音频比特率')
    convert_parser.add_argument('--fps', type=int, help='帧率（GIF）')
    convert_parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    convert_parser.set_defaults(func=cmd_convert)
    
    # info 命令
    info_parser = subparsers.add_parser('info', help='获取视频信息')
    info_parser.add_argument('input', help='输入文件')
    info_parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    info_parser.set_defaults(func=cmd_info)
    
    # screenshot 命令
    screenshot_parser = subparsers.add_parser('screenshot', help='截取截图')
    screenshot_parser.add_argument('input', help='输入文件')
    screenshot_parser.add_argument('-o', '--output', help='输出文件')
    screenshot_parser.add_argument('-t', '--timestamp', help='时间戳')
    screenshot_parser.add_argument('-w', '--width', type=int, help='宽度')
    screenshot_parser.add_argument('-b', '--batch', action='store_true', help='批量截图')
    screenshot_parser.add_argument('--interval', type=int, default=60, help='截图间隔（秒）')
    screenshot_parser.add_argument('--output-dir', help='输出目录（批量）')
    screenshot_parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    screenshot_parser.set_defaults(func=cmd_screenshot)
    
    # merge 命令
    merge_parser = subparsers.add_parser('merge', help='合并视频')
    merge_parser.add_argument('inputs', nargs='+', help='输入文件列表')
    merge_parser.add_argument('-o', '--output', required=True, help='输出文件')
    merge_parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    merge_parser.set_defaults(func=cmd_merge)
    
    # parse 命令
    parse_parser = subparsers.add_parser('parse', help='解析视频 URL')
    parse_parser.add_argument('url', help='视频 URL')
    parse_parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    parse_parser.set_defaults(func=cmd_parse)

    # doctor 命令
    doctor_parser = subparsers.add_parser('doctor', help='检查运行环境依赖')
    doctor_parser.add_argument('--redis-url', help='验证 Redis 连接，例如 redis://localhost:6379/0')
    doctor_parser.add_argument('--json', action='store_true', help='以 JSON 输出检查结果')
    doctor_parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    doctor_parser.set_defaults(func=cmd_doctor)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
