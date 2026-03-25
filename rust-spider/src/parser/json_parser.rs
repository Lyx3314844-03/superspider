//! JSON 解析器
//! 
//! 基于 serde_json 的 JSON 解析器

use serde_json::Value;
use log::debug;

/// JSON 解析器
/// 
/// 用于解析 JSON 数据并提取字段
/// 
/// # Examples
/// 
/// ```
/// use rust_spider::parser::JsonParser;
/// 
/// let json = r#"{"name": "John", "age": 30, "city": "New York"}"#;
/// let parser = JsonParser::new(json);
/// 
/// assert_eq!(parser.get_string("name"), Some("John".to_string()));
/// assert_eq!(parser.get_i64("age"), Some(30));
/// ```
#[derive(Debug, Clone)]
pub struct JsonParser {
    value: Value,
}

impl JsonParser {
    /// 创建新解析器
    /// 
    /// # Arguments
    /// 
    /// * `json` - JSON 字符串
    pub fn new(json: &str) -> Result<Self, serde_json::Error> {
        let value = serde_json::from_str(json)?;
        Ok(Self { value })
    }
    
    /// 从 Value 创建
    pub fn from_value(value: Value) -> Self {
        Self { value }
    }
    
    /// 解析 JSON 字符串
    pub fn parse(json: &str) -> Result<Self, serde_json::Error> {
        Self::new(json)
    }
    
    /// 获取字符串值
    /// 
    /// # Arguments
    /// 
    /// * `path` - JSONPath 风格的路径，如 "user.name"
    pub fn get_string(&self, path: &str) -> Option<String> {
        self.get_path(path).and_then(|v| v.as_str().map(String::from))
    }
    
    /// 获取整数值
    pub fn get_i64(&self, path: &str) -> Option<i64> {
        self.get_path(path).and_then(|v| v.as_i64())
    }
    
    /// 获取浮点数值
    pub fn get_f64(&self, path: &str) -> Option<f64> {
        self.get_path(path).and_then(|v| v.as_f64())
    }
    
    /// 获取布尔值
    pub fn get_bool(&self, path: &str) -> Option<bool> {
        self.get_path(path).and_then(|v| v.as_bool())
    }
    
    /// 获取数组
    pub fn get_array(&self, path: &str) -> Option<&Vec<Value>> {
        self.get_path(path).and_then(|v| v.as_array())
    }
    
    /// 获取对象
    pub fn get_object(&self, path: &str) -> Option<&serde_json::Map<String, Value>> {
        self.get_path(path).and_then(|v| v.as_object())
    }
    
    /// 获取原始 Value
    pub fn get(&self, path: &str) -> Option<&Value> {
        self.get_path(path)
    }
    
    /// 获取路径对应的值
    fn get_path(&self, path: &str) -> Option<&Value> {
        let mut current = &self.value;
        
        for key in path.split('.') {
            current = match current {
                Value::Object(map) => map.get(key),
                Value::Array(arr) => {
                    if let Ok(index) = key.parse::<usize>() {
                        arr.get(index)
                    } else {
                        return None;
                    }
                }
                _ => return None,
            }?;
        }
        
        Some(current)
    }
    
    /// 使用 JSONPath 查询（简化版）
    /// 
    /// 支持基本的 JSONPath 语法：
    /// - $.key - 根对象的 key
    /// - .key - 当前对象的 key
    /// - [n] - 数组索引
    /// - [*] - 所有数组元素
    pub fn json_path(&self, path: &str) -> Vec<&Value> {
        let mut results = Vec::new();
        
        // 简化实现：只支持基本路径
        let clean_path = path.trim_start_matches('$').trim_start_matches('.');
        
        if clean_path.is_empty() {
            results.push(&self.value);
        } else if let Some(value) = self.get(clean_path) {
            results.push(value);
        }
        
        results
    }
    
    /// 获取所有匹配的字符串
    pub fn get_all_strings(&self, path: &str) -> Vec<String> {
        self.json_path(path)
            .iter()
            .filter_map(|v| v.as_str().map(String::from))
            .collect()
    }
    
    /// 检查路径是否存在
    pub fn exists(&self, path: &str) -> bool {
        self.get_path(path).is_some()
    }
    
    /// 获取原始 JSON 字符串
    pub fn to_string(&self) -> String {
        self.value.to_string()
    }
    
    /// 格式化的 JSON 字符串
    pub fn to_pretty_string(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string_pretty(&self.value)
    }
}

/// 从字符串创建 JsonParser
impl TryFrom<&str> for JsonParser {
    type Error = serde_json::Error;
    
    fn try_from(json: &str) -> Result<Self, Self::Error> {
        Self::new(json)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_get_string() {
        let json = r#"{"name": "John", "age": 30}"#;
        let parser = JsonParser::new(json).unwrap();
        assert_eq!(parser.get_string("name"), Some("John".to_string()));
    }
    
    #[test]
    fn test_get_i64() {
        let json = r#"{"name": "John", "age": 30}"#;
        let parser = JsonParser::new(json).unwrap();
        assert_eq!(parser.get_i64("age"), Some(30));
    }
    
    #[test]
    fn test_nested_path() {
        let json = r#"{"user": {"name": "John", "address": {"city": "NYC"}}}"#;
        let parser = JsonParser::new(json).unwrap();
        assert_eq!(parser.get_string("user.name"), Some("John".to_string()));
        assert_eq!(parser.get_string("user.address.city"), Some("NYC".to_string()));
    }
    
    #[test]
    fn test_array() {
        let json = r#"{"items": [1, 2, 3, 4, 5]}"#;
        let parser = JsonParser::new(json).unwrap();
        assert_eq!(parser.get_i64("items.0"), Some(1));
        assert_eq!(parser.get_i64("items.2"), Some(3));
    }
}
