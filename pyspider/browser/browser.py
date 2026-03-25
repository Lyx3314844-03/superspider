"""
浏览器自动化模块
支持 Selenium 和 Playwright
"""

from typing import Optional, Dict, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time


class BrowserManager:
    """浏览器管理器（Selenium）"""
    
    def __init__(self, headless: bool = True, user_agent: Optional[str] = None):
        self.headless = headless
        self.user_agent = user_agent
        self.driver = self._create_driver()
    
    def _create_driver(self):
        """创建浏览器驱动"""
        options = ChromeOptions()
        
        if self.headless:
            options.add_argument("--headless")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        if self.user_agent:
            options.add_argument(f"--user-agent={self.user_agent}")
        
        # 隐藏自动化特征
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        # 注入脚本隐藏自动化特征
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        
        return driver
    
    def navigate(self, url: str):
        """导航到 URL"""
        self.driver.get(url)
    
    def get_html(self) -> str:
        """获取 HTML"""
        return self.driver.page_source
    
    def get_text(self) -> str:
        """获取文本"""
        return self.driver.find_element("tag name", "body").text
    
    def get_title(self) -> str:
        """获取标题"""
        return self.driver.title
    
    def click(self, selector: str):
        """点击"""
        element = self.driver.find_element("css selector", selector)
        element.click()
    
    def input_text(self, selector: str, text: str):
        """输入文本"""
        element = self.driver.find_element("css selector", selector)
        element.clear()
        element.send_keys(text)
    
    def screenshot(self, path: str):
        """截图"""
        self.driver.save_screenshot(path)
    
    def execute_script(self, script: str, *args):
        """执行 JavaScript"""
        return self.driver.execute_script(script, *args)
    
    def scroll_to_bottom(self):
        """滚动到底部"""
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    def wait_for_element(self, selector: str, timeout: int = 30):
        """等待元素"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()


class PlaywrightManager:
    """Playwright 浏览器管理器"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.page = None
        self._init_browser()
    
    def _init_browser(self):
        """初始化浏览器"""
        from playwright.sync_api import sync_playwright
        
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
    
    def navigate(self, url: str):
        """导航"""
        self.page.goto(url)
    
    def get_html(self) -> str:
        """获取 HTML"""
        return self.page.content()
    
    def get_text(self, selector: str = "body") -> str:
        """获取文本"""
        return self.page.text_content(selector)
    
    def click(self, selector: str):
        """点击"""
        self.page.click(selector)
    
    def fill(self, selector: str, value: str):
        """填写"""
        self.page.fill(selector, value)
    
    def screenshot(self, path: str):
        """截图"""
        self.page.screenshot(path=path)
    
    def execute_script(self, script: str):
        """执行 JavaScript"""
        return self.page.evaluate(script)
    
    def wait_for_selector(self, selector: str, timeout: int = 30000):
        """等待元素"""
        self.page.wait_for_selector(selector, timeout=timeout)
    
    def scroll_to_bottom(self):
        """滚动到底部"""
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    
    def close(self):
        """关闭"""
        if self.browser:
            self.browser.close()


class JavaScriptExecutor:
    """JavaScript 执行器"""
    
    def __init__(self, driver):
        self.driver = driver
    
    def execute(self, script: str, *args):
        """执行脚本"""
        return self.driver.execute_script(script, *args)
    
    def get_title(self) -> str:
        """获取标题"""
        return self.driver.execute_script("return document.title")
    
    def get_url(self) -> str:
        """获取 URL"""
        return self.driver.execute_script("return window.location.href")
    
    def get_cookies(self) -> Dict[str, str]:
        """获取 Cookie"""
        cookies = {}
        for cookie in self.driver.get_cookies():
            cookies[cookie['name']] = cookie['value']
        return cookies
    
    def set_cookie(self, name: str, value: str):
        """设置 Cookie"""
        self.driver.add_cookie({'name': name, 'value': value})
    
    def get_local_storage(self) -> Dict[str, str]:
        """获取 localStorage"""
        return self.driver.execute_script("""
            var ls = window.localStorage;
            var obj = {};
            for (var i = 0; i < ls.length; i++) {
                obj[ls.key(i)] = ls.getItem(ls.key(i));
            }
            return obj;
        """)
    
    def bypass_detection(self):
        """绕过自动化检测"""
        self.driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
        """)
