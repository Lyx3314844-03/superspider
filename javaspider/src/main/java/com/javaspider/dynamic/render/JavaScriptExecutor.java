package com.javaspider.dynamic.render;

import com.javaspider.browser.BrowserManager;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.WebDriver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * JavaScript 执行器
 * 支持执行自定义 JS、注入脚本、绕过检测等
 * 
 * 特性:
 * - 执行自定义 JavaScript
 * - 注入初始化脚本
 * - 绕过自动化检测
 * - 执行异步脚本
 */
public class JavaScriptExecutor {
    private static final Logger logger = LoggerFactory.getLogger(JavaScriptExecutor.class);
    
    private final BrowserManager browser;
    private final JavascriptExecutor jsExecutor;
    private final List<String> injectedScripts = new ArrayList<>();
    
    /**
     * 构造函数
     */
    public JavaScriptExecutor(BrowserManager browser) {
        this.browser = browser;
        this.jsExecutor = (JavascriptExecutor) browser.getDriver();
    }
    
    /**
     * 执行 JavaScript
     */
    public Object execute(String script) {
        logger.debug("Executing JavaScript: {}", truncate(script, 100));
        try {
            return jsExecutor.executeScript(script);
        } catch (Exception e) {
            logger.error("Failed to execute JavaScript: {}", e.getMessage());
            return null;
        }
    }
    
    /**
     * 执行 JavaScript（带参数）
     */
    public Object execute(String script, Object... args) {
        logger.debug("Executing JavaScript with {} args", args.length);
        try {
            return jsExecutor.executeScript(script, args);
        } catch (Exception e) {
            logger.error("Failed to execute JavaScript: {}", e.getMessage());
            return null;
        }
    }
    
    /**
     * 异步执行 JavaScript
     */
    public Object executeAsync(String script) {
        logger.debug("Executing async JavaScript: {}", truncate(script, 100));
        try {
            return jsExecutor.executeAsyncScript(script);
        } catch (Exception e) {
            logger.error("Failed to execute async JavaScript: {}", e.getMessage());
            return null;
        }
    }
    
    /**
     * 注入初始化脚本（每页加载时执行）
     */
    public void injectInitScript(String script) {
        injectedScripts.add(script);
        logger.debug("Injected init script");
        
        // 立即执行
        execute(script);
    }
    
    /**
     * 绕过自动化检测
     */
    public void bypassAutomationDetection() {
        logger.debug("Bypassing automation detection");
        
        String script = 
            "() => {" +
            // 隐藏 webdriver 属性
            "Object.defineProperty(navigator, 'webdriver', {" +
            "  get: () => undefined" +
            "});" +
            
            // 隐藏 __webdriver 属性
            "delete navigator.__webdriver;" +
            
            // 修改 plugins
            "Object.defineProperty(navigator, 'plugins', {" +
            "  get: () => [1, 2, 3, 4, 5]" +
            "});" +
            
            // 修改 languages
            "Object.defineProperty(navigator, 'languages', {" +
            "  get: () => ['zh-CN', 'zh', 'en']" +
            "});" +
            
            // 隐藏 chrome 属性
            "delete window.chrome;" +
            
            // 修改 permissions
            "const originalQuery = window.navigator.permissions.query;" +
            "window.navigator.permissions.query = (parameters) => (" +
            "  parameters.name === 'notifications' ?" +
            "    Promise.resolve({ state: Notification.permission }) :" +
            "    originalQuery(parameters)" +
            ");" +
            "}";
        
        execute(script);
        injectedScripts.add(script);
    }
    
    /**
     * 获取页面标题
     */
    public String getTitle() {
        return (String) execute("return document.title");
    }
    
    /**
     * 获取页面 URL
     */
    public String getUrl() {
        return (String) execute("return window.location.href");
    }
    
    /**
     * 获取页面 HTML
     */
    public String getHtml() {
        return (String) execute("return document.documentElement.outerHTML");
    }
    
    /**
     * 获取页面文本
     */
    public String getText() {
        return (String) execute("return document.body.innerText");
    }
    
    /**
     * 滚动到页面底部
     */
    public void scrollToBottom() {
        logger.debug("Scrolling to bottom");
        execute("window.scrollTo(0, document.body.scrollHeight)");
    }
    
