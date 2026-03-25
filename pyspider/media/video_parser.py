"""
视频平台专用解析器
支持优酷、爱奇艺、腾讯视频等平台
"""

import re
import json
import time
import hashlib
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import logging
import requests


logger = logging.getLogger(__name__)


@dataclass
class VideoData:
    """视频数据"""
    title: str
    video_id: str
    platform: str
    m3u8_url: Optional[str] = None
    mp4_url: Optional[str] = None
    dash_url: Optional[str] = None
    download_url: Optional[str] = None
    cover_url: Optional[str] = None
    duration: int = 0
    description: str = ""
    quality_options: List[str] = None
    
    def __post_init__(self):
        if self.quality_options is None:
            self.quality_options = []


class YoukuParser:
    """优酷视频解析器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://v.youku.com/',
        })
    
    def parse(self, url: str) -> Optional[VideoData]:
        """解析优酷视频"""
        # 提取视频 ID
        video_id = self._extract_video_id(url)
        if not video_id:
            logger.error("无法提取视频 ID")
            return None
        
        logger.info(f"解析优酷视频：{video_id}")
        
        try:
            # 获取页面
            resp = self.session.get(url, timeout=30)
            html = resp.text
            
            # 提取标题
            title = self._extract_title(html, video_id)
            
            # 提取播放数据
            video_data = self._extract_video_data(html, video_id)
            
            if video_data:
                return VideoData(
                    title=title,
                    video_id=video_id,
                    platform="youku",
                    m3u8_url=video_data.get('m3u8_url'),
                    mp4_url=video_data.get('mp4_url'),
                    download_url=video_data.get('download_url'),
                    cover_url=video_data.get('cover_url'),
                    duration=video_data.get('duration', 0),
                    quality_options=video_data.get('quality_options', []),
                )
            
            return None
            
        except Exception as e:
            logger.error(f"解析失败：{e}")
            return None
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """提取视频 ID"""
        patterns = [
            r'id_(?:X)?([a-zA-Z0-9=]+)',
            r'/v_(?:id/)?([a-zA-Z0-9]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_title(self, html: str, video_id: str) -> str:
        """提取标题"""
        patterns = [
            r'<title>([^<]+)</title>',
            r'"title"\s*:\s*"([^"]+)"',
            r'<h1[^>]*>([^<]+)</h1>',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                title = match.group(1).strip()
                # 清理标题
                title = re.sub(r'\s*-?\s*优酷\s*$', '', title)
                title = re.sub(r'\s*高清完整正版.*$', '', title)
                return title
        
        return f"Youku Video {video_id}"
    
    def _extract_video_data(self, html: str, video_id: str) -> Optional[Dict]:
        """提取视频数据"""
        data = {
            'm3u8_url': None,
            'mp4_url': None,
            'download_url': None,
            'cover_url': None,
            'duration': 0,
            'quality_options': [],
        }
        
        # 尝试从 JSON 数据提取
        json_patterns = [
            r'window\.__INITIAL_DATA__\s*=\s*({.+?});',
            r'var\s+__INITIAL_DATA__\s*=\s*({.+?});',
            r'"videoData"\s*:\s*({.+?})[,}]',
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, html)
            if match:
                try:
                    json_str = match.group(1).replace('undefined', 'null')
                    json_data = json.loads(json_str)
                    
                    # 递归查找视频数据
                    video_info = self._find_video_info(json_data)
                    if video_info:
                        data.update(video_info)
                        break
                except Exception as e:
                    logger.debug(f"JSON 解析失败：{e}")
        
        # 尝试从 script 标签提取
        if not data['m3u8_url']:
            m3u8_pattern = r'(https?://[^"\s]+\.m3u8[^"\s]*)'
            match = re.search(m3u8_pattern, html)
            if match:
                data['m3u8_url'] = match.group(1)
        
        # 提取封面
        cover_patterns = [
            r'"poster"\s*:\s*"([^"]+)"',
            r'"cover"\s*:\s*"([^"]+)"',
            r'meta property="og:image"\s+content="([^"]+)"',
        ]
        
        for pattern in cover_patterns:
            match = re.search(pattern, html)
            if match:
                data['cover_url'] = match.group(1)
                break
        
        return data if any(data.values()) else None
    
    def _find_video_info(self, data: Any) -> Optional[Dict]:
        """递归查找视频信息"""
        if isinstance(data, dict):
            # 检查是否包含视频 URL
            if 'm3u8Url' in data:
                return {
                    'm3u8_url': data.get('m3u8Url'),
                    'mp4_url': data.get('mp4Url'),
                    'duration': data.get('duration', 0),
                }
            
            if 'videoUrl' in data:
                return {
                    'download_url': data.get('videoUrl'),
                }
            
            # 递归搜索
            for key, value in data.items():
                if key in ['data', 'video', 'videoInfo', 'result']:
                    result = self._find_video_info(value)
                    if result:
                        return result
            
            # 搜索所有值
            for value in data.values():
                result = self._find_video_info(value)
                if result:
                    return result
        
        elif isinstance(data, list):
            for item in data:
                result = self._find_video_info(item)
                if result:
                    return result
        
        return None


class IqiyiParser:
    """爱奇艺视频解析器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.iqiyi.com/',
        })
    
    def parse(self, url: str) -> Optional[VideoData]:
        """解析爱奇艺视频"""
        # 提取视频 ID
        video_id = self._extract_video_id(url)
        if not video_id:
            return None
        
        logger.info(f"解析爱奇艺视频：{video_id}")
        
        try:
            resp = self.session.get(url, timeout=30)
            html = resp.text
            
            title = self._extract_title(html, video_id)
            video_data = self._extract_video_data(html, video_id)
            
            if video_data:
                return VideoData(
                    title=title,
                    video_id=video_id,
                    platform="iqiyi",
                    m3u8_url=video_data.get('m3u8_url'),
                    dash_url=video_data.get('dash_url'),
                    quality_options=video_data.get('quality_options', []),
                )
            
            return None
            
        except Exception as e:
            logger.error(f"解析失败：{e}")
            return None
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """提取视频 ID"""
        # 爱奇艺视频 ID 通常在 URL 中
        patterns = [
            r'/v_(\w+)\.html',
            r'/play/(\w+)',
            r'curid=([^&]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_title(self, html: str, video_id: str) -> str:
        """提取标题"""
        match = re.search(r'<title>([^<]+)</title>', html)
        if match:
            title = match.group(1).strip()
            title = re.sub(r'\s*-?\s*爱奇艺.*$', '', title)
            return title
        return f"IQIYI Video {video_id}"
    
    def _extract_video_data(self, html: str, video_id: str) -> Optional[Dict]:
        """提取视频数据"""
        data = {
            'm3u8_url': None,
            'dash_url': None,
            'quality_options': [],
        }
        
        # 查找 M3U8 URL
        m3u8_pattern = r'(https?://[^"\s]+\.m3u8[^"\s]*)'
        match = re.search(m3u8_pattern, html)
        if match:
            data['m3u8_url'] = match.group(1)
        
        # 查找 DASH URL
        dash_pattern = r'(https?://[^"\s]+/dash[^"\s]*)'
        match = re.search(dash_pattern, html)
        if match:
            data['dash_url'] = match.group(1)
        
        # 查找质量选项
        quality_pattern = r'"quality"\s*:\s*\[([^\]]+)\]'
        match = re.search(quality_pattern, html)
        if match:
            qualities = match.group(1).split(',')
            data['quality_options'] = [q.strip() for q in qualities if q.strip()]
        
        return data if any(data.values()) else None


class TencentParser:
    """腾讯视频解析器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://v.qq.com/',
        })
    
    def parse(self, url: str) -> Optional[VideoData]:
        """解析腾讯视频"""
        # 提取视频 ID
        video_id = self._extract_video_id(url)
        if not video_id:
            return None
        
        logger.info(f"解析腾讯视频：{video_id}")
        
        try:
            resp = self.session.get(url, timeout=30)
            html = resp.text
            
            title = self._extract_title(html, video_id)
            video_data = self._extract_video_data(html, video_id)
            
            if video_data:
                return VideoData(
                    title=title,
                    video_id=video_id,
                    platform="tencent",
                    mp4_url=video_data.get('mp4_url'),
                    cover_url=video_data.get('cover_url'),
                    duration=video_data.get('duration', 0),
                )
            
            return None
            
        except Exception as e:
            logger.error(f"解析失败：{e}")
            return None
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """提取视频 ID"""
        patterns = [
            r'/x/(\w+)\.html',
            r'/cover/(\w+)',
            r'vid=(\w+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_title(self, html: str, video_id: str) -> str:
        """提取标题"""
        match = re.search(r'<title>([^<]+)</title>', html)
        if match:
            title = match.group(1).strip()
            title = re.sub(r'\s*-?\s*腾讯视频.*$', '', title)
            return title
        return f"Tencent Video {video_id}"
    
    def _extract_video_data(self, html: str, video_id: str) -> Optional[Dict]:
        """提取视频数据"""
        data = {
            'mp4_url': None,
            'cover_url': None,
            'duration': 0,
        }
        
        # 查找 MP4 URL
        mp4_pattern = r'"url"\s*:\s*"([^"]+\.mp4[^"]*)"'
        match = re.search(mp4_pattern, html)
        if match:
            data['mp4_url'] = match.group(1)
        
        # 查找封面
        cover_pattern = r'"pic"\s*:\s*"([^"]+)"'
        match = re.search(cover_pattern, html)
        if match:
            data['cover_url'] = match.group(1)
        
        return data if any(data.values()) else None


class UniversalParser:
    """通用视频解析器"""
    
    def __init__(self):
        self.parsers = {
            'youku': YoukuParser(),
            'iqiyi': IqiyiParser(),
            'tencent': TencentParser(),
        }
    
    def parse(self, url: str) -> Optional[VideoData]:
        """解析任意平台视频"""
        # 检测平台
        platform = self._detect_platform(url)
        
        if platform and platform in self.parsers:
            logger.info(f"检测到平台：{platform}")
            return self.parsers[platform].parse(url)
        
        # 尝试通用解析
        return self._universal_parse(url)
    
    def _detect_platform(self, url: str) -> Optional[str]:
        """检测视频平台"""
        if 'youku.com' in url or 'youku.tv' in url:
            return 'youku'
        elif 'iqiyi.com' in url:
            return 'iqiyi'
        elif 'qq.com' in url or 'v.qq.com' in url:
            return 'tencent'
        elif 'bilibili.com' in url:
            return 'bilibili'
        elif 'douyin.com' in url:
            return 'douyin'
        return None
    
    def _universal_parse(self, url: str) -> Optional[VideoData]:
        """通用解析"""
        try:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            })
            
            resp = session.get(url, timeout=30)
            html = resp.text
            
            # 提取标题
            title_match = re.search(r'<title>([^<]+)</title>', html)
            title = title_match.group(1).strip() if title_match else "Unknown Video"
            
            # 提取 M3U8
            m3u8_match = re.search(r'(https?://[^"\s]+\.m3u8[^"\s]*)', html)
            m3u8_url = m3u8_match.group(1) if m3u8_match else None
            
            # 提取 MP4
            mp4_match = re.search(r'(https?://[^"\s]+\.mp4[^"\s]*)', html)
            mp4_url = mp4_match.group(1) if mp4_match else None
            
            if m3u8_url or mp4_url:
                return VideoData(
                    title=title,
                    video_id=hashlib.md5(url.encode()).hexdigest()[:16],
                    platform="unknown",
                    m3u8_url=m3u8_url,
                    mp4_url=mp4_url,
                )
            
            return None
            
        except Exception as e:
            logger.error(f"通用解析失败：{e}")
            return None


# 使用示例
if __name__ == "__main__":
    import sys
    
    parser = UniversalParser()
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        
        print(f"解析视频：{url}")
        video_data = parser.parse(url)
        
        if video_data:
            print(f"\n✓ 解析成功")
            print(f"  平台：{video_data.platform}")
            print(f"  标题：{video_data.title}")
            print(f"  视频 ID: {video_data.video_id}")
            if video_data.m3u8_url:
                print(f"  M3U8: {video_data.m3u8_url[:80]}...")
            if video_data.mp4_url:
                print(f"  MP4: {video_data.mp4_url[:80]}...")
            if video_data.cover_url:
                print(f"  封面：{video_data.cover_url}")
        else:
            print("✗ 解析失败")
    else:
        print("用法：python video_parser.py <video_url>")
