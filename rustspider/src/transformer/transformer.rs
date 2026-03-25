//! 数据转换模块

use std::collections::HashMap;
use regex::Regex;

/// 数据转换器
pub struct DataTransformer {
    rules: Vec<TransformRule>,
}

impl DataTransformer {
    /// 创建数据转换器
    pub fn new() -> Self {
        DataTransformer {
            rules: Vec::new(),
        }
    }
    
    /// 添加去除空白规则
    pub fn add_trim_rule(mut self, field: &str) -> Self {
        self.rules.push(TransformRule {
            field: field.to_string(),
            rule_type: "trim".to_string(),
            pattern: None,
            apply: Box::new(|v| {
                if let Some(s) = v.as_str() {
                    Some(s.trim().to_string())
                } else {
                    v
                }
            }),
        });
        self
    }
    
    /// 添加替换规则
    pub fn add_replace_rule(mut self, field: &str, from: &str, to: &str) -> Self {
        let from_str = from.to_string();
        let to_str = to.to_string();
        
        self.rules.push(TransformRule {
            field: field.to_string(),
            rule_type: "replace".to_string(),
            pattern: None,
            apply: Box::new(move |v| {
                if let Some(s) = v.as_str() {
                    Some(s.replace(&from_str, &to_str))
                } else {
                    v
                }
            }),
        });
        self
    }
    
    /// 添加正则提取规则
    pub fn add_regex_rule(mut self, field: &str, pattern: &str) -> Self {
        let regex = Regex::new(pattern).ok();
        
        self.rules.push(TransformRule {
            field: field.to_string(),
            rule_type: "regex".to_string(),
            pattern: pattern.to_string(),
            apply: Box::new(move |v| {
                if let Some(s) = v.as_str() {
                    if let Some(ref re) = regex {
                        if let Some(caps) = re.captures(s) {
                            if caps.len() > 1 {
                                return Some(caps[1].to_string());
                            }
                        }
                    }
                    Some(s.to_string())
                } else {
                    v
                }
            }),
        });
        self
    }
    
    /// 添加大写规则
    pub fn add_upper_case_rule(mut self, field: &str) -> Self {
        self.rules.push(TransformRule {
            field: field.to_string(),
            rule_type: "upper".to_string(),
            pattern: None,
            apply: Box::new(|v| {
                if let Some(s) = v.as_str() {
                    Some(s.to_uppercase())
                } else {
                    v
                }
            }),
        });
        self
    }
    
    /// 添加小写规则
    pub fn add_lower_case_rule(mut self, field: &str) -> Self {
        self.rules.push(TransformRule {
            field: field.to_string(),
            rule_type: "lower".to_string(),
            pattern: None,
            apply: Box::new(|v| {
                if let Some(s) = v.as_str() {
                    Some(s.to_lowercase())
                } else {
                    v
                }
            }),
        });
        self
    }
    
    /// 添加 HTML 清理规则
    pub fn add_html_clean_rule(mut self, field: &str) -> Self {
        let html_regex = Regex::new(r"<[^>]*>").ok();
        
        self.rules.push(TransformRule {
            field: field.to_string(),
            rule_type: "html_clean".to_string(),
            pattern: None,
            apply: Box::new(move |v| {
                if let Some(s) = v.as_str() {
                    if let Some(ref re) = html_regex {
                        return Some(re.replace_all(s, "").to_string());
                    }
                    Some(s.to_string())
                } else {
                    v
                }
            }),
        });
        self
    }
    
    /// 添加空值处理规则
    pub fn add_null_rule(mut self, field: &str, default_value: &str) -> Self {
        let default = default_value.to_string();
        
        self.rules.push(TransformRule {
            field: field.to_string(),
            rule_type: "null".to_string(),
            pattern: None,
            apply: Box::new(move |v| {
                if v.is_none() || v.as_str().map(|s| s.is_empty()).unwrap_or(false) {
                    Some(default.clone())
                } else {
                    v
                }
            }),
        });
        self
    }
    
    /// 转换数据
    pub fn transform(&self, mut data: HashMap<String, String>) -> HashMap<String, String> {
        for rule in &self.rules {
            if let Some(value) = data.get(&rule.field) {
                let value = value.clone();
                if let Some(transformed) = (rule.apply)(Some(value)) {
                    data.insert(rule.field.clone(), transformed);
                }
            }
        }
        data
    }
    
    /// 清空规则
    pub fn clear_rules(&mut self) {
        self.rules.clear();
    }
}

impl Default for DataTransformer {
    fn default() -> Self {
        Self::new()
    }
}

/// 转换规则
struct TransformRule {
    field: String,
    rule_type: String,
    pattern: Option<String>,
    apply: Box<dyn Fn(Option<String>) -> Option<String> + Send + Sync>,
}

/// 数据验证器
pub struct DataValidator;

impl DataValidator {
    /// 验证邮箱
    pub fn is_email(value: &str) -> bool {
        let pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$";
        Regex::new(pattern).map(|re| re.is_match(value)).unwrap_or(false)
    }
    
    /// 验证中国手机号
    pub fn is_phone_cn(value: &str) -> bool {
        let pattern = r"^1[3-9]\d{9}$";
        Regex::new(pattern).map(|re| re.is_match(value)).unwrap_or(false)
    }
    
    /// 验证 URL
    pub fn is_url(value: &str) -> bool {
        let pattern = r"^https?://.+";
        Regex::new(pattern).map(|re| re.is_match(value)).unwrap_or(false)
    }
    
    /// 验证数字
    pub fn is_number(value: &str) -> bool {
        value.parse::<f64>().is_ok()
    }
    
    /// 验证日期
    pub fn is_date(value: &str, format: Option<&str>) -> bool {
        // 简单实现
        let patterns = match format {
            Some(fmt) => vec![fmt.to_string()],
            None => vec![
                r"^\d{4}-\d{2}-\d{2}$".to_string(),
                r"^\d{4}/\d{2}/\d{2}$".to_string(),
                r"^\d{2}/\d{2}/\d{4}$".to_string(),
            ],
        };
        
        patterns.iter().any(|pattern| {
            Regex::new(pattern).map(|re| re.is_match(value)).unwrap_or(false)
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_trim_rule() {
        let transformer = DataTransformer::new().add_trim_rule("field1");
        let mut data = HashMap::new();
        data.insert("field1".to_string(), "  hello  ".to_string());
        
        let result = transformer.transform(data);
        assert_eq!(result.get("field1").unwrap(), "hello");
    }
    
    #[test]
    fn test_email_validation() {
        assert!(DataValidator::is_email("test@example.com"));
        assert!(!DataValidator::is_email("invalid"));
    }
    
    #[test]
    fn test_phone_cn_validation() {
        assert!(DataValidator::is_phone_cn("13800138000"));
        assert!(!DataValidator::is_phone_cn("12345678901"));
    }
}
