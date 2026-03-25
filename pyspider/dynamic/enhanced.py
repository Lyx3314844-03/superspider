"""
动态爬取增强模块
支持 Selenium/Playwright 动态等待、滚动加载、表单交互
"""

from typing import Optional, Callable, List, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time


class DynamicWaitEnhanced:
    """动态等待（增强版）"""
    
    def __init__(self, driver, timeout: int = 30, poll_frequency: float = 0.5):
        self.driver = driver
        self.timeout = timeout
        self.poll_frequency = poll_frequency
        self.wait = WebDriverWait(driver, timeout, poll_frequency)
    
    def wait_for_element_visible(self, selector: str, by=By.CSS_SELECTOR, timeout: int = None) -> bool:
        """等待元素可见"""
        try:
            wait = WebDriverWait(self.driver, timeout or self.timeout)
            wait.until(EC.visibility_of_element_located((by, selector)))
            return True
        except TimeoutException:
            return False
    
    def wait_for_element_clickable(self, selector: str, by=By.CSS_SELECTOR, timeout: int = None) -> bool:
        """等待元素可点击"""
        try:
            wait = WebDriverWait(self.driver, timeout or self.timeout)
            wait.until(EC.element_to_be_clickable((by, selector)))
            return True
        except TimeoutException:
            return False
    
    def wait_for_element_present(self, selector: str, by=By.CSS_SELECTOR, timeout: int = None) -> bool:
        """等待元素存在"""
        try:
            wait = WebDriverWait(self.driver, timeout or self.timeout)
            wait.until(EC.presence_of_element_located((by, selector)))
            return True
        except TimeoutException:
            return False
    
    def wait_for_text_present(self, text: str, timeout: int = None) -> bool:
        """等待文本出现"""
        try:
            wait = WebDriverWait(self.driver, timeout or self.timeout)
            wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), text))
            return True
        except TimeoutException:
            return False
    
    def wait_for_url_contains(self, text: str, timeout: int = None) -> bool:
        """等待 URL 包含"""
        try:
            wait = WebDriverWait(self.driver, timeout or self.timeout)
            wait.until(EC.url_contains(text))
            return True
        except TimeoutException:
            return False
    
    def wait_for_url_matches(self, pattern: str, timeout: int = None) -> bool:
        """等待 URL 匹配"""
        try:
            wait = WebDriverWait(self.driver, timeout or self.timeout)
            wait.until(EC.url_matches(pattern))
            return True
        except TimeoutException:
            return False
    
    def wait_for_ajax(self, timeout: int = None) -> bool:
        """等待 AJAX 完成"""
        try:
            wait = WebDriverWait(self.driver, timeout or self.timeout)
            wait.until(lambda d: d.execute_script("return jQuery.active == 0") if d.execute_script("return typeof jQuery !== 'undefined'") else True)
            return True
        except TimeoutException:
            return True
    
    def wait_for_network_idle(self, timeout: int = None) -> bool:
        """等待网络空闲"""
        try:
            wait = WebDriverWait(self.driver, timeout or self.timeout)
            wait.until(lambda d: d.execute_script("""
                var entries = performance.getEntriesByType('resource');
                var loading = entries.filter(function(e) { return e.responseEnd === 0; }).length;
                return loading === 0;
            """))
            return True
        except TimeoutException:
            return False
    
    def wait_for_condition(self, condition: Callable, timeout: int = None, message: str = "") -> bool:
        """等待自定义条件"""
        try:
            wait = WebDriverWait(self.driver, timeout or self.timeout, 
                              poll_frequency=self.poll_frequency,
                              ignored_exceptions=[TimeoutException])
            wait.until(condition, message)
            return True
        except TimeoutException:
            return False
    
    def wait_for_elements_count(self, selector: str, count: int, by=By.CSS_SELECTOR, timeout: int = None) -> bool:
        """等待元素数量"""
        try:
            wait = WebDriverWait(self.driver, timeout or self.timeout)
            wait.until(lambda d: len(d.find_elements(by, selector)) == count)
            return True
        except TimeoutException:
            return False
    
    def sleep(self, ms: int) -> None:
        """休眠"""
        time.sleep(ms / 1000.0)