    /**
     * 滚动到页面顶部
     */
    public void scrollToTop() {
        logger.debug("Scrolling to top");
        execute("window.scrollTo(0, 0)");
    }
    
    /**
     * 滚动到元素
     */
    public void scrollToElement(String selector) {
        logger.debug("Scrolling to element: {}", selector);
        String script = 
            "document.querySelector('" + selector + "').scrollIntoView({behavior: 'smooth'})";
        execute(script);
    }
    
    /**
     * 点击元素
     */
    public void clickElement(String selector) {
        logger.debug("Clicking element: {}", selector);
        String script = 
            "document.querySelector('" + selector + "').click()";
        execute(script);
    }
    
    /**
     * 输入文本
     */
    public void inputText(String selector, String text) {
        logger.debug("Inputting text into: {}", selector);
        String script = 
            "var el = document.querySelector('" + selector + "');" +
            "el.value = '" + text + "';" +
            "el.dispatchEvent(new Event('input', {bubbles: true}));" +
            "el.dispatchEvent(new Event('change', {bubbles: true}));";
        execute(script);
    }
    
    /**
     * 清除输入框
     */
    public void clearInput(String selector) {
        logger.debug("Clearing input: {}", selector);
        String script = 
            "document.querySelector('" + selector + "').value = ''";
        execute(script);
    }
    
    /**
     * 选择下拉选项
     */
    public void selectOption(String selector, String value) {
        logger.debug("Selecting option: {} in {}", value, selector);
        String script = 
            "var select = document.querySelector('" + selector + "');" +
            "for (var i = 0; i < select.options.length; i++) {" +
            "  if (select.options[i].value === '" + value + "') {" +
            "    select.selectedIndex = i;" +
            "    select.dispatchEvent(new Event('change'));" +
            "    break;" +
            "  }" +
            "}";
        execute(script);
    }
    
    /**
     * 获取元素属性
     */
    public String getElementAttribute(String selector, String attribute) {
        String script = 
            "return document.querySelector('" + selector + "').getAttribute('" + attribute + "')";
        return (String) execute(script);
    }
    
    /**
     * 获取元素文本
     */
    public String getElementText(String selector) {
        String script = 
            "return document.querySelector('" + selector + "').textContent";
        return (String) execute(script);
    }
    
    /**
     * 获取元素数量
     */
    public int getElementCount(String selector) {
        Object result = execute("return document.querySelectorAll('" + selector + "').length");
        return result != null ? ((Number) result).intValue() : 0;
    }
    
    /**
     * 检查元素是否存在
     */
    public boolean elementExists(String selector) {
        Object result = execute(
            "return document.querySelector('" + selector + "') !== null");
        return result != null && (Boolean) result;
    }
    
    /**
     * 检查元素是否可见
     */
    public boolean elementIsVisible(String selector) {
        Object result = execute(
            "var el = document.querySelector('" + selector + "');" +
            "return el && el.offsetParent !== null");
        return result != null && (Boolean) result;
    }
    
    /**
     * 获取 Cookie
     */
    public Map<String, String> getCookies() {
        Object result = execute("return document.cookie");
        Map<String, String> cookies = new HashMap<>();
        
        if (result != null) {
            String cookieStr = (String) result;
            for (String pair : cookieStr.split(";")) {
                String[] parts = pair.trim().split("=");
                if (parts.length == 2) {
                    cookies.put(parts[0], parts[1]);
                }
            }
        }
        
        return cookies;
    }
    
    /**
     * 设置 Cookie
     */
    public void setCookie(String name, String value) {
        execute("document.cookie = '" + name + "=" + value + "; path=/'");
    }
    
    /**
     * 删除 Cookie
     */
    public void deleteCookie(String name) {
        execute("document.cookie = '" + name + "=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/'");
    }
    
    /**
     * 清除所有 Cookie
     */
    public void clearCookies() {
        execute(
            "document.cookie.split(';').forEach(function(c) {" +
            "  document.cookie = c.replace(/^ +/, '').replace(/=.*/, '=;expires=' + " +
            "  new Date().toUTCString() + ';path=/');" +
            "})");
    }
    
