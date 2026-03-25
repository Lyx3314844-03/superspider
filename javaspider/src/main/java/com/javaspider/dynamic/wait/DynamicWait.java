package com.javaspider.dynamic.wait;

import com.javaspider.browser.BrowserManager;
import org.openqa.selenium.*;
import org.openqa.selenium.support.ui.ExpectedCondition;
import org.openqa.selenium.support.ui.FluentWait;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;

/**
 * 动态等待条件
 * 类似 Selenium WebDriverWait + ExpectedConditions
 *
 * 特性:
 * - 元素可见性等待
 * - 元素可点击等待
 * - 文本存在等待
 * - 自定义条件等待
 * - 链式等待
 */
public class DynamicWait {
    private static final Logger logger = LoggerFactory.getLogger(DynamicWait.class);

    // 默认配置
    private static final long DEFAULT_TIMEOUT = 30000; // 30 秒
    private static final long DEFAULT_POLLING = 500; // 0.5 秒

    private final BrowserManager browser;
    private final FluentWait<WebDriver> wait;
    private final List<String> waitLog = new ArrayList<>();

    // ExpectedConditions 兼容类
    public static class ExpectedConditions {
        public static ExpectedCondition<WebElement> visibilityOfElementLocated(By locator) {
            return driver -> driver.findElement(locator);
        }

        public static ExpectedCondition<WebElement> elementToBeClickable(By locator) {
            return driver -> {
                WebElement element = driver.findElement(locator);
                return element.isEnabled() ? element : null;
            };
        }

        public static ExpectedCondition<WebElement> presenceOfElementLocated(By locator) {
            return driver -> driver.findElement(locator);
        }

        public static ExpectedCondition<Boolean> textToBePresentInElementLocated(By locator, String text) {
            return driver -> {
                WebElement element = driver.findElement(locator);
                return element.getText().contains(text);
            };
        }

        public static ExpectedCondition<Boolean> invisibilityOfElementLocated(By locator) {
            return driver -> {
                try {
                    WebElement element = driver.findElement(locator);
                    return !element.isDisplayed();
                } catch (org.openqa.selenium.NoSuchElementException e) {
                    return true;
                }
            };
        }

        public static ExpectedCondition<Boolean> urlContains(String text) {
            return driver -> driver.getCurrentUrl().contains(text);
        }

        public static ExpectedCondition<Boolean> urlMatches(String regex) {
            return driver -> driver.getCurrentUrl().matches(regex);
        }

        public static ExpectedCondition<Void> frameToBeAvailableAndSwitchToIt(By locator) {
            return driver -> {
                WebElement frame = driver.findElement(locator);
                driver.switchTo().frame(frame);
                return null;
            };
        }

        public static ExpectedCondition<Boolean> alertIsPresent() {
            return driver -> {
                try {
                    driver.switchTo().alert();
                    return true;
                } catch (org.openqa.selenium.NoAlertPresentException e) {
                    return false;
                }
            };
        }
    }
    
    /**
     * 构造函数
     */
    public DynamicWait(BrowserManager browser) {
        this(browser, DEFAULT_TIMEOUT, DEFAULT_POLLING);
    }
    
    /**
     * 构造函数
     */
    public DynamicWait(BrowserManager browser, long timeoutMs, long pollingMs) {
        this.browser = browser;
        this.wait = new FluentWait<>(browser.getDriver())
                .withTimeout(Duration.ofMillis(timeoutMs))
                .pollingEvery(Duration.ofMillis(pollingMs))
                .ignoring(NoSuchElementException.class)
                .ignoring(StaleElementReferenceException.class);
    }
    
    /**
     * 等待元素可见
     */
    public boolean waitForElementVisible(String selector, long timeoutMs) {
        logger.debug("Waiting for element visible: {}", selector);
        waitLog.add("waitForElementVisible: " + selector);
        
        try {
            wait.until(ExpectedConditions.visibilityOfElementLocated(By.cssSelector(selector)));
            logger.debug("Element visible: {}", selector);
            return true;
        } catch (Exception e) {
            logger.warn("Timeout waiting for element visible: {}", selector);
            return false;
        }
    }
    
    /**
     * 等待元素可见
     */
    public boolean waitForElementVisible(By by, long timeoutMs) {
        logger.debug("Waiting for element visible: {}", by);
        waitLog.add("waitForElementVisible: " + by);
        
        try {
            wait.until(ExpectedConditions.visibilityOfElementLocated(by));
            logger.debug("Element visible: {}", by);
            return true;
        } catch (Exception e) {
            logger.warn("Timeout waiting for element visible: {}", by);
            return false;
        }
    }
    
