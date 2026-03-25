package com.javaspider.dynamic.interaction;

import com.javaspider.browser.BrowserManager;
import com.javaspider.dynamic.render.JavaScriptExecutor;
import org.openqa.selenium.*;
import org.openqa.selenium.interactions.Actions;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;

/**
 * 动态表单交互
 * 支持点击、输入、选择、拖拽等操作
 * 
 * 特性:
 * - 智能元素查找
 * - 多种输入方式
 * - 下拉框选择
 * - 文件上传
 * - 拖拽操作
 * - 右键菜单
 */
public class FormInteractor {
    private static final Logger logger = LoggerFactory.getLogger(FormInteractor.class);
    
    private final BrowserManager browser;
    private final WebDriver driver;
    private final JavaScriptExecutor jsExecutor;
    private final Actions actions;
    
    /**
     * 构造函数
     */
    public FormInteractor(BrowserManager browser) {
        this.browser = browser;
        this.driver = browser.getDriver();
        this.jsExecutor = new JavaScriptExecutor(browser);
        this.actions = new Actions(driver);
    }
    
    // ========== 点击操作 ==========
    
    /**
     * 点击元素
     */
    public boolean click(String selector) {
        logger.debug("Clicking: {}", selector);
        try {
            WebElement element = findElement(selector);
            if (element != null) {
                element.click();
                logger.debug("Clicked: {}", selector);
                return true;
            }
        } catch (Exception e) {
            logger.warn("Click failed: {}", e.getMessage());
            // 尝试 JS 点击
            return jsClick(selector);
        }
        return false;
    }
    
    /**
     * 双击元素
     */
    public boolean doubleClick(String selector) {
        logger.debug("Double clicking: {}", selector);
        try {
            WebElement element = findElement(selector);
            if (element != null) {
                actions.doubleClick(element).perform();
                return true;
            }
        } catch (Exception e) {
            logger.warn("Double click failed: {}", e.getMessage());
        }
        return false;
    }
    
    /**
     * 右键点击
     */
    public boolean rightClick(String selector) {
        logger.debug("Right clicking: {}", selector);
        try {
            WebElement element = findElement(selector);
            if (element != null) {
                actions.contextClick(element).perform();
                return true;
            }
        } catch (Exception e) {
            logger.warn("Right click failed: {}", e.getMessage());
        }
        return false;
    }
    
    /**
     * JS 点击（绕过某些限制）
     */
    public boolean jsClick(String selector) {
        logger.debug("JS clicking: {}", selector);
        String script = 
            "var el = document.querySelector('" + selector + "');" +
            "if (el) { el.click(); }";
        Object result = jsExecutor.execute(script);
        return result != null;
    }
    
    // ========== 输入操作 ==========
    
    /**
     * 输入文本
     */
    public boolean inputText(String selector, String text) {
        logger.debug("Inputting text into: {}", selector);
        try {
            WebElement element = findElement(selector);
            if (element != null) {
                element.clear();
                element.sendKeys(text);
                logger.debug("Text input: {}", selector);
                return true;
            }
        } catch (Exception e) {
            logger.warn("Input failed: {}", e.getMessage());
        }
        return false;
    }
    
    /**
     * 追加文本
     */
    public boolean appendText(String selector, String text) {
        logger.debug("Appending text into: {}", selector);
        try {
            WebElement element = findElement(selector);
            if (element != null) {
                element.sendKeys(text);
                return true;
            }
        } catch (Exception e) {
            logger.warn("Append failed: {}", e.getMessage());
        }
        return false;
    }
    
    /**
     * 清空输入框
     */
    public boolean clear(String selector) {
        logger.debug("Clearing: {}", selector);
        try {
            WebElement element = findElement(selector);
            if (element != null) {
                element.clear();
                return true;
            }
        } catch (Exception e) {
            logger.warn("Clear failed: {}", e.getMessage());
        }
        return false;
    }
    
    /**
     * 获取输入框值
     */
    public String getInputValue(String selector) {
        try {
            WebElement element = findElement(selector);
            if (element != null) {
                return element.getAttribute("value");
            }
        } catch (Exception e) {
            logger.warn("Get value failed: {}", e.getMessage());
        }
        return null;
    }
    
    // ========== 下拉框选择 ==========
    
    /**
     * 选择下拉选项（按文本）
     */
    public boolean selectByText(String selector, String text) {
        logger.debug("Selecting by text: {} in {}", text, selector);
        try {
            WebElement select = findElement(selector);
            if (select != null) {
                List<WebElement> options = select.findElements(By.tagName("option"));
                for (WebElement option : options) {
                    if (option.getText().equals(text)) {
                        option.click();
                        logger.debug("Selected: {}", text);
                        return true;
                    }
                }
            }
        } catch (Exception e) {
            logger.warn("Select by text failed: {}", e.getMessage());
        }
        return false;
    }
    
    /**
     * 选择下拉选项（按值）
     */
    public boolean selectByValue(String selector, String value) {
        logger.debug("Selecting by value: {} in {}", value, selector);
        try {
            WebElement select = findElement(selector);
            if (select != null) {
                List<WebElement> options = select.findElements(By.tagName("option"));
                for (WebElement option : options) {
                    if (option.getAttribute("value").equals(value)) {
                        option.click();
                        logger.debug("Selected value: {}", value);
                        return true;
                    }
                }
            }
        } catch (Exception e) {
            logger.warn("Select by value failed: {}", e.getMessage());
        }
        return false;
    }
    
