//! rustspider - Rust Web Crawler Framework
//!
//! 核心模块

use std::collections::HashMap;
use std::time::Duration;

/// 爬虫请求
#[derive(Debug, Clone)]
pub struct Request {
    pub url: String,
    pub method: String,
    pub headers: HashMap<String, String>,
    pub body: Option<String>,
    pub meta: HashMap<String, String>,
    pub priority: i32,
}

impl Request {
    /// 创建新请求
    pub fn new(url: String) -> Self {
        Request {
            url,
            method: "GET".to_string(),
            headers: HashMap::new(),
            body: None,
            meta: HashMap::new(),
            priority: 0,
        }
    }

    /// 设置请求头
    pub fn header(mut self, key: &str, value: &str) -> Self {
        self.headers.insert(key.to_string(), value.to_string());
        self
    }

    /// 设置元数据
    pub fn meta(mut self, key: &str, value: &str) -> Self {
        self.meta.insert(key.to_string(), value.to_string());
        self
    }

    /// 设置方法
    pub fn method(mut self, method: &str) -> Self {
        self.method = method.to_string();
        self
    }

    /// 设置请求体
    pub fn body(mut self, body: &str) -> Self {
        self.body = Some(body.to_string());
        self
    }

    /// 设置优先级
    pub fn priority(mut self, priority: i32) -> Self {
        self.priority = priority;
        self
    }
}

/// 爬虫响应
#[derive(Debug)]
pub struct Response {
    pub url: String,
    pub status_code: u16,
    pub headers: HashMap<String, String>,
    pub text: String,
    pub bytes: Vec<u8>,
    pub duration: Duration,
    pub error: Option<String>,
    pub access_friction: Option<crate::antibot::friction::AccessFrictionReport>,
}

/// 页面对象
pub struct Page {
    pub response: Response,
    pub data: HashMap<String, String>,
}

impl Page {
    /// 创建新页面
    pub fn new(response: Response) -> Self {
        Page {
            response,
            data: HashMap::new(),
        }
    }

    /// 设置数据
    pub fn set_data(&mut self, key: &str, value: &str) {
        self.data.insert(key.to_string(), value.to_string());
    }

    /// 获取数据
    pub fn get_data(&self, key: &str) -> Option<&String> {
        self.data.get(key)
    }
}
