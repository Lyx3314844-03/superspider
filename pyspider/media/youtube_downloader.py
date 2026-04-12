"""
YouTube 视频下载器
支持 YouTube 视频信息提取和下载
"""

import re
import json
import os
from typing import Optional, Dict, List
from dataclasses import dataclass
import logging
import requests

logger = logging.getLogger(__name__)


@dataclass
class YouTubeVideoData:
    """YouTube 视频数据"""

    title: str
    video_id: str
    author: str
    duration: int
    description: str = ""
    thumbnail: str = ""
    formats: List[Dict] = None
    video_url: Optional[str] = None
    audio_url: Optional[str] = None

    def __post_init__(self):
        if self.formats is None:
            self.formats = []


class YouTubeParser:
    """YouTube 视频解析器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def extract_video_info(self, html: str) -> Optional[YouTubeVideoData]:
        """从 HTML 提取视频信息"""
        # 查找 ytInitialPlayerResponse
        patterns = [
            r"ytInitialPlayerResponse\s*=\s*({.+?});",
            r"var\s+ytInitialPlayerResponse\s*=\s*({.+?});",
        ]

        player_response = None
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                try:
                    player_response = json.loads(match.group(1))
                    break
                except json.JSONDecodeError as e:
                    logger.debug(f"JSON 解析失败：{e}")

        if not player_response:
            logger.error("无法找到视频数据")
            return None

        video_data = YouTubeVideoData(
            title="",
            video_id="",
            author="",
            duration=0,
        )

        # 提取视频详情
        video_details = player_response.get("videoDetails", {})
        if video_details:
            video_data.title = video_details.get("title", "")
            video_data.video_id = video_details.get("videoId", "")
            video_data.author = video_details.get("author", "")
            video_data.duration = int(video_details.get("lengthSeconds", 0))
            video_data.description = video_details.get("shortDescription", "")

            # 提取缩略图
            thumbnail = video_details.get("thumbnail", {})
            thumbnails = thumbnail.get("thumbnails", [])
            if thumbnails:
                video_data.thumbnail = thumbnails[-1].get("url", "")

        # 提取流媒体数据
        streaming_data = player_response.get("streamingData", {})
        if streaming_data:
            # 提取普通格式（带音频的视频）
            formats = streaming_data.get("formats", [])
            adaptive_formats = streaming_data.get("adaptiveFormats", [])

            for fmt in formats + adaptive_formats:
                format_info = {
                    "itag": fmt.get("itag"),
                    "mimeType": fmt.get("mimeType", ""),
                    "quality": fmt.get("quality", ""),
                    "width": fmt.get("width", 0),
                    "height": fmt.get("height", 0),
                    "bitrate": fmt.get("bitrate", 0),
                    "url": fmt.get("url", ""),
                    "hasAudio": self._has_audio(fmt.get("mimeType", "")),
                    "hasVideo": self._has_video(fmt.get("mimeType", "")),
                    "codecs": fmt.get("codecs", ""),
                }
                video_data.formats.append(format_info)

                # 选择最佳格式（带音频的视频）
                if (
                    format_info["hasAudio"]
                    and format_info["hasVideo"]
                    and not video_data.video_url
                ):
                    video_data.video_url = format_info["url"]

        if not video_data.video_url and video_data.formats:
            logger.error("未找到可下载的视频流")
            return None

        return video_data

    def _has_audio(self, mime_type: str) -> bool:
        """检查是否包含音频"""
        audio_codecs = ["mp4a", "opus", "ac-3", "webma"]
        return any(codec in mime_type for codec in audio_codecs)

    def _has_video(self, mime_type: str) -> bool:
        """检查是否包含视频"""
        video_indicators = ["video/", "avc", "vp9", "vp8", "hevc"]
        return any(ind in mime_type for ind in video_indicators)

    def parse(self, url: str, html: Optional[str] = None) -> Optional[YouTubeVideoData]:
        """解析 YouTube 视频"""
        # 提取视频 ID
        video_id = self._extract_video_id(url)
        if not video_id:
            logger.error("无法提取视频 ID")
            return None

        logger.info(f"解析 YouTube 视频：{video_id}")

        # 如果没有提供 HTML，获取页面
        if not html:
            try:
                resp = self.session.get(url, timeout=30)
                html = resp.text
            except Exception as e:
                logger.error(f"获取页面失败：{e}")
                return None

        return self.extract_video_info(html)

    def _extract_video_id(self, url: str) -> Optional[str]:
        """从 URL 提取视频 ID"""
        patterns = [
            r"[?&]v=([a-zA-Z0-9_-]+)",
            r"youtu\.be/([a-zA-Z0-9_-]+)",
            r"/embed/([a-zA-Z0-9_-]+)",
            r"/v/([a-zA-Z0-9_-]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None


class YouTubeDownloader:
    """YouTube 视频下载器"""

    def __init__(self, output_dir: str = "./downloads"):
        self.output_dir = output_dir
        self.parser = YouTubeParser()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.youtube.com/",
            }
        )

    def download(self, url: str, quality: str = "best") -> Optional[str]:
        """下载 YouTube 视频"""
        # 解析视频
        video_data = self.parser.parse(url)
        if not video_data:
            logger.error("解析视频失败")
            return None

        print("\n📺 YouTube 视频信息:")
        print(f"  标题：{video_data.title}")
        print(f"  作者：{video_data.author}")
        print(f"  时长：{video_data.duration}秒")
        print(f"  可用格式：{len(video_data.formats)}")

        # 选择格式
        best_format = self._select_format(video_data.formats, quality)
        if not best_format:
            logger.error("未找到合适的视频格式")
            return None

        print(
            f"  选择格式：{best_format['quality']} ({best_format['width']}x{best_format['height']})"
        )

        # 清理文件名
        safe_title = self._sanitize_filename(video_data.title)
        output_file = os.path.join(
            self.output_dir, f"{safe_title}_{video_data.video_id}.mp4"
        )

        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)

        # 下载视频
        print("\n⬇️  正在下载...")
        try:
            resp = self.session.get(best_format["url"], stream=True, timeout=60)
            resp.raise_for_status()

            with open(output_file, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"✅ 下载完成：{output_file}")
            return output_file

        except Exception as e:
            logger.error(f"下载失败：{e}")
            return None

    def _select_format(self, formats: List[Dict], quality: str) -> Optional[Dict]:
        """选择最佳格式"""
        # 过滤出带音频的视频格式
        video_formats = [f for f in formats if f["hasAudio"] and f["hasVideo"]]

        if not video_formats:
            return None

        # 按高度排序
        video_formats.sort(key=lambda x: x["height"], reverse=True)

        if quality == "best":
            return video_formats[0]
        elif quality == "1080p":
            for f in video_formats:
                if f["height"] >= 1080:
                    return f
            return video_formats[0]
        elif quality == "720p":
            for f in video_formats:
                if f["height"] >= 720:
                    return f
            return video_formats[0]
        elif quality == "480p":
            for f in video_formats:
                if f["height"] >= 480:
                    return f
            return video_formats[0]

        return video_formats[0]

    def _sanitize_filename(self, name: str) -> str:
        """清理文件名"""
        invalid_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
        for c in invalid_chars:
            name = name.replace(c, "")
        name = name.strip()
        if len(name) > 100:
            name = name[:100]
        return name


# 使用示例
if __name__ == "__main__":
    import sys

    downloader = YouTubeDownloader(output_dir="./downloads")

    if len(sys.argv) > 1:
        url = sys.argv[1]
        quality = sys.argv[2] if len(sys.argv) > 2 else "best"

        print(f"下载 YouTube 视频：{url}")
        result = downloader.download(url, quality)

        if result:
            print(f"\n✓ 下载成功：{result}")
        else:
            print("\n✗ 下载失败")
    else:
        print("用法：python youtube_downloader.py <youtube_url> [quality]")
        print(
            "示例：python youtube_downloader.py https://www.youtube.com/watch?v=xxx 1080p"
        )
