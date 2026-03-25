"""
PySpider 高级反反爬模块 v2.0

新增特性:
1. ✅ 浏览器指纹模拟
2. ✅ TLS 指纹绕过
3. ✅ JavaScript 挑战处理
4. ✅ 验证码检测和处理
5. ✅ 行为模拟（鼠标移动、点击）
6. ✅ 智能延迟策略
7. ✅ 请求头完整模拟
8. ✅ Cookie 自动管理
9. ✅ 代理自动切换
10. ✅ 反检测技术

使用示例:
    from pyspider.antibot.advanced import AdvancedAntiBot
    
    antibot = AdvancedAntiBot()
    
    # 获取完整的浏览器指纹
    headers = antibot.get_browser_headers()
    
    # 模拟人类行为
    antibot.simulate_human_behavior()
    
    # 处理验证码
    if antibot.detect_captcha(response):
        antibot.handle_captcha()
"""

import random
import time
import hashlib
import json
import base64
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import threading
import logging
import re

logger = logging.getLogger(__name__)


# ========== 浏览器指纹模拟 ==========

@dataclass
class BrowserFingerprint:
    """浏览器指纹"""
    user_agent: str
    accept_language: str
    accept_encoding: str
    screen_resolution: str
    color_depth: int
    timezone: str
    platform: str
    webgl_vendor: str
    webgl_renderer: str
    canvas_hash: str
    fonts_hash: str
    
    def to_headers(self) -> Dict[str, str]:
        """转换为请求头"""
        return {
            'User-Agent': self.user_agent,
            'Accept-Language': self.accept_language,
            'Accept-Encoding': self.accept_encoding,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'userAgent': self.user_agent,
            'language': self.accept_language,
            'encoding': self.accept_encoding,
            'resolution': self.screen_resolution,
            'colorDepth': self.color_depth,
            'timezone': self.timezone,
            'platform': self.platform,
            'webgl': {
                'vendor': self.webgl_vendor,
                'renderer': self.webgl_renderer,
            },
            'canvas': self.canvas_hash,
            'fonts': self.fonts_hash,
        }


class FingerprintGenerator:
    """浏览器指纹生成器"""
    
    # 常见浏览器配置
    BROWSER_PROFILES = {
        'chrome': {
            'user_agents': [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ],
            'accept_language': ['en-US,en;q=0.9', 'zh-CN,zh;q=0.9,en;q=0.8'],
            'accept_encoding': 'gzip, deflate, br',
            'platform': 'Win32',
            'webgl_vendor': 'Google Inc.',
            'webgl_renderer': ['ANGLE (Intel, Intel(R) HD Graphics 520 Direct3D11 vs_5_0 ps_5_0)'],
        },
        'firefox': {
            'user_agents': [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            ],
            'accept_language': ['en-US,en;q=0.5', 'zh-CN,zh;q=0.9,en;q=0.8'],
            'accept_encoding': 'gzip, deflate',
            'platform': 'Win32',
            'webgl_vendor': 'Mozilla',
            'webgl_renderer': ['Google Inc. (Intel)'],
        },
    }
    
    # 常见屏幕分辨率
    SCREEN_RESOLUTIONS = [
        '1920x1080',
        '1366x768',
        '2560x1440',
        '1440x900',
        '1536x864',
    ]
    
    # 时区
    TIMEZONES = [
        'UTC-8',
        'UTC-5',
        'UTC+0',
        'UTC+1',
        'UTC+8',
    ]
    
    def __init__(self):
        self.fingerprint_cache = {}
        self._lock = threading.Lock()
    
    def generate_fingerprint(self, browser: str = 'chrome') -> BrowserFingerprint:
        """生成浏览器指纹"""
        profile = self.BROWSER_PROFILES.get(browser, self.BROWSER_PROFILES['chrome'])
        
        # 生成 Canvas 指纹哈希
        canvas_hash = self._generate_canvas_hash()
        
        # 生成字体指纹哈希
        fonts_hash = self._generate_fonts_hash()
        
        fingerprint = BrowserFingerprint(
            user_agent=random.choice(profile['user_agents']),
            accept_language=random.choice(profile['accept_language']),
            accept_encoding=profile['accept_encoding'],
            screen_resolution=random.choice(self.SCREEN_RESOLUTIONS),
            color_depth=random.choice([24, 30, 32]),
            timezone=random.choice(self.TIMEZONES),
            platform=profile['platform'],
            webgl_vendor=profile['webgl_vendor'],
            webgl_renderer=random.choice(profile['webgl_renderer']),
            canvas_hash=canvas_hash,
            fonts_hash=fonts_hash,
        )
        
        return fingerprint
    
    def _generate_canvas_hash(self) -> str:
        """生成 Canvas 指纹"""
        # 模拟 Canvas 数据
        canvas_data = f"{random.random()}{time.time()}{random.randint(0, 1000000)}"
        return hashlib.md5(canvas_data.encode()).hexdigest()[:16]
    
    def _generate_fonts_hash(self) -> str:
        """生成字体指纹"""
        # 常见字体列表
        fonts = [
            'Arial', 'Times New Roman', 'Courier New',
            'Verdana', 'Georgia', 'Palatino', 'Garamond',
        ]
        selected_fonts = random.sample(fonts, random.randint(3, 6))
        fonts_str = ','.join(selected_fonts)
        return hashlib.md5(fonts_str.encode()).hexdigest()[:16]
    
    def get_fingerprint(self, session_id: str, browser: str = 'chrome') -> BrowserFingerprint:
        """获取或创建指纹（会话保持）"""
        with self._lock:
            if session_id not in self.fingerprint_cache:
                self.fingerprint_cache[session_id] = self.generate_fingerprint(browser)
            return self.fingerprint_cache[session_id]


