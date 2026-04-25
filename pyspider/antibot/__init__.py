"""
PySpider 反反爬模块

特性:
1. ✅ User-Agent 轮换
2. ✅ IP 代理池
3. ✅ Cookie 管理
4. ✅ 请求头随机化
5. ✅ 访问延迟模拟
6. ✅ 人机验证处理

使用示例:
    from pyspider.antibot import UserAgentRotator, ProxyPool

    # UA 轮换
    rotator = UserAgentRotator()
    ua = rotator.get_random_user_agent()

    # 代理池
    pool = ProxyPool()
    pool.add_proxy('http', '1.2.3.4', 8080)
    proxy = pool.get_random_proxy()
"""

import random
import time
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProxyInfo:
    """代理信息"""

    ip: str
    port: int
    protocol: str = "http"
    username: Optional[str] = None
    password: Optional[str] = None
    country: str = "Unknown"
    added_time: datetime = None

    def __post_init__(self):
        if self.added_time is None:
            self.added_time = datetime.now()

    @property
    def url(self) -> str:
        """获取代理 URL"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.ip}:{self.port}"
        return f"{self.protocol}://{self.ip}:{self.port}"

    def to_requests_proxy(self) -> Dict[str, str]:
        """转换为 requests 代理格式"""
        return {
            "http": self.url,
            "https": self.url,
        }


class UserAgentRotator:
    """User-Agent 轮换器"""

    # 浏览器 UA 池
    CHROME_UAS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    FIREFOX_UAS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]

    SAFARI_UAS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    ]

    EDGE_UAS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    ]

    MOBILE_UAS = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
    ]

    def __init__(self):
        self.ua_pool = []
        self.usage_count = {}
        self._initialize_pool()

    def _initialize_pool(self):
        """初始化 UA 池"""
        self.ua_pool = (
            self.CHROME_UAS
            + self.FIREFOX_UAS
            + self.SAFARI_UAS
            + self.EDGE_UAS
            + self.MOBILE_UAS
        )

        for ua in self.ua_pool:
            self.usage_count[ua] = 0

        logger.info(
            f"UserAgentRotator 初始化完成，共 {len(self.ua_pool)} 个 User-Agent"
        )

    def get_random_user_agent(self) -> str:
        """获取随机 User-Agent"""
        ua = random.choice(self.ua_pool)
        self.usage_count[ua] = self.usage_count.get(ua, 0) + 1
        return ua

    def get_browser_user_agent(self, browser: str) -> str:
        """获取指定浏览器的 User-Agent"""
        browser_map = {
            "chrome": self.CHROME_UAS,
            "firefox": self.FIREFOX_UAS,
            "safari": self.SAFARI_UAS,
            "edge": self.EDGE_UAS,
            "mobile": self.MOBILE_UAS,
        }

        pool = browser_map.get(browser.lower(), self.ua_pool)
        ua = random.choice(pool)
        self.usage_count[ua] = self.usage_count.get(ua, 0) + 1
        return ua

    def get_least_used_user_agent(self) -> str:
        """获取最少使用的 User-Agent"""
        if not self.usage_count:
            return self.get_random_user_agent()

        least_used = min(self.usage_count, key=self.usage_count.get)
        self.usage_count[least_used] += 1
        return least_used

    def add_user_agent(self, ua: str):
        """添加自定义 User-Agent"""
        if ua not in self.ua_pool:
            self.ua_pool.append(ua)
            self.usage_count[ua] = 0
            logger.info(f"添加自定义 User-Agent: {ua[:50]}...")

    def reset_usage_count(self):
        """重置使用计数"""
        for ua in self.usage_count:
            self.usage_count[ua] = 0
        logger.info("User-Agent 使用计数已重置")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_uas": len(self.ua_pool),
            "total_requests": sum(self.usage_count.values()),
            "most_used_ua": (
                max(self.usage_count, key=self.usage_count.get)
                if self.usage_count
                else "N/A"
            ),
        }


class ProxyPool:
    """IP 代理池"""

    def __init__(self, health_check_interval: int = 300, timeout: int = 5000):
        """
        初始化代理池

        Args:
            health_check_interval: 健康检查间隔 (秒)
            timeout: 代理超时时间 (毫秒)
        """
        self.proxies: List[ProxyInfo] = []
        self.usage_count = {}
        self.health_status = {}
        self.last_check = {}

        self.health_check_interval = health_check_interval
        self.timeout = timeout

        self._lock = threading.Lock()
        self._start_health_check()

        logger.info(f"ProxyPool 初始化完成，健康检查间隔：{health_check_interval}秒")

    def add_proxy(
        self,
        protocol: str,
        ip: str,
        port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        country: str = "Unknown",
    ):
        """添加代理"""
        proxy = ProxyInfo(ip, port, protocol, username, password, country)

        with self._lock:
            if proxy not in self.proxies:
                self.proxies.append(proxy)
                self.usage_count[str(proxy)] = 0
                self.health_status[str(proxy)] = True
                logger.info(f"添加代理：{proxy}")

    def add_proxies(self, proxies: List[ProxyInfo]):
        """批量添加代理"""
        for proxy in proxies:
            self.add_proxy(
                proxy.protocol,
                proxy.ip,
                proxy.port,
                proxy.username,
                proxy.password,
                proxy.country,
            )
        logger.info(f"批量添加 {len(proxies)} 个代理")

    def load_from_file(self, file_path: str):
        """从文件加载代理"""
        proxies = []

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # 格式：ip:port 或 ip:port:username:password
                parts = line.split(":")
                if len(parts) >= 2:
                    ip = parts[0]
                    port = int(parts[1])
                    protocol = parts[2] if len(parts) > 2 else "http"
                    username = parts[3] if len(parts) > 3 else None
                    password = parts[4] if len(parts) > 4 else None

                    proxies.append(ProxyInfo(ip, port, protocol, username, password))

        self.add_proxies(proxies)
        logger.info(f"从文件加载 {len(proxies)} 个代理：{file_path}")

    def get_random_proxy(self) -> Optional[ProxyInfo]:
        """获取随机代理"""
        healthy_proxies = self.get_healthy_proxies()

        if not healthy_proxies:
            logger.warning("没有可用的健康代理")
            return None

        proxy = random.choice(healthy_proxies)
        self.usage_count[str(proxy)] = self.usage_count.get(str(proxy), 0) + 1
        return proxy

    def get_least_used_proxy(self) -> Optional[ProxyInfo]:
        """获取最少使用的代理"""
        healthy_proxies = self.get_healthy_proxies()

        if not healthy_proxies:
            return None

        least_used = min(healthy_proxies, key=lambda p: self.usage_count.get(str(p), 0))
        self.usage_count[str(least_used)] += 1
        return least_used

    def get_healthy_proxies(self) -> List[ProxyInfo]:
        """获取健康代理列表"""
        return [p for p in self.proxies if self.health_status.get(str(p), True)]

    def mark_unhealthy(self, proxy: ProxyInfo):
        """标记代理为不健康"""
        self.health_status[str(proxy)] = False
        logger.warning(f"标记代理为不健康：{proxy}")

    def _start_health_check(self):
        """启动健康检查"""

        def health_check_loop():
            while True:
                time.sleep(self.health_check_interval)
                self._health_check_all()

        thread = threading.Thread(target=health_check_loop, daemon=True)
        thread.start()

    def _health_check_all(self):
        """健康检查所有代理"""
        logger.info("开始代理健康检查...")

        healthy_count = 0
        unhealthy_count = 0

        for proxy in self.proxies:
            is_healthy = self._check_proxy_health(proxy)
            self.health_status[str(proxy)] = is_healthy
            self.last_check[str(proxy)] = datetime.now()

            if is_healthy:
                healthy_count += 1
            else:
                unhealthy_count += 1

        logger.info(
            f"代理健康检查完成：健康={healthy_count}, 不健康={unhealthy_count}, 总计={len(self.proxies)}"
        )

    def _check_proxy_health(self, proxy: ProxyInfo) -> bool:
        """检查单个代理健康"""
        try:
            # 尝试访问测试网站
            test_url = "https://www.google.com"
            response = requests.get(
                test_url, proxies=proxy.to_requests_proxy(), timeout=self.timeout / 1000
            )
            return response.status_code in [200, 302]
        except Exception as e:
            logger.debug(f"代理健康检查失败 {proxy}: {e}")
            return False

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_proxies": len(self.proxies),
            "healthy_proxies": len(self.get_healthy_proxies()),
            "unhealthy_proxies": len(self.proxies) - len(self.get_healthy_proxies()),
            "total_requests": sum(self.usage_count.values()),
        }

    def remove_proxy(self, proxy: ProxyInfo):
        """移除代理"""
        with self._lock:
            if proxy in self.proxies:
                self.proxies.remove(proxy)
                self.usage_count.pop(str(proxy), None)
                self.health_status.pop(str(proxy), None)
                logger.info(f"移除代理：{proxy}")

    def clear(self):
        """清空代理池"""
        with self._lock:
            self.proxies.clear()
            self.usage_count.clear()
            self.health_status.clear()
            self.last_check.clear()
            logger.info("清空代理池")


class RequestHeadersGenerator:
    """请求头生成器"""

    # 常见 Accept 头
    ACCEPT_HEADERS = [
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "text/html,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    ]

    # 常见 Accept-Language
    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "zh-CN,zh;q=0.9,en;q=0.8",
        "en-GB,en;q=0.9",
        "de-DE,de;q=0.9,en;q=0.8",
    ]

    # 常见 Sec-Ch-Ua
    SEC_CH_UA = [
        '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        '"Not_A Brand";v="99", "Chromium";v="99", "Microsoft Edge";v="120"',
    ]

    def __init__(self):
        self.ua_rotator = UserAgentRotator()

    def generate_headers(self, browser: str = "chrome") -> Dict[str, str]:
        """生成随机请求头"""
        return {
            "User-Agent": self.ua_rotator.get_browser_user_agent(browser),
            "Accept": random.choice(self.ACCEPT_HEADERS),
            "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Ch-Ua": random.choice(self.SEC_CH_UA),
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Cache-Control": "max-age=0",
        }


class AntiBotManager:
    """反反爬管理器"""

    def __init__(self):
        self.ua_rotator = UserAgentRotator()
        self.proxy_pool = ProxyPool()
        self.headers_generator = RequestHeadersGenerator()

        # 请求延迟配置
        self.min_delay = 1.0  # 最小延迟 (秒)
        self.max_delay = 3.0  # 最大延迟 (秒)

        # Cookie 管理
        self.cookies = {}

    def get_random_headers(self, browser: str = "chrome") -> Dict[str, str]:
        """获取随机请求头"""
        return self.headers_generator.generate_headers(browser)

    def get_proxy(self) -> Optional[Dict[str, str]]:
        """获取代理"""
        proxy = self.proxy_pool.get_random_proxy()
        if proxy:
            return proxy.to_requests_proxy()
        return None

    def add_random_delay(self):
        """添加随机延迟"""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

    def set_delay(self, min_delay: float, max_delay: float):
        """设置延迟范围"""
        self.min_delay = min_delay
        self.max_delay = max_delay

    def get_cookies(self, domain: str) -> Dict[str, str]:
        """获取指定域名的 Cookie"""
        return self.cookies.get(domain, {})

    def set_cookies(self, domain: str, cookies: Dict[str, str]):
        """设置 Cookie"""
        self.cookies[domain] = cookies

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "ua_stats": self.ua_rotator.get_stats(),
            "proxy_stats": self.proxy_pool.get_stats(),
            "delay_range": (self.min_delay, self.max_delay),
            "cookie_domains": list(self.cookies.keys()),
        }


# 便捷函数
def get_random_user_agent() -> str:
    """获取随机 User-Agent"""
    rotator = UserAgentRotator()
    return rotator.get_random_user_agent()


def generate_random_headers(browser: str = "chrome") -> Dict[str, str]:
    """生成随机请求头"""
    generator = RequestHeadersGenerator()
    return generator.generate_headers(browser)


from .friction import AccessFrictionReport, analyze_access_friction
