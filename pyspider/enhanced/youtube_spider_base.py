"""
pyspider 框架增强模块
整合所有增强功能，提供统一的爬虫接口
"""

import sys
sys.path.insert(0, 'C:/Users/Administrator/spider')

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
import json
import time
from datetime import datetime
import re


# ============================================================================
# 基础数据模型
# ============================================================================

@dataclass
class VideoItem:
    """视频数据项"""
    title: str = ""
    duration: str = ""
    channel: str = ""
    url: str = ""
    thumbnail: str = ""
    views: str = ""
    published: str = ""
    description: str = ""
    index: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self, ensure_ascii: bool = False, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii, indent=indent)


@dataclass
class CrawlStats:
    """爬取统计信息"""
    total_videos: int = 0
    total_duration: str = ""
    unique_channels: int = 0
    crawl_time: float = 0.0
    start_time: str = ""
    end_time: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# 增强型 YouTube 爬虫基类
# ============================================================================

class YouTubeSpiderBase:
    """YouTube 爬虫基类（通用接口）"""
    
    name: str = "youtube_spider"
    platform: str = "unknown"
    
    def __init__(self, playlist_url: str, **kwargs):
        self.playlist_url = playlist_url
        self.videos: List[VideoItem] = []
        self.stats = CrawlStats()
        self.settings = kwargs
        self._start_time = None
        self._end_time = None
        
    def start(self) -> List[VideoItem]:
        """启动爬虫（模板方法）"""
        self._before_start()
        
        try:
            self._initialize()
            self._navigate()
            self._wait_and_scroll()
            self._extract_content()
            self._parse_videos()
            self._after_extract()
            
            self._calculate_stats()
            self._print_results()
            
            return self.videos
            
        except Exception as e:
            self._on_error(e)
            return []
            
        finally:
            self._cleanup()
    
    def _before_start(self):
        """启动前钩子"""
        self._start_time = datetime.now()
        self.stats.start_time = self._start_time.strftime('%Y-%m-%d %H:%M:%S')
        self._print_header()
    
    def _print_header(self):
        """打印头部"""
        print("\n" + "╔"*30 + "╗")
        print("║"*10 + f" {self.platform} - YouTube 爬虫 " + "║"*10)
        print("╚"*30 + "╝")
        print(f"\n📺 播放列表：{self.playlist_url}\n")
    
    def _initialize(self):
        """初始化"""
        pass
    
    def _navigate(self):
        """导航到页面"""
        pass
    
    def _wait_and_scroll(self):
        """等待和滚动"""
        pass
    
    def _extract_content(self):
        """提取内容"""
        pass
    
    def _parse_videos(self):
        """解析视频"""
        pass
    
    def _after_extract(self):
        """提取后钩子"""
        self._end_time = datetime.now()
        self.stats.end_time = self._end_time.strftime('%Y-%m-%d %H:%M:%S')
        self.stats.crawl_time = (self._end_time - self._start_time).total_seconds()
    
    def _calculate_stats(self):
        """计算统计信息"""
        self.stats.total_videos = len(self.videos)
        channels = set(v.channel for v in self.videos if v.channel)
        self.stats.unique_channels = len(channels)
    
    def _print_results(self):
        """打印结果"""
        print("\n" + "═"*60)
        print(" " * 20 + "爬取结果")
        print("═"*60)
        print(f"共找到 {self.stats.total_videos} 个视频")
        print(f"唯一频道数：{self.stats.unique_channels}")
        print(f"爬取耗时：{self.stats.crawl_time:.2f}秒")
        print("\n前 20 个视频:")
        
        for i, video in enumerate(self.videos[:20]):
            print(f"\n{i+1:2d}. {video.title}")
            if video.duration:
                print(f"    ⏱️  时长：{video.duration}")
            if video.channel:
                print(f"    👤  频道：{video.channel}")
        
        if len(self.videos) > 20:
            print(f"\n... 还有 {len(self.videos) - 20} 个视频")
    
    def _on_error(self, error: Exception):
        """错误处理"""
        print(f"\n❌ 爬取失败：{error}")
        import traceback
        traceback.print_exc()
    
    def _cleanup(self):
        """清理"""
        pass
    
    def save_to_file(self, filename: str = None, format: str = "json") -> str:
        """保存到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"youtube_playlist_{timestamp}.{format}"
        
        if format == "json":
            self._save_json(filename)
        elif format == "txt":
            self._save_txt(filename)
        elif format == "csv":
            self._save_csv(filename)
        
        print(f"💾 结果已保存到：{filename}")
        return filename
    
    def _save_json(self, filename: str):
        """保存为 JSON"""
        data = {
            "playlist_url": self.playlist_url,
            "crawl_stats": self.stats.to_dict(),
            "videos": [v.to_dict() for v in self.videos]
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _save_txt(self, filename: str):
        """保存为 TXT"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("YouTube 播放列表视频列表\n")
            f.write("═"*60 + "\n\n")
            f.write(f"播放列表 URL: {self.playlist_url}\n")
            f.write(f"爬取时间：{self.stats.start_time}\n")
            f.write(f"视频总数：{self.stats.total_videos}\n")
            f.write(f"唯一频道数：{self.stats.unique_channels}\n")
            f.write(f"爬取耗时：{self.stats.crawl_time:.2f}秒\n\n")
            f.write("═"*60 + "\n\n")
            
            for i, video in enumerate(self.videos):
                f.write(f"{i+1}. {video.title}\n")
                if video.duration:
                    f.write(f"   时长：{video.duration}\n")
                if video.channel:
                    f.write(f"   频道：{video.channel}\n")
                if video.url:
                    f.write(f"   链接：{video.url}\n")
                f.write("\n")
    
    def _save_csv(self, filename: str):
        """保存为 CSV"""
        import csv
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = ['index', 'title', 'duration', 'channel', 'url', 'thumbnail', 'views', 'published']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for video in self.videos:
                writer.writerow(video.to_dict())


# ============================================================================
# 工具函数
# ============================================================================

def parse_duration_to_seconds(duration: str) -> int:
    """将时长字符串转换为秒"""
    if not duration:
        return 0
    
    parts = duration.split(':')
    seconds = 0
    
    if len(parts) == 1:  # 只有秒
        seconds = int(parts[0])
    elif len(parts) == 2:  # 分：秒
        seconds = int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:  # 时：分：秒
        seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    
    return seconds


def format_seconds_to_duration(seconds: int) -> str:
    """将秒转换为时长字符串"""
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}分{secs}秒"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}小时{minutes}分{secs}秒"


def extract_video_id(url: str) -> str:
    """从 URL 提取视频 ID"""
    patterns = [
        r'v=([a-zA-Z0-9_-]+)',
        r'youtu\.be/([a-zA-Z0-9_-]+)',
        r'embed/([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return ""


def build_youtube_url(video_id: str, playlist_id: str = None, index: int = None) -> str:
    """构建 YouTube URL"""
    base = f"https://www.youtube.com/watch?v={video_id}"
    
    if playlist_id:
        base += f"&list={playlist_id}"
    if index:
        base += f"&index={index}"
    
    return base


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    'VideoItem',
    'CrawlStats',
    'YouTubeSpiderBase',
    'parse_duration_to_seconds',
    'format_seconds_to_duration',
    'extract_video_id',
    'build_youtube_url',
]