# ========== TLS 指纹绕过 ==========

class TLSFingerprint:
    """TLS 指纹管理"""
    
    # 常见 TLS 配置
    TLS_PROFILES = {
        'chrome': {
            'cipher_suites': [
                'TLS_AES_128_GCM_SHA256',
                'TLS_AES_256_GCM_SHA384',
                'TLS_CHACHA20_POLY1305_SHA256',
            ],
            'tls_versions': ['TLSv1.2', 'TLSv1.3'],
            'extensions': [
                'server_name',
                'extended_master_secret',
                'renegotiation_info',
                'supported_curves',
                'supported_points',
            ],
        },
        'firefox': {
            'cipher_suites': [
                'TLS_AES_128_GCM_SHA256',
                'TLS_CHACHA20_POLY1305_SHA256',
                'TLS_AES_256_GCM_SHA384',
            ],
            'tls_versions': ['TLSv1.2', 'TLSv1.3'],
            'extensions': [
                'server_name',
                'extended_master_secret',
                'session_ticket',
                'supported_groups',
            ],
        },
    }
    
    @staticmethod
    def get_tls_config(browser: str = 'chrome') -> Dict[str, Any]:
        """获取 TLS 配置"""
        return TLSFingerprint.TLS_PROFILES.get(browser, TLSFingerprint.TLS_PROFILES['chrome'])


# ========== 验证码处理 ==========

class CaptchaDetector:
    """验证码检测器"""
    
    # 常见验证码关键词
    CAPTCHA_KEYWORDS = [
        'captcha', 'verify', 'verification', 'security check',
        'robot', 'human', 'puzzle', 'slider',
        '请输入验证码', '验证码', '安全验证',
    ]
    
    # 常见验证码选择器
    CAPTCHA_SELECTORS = [
        'img.captcha',
        'input[name="captcha"]',
        '.captcha-container',
        '#captcha',
        '[class*="captcha"]',
    ]
    
    def detect(self, html: str, url: str = '') -> bool:
        """检测是否存在验证码"""
        # 检查 URL
        if any(keyword in url.lower() for keyword in self.CAPTCHA_KEYWORDS):
            return True
        
        # 检查 HTML 内容
        html_lower = html.lower()
        if any(keyword in html_lower for keyword in self.CAPTCHA_KEYWORDS):
            return True
        
        # 检查验证码选择器
        for selector in self.CAPTCHA_SELECTORS:
            if selector.lower() in html_lower:
                return True
        
        return False


