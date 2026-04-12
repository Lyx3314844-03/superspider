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
from typing import Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyspider.media.hls_downloader import HLSDownloader, DASHDownloader
from pyspider.media.drm_detector import DRMDetector, DRMHandler, check_drm_status
from pyspider.media.ffmpeg_tools import FFmpegExecutor, FFmpegTools, FFmpegNotFoundError
from pyspider.media.multimedia_downloader import create_multimedia_spider
from pyspider.media.video_parser import UniversalParser, VideoData
from pyspider.media.youtube_downloader import YouTubeDownloader
from pyspider.cli.dependencies import dependency_report_to_dict
from pyspider.cli.dependencies import run_dependency_doctor as collect_dependency_doctor
from pyspider.cli.dependencies import resolve_ffmpeg_path


def setup_logging(verbose: bool = False):
    """设置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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
    return collect_dependency_doctor(
        config_path=getattr(args, "config", None),
        redis_url=getattr(args, "redis_url", None),
    )


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


def _load_artifact_text(path_value: Optional[str]) -> str:
    if not path_value:
        return ""
    return Path(path_value).read_text(encoding="utf-8", errors="ignore")


def _discover_artifact_path(
    artifact_dir: Optional[str],
    current_value: Optional[str],
    candidates: list[str],
    patterns: list[str],
) -> str:
    if current_value:
        return current_value
    if not artifact_dir:
        return ""

    root = Path(artifact_dir)
    if not root.is_dir():
        return ""

    for candidate in candidates:
        path = root / candidate
        if path.is_file():
            return str(path)
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                return str(path)
    return ""


def _resolve_artifact_bundle(args) -> tuple[str, str, str]:
    artifact_dir = getattr(args, "artifact_dir", "")
    html_file = _discover_artifact_path(
        artifact_dir,
        getattr(args, "html_file", ""),
        [
            "page.html",
            "content.html",
            "document.html",
            "browser.html",
            "response.html",
            "index.html",
        ],
        ["*page*.html", "*content*.html", "*.html"],
    )
    network_file = _discover_artifact_path(
        artifact_dir,
        getattr(args, "network_file", ""),
        [
            "network.json",
            "requests.json",
            "trace.json",
            "network.log",
            "network.txt",
        ],
        ["*network*.json", "*request*.json", "*trace*.json", "*network*.txt"],
    )
    har_file = _discover_artifact_path(
        artifact_dir,
        getattr(args, "har_file", ""),
        [
            "trace.har",
            "network.har",
            "session.har",
            "browser.har",
            "page.har",
        ],
        ["*.har"],
    )
    return html_file, network_file, har_file


def _video_payload(args, video_data: VideoData) -> dict:
    return {
        "command": "parse",
        "runtime": "python",
        "url": getattr(args, "url", "") or "https://example.com/",
        "artifact_dir": getattr(args, "artifact_dir", "") or "",
        "html_file": getattr(args, "html_file", "") or "",
        "network_file": getattr(args, "network_file", "") or "",
        "har_file": getattr(args, "har_file", "") or "",
        "video": {
            "platform": video_data.platform,
            "title": video_data.title,
            "video_id": video_data.video_id,
            "m3u8_url": video_data.m3u8_url,
            "mp4_url": video_data.mp4_url,
            "dash_url": video_data.dash_url,
            "download_url": video_data.download_url,
            "cover_url": video_data.cover_url,
            "duration": video_data.duration,
            "description": video_data.description,
            "quality_options": list(video_data.quality_options or []),
        },
    }


def _parse_video_input(args, logger: logging.Logger) -> Optional[VideoData]:
    parser = UniversalParser()
    html_file, network_file, har_file = _resolve_artifact_bundle(args)
    setattr(args, "html_file", html_file)
    setattr(args, "network_file", network_file)
    setattr(args, "har_file", har_file)
    html = _load_artifact_text(html_file)
    network = _load_artifact_text(network_file)
    har = _load_artifact_text(har_file)
    artifact_texts = [text for text in (network, har) if text]

    if html or artifact_texts:
        page_url = getattr(args, "url", "") or "https://example.com/"
        logger.info(f"解析 artifact 视频输入：{page_url}")
        return parser.parse_artifacts(page_url, html=html, artifact_texts=artifact_texts)

    target_url = getattr(args, "url", "")
    if not target_url:
        logger.error("需要提供 URL 或至少一个 artifact 文件")
        return None

    logger.info(f"解析视频：{target_url}")
    return parser.parse(target_url)


def _download_video_data(args, logger: logging.Logger, video_data: VideoData) -> tuple[int, Optional[str]]:
    download_url = resolve_download_url(
        video_data, getattr(args, "quality", None), logger
    )

    if not download_url:
        logger.error("未找到可下载的 URL")
        return 1, None

    if video_data.m3u8_url and download_url == video_data.m3u8_url:
        logger.info("使用 HLS 下载")
    elif video_data.mp4_url and download_url == video_data.mp4_url:
        logger.info("使用 MP4 下载")
    elif video_data.dash_url and download_url == video_data.dash_url:
        logger.info("使用 DASH 下载")
    else:
        logger.info("使用通用下载地址")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_name or video_data.video_id

    if ".m3u8" in download_url:
        downloader = HLSDownloader(
            output_dir=str(output_dir),
            max_workers=args.workers,
            retry_times=args.retries,
        )
        success = downloader.download(download_url, output_name)
        if not success:
            return 1, None
        output_file = output_dir / f"{output_name}.ts"
        logger.info(f"✓ 下载完成：{output_file}")
        if args.convert:
            return (0 if convert_video(output_file, args.convert, args) else 1), str(output_file)
        return 0, str(output_file)

    if ".mpd" in download_url:
        downloader = DASHDownloader(
            output_dir=str(output_dir),
            max_workers=args.workers,
        )
        success = downloader.download(download_url, output_name)
        if not success:
            return 1, None
        output_file = output_dir / f"{output_name}.mp4"
        logger.info(f"✓ 下载完成：{output_file}")
        if args.convert:
            return (0 if convert_video(output_file, args.convert, args) else 1), str(output_file)
        return 0, str(output_file)

    import requests

    try:
        logger.info(f"下载 MP4: {download_url}")
        resp = requests.get(download_url, stream=True, timeout=3600)
        resp.raise_for_status()

        output_file = output_dir / f"{output_name}.mp4"
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with open(output_file, "wb") as f:
            for chunk in resp.iter_content(8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        percent = downloaded / total * 100
                        print(f"\r进度：{percent:.1f}%", end="", flush=True)

        print()
        logger.info(f"✓ 下载完成：{output_file}")

        if args.convert:
            return (0 if convert_video(output_file, args.convert, args) else 1), str(output_file)
        return 0, str(output_file)

    except Exception as e:
        logger.error(f"下载失败：{e}")
        return 1, None


def cmd_download(args):
    """下载视频"""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    video_data = _parse_video_input(args, logger)

    if not video_data:
        logger.error("无法解析视频")
        return 1

    logger.info(f"✓ 解析成功：{video_data.title}")
    logger.info(f"  平台：{video_data.platform}")

    exit_code, _ = _download_video_data(args, logger, video_data)
    return exit_code


def cmd_artifact(args):
    """统一 artifact-driven 视频入口。"""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    if not args.artifact_dir:
        logger.error("artifact 命令需要 --artifact-dir")
        return 2

    video_data = _parse_video_input(args, logger)
    if not video_data:
        logger.error("无法从 artifact 解析视频")
        return 1

    payload = _video_payload(args, video_data)
    payload["command"] = "artifact"
    payload["runtime"] = "python"
    payload["download"] = {"requested": bool(args.download), "output": None}

    if args.download:
        exit_code, output_path = _download_video_data(args, logger, video_data)
        payload["download"]["output"] = output_path
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return exit_code

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_convert(args):
    """转换视频格式"""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        tools = create_ffmpeg_tools(args.config)

        logger.info(f"转换视频：{args.input} -> {args.output}")

        if args.format in {"mp4", "avi", "mkv"}:
            success = tools.convert_format(
                args.input,
                args.output,
                output_format=args.format,
                video_codec=args.video_codec or "libx264",
                audio_codec=args.audio_codec or "aac",
                crf=args.crf or 23,
            )
        elif args.format == "mp3":
            success = tools.extract_audio(
                args.input,
                args.output,
                audio_format="mp3",
                bitrate=args.audio_bitrate or "192k",
            )
        elif args.format == "gif":
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
            print("\n视频信息:")
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
            output_file = args.output or "screenshot.jpg"
            success = tools.take_screenshot(
                args.input,
                output_file,
                timestamp=args.timestamp or "00:00:01",
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
        print(
            json.dumps(dependency_report_to_dict(report), ensure_ascii=False, indent=2)
        )
        return report.exit_code

    labels = {
        "ok": "OK",
        "warn": "WARN",
        "fail": "FAIL",
        "skip": "SKIP",
    }

    print("Runtime dependency report:")
    for status in report.statuses:
        print(
            f"[{labels.get(status.level, status.level.upper())}] {status.name}: {status.message}"
        )
    print(f"Summary: {report.summary}")
    return report.exit_code


def cmd_youtube(args):
    """下载 YouTube 视频"""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    downloader = YouTubeDownloader(output_dir=args.output_dir)

    logger.info(f"下载 YouTube 视频：{args.url}")
    result = downloader.download(args.url, args.quality)

    if result:
        logger.info(f"✓ 下载成功：{result}")
        return 0
    else:
        logger.error("✗ 下载失败")
        return 1


def cmd_parse(args):
    """解析视频 URL"""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    video_data = _parse_video_input(args, logger)

    if video_data:
        if getattr(args, "json", False):
            print(json.dumps(_video_payload(args, video_data), ensure_ascii=False, indent=2))
            return 0
        print("\n视频信息:")
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


def cmd_drm(args):
    """检测 DRM 信息。"""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        payload = inspect_drm_source(
            url=args.url or "",
            input_path=args.input or "",
            inline_content=args.content or "",
            content_file=args.content_file or "",
        )
    except ValueError as exc:
        logger.error(str(exc))
        return 2
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        logger.error(f"DRM 检测失败：{exc}")
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_multimedia(args):
    """抓取页面中的多媒体资源。"""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    spider = create_multimedia_spider(args.urls, output_dir=args.output_dir)
    logger.info("使用多媒体爬虫：%s", spider.__class__.__name__)

    videos = spider.crawl_videos()
    images = spider.crawl_images()
    audios = spider.crawl_audios()
    spider.save_metadata()

    payload = {
        "command": "multimedia",
        "spider": spider.__class__.__name__,
        "urls": list(args.urls),
        "counts": {
            "videos": len(videos),
            "images": len(images),
            "audios": len(audios),
        },
        "videos": [item.to_dict() for item in videos],
        "images": [item.to_dict() for item in images],
        "audios": [item.to_dict() for item in audios],
    }

    if args.download:
        payload["download"] = spider.download_all(max_workers=args.workers)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def inspect_drm_source(
    *, url: str, input_path: str, inline_content: str, content_file: str
) -> dict:
    source_kind = ""
    source_value = ""
    content = ""

    if content_file:
        source_kind = "content-file"
        source_value = content_file
        content = Path(content_file).read_text(encoding="utf-8")
    elif inline_content:
        source_kind = "inline-content"
        source_value = "inline"
        content = inline_content
    elif input_path:
        path = Path(input_path)
        if not path.exists():
            raise ValueError(f"输入文件不存在：{input_path}")
        source_kind = "input"
        source_value = str(path)
        if path.suffix.lower() in {".m3u8", ".mpd", ".txt"}:
            content = path.read_text(encoding="utf-8", errors="ignore")
        else:
            detector = DRMDetector()
            handler = DRMHandler()
            drm_info = detector.detect_from_video_file(str(path))
            downloadable, message = handler.is_downloadable(drm_info)
            return {
                "command": "drm",
                "source": {"kind": source_kind, "value": source_value},
                "drm_info": drm_info.to_dict(),
                "downloadable": downloadable,
                "message": message,
            }
    elif url:
        import requests

        source_kind = "url"
        source_value = url
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        content = response.text
    else:
        raise ValueError("drm 需要 --url、--input、--content 或 --content-file")

    payload = check_drm_status(content, url or source_value)
    payload["command"] = "drm"
    payload["source"] = {"kind": source_kind, "value": source_value}
    return payload


def convert_video(input_file: Path, output_format: str, args):
    """转换视频格式"""
    logger = logging.getLogger(__name__)

    try:
        tools = create_ffmpeg_tools(getattr(args, "config", None))
        output_file = input_file.with_suffix(f".{output_format}")

        logger.info(f"转换格式：{input_file} -> {output_file}")

        if output_format == "mp4":
            success = tools.convert_format(str(input_file), str(output_file))
        elif output_format == "mp3":
            success = tools.extract_audio(str(input_file), str(output_file))
        elif output_format == "gif":
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
        description="视频下载命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 下载视频
  %(prog)s download https://v.youku.com/v_show/id_X.html
  
  # 下载并转换格式
  %(prog)s download https://v.youku.com/v_show/id_X.html --convert mp4
  
  # 解析视频 URL
  %(prog)s parse https://v.youku.com/v_show/id_X.html

  # 检测 manifest DRM
  %(prog)s drm --content "#EXTM3U..."
  
  # 获取视频信息
  %(prog)s info video.mp4
  
  # 转换视频格式
  %(prog)s convert input.flv output.mp4
  
  # 截取截图
  %(prog)s screenshot video.mp4 --batch
  
  # 合并视频
  %(prog)s merge video1.mp4 video2.mp4 -o merged.mp4
        """,
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("--config", help="配置文件路径")

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # download 命令
    download_parser = subparsers.add_parser("download", help="下载视频")
    download_parser.add_argument("url", nargs="?", help="视频 URL")
    download_parser.add_argument(
        "-o", "--output-dir", default="downloads", help="输出目录"
    )
    download_parser.add_argument("-n", "--output-name", help="输出文件名")
    download_parser.add_argument("-w", "--workers", type=int, default=10, help="并发数")
    download_parser.add_argument(
        "-r", "--retries", type=int, default=3, help="重试次数"
    )
    download_parser.add_argument(
        "-q", "--quality", choices=["best", "1080p", "720p", "480p"], help="质量"
    )
    download_parser.add_argument(
        "-c", "--convert", choices=["mp4", "mp3", "gif"], help="转换格式"
    )
    download_parser.add_argument("--html-file", help="浏览器抓取的 HTML artifact")
    download_parser.add_argument(
        "--network-file", help="浏览器抓取的 network artifact"
    )
    download_parser.add_argument("--har-file", help="浏览器抓取的 HAR artifact")
    download_parser.add_argument(
        "--artifact-dir", help="浏览器产物目录，会自动发现 html/network/har 文件"
    )
    download_parser.add_argument(
        "-v", "--verbose", action="store_true", help="详细输出"
    )
    download_parser.set_defaults(func=cmd_download)

    # convert 命令
    convert_parser = subparsers.add_parser("convert", help="转换视频格式")
    convert_parser.add_argument("input", help="输入文件")
    convert_parser.add_argument("output", help="输出文件")
    convert_parser.add_argument(
        "-f",
        "--format",
        required=True,
        choices=["mp4", "mp3", "gif", "avi", "mkv"],
        help="目标格式",
    )
    convert_parser.add_argument("--video-codec", help="视频编码器")
    convert_parser.add_argument("--audio-codec", help="音频编码器")
    convert_parser.add_argument("--crf", type=int, help="质量因子")
    convert_parser.add_argument("--audio-bitrate", help="音频比特率")
    convert_parser.add_argument("--fps", type=int, help="帧率（GIF）")
    convert_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    convert_parser.set_defaults(func=cmd_convert)

    # info 命令
    info_parser = subparsers.add_parser("info", help="获取视频信息")
    info_parser.add_argument("input", help="输入文件")
    info_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    info_parser.set_defaults(func=cmd_info)

    # screenshot 命令
    screenshot_parser = subparsers.add_parser("screenshot", help="截取截图")
    screenshot_parser.add_argument("input", help="输入文件")
    screenshot_parser.add_argument("-o", "--output", help="输出文件")
    screenshot_parser.add_argument("-t", "--timestamp", help="时间戳")
    screenshot_parser.add_argument("-w", "--width", type=int, help="宽度")
    screenshot_parser.add_argument(
        "-b", "--batch", action="store_true", help="批量截图"
    )
    screenshot_parser.add_argument(
        "--interval", type=int, default=60, help="截图间隔（秒）"
    )
    screenshot_parser.add_argument("--output-dir", help="输出目录（批量）")
    screenshot_parser.add_argument(
        "-v", "--verbose", action="store_true", help="详细输出"
    )
    screenshot_parser.set_defaults(func=cmd_screenshot)

    # merge 命令
    merge_parser = subparsers.add_parser("merge", help="合并视频")
    merge_parser.add_argument("inputs", nargs="+", help="输入文件列表")
    merge_parser.add_argument("-o", "--output", required=True, help="输出文件")
    merge_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    merge_parser.set_defaults(func=cmd_merge)

    # parse 命令
    parse_parser = subparsers.add_parser("parse", help="解析视频 URL")
    parse_parser.add_argument("url", nargs="?", help="视频 URL")
    parse_parser.add_argument("--html-file", help="浏览器抓取的 HTML artifact")
    parse_parser.add_argument("--network-file", help="浏览器抓取的 network artifact")
    parse_parser.add_argument("--har-file", help="浏览器抓取的 HAR artifact")
    parse_parser.add_argument(
        "--artifact-dir", help="浏览器产物目录，会自动发现 html/network/har 文件"
    )
    parse_parser.add_argument("--json", action="store_true", help="以 JSON 输出解析结果")
    parse_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parse_parser.set_defaults(func=cmd_parse)

    # drm 命令
    drm_parser = subparsers.add_parser("drm", help="检测媒体或清单中的 DRM 信息")
    drm_parser.add_argument("--url", help="远程清单或页面 URL")
    drm_parser.add_argument("--input", help="本地媒体文件或清单文件路径")
    drm_parser.add_argument("--content", help="直接传入 manifest 内容")
    drm_parser.add_argument("--content-file", help="本地 manifest 文本文件路径")
    drm_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    drm_parser.set_defaults(func=cmd_drm)

    # multimedia 命令
    multimedia_parser = subparsers.add_parser(
        "multimedia", help="抓取页面中的视频/图片/音频资源"
    )
    multimedia_parser.add_argument("urls", nargs="+", help="页面 URL 列表")
    multimedia_parser.add_argument(
        "-o", "--output-dir", default="downloads", help="输出目录"
    )
    multimedia_parser.add_argument(
        "-w", "--workers", type=int, default=3, help="下载并发数"
    )
    multimedia_parser.add_argument(
        "--download", action="store_true", help="抓取后立即下载全部资源"
    )
    multimedia_parser.add_argument(
        "-v", "--verbose", action="store_true", help="详细输出"
    )
    multimedia_parser.set_defaults(func=cmd_multimedia)

    # youtube 命令
    youtube_parser = subparsers.add_parser("youtube", help="下载 YouTube 视频")
    youtube_parser.add_argument("url", help="YouTube 视频 URL")
    youtube_parser.add_argument(
        "-o", "--output-dir", default="downloads", help="输出目录"
    )
    youtube_parser.add_argument(
        "-q",
        "--quality",
        choices=["best", "1080p", "720p", "480p"],
        default="best",
        help="质量",
    )
    youtube_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    youtube_parser.set_defaults(func=cmd_youtube)

    # artifact 命令
    artifact_parser = subparsers.add_parser("artifact", help="从 browser/network/har artifact 驱动视频解析或下载")
    artifact_parser.add_argument("--url", default="https://example.com/", help="原始页面 URL")
    artifact_parser.add_argument("--artifact-dir", required=True, help="artifact 目录")
    artifact_parser.add_argument("--html-file", help="显式指定 HTML artifact")
    artifact_parser.add_argument("--network-file", help="显式指定 network artifact")
    artifact_parser.add_argument("--har-file", help="显式指定 HAR artifact")
    artifact_parser.add_argument("--download", action="store_true", help="解析后立即下载")
    artifact_parser.add_argument("-o", "--output-dir", default="downloads", help="输出目录")
    artifact_parser.add_argument("-n", "--output-name", help="输出文件名")
    artifact_parser.add_argument("-w", "--workers", type=int, default=10, help="并发数")
    artifact_parser.add_argument("-r", "--retries", type=int, default=3, help="重试次数")
    artifact_parser.add_argument("-q", "--quality", choices=["best", "1080p", "720p", "480p"], help="质量")
    artifact_parser.add_argument("-c", "--convert", choices=["mp4", "mp3", "gif"], help="转换格式")
    artifact_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    artifact_parser.set_defaults(func=cmd_artifact)

    # doctor 命令
    doctor_parser = subparsers.add_parser("doctor", help="检查运行环境依赖")
    doctor_parser.add_argument(
        "--redis-url", help="验证 Redis 连接，例如 redis://localhost:6379/0"
    )
    doctor_parser.add_argument(
        "--json", action="store_true", help="以 JSON 输出检查结果"
    )
    doctor_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    doctor_parser.set_defaults(func=cmd_doctor)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
