"""
pyspider 多媒体下载模块
支持视频、图片、音乐批量下载
"""

import sys
import time
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import re
import requests

sys.path.insert(0, "C:/Users/Administrator/spider")


@dataclass
class MediaItem:
    """媒体项基类"""

    id: str = ""
    title: str = ""
    url: str = ""
    thumbnail: str = ""
    duration: str = ""
    size: int = 0
    format: str = ""
    quality: str = ""
    downloaded: bool = False
    download_path: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VideoItem(MediaItem):
    """视频项"""

    channel: str = ""
    views: str = ""
    published: str = ""
    description: str = ""
    index: int = 0


@dataclass
class ImageItem(MediaItem):
    """图片项"""

    width: int = 0
    height: int = 0
    alt: str = ""
    source: str = ""


@dataclass
class AudioItem(MediaItem):
    """音频项"""

    artist: str = ""
    album: str = ""
    track: int = 0
    lyrics: str = ""


class MediaDownloader:
    """媒体下载器"""

    def __init__(self, output_dir: str = "downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

    def download_file(self, url: str, save_path: Path, timeout: int = 300) -> bool:
        """下载文件"""
        try:
            print(f"   📥 下载：{url}")

            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # 显示进度
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\r   进度：{progress:.1f}%", end="", flush=True)

            print(f"\r   ✓ 下载完成：{save_path.name}")
            return True

        except Exception as e:
            print(f"\n   ❌ 下载失败：{e}")
            return False

    def download_video(self, video: VideoItem, quality: str = "best") -> bool:
        """下载视频"""
        try:
            # 创建视频目录
            video_dir = self.output_dir / "videos"
            video_dir.mkdir(exist_ok=True)

            # 生成文件名
            safe_title = self._sanitize_filename(video.title)
            ext = "mp4"
            filename = f"{safe_title}.{ext}"
            save_path = video_dir / filename

            # 处理 YouTube URL
            if "youtube.com" in video.url or "youtu.be" in video.url:
                return self._download_youtube_video(video.url, save_path, quality)

            # 普通下载
            return self.download_file(video.url, save_path)

        except Exception as e:
            video.error = str(e)
            return False

    def download_audio(self, audio: AudioItem, format: str = "mp3") -> bool:
        """下载音频"""
        try:
            # 创建音频目录
            audio_dir = self.output_dir / "audios"
            audio_dir.mkdir(exist_ok=True)

            # 生成文件名
            safe_title = self._sanitize_filename(audio.title)
            filename = f"{safe_title}.{format}"
            save_path = audio_dir / filename

            return self.download_file(audio.url, save_path)

        except Exception as e:
            audio.error = str(e)
            return False

    def download_image(self, image: ImageItem) -> bool:
        """下载图片"""
        try:
            # 创建图片目录
            image_dir = self.output_dir / "images"
            image_dir.mkdir(exist_ok=True)

            # 生成文件名
            safe_title = self._sanitize_filename(image.title or image.alt)
            ext = self._get_image_extension(image.url)
            filename = f"{safe_title}.{ext}"
            save_path = image_dir / filename

            return self.download_file(image.url, save_path)

        except Exception as e:
            image.error = str(e)
            return False

    def download_batch(
        self, items: List[MediaItem], max_workers: int = 3
    ) -> Dict[str, Any]:
        """批量下载"""
        stats = {
            "total": len(items),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": datetime.now().isoformat(),
            "items": [],
        }

        print(f"\n📦 开始批量下载 {len(items)} 个文件...")
        print(f"   并发数：{max_workers}")
        print(f"   输出目录：{self.output_dir}")
        print()

        for i, item in enumerate(items, 1):
            print(f"[{i}/{len(items)}] ", end="")

            # 检查是否已下载
            if self._is_already_downloaded(item):
                print("⏭️  跳过（已存在）")
                stats["skipped"] += 1
                continue

            # 下载
            success = False

            if isinstance(item, VideoItem):
                success = self.download_video(item)
            elif isinstance(item, AudioItem):
                success = self.download_audio(item)
            elif isinstance(item, ImageItem):
                success = self.download_image(item)

            if success:
                stats["success"] += 1
                item.downloaded = True
                item.download_path = str(self.output_dir)
            else:
                stats["failed"] += 1

            stats["items"].append(item.to_dict())

            # 礼貌延迟
            time.sleep(0.5)

        stats["end_time"] = datetime.now().isoformat()
        self._save_download_log(stats)

        return stats

    def _download_youtube_video(self, url: str, save_path: Path, quality: str) -> bool:
        """下载 YouTube 视频（使用 yt-dlp）"""
        try:
            import subprocess

            # 检查 yt-dlp 是否安装
            result = subprocess.run(
                ["yt-dlp", "--version"], capture_output=True, text=True
            )

            if result.returncode != 0:
                print("   ⚠️  yt-dlp 未安装，尝试使用 pip 安装...")
                subprocess.run(["pip", "install", "yt-dlp"])

            # 构建命令
            cmd = [
                "yt-dlp",
                "-o",
                str(save_path),
                "--no-playlist",
            ]

            if quality == "best":
                cmd.extend(["-f", "bestvideo+bestaudio/best"])
            elif quality == "720":
                cmd.extend(["-f", "bestvideo[height<=720]+bestaudio/best[height<=720]"])
            elif quality == "audio":
                cmd.extend(["-x", "--audio-format", "mp3"])

            cmd.append(url)

            # 执行下载
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print("   ✓ YouTube 视频下载完成")
                return True
            else:
                print(f"   ❌ YouTube 下载失败：{result.stderr}")
                return False

        except Exception as e:
            print(f"   ❌ YouTube 下载异常：{e}")
            return False

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名"""
        if not filename:
            return "untitled"

        # 移除非法字符
        illegal_chars = '<>:"/\\|？*'
        for char in illegal_chars:
            filename = filename.replace(char, "_")

        # 限制长度
        if len(filename) > 100:
            filename = filename[:100]

        return filename.strip()

    def _get_image_extension(self, url: str) -> str:
        """从 URL 获取图片扩展名"""
        ext_map = {
            "jpg": "jpeg",
            "jpeg": "jpeg",
            "png": "png",
            "gif": "gif",
            "webp": "webp",
            "bmp": "bmp",
            "svg": "svg",
        }

        url_lower = url.lower()
        for ext in ext_map.keys():
            if f".{ext}" in url_lower or f"{ext}?" in url_lower:
                return ext_map[ext]

        # 默认返回 jpeg
        return "jpeg"

    def _is_already_downloaded(self, item: MediaItem) -> bool:
        """检查是否已下载"""
        if not item.title:
            return False

        safe_title = self._sanitize_filename(item.title)

        if isinstance(item, VideoItem):
            check_dir = self.output_dir / "videos"
        elif isinstance(item, AudioItem):
            check_dir = self.output_dir / "audios"
        elif isinstance(item, ImageItem):
            check_dir = self.output_dir / "images"
        else:
            return False

        # 检查是否存在同名文件
        for ext in ["mp4", "mkv", "webm", "mp3", "wav", "flac", "jpg", "png", "gif"]:
            if (check_dir / f"{safe_title}.{ext}").exists():
                return True

        return False

    def _save_download_log(self, stats: Dict[str, Any]):
        """保存下载日志"""
        log_file = self.output_dir / "download_log.json"

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        print(f"\n📝 下载日志已保存到：{log_file}")


class MultiMediaSpider:
    """多媒体爬虫基类"""

    def __init__(self, urls: List[str], output_dir: str = "downloads"):
        self.urls = urls
        self.output_dir = output_dir
        self.downloader = MediaDownloader(output_dir)
        self.videos: List[VideoItem] = []
        self.images: List[ImageItem] = []
        self.audios: List[AudioItem] = []

    def crawl_videos(self) -> List[VideoItem]:
        """爬取页面中的通用视频资源"""
        self.videos = []
        seen = set()

        for page_url in self.urls:
            html = self._fetch_html(page_url)
            if not html:
                continue

            title = self._extract_title(html) or page_url
            video_urls = self._extract_media_urls(
                html,
                patterns=[
                    r'<meta[^>]+property=["\']og:video["\'][^>]+content=["\']([^"\']+)["\']',
                    r'<video[^>]+src=["\']([^"\']+)["\']',
                    r'<source[^>]+src=["\']([^"\']+\.(?:mp4|m3u8|webm|mov)(?:\?[^"\']*)?)["\']',
                    r'<meta[^>]+name=["\']twitter:player:stream["\'][^>]+content=["\']([^"\']+)["\']',
                ],
                base_url=page_url,
            )

            for index, video_url in enumerate(video_urls, 1):
                if video_url in seen:
                    continue
                seen.add(video_url)

                video = VideoItem()
                video.id = hashlib.md5(video_url.encode()).hexdigest()[:12]
                video.title = (
                    f"{title} - 视频 {index}" if len(video_urls) > 1 else title
                )
                video.url = video_url
                video.index = len(self.videos) + 1
                self.videos.append(video)

        return self.videos

    def crawl_images(self) -> List[ImageItem]:
        """爬取页面中的通用图片资源"""
        self.images = []
        seen = set()

        for page_url in self.urls:
            html = self._fetch_html(page_url)
            if not html:
                continue

            title = self._extract_title(html) or page_url
            image_urls = self._extract_media_urls(
                html,
                patterns=[
                    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                    r'<img[^>]+src=["\']([^"\']+)["\']',
                ],
                base_url=page_url,
            )

            for index, image_url in enumerate(image_urls, 1):
                if image_url in seen:
                    continue
                seen.add(image_url)

                image = ImageItem()
                image.id = hashlib.md5(image_url.encode()).hexdigest()[:12]
                image.title = (
                    f"{title} - 图片 {index}" if len(image_urls) > 1 else title
                )
                image.url = image_url
                image.source = page_url
                self.images.append(image)

        return self.images

    def crawl_audios(self) -> List[AudioItem]:
        """爬取页面中的通用音频资源"""
        self.audios = []
        seen = set()

        for page_url in self.urls:
            html = self._fetch_html(page_url)
            if not html:
                continue

            title = self._extract_title(html) or page_url
            audio_urls = self._extract_media_urls(
                html,
                patterns=[
                    r'<audio[^>]+src=["\']([^"\']+)["\']',
                    r'<source[^>]+src=["\']([^"\']+\.(?:mp3|wav|m4a|aac|flac|ogg)(?:\?[^"\']*)?)["\']',
                    r'href=["\']([^"\']+\.(?:mp3|wav|m4a|aac|flac|ogg)(?:\?[^"\']*)?)["\']',
                ],
                base_url=page_url,
            )

            for index, audio_url in enumerate(audio_urls, 1):
                if audio_url in seen:
                    continue
                seen.add(audio_url)

                audio = AudioItem()
                audio.id = hashlib.md5(audio_url.encode()).hexdigest()[:12]
                audio.title = (
                    f"{title} - 音频 {index}" if len(audio_urls) > 1 else title
                )
                audio.url = audio_url
                self.audios.append(audio)

        return self.audios

    def download_all(self, max_workers: int = 3) -> Dict[str, Any]:
        """下载所有媒体"""
        all_items = self.videos + self.images + self.audios
        return self.downloader.download_batch(all_items, max_workers)

    def save_metadata(self):
        """保存元数据"""
        metadata = {
            "crawl_time": datetime.now().isoformat(),
            "urls": self.urls,
            "videos": [v.to_dict() for v in self.videos],
            "images": [i.to_dict() for i in self.images],
            "audios": [a.to_dict() for a in self.audios],
        }

        meta_file = Path(self.output_dir) / "metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"📋 元数据已保存到：{meta_file}")

    def _fetch_html(self, page_url: str) -> str:
        """抓取页面 HTML，失败时返回空字符串。"""
        try:
            response = self.downloader.session.get(page_url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception:
            return ""

    def _extract_title(self, html: str) -> str:
        """提取页面标题。"""
        match = re.search(
            r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL
        )
        if not match:
            return ""
        return re.sub(r"\s+", " ", match.group(1)).strip()

    def _extract_media_urls(
        self, html: str, patterns: List[str], base_url: str
    ) -> List[str]:
        """按给定模式提取媒体 URL，并转换为绝对 URL。"""
        from urllib.parse import urljoin

        urls = []
        seen = set()
        for pattern in patterns:
            for match in re.findall(pattern, html, flags=re.IGNORECASE):
                media_url = urljoin(base_url, match.strip())
                if media_url and media_url not in seen:
                    seen.add(media_url)
                    urls.append(media_url)
        return urls


class PlatformMultiMediaSpider(MultiMediaSpider):
    """基于平台解析器的多媒体爬虫。"""

    platform_name = "generic"

    def __init__(self, urls: List[str], output_dir: str = "downloads"):
        super().__init__(urls, output_dir)
        self._parsed_videos = []

    def create_parser(self):
        raise NotImplementedError

    def crawl_videos(self) -> List[VideoItem]:
        self.videos = []
        self._parsed_videos = []
        parser = self.create_parser()

        for index, page_url in enumerate(self.urls, 1):
            try:
                video_data = parser.parse(page_url)
            except Exception:
                video_data = None
            if not video_data:
                continue

            stream_url = (
                video_data.download_url
                or video_data.m3u8_url
                or video_data.mp4_url
                or video_data.dash_url
                or page_url
            )

            video = VideoItem()
            video.id = (
                video_data.video_id or hashlib.md5(page_url.encode()).hexdigest()[:12]
            )
            video.title = video_data.title or page_url
            video.url = stream_url
            video.thumbnail = video_data.cover_url or ""
            video.duration = str(video_data.duration) if video_data.duration else ""
            video.description = video_data.description or ""
            video.quality = ", ".join(video_data.quality_options or [])
            video.format = self._detect_stream_format(stream_url)
            video.index = index
            self.videos.append(video)
            self._parsed_videos.append(video_data)

        return self.videos

    def crawl_images(self) -> List[ImageItem]:
        self.images = []
        seen = set()

        for video, parsed in zip(self.videos, self._parsed_videos):
            cover_url = getattr(parsed, "cover_url", None) or video.thumbnail
            if not cover_url or cover_url in seen:
                continue
            seen.add(cover_url)

            image = ImageItem()
            image.id = hashlib.md5(cover_url.encode()).hexdigest()[:12]
            image.title = f"{video.title} - 封面"
            image.url = cover_url
            image.alt = video.title
            image.source = self.platform_name
            self.images.append(image)

        return self.images

    def crawl_audios(self) -> List[AudioItem]:
        self.audios = []
        for video in self.videos:
            audio = AudioItem()
            audio.id = video.id
            audio.title = video.title
            audio.url = video.url
            audio.artist = self.platform_name
            audio.format = "mp3" if "m3u8" not in video.url else "aac"
            self.audios.append(audio)
        return self.audios

    def _detect_stream_format(self, url: str) -> str:
        lowered = (url or "").lower()
        if ".m3u8" in lowered:
            return "hls"
        if ".mpd" in lowered or "dash" in lowered:
            return "dash"
        if ".mp4" in lowered:
            return "mp4"
        return "unknown"


class YoukuMultiMediaSpider(PlatformMultiMediaSpider):
    platform_name = "Youku"

    def create_parser(self):
        from pyspider.media.video_parser import YoukuParser

        return YoukuParser()


class IqiyiMultiMediaSpider(PlatformMultiMediaSpider):
    platform_name = "IQIYI"

    def create_parser(self):
        from pyspider.media.video_parser import IqiyiParser

        return IqiyiParser()


class TencentMultiMediaSpider(PlatformMultiMediaSpider):
    platform_name = "Tencent"

    def create_parser(self):
        from pyspider.media.video_parser import TencentParser

        return TencentParser()


class BilibiliMultiMediaSpider(PlatformMultiMediaSpider):
    platform_name = "Bilibili"

    def create_parser(self):
        from pyspider.media.video_parser import BilibiliParser

        return BilibiliParser()


class DouyinMultiMediaSpider(PlatformMultiMediaSpider):
    platform_name = "Douyin"

    def create_parser(self):
        from pyspider.media.video_parser import DouyinParser

        return DouyinParser()


def create_multimedia_spider(
    urls: List[str], output_dir: str = "downloads"
) -> MultiMediaSpider:
    """根据 URL 选择更合适的平台特化 spider。"""
    lowered = " ".join(urls).lower()
    if any(domain in lowered for domain in ("youtube.com", "youtu.be")):
        return YouTubeMultiMediaSpider(urls, output_dir=output_dir)
    if "youku.com" in lowered or "youku.tv" in lowered:
        return YoukuMultiMediaSpider(urls, output_dir=output_dir)
    if "iqiyi.com" in lowered:
        return IqiyiMultiMediaSpider(urls, output_dir=output_dir)
    if "v.qq.com" in lowered or "qq.com" in lowered:
        return TencentMultiMediaSpider(urls, output_dir=output_dir)
    if "bilibili.com" in lowered or "b23.tv" in lowered:
        return BilibiliMultiMediaSpider(urls, output_dir=output_dir)
    if "douyin.com" in lowered or "iesdouyin.com" in lowered:
        return DouyinMultiMediaSpider(urls, output_dir=output_dir)
    return MultiMediaSpider(urls, output_dir=output_dir)


# YouTube 多媒体爬虫
class YouTubeMultiMediaSpider(MultiMediaSpider):
    """YouTube 多媒体爬虫"""

    def __init__(self, playlist_urls: List[str], output_dir: str = "downloads"):
        super().__init__(playlist_urls, output_dir)

    def crawl_videos(self) -> List[VideoItem]:
        """从 YouTube 播放列表爬取视频"""
        from pyspider.browser.browser import PlaywrightManager
        from pyspider.parser.parser import HTMLParser

        print("\n🎬 爬取 YouTube 视频...")

        for url in self.urls:
            print(f"\n处理播放列表：{url}")

            browser = PlaywrightManager(headless=True)

            try:
                browser.navigate(url)
                time.sleep(5)

                # 滚动加载
                for i in range(10):
                    browser.execute_script(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )
                    time.sleep(1)
                    browser.execute_script("window.scrollTo(0, 0)")
                    time.sleep(0.5)

                html = browser.get_html()
                parser = HTMLParser(html)

                # 解析视频
                video_elements = parser.css("ytd-playlist-panel-video-renderer")

                for elem in video_elements:
                    try:
                        video = VideoItem()

                        # 提取标题
                        title_elem = elem.querySelector("#video-title")
                        if title_elem:
                            video.title = title_elem.text.strip()

                        # 提取 URL
                        url_elem = elem.querySelector("a#wc-endpoint")
                        if url_elem:
                            video.url = url_elem.get_attribute("href", "")

                        # 提取频道
                        channel_elem = elem.querySelector("#byline")
                        if channel_elem:
                            video.channel = channel_elem.text.strip()

                        # 提取时长
                        duration_elem = elem.querySelector(
                            "span.ytd-thumbnail-overlay-time-status-renderer"
                        )
                        if duration_elem:
                            video.duration = duration_elem.text.strip()

                        # 提取缩略图
                        thumb_elem = elem.querySelector("img#thumbnail")
                        if thumb_elem:
                            video.thumbnail = thumb_elem.get_attribute("src", "")

                        if video.title:
                            video.id = hashlib.md5(video.title.encode()).hexdigest()[
                                :12
                            ]
                            video.index = len(self.videos) + 1
                            self.videos.append(video)

                    except Exception:
                        continue

                print(f"   ✓ 找到 {len(self.videos)} 个视频")

            finally:
                browser.close()

        return self.videos

    def crawl_images(self) -> List[ImageItem]:
        """从视频缩略图爬取图片"""
        print("\n🖼️  收集图片（缩略图）...")

        for video in self.videos:
            if video.thumbnail:
                image = ImageItem()
                image.id = hashlib.md5(video.thumbnail.encode()).hexdigest()[:12]
                image.title = f"{video.title} - 缩略图"
                image.url = video.thumbnail
                image.alt = video.title
                image.source = "YouTube"
                self.images.append(image)

        print(f"   ✓ 收集到 {len(self.images)} 张图片")
        return self.images

    def crawl_audios(self) -> List[AudioItem]:
        """从视频提取音频（标记为音频下载）"""
        print("\n🎵 准备音频下载...")

        for video in self.videos:
            audio = AudioItem()
            audio.id = video.id
            audio.title = video.title
            audio.url = video.url  # YouTube URL，将使用 yt-dlp 提取音频
            audio.artist = video.channel
            audio.format = "mp3"
            self.audios.append(audio)

        print(f"   ✓ 准备 {len(self.audios)} 个音频")
        return self.audios


def main():
    """示例使用"""
    playlist_urls = [
        "https://www.youtube.com/watch?v=tr5yZ2TzXaY&list=PLRuPQZBVD6vV89UKIzUwZFUhDx9DjXLxc"
    ]

    # 创建爬虫
    spider = YouTubeMultiMediaSpider(playlist_urls, output_dir="youtube_downloads")

    # 爬取视频
    videos = spider.crawl_videos()
    print(f"\n共找到 {len(videos)} 个视频")

    # 收集图片（缩略图）
    images = spider.crawl_images()
    print(f"共收集 {len(images)} 张图片")

    # 准备音频
    audios = spider.crawl_audios()
    print(f"准备 {len(audios)} 个音频")

    # 保存元数据
    spider.save_metadata()

    # 下载选项
    print("\n" + "=" * 60)
    print("下载选项:")
    print("1. 下载所有视频")
    print("2. 只下载音频（提取 MP3）")
    print("3. 只下载缩略图")
    print("4. 跳过下载")

    choice = input("\n请选择 (1-4): ").strip()

    if choice == "1":
        stats = spider.download_all(max_workers=2)
        print("\n✅ 下载完成!")
        print(f"   成功：{stats['success']}")
        print(f"   失败：{stats['failed']}")
        print(f"   跳过：{stats['skipped']}")

    elif choice == "2":
        # 只下载音频
        downloader = MediaDownloader(spider.output_dir)
        stats = downloader.download_batch(spider.audios, max_workers=2)
        print("\n✅ 音频下载完成!")

    elif choice == "3":
        # 只下载图片
        downloader = MediaDownloader(spider.output_dir)
        stats = downloader.download_batch(spider.images, max_workers=3)
        print("\n✅ 图片下载完成!")

    print("\n🎉 全部完成!")


if __name__ == "__main__":
    main()
