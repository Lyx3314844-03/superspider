package com.javaspider.browser;

import org.openqa.selenium.*;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.openqa.selenium.firefox.FirefoxDriver;
import org.openqa.selenium.firefox.FirefoxOptions;
import org.openqa.selenium.interactions.Actions;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;
import java.util.logging.Level;
import java.util.logging.LogManager;

/**
 * 浏览器自动化管理器
 * 支持 Selenium WebDriver，用于爬取 JavaScript 渲染的页面
 */
public class BrowserManager {
    private static final Logger logger = LoggerFactory.getLogger(BrowserManager.class);
    static {
        suppressSeleniumWarnings();
    }

    private WebDriver driver;
    private final BrowserType browserType;
    private final boolean headless;
    private final boolean incognito;
    private final String customUserAgent;
    private final String proxyServer;
    private WebDriverWait wait;
    private boolean isInitialized = false;

    public enum BrowserType {
        CHROME,
        FIREFOX,
        EDGE,
        SAFARI
    }

    public BrowserManager() {
        this(BrowserType.CHROME, true, false, "", "");
    }

    public BrowserManager(BrowserType browserType, boolean headless, boolean incognito) {
        this(browserType, headless, incognito, "", "");
    }

    public BrowserManager(BrowserType browserType, boolean headless, boolean incognito, String customUserAgent, String proxyServer) {
        this.browserType = browserType;
        this.headless = headless;
        this.incognito = incognito;
        this.customUserAgent = customUserAgent == null ? "" : customUserAgent;
        this.proxyServer = proxyServer == null ? "" : proxyServer;
    }

    private static void suppressSeleniumWarnings() {
        for (String name : new String[]{
            "org.openqa.selenium",
            "org.openqa.selenium.devtools.CdpVersionFinder",
            "org.openqa.selenium.chromium.ChromiumDriver",
            "org.openqa.selenium.manager.SeleniumManager",
        }) {
            java.util.logging.Logger.getLogger(name).setLevel(Level.SEVERE);
        }
        LogManager.getLogManager().getLogger("").setLevel(Level.INFO);
    }

    /**
     * 初始化浏览器
     */
    public void init() {
        if (isInitialized) {
            return;
        }

        try {
            switch (browserType) {
                case CHROME:
                    driver = createChromeDriver();
                    break;
                case FIREFOX:
                    driver = createFirefoxDriver();
                    break;
                default:
                    driver = createChromeDriver();
            }

            wait = new WebDriverWait(driver, Duration.ofSeconds(30));
            isInitialized = true;
            logger.info("Browser initialized: {}", browserType);
        } catch (Exception e) {
            logger.error("Failed to initialize browser", e);
            throw new RuntimeException("Failed to initialize browser", e);
        }
    }

    /**
     * 创建 Chrome Driver
     */
    private WebDriver createChromeDriver() {
        ChromeOptions options = new ChromeOptions();
        
        if (headless) {
            options.addArguments("--headless=new");
        }
        
        if (incognito) {
            options.addArguments("--incognito");
        }
        
        options.addArguments("--disable-gpu");
        options.addArguments("--no-sandbox");
        options.addArguments("--disable-dev-shm-usage");
        options.addArguments("--window-size=1920,1080");
        if (!proxyServer.isBlank()) {
            options.addArguments("--proxy-server=" + proxyServer);
        }
        
        // 禁用自动化特征检测
        options.addArguments("--disable-blink-features=AutomationControlled");
        options.setExperimentalOption("excludeSwitches", new String[]{"enable-automation"});
        options.setExperimentalOption("useAutomationExtension", false);
        
        // 设置 User-Agent
        Map<String, Object> prefs = new HashMap<>();
        prefs.put("profile.default_content_setting_values.notifications", 2);
        options.setExperimentalOption("prefs", prefs);
        
        String userAgent = customUserAgent.isBlank()
            ? "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            : customUserAgent;
        options.addArguments("--user-agent=" + userAgent);

        return new ChromeDriver(options);
    }

