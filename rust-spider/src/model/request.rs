//! 请求对象
//! 
//! 表示一个待爬取的请求，包含 URL、优先级、回调函数等信息

use std::collections::HashMap;
use serde::{Deserialize, Serialize};

/// 请求优先级
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Priority {
    Low = 0,
    Normal = 1,
    High = 2,
}

impl Default for Priority {
    fn default() -> Self {
        Priority::Normal
    }
}

/// 请求对象
/// 
/// 表示一个待爬取的 HTTP 请求
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Request {
    /// 请求 URL
    pub url: String,
    /// 请求方法
    pub method: String,
    /// 请求头
    pub headers: HashMap<String, String>,
    /// 请求体
    pub body: Option<String>,
    /// 优先级
    pub priority: Priority,
    /// 元数据
    pub meta: HashMap<String, String>,
    /// 回调函数名称
    pub callback: Option<String>,
    /// 是否去重
    pub deduplicate: bool,
    /// 重试次数
    pub retry_times: u32,
    /// 最大重试次数
    pub max_retry_times: u32,
}

impl Request {
    /// 创建新请求
    /// 
    /// # Examples
    /// 
    /// ```
    /// use rust_spider::Request;
    /// 
    /// let request = Request::new("https://example.com");
    /// ```
    pub fn new(url: impl Into<String>) -> Self {
        Self {
            url: url.into(),
            method: "GET".to_string(),
            headers: HashMap::new(),
            body: None,
            priority: Priority::Normal,
            meta: HashMap::new(),
            callback: None,
            deduplicate: true,
            retry_times: 0,
            max_retry_times: 3,
        }
    }
    
    /// 创建带回调的请求
    pub fn with_callback(url: impl Into<String>, callback: impl Into<String>) -> Self {
        Self {
            callback: Some(callback.into()),
            ..Self::new(url)
        }
    }
    
    /// 设置请求方法
    pub fn with_method(mut self, method: impl Into<String>) -> Self {
        self.method = method.into();
        self
    }
    
    /// 设置请求头
    pub fn with_header(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.headers.insert(key.into(), value.into());
        self
    }
    
    /// 设置请求体
    pub fn with_body(mut self, body: impl Into<String>) -> Self {
        self.body = Some(body.into());
        self
    }
    
    /// 设置优先级
    pub fn with_priority(mut self, priority: Priority) -> Self {
        self.priority = priority;
        self
    }
    
    /// 设置元数据
    pub fn with_meta(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.meta.insert(key.into(), value.into());
        self
    }
    
    /// 设置回调函数名称
    pub fn with_callback(mut self, callback: impl Into<String>) -> Self {
        self.callback = Some(callback.into());
        self
    }
    
    /// 设置是否去重
    pub fn with_deduplicate(mut self, deduplicate: bool) -> Self {
        self.deduplicate = deduplicate;
        self
    }
    
    /// 获取 URL 的哈希值，用于去重
    pub fn fingerprint(&self) -> String {
        format!("{:x}", md5::compute(&self.url))
    }
}

impl From<&str> for Request {
    fn from(url: &str) -> Self {
        Request::new(url)
    }
}

impl From<String> for Request {
    fn from(url: String) -> Self {
        Request::new(url)
    }
}
