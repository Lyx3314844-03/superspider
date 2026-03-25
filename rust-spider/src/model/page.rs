//! 页面对象
//! 
//! 表示已解析的页面数据，包含响应和提取的字段

use std::collections::HashMap;
use crate::Response;

/// 页面对象
/// 
/// 包含响应数据和提取的字段
#[derive(Debug, Clone)]
pub struct Page {
    /// 页面 URL
    pub url: String,
    /// HTTP 响应
    pub response: Response,
    /// 页面标题
    pub title: Option<String>,
    /// HTML 内容
    pub html: String,
    /// 提取的字段
    pub fields: HashMap<String, String>,
    /// 待爬取的链接
    pub target_urls: Vec<String>,
    /// 错误信息
    pub error: Option<String>,
}

impl Page {
    /// 从响应创建页面
    pub fn from_response(response: Response) -> Self {
        let html = response.text.clone();
        let title = Self::extract_title(&html);
        
        Self {
            url: response.url.clone(),
            response,
            title,
            html,
            fields: HashMap::new(),
            target_urls: Vec::new(),
            error: None,
        }
    }
    
    /// 提取 HTML 标题
    fn extract_title(html: &str) -> Option<String> {
        use scraper::{Html, Selector};
        
        let document = Html::parse_document(html);
        let selector = Selector::parse("title").ok()?;
        
        document
            .select(&selector)
            .next()
            .map(|element| element.text().collect::<String>())
    }
    
    /// 提取 CSS 选择器匹配的第一个元素文本
    pub fn css_first(&self, selector: &str) -> Option<String> {
        use scraper::{Html, Selector};
        
        let document = Html::parse_document(&self.html);
        let selector = Selector::parse(selector).ok()?;
        
        document
            .select(&selector)
            .next()
            .map(|element| element.text().collect::<String>())
    }
    
    /// 提取 CSS 选择器匹配的所有元素文本
    pub fn css(&self, selector: &str) -> Vec<String> {
        use scraper::{Html, Selector};
        
        let document = Html::parse_document(&self.html);
        
        if let Ok(selector) = Selector::parse(selector) {
            document
                .select(&selector)
                .map(|element| element.text().collect::<String>())
                .collect()
        } else {
            Vec::new()
        }
    }
    
    /// 提取 CSS 选择器匹配的第一个元素的属性
    pub fn css_attr(&self, selector: &str, attr: &str) -> Option<String> {
        use scraper::{Html, Selector};
        
        let document = Html::parse_document(&self.html);
        let selector = Selector::parse(selector).ok()?;
        
        document
            .select(&selector)
            .next()
            .and_then(|element| element.value().attr(attr).map(String::from))
    }
    
    /// 提取所有链接
    pub fn get_links(&self) -> Vec<String> {
        self.css_attr("a", "href")
            .into_iter()
            .collect()
    }
    
    /// 提取所有图片链接
    pub fn get_images(&self) -> Vec<String> {
        self.css_attr("img", "src")
            .into_iter()
            .collect()
    }
    
    /// 添加提取字段
    pub fn put_field(&mut self, key: impl Into<String>, value: impl Into<String>) {
        self.fields.insert(key.into(), value.into());
    }
    
    /// 获取字段
    pub fn get_field(&self, key: &str) -> Option<&String> {
        self.fields.get(key)
    }
    
    /// 添加目标 URL
    pub fn add_target_url(&mut self, url: impl Into<String>) {
        self.target_urls.push(url.into());
    }
    
    /// 设置错误信息
    pub fn set_error(&mut self, error: impl Into<String>) {
        self.error = Some(error.into());
    }
    
    /// 检查是否有错误
    pub fn has_error(&self) -> bool {
        self.error.is_some()
    }
}

impl From<Response> for Page {
    fn from(response: Response) -> Self {
        Self::from_response(response)
    }
}
