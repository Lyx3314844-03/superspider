package com.javaspider.downloader;

import com.javaspider.core.Page;
import com.javaspider.core.Request;
import com.javaspider.core.Site;
import io.github.bonigarcia.wdm.WebDriverManager;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.openqa.selenium.firefox.FirefoxDriver;
import org.openqa.selenium.firefox.FirefoxOptions;

import java.util.concurrent.TimeUnit;

/**
 * Selenium 下载器
 * 支持 JavaScript 渲染的网站
 */
public class SeleniumDownloader implements Downloader {
    
    private WebDriver driver;
    private final String browserType;
    private final boolean headless;
    private final long pageLoadTimeout;
    
    /**
     * 创建 Chrome 下载器
     */
    public SeleniumDownloader() {
        this("chrome", true);
    }
    
    /**
     * 创建 Selenium 下载器
     * @param browserType 浏览器类型 (chrome/firefox)
     * @param headless 是否无头模式
     */
    public SeleniumDownloader(String browserType, boolean headless) {
        this.browserType = browserType;
        this.headless = headless;
        this.pageLoadTimeout = 30000;
        initDriver();
    }
    
    /**
     * 创建 Selenium 下载器（自定义超时）
     */
    public SeleniumDownloader(String browserType, boolean headless, long pageLoadTimeout) {
        this.browserType = browserType;
        this.headless = headless;
        this.pageLoadTimeout = pageLoadTimeout;
        initDriver();
    }
    
    /**
     * 初始化 WebDriver
     */
    private void initDriver() {
        if ("chrome".equals(browserType)) {
            WebDriverManager.chromedriver().setup();
            ChromeOptions options = new ChromeOptions();
            if (headless) {
                options.addArguments("--headless");
            }
            options.addArguments("--no-sandbox");
            options.addArguments("--disable-dev-shm-usage");
            options.addArguments("--disable-gpu");
            options.addArguments("--window-size=1920,1080");
            driver = new ChromeDriver(options);
        } else if ("firefox".equals(browserType)) {
            WebDriverManager.firefoxdriver().setup();
            FirefoxOptions options = new FirefoxOptions();
            if (headless) {
                options.addArguments("--headless");
            }
            driver = new FirefoxDriver(options);
        } else {
            throw new IllegalArgumentException("Unsupported browser type: " + browserType);
        }
        
        driver.manage().timeouts().pageLoadTimeout(java.time.Duration.ofMillis(pageLoadTimeout));
        driver.manage().timeouts().implicitlyWait(java.time.Duration.ofSeconds(5));
    }
    
    @Override
    public Page download(Request request, Site site) {
        Page page = new Page();
        page.setRequest(request);
        page.setUrl(request.getUrl());
        
        try {
            // 设置请求头
            if (site != null && site.getUserAgent() != null) {
                ((org.openqa.selenium.remote.RemoteWebDriver) driver)
                    .executeScript("Object.defineProperty(navigator, 'userAgent', {value: '" + 
                        site.getUserAgent() + "', writable: false});");
            }
            
            // 访问页面
            driver.get(request.getUrl());
            
            // 等待页面加载（可等待特定元素）
            Thread.sleep(2000);
            
            // 获取 HTML
            String html = driver.getPageSource();
            page.setRawText(html);
            page.setStatusCode(200);
            page.setDownloadTime(System.currentTimeMillis());
            
        } catch (Exception e) {
            page.setSkip(true);
            System.err.println("Error downloading " + request.getUrl() + ": " + e.getMessage());
        }
        
        return page;
    }
    
    /**
     * 等待特定元素出现
     */
    public void waitForElement(String cssSelector) {
        try {
            org.openqa.selenium.support.ui.WebDriverWait wait =
                new org.openqa.selenium.support.ui.WebDriverWait(driver, java.time.Duration.ofSeconds(10));
            wait.until(org.openqa.selenium.support.ui.ExpectedConditions
                .presenceOfElementLocated(org.openqa.selenium.By.cssSelector(cssSelector)));
        } catch (Exception e) {
            System.err.println("Timeout waiting for element: " + cssSelector);
        }
    }
    
    /**
     * 点击元素
     */
    public void clickElement(String cssSelector) {
        try {
            org.openqa.selenium.WebElement element = driver.findElement(
                org.openqa.selenium.By.cssSelector(cssSelector));
            element.click();
        } catch (Exception e) {
            System.err.println("Error clicking element: " + cssSelector);
        }
    }
    
    /**
     * 滚动到页面底部
     */
    public void scrollToBottom() {
        ((org.openqa.selenium.JavascriptExecutor) driver)
            .executeScript("window.scrollTo(0, document.body.scrollHeight);");
    }
    
    /**
     * 关闭浏览器
     */
    public void close() {
        if (driver != null) {
            driver.quit();
        }
    }
}
