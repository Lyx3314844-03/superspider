"""
反反爬模块
提供多种反反爬策略
"""

import random
import time
import hashlib
import re
from typing import Dict, List, Optional
from datetime import datetime


class AntiBotHandler:
    """反反爬处理器"""

    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        ]
        self.referers = [
            "https://www.google.com/",
            "https://www.bing.com/",
            "https://www.baidu.com/",
            "https://duckduckgo.com/",
        ]
        self.languages = [
            "zh-CN,zh;q=0.9,en;q=0.8",
            "en-US,en;q=0.9",
            "zh-TW,zh;q=0.9",
            "ja-JP,ja;q=0.9",
        ]

    def get_random_headers(self) -> Dict[str, str]:
        """获取随机请求头"""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Referer": random.choice(self.referers),
            "Accept-Language": random.choice(self.languages),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }

    def get_intelligent_delay(self, base_delay: float = 1.0) -> float:
        """获取智能延迟"""
        # 基础延迟
        delay = base_delay + random.uniform(0, 2)

        # 随机添加额外延迟（30% 概率）
        if random.random() < 0.3:
            delay += random.uniform(1, 3)

        # 时间段调整（夜间增加延迟）
        hour = datetime.now().hour
        if hour < 6 or hour > 23:
            delay *= 1.5

        return delay

    def is_blocked(self, html: str, status_code: int) -> bool:
        """检查是否被封禁"""
        blocked_keywords = [
            "access denied",
            "blocked",
            "captcha",
            "验证码",
            "封禁",
            "403 forbidden",
            "429 too many requests",
            "request rejected",
            "ip banned",
        ]

        html_lower = html.lower()
        for keyword in blocked_keywords:
            if keyword.lower() in html_lower:
                return True

        if status_code in (403, 429):
            return True

        return False

    def bypass_cloudflare(self) -> Dict[str, str]:
        """绕过 Cloudflare"""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def bypass_akamai(self) -> Dict[str, str]:
        """绕过 Akamai"""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "X-Requested-With": "XMLHttpRequest",
        }

    def generate_fingerprint(self) -> str:
        """生成浏览器指纹"""
        data = f"{time.time()}{random.random()}"
        return hashlib.md5(data.encode()).hexdigest()

    def rotate_proxy(self, proxy_pool: List[str]) -> str:
        """轮换代理"""
        if not proxy_pool:
            return None
        return random.choice(proxy_pool)

    def solve_captcha(self, captcha_image: bytes, api_key: str = None) -> Optional[str]:
        """解决验证码（需要第三方服务）"""
        # 可集成 2Captcha、Anti-Captcha 等服务
        # 这里只是示例
        if api_key:
            # 调用第三方 API
            pass
        return None

    def get_stealth_headers(self) -> Dict[str, str]:
        """获取隐身请求头"""
        return {
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
        }


class CloudflareBypass:
    """Cloudflare 绕过"""

    def __init__(self):
        self.antibot = AntiBotHandler()

    def get_headers(self) -> Dict[str, str]:
        """获取绕过 Cloudflare 的请求头"""
        headers = self.antibot.bypass_cloudflare()
        headers.update(self.antibot.get_stealth_headers())
        return headers

    def solve_challenge(self, html: str) -> Optional[str]:
        """解决 Cloudflare 挑战"""
        # 提取挑战参数
        challenge_match = re.search(r'name="jschl_vc" value="([^"]+)"', html)
        if not challenge_match:
            return None

        # 这里需要解析 JavaScript 挑战
        # 实际应该使用 selenium 或 cloudscraper
        return None


class AkamaiBypass:
    """Akamai 绕过"""

    def __init__(self):
        self.antibot = AntiBotHandler()

    def get_headers(self) -> Dict[str, str]:
        """获取绕过 Akamai 的请求头"""
        headers = self.antibot.bypass_akamai()
        headers.update(self.antibot.get_stealth_headers())
        return headers


class CaptchaSolver:
    """验证码解决器"""

    def __init__(self, api_key: str = None, service: str = "2captcha"):
        self.api_key = api_key
        self.service = service

    def solve_image(self, image_data: bytes) -> Optional[str]:
        """解决图片验证码"""
        if not self.api_key:
            return None

        # 调用第三方服务
        # 如 2Captcha、Anti-Captcha 等
        return None

    def solve_recaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """解决 reCAPTCHA"""
        if not self.api_key:
            return None

        # 调用第三方服务
        return None

    def solve_hcaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """解决 hCaptcha"""
        if not self.api_key:
            return None

        # 调用第三方服务
        return None
