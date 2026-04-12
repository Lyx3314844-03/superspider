"""
PySpider Playwright 浏览器模块

功能:
1. ✅ 浏览器启动和关闭
2. ✅ 页面导航
3. ✅ 元素操作（点击、输入、选择）
4. ✅ 截图和 PDF
5. ✅ JavaScript 执行
6. ✅ 文件下载
7. ✅ Cookie 管理
8. ✅ 无头/有头模式切换
9. ✅ 反检测（User-Agent、指纹等）

使用示例:
    from pyspider.browser import PlaywrightBrowser

    browser = PlaywrightBrowser(headless=True)
    browser.start()

    page = browser.navigate("https://example.com")
    title = browser.get_title()

    browser.screenshot("screenshot.png")
    browser.close()
"""

import json
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    from playwright.sync_api import (
        sync_playwright,
        Page,
        Browser,
        BrowserContext,
        Playwright,
    )

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright 未安装，请运行：pip install playwright")
    print("然后运行：playwright install")


class PlaywrightBrowser:
    """Playwright 浏览器管理器"""

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,
        user_agent: Optional[str] = None,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        ignore_https_errors: bool = True,
        storage_state: Optional[str] = None,
    ):
        """
        初始化浏览器

        Args:
            headless: 是否无头模式
            timeout: 超时时间（毫秒）
            user_agent: User-Agent
            viewport_width: 视口宽度
            viewport_height: 视口高度
            ignore_https_errors: 忽略 HTTPS 错误
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright 未安装")

        self.headless = headless
        self.timeout = timeout
        self.user_agent = (
            user_agent
            or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.ignore_https_errors = ignore_https_errors
        self.storage_state = storage_state

        # Playwright 实例
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        self.is_started = False

        print("=" * 60)
        print("Playwright 浏览器")
        print("=" * 60)
        print(f"无头模式：{headless}")
        print(f"超时时间：{timeout}ms")
        print(f"视口大小：{viewport_width}x{viewport_height}")
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
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                timeout=self.timeout,
            )

            # 创建浏览器上下文
            self.context = self.browser.new_context(
                user_agent=self.user_agent,
                viewport={"width": self.viewport_width, "height": self.viewport_height},
                ignore_https_errors=self.ignore_https_errors,
                storage_state=self.storage_state if self.storage_state else None,
            )

            # 创建页面
            self.page = self.context.new_page()
            self.page.set_default_timeout(self.timeout)
            self.page.set_default_navigation_timeout(self.timeout)

            self.is_started = True
            print("✓ 浏览器启动成功")

        except Exception as e:
            print(f"❌ 浏览器启动失败：{e}")
            self.close()
            raise

    def navigate(self, url: str, wait_until: str = "networkidle") -> Page:
        """
        导航到页面

        Args:
            url: URL 地址
            wait_until: 等待状态 ('load', 'domcontentloaded', 'networkidle', 'commit')

        Returns:
            Page 对象
        """
        self._ensure_started()

        try:
            print(f"正在导航：{url}")
            self.page.goto(url, wait_until=wait_until, timeout=self.timeout)

            title = self.page.title()
            print(f"✓ 页面加载完成：{title}")

            return self.page

        except Exception as e:
            print(f"❌ 导航失败：{e}")
            raise

    def click(self, selector: str):
        """点击元素"""
        self._ensure_started()
        self.page.click(selector)

    def fill(self, selector: str, value: str):
        """输入文本"""
        self._ensure_started()
        self.page.fill(selector, value)

    def get_text(self, selector: str) -> str:
        """获取元素文本"""
        self._ensure_started()
        element = self.page.query_selector(selector)
        return element.text_content() if element else ""

    def get_attribute(self, selector: str, attribute: str) -> str:
        """获取元素属性"""
        self._ensure_started()
        return self.page.get_attribute(selector, attribute)

    def evaluate(self, script: str, arg: Any = None) -> Any:
        """
        执行 JavaScript

        Args:
            script: JavaScript 代码
            arg: 参数

        Returns:
            执行结果
        """
        self._ensure_started()
        if arg is not None:
            return self.page.evaluate(script, arg)
        return self.page.evaluate(script)

    def screenshot(self, path: str, full_page: bool = True):
        """
        截图

        Args:
            path: 保存路径
            full_page: 是否全屏截图
        """
        self._ensure_started()

        screenshot_path = Path(path)
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)

        self.page.screenshot(
            path=str(screenshot_path),
            full_page=full_page,
        )

        print(f"✓ 截图已保存：{path}")

    def pdf(self, path: str):
        """
        保存为 PDF

        Args:
            path: 保存路径
        """
        self._ensure_started()

        pdf_path = Path(path)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        self.page.pdf(
            path=str(pdf_path),
            print_background=True,
        )

        print(f"✓ PDF 已保存：{path}")

    def download_file(self, url: str, save_path: str) -> str:
        """
        下载文件

        Args:
            url: 文件 URL
            save_path: 保存路径

        Returns:
            保存路径
        """
        self._ensure_started()

        try:
            with self.page.expect_download() as download_info:
                self.page.goto(url)

            download = download_info.value
            download.save_as(save_path)

            print(f"✓ 文件已下载：{save_path}")
            return save_path

        except Exception as e:
            print(f"❌ 下载失败：{e}")
            raise

    def get_all_links(self) -> List[str]:
        """获取所有链接"""
        self._ensure_started()
        return self.page.locator("a").all_text_contents()

    def get_all_images(self) -> List[str]:
        """获取所有图片 URL"""
        self._ensure_started()
        return self.page.locator("img").get_attribute("src")

    def scroll_to(self, x: int, y: int):
        """滚动页面"""
        self._ensure_started()
        self.page.evaluate(f"window.scrollTo({x}, {y})")

    def scroll_to_bottom(self):
        """滚动到底部"""
        self._ensure_started()
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    def set_cookie(self, name: str, value: str, domain: str):
        """设置 Cookie"""
        self._ensure_started()
        self.context.add_cookies(
            [
                {
                    "name": name,
                    "value": value,
                    "domain": domain,
                    "path": "/",
                }
            ]
        )

    def get_cookies(self) -> List[Dict]:
        """获取 Cookie"""
        self._ensure_started()
        return self.context.cookies()

    def clear_cookies(self):
        """清除 Cookie"""
        self._ensure_started()
        self.context.clear_cookies()

    def load_cookies_file(self, path: str):
        """从 JSON 文件加载 Cookie"""
        self._ensure_started()
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("cookies") or payload.get("items") or list(payload.values())
        cookies = [item for item in payload if isinstance(item, dict)]
        if cookies:
            self.context.add_cookies(cookies)

    def save_storage_state(self, path: str):
        """保存 Playwright storage state"""
        self._ensure_started()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.context.storage_state(path=str(target))

    def save_cookies(self, path: str):
        """保存当前 Cookie 到 JSON 文件"""
        self._ensure_started()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.context.cookies(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def set_user_agent(self, user_agent: str):
        """设置 User-Agent"""
        self._ensure_started()
        self.user_agent = user_agent
        self.context.add_init_script(f"""
            Object.defineProperty(navigator, 'userAgent', {{
                value: '{user_agent}'
            }})
        """)

    def reload(self):
        """刷新页面"""
        self._ensure_started()
        self.page.reload()

    def go_back(self):
        """后退"""
        self._ensure_started()
        self.page.go_back()

    def go_forward(self):
        """前进"""
        self._ensure_started()
        self.page.go_forward()

    def get_title(self) -> str:
        """获取页面标题"""
        self._ensure_started()
        return self.page.title()

    def get_url(self) -> str:
        """获取当前 URL"""
        self._ensure_started()
        return self.page.url

    def get_content(self) -> str:
        """获取页面 HTML"""
        self._ensure_started()
        return self.page.content()

    def is_visible(self, selector: str) -> bool:
        """检查元素是否可见"""
        self._ensure_started()
        return self.page.is_visible(selector)

    def is_hidden(self, selector: str) -> bool:
        """检查元素是否隐藏"""
        self._ensure_started()
        return self.page.is_hidden(selector)

    def wait_for_selector(self, selector: str, timeout: Optional[int] = None):
        """等待元素出现"""
        self._ensure_started()
        self.page.wait_for_selector(selector, timeout=timeout or self.timeout)

    def wait_for_load_state(self, state: str = "networkidle"):
        """等待加载状态"""
        self._ensure_started()
        self.page.wait_for_load_state(state)

    def set_timeout(self, timeout: int):
        """更新默认超时设置（毫秒）。"""
        self.timeout = timeout
        if self.page:
            self.page.set_default_timeout(timeout)
            self.page.set_default_navigation_timeout(timeout)

    def select_option(self, selector: str, value: str) -> List[str]:
        """选择下拉框选项"""
        self._ensure_started()
        return self.page.select_option(selector, value)

    def upload_file(self, selector: str, file_path: str):
        """上传文件"""
        self._ensure_started()
        self.page.set_input_files(selector, file_path)

    def _ensure_started(self):
        """确保已启动"""
        if not self.is_started:
            raise RuntimeError("浏览器未启动，请先调用 start()")

    def close(self):
        """关闭浏览器"""
        if not any([self.browser, self.playwright, self.context, self.page]):
            self.is_started = False
            return
        try:
            if self.page:
                try:
                    self.page.close()
                except Exception:
                    pass
            if self.context:
                try:
                    self.context.close()
                except Exception:
                    pass
            if self.browser:
                try:
                    self.browser.close()
                except Exception:
                    pass
            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception as e:
                    if "Event loop is closed" not in str(e):
                        raise

            self.is_started = False
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
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
        try:
            self.close()
        except Exception:
            pass


# 便捷函数


def create_browser(headless: bool = True, **kwargs) -> PlaywrightBrowser:
    """创建浏览器"""
    return PlaywrightBrowser(headless=headless, **kwargs)


def quick_scrape(url: str, selectors: Dict[str, str]) -> Dict[str, str]:
    """
    快速爬取

    Args:
        url: URL
        selectors: CSS 选择器字典

    Returns:
        提取的数据
    """
    browser = PlaywrightBrowser()
    browser.start()

    try:
        browser.navigate(url)

        data = {}
        for key, selector in selectors.items():
            data[key] = browser.get_text(selector)

        return data

    finally:
        browser.close()


# 使用示例

if __name__ == "__main__":
    # 示例 1: 基础使用
    print("\n" + "=" * 60)
    print("示例 1: 基础使用")
    print("=" * 60)

    with PlaywrightBrowser(headless=True) as browser:
        browser.navigate("https://www.example.com")

        title = browser.get_title()
        print(f"页面标题：{title}")

        content = browser.get_text("h1")
        print(f"主要内容：{content}")

        browser.screenshot("downloads/example.png")

    # 示例 2: 执行 JavaScript
    print("\n" + "=" * 60)
    print("示例 2: 执行 JavaScript")
    print("=" * 60)

    with PlaywrightBrowser() as browser:
        browser.navigate("https://www.google.com")

        # 获取窗口大小
        window_size = browser.evaluate("""
            () => {
                return {
                    width: window.innerWidth,
                    height: window.innerHeight
                }
            }
        """)

        print(f"窗口大小：{window_size}")

    # 示例 3: 快速爬取
    print("\n" + "=" * 60)
    print("示例 3: 快速爬取")
    print("=" * 60)

    data = quick_scrape(
        "https://www.example.com",
        {
            "title": "h1",
            "description": "p",
        },
    )

    print(f"提取的数据：{data}")