class ScrollLoaderEnhanced:
    """滚动加载器（增强版）"""
    
    def __init__(self, driver):
        self.driver = driver
    
    def scroll_to_bottom(self, pause_ms: int = 1000, max_scrolls: int = 50, stable_threshold: int = 2) -> int:
        """滚动到底部"""
        scroll_count = 0
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        stable_count = 0
        
        while scroll_count < max_scrolls:
            # 滚动到底部
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            scroll_count += 1
            
            # 等待加载
            time.sleep(pause_ms / 1000.0)
            
            # 检查新高度
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                stable_count += 1
                if stable_count >= stable_threshold:
                    break
            else:
                stable_count = 0
                last_height = new_height
        
        return scroll_count
    
    def scroll_to_top(self) -> None:
        """滚动到顶部"""
        self.driver.execute_script("window.scrollTo(0, 0);")
    
    def scroll_to_element(self, selector: str) -> None:
        """滚动到元素"""
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
    
    def scroll_to_position(self, x: int, y: int) -> None:
        """滚动到指定位置"""
        self.driver.execute_script(f"window.scrollTo({x}, {y});")
    
    def get_scroll_progress(self) -> float:
        """获取滚动进度"""
        return self.driver.execute_script("""
            var h = document.documentElement, 
                b = document.body,
                st = 'scrollTop',
                sh = 'scrollHeight';
            return (h[st]||b[st]) / ((h[sh]||b[sh]) - h.clientHeight) * 100;
        """)
    
    def get_scroll_position(self) -> dict:
        """获取滚动位置"""
        return {
            "scrollX": self.driver.execute_script("return window.pageXOffset"),
            "scrollY": self.driver.execute_script("return window.pageYOffset"),
        }


class FormInteractorEnhanced:
    """表单交互器（增强版）"""
    
    def __init__(self, driver):
        self.driver = driver
    
    def click(self, selector: str, timeout: int = 10) -> bool:
        """点击"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            element.click()
            return True
        except Exception:
            return False
    
    def double_click(self, selector: str) -> bool:
        """双击"""
        from selenium.webdriver.common.action_chains import ActionChains
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            ActionChains(self.driver).double_click(element).perform()
            return True
        except Exception:
            return False
    
    def right_click(self, selector: str) -> bool:
        """右键点击"""
        from selenium.webdriver.common.action_chains import ActionChains
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            ActionChains(self.driver).context_click(element).perform()
            return True
        except Exception:
            return False
    
    def input_text(self, selector: str, text: str, clear: bool = True) -> bool:
        """输入文本"""
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            if clear:
                element.clear()
            element.send_keys(text)
            return True
        except Exception:
            return False
    
    def submit_form(self, selector: str) -> bool:
        """提交表单"""
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            element.submit()
            return True
        except Exception:
            return False
    
    def select_option(self, selector: str, value: str = None, text: str = None, index: int = None) -> bool:
        """选择选项"""
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            select = Select(element)
            
            if value:
                select.select_by_value(value)
            elif text:
                select.select_by_visible_text(text)
            elif index is not None:
                select.select_by_index(index)
            return True
        except Exception:
            return False
    
    def get_selected_option(self, selector: str) -> Optional[str]:
        """获取选中选项"""
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            select = Select(element)
            return select.first_selected_option.text
        except Exception:
            return None
    
    def upload_file(self, selector: str, file_path: str) -> bool:
        """上传文件"""
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            element.send_keys(file_path)
            return True
        except Exception:
            return False
    
    def hover(self, selector: str) -> bool:
        """悬停"""
        from selenium.webdriver.common.action_chains import ActionChains
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            ActionChains(self.driver).move_to_element(element).perform()
            return True
        except Exception:
            return False
    
    def drag_and_drop(self, from_selector: str, to_selector: str) -> bool:
        """拖拽"""
        from selenium.webdriver.common.action_chains import ActionChains
        try:
            from_element = self.driver.find_element(By.CSS_SELECTOR, from_selector)
            to_element = self.driver.find_element(By.CSS_SELECTOR, to_selector)
            ActionChains(self.driver).drag_and_drop(from_element, to_element).perform()
            return True
        except Exception:
            return False
    
    def drag_and_drop_by_offset(self, selector: str, x_offset: int, y_offset: int) -> bool:
        """拖拽到偏移位置"""
        from selenium.webdriver.common.action_chains import ActionChains
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            ActionChains(self.driver).drag_and_drop_by_offset(element, x_offset, y_offset).perform()
            return True
        except Exception:
            return False
