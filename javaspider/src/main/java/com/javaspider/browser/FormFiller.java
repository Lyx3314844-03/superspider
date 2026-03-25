package com.javaspider.browser;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 自动表单填写器
 * 支持自动识别和填写表单字段
 */
public class FormFiller {
    private static final Logger logger = LoggerFactory.getLogger(FormFiller.class);

    private final WebDriver driver;

    // 字段名映射
    private static final Map<String, String[]> FIELD_MAPPINGS = new HashMap<>();
    
    static {
        // 用户名/邮箱字段
        FIELD_MAPPINGS.put("username", new String[]{"username", "user", "name", "uname", "nick", "nickname"});
        FIELD_MAPPINGS.put("email", new String[]{"email", "mail", "e-mail", "mailbox"});
        FIELD_MAPPINGS.put("password", new String[]{"password", "passwd", "pwd", "pass"});
        FIELD_MAPPINGS.put("phone", new String[]{"phone", "mobile", "tel", "telephone", "cell"});
        FIELD_MAPPINGS.put("captcha", new String[]{"captcha", "verify", "code", "validation", "check"});
        FIELD_MAPPINGS.put("firstName", new String[]{"firstname", "first_name", "fname", "given-name"});
        FIELD_MAPPINGS.put("lastName", new String[]{"lastname", "last_name", "lname", "family-name", "surname"});
        FIELD_MAPPINGS.put("address", new String[]{"address", "addr", "street"});
        FIELD_MAPPINGS.put("city", new String[]{"city", "town"});
        FIELD_MAPPINGS.put("zipcode", new String[]{"zipcode", "zip", "postal", "post_code"});
        FIELD_MAPPINGS.put("country", new String[]{"country", "nation"});
    }

    public FormFiller(WebDriver driver) {
        this.driver = driver;
    }

    /**
     * 自动填写表单
     */
    public void fillForm(Map<String, String> formData) {
        List<WebElement> forms = driver.findElements(By.tagName("form"));
        
        if (forms.isEmpty()) {
            logger.warn("No forms found on page");
            return;
        }

        WebElement mainForm = forms.get(0);
        
        for (Map.Entry<String, String> entry : formData.entrySet()) {
            fillField(entry.getKey(), entry.getValue());
        }
    }

    /**
     * 填写指定字段
     */
    public void fillField(String fieldName, String value) {
        String[] possibleNames = FIELD_MAPPINGS.getOrDefault(fieldName, new String[]{fieldName});
        
        for (String possibleName : possibleNames) {
            // 尝试 name 属性
            WebElement element = findElementByName(possibleName);
            if (element != null) {
                fillElement(element, value);
                return;
            }
            
            // 尝试 id 属性
            element = findElementById(possibleName);
            if (element != null) {
                fillElement(element, value);
                return;
            }
            
            // 尝试 placeholder
            element = findElementByPlaceholder(possibleName);
            if (element != null) {
                fillElement(element, value);
                return;
            }
            
            // 尝试 label
            element = findElementByLabel(possibleName);
            if (element != null) {
                fillElement(element, value);
                return;
            }
        }
        
        logger.debug("Field not found: {}", fieldName);
    }

    /**
     * 填写元素
     */
    private void fillElement(WebElement element, String value) {
        try {
            String type = element.getAttribute("type");
            String tagName = element.getTagName();
            
            if ("checkbox".equals(type)) {
                if (Boolean.parseBoolean(value) && !element.isSelected()) {
                    element.click();
                }
            } else if ("radio".equals(type)) {
                if (!element.isSelected()) {
                    element.click();
                }
            } else if ("select".equals(tagName) || element.getAttribute("role") != null) {
                // 下拉选择
                org.openqa.selenium.support.ui.Select select = new org.openqa.selenium.support.ui.Select(element);
                select.selectByVisibleText(value);
            } else {
                // 文本输入
                element.clear();
                element.sendKeys(value);
            }
            
            logger.debug("Filled field with value: {}", value);
        } catch (Exception e) {
            logger.error("Failed to fill element", e);
        }
    }

    /**
     * 按 name 查找元素
     */
    private WebElement findElementByName(String name) {
        try {
            return driver.findElement(By.name(name));
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * 按 id 查找元素
     */
    private WebElement findElementById(String id) {
        try {
            return driver.findElement(By.id(id));
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * 按 placeholder 查找元素
     */
    private WebElement findElementByPlaceholder(String placeholder) {
        try {
            return driver.findElement(By.cssSelector("input[placeholder*='" + placeholder + "'], textarea[placeholder*='" + placeholder + "']"));
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * 按 label 查找元素
     */
    private WebElement findElementByLabel(String labelText) {
        try {
            WebElement label = driver.findElement(By.xpath("//label[contains(text(), '" + labelText + "')]"));
            String forAttr = label.getAttribute("for");
            if (forAttr != null && !forAttr.isEmpty()) {
                return driver.findElement(By.id(forAttr));
            }
            // 查找 label 内的 input
            return label.findElement(By.cssSelector("input, textarea, select"));
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * 提交表单
     */
    public void submitForm() {
        List<WebElement> forms = driver.findElements(By.tagName("form"));
        if (!forms.isEmpty()) {
            forms.get(0).submit();
            logger.info("Form submitted");
        }
    }

    /**
     * 点击提交按钮
     */
    public void clickSubmit() {
        // 尝试多种选择器
        String[] submitSelectors = {
            "input[type='submit']",
            "button[type='submit']",
            "button.submit",
            "input.submit",
            "button:contains('Submit')",
            "button:contains('登录')",
            "button:contains('注册')",
            "button:contains('Sign In')",
            "button:contains('Sign Up')"
        };
        
        for (String selector : submitSelectors) {
            try {
                List<WebElement> buttons = driver.findElements(By.cssSelector(selector));
                if (!buttons.isEmpty() && buttons.get(0).isDisplayed()) {
                    buttons.get(0).click();
                    logger.info("Submit button clicked");
                    return;
                }
            } catch (Exception e) {
                // 继续尝试下一个
            }
        }
        
        logger.warn("Submit button not found");
    }

    /**
     * 获取表单字段列表
     */
    public Map<String, String> getFormFields() {
        Map<String, String> fields = new HashMap<>();
        
        List<WebElement> inputs = driver.findElements(By.cssSelector("input, textarea, select"));
        for (WebElement input : inputs) {
            if (!input.isDisplayed()) continue;
            
            String name = input.getAttribute("name");
            String id = input.getAttribute("id");
            String type = input.getAttribute("type");
            String placeholder = input.getAttribute("placeholder");
            
            if (name != null && !name.isEmpty()) {
                fields.put(name, type != null ? type : "text");
            } else if (id != null && !id.isEmpty()) {
                fields.put(id, type != null ? type : "text");
            } else if (placeholder != null && !placeholder.isEmpty()) {
                fields.put(placeholder, type != null ? type : "text");
            }
        }
        
        return fields;
    }

    /**
     * 创建 FormFiller
     */
    public static FormFiller create(WebDriver driver) {
        return new FormFiller(driver);
    }
}
