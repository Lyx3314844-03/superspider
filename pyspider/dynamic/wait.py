"""
动态等待模块
支持各种等待条件
"""

import time
from typing import Callable
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class DynamicWait:
    """动态等待器"""

    def __init__(self, driver, timeout: int = 30, poll_frequency: float = 0.5):
        self.driver = driver
        self.timeout = timeout
        self.poll_frequency = poll_frequency
        self.wait = WebDriverWait(driver, timeout, poll_frequency)

    def wait_for_element_visible(self, selector: str, by=By.CSS_SELECTOR) -> bool:
        """等待元素可见"""
        try:
            self.wait.until(EC.visibility_of_element_located((by, selector)))
            return True
        except Exception:
            return False

    def wait_for_element_clickable(self, selector: str, by=By.CSS_SELECTOR) -> bool:
        """等待元素可点击"""
        try:
            self.wait.until(EC.element_to_be_clickable((by, selector)))
            return True
        except Exception:
            return False

    def wait_for_element_present(self, selector: str, by=By.CSS_SELECTOR) -> bool:
        """等待元素存在"""
        try:
            self.wait.until(EC.presence_of_element_located((by, selector)))
            return True
        except Exception:
            return False

    def wait_for_text_present(self, text: str) -> bool:
        """等待文本出现"""
        try:
            self.wait.until(
                EC.text_to_be_present_in_element((By.TAG_NAME, "body"), text)
            )
            return True
        except Exception:
            return False

    def wait_for_url_contains(self, text: str) -> bool:
        """等待 URL 包含"""
        try:
            self.wait.until(EC.url_contains(text))
            return True
        except Exception:
            return False

    def wait_for_ajax(self) -> bool:
        """等待 AJAX 完成"""
        try:
            self.wait.until(
                lambda driver: (
                    driver.execute_script("return jQuery.active == 0")
                    if driver.execute_script("return typeof jQuery !== 'undefined'")
                    else True
                )
            )
            return True
        except Exception:
            return True

    def wait_for_condition(self, condition: Callable) -> bool:
        """等待自定义条件"""
        try:
            self.wait.until(condition)
            return True
        except Exception:
            return False

    def sleep(self, ms: int):
        """休眠"""
        time.sleep(ms / 1000.0)


class ScrollLoader:
    """滚动加载器"""

    def __init__(self, driver):
        self.driver = driver

    def scroll_to_bottom(self, pause_ms: int = 1000, max_scrolls: int = 50) -> int:
        """滚动到底部"""
        scroll_count = 0
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        stable_count = 0

        while scroll_count < max_scrolls:
            # 滚动到底部
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            scroll_count += 1

            # 等待加载
            time.sleep(pause_ms / 1000.0)

            # 检查新高度
            new_height = self.driver.execute_script("return document.body.scrollHeight")

            if new_height == last_height:
                stable_count += 1
                if stable_count >= 2:
                    break
            else:
                stable_count = 0
                last_height = new_height

        return scroll_count

    def scroll_to_element(self, selector: str):
        """滚动到元素"""
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)

    def get_scroll_progress(self) -> float:
        """获取滚动进度"""
        return self.driver.execute_script("""
            var h = document.documentElement, 
                b = document.body,
                st = 'scrollTop',
                sh = 'scrollHeight';
            return (h[st]||b[st]) / ((h[sh]||b[sh]) - h.clientHeight) * 100;
        """)


class FormInteractor:
    """表单交互器"""

    def __init__(self, driver):
        self.driver = driver

    def click(self, selector: str):
        """点击"""
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        element.click()

    def input_text(self, selector: str, text: str):
        """输入文本"""
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        element.clear()
        element.send_keys(text)

    def select_option(self, selector: str, value: str):
        """选择选项"""
        from selenium.webdriver.support.ui import Select

        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        select = Select(element)
        select.select_by_value(value)

    def upload_file(self, selector: str, file_path: str):
        """上传文件"""
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        element.send_keys(file_path)

    def hover(self, selector: str):
        """悬停"""
        from selenium.webdriver.common.action_chains import ActionChains

        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        ActionChains(self.driver).move_to_element(element).perform()