    /**
     * 创建 Firefox Driver
     */
    private WebDriver createFirefoxDriver() {
        FirefoxOptions options = new FirefoxOptions();
        
        if (headless) {
            options.addArguments("--headless");
        }
        
        if (incognito) {
            options.addArguments("-private");
        }
        
        options.addArguments("--width=1920");
        options.addArguments("--height=1080");

        return new FirefoxDriver(options);
    }

    /**
     * 导航到 URL
     */
    public void navigate(String url) {
        if (!isInitialized) {
            init();
        }
        driver.get(url);
        logger.debug("Navigated to: {}", url);
    }

    /**
     * 等待元素出现
     */
    public WebElement waitForElement(String selector, By byType) {
        return wait.until(ExpectedConditions.presenceOfElementLocated(byType));
    }

    /**
     * 等待元素可见
     */
    public WebElement waitForElementVisible(String selector, By byType) {
        return wait.until(ExpectedConditions.visibilityOfElementLocated(byType));
    }

    /**
     * 等待元素可点击
     */
    public WebElement waitForElementClickable(String selector, By byType) {
        return wait.until(ExpectedConditions.elementToBeClickable(byType));
    }

    /**
     * 点击元素
     */
    public void click(String selector, By byType) {
        WebElement element = waitForElementClickable(selector, byType);
        element.click();
        logger.debug("Clicked: {}", selector);
    }

    public void clickHumanized(String selector, By byType) {
        WebElement element = waitForElementClickable(selector, byType);
        try {
            int x = ThreadLocalRandom.current().nextInt(-3, 4);
            int y = ThreadLocalRandom.current().nextInt(-3, 4);
            new Actions(driver)
                .moveToElement(element, x, y)
                .pause(Duration.ofMillis(ThreadLocalRandom.current().nextLong(20, 60)))
                .click()
                .perform();
        } catch (Exception ignored) {
            element.click();
        }
        logger.debug("Humanized click: {}", selector);
    }

    /**
     * 输入文本
     */
    public void type(String selector, By byType, String text) {
        WebElement element = waitForElement(selector, byType);
        element.clear();
        element.sendKeys(text);
        logger.debug("Typed into: {}", selector);
    }

    public void typeHumanized(String selector, By byType, String text) {
        WebElement element = waitForElement(selector, byType);
        element.clear();
        for (char ch : text.toCharArray()) {
            element.sendKeys(String.valueOf(ch));
            sleepJitter(15, 40);
        }
        logger.debug("Humanized type into: {}", selector);
    }

    /**
     * 提交表单
     */
    public void submit(String selector, By byType) {
        WebElement element = waitForElement(selector, byType);
        element.submit();
        logger.debug("Submitted form: {}", selector);
    }

    /**
     * 获取页面 HTML
     */
    public String getPageSource() {
        return driver.getPageSource();
    }

    /**
     * 获取页面文本
     */
    public String getPageText() {
        return driver.findElement(By.tagName("body")).getText();
    }

    /**
     * 获取页面标题
     */
    public String getTitle() {
        return driver.getTitle();
    }

    /**
     * 获取当前 URL
     */
    public String getCurrentUrl() {
        return driver.getCurrentUrl();
    }

    /**
     * 执行 JavaScript
     */
    public Object executeScript(String script, Object... args) {
        JavascriptExecutor js = (JavascriptExecutor) driver;
        return js.executeScript(script, args);
    }

    /**
     * 异步执行 JavaScript
     */
    public Object executeAsyncScript(String script, Object... args) {
        JavascriptExecutor js = (JavascriptExecutor) driver;
        return js.executeAsyncScript(script, args);
    }

    /**
     * 截图
     */
    public byte[] screenshot() {
        TakesScreenshot ts = (TakesScreenshot) driver;
        return ts.getScreenshotAs(OutputType.BYTES);
    }

    /**
     * 截图保存
     */
    public void screenshotToFile(String filePath) {
        TakesScreenshot ts = (TakesScreenshot) driver;
        ts.getScreenshotAs(OutputType.FILE).renameTo(new java.io.File(filePath));
    }

    /**
     * 等待页面加载完成
     */
    public void waitForPageLoad() {
        wait.until(webDriver -> ((JavascriptExecutor) webDriver)
                .executeScript("return document.readyState").equals("complete"));
    }

