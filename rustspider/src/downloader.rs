//! HTTP 下载器

use crate::models::{Request, Response};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};

/// HTTP 下载器
#[derive(Clone)]
pub struct HTTPDownloader {
    client: Arc<reqwest::blocking::Client>,
}

impl HTTPDownloader {
    /// 创建新下载器
    pub fn new() -> Self {
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(30))
            .build()
            .unwrap();

        HTTPDownloader {
            client: Arc::new(client),
        }
    }

    /// 下载页面
    pub fn download(&self, req: &Request) -> Response {
        let start = Instant::now();

        // 创建请求
        let mut req_builder = match req.method.as_str() {
            "POST" => self.client.post(&req.url),
            "PUT" => self.client.put(&req.url),
            "DELETE" => self.client.delete(&req.url),
            _ => self.client.get(&req.url),
        };

        // 设置请求头
        for (key, value) in &req.headers {
            req_builder = req_builder.header(key, value);
        }

        // 设置请求体
        if let Some(body) = &req.body {
            req_builder = req_builder.body(body.clone());
        }

        // 执行请求
        match req_builder.send() {
            Ok(resp) => {
                let status_code = resp.status().as_u16();
                let headers = resp
                    .headers()
                    .iter()
                    .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
                    .collect();

                let bytes = resp.bytes().unwrap_or_default();
                let text = String::from_utf8_lossy(&bytes).to_string();

                Response {
                    url: req.url.clone(),
                    status_code,
                    headers,
                    text,
                    bytes: bytes.to_vec(),
                    duration: start.elapsed(),
                    error: None,
                }
            }
            Err(e) => Response {
                url: req.url.clone(),
                status_code: 0,
                headers: HashMap::new(),
                text: String::new(),
                bytes: Vec::new(),
                duration: start.elapsed(),
                error: Some(e.to_string()),
            },
        }
    }

    /// 设置超时
    pub fn with_timeout(timeout_secs: u64) -> Self {
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(timeout_secs))
            .build()
            .unwrap();

        HTTPDownloader {
            client: Arc::new(client),
        }
    }
}

impl Default for HTTPDownloader {
    fn default() -> Self {
        Self::new()
    }
}