    /**
     * 等待元素可点击
     */
    public boolean waitForElementClickable(String selector, long timeoutMs) {
        logger.debug("Waiting for element clickable: {}", selector);
        waitLog.add("waitForElementClickable: " + selector);
        
        try {
            wait.until(ExpectedConditions.elementToBeClickable(By.cssSelector(selector)));
            logger.debug("Element clickable: {}", selector);
            return true;
        } catch (Exception e) {
            logger.warn("Timeout waiting for element clickable: {}", selector);
            return false;
        }
    }
    
    /**
     * 等待元素存在
     */
    public boolean waitForElementPresent(String selector, long timeoutMs) {
        logger.debug("Waiting for element present: {}", selector);
        waitLog.add("waitForElementPresent: " + selector);
        
        try {
            wait.until(ExpectedConditions.presenceOfElementLocated(By.cssSelector(selector)));
            logger.debug("Element present: {}", selector);
            return true;
        } catch (Exception e) {
            logger.warn("Timeout waiting for element present: {}", selector);
            return false;
        }
    }
    
    /**
     * 等待文本存在
     */
    public boolean waitForTextPresent(String text, long timeoutMs) {
        logger.debug("Waiting for text present: {}", text);
        waitLog.add("waitForTextPresent: " + text);
        
        try {
            wait.until(ExpectedConditions.textToBePresentInElementLocated(
                By.tagName("body"), text));
            logger.debug("Text present: {}", text);
            return true;
        } catch (Exception e) {
            logger.warn("Timeout waiting for text present: {}", text);
            return false;
        }
    }
    
    /**
     * 等待元素消失
     */
    public boolean waitForElementInvisible(String selector, long timeoutMs) {
        logger.debug("Waiting for element invisible: {}", selector);
        waitLog.add("waitForElementInvisible: " + selector);
        
        try {
            wait.until(ExpectedConditions.invisibilityOfElementLocated(By.cssSelector(selector)));
            logger.debug("Element invisible: {}", selector);
            return true;
        } catch (Exception e) {
            logger.warn("Timeout waiting for element invisible: {}", selector);
            return false;
        }
    }
    
    /**
     * 等待页面加载完成
     */
    public boolean waitForPageLoad(long timeoutMs) {
        logger.debug("Waiting for page load");
        waitLog.add("waitForPageLoad");
        
        try {
            wait.until(webDriver -> ((JavascriptExecutor) webDriver)
                .executeScript("return document.readyState").equals("complete"));
            logger.debug("Page loaded");
            return true;
        } catch (Exception e) {
            logger.warn("Timeout waiting for page load");
            return false;
        }
    }
    
    /**
     * 等待 AJAX 加载完成
     */
    public boolean waitForAjaxComplete(long timeoutMs) {
        logger.debug("Waiting for AJAX complete");
        waitLog.add("waitForAjaxComplete");
        
        try {
            wait.until(webDriver -> ((JavascriptExecutor) webDriver)
                .executeScript("return jQuery.active == 0").equals(true));
            logger.debug("AJAX complete");
            return true;
        } catch (Exception e) {
            logger.debug("jQuery not available, using fallback");
            // Fallback: 等待网络空闲
            return waitForNetworkIdle(timeoutMs);
        }
    }
    
    /**
     * 等待网络空闲
     */
    public boolean waitForNetworkIdle(long timeoutMs) {
        logger.debug("Waiting for network idle");
        waitLog.add("waitForNetworkIdle");
        
        try {
            wait.until(webDriver -> {
                JavascriptExecutor js = (JavascriptExecutor) webDriver;
                String performanceApi = 
                    "var entries = performance.getEntriesByType('resource');" +
                    "var loading = entries.filter(function(e) { return e.responseEnd === 0; }).length;" +
                    "return loading === 0;";
                return (Boolean) js.executeScript(performanceApi);
            });
            logger.debug("Network idle");
            return true;
        } catch (Exception e) {
            logger.warn("Timeout waiting for network idle");
            return false;
        }
    }
    
    /**
     * 等待自定义条件
     */
    public <T> T waitForCondition(Function<WebDriver, T> condition, long timeoutMs) {
        logger.debug("Waiting for custom condition");
        waitLog.add("waitForCondition");
        
        try {
            FluentWait<WebDriver> customWait = new FluentWait<>(browser.getDriver())
                    .withTimeout(Duration.ofMillis(timeoutMs))
                    .pollingEvery(Duration.ofMillis(DEFAULT_POLLING))
                    .ignoring(Exception.class);
            
            T result = customWait.until(condition);
            logger.debug("Custom condition met");
            return result;
        } catch (Exception e) {
            logger.warn("Timeout waiting for custom condition");
            return null;
        }
    }
    
    /**
     * 等待元素数量
     */
    public boolean waitForElementCount(String selector, int count, long timeoutMs) {
        logger.debug("Waiting for element count: {} = {}", selector, count);
        waitLog.add("waitForElementCount: " + selector + " = " + count);
        
        try {
            wait.until(driver -> 
                driver.findElements(By.cssSelector(selector)).size() == count);
            logger.debug("Element count met: {}", count);
            return true;
        } catch (Exception e) {
            logger.warn("Timeout waiting for element count: {}", selector);
            return false;
        }
    }
    
