//! 浏览器自动化模块
//! 使用 fantoccini (WebDriver 客户端)

use std::time::Duration;

/// 浏览器管理器
#[cfg(feature = "browser")]
pub struct BrowserManager {
    webdriver: fantoccini::Client,
}

#[cfg(feature = "browser")]
impl BrowserManager {
    /// 创建浏览器管理器
    pub async fn new(headless: bool) -> Result<Self, fantoccini::error::CmdError> {
        use fantoccini::{ClientBuilder, Locator};
        
        let mut caps = serde_json::map::Map::new();
        
        if headless {
            let mut args = serde_json::map::Map::new();
            args.insert("args".to_string(), vec!["--headless".into()].into());
            caps.insert("goog:chromeOptions".to_string(), args.into());
        }
        
        let webdriver = ClientBuilder::native()
            .capabilities(caps)
            .connect("http://localhost:4444")
            .await?;
        
        Ok(BrowserManager { webdriver })
    }
    
    /// 导航到 URL
    pub async fn navigate(&self, url: &str) -> Result<(), fantoccini::error::CmdError> {
        self.webdriver.goto(url).await
    }
    
    /// 获取 HTML
    pub async fn get_html(&self) -> Result<String, fantoccini::error::CmdError> {
        self.webdriver.source().await
    }
    
    /// 获取标题
    pub async fn get_title(&self) -> Result<String, fantoccini::error::CmdError> {
        self.webdriver.title().await
    }
    
    /// 点击元素
    pub async fn click(&self, selector: &str) -> Result<(), fantoccini::error::CmdError> {
        let element = self.webdriver.wait().for_element(Locator::Css(selector)).await?;
        element.click().await
    }
    
    /// 输入文本
    pub async fn fill(&self, selector: &str, text: &str) -> Result<(), fantoccini::error::CmdError> {
        let element = self.webdriver.wait().for_element(Locator::Css(selector)).await?;
        element.send_keys(text).await
    }
    
    /// 截图
    pub async fn screenshot(&self) -> Result<Vec<u8>, fantoccini::error::CmdError> {
        self.webdriver.screenshot().await
    }
    
    /// 执行 JavaScript
    pub async fn execute_script(&self, script: &str) -> Result<(), fantoccini::error::CmdError> {
        self.webdriver.execute(script, Vec::new()).await
    }
    
    /// 滚动到底部
    pub async fn scroll_to_bottom(&self) -> Result<(), fantoccini::error::CmdError> {
        self.webdriver.execute("window.scrollTo(0, document.body.scrollHeight);", Vec::new()).await
    }
    
    /// 等待元素
    pub async fn wait_for_element(&self, selector: &str, timeout: Duration) -> Result<(), fantoccini::error::CmdError> {
        self.webdriver.wait().with_timeout(timeout).for_element(Locator::Css(selector)).await?;
        Ok(())
    }
    
    /// 关闭浏览器
    pub async fn close(self) -> Result<(), fantoccini::error::CmdError> {
        self.webdriver.close().await
    }
}

/// 滚动加载器
pub struct ScrollLoader {
    scroll_action: Box<dyn FnMut() + Send>,
    get_height_action: Box<dyn FnMut() -> i64 + Send>,
}

impl ScrollLoader {
    /// 创建滚动加载器
    pub fn new<F, G>(scroll_fn: F, get_height_fn: G) -> Self
    where
        F: FnMut() + Send + 'static,
        G: FnMut() -> i64 + Send + 'static,
    {
        ScrollLoader {
            scroll_action: Box::new(scroll_fn),
            get_height_action: Box::new(get_height_fn),
        }
    }
    
    /// 滚动到底部
    pub fn scroll_to_bottom(&mut self, pause_ms: u64, max_scrolls: usize) -> usize {
        use crate::dynamic::wait::DynamicWait;
        
        let mut scroll_count = 0;
        let mut last_height = (self.get_height_action)();
        let mut stable_count = 0;
        
        while scroll_count < max_scrolls {
            // 滚动到底部
            (self.scroll_action)();
            scroll_count += 1;
            
            // 等待加载
            DynamicWait::sleep(pause_ms);
            
            // 检查新高度
            let new_height = (self.get_height_action)();
            
            if new_height == last_height {
                stable_count += 1;
                if stable_count >= 2 {
                    break;
                }
            } else {
                stable_count = 0;
                last_height = new_height;
            }
        }
        
        scroll_count
    }
}

/// JavaScript 执行器
pub struct JavaScriptExecutor<F> {
    execute_fn: F,
}

impl<F> JavaScriptExecutor<F>
where
    F: FnMut(&str) -> Result<serde_json::Value, String>,
{
    /// 创建执行器
    pub fn new(execute_fn: F) -> Self {
        JavaScriptExecutor { execute_fn }
    }
    
    /// 执行脚本
    pub fn execute(&mut self, script: &str) -> Result<serde_json::Value, String> {
        (self.execute_fn)(script)
    }
    
    /// 获取标题
    pub fn get_title(&mut self) -> Result<String, String> {
        let result = self.execute("return document.title")?;
        result.as_str().map(|s| s.to_string()).ok_or_else(|| "Invalid result".to_string())
    }
    
    /// 获取 URL
    pub fn get_url(&mut self) -> Result<String, String> {
        let result = self.execute("return window.location.href")?;
        result.as_str().map(|s| s.to_string()).ok_or_else(|| "Invalid result".to_string())
    }
    
    /// 绕过自动化检测
    pub fn bypass_detection(&mut self) -> Result<(), String> {
        self.execute(r#"
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
        "#)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_scroll_loader() {
        let mut scroll_count = 0;
        let mut height = 1000i64;
        let mut stable = 0;
        
        let mut loader = ScrollLoader::new(
            || { scroll_count += 1; },
            || { 
                if stable < 2 { stable += 1; height } else { height }
            },
        );
        
        let result = loader.scroll_to_bottom(10, 50);
        assert!(result > 0);
    }
}
