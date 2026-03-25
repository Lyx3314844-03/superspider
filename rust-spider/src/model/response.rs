//! 响应对象
//! 
//! 表示 HTTP 响应数据

use std::collections::HashMap;
use serde::{Deserialize, Serialize};

/// HTTP 响应对象
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Response {
    /// 响应 URL
    pub url: String,
    /// 状态码
    pub status_code: u16,
    /// 响应头
    pub headers: HashMap<String, String>,
    /// 响应体（文本）
    pub text: String,
    /// 响应体（二进制）
    pub bytes: Vec<u8>,
    /// 内容类型
    pub content_type: Option<String>,
    /// 编码
    pub encoding: String,
    /// 请求耗时（毫秒）
    pub elapsed_ms: u64,
    /// 错误信息
    pub error: Option<String>,
}

impl Response {
    /// 创建新响应
    pub fn new(url: impl Into<String>) -> Self {
        Self {
            url: url.into(),
            status_code: 0,
            headers: HashMap::new(),
            text: String::new(),
            bytes: Vec::new(),
            content_type: None,
            encoding: "utf-8".to_string(),
            elapsed_ms: 0,
            error: None,
        }
    }
    
    /// 创建成功响应
    pub fn success(
        url: impl Into<String>,
        status_code: u16,
        text: impl Into<String>,
        elapsed_ms: u64,
    ) -> Self {
        let text = text.into();
        let content_type = Self::extract_content_type(&HashMap::new());
        Self {
            url: url.into(),
            status_code,
            text: text.clone(),
            bytes: text.as_bytes().to_vec(),
            content_type,
            elapsed_ms,
            ..Self::new(url)
        }
    }
    
    /// 创建错误响应
    pub fn error(url: impl Into<String>, error: impl Into<String>) -> Self {
        Self {
            error: Some(error.into()),
            ..Self::new(url)
        }
    }
    
    /// 检查是否成功
    pub fn is_success(&self) -> bool {
        self.status_code >= 200 && self.status_code < 300 && self.error.is_none()
    }
    
    /// 检查是否有错误
    pub fn is_error(&self) -> bool {
        self.error.is_some() || self.status_code >= 400
    }
    
    /// 获取响应头中的内容类型
    fn extract_content_type(headers: &HashMap<String, String>) -> Option<String> {
        headers.get("content-type")
            .or_else(|| headers.get("Content-Type"))
            .cloned()
    }
    
    /// 设置响应头
    pub fn with_headers(mut self, headers: HashMap<String, String>) -> Self {
        self.content_type = Self::extract_content_type(&headers);
        self.headers = headers;
        self
    }
}

impl From<reqwest::Response> for Response {
    fn from(response: reqwest::Response) -> Self {
        let url = response.url().to_string();
        let status_code = response.status().as_u16();
        let headers = response
            .headers()
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
            .collect();
        
        Self {
            url,
            status_code,
            headers,
            ..Self::new("")
        }
    }
}
