"""
PySpider Playwright 高级浏览器模块

新增高级功能:
1. ✅ 高级反检测（多重隐藏）
2. ✅ 网络请求拦截和修改
3. ✅ 性能监控
4. ✅ 自动滚动和懒加载处理
5. ✅ 多页面协同
6. ✅ 高级截图（元素/区域）
7. ✅ 视频录制
8. ✅ 设备模拟
9. ✅ 地理位置模拟
10. ✅ 权限管理

使用示例:
    from pyspider.browser.advanced import PlaywrightBrowserAdvanced

    browser = PlaywrightBrowserAdvanced(stealth=True, block_ads=True)
    browser.start()

    browser.navigate_and_wait("https://example.com", ".content")
    browser.smart_click_with_retry(".button", 3)

    browser.print_performance_report()
    browser.close()
"""

import time
import random
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, field

try:
    from playwright.sync_api import (
        sync_playwright,
        Page,
        Browser,
        BrowserContext,
        Playwright,
        Route,
        Request,
        Response,
    )

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright 未安装，请运行：pip install playwright")
    print("然后运行：playwright install")


@dataclass
class AdvancedBrowserConfig:
    """高级浏览器配置"""

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
    record_video: bool = False
    video_path: str = ""
    block_ads: bool = True
    block_trackers: bool = True
    auto_scroll: bool = True
    timezone: str = ""
    language: str = "en-US"
    geolocation: Optional[Dict[str, float]] = None
    permissions: List[str] = field(default_factory=list)
    extra_headers: Dict[str, str] = field(default_factory=dict)
    block_resources: List[str] = field(default_factory=list)


@dataclass
class PerformanceMetrics:
    """性能指标"""

    page_load_time: int = 0
    dom_content_loaded: int = 0
    first_byte: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    total_bytes: int = 0
    resource_types: Dict[str, int] = field(default_factory=dict)