    /**
     * 等待元素数量大于
     */
    public boolean waitForElementCountGreaterThan(String selector, int count, long timeoutMs) {
        logger.debug("Waiting for element count: {} > {}", selector, count);
        waitLog.add("waitForElementCountGreaterThan: " + selector + " > " + count);
        
        try {
            wait.until(driver -> 
                driver.findElements(By.cssSelector(selector)).size() > count);
            logger.debug("Element count > {}", count);
            return true;
        } catch (Exception e) {
            logger.warn("Timeout waiting for element count > {}: {}", count, selector);
            return false;
        }
    }
    
    /**
     * 等待 URL 包含
     */
    public boolean waitForUrlContains(String text, long timeoutMs) {
        logger.debug("Waiting for URL contains: {}", text);
        waitLog.add("waitForUrlContains: " + text);
        
        try {
            wait.until(ExpectedConditions.urlContains(text));
            logger.debug("URL contains: {}", text);
            return true;
        } catch (Exception e) {
            logger.warn("Timeout waiting for URL contains: {}", text);
            return false;
        }
    }
    
    /**
     * 等待 URL 匹配
     */
    public boolean waitForUrlMatches(String regex, long timeoutMs) {
        logger.debug("Waiting for URL matches: {}", regex);
        waitLog.add("waitForUrlMatches: " + regex);
        
        try {
            wait.until(ExpectedConditions.urlMatches(regex));
            logger.debug("URL matches: {}", regex);
            return true;
        } catch (Exception e) {
            logger.warn("Timeout waiting for URL matches: {}", regex);
            return false;
        }
    }
    
    /**
     * 等待帧可用
     */
    public boolean waitForFrame(String selector, long timeoutMs) {
        logger.debug("Waiting for frame: {}", selector);
        waitLog.add("waitForFrame: " + selector);
        
        try {
            wait.until(ExpectedConditions.frameToBeAvailableAndSwitchToIt(By.cssSelector(selector)));
            logger.debug("Frame available: {}", selector);
            return true;
        } catch (Exception e) {
            logger.warn("Timeout waiting for frame: {}", selector);
            return false;
        }
    }
    
    /**
     * 等待警告框出现
     */
    public boolean waitForAlert(long timeoutMs) {
        logger.debug("Waiting for alert");
        waitLog.add("waitForAlert");
        
        try {
            wait.until(ExpectedConditions.alertIsPresent());
            logger.debug("Alert present");
            return true;
        } catch (Exception e) {
            logger.warn("Timeout waiting for alert");
            return false;
        }
    }
    
    /**
     * 链式等待构建器
     */
    public WaitChain chain() {
        return new WaitChain(this);
    }
    
    /**
     * 获取等待日志
     */
    public List<String> getWaitLog() {
        return new ArrayList<>(waitLog);
    }
    
    /**
     * 清空等待日志
     */
    public void clearWaitLog() {
        waitLog.clear();
    }
    
    /**
     * 链式等待
     */
    public static class WaitChain {
        private final DynamicWait dynamicWait;
        private boolean allSuccess = true;
        
        public WaitChain(DynamicWait dynamicWait) {
            this.dynamicWait = dynamicWait;
        }
        
        public WaitChain elementVisible(String selector, long timeoutMs) {
            if (!dynamicWait.waitForElementVisible(selector, timeoutMs)) {
                allSuccess = false;
            }
            return this;
        }
        
        public WaitChain elementClickable(String selector, long timeoutMs) {
            if (!dynamicWait.waitForElementClickable(selector, timeoutMs)) {
                allSuccess = false;
            }
            return this;
        }
        
        public WaitChain elementPresent(String selector, long timeoutMs) {
            if (!dynamicWait.waitForElementPresent(selector, timeoutMs)) {
                allSuccess = false;
            }
            return this;
        }
        
        public WaitChain textPresent(String text, long timeoutMs) {
            if (!dynamicWait.waitForTextPresent(text, timeoutMs)) {
                allSuccess = false;
            }
            return this;
        }
        
        public WaitChain pageLoad(long timeoutMs) {
            if (!dynamicWait.waitForPageLoad(timeoutMs)) {
                allSuccess = false;
            }
            return this;
        }
        
        public WaitChain ajaxComplete(long timeoutMs) {
            if (!dynamicWait.waitForAjaxComplete(timeoutMs)) {
                allSuccess = false;
            }
            return this;
        }
        
        public boolean isSuccess() {
            return allSuccess;
        }
        
        public DynamicWait end() {
            return dynamicWait;
        }
    }
}