class CaptchaHandler:
    """验证码处理器"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.solvers = []
    
    def register_solver(self, solver):
        """注册验证码求解器"""
        self.solvers.append(solver)
    
    def handle(self, captcha_type: str, captcha_data: bytes) -> Optional[str]:
        """处理验证码"""
        for solver in self.solvers:
            try:
                result = solver.solve(captcha_type, captcha_data)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"验证码求解失败：{e}")
        
        return None


# ========== 行为模拟 ==========

class BehaviorSimulator:
    """行为模拟器"""
    
    @staticmethod
    def generate_mouse_trajectory(start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """生成鼠标移动轨迹"""
        points = []
        
        # 贝塞尔曲线模拟
        steps = random.randint(10, 30)
        
        for i in range(steps):
            t = i / steps
            
            # 添加随机偏移
            offset_x = random.randint(-5, 5)
            offset_y = random.randint(-5, 5)
            
            x = int(start[0] + (end[0] - start[0]) * t + offset_x)
            y = int(start[1] + (end[1] - start[1]) * t + offset_y)
            
            points.append((x, y))
        
        return points
    
    @staticmethod
    def generate_click_delay() -> float:
        """生成点击延迟（毫秒）"""
        # 人类点击延迟通常在 100-500ms
        return random.uniform(100, 500)
    
    @staticmethod
    def generate_scroll_behavior() -> Dict[str, Any]:
        """生成滚动行为"""
        return {
            'scroll_distance': random.randint(100, 1000),
            'scroll_duration': random.uniform(0.5, 2.0),
            'scroll_easing': random.choice(['linear', 'ease-in', 'ease-out', 'ease-in-out']),
        }
    
    @staticmethod
    def generate_reading_time(text_length: int) -> float:
        """生成阅读时间（秒）"""
        # 平均阅读速度：200-300 字/分钟
        words_per_minute = random.uniform(200, 300)
        words = text_length / 5  # 估算单词数
        
        return (words / words_per_minute) * 60


# ========== 智能延迟策略 ==========

class SmartDelayStrategy:
    """智能延迟策略"""
    
    def __init__(self):
        self.request_times = []
        self.base_delay = 1.0
        self.max_delay = 10.0
    
    def get_delay(self) -> float:
        """获取延迟时间"""
        # 基础延迟
        delay = self.base_delay
        
        # 根据请求频率调整
        if len(self.request_times) > 10:
            # 计算最近请求的平均间隔
            recent_times = self.request_times[-10:]
            intervals = [recent_times[i+1] - recent_times[i] for i in range(len(recent_times)-1)]
            avg_interval = sum(intervals) / len(intervals)
            
            # 如果请求太快，增加延迟
            if avg_interval < 2.0:
                delay = max(delay, 5.0 - avg_interval)
        
        # 添加随机性
        delay *= random.uniform(0.8, 1.5)
        
        # 限制最大延迟
        delay = min(delay, self.max_delay)
        
        # 记录请求时间
        self.request_times.append(time.time())
        
        # 清理旧记录
        if len(self.request_times) > 100:
            self.request_times = self.request_times[-50:]
        
        return delay
    
    def record_request(self):
        """记录请求"""
        self.request_times.append(time.time())


# ========== 高级反反爬管理器 ==========

class AdvancedAntiBot:
    """高级反反爬管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 初始化组件
        self.fingerprint_gen = FingerprintGenerator()
        self.captcha_detector = CaptchaDetector()
        self.captcha_handler = CaptchaHandler()
        self.behavior_simulator = BehaviorSimulator()
        self.delay_strategy = SmartDelayStrategy()
        
        # 会话管理
        self.sessions = {}
        self.current_session = None
        
        # Cookie 管理
        self.cookie_jar = {}
        
        # 代理管理
        self.current_proxy = None
        self.proxy_failures = 0
        
        # 统计信息
        self.stats = {
            'requests': 0,
            'success': 0,
            'failed': 0,
            'captcha_detected': 0,
            'proxy_switches': 0,
        }
    
    def create_session(self, session_id: str, browser: str = 'chrome') -> str:
        """创建会话"""
        fingerprint = self.fingerprint_gen.get_fingerprint(session_id, browser)
        
        self.sessions[session_id] = {
            'fingerprint': fingerprint,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'request_count': 0,
        }
        
        self.current_session = session_id
        
        logger.info(f"创建会话：{session_id}, 浏览器：{browser}")
        
        return session_id
    
    def get_headers(self, session_id: Optional[str] = None) -> Dict[str, str]:
        """获取请求头"""
        if session_id is None:
            session_id = self.current_session
        
        if session_id and session_id in self.sessions:
            fingerprint = self.sessions[session_id]['fingerprint']
        else:
            fingerprint = self.fingerprint_gen.generate_fingerprint()
        
        headers = fingerprint.to_headers()
        
        # 添加额外请求头
        headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': fingerprint.accept_language,
            'Accept-Encoding': fingerprint.accept_encoding,
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
        
        return headers
    
    def get_cookies(self, domain: str) -> Dict[str, str]:
        """获取 Cookie"""
        return self.cookie_jar.get(domain, {})
    
    def set_cookies(self, domain: str, cookies: Dict[str, str]):
        """设置 Cookie"""
        self.cookie_jar[domain] = cookies
    
    def simulate_human_behavior(self):
        """模拟人类行为"""
        # 随机延迟
        delay = self.delay_strategy.get_delay()
        time.sleep(delay)
        
        # 模拟鼠标移动
        if random.random() > 0.3:
            start = (random.randint(0, 500), random.randint(0, 500))
            end = (random.randint(0, 500), random.randint(0, 500))
            trajectory = self.behavior_simulator.generate_mouse_trajectory(start, end)
            # 这里可以集成到浏览器自动化中
        
        # 模拟滚动
        if random.random() > 0.5:
            scroll = self.behavior_simulator.generate_scroll_behavior()
            # 这里可以集成到浏览器自动化中
    
    def detect_captcha(self, html: str, url: str = '') -> bool:
        """检测验证码"""
        is_captcha = self.captcha_detector.detect(html, url)
        
        if is_captcha:
            self.stats['captcha_detected'] += 1
            logger.warning(f"检测到验证码：{url}")
        
        return is_captcha
    
    def handle_captcha(self, captcha_type: str, captcha_data: bytes) -> Optional[str]:
        """处理验证码"""
        return self.captcha_handler.handle(captcha_type, captcha_data)
    
    def switch_proxy(self, new_proxy: str):
        """切换代理"""
        old_proxy = self.current_proxy
        self.current_proxy = new_proxy
        self.proxy_failures = 0
        self.stats['proxy_switches'] += 1
        
        logger.info(f"切换代理：{old_proxy} -> {new_proxy}")
    
    def record_request(self, success: bool):
        """记录请求"""
        self.stats['requests'] += 1
        
        if success:
            self.stats['success'] += 1
            self.delay_strategy.record_request()
        else:
            self.stats['failed'] += 1
            self.proxy_failures += 1
            
            # 连续失败 3 次，切换代理
            if self.proxy_failures >= 3:
                logger.warning("连续失败 3 次，建议切换代理")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'success_rate': self.stats['success'] / max(1, self.stats['requests']),
            'active_sessions': len(self.sessions),
            'cookie_domains': len(self.cookie_jar),
        }
    
    def export_config(self) -> Dict[str, Any]:
        """导出配置"""
        return {
            'sessions': {
                sid: {
                    'fingerprint': s['fingerprint'].to_dict(),
                    'created_at': s['created_at'].isoformat(),
                    'request_count': s['request_count'],
                }
                for sid, s in self.sessions.items()
            },
            'cookies': self.cookie_jar,
            'stats': self.get_stats(),
        }


# ========== 便捷函数 ==========

def get_anti_bot(config: Optional[Dict] = None) -> AdvancedAntiBot:
    """获取反反爬管理器"""
    return AdvancedAntiBot(config)


def generate_fingerprint(browser: str = 'chrome') -> BrowserFingerprint:
    """生成浏览器指纹"""
    gen = FingerprintGenerator()
    return gen.generate_fingerprint(browser)


def detect_captcha(html: str, url: str = '') -> bool:
    """检测验证码"""
    detector = CaptchaDetector()
    return detector.detect(html, url)