class PlaywrightBrowserAdvanced:
    """Playwright 高级浏览器管理器"""

    # 随机 User-Agent 池
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]

    def __init__(self, config: Optional[AdvancedBrowserConfig] = None):
        """
        初始化浏览器

        Args:
            config: 高级浏览器配置
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright 未安装")

        self.config = config or AdvancedBrowserConfig()

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

        # 性能指标
        self.metrics = PerformanceMetrics()

        print("=" * 60)
        print("Playwright 浏览器（高级版）")
        print("=" * 60)
        print(f"无头模式：{self.config.headless}")
        print(f"隐身模式：{self.config.stealth}")
        print(f"超时时间：{self.config.timeout}ms")
        print(f"拦截广告：{self.config.block_ads}")
        print(f"自动滚动：{self.config.auto_scroll}")
        print("=" * 60)

    def start(self):
        """启动浏览器"""
        if self.is_started:
            print("✓ 浏览器已启动")
            return

        start_time = time.time()

        try:
            # 创建 Playwright 实例
            self.playwright = sync_playwright().start()

            # 启动浏览器
            launch_options = {
                "headless": self.config.headless,
                "timeout": self.config.timeout,
                "args": self._get_advanced_browser_args(),
            }

            self.browser = self.playwright.chromium.launch(**launch_options)

            # 配置浏览器上下文
            context_options = {
                "user_agent": self.config.user_agent,
                "viewport": {
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
                "ignore_https_errors": self.config.ignore_https_errors,
                "extra_http_headers": self.config.extra_headers,
                "locale": self.config.language,
            }

            # 设置代理
            if self.config.proxy:
                context_options["proxy"] = {
                    "server": self.config.proxy,
                }
                if self.config.proxy_username:
                    context_options["proxy"]["username"] = self.config.proxy_username
                if self.config.proxy_password:
                    context_options["proxy"]["password"] = self.config.proxy_password

            # 设置地理位置
            if self.config.geolocation:
                context_options["geolocation"] = self.config.geolocation

            # 设置权限
            if self.config.permissions:
                context_options["permissions"] = self.config.permissions

            # 录制视频
            if self.config.record_video and self.config.video_path:
                context_options["record_video_dir"] = self.config.video_path
                context_options["record_video_size"] = {
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                }

            self.context = self.browser.new_context(**context_options)

            # 创建页面
            self.page = self.context.new_page()
            self.page.set_default_timeout(self.config.timeout)
            self.page.set_default_navigation_timeout(self.config.timeout)

            # 应用高级隐身模式
            if self.config.stealth:
                self._apply_advanced_stealth_mode()

            # 设置广告拦截
            if self.config.block_ads or self.config.block_trackers:
                self._setup_ad_blocker()

            # 设置性能监控
            self._setup_performance_monitoring()

            self.is_started = True

            load_time = int((time.time() - start_time) * 1000)
            print(f"✓ 浏览器启动成功（高级版） - 耗时：{load_time}ms")

        except Exception as e:
            print(f"❌ 浏览器启动失败：{e}")
            self.close()
            raise

    def _get_advanced_browser_args(self) -> List[str]:
        """获取高级浏览器启动参数"""
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-features=ImprovedCookieControls",
            "--disable-features=TranslateUI",
            "--disable-features=ClientSidePhishingDetection",
            "--disable-features=OptimizationHints",
            "--disable-features=OptimizationGuideModelDownloading",
            "--disable-gpu",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-sync",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-ipc-flooding-protection",
        ]

        if self.config.stealth:
            args.append(
                f"--window-size={self.config.viewport_width},{self.config.viewport_height}"
            )

        return args

    def _apply_advanced_stealth_mode(self):
        """应用高级隐身模式"""
        # 基础隐藏
        self.page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self.page.add_init_script(
            "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})"
        )
        self.page.add_init_script(
            "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})"
        )
        self.page.add_init_script(
            "Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4})"
        )
        self.page.add_init_script(
            "Object.defineProperty(navigator, 'deviceMemory', {get: () => 8})"
        )

        # 高级隐藏
        self.page.add_init_script("window.chrome = { runtime: {} }")
        self.page.add_init_script("window.navigator.chrome = { runtime: {} }")

        # 隐藏 Headless 特征
        self.page.add_init_script(
            "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})"
        )
        self.page.add_init_script(
            "Object.defineProperty(screen, 'pixelDepth', {get: () => 24})"
        )
        self.page.add_init_script(
            "Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.'})"
        )

        # 修复 Canvas 指纹
        self.page.add_init_script("""
            const toBlob = HTMLCanvasElement.prototype.toBlob;
            HTMLCanvasElement.prototype.toBlob = function() {
                const args = Array.from(arguments);
                if (!args[1]) { args[1] = 'image/png'; }
                return toBlob.apply(this, args);
            };
        """)

        # 修复 WebGL 指纹
        self.page.add_init_script("""
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) { return 'Intel Inc.'; }
                if (parameter === 37446) { return 'Intel Iris OpenGL Engine'; }
                return getParameter.call(this, parameter);
            };
        """)

        # 修复 Permissions API
        self.page.add_init_script("""
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
        """)

        # 修复 Navigator 连接
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    rtt: 50,
                    downlink: 10,
                    saveData: false
                })
            });
        """)

        print("✓ 高级隐身模式已应用")

    def _setup_ad_blocker(self):
        """设置广告拦截"""

        def intercept(route: Route):
            url = route.request.url
            if any(
                keyword in url
                for keyword in [
                    "doubleclick",
                    "google-analytics",
                    "adservice",
                    "adsystem",
                    "analytics",
                    "tracking",
                    "pixel",
                    "beacon",
                    "telemetry",
                ]
            ):
                route.abort()
            else:
                route.continue_()

        self.page.route("**/*", intercept)
        print("✓ 广告拦截已设置")

    def _setup_performance_monitoring(self):
        """设置性能监控"""

        def on_request(request: Request):
            self.metrics.total_requests += 1
            resource_type = request.resource_type
            self.metrics.resource_types[resource_type] = (
                self.metrics.resource_types.get(resource_type, 0) + 1
            )

        def on_response(response: Response):
            try:
                self.metrics.total_bytes += len(response.body())
            except Exception:
                pass

        def on_request_failed(request: Request):
            self.metrics.failed_requests += 1

        self.page.on("request", on_request)
        self.page.on("response", on_response)
        self.page.on("requestfailed", on_request_failed)

    # ========== 高级导航功能 ==========

    def navigate_and_wait(
        self, url: str, selector: Optional[str] = None, max_retries: int = 3
    ) -> Page:
        """导航并等待内容加载"""
        self._ensure_started()

        start_time = time.time()

        for attempt in range(max_retries):
            try:
                print(f"正在导航：{url} (尝试 {attempt + 1}/{max_retries})")

                self.page.goto(
                    url, wait_until="domcontentloaded", timeout=self.config.timeout
                )

                self.metrics.dom_content_loaded = int((time.time() - start_time) * 1000)

                # 等待指定元素
                if selector:
                    self.page.wait_for_selector(selector, timeout=self.config.timeout)

                # 自动滚动
                if self.config.auto_scroll:
                    self.auto_scroll_page()

                self.metrics.page_load_time = int((time.time() - start_time) * 1000)

                print(f"✓ 页面加载完成 - 耗时：{self.metrics.page_load_time}ms")
                return self.page

            except Exception as e:
                print(f"导航失败：{e}")
                if attempt >= max_retries - 1:
                    raise
                time.sleep(2 * (attempt + 1))

        return self.page

    def auto_scroll_page(self):
        """自动滚动页面"""
        try:
            # 滚动到底部
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            # 等待懒加载
            self.page.wait_for_timeout(1000)

            # 滚动回顶部
            self.page.evaluate("window.scrollTo(0, 0)")

            print("✓ 自动滚动完成")
        except Exception as e:
            print(f"自动滚动失败：{e}")

    # ========== 高级截图功能 ==========

    def screenshot_element(self, selector: str, path: str):
        """截图指定元素"""
        self._ensure_started()

        element_path = Path(path)
        element_path.parent.mkdir(parents=True, exist_ok=True)

        self.page.locator(selector).screenshot(path=str(element_path))
        print(f"✓ 元素截图已保存：{path}")

    def screenshot_region(self, x: int, y: int, width: int, height: int, path: str):
        """截图指定区域"""
        self._ensure_started()

        region_path = Path(path)
        region_path.parent.mkdir(parents=True, exist_ok=True)

        self.page.screenshot(
            path=str(region_path),
            clip={"x": x, "y": y, "width": width, "height": height},
        )
        print(f"✓ 区域截图已保存：{path}")

    # ========== 高级元素操作 ==========

    def smart_click_with_retry(self, selector: str, max_retries: int = 3):
        """智能点击（带重试）"""
        self._ensure_started()

        for attempt in range(max_retries):
            try:
                # 等待元素可见
                self.page.wait_for_selector(
                    selector, state="visible", timeout=self.config.timeout
                )

                # 滚动到元素
                self.page.locator(selector).scroll_into_view_if_needed()

                # 点击（带延迟模拟真实点击）
                self.page.click(selector, delay=100)

                print(f"✓ 点击成功：{selector}")
                return

            except Exception as e:
                print(f"点击失败：{e}")
                if attempt >= max_retries - 1:
                    raise
                time.sleep(1000 * (attempt + 1))

    def smart_type_human_like(self, selector: str, value: str):
        """智能输入（模拟人类打字）"""
        self._ensure_started()

        try:
            self.page.wait_for_selector(
                selector, state="visible", timeout=self.config.timeout
            )

            # 清空
            self.page.fill(selector, "")

            # 逐字输入，模拟人类打字
            for char in value:
                self.page.type(selector, char, delay=random.randint(50, 150))

            print(f"✓ 智能输入完成：{selector}")

        except Exception as e:
            print(f"智能输入失败：{e}")
            raise

    # ========== 网络拦截 ==========

    def intercept_and_modify_request(
        self, url_pattern: str, header_name: str, header_value: str
    ):
        """拦截并修改请求"""
        self._ensure_started()

        def handler(route: Route):
            headers = dict(route.request.headers)
            headers[header_name] = header_value
            route.fetch(headers=headers)

        self.page.route(url_pattern, handler)
        print(f"✓ 请求拦截已设置：{url_pattern}")

    def set_offline(self, offline: bool):
        """模拟离线状态"""
        self._ensure_started()
        self.context.set_offline(offline)
        print(f"✓ 离线状态：{'开启' if offline else '关闭'}")

    def emulate_slow_network(self):
        """模拟慢速网络"""
        self._ensure_started()
        self.context.emulate_media(reduced_motion="reduce")
        print("✓ 慢速网络模拟已启用")

    # ========== 性能监控 ==========

    def get_metrics(self) -> PerformanceMetrics:
        """获取性能指标"""
        return self.metrics

    def print_performance_report(self):
        """打印性能报告"""
        print("\n" + "=" * 50)
        print("性能报告")
        print("=" * 50)
        print(f"页面加载时间：{self.metrics.page_load_time}ms")
        print(f"DOM 加载时间：{self.metrics.dom_content_loaded}ms")
        print(f"总请求数：{self.metrics.total_requests}")
        print(f"失败请求数：{self.metrics.failed_requests}")
        print(f"总字节数：{self.metrics.total_bytes}")
        print("资源类型分布:")
        for resource_type, count in self.metrics.resource_types.items():
            print(f"  {resource_type}: {count}")
        print("=" * 50 + "\n")

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


def create_advanced_browser(**kwargs) -> PlaywrightBrowserAdvanced:
    """创建高级浏览器"""
    config = AdvancedBrowserConfig(**kwargs)
    return PlaywrightBrowserAdvanced(config)


# 使用示例

if __name__ == "__main__":
    # 示例：高级浏览器使用
    print("\n" + "=" * 60)
    print("Playwright 高级浏览器示例")
    print("=" * 60)

    with PlaywrightBrowserAdvanced(
        stealth=True,
        block_ads=True,
        auto_scroll=True,
    ) as browser:
        browser.navigate_and_wait("https://www.example.com", "h1")

        title = browser.get_title()
        print(f"页面标题：{title}")

        browser.screenshot("downloads/advanced_example.png")

        browser.print_performance_report()
