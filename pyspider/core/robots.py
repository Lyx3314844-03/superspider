"""
robots.txt 解析和遵守模块
"""

import time
import logging
from typing import Optional, Dict
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)


class RobotsChecker:
    """robots.txt 检查器"""

    def __init__(self, user_agent: str = "*", cache_timeout: int = 3600):
        self._user_agent = user_agent
        self._cache_timeout = cache_timeout
        self._parsers: Dict[str, tuple] = {}  # {domain: (parser, timestamp)}
        self._respect_robots = True

    def set_respect_robots(self, respect: bool) -> None:
        """设置是否遵守 robots.txt"""
        self._respect_robots = respect

    def _get_domain(self, url: str) -> str:
        """获取域名"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _get_parser(self, url: str) -> Optional[RobotFileParser]:
        """获取或创建 RobotFileParser"""
        if not self._respect_robots:
            return None

        domain = self._get_domain(url)
        if domain in self._parsers:
            parser, timestamp = self._parsers[domain]
            if time.time() - timestamp < self._cache_timeout:
                return parser

        try:
            robots_url = f"{domain}/robots.txt"
            # 修复: 使用 urllib 带超时获取
            import urllib.request

            req = urllib.request.Request(robots_url)
            resp = urllib.request.urlopen(req, timeout=10)

            rp = RobotFileParser()
            rp.parse(resp.read().decode("utf-8", errors="ignore").splitlines())
            self._parsers[domain] = (rp, time.time())
            logger.info(f"已加载 robots.txt: {robots_url}")
            return rp
        except Exception as e:
            logger.warning(f"无法加载 robots.txt {domain}: {e}")
            # 缓存失败结果,避免重复尝试
            self._parsers[domain] = (None, time.time())
            return None

    def is_allowed(self, url: str, user_agent: Optional[str] = None) -> bool:
        """检查 URL 是否允许爬取"""
        if not self._respect_robots:
            return True

        parser = self._get_parser(url)
        if parser is None:
            return True  # 无法获取 robots.txt,默认允许

        ua = user_agent or self._user_agent
        try:
            allowed = parser.can_fetch(ua, url)
            if not allowed:
                logger.debug(f"robots.txt 禁止: {url} (UA: {ua})")
            return allowed
        except Exception as e:
            logger.warning(f"robots.txt 检查失败 {url}: {e}")
            return True  # 检查失败,默认允许

    def get_crawl_delay(
        self, url: str, user_agent: Optional[str] = None
    ) -> Optional[float]:
        """获取爬取延迟(秒)"""
        parser = self._get_parser(url)
        if parser is None:
            return None

        ua = user_agent or self._user_agent
        try:
            delay = parser.crawl_delay(ua)
            return delay if delay else None
        except Exception:
            return None

    def get_request_rate(
        self, url: str, user_agent: Optional[str] = None
    ) -> Optional[float]:
        """获取请求速率限制(请求/秒)"""
        delay = self.get_crawl_delay(url, user_agent)
        if delay and delay > 0:
            return 1.0 / delay
        return None

    def clear_cache(self) -> None:
        """清除缓存"""
        self._parsers.clear()

    def is_respecting_robots(self) -> bool:
        """是否正在遵守 robots.txt"""
        return self._respect_robots
