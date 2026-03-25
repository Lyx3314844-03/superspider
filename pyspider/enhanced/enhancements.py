"""
pyspider 增强模块
添加更多实用功能和工具类
"""

import sys
sys.path.insert(0, 'C:/Users/Administrator/spider')

from pyspider.browser.browser import BrowserManager, PlaywrightManager
from pyspider.parser.parser import HTMLParser, JSONParser
from pyspider.core.models import Request, Response, Page
from pyspider.core.spider import Spider
from pyspider.downloader.downloader import HTTPDownloader
import time
import json
import random
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from pathlib import Path


# ============== 增强功能 1: 智能重试机制 ==============
class RetryHandler:
    """智能重试处理器"""
    
    def __init__(self, max_retries=3, base_delay=1.0, exponential=True):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.exponential = exponential
    
    def execute_with_retry(self, func, *args, **kwargs):
        """带重试执行函数"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                delay = self._calculate_delay(attempt)
                print(f"  尝试 {attempt+1}/{self.max_retries} 失败：{e}")
                print(f"  等待 {delay:.1f} 秒后重试...")
                time.sleep(delay)
        
        raise last_exception
    
    def _calculate_delay(self, attempt):
        """计算延迟时间"""
        if self.exponential:
            return self.base_delay * (2 ** attempt)
        return self.base_delay


# ============== 增强功能 2: 请求头随机化 ==============
class UserAgentRotator:
    """User-Agent 轮换器"""
    
    USER_AGENTS = [
        # Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        # Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]
    
    @classmethod
    def get_random_ua(cls):
        """获取随机 User-Agent"""
        return random.choice(cls.USER_AGENTS)
    
    @classmethod
    def get_headers(cls, referer=None):
        """获取随机请求头"""
        headers = {
            "User-Agent": cls.get_random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }
        if referer:
            headers["Referer"] = referer
        return headers


# ============== 增强功能 3: 代理池支持 ==============
@dataclass
class Proxy:
    """代理服务器"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"
    
    def to_url(self) -> str:
        """转换为代理 URL"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"


class ProxyPool:
    """代理池"""
    
    def __init__(self):
        self.proxies: List[Proxy] = []
        self.current_index = 0
    
    def add_proxy(self, proxy: Proxy):
        """添加代理"""
        self.proxies.append(proxy)
    
    def get_next(self) -> Optional[Proxy]:
        """获取下一个代理"""
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
    
    def remove_current(self):
        """移除当前代理（失败时）"""
        if self.proxies:
            self.proxies.pop(self.current_index)
            if self.current_index >= len(self.proxies):
                self.current_index = 0


# ============== 增强功能 4: 数据导出器 ==============
class DataExporter:
    """数据导出器"""
    
    @staticmethod
    def to_json(data: List[Dict], filename: str, indent=2, ensure_ascii=False):
        """导出为 JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
        print(f"  数据已导出到：{filename}")
    
    @staticmethod
    def to_csv(data: List[Dict], filename: str, delimiter=','):
        """导出为 CSV"""
        if not data:
            return
        
        with open(filename, 'w', encoding='utf-8') as f:
            # 写入表头
            headers = list(data[0].keys())
            f.write(delimiter.join(headers) + '\n')
            
            # 写入数据
            for row in data:
                values = [str(row.get(h, '')) for h in headers]
                f.write(delimiter.join(values) + '\n')
        
        print(f"  数据已导出到：{filename}")
    
    @staticmethod
    def to_txt(data: List[Dict], filename: str, encoding='utf-8'):
        """导出为文本"""
        with open(filename, 'w', encoding=encoding) as f:
            for i, item in enumerate(data):
                f.write(f"{'='*50}\n")
                f.write(f"记录 {i+1}\n")
                f.write(f"{'='*50}\n")
                for key, value in item.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")
        
        print(f"  数据已导出到：{filename}")


