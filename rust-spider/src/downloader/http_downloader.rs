//! HTTP 下载器
//! 
//! 基于 reqwest 的异步 HTTP 下载器

use std::time::Instant;
use log::debug;
use reqwest::{Client, Response as ReqwestResponse};

use crate::model::{Request, Response};

/// HTTP 下载器
/// 
/// 用于下载 HTTP/HTTPS 页面
#[derive(Clone)]
pub struct HttpDownloader {
    client: Client,
}

impl HttpDownloader {
    /// 创建新下载器
    pub fn new() -> Self {
        let client = Client::builder()
            .pool_max_idle_per_host(10)
            .connect_timeout(std::time::Duration::from_secs(10))
            .timeout(std::time::Duration::from_secs(30))
            .redirect(reqwest::redirect::Policy::limited(10))
            .build()
            .expect("Failed to create HTTP client");
        
        Self { client }
    }
    
    /// 创建带自定义配置的下载器
    pub fn with_config(
        timeout_secs: u64,
        max_redirects: usize,
        user_agent: &str,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        let client = Client::builder()
            .pool_max_idle_per_host(10)
            .connect_timeout(std::time::Duration::from_secs(10))
            .timeout(std::time::Duration::from_secs(timeout_secs))
            .redirect(reqwest::redirect::Policy::limited(max_redirects))
            .user_agent(user_agent)
            .build()?;
        
        Ok(Self { client })
    }
    
    /// 下载页面
    /// 
    /// # Arguments
    /// 
    /// * `request` - 请求对象
    /// 
    /// # Returns
    /// 
    /// 返回响应对象或错误
    pub async fn download(&self, request: &Request) -> Result<Response, Box<dyn std::error::Error>> {
        debug!("Downloading: {}", request.url);
        
        let start_time = Instant::now();
        
        // 构建请求
        let mut req_builder = match request.method.as_str() {
            "GET" => self.client.get(&request.url),
            "POST" => self.client.post(&request.url),
            "PUT" => self.client.put(&request.url),
            "DELETE" => self.client.delete(&request.url),
            "HEAD" => self.client.head(&request.url),
            "PATCH" => self.client.patch(&request.url),
            _ => self.client.get(&request.url),
        };
        
        // 添加请求头
        for (key, value) in &request.headers {
            req_builder = req_builder.header(key, value);
        }
        
        // 添加请求体
        if let Some(body) = &request.body {
            req_builder = req_builder.body(body.clone());
        }
        
        // 发送请求
        let response = req_builder.send().await?;
        
        // 检查状态码
        let status_code = response.status().as_u16();
        
        // 获取响应头
        let headers = response
            .headers()
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
            .collect();
        
        // 获取响应体
        let bytes = response.bytes().await?;
        let text = String::from_utf8_lossy(&bytes).to_string();
        
        let elapsed = start_time.elapsed().as_millis() as u64;
        
        debug!("Downloaded: {} (Status: {}, Time: {}ms)", request.url, status_code, elapsed);
        
        Ok(Response {
            url: request.url.clone(),
            status_code,
            headers,
            text,
            bytes: bytes.to_vec(),
            content_type: headers.get("content-type").cloned(),
            encoding: "utf-8".to_string(),
            elapsed_ms: elapsed,
            error: None,
        })
    }
    
    /// 批量下载
    pub async fn download_batch(
        &self,
        requests: Vec<Request>,
    ) -> Vec<Result<Response, Box<dyn std::error::Error>>> {
        let futures: Vec<_> = requests
            .iter()
            .map(|req| self.download(req))
            .collect();
        
        futures::future::join_all(futures).await
    }
}

impl Default for HttpDownloader {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_download() {
        let downloader = HttpDownloader::new();
        let request = Request::new("https://httpbin.org/html");
        
        let response = downloader.download(&request).await;
        
        assert!(response.is_ok());
        let response = response.unwrap();
        assert_eq!(response.status_code, 200);
        assert!(!response.text.is_empty());
    }
}
