"""
PySpider Playwright 浏览器模块（增强版）

新增功能:
1. ✅ 反检测（隐藏自动化特征）
2. ✅ 代理支持
3. ✅ 多标签页管理
4. ✅ 网络拦截
5. ✅ 请求/响应监听
6. ✅ 指纹模拟
7. ✅ stealth 模式
8. ✅ 自动重试
9. ✅ 智能等待
10. ✅ 人类行为模拟

使用示例:
    from pyspider.browser.enhanced import PlaywrightBrowserEnhanced
    
    browser = PlaywrightBrowserEnhanced(stealth=True)
    browser.start()
    
    browser.navigate("https://example.com")
    browser.smart_click(".button")
    
    browser.close()
"""

import time
import json
import random
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field

try:
    from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, Playwright, Route, Request, Response
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright 未安装，请运行：pip install playwright")
    print("然后运行：playwright install")


@dataclass
class BrowserConfig:
    """浏览器配置"""
    headless: bool = True
    stealth: bool = True
    timeout: int = 30000
    user_agent: str = ""
    proxy: str = ""
    proxy_username: str = ""
    proxy_password: str = ""
    viewport_width: int = 1920
    viewport_height: int = 1080
    ignore_https_errors: bool = True
    record_har: bool = False
    har_path: str = ""
    extra_headers: Dict[str, str] = field(default_factory=dict)
    block_resources: List[str] = field(default_factory=list)


