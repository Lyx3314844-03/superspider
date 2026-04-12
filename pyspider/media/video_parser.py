"""
视频平台专用解析器
支持优酷、爱奇艺、腾讯视频等平台
"""

import re
import json
import hashlib
from html import unescape
from urllib.parse import urljoin, urlparse
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


def _clean_text(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def _normalize_media_url(page_url: str, candidate: Optional[str]) -> Optional[str]:
    if not candidate:
        return None
    value = (
        unescape(candidate)
        .replace("\\/", "/")
        .replace("\\u002F", "/")
        .replace("\\u003A", ":")
        .strip()
    )
    if not value or value.startswith("data:") or value.startswith("javascript:"):
        return None
    if value.startswith("//"):
        parsed = urlparse(page_url)
        scheme = parsed.scheme or "https"
        return f"{scheme}:{value}"
    return urljoin(page_url, value)


def _is_media_url(url: str) -> bool:
    lower = url.lower()
    return any(ext in lower for ext in (".m3u8", ".mpd", ".mp4", ".webm", ".m4v", ".mov"))


def _classify_media_url(url: str) -> str:
    lower = url.lower()
    if ".m3u8" in lower:
        return "m3u8"
    if ".mpd" in lower or "dash" in lower:
        return "dash"
    if any(ext in lower for ext in (".mp4", ".webm", ".m4v", ".mov")):
        return "mp4"
    return "download"


def _extract_json_ld_blocks(html: str) -> List[Any]:
    blocks: List[Any] = []
    for match in re.finditer(
        r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
    ):
        raw = _clean_text(match.group(1))
        if not raw:
            continue
        try:
            blocks.append(json.loads(raw))
        except Exception:
            continue
    return blocks


def _collect_from_json(value: Any, page_url: str, collector: Dict[str, Any]) -> None:
    if isinstance(value, list):
        for item in value:
            _collect_from_json(item, page_url, collector)
        return
    if not isinstance(value, dict):
        return

    object_types = value.get("@type", [])
    if isinstance(object_types, str):
        object_types = [object_types]
    object_types = [str(item).lower() for item in object_types]

    if "videoobject" in object_types:
        title_value = _clean_text(value.get("name") or value.get("headline"))
        if title_value:
            collector["title"] = title_value
        description_value = _clean_text(value.get("description"))
        if description_value:
            collector["description"] = description_value
        collector["cover_url"] = collector["cover_url"] or _normalize_media_url(
            page_url, value.get("thumbnailUrl")
        )
        for key in (
            "contentUrl",
            "embedUrl",
            "url",
            "videoUrl",
            "m3u8Url",
            "dashUrl",
        ):
            normalized = _normalize_media_url(page_url, value.get(key))
            if normalized:
                collector["urls"].append(normalized)

    for key in (
        "contentUrl",
        "embedUrl",
        "videoUrl",
        "video_url",
        "playAddr",
        "play_url",
        "m3u8Url",
        "m3u8_url",
        "dashUrl",
        "dash_url",
        "mp4Url",
        "mp4_url",
    ):
        normalized = _normalize_media_url(page_url, value.get(key))
        if normalized:
            collector["urls"].append(normalized)

    for nested in value.values():
        _collect_from_json(nested, page_url, collector)


def _discover_video_data_from_html(page_url: str, html: str) -> Optional[VideoData]:
    collector: Dict[str, Any] = {
        "title": "",
        "description": "",
        "cover_url": None,
        "urls": [],
    }

    title_patterns = [
        r'(?is)<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
        r'(?is)<meta[^>]+name=["\']twitter:title["\'][^>]+content=["\']([^"\']+)["\']',
        r"(?is)<title>([^<]+)</title>",
    ]
    for pattern in title_patterns:
        match = re.search(pattern, html)
        if match:
            collector["title"] = _clean_text(match.group(1))
            if collector["title"]:
                break

    description_patterns = [
        r'(?is)<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
        r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
    ]
    for pattern in description_patterns:
        match = re.search(pattern, html)
        if match:
            collector["description"] = _clean_text(match.group(1))
            if collector["description"]:
                break

    cover_patterns = [
        r'(?is)<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'(?is)<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'(?is)<video[^>]+poster=["\']([^"\']+)["\']',
    ]
    for pattern in cover_patterns:
        match = re.search(pattern, html)
        if match:
            collector["cover_url"] = _normalize_media_url(page_url, match.group(1))
            if collector["cover_url"]:
                break

    html_patterns = [
        r'(?is)<meta[^>]+(?:property|name)=["\'](?:og:video(?::url)?|twitter:player:stream)["\'][^>]+content=["\']([^"\']+)["\']',
        r'(?is)<video[^>]+src=["\']([^"\']+)["\']',
        r'(?is)<source[^>]+src=["\']([^"\']+)["\']',
        r'(?is)\b(?:contentUrl|embedUrl|videoUrl|video_url|playAddr|play_url|m3u8Url|m3u8_url|dashUrl|dash_url|mp4Url|mp4_url)\b["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        r"(https?://[^\"'\s<>]+(?:\.m3u8|\.mpd|\.mp4|\.webm|\.m4v|\.mov)[^\"'\s<>]*)",
    ]
    for pattern in html_patterns:
        for match in re.finditer(pattern, html):
            normalized = _normalize_media_url(page_url, match.group(1))
            if normalized:
                collector["urls"].append(normalized)

    for block in _extract_json_ld_blocks(html):
        _collect_from_json(block, page_url, collector)

    deduped_urls: List[str] = []
    for candidate in collector["urls"]:
        if candidate and candidate not in deduped_urls:
            deduped_urls.append(candidate)

    m3u8_url = next((item for item in deduped_urls if _classify_media_url(item) == "m3u8"), None)
    dash_url = next((item for item in deduped_urls if _classify_media_url(item) == "dash"), None)
    mp4_url = next((item for item in deduped_urls if _classify_media_url(item) == "mp4"), None)
    download_url = next(
        (
            item
            for item in deduped_urls
            if item not in {m3u8_url, dash_url, mp4_url}
        ),
        None,
    )

    if not any((m3u8_url, dash_url, mp4_url, download_url)):
        return None

    title = collector["title"] or "Unknown Video"
    return VideoData(
        title=title,
        video_id=hashlib.md5(page_url.encode()).hexdigest()[:16],
        platform="generic",
        m3u8_url=m3u8_url,
        mp4_url=mp4_url,
        dash_url=dash_url,
        download_url=download_url,
        cover_url=collector["cover_url"],
        description=collector["description"],
    )


def _merge_video_data(primary: Optional[VideoData], fallback: Optional[VideoData]) -> Optional[VideoData]:
    if primary is None:
        return fallback
    if fallback is None:
        return primary
    if not primary.title or primary.title == "Unknown Video":
        primary.title = fallback.title
    primary.m3u8_url = primary.m3u8_url or fallback.m3u8_url
    primary.mp4_url = primary.mp4_url or fallback.mp4_url
    primary.dash_url = primary.dash_url or fallback.dash_url
    primary.download_url = primary.download_url or fallback.download_url
    primary.cover_url = primary.cover_url or fallback.cover_url
    primary.description = primary.description or fallback.description
    if not primary.quality_options and fallback.quality_options:
        primary.quality_options = list(fallback.quality_options)
    return primary


def _discover_video_data_from_artifacts(
    page_url: str, html: str = "", artifact_texts: Optional[List[str]] = None
) -> Optional[VideoData]:
    collector: Dict[str, Any] = {
        "title": "",
        "description": "",
        "cover_url": None,
        "urls": [],
    }

    if html:
        html_result = _discover_video_data_from_html(page_url, html)
        if html_result:
            collector["title"] = html_result.title
            collector["description"] = html_result.description
            collector["cover_url"] = html_result.cover_url
            for candidate in (
                html_result.m3u8_url,
                html_result.dash_url,
                html_result.mp4_url,
                html_result.download_url,
            ):
                if candidate:
                    collector["urls"].append(candidate)

    for artifact_text in artifact_texts or []:
        if not artifact_text:
            continue
        for pattern in (
            r'(?is)\b(?:contentUrl|embedUrl|videoUrl|video_url|playAddr|play_url|m3u8Url|m3u8_url|dashUrl|dash_url|mp4Url|mp4_url)\b["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r"(https?://[^\"'\s<>]+(?:\.m3u8|\.mpd|\.mp4|\.webm|\.m4v|\.mov)[^\"'\s<>]*)",
        ):
            for match in re.finditer(pattern, artifact_text):
                normalized = _normalize_media_url(page_url, match.group(1))
                if normalized:
                    collector["urls"].append(normalized)
        try:
            payload = json.loads(artifact_text)
        except Exception:
            continue
        _collect_from_json(payload, page_url, collector)

    deduped_urls: List[str] = []
    for candidate in collector["urls"]:
        if candidate and candidate not in deduped_urls:
            deduped_urls.append(candidate)

    m3u8_url = next(
        (item for item in deduped_urls if _classify_media_url(item) == "m3u8"), None
    )
    dash_url = next(
        (item for item in deduped_urls if _classify_media_url(item) == "dash"), None
    )
    mp4_url = next(
        (item for item in deduped_urls if _classify_media_url(item) == "mp4"), None
    )
    download_url = next(
        (
            item
            for item in deduped_urls
            if item not in {m3u8_url, dash_url, mp4_url}
        ),
        None,
    )

    if not any((m3u8_url, dash_url, mp4_url, download_url)):
        return None

    return VideoData(
        title=collector["title"] or "Unknown Video",
        video_id=hashlib.md5(page_url.encode()).hexdigest()[:16],
        platform="generic-artifact",
        m3u8_url=m3u8_url,
        mp4_url=mp4_url,
        dash_url=dash_url,
        download_url=download_url,
        cover_url=collector["cover_url"],
        description=collector["description"],
    )


class YoukuParser:
    """优酷视频解析器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://v.youku.com/",
            }
        )

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
                    m3u8_url=video_data.get("m3u8_url"),
                    mp4_url=video_data.get("mp4_url"),
                    download_url=video_data.get("download_url"),
                    cover_url=video_data.get("cover_url"),
                    duration=video_data.get("duration", 0),
                    quality_options=video_data.get("quality_options", []),
                )

            return None

        except Exception as e:
            logger.error(f"解析失败：{e}")
            return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        """提取视频 ID"""
        patterns = [
            r"id_(?:X)?([a-zA-Z0-9=]+)",
            r"/v_(?:id/)?([a-zA-Z0-9]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def _extract_title(self, html: str, video_id: str) -> str:
        """提取标题"""
        patterns = [
            r"<title>([^<]+)</title>",
            r'"title"\s*:\s*"([^"]+)"',
            r"<h1[^>]*>([^<]+)</h1>",
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                title = match.group(1).strip()
                # 清理标题
                title = re.sub(r"\s*-?\s*优酷\s*$", "", title)
                title = re.sub(r"\s*高清完整正版.*$", "", title)
                return title

        return f"Youku Video {video_id}"

    def _extract_video_data(self, html: str, video_id: str) -> Optional[Dict]:
        """提取视频数据"""
        data = {
            "m3u8_url": None,
            "mp4_url": None,
            "download_url": None,
            "cover_url": None,
            "duration": 0,
            "quality_options": [],
        }

        # 尝试从 JSON 数据提取
        json_patterns = [
            r"window\.__INITIAL_DATA__\s*=\s*({.+?});",
            r"var\s+__INITIAL_DATA__\s*=\s*({.+?});",
            r'"videoData"\s*:\s*({.+?})[,}]',
        ]

        for pattern in json_patterns:
            match = re.search(pattern, html)
            if match:
                try:
                    json_str = match.group(1).replace("undefined", "null")
                    json_data = json.loads(json_str)

                    # 递归查找视频数据
                    video_info = self._find_video_info(json_data)
                    if video_info:
                        data.update(video_info)
                        break
                except Exception as e:
                    logger.debug(f"JSON 解析失败：{e}")

        # 尝试从 script 标签提取
        if not data["m3u8_url"]:
            m3u8_pattern = r'(https?://[^"\s]+\.m3u8[^"\s]*)'
            match = re.search(m3u8_pattern, html)
            if match:
                data["m3u8_url"] = match.group(1)

        # 提取封面
        cover_patterns = [
            r'"poster"\s*:\s*"([^"]+)"',
            r'"cover"\s*:\s*"([^"]+)"',
            r'meta property="og:image"\s+content="([^"]+)"',
        ]

        for pattern in cover_patterns:
            match = re.search(pattern, html)
            if match:
                data["cover_url"] = match.group(1)
                break

        return data if any(data.values()) else None

    def _find_video_info(self, data: Any) -> Optional[Dict]:
        """递归查找视频信息"""
        if isinstance(data, dict):
            # 检查是否包含视频 URL
            if "m3u8Url" in data:
                return {
                    "m3u8_url": data.get("m3u8Url"),
                    "mp4_url": data.get("mp4Url"),
                    "duration": data.get("duration", 0),
                }

            if "videoUrl" in data:
                return {
                    "download_url": data.get("videoUrl"),
                }

            # 递归搜索
            for key, value in data.items():
                if key in ["data", "video", "videoInfo", "result"]:
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
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.iqiyi.com/",
            }
        )

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
                    m3u8_url=video_data.get("m3u8_url"),
                    dash_url=video_data.get("dash_url"),
                    quality_options=video_data.get("quality_options", []),
                )

            return None

        except Exception as e:
            logger.error(f"解析失败：{e}")
            return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        """提取视频 ID"""
        # 爱奇艺视频 ID 通常在 URL 中
        patterns = [
            r"/v_(\w+)\.html",
            r"/play/(\w+)",
            r"curid=([^&]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def _extract_title(self, html: str, video_id: str) -> str:
        """提取标题"""
        match = re.search(r"<title>([^<]+)</title>", html)
        if match:
            title = match.group(1).strip()
            title = re.sub(r"\s*-?\s*爱奇艺.*$", "", title)
            return title
        return f"IQIYI Video {video_id}"

    def _extract_video_data(self, html: str, video_id: str) -> Optional[Dict]:
        """提取视频数据"""
        data = {
            "m3u8_url": None,
            "dash_url": None,
            "quality_options": [],
        }

        # 查找 M3U8 URL
        m3u8_pattern = r'(https?://[^"\s]+\.m3u8[^"\s]*)'
        match = re.search(m3u8_pattern, html)
        if match:
            data["m3u8_url"] = match.group(1)

        # 查找 DASH URL
        dash_pattern = r'(https?://[^"\s]+/dash[^"\s]*)'
        match = re.search(dash_pattern, html)
        if match:
            data["dash_url"] = match.group(1)

        # 查找质量选项
        quality_pattern = r'"quality"\s*:\s*\[([^\]]+)\]'
        match = re.search(quality_pattern, html)
        if match:
            qualities = match.group(1).split(",")
            data["quality_options"] = [q.strip() for q in qualities if q.strip()]

        return data if any(data.values()) else None


class TencentParser:
    """腾讯视频解析器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://v.qq.com/",
            }
        )

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
                    mp4_url=video_data.get("mp4_url"),
                    cover_url=video_data.get("cover_url"),
                    duration=video_data.get("duration", 0),
                )

            return None

        except Exception as e:
            logger.error(f"解析失败：{e}")
            return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        """提取视频 ID"""
        patterns = [
            r"/x/(\w+)\.html",
            r"/cover/(\w+)",
            r"vid=(\w+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def _extract_title(self, html: str, video_id: str) -> str:
        """提取标题"""
        match = re.search(r"<title>([^<]+)</title>", html)
        if match:
            title = match.group(1).strip()
            title = re.sub(r"\s*-?\s*腾讯视频.*$", "", title)
            return title
        return f"Tencent Video {video_id}"

    def _extract_video_data(self, html: str, video_id: str) -> Optional[Dict]:
        """提取视频数据"""
        data = {
            "mp4_url": None,
            "cover_url": None,
            "duration": 0,
        }

        # 查找 MP4 URL
        mp4_pattern = r'"url"\s*:\s*"([^"]+\.mp4[^"]*)"'
        match = re.search(mp4_pattern, html)
        if match:
            data["mp4_url"] = match.group(1)

        # 查找封面
        cover_pattern = r'"pic"\s*:\s*"([^"]+)"'
        match = re.search(cover_pattern, html)
        if match:
            data["cover_url"] = match.group(1)

        return data if any(data.values()) else None


class BilibiliParser:
    """Bilibili 视频解析器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.bilibili.com/",
            }
        )

    def parse(self, url: str) -> Optional[VideoData]:
        video_id = self._extract_video_id(url)
        if not video_id:
            return None

        logger.info(f"解析 Bilibili 视频：{video_id}")
        try:
            resp = self.session.get(url, timeout=30)
            html = resp.text

            title = self._extract_title(html, video_id)
            video_data = self._extract_video_data(html)
            if video_data:
                return VideoData(
                    title=title,
                    video_id=video_id,
                    platform="bilibili",
                    m3u8_url=video_data.get("m3u8_url"),
                    mp4_url=video_data.get("mp4_url"),
                    dash_url=video_data.get("dash_url"),
                    cover_url=video_data.get("cover_url"),
                    duration=video_data.get("duration", 0),
                    description=video_data.get("description", ""),
                    quality_options=video_data.get("quality_options", []),
                )
            return None
        except Exception as e:
            logger.error(f"解析失败：{e}")
            return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        patterns = [
            r"/video/((?:BV|av)[A-Za-z0-9]+)",
            r"/bangumi/play/(ep\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _extract_title(self, html: str, video_id: str) -> str:
        patterns = [
            r"<title[^>]*>([^<]+)</title>",
            r'"title"\s*:\s*"([^"]+)"',
            r'"part"\s*:\s*"([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                title = match.group(1).strip()
                title = re.sub(r"\s*[-_–—|]+\s*哔哩哔哩.*$", "", title)
                if title:
                    return title
        return f"Bilibili Video {video_id}"

    def _extract_video_data(self, html: str) -> Optional[Dict]:
        data = {
            "m3u8_url": None,
            "mp4_url": None,
            "dash_url": None,
            "cover_url": None,
            "duration": 0,
            "description": "",
            "quality_options": [],
        }

        patterns = {
            "m3u8_url": r'(https?://[^"\s]+\.m3u8[^"\s]*)',
            "mp4_url": r'(https?://[^"\s]+\.mp4[^"\s]*)',
            "dash_url": r'"baseUrl"\s*:\s*"(https?://[^"]+)"',
            "cover_url": r'"(?:cover|pic|thumbnailUrl)"\s*:\s*"([^"]+)"',
            "description": r'"(?:desc|description)"\s*:\s*"([^"]+)"',
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, html)
            if match:
                data[key] = match.group(1)

        duration_match = re.search(r'"duration"\s*:\s*(\d+)', html)
        if duration_match:
            data["duration"] = int(duration_match.group(1))

        quality_matches = re.findall(
            r'"(?:quality|accept_description)"\s*:\s*\[([^\]]+)\]', html
        )
        for raw in quality_matches:
            for quality in raw.split(","):
                cleaned = quality.strip().strip('"')
                if cleaned and cleaned not in data["quality_options"]:
                    data["quality_options"].append(cleaned)

        return data if any(data.values()) else None


class DouyinParser:
    """抖音视频解析器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.douyin.com/",
            }
        )

    def parse(self, url: str) -> Optional[VideoData]:
        video_id = self._extract_video_id(url)
        if not video_id:
            return None

        logger.info(f"解析 Douyin 视频：{video_id}")
        try:
            resp = self.session.get(url, timeout=30)
            html = resp.text

            title = self._extract_title(html, video_id)
            video_data = self._extract_video_data(html)
            if video_data:
                return VideoData(
                    title=title,
                    video_id=video_id,
                    platform="douyin",
                    mp4_url=video_data.get("mp4_url"),
                    download_url=video_data.get("download_url"),
                    cover_url=video_data.get("cover_url"),
                    duration=video_data.get("duration", 0),
                    description=video_data.get("description", ""),
                )
            return None
        except Exception as e:
            logger.error(f"解析失败：{e}")
            return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        patterns = [
            r"/video/(\d+)",
            r"modal_id=(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _extract_title(self, html: str, video_id: str) -> str:
        patterns = [
            r"<title[^>]*>([^<]+)</title>",
            r'"desc"\s*:\s*"([^"]+)"',
            r'"title"\s*:\s*"([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                title = match.group(1).strip()
                title = re.sub(r"\s*[-_–—|]+\s*抖音.*$", "", title)
                if title:
                    return title
        return f"Douyin Video {video_id}"

    def _extract_video_data(self, html: str) -> Optional[Dict]:
        data = {
            "mp4_url": None,
            "download_url": None,
            "cover_url": None,
            "duration": 0,
            "description": "",
        }

        patterns = {
            "mp4_url": r'"(?:playAddr|play_api|playUrl)"\s*:\s*"([^"]+)"',
            "download_url": r'"(?:downloadAddr|download_url)"\s*:\s*"([^"]+)"',
            "cover_url": r'"(?:cover|dynamic_cover|originCover)"\s*:\s*"([^"]+)"',
            "description": r'"(?:desc|description)"\s*:\s*"([^"]+)"',
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, html)
            if match:
                data[key] = match.group(1).replace("\\u002F", "/")

        duration_match = re.search(r'"duration"\s*:\s*(\d+)', html)
        if duration_match:
            data["duration"] = int(duration_match.group(1))

        return data if any(data.values()) else None


class UniversalParser:
    """通用视频解析器"""

    def __init__(self):
        self.parsers = {
            "youku": YoukuParser(),
            "iqiyi": IqiyiParser(),
            "tencent": TencentParser(),
            "bilibili": BilibiliParser(),
            "douyin": DouyinParser(),
        }

    def parse(self, url: str) -> Optional[VideoData]:
        """解析任意平台视频"""
        # 检测平台
        platform = self._detect_platform(url)

        specific: Optional[VideoData] = None
        if platform and platform in self.parsers:
            logger.info(f"检测到平台：{platform}")
            specific = self.parsers[platform].parse(url)

        # 尝试通用解析
        return _merge_video_data(specific, self._universal_parse(url))

    def parse_artifacts(
        self,
        page_url: str,
        *,
        html: str = "",
        artifact_texts: Optional[List[str]] = None,
    ) -> Optional[VideoData]:
        specific = None
        platform = self._detect_platform(page_url)
        if html and platform and platform in self.parsers:
            try:
                specific = self.parsers[platform].parse(page_url)
            except Exception:
                specific = None
        generic = _discover_video_data_from_artifacts(
            page_url, html=html, artifact_texts=artifact_texts
        )
        return _merge_video_data(specific, generic)

    def _detect_platform(self, url: str) -> Optional[str]:
        """检测视频平台"""
        if "youku.com" in url or "youku.tv" in url:
            return "youku"
        elif "iqiyi.com" in url:
            return "iqiyi"
        elif "qq.com" in url or "v.qq.com" in url:
            return "tencent"
        elif "bilibili.com" in url:
            return "bilibili"
        elif "douyin.com" in url:
            return "douyin"
        return None

    def _universal_parse(self, url: str) -> Optional[VideoData]:
        """通用解析"""
        try:
            direct_url = _normalize_media_url(url, url)
            if direct_url and _is_media_url(direct_url):
                kind = _classify_media_url(direct_url)
                return VideoData(
                    title="Unknown Video",
                    video_id=hashlib.md5(url.encode()).hexdigest()[:16],
                    platform="generic",
                    m3u8_url=direct_url if kind == "m3u8" else None,
                    dash_url=direct_url if kind == "dash" else None,
                    mp4_url=direct_url if kind == "mp4" else None,
                    download_url=None if kind in {"m3u8", "dash", "mp4"} else direct_url,
                )

            session = requests.Session()
            session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                }
            )

            resp = session.get(url, timeout=30)
            html = resp.text
            return _discover_video_data_from_html(url, html)

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
            print("\n✓ 解析成功")
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
