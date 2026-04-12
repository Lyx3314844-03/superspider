//! HTML 和 JSON 解析器

use scraper::{Html, Selector};
use serde_json::Value;
use std::io::Write;
use std::process::{Command, Stdio};

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

    pub fn xpath_first(&self, xpath: &str) -> Option<String> {
        self.xpath_first_strict(xpath).ok().flatten()
    }

    pub fn xpath_first_strict(&self, xpath: &str) -> Result<Option<String>, String> {
        run_xpath_helper(&self.html(), xpath)
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

    pub fn html(&self) -> String {
        self.document.root_element().html()
    }
}

fn run_xpath_helper(html: &str, xpath: &str) -> Result<Option<String>, String> {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or_else(|| "failed to resolve workspace root".to_string())?;
    let script = root.join("tools").join("xpath_extract.py");
    if !script.exists() {
        return Err(format!("missing helper script: {}", script.display()));
    }

    let mut child = Command::new("python")
        .arg(script)
        .arg(xpath)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|err| format!("failed to spawn xpath helper: {err}"))?;

    if let Some(stdin) = child.stdin.as_mut() {
        stdin
            .write_all(html.as_bytes())
            .map_err(|err| format!("failed to write xpath helper stdin: {err}"))?;
    }
    let output = child
        .wait_with_output()
        .map_err(|err| format!("failed to wait for xpath helper: {err}"))?;
    if !output.status.success() {
        return Err(format!(
            "xpath helper failed: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    let payload: serde_json::Value = serde_json::from_slice(&output.stdout)
        .map_err(|err| format!("invalid xpath helper output: {err}"))?;
    if let Some(error) = payload.get("error").and_then(|value| value.as_str()) {
        return Err(error.to_string());
    }
    let values = payload
        .get("values")
        .and_then(|value| value.as_array())
        .ok_or_else(|| "xpath helper returned malformed payload".to_string())?;
    Ok(values
        .first()
        .and_then(|value| value.as_str())
        .map(|value| value.to_string()))
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

#[cfg(test)]
mod tests {
    use super::HTMLParser;

    #[test]
    fn xpath_first_strict_supports_full_xpath() {
        let parser = HTMLParser::new(r#"<html><div><span>One</span><span>Two</span></div></html>"#);
        let value = parser
            .xpath_first_strict("//div/span[2]/text()")
            .expect("xpath");
        assert_eq!(value.as_deref(), Some("Two"));
    }

    #[test]
    fn xpath_first_strict_rejects_invalid_expressions() {
        let parser = HTMLParser::new(r#"<html><div><span>Demo</span></div></html>"#);
        let err = parser.xpath_first_strict("//*[");
        assert!(err.is_err());
    }
}
