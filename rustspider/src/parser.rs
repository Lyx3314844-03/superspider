//! HTML 和 JSON 解析器

use scraper::{Html, Selector};
use serde_json::Value;

/// HTML 解析器
pub struct HTMLParser {
    document: Html,
}

impl HTMLParser {
    /// 创建新解析器
    pub fn new(html: &str) -> Self {
        HTMLParser {
            document: Html::parse_document(html),
        }
    }

    /// CSS 选择器提取
    pub fn css(&self, selector: &str) -> Vec<String> {
        if let Ok(sel) = Selector::parse(selector) {
            self.document
                .select(&sel)
                .map(|elem| elem.text().collect::<String>().trim().to_string())
                .collect()
        } else {
            Vec::new()
        }
    }

    /// 获取第一个匹配
    pub fn css_first(&self, selector: &str) -> Option<String> {
        if let Ok(sel) = Selector::parse(selector) {
            self.document
                .select(&sel)
                .next()
                .map(|elem| elem.text().collect::<String>().trim().to_string())
        } else {
            None
        }
    }

    /// 获取属性
    pub fn css_attr(&self, selector: &str, attr: &str) -> Vec<String> {
        if let Ok(sel) = Selector::parse(selector) {
            self.document
                .select(&sel)
                .filter_map(|elem| elem.value().attr(attr).map(|s| s.to_string()))
                .collect()
        } else {
            Vec::new()
        }
    }

    /// 获取第一个属性
    pub fn css_attr_first(&self, selector: &str, attr: &str) -> Option<String> {
        if let Ok(sel) = Selector::parse(selector) {
            self.document
                .select(&sel)
                .next()
                .and_then(|elem| elem.value().attr(attr).map(|s| s.to_string()))
        } else {
            None
        }
    }

    /// 获取所有链接
    pub fn links(&self) -> Vec<String> {
        self.css_attr("a", "href")
    }

    /// 获取所有图片
    pub fn images(&self) -> Vec<String> {
        self.css_attr("img", "src")
    }

    /// 获取标题
    pub fn title(&self) -> Option<String> {
        self.css_first("title")
    }

    /// 获取文本
    pub fn text(&self) -> String {
        self.document
            .root_element()
            .text()
            .collect::<Vec<_>>()
            .join(" ")
    }
}

/// JSON 解析器
pub struct JSONParser {
    value: Value,
}

impl JSONParser {
    /// 创建新解析器
    pub fn new(json: &str) -> Option<Self> {
        serde_json::from_str(json)
            .ok()
            .map(|value| JSONParser { value })
    }

    /// 获取 JSON 路径
    pub fn get(&self, path: &str) -> Option<&Value> {
        let mut current = &self.value;
        for key in path.split('.') {
            current = match current {
                Value::Object(map) => map.get(key)?,
                Value::Array(arr) => {
                    let idx = key.parse::<usize>().ok()?;
                    arr.get(idx)?
                }
                _ => return None,
            };
        }
        Some(current)
    }

    /// 获取字符串
    pub fn get_string(&self, path: &str) -> Option<String> {
        self.get(path)
            .and_then(|v| v.as_str().map(|s| s.to_string()))
    }

    /// 获取整数
    pub fn get_i64(&self, path: &str) -> Option<i64> {
        self.get(path).and_then(|v| v.as_i64())
    }

    /// 获取浮点数
    pub fn get_f64(&self, path: &str) -> Option<f64> {
        self.get(path).and_then(|v| v.as_f64())
    }

    /// 获取布尔值
    pub fn get_bool(&self, path: &str) -> Option<bool> {
        self.get(path).and_then(|v| v.as_bool())
    }

    /// 获取数组
    pub fn get_array(&self, path: &str) -> Option<&Vec<Value>> {
        self.get(path).and_then(|v| v.as_array())
    }
}