@dataclass
class RequestStats:
    """请求统计"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_bytes: int = 0
    resource_types: Dict[str, int] = field(default_factory=dict)


class PlaywrightBrowserEnhanced:
    """Playwright 浏览器管理器（增强版）"""
    
    # 随机 User-Agent 池
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]
    
    def __init__(self, config: Optional[BrowserConfig] = None):
        """
        初始化浏览器
        
        Args:
            config: 浏览器配置
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright 未安装")
        
        self.config = config or BrowserConfig()
        
        # 如果没有设置 User-Agent，随机选择一个
        if not self.config.user_agent:
            self.config.user_agent = random.choice(self.USER_AGENTS)
        
        # Playwright 实例
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # 状态
        self.is_started = False
        self.page_count = 0
        
        # 统计
        self.stats = RequestStats()
        
        print("=" * 60)
        print("Playwright 浏览器（增强版）")
        print("=" * 60)
        print(f"无头模式：{self.config.headless}")
        print(f"隐身模式：{self.config.stealth}")
        print(f"超时时间：{self.config.timeout}ms")
        print(f"User-Agent: {self.config.user_agent[:50]}...")
        print("=" * 60)
    
    def start(self):
        """启动浏览器"""
        if self.is_started:
            print("✓ 浏览器已启动")
            return
        
        try:
            # 创建 Playwright 实例
            self.playwright = sync_playwright().start()
            
            # 启动浏览器
            launch_options = {
                'headless': self.config.headless,
                'timeout': self.config.timeout,
                'args': self._get_browser_args(),
            }
            
            self.browser = self.playwright.chromium.launch(**launch_options)
            
            # 配置浏览器上下文
            context_options = {
                'user_agent': self.config.user_agent,
                'viewport': {'width': self.config.viewport_width, 'height': self.config.viewport_height},
                'ignore_https_errors': self.config.ignore_https_errors,
                'extra_http_headers': self.config.extra_headers,
            }
            
            # 设置代理
            if self.config.proxy:
                context_options['proxy'] = {
                    'server': self.config.proxy,
                }
                if self.config.proxy_username:
                    context_options['proxy']['username'] = self.config.proxy_username
                if self.config.proxy_password:
                    context_options['proxy']['password'] = self.config.proxy_password
            
            # 记录 HAR
            if self.config.record_har and self.config.har_path:
                context_options['record_har_path'] = self.config.har_path
            
            self.context = self.browser.new_context(**context_options)
            
            # 创建页面
            self.page = self.context.new_page()
            self.page.set_default_timeout(self.config.timeout)
            self.page.set_default_navigation_timeout(self.config.timeout)
            
            # 应用隐身模式
            if self.config.stealth:
                self._apply_stealth_mode()
            
            # 设置资源拦截
            if self.config.block_resources:
                self._setup_resource_interception()
            
            # 监听请求
            self._setup_request_listeners()
            
            self.is_started = True
            self.page_count = 1
            
            print("✓ 浏览器启动成功（增强版）")
            
        except Exception as e:
            print(f"❌ 浏览器启动失败：{e}")
            self.close()
            raise
    
    def _get_browser_args(self) -> List[str]:
        """获取浏览器启动参数"""
        args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-features=ImprovedCookieControls',
            '--disable-features=TranslateUI',
            '--disable-gpu',
            '--disable-extensions',
            '--disable-background-networking',
            '--disable-default-apps',
            '--disable-sync',
        ]
        
        if self.config.stealth:
            args.append(f'--window-size={self.config.viewport_width},{self.config.viewport_height}')
        
        return args
    
    def _apply_stealth_mode(self):
        """应用隐身模式"""
        # 隐藏 webdriver 特征
        self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # 隐藏自动化特征
        self.page.add_init_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        self.page.add_init_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        
        # 模拟真实浏览器
        self.page.add_init_script("Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4})")
        self.page.add_init_script("Object.defineProperty(navigator, 'deviceMemory', {get: () => 8})")
        
        # 隐藏 Headless 特征
        self.page.add_init_script("window.chrome = { runtime: {} }")
        self.page.add_init_script("window.navigator.chrome = { runtime: {} }")
        
        # 修复 Permissions API
        self.page.add_init_script("""
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
        """)
        
        print("✓ 隐身模式已应用")
    
    def _setup_resource_interception(self):
        """设置资源拦截"""
        def intercept(route: Route):
            if route.request.resource_type in self.config.block_resources:
                route.abort()
            else:
                route.continue_()
        
        self.page.route("**/*", intercept)
        print(f"✓ 资源拦截已设置：{self.config.block_resources}")
    
    def _setup_request_listeners(self):
        """设置请求监听"""
        def on_request(request: Request):
            self.stats.total_requests += 1
            resource_type = request.resource_type
            self.stats.resource_types[resource_type] = self.stats.resource_types.get(resource_type, 0) + 1
        
        def on_response(response: Response):
            self.stats.successful_requests += 1
            # 计算响应大小
            try:
                self.stats.total_bytes += len(response.body())
            except:
                pass
        
        def on_request_failed(request: Request):
            self.stats.failed_requests += 1
            print(f"❌ 请求失败：{request.url}")
        
        self.page.on("request", on_request)
        self.page.on("response", on_response)
        self.page.on("requestfailed", on_request_failed)
    
    # ========== 高级导航功能 ==========
    
    def navigate(self, url: str, max_retries: int = 3) -> Page:
        """
        导航到页面（带重试）
        
        Args:
            url: URL 地址
            max_retries: 最大重试次数
            
        Returns:
            Page 对象
        """
        self._ensure_started()
        
        attempts = 0
        while attempts < max_retries:
            try:
                print(f"正在导航：{url} (尝试 {attempts + 1}/{max_retries})")
                
                self.page.goto(url, wait_until='networkidle', timeout=self.config.timeout)
                
                print(f"✓ 页面加载完成：{self.page.title()}")
                return self.page
                
            except Exception as e:
                attempts += 1
                print(f"导航失败：{e}")
                
                if attempts >= max_retries:
                    raise
                
                time.sleep(2 * attempts)  # 递增延迟
        
        return self.page
    
    def navigate_and_wait(self, url: str, selector: str) -> Page:
        """
        导航并等待元素
        
        Args:
            url: URL 地址
            selector: CSS 选择器
            
        Returns:
            Page 对象
        """
        self._ensure_started()
        
        self.page.goto(url, wait_until='domcontentloaded', timeout=self.config.timeout)
        self.page.wait_for_selector(selector, timeout=self.config.timeout)
        
        print(f"✓ 页面加载完成并等待到元素：{selector}")
        return self.page
    
    # ========== 高级元素操作 ==========
    
    def smart_click(self, selector: str, timeout: Optional[int] = None):
        """
        智能点击（带重试和等待）
        
        Args:
            selector: CSS 选择器
            timeout: 超时时间
        """
        self._ensure_started()
        
        try:
            # 等待元素可见
            self.page.wait_for_selector(selector, state='visible', timeout=timeout or self.config.timeout)
            
            # 滚动到元素
            self.page.locator(selector).scroll_into_view_if_needed()
            
            # 点击（带延迟模拟真实点击）
            self.page.click(selector, delay=100)
            
            print(f"✓ 点击成功：{selector}")
            
        except Exception as e:
            print(f"❌ 点击失败：{e}")
            raise
    
    def smart_fill(self, selector: str, value: str, human_like: bool = True):
        """
        智能输入（模拟人类打字）
        
        Args:
            selector: CSS 选择器
            value: 输入值
            human_like: 是否模拟人类打字
        """
        self._ensure_started()
        
        try:
            self.page.wait_for_selector(selector, state='visible', timeout=self.config.timeout)
            
            if human_like:
                # 逐字输入，模拟人类打字
                self.page.fill(selector, "")
                for char in value:
                    self.page.type(selector, char, delay=random.randint(50, 150))
            else:
                self.page.fill(selector, value)
            
            print(f"✓ 输入成功：{selector}")
            
        except Exception as e:
            print(f"❌ 输入失败：{e}")
            raise
    
    def drag_and_drop(self, source_selector: str, target_selector: str):
        """拖拽元素"""
        self._ensure_started()
        self.page.locator(source_selector).drag_to(self.page.locator(target_selector))
        print(f"✓ 拖拽完成：{source_selector} -> {target_selector}")
    
    def hover(self, selector: str):
        """悬停元素"""
        self._ensure_started()
        self.page.hover(selector)
    
    # ========== 高级截图功能 ==========
    
    def screenshot(self, path: str, full_page: bool = True, **kwargs):
        """截图"""
        self._ensure_started()
        
        screenshot_path = Path(path)
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.page.screenshot(path=str(screenshot_path), full_page=full_page, **kwargs)
        print(f"✓ 截图已保存：{path}")
    
    def screenshot_element(self, selector: str, path: str):
        """截图指定元素"""
        self._ensure_started()
        
        element_path = Path(path)
        element_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.page.locator(selector).screenshot(path=str(element_path))
        print(f"✓ 元素截图已保存：{path}")
    
    # ========== 网络拦截 ==========
    
    def intercept_request(self, url_pattern: str, handler: Callable[[Route], None]):
        """拦截请求"""
        self._ensure_started()
        self.page.route(url_pattern, handler)
        print(f"✓ 请求拦截已设置：{url_pattern}")
    
    def set_request_header(self, name: str, value: str):
        """设置请求头"""
        self._ensure_started()
        self.config.extra_headers[name] = value
        self.context.set_extra_http_headers(self.config.extra_headers)
    
    def block_resource(self, resource_type: str):
        """阻止资源加载"""
        if resource_type not in self.config.block_resources:
            self.config.block_resources.append(resource_type)
    
    # ========== Cookie 管理 ==========
    
    def export_cookies(self) -> List[Dict]:
        """导出 Cookie"""
        self._ensure_started()
        return self.context.cookies()
    
    def import_cookies(self, cookies: List[Dict]):
        """导入 Cookie"""
        self._ensure_started()
        self.context.add_cookies(cookies)
        print(f"✓ 已导入 {len(cookies)} 个 Cookie")
    
    def save_cookies_to_file(self, file_path: str):
        """保存 Cookie 到文件"""
        self._ensure_started()
        
        try:
            cookies = self.context.cookies()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            print(f"✓ Cookie 已保存到：{file_path}")
        except Exception as e:
            print(f"❌ 保存 Cookie 失败：{e}")
    
    def load_cookies_from_file(self, file_path: str):
        """从文件加载 Cookie"""
        self._ensure_started()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            self.context.add_cookies(cookies)
            print(f"✓ Cookie 已从文件加载：{file_path}")
        except Exception as e:
            print(f"❌ 加载 Cookie 失败：{e}")
    
    # ========== 多标签页管理 ==========
    
    def new_page(self) -> Page:
        """创建新标签页"""
        self._ensure_started()
        new_page = self.context.new_page()
        self.page_count += 1
        print(f"✓ 创建新标签页，当前标签页数：{self.page_count}")
        return new_page
    
    def close_page(self):
        """关闭当前标签页"""
        self._ensure_started()
        if self.page_count > 1:
            self.page.close()
            self.page_count -= 1
            print(f"✓ 关闭标签页，当前标签页数：{self.page_count}")
    
    def switch_to_page(self, index: int):
        """切换到指定标签页"""
        self._ensure_started()
        pages = self.context.pages
        if 0 <= index < len(pages):
            pages[index].bring_to_front()
            self.page = pages[index]
    
    # ========== 性能优化 ==========
    
    def enable_cache(self):
        """启用缓存"""
        self._ensure_started()
        self.context.set_offline(False)
    
    def disable_cache(self):
        """禁用缓存"""
        self._ensure_started()
        self.context.clear_cookies()
    
    def clear_cache(self):
        """清除缓存"""
        self._ensure_started()
        self.context.clear_cookies()
    
    # ========== 工具方法 ==========
    
    def get_stats(self) -> RequestStats:
        """获取请求统计"""
        return self.stats
    
    def print_stats(self):
        """打印统计信息"""
        print("\n" + "=" * 40)
        print("请求统计")
        print("=" * 40)
        print(f"总请求数：{self.stats.total_requests}")
        print(f"成功：{self.stats.successful_requests}")
        print(f"失败：{self.stats.failed_requests}")
        print(f"总字节数：{self.stats.total_bytes}")
        print("资源类型分布:")
        for resource_type, count in self.stats.resource_types.items():
            print(f"  {resource_type}: {count}")
        print("=" * 40 + "\n")
    
    def _ensure_started(self):
        """确保已启动"""
        if not self.is_started:
            raise RuntimeError("浏览器未启动，请先调用 start()")
    
    def close(self):
        """关闭浏览器"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            
            self.is_started = False
            print("✓ 浏览器已关闭")
        except Exception as e:
            print(f"❌ 关闭失败：{e}")
    
    def __enter__(self):
        """上下文管理器进入"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
    
    def __del__(self):
        """析构函数"""
        self.close()


# 便捷函数

def create_browser(headless: bool = True, stealth: bool = True, **kwargs) -> PlaywrightBrowserEnhanced:
    """创建浏览器"""
    config = BrowserConfig(headless=headless, stealth=stealth, **kwargs)
    return PlaywrightBrowserEnhanced(config)


# 使用示例

if __name__ == "__main__":
    # 示例 1: 基础使用
    print("\n" + "=" * 60)
    print("示例 1: 基础使用")
    print("=" * 60)
    
    with PlaywrightBrowserEnhanced(stealth=True) as browser:
        browser.navigate("https://www.example.com")
        
        title = browser.get_title()
        print(f"页面标题：{title}")
        
        browser.screenshot("downloads/example.png")
    
    # 示例 2: 智能操作
    print("\n" + "=" * 60)
    print("示例 2: 智能操作")
    print("=" * 60)
    
    with PlaywrightBrowserEnhanced() as browser:
        browser.navigate("https://www.google.com")
        
        # 智能输入
        browser.smart_fill("input[name='q']", "Playwright tutorial", human_like=True)
        
        # 智能点击
        browser.smart_click("input[type='submit']")
        
        # 等待结果
        browser.wait_for_selector("#search", timeout=10000)
        
        browser.print_stats()