    /**
     * 选择下拉选项（按索引）
     */
    public boolean selectByIndex(String selector, int index) {
        logger.debug("Selecting by index: {} in {}", index, selector);
        try {
            WebElement select = findElement(selector);
            if (select != null) {
                List<WebElement> options = select.findElements(By.tagName("option"));
                if (index >= 0 && index < options.size()) {
                    options.get(index).click();
                    return true;
                }
            }
        } catch (Exception e) {
            logger.warn("Select by index failed: {}", e.getMessage());
        }
        return false;
    }
    
    /**
     * 获取选中的选项
     */
    public String getSelectedOption(String selector) {
        try {
            WebElement select = findElement(selector);
            if (select != null) {
                List<WebElement> options = select.findElements(By.tagName("option"));
                for (WebElement option : options) {
                    if (option.isSelected()) {
                        return option.getText();
                    }
                }
            }
        } catch (Exception e) {
            logger.warn("Get selected failed: {}", e.getMessage());
        }
        return null;
    }
    
    // ========== 文件上传 ==========
    
    /**
     * 上传文件
     */
    public boolean uploadFile(String selector, String filePath) {
        logger.debug("Uploading file: {} to {}", filePath, selector);
        try {
            WebElement element = findElement(selector);
            if (element != null) {
                element.sendKeys(filePath);
                logger.debug("File uploaded: {}", filePath);
                return true;
            }
        } catch (Exception e) {
            logger.warn("Upload failed: {}", e.getMessage());
        }
        return false;
    }
    
    // ========== 拖拽操作 ==========
    
    /**
     * 拖拽元素
     */
    public boolean dragAndDrop(String fromSelector, String toSelector) {
        logger.debug("Drag and drop: {} -> {}", fromSelector, toSelector);
        try {
            WebElement from = findElement(fromSelector);
            WebElement to = findElement(toSelector);
            
            if (from != null && to != null) {
                actions.dragAndDrop(from, to).perform();
                logger.debug("Dragged and dropped");
                return true;
            }
        } catch (Exception e) {
            logger.warn("Drag and drop failed: {}", e.getMessage());
        }
        return false;
    }
    
    /**
     * 拖拽到指定位置
     */
    public boolean dragAndDropBy(String selector, int xOffset, int yOffset) {
        logger.debug("Drag and drop by: {} ({}, {})", selector, xOffset, yOffset);
        try {
            WebElement element = findElement(selector);
            if (element != null) {
                actions.dragAndDropBy(element, xOffset, yOffset).perform();
                return true;
            }
        } catch (Exception e) {
            logger.warn("Drag and drop by failed: {}", e.getMessage());
        }
        return false;
    }
    
    // ========== 悬停操作 ==========
    
    /**
     * 悬停元素
     */
    public boolean hover(String selector) {
        logger.debug("Hovering: {}", selector);
        try {
            WebElement element = findElement(selector);
            if (element != null) {
                actions.moveToElement(element).perform();
                logger.debug("Hovered: {}", selector);
                return true;
            }
        } catch (Exception e) {
            logger.warn("Hover failed: {}", e.getMessage());
        }
        return false;
    }
    
    // ========== 键盘操作 ==========
    
    /**
     * 按键盘
     */
    public boolean sendKeys(String key) {
        logger.debug("Sending key: {}", key);
        try {
            Keys keys = Keys.valueOf(key.toUpperCase());
            actions.sendKeys(keys).perform();
            return true;
        } catch (Exception e) {
            logger.warn("Send keys failed: {}", e.getMessage());
        }
        return false;
    }
    
    /**
     * 向元素发送键盘
     */
    public boolean sendKeysToElement(String selector, String keys) {
        logger.debug("Sending keys to {}: {}", selector, keys);
        try {
            WebElement element = findElement(selector);
            if (element != null) {
                element.sendKeys(keys);
                return true;
            }
        } catch (Exception e) {
            logger.warn("Send keys failed: {}", e.getMessage());
        }
        return false;
    }
    
    // ========== 辅助方法 ==========
    
    /**
     * 查找元素
     */
    private WebElement findElement(String selector) {
        try {
            // 尝试 CSS 选择器
            return driver.findElement(By.cssSelector(selector));
        } catch (Exception e) {
            try {
                // 尝试 XPath
                return driver.findElement(By.xpath(selector));
            } catch (Exception e2) {
                try {
                    // 尝试 ID
                    return driver.findElement(By.id(selector));
                } catch (Exception e3) {
                    logger.warn("Element not found: {}", selector);
                    return null;
                }
            }
        }
    }
    
    /**
     * 查找多个元素
     */
    public List<WebElement> findElements(String selector) {
        try {
            return driver.findElements(By.cssSelector(selector));
        } catch (Exception e) {
            logger.warn("Elements not found: {}", selector);
            return null;
        }
    }
    
    /**
     * 检查元素是否存在
     */
    public boolean elementExists(String selector) {
        return findElement(selector) != null;
    }
    
    /**
     * 检查元素是否可见
     */
    public boolean elementVisible(String selector) {
        WebElement element = findElement(selector);
        return element != null && element.isDisplayed();
    }
    
    /**
     * 检查元素是否可点击
     */
    public boolean elementClickable(String selector) {
        WebElement element = findElement(selector);
        return element != null && element.isEnabled();
    }
}