    /**
     * 等待 AJAX 加载完成
     */
    public void waitForAjaxLoad() {
        wait.until(webDriver -> ((JavascriptExecutor) webDriver)
                .executeScript("return jQuery.active == 0").equals(true));
    }

    /**
     * 滚动到页面底部
     */
    public void scrollToBottom() {
        executeScript("window.scrollTo(0, document.body.scrollHeight)");
    }

    public void scrollToBottomHumanized(int maxScrolls) {
        int scrolls = Math.max(1, maxScrolls);
        for (int i = 0; i < scrolls; i++) {
            long delta = ThreadLocalRandom.current().nextLong(300, 900);
            executeScript("window.scrollBy(0, arguments[0]);", delta);
            sleepJitter(40, 90);
        }
    }

    /**
     * 滚动到页面顶部
     */
    public void scrollToTop() {
        executeScript("window.scrollTo(0, 0)");
    }

    /**
     * 滚动到元素
     */
    public void scrollToElement(String selector, By byType) {
        WebElement element = waitForElement(selector, byType);
        ((JavascriptExecutor) driver).executeScript("arguments[0].scrollIntoView(true);", element);
    }

    public void hoverHumanized(String selector, By byType) {
        WebElement element = waitForElement(selector, byType);
        try {
            int x = ThreadLocalRandom.current().nextInt(-5, 6);
            int y = ThreadLocalRandom.current().nextInt(-5, 6);
            new Actions(driver)
                .moveToElement(element, x, y)
                .pause(Duration.ofMillis(ThreadLocalRandom.current().nextLong(30, 80)))
                .perform();
        } catch (Exception ignored) {
            executeScript(
                "var el = arguments[0]; if (el) { el.dispatchEvent(new MouseEvent('mouseover', {bubbles: true})); }",
                element
            );
        }
    }

    private void sleepJitter(long minMs, long maxMs) {
        try {
            Thread.sleep(ThreadLocalRandom.current().nextLong(minMs, maxMs + 1));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    /**
     * 获取元素文本
     */
    public String getElementText(String selector, By byType) {
        WebElement element = waitForElement(selector, byType);
        return element.getText();
    }

    /**
     * 获取元素属性
     */
    public String getElementAttribute(String selector, By byType, String attribute) {
        WebElement element = waitForElement(selector, byType);
        return element.getAttribute(attribute);
    }

    /**
     * 获取元素数量
     */
    public int getElementCount(String selector, By byType) {
        return driver.findElements(byType).size();
    }

    /**
     * 切换到 iframe
     */
    public void switchToFrame(String frameSelector, By byType) {
        WebElement frame = waitForElement(frameSelector, byType);
        driver.switchTo().frame(frame);
    }

    /**
     * 切换到主窗口
     */
    public void switchToDefaultContent() {
        driver.switchTo().defaultContent();
    }

    /**
     * 切换到新标签页
     */
    public void switchToNewTab() {
        String currentWindow = driver.getWindowHandle();
        for (String window : driver.getWindowHandles()) {
            if (!window.equals(currentWindow)) {
                driver.switchTo().window(window);
                break;
            }
        }
    }

    /**
     * 关闭浏览器
     */
    public void close() {
        if (driver != null) {
            try {
                driver.quit();
                isInitialized = false;
                logger.info("Browser closed");
            } catch (Exception e) {
                logger.error("Failed to close browser", e);
            }
        }
    }

    /**
     * 获取 WebDriver
     */
    public WebDriver getDriver() {
        if (!isInitialized) {
            init();
        }
        return driver;
    }

    /**
     * 获取 WebDriverWait
     */
    public WebDriverWait getWait() {
        return wait;
    }

    /**
     * 检查是否已初始化
     */
    public boolean isInitialized() {
        return isInitialized;
    }

    /**
     * 创建 BrowserManager 实例
     */
    public static BrowserManager create() {
        return new BrowserManager();
    }

    /**
     * 创建无头 BrowserManager 实例
     */
    public static BrowserManager headless() {
        return new BrowserManager(BrowserType.CHROME, true, false);
    }

    /**
     * 创建带 UI 的 BrowserManager 实例
     */
    public static BrowserManager withUI() {
        return new BrowserManager(BrowserType.CHROME, false, false);
    }
}
