//! HTML 解析器
//! 
//! 基于 scraper 库的 HTML 解析器

use scraper::{Html, Selector, ElementRef};

/// HTML 解析器
/// 
/// 用于解析 HTML 文档并提取数据
#[derive(Debug, Clone)]
pub struct HtmlParser {
    document: Html,
}

impl HtmlParser {
    /// 创建新解析器
    /// 
    /// # Arguments
    /// 
    /// * `html` - HTML 字符串
    /// 
    /// # Examples
    /// 
    /// ```
    /// use rust_spider::parser::HtmlParser;
    /// 
    /// let html = "<html><head><title>Test</title></head><body><h1>Hello</h1></body></html>";
    /// let parser = HtmlParser::new(html);
    /// ```
    pub fn new(html: &str) -> Self {
        Self {
            document: Html::parse_document(html),
        }
    }
    
    /// 从字符串创建
    pub fn from_str(html: &str) -> Self {
        Self::new(html)
    }
    
    /// 获取文档标题
    pub fn title(&self) -> Option<String> {
        let selector = Selector::parse("title").ok()?;
        self.document
            .select(&selector)
            .next()
            .map(|elem| elem.text().collect())
    }
    
    /// CSS 选择器 - 获取第一个匹配元素
    /// 
    /// # Arguments
    /// 
    /// * `selector` - CSS 选择器
    /// 
    /// # Examples
    /// 
    /// ```
    /// use rust_spider::parser::HtmlParser;
    /// 
    /// let html = r#"<div class="content"><h1>Title</h1></div>"#;
    /// let parser = HtmlParser::new(html);
    /// let title = parser.css_first("h1");
    /// ```
    pub fn css_first(&self, selector: &str) -> Option<String> {
        let selector = Selector::parse(selector).ok()?;
        self.document
            .select(&selector)
            .next()
            .map(|elem| elem.text().collect())
    }
    
    /// CSS 选择器 - 获取所有匹配元素
    pub fn css(&self, selector: &str) -> Vec<String> {
        if let Ok(selector) = Selector::parse(selector) {
            self.document
                .select(&selector)
                .map(|elem| elem.text().collect())
                .collect()
        } else {
            Vec::new()
        }
    }
    
    /// CSS 选择器 - 获取第一个元素的属性
    /// 
    /// # Arguments
    /// 
    /// * `selector` - CSS 选择器
    /// * `attr` - 属性名
    /// 
    /// # Examples
    /// 
    /// ```
    /// use rust_spider::parser::HtmlParser;
    /// 
    /// let html = r#"<a href="https://example.com">Link</a>"#;
    /// let parser = HtmlParser::new(html);
    /// let href = parser.css_attr("a", "href");
    /// ```
    pub fn css_attr(&self, selector: &str, attr: &str) -> Option<String> {
        let selector = Selector::parse(selector).ok()?;
        self.document
            .select(&selector)
            .next()
            .and_then(|elem| elem.value().attr(attr).map(String::from))
    }
    
    /// CSS 选择器 - 获取所有元素的属性
    pub fn css_attrs(&self, selector: &str, attr: &str) -> Vec<String> {
        if let Ok(selector) = Selector::parse(selector) {
            self.document
                .select(&selector)
                .filter_map(|elem| elem.value().attr(attr).map(String::from))
                .collect()
        } else {
            Vec::new()
        }
    }
    
    /// 获取所有链接
    pub fn links(&self) -> Vec<String> {
        self.css_attrs("a", "href")
    }
    
    /// 获取所有图片链接
    pub fn images(&self) -> Vec<String> {
        self.css_attrs("img", "src")
    }
    
    /// 获取所有段落
    pub fn paragraphs(&self) -> Vec<String> {
        self.css("p")
    }
    
    /// 获取所有标题 (h1-h6)
    pub fn headings(&self) -> Vec<String> {
        let mut headings = Vec::new();
        for tag in &["h1", "h2", "h3", "h4", "h5", "h6"] {
            headings.extend(self.css(tag));
        }
        headings
    }
    
    /// 获取元数据
    pub fn meta(&self, name: &str) -> Option<String> {
        let selector = format!("meta[name=\"{}\"]", name);
        self.css_attr(&selector, "content")
    }
    
    /// 获取 Open Graph 数据
    pub fn og(&self, property: &str) -> Option<String> {
        let selector = format!("meta[property=\"{}\"]", property);
        self.css_attr(&selector, "content")
    }
    
    /// 使用 XPath 选择元素（简化版）
    pub fn xpath(&self, _xpath: &str) -> Vec<String> {
        // 注意：scraper 不支持 XPath，这里返回空
        // 如需 XPath 支持，可以使用 xpath  crate
        log::warn!("XPath is not fully supported, use css selectors instead");
        Vec::new()
    }
    
    /// 获取纯文本内容
    pub fn text(&self) -> String {
        self.document.root_element().text().collect()
    }
    
    /// 检查是否存在匹配的元素
    pub fn exists(&self, selector: &str) -> bool {
        if let Ok(selector) = Selector::parse(selector) {
            self.document.select(&selector).next().is_some()
        } else {
            false
        }
    }
    
    /// 获取匹配元素的数量
    pub fn count(&self, selector: &str) -> usize {
        if let Ok(selector) = Selector::parse(selector) {
            self.document.select(&selector).count()
        } else {
            0
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_title() {
        let html = "<html><head><title>Test Title</title></head><body></body></html>";
        let parser = HtmlParser::new(html);
        assert_eq!(parser.title(), Some("Test Title".to_string()));
    }
    
    #[test]
    fn test_css_first() {
        let html = r#"<div><h1 class="main">Hello</h1></div>"#;
        let parser = HtmlParser::new(html);
        assert_eq!(parser.css_first("h1.main"), Some("Hello".to_string()));
    }
    
    #[test]
    fn test_links() {
        let html = r#"<html><body>
            <a href="/link1">Link 1</a>
            <a href="/link2">Link 2</a>
        </body></html>"#;
        let parser = HtmlParser::new(html);
        let links = parser.links();
        assert_eq!(links.len(), 2);
        assert_eq!(links[0], "/link1");
        assert_eq!(links[1], "/link2");
    }
}