    /**
     * 获取 localStorage
     */
    public Map<String, String> getLocalStorage() {
        Object result = execute(
            "var ls = window.localStorage; var obj = {};" +
            "for (var i = 0; i < ls.length; i++) {" +
            "  obj[ls.key(i)] = ls.getItem(ls.key(i));" +
            "}" +
            "return obj");

        return toStringMap(result);
    }
    
    /**
     * 设置 localStorage
     */
    public void setLocalStorage(String key, String value) {
        execute("window.localStorage.setItem('" + key + "', '" + value + "')");
    }
    
    /**
     * 获取 sessionStorage
     */
    public Map<String, String> getSessionStorage() {
        Object result = execute(
            "var ss = window.sessionStorage; var obj = {};" +
            "for (var i = 0; i < ss.length; i++) {" +
            "  obj[ss.key(i)] = ss.getItem(ss.key(i));" +
            "}" +
            "return obj");

        return toStringMap(result);
    }
    
    /**
     * 截图（Base64）
     */
    public String screenshotBase64() {
        Object result = execute(
            "return canvas.toDataURL('image/png').substring(22)");
        return result != null ? (String) result : null;
    }
    
    /**
     * 获取网络请求信息
     */
    public List<Map<String, Object>> getNetworkRequests() {
        Object result = execute(
            "return performance.getEntriesByType('resource').map(function(r) {" +
            "  return {" +
            "    name: r.name," +
            "    type: r.initiatorType," +
            "    duration: r.duration," +
            "    startTime: r.startTime" +
            "  };" +
            "})");

        return toListOfObjectMaps(result);
    }
    
    /**
     * 获取性能指标
     */
    public Map<String, Object> getPerformanceMetrics() {
        Object result = execute(
            "return {" +
            "  loadTime: performance.timing.loadEventEnd - performance.timing.navigationStart," +
            "  domReady: performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart," +
            "  firstPaint: performance.getEntriesByType('paint').find(p => p.name === 'first-contentful-paint')?.startTime" +
            "}");

        return toObjectMap(result);
    }

    private Map<String, String> toStringMap(Object value) {
        Map<String, String> converted = new HashMap<>();
        if (value instanceof Map<?, ?> rawMap) {
            for (Map.Entry<?, ?> entry : rawMap.entrySet()) {
                converted.put(String.valueOf(entry.getKey()), entry.getValue() == null ? null : String.valueOf(entry.getValue()));
            }
        }
        return converted;
    }

    private Map<String, Object> toObjectMap(Object value) {
        Map<String, Object> converted = new HashMap<>();
        if (value instanceof Map<?, ?> rawMap) {
            for (Map.Entry<?, ?> entry : rawMap.entrySet()) {
                converted.put(String.valueOf(entry.getKey()), entry.getValue());
            }
        }
        return converted;
    }

    private List<Map<String, Object>> toListOfObjectMaps(Object value) {
        List<Map<String, Object>> converted = new ArrayList<>();
        if (value instanceof List<?> rawList) {
            for (Object item : rawList) {
                converted.add(toObjectMap(item));
            }
        }
        return converted;
    }
    
    /**
     * 模拟鼠标移动
     */
    public void simulateMouseMove(String selector) {
        String script = 
            "var el = document.querySelector('" + selector + "');" +
            "var event = new MouseEvent('mousemove', {bubbles: true, cancelable: true});" +
            "el.dispatchEvent(event);";
        execute(script);
    }
    
    /**
     * 等待（JS 版本）
     */
    public void sleep(long ms) {
        try {
            execute(
                "var start = Date.now();" +
                "while (Date.now() - start < " + ms + ") {}");
        } catch (Exception e) {
            // Fallback: Java sleep
            try {
                Thread.sleep(ms);
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
            }
        }
    }
    
    /**
     * 获取注入的脚本列表
     */
    public List<String> getInjectedScripts() {
        return new ArrayList<>(injectedScripts);
    }
    
    /**
     * 清除注入的脚本
     */
    public void clearInjectedScripts() {
        injectedScripts.clear();
    }
    
    /**
     * 截断字符串
     */
    private String truncate(String str, int maxLen) {
        if (str.length() <= maxLen) {
            return str;
        }
        return str.substring(0, maxLen) + "...";
    }
}