# ============== 增强功能 5: 智能爬虫基类 ==============
class EnhancedSpider(Spider):
    """增强型爬虫基类"""
    
    def __init__(self, name="EnhancedSpider", use_proxy=False, use_retry=True):
        super().__init__(name=name)
        self.use_proxy = use_proxy
        self.use_retry = use_retry
        self.proxy_pool = ProxyPool() if use_proxy else None
        self.retry_handler = RetryHandler() if use_retry else None
        self.stats = {
            'pages_crawled': 0,
            'pages_failed': 0,
            'items_extracted': 0,
            'bytes_downloaded': 0,
            'start_time': time.time(),
        }
    
    def add_proxy(self, host, port, username=None, password=None, protocol='http'):
        """添加代理"""
        if self.proxy_pool:
            proxy = Proxy(host=host, port=port, username=username, password=password, protocol=protocol)
            self.proxy_pool.add_proxy(proxy)
    
    def crawl_with_retry(self, url, callback, **kwargs):
        """带重试的爬取"""
        if self.use_retry:
            return self.retry_handler.execute_with_retry(self._crawl_single, url, callback, **kwargs)
        return self._crawl_single(url, callback, **kwargs)
    
    def _crawl_single(self, url, callback, **kwargs):
        """单次爬取"""
        headers = UserAgentRotator.get_headers()
        request = Request(url=url, headers=headers)
        
        if self.proxy_pool:
            proxy = self.proxy_pool.get_next()
            if proxy:
                request.meta['proxy'] = proxy.to_url()
        
        response = self.downloader.download(request)
        page = Page(response=response)
        
        self.stats['pages_crawled'] += 1
        self.stats['bytes_downloaded'] += len(response.text.encode('utf-8'))
        
        try:
            items = callback(page)
            if items:
                self.stats['items_extracted'] += len(items)
            return items
        except Exception as e:
            self.stats['pages_failed'] += 1
            print(f"  爬取失败 {url}: {e}")
            if self.proxy_pool:
                self.proxy_pool.remove_current()
            raise
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        elapsed = time.time() - self.stats['start_time']
        return {
            **self.stats,
            'elapsed_seconds': elapsed,
            'pages_per_second': self.stats['pages_crawled'] / elapsed if elapsed > 0 else 0,
        }
    
    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        print("\n" + "="*50)
        print("爬虫统计")
        print("="*50)
        print(f"爬取页面：{stats['pages_crawled']}")
        print(f"失败页面：{stats['pages_failed']}")
        print(f"提取数据：{stats['items_extracted']} 条")
        print(f"下载字节：{stats['bytes_downloaded']:,} bytes")
        print(f"运行时间：{stats['elapsed_seconds']:.1f} 秒")
        print(f"页面/秒：{stats['pages_per_second']:.2f}")
        print("="*50)


# ============== 增强功能 6: 反反爬虫工具 ==============
class AntiBot:
    """反反爬虫工具"""
    
    @staticmethod
    def get_stealth_headers() -> Dict[str, str]:
        """获取隐身请求头"""
        return {
            **UserAgentRotator.get_headers(),
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Priority": "u=0, i",
        }
    
    @staticmethod
    def generate_random_delay(min_sec=1.0, max_sec=3.0) -> float:
        """生成随机延迟"""
        return random.uniform(min_sec, max_sec)
    
    @staticmethod
    def human_like_scroll(browser, scroll_times=5, scroll_pause=1.0):
        """模拟人类滚动行为"""
        for i in range(scroll_times):
            # 随机滚动距离
            scroll_distance = random.randint(300, 800)
            browser.execute_script(f"window.scrollBy(0, {scroll_distance})")
            
            # 随机暂停
            time.sleep(AntiBot.generate_random_delay(scroll_pause, scroll_pause+1))
        
        # 滚动回顶部
        browser.execute_script("window.scrollTo(0, 0)")
        time.sleep(0.5)
    
    @staticmethod
    def bypass_cloudflare(browser, timeout=30):
        """绕过 Cloudflare 验证"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 检查是否还在验证页面
            html = browser.get_html()
            
            if "Checking your browser" in html or "just a moment" in html.lower():
                print("  检测到 Cloudflare 验证，等待中...")
                time.sleep(2)
            else:
                print("  通过 Cloudflare 验证")
                return True
        
        print("  Cloudflare 验证超时")
        return False


# ============== 使用示例 ==============
def demo():
    """演示增强功能"""
    print("="*60)
    print("pyspider 增强功能演示")
    print("="*60)
    
    # 1. User-Agent 轮换
    print("\n1. User-Agent 轮换:")
    for i in range(3):
        ua = UserAgentRotator.get_random_ua()
        print(f"   {i+1}. {ua[:60]}...")
    
    # 2. 代理池
    print("\n2. 代理池:")
    pool = ProxyPool()
    pool.add_proxy(Proxy("proxy1.example.com", 8080))
    pool.add_proxy(Proxy("proxy2.example.com", 8080, "user", "pass"))
    for i in range(4):
        proxy = pool.get_next()
        if proxy:
            print(f"   {i+1}. {proxy.to_url()}")
    
    # 3. 数据导出
    print("\n3. 数据导出:")
    test_data = [
        {"title": "视频 1", "duration": "10:00", "url": "https://example.com/1"},
        {"title": "视频 2", "duration": "20:00", "url": "https://example.com/2"},
    ]
    DataExporter.to_json(test_data, "test_export.json")
    DataExporter.to_csv(test_data, "test_export.csv")
    
    # 4. 重试机制
    print("\n4. 重试机制:")
    retry = RetryHandler(max_retries=3, base_delay=0.5)
    attempt_count = [0]
    
    def failing_func():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise Exception("模拟失败")
        return "成功"
    
    try:
        result = retry.execute_with_retry(failing_func)
        print(f"   结果：{result}")
    except Exception as e:
        print(f"   最终失败：{e}")
    
    print("\n" + "="*60)
    print("演示完成!")
    print("="*60)


if __name__ == "__main__":
    demo()
