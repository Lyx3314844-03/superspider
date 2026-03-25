"""
媒体下载模块
支持图片、视频、音乐爬取
"""

import os
import re
import json
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DownloadResult:
    """下载结果"""
    url: str
    path: str
    size: int
    success: bool
    error: Optional[str] = None


@dataclass
class VideoInfo:
    """视频信息"""
    title: str
    duration: int
    thumbnail: str
    formats: List[Dict]


class MediaDownloader:
    """媒体下载器"""
    
    def __init__(self, output_dir: str = "./downloads"):
        self.output_dir = Path(output_dir)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        })
        self._create_dirs()
    
    def _create_dirs(self) -> None:
        """创建目录"""
        (self.output_dir / "images").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "videos").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "audio").mkdir(parents=True, exist_ok=True)
    
    def download_image(
        self,
        url: str,
        filename: str = None,
        referer: str = None,
    ) -> DownloadResult:
        """下载图片"""
        try:
            headers = {}
            if referer:
                headers["Referer"] = referer
            
            resp = self.session.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            
            # 生成文件名
            if not filename:
                filename = os.path.basename(url.split("?")[0])
                if not filename:
                    filename = f"image_{len(os.listdir(self.output_dir / 'images'))}.jpg"
            
            filepath = self.output_dir / "images" / filename
            
            # 保存文件
            with open(filepath, "wb") as f:
                f.write(resp.content)
            
            return DownloadResult(
                url=url,
                path=str(filepath),
                size=len(resp.content),
                success=True,
            )
        except Exception as e:
            return DownloadResult(
                url=url,
                path="",
                size=0,
                success=False,
                error=str(e),
            )
    
    def download_images(self, urls: List[str]) -> List[DownloadResult]:
        """批量下载图片"""
        results = []
        for url in urls:
            result = self.download_image(url)
            results.append(result)
        return results
    
    def download_video(
        self,
        url: str,
        filename: str = None,
        chunk_size: int = 8192,
    ) -> DownloadResult:
        """下载视频"""
        try:
            resp = self.session.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            
            # 生成文件名
            if not filename:
                filename = f"video_{len(os.listdir(self.output_dir / 'videos'))}.mp4"
            
            filepath = self.output_dir / "videos" / filename
            
            # 保存文件
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
            
            return DownloadResult(
                url=url,
                path=str(filepath),
                size=filepath.stat().st_size,
                success=True,
            )
        except Exception as e:
            return DownloadResult(
                url=url,
                path="",
                size=0,
                success=False,
                error=str(e),
            )
    
    def download_audio(
        self,
        url: str,
        filename: str = None,
        chunk_size: int = 8192,
    ) -> DownloadResult:
        """下载音频"""
        try:
            resp = self.session.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            
            # 生成文件名
            if not filename:
                filename = f"audio_{len(os.listdir(self.output_dir / 'audio'))}.mp3"
            
            filepath = self.output_dir / "audio" / filename
            
            # 保存文件
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
            
            return DownloadResult(
                url=url,
                path=str(filepath),
                size=filepath.stat().st_size,
                success=True,
            )
        except Exception as e:
            return DownloadResult(
                url=url,
                path="",
                size=0,
                success=False,
                error=str(e),
            )
    
    def extract_images_from_html(self, html: str) -> List[str]:
        """从 HTML 中提取图片链接"""
        urls = []
        
        # 匹配 img 标签
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
        matches = re.findall(img_pattern, html, re.IGNORECASE)
        urls.extend(matches)
        
        # 匹配背景图片
        bg_pattern = r'url\(["\']?([^"\')\s]+)["\']?\)'
        bg_matches = re.findall(bg_pattern, html, re.IGNORECASE)
        urls.extend([url for url in bg_matches if any(ext in url for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"])])
        
        # 去重和过滤
        urls = list(set(urls))
        urls = [url for url in urls if url.startswith(("http://", "https://"))]
        
        return urls
    
    def extract_media_urls(self, html: str) -> "MediaURLs":
        """从 HTML 中提取所有媒体 URL"""
        urls = MediaURLs()
        
        # 提取图片
        img_pattern = r'(https?://[^\s"\'\'>]+\.(?:jpg|jpeg|png|gif|webp|bmp))'
        urls.images = list(set(re.findall(img_pattern, html, re.IGNORECASE)))
        
        # 提取视频
        video_pattern = r'(https?://[^\s"\'\'>]+\.(?:mp4|webm|avi|mov|flv|mkv))'
        urls.videos = list(set(re.findall(video_pattern, html, re.IGNORECASE)))
        
        # 提取音频
        audio_pattern = r'(https?://[^\s"\'\'>]+\.(?:mp3|wav|ogg|flac|aac|m4a))'
        urls.audios = list(set(re.findall(audio_pattern, html, re.IGNORECASE)))
        
        return urls
    
    def download_all(self, media_urls: "MediaURLs") -> "DownloadStats":
        """下载所有媒体"""
        stats = DownloadStats()
        
        # 下载图片
        for url in media_urls.images:
            result = self.download_image(url)
            if result.success:
                stats.images_downloaded += 1
                stats.total_bytes += result.size
            else:
                stats.images_failed += 1
        
        # 下载视频
        for url in media_urls.videos:
            result = self.download_video(url)
            if result.success:
                stats.videos_downloaded += 1
                stats.total_bytes += result.size
            else:
                stats.videos_failed += 1
        
        # 下载音频
        for url in media_urls.audios:
            result = self.download_audio(url)
            if result.success:
                stats.audios_downloaded += 1
                stats.total_bytes += result.size
            else:
                stats.audios_failed += 1
        
        return stats
    
    def get_video_info(self, url: str) -> Optional[VideoInfo]:
        """获取视频信息（模拟实现）"""
        # 实际应该调用 yt-dlp 或类似工具
        return VideoInfo(
            title="Video Title",
            duration=0,
            thumbnail="",
            formats=[],
        )


@dataclass
class MediaURLs:
    """媒体 URL 集合"""
    images: List[str] = None
    videos: List[str] = None
    audios: List[str] = None
    
    def __post_init__(self):
        if self.images is None:
            self.images = []
        if self.videos is None:
            self.videos = []
        if self.audios is None:
            self.audios = []


@dataclass
class DownloadStats:
    """下载统计"""
    images_downloaded: int = 0
    images_failed: int = 0
    videos_downloaded: int = 0
    videos_failed: int = 0
    audios_downloaded: int = 0
    audios_failed: int = 0
    total_bytes: int = 0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "images_downloaded": self.images_downloaded,
            "images_failed": self.images_failed,
            "videos_downloaded": self.videos_downloaded,
            "videos_failed": self.videos_failed,
            "audios_downloaded": self.audios_downloaded,
            "audios_failed": self.audios_failed,
            "total_bytes": self.total_bytes,
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
