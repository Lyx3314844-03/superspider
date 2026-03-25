// Rustspider 爬虫核心模块

//! 爬虫核心实现
//!
//! 吸收 Crawlee 的爬虫设计理念

use reqwest::Client;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tokio::time::sleep;

use crate::async_runtime::{DedupQueue, Error, PriorityQueue, Request, RequestQueue};
use crate::graph::GraphBuilder;

/// 爬虫配置
#[derive(Debug, Clone)]
pub struct SpiderConfig {
    pub name: String,
    pub concurrency: usize,
    pub max_requests: usize,
    pub max_depth: usize,
    pub request_timeout: Duration,
    pub retry_count: usize,
    pub user_agent: String,
    pub proxy_url: Option<String>,
    pub delay: Duration,
}

impl Default for SpiderConfig {
    fn default() -> Self {
        Self {
            name: "default".to_string(),
            concurrency: 5,
            max_requests: 1000,
            max_depth: 5,
            request_timeout: Duration::from_secs(30),
            retry_count: 3,
            user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36".to_string(),
            proxy_url: None,
            delay: Duration::from_millis(100),
        }
    }
}

/// 爬虫引擎
pub struct SpiderEngine {
    config: SpiderConfig,
    queue: Arc<DedupQueue>,
    client: Client,
    running: Arc<Mutex<bool>>,
    requested: Arc<Mutex<usize>>,
    handled: Arc<Mutex<usize>>,
    failed: Arc<Mutex<usize>>,
}

impl SpiderEngine {
    /// 创建爬虫引擎
    pub fn new(config: SpiderConfig) -> Self {
        let queue = Arc::new(DedupQueue::new(Arc::new(PriorityQueue::new())));

        let client = Client::builder()
            .timeout(config.request_timeout)
            .user_agent(&config.user_agent)
            .build()
            .unwrap_or_default();

        Self {
            config,
            queue,
            client,
            running: Arc::new(Mutex::new(false)),
            requested: Arc::new(Mutex::new(0)),
            handled: Arc::new(Mutex::new(0)),
            failed: Arc::new(Mutex::new(0)),
        }
    }

    /// 添加请求
    pub fn add_request(&self, request: Request) -> Result<(), Error> {
        self.queue.push(request)
    }

    /// 添加多个请求
    pub fn add_requests(&self, requests: Vec<Request>) -> Result<(), Error> {
        for request in requests {
            self.add_request(request)?;
        }
        Ok(())
    }

    /// 添加 URL
    pub fn add_url(&self, url: &str) -> Result<(), Error> {
        let request = Request::new(url.to_string());
        self.add_request(request)
    }

    /// 运行爬虫
    pub async fn run(&self) -> Result<(), Error> {
        {
            let mut running = self.running.lock().unwrap();
            if *running {
                return Err(Error::new("Spider is already running"));
            }
            *running = true;
        }

        // 启动工作线程
        let mut handles = Vec::new();

        for i in 0..self.config.concurrency {
            let queue = Arc::clone(&self.queue);
            let client = self.client.clone();
            let running = Arc::clone(&self.running);
            let requested = Arc::clone(&self.requested);
            let handled = Arc::clone(&self.handled);
            let failed = Arc::clone(&self.failed);
            let max_requests = self.config.max_requests;
            let delay = self.config.delay;

            let handle = tokio::spawn(async move {
                while let Some(request) = queue.pop() {
                    // 检查是否停止
                    {
                        let running = running.lock().unwrap();
                        if !*running {
                            break;
                        }
                    }

                    // 检查是否达到最大请求数
                    {
                        let req = requested.lock().unwrap();
                        if *req >= max_requests {
                            break;
                        }
                    }

                    // 执行请求
                    println!("Worker {} processing: {}", i, request.url);

                    // 延迟
                    sleep(delay).await;

                    // 发送 HTTP 请求
                    match client.get(&request.url).send().await {
                        Ok(response) => {
                            println!("Worker {} got response: {}", i, response.status());
                            *handled.lock().unwrap() += 1;
                        }
                        Err(e) => {
                            eprintln!("Worker {} error: {}", i, e);
                            *failed.lock().unwrap() += 1;
                        }
                    }

                    *requested.lock().unwrap() += 1;
                }
            });

            handles.push(handle);
        }

        // 等待所有工作线程完成
        for handle in handles {
            let _ = handle.await;
        }

        {
            let mut running = self.running.lock().unwrap();
            *running = false;
        }

        Ok(())
    }

    /// 停止爬虫
    pub fn stop(&self) -> Result<(), Error> {
        let mut running = self.running.lock().unwrap();
        *running = false;
        Ok(())
    }

    /// 是否运行中
    pub fn is_running(&self) -> bool {
        let running = self.running.lock().unwrap();
        *running
    }

    /// 获取统计信息
    pub fn get_stats(&self) -> SpiderStats {
        SpiderStats {
            name: self.config.name.clone(),
            running: self.is_running(),
            requested: *self.requested.lock().unwrap(),
            handled: *self.handled.lock().unwrap(),
            failed: *self.failed.lock().unwrap(),
            queue_size: self.queue.size(),
        }
    }
}

/// 爬虫统计信息
#[derive(Debug, Clone)]
pub struct SpiderStats {
    pub name: String,
    pub running: bool,
    pub requested: usize,
    pub handled: usize,
    pub failed: usize,
    pub queue_size: usize,
}

impl std::fmt::Display for SpiderStats {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(
            f,
            "SpiderStats {{ name: {}, running: {}, requested: {}, handled: {}, failed: {}, queue_size: {} }}",
            self.name, self.running, self.requested, self.handled, self.failed, self.queue_size
        )
    }
}

/// 爬虫构建器
pub struct SpiderBuilder {
    config: SpiderConfig,
}

impl SpiderBuilder {
    /// 创建构建器
    pub fn new() -> Self {
        Self {
            config: SpiderConfig::default(),
        }
    }

    /// 设置名称
    pub fn name(mut self, name: &str) -> Self {
        self.config.name = name.to_string();
        self
    }

    /// 设置并发数
    pub fn concurrency(mut self, concurrency: usize) -> Self {
        self.config.concurrency = concurrency;
        self
    }

    /// 设置最大请求数
    pub fn max_requests(mut self, max_requests: usize) -> Self {
        self.config.max_requests = max_requests;
        self
    }

    /// 设置最大深度
    pub fn max_depth(mut self, max_depth: usize) -> Self {
        self.config.max_depth = max_depth;
        self
    }

    /// 设置请求超时
    pub fn request_timeout(mut self, timeout: Duration) -> Self {
        self.config.request_timeout = timeout;
        self
    }

    /// 设置重试次数
    pub fn retry_count(mut self, retry_count: usize) -> Self {
        self.config.retry_count = retry_count;
        self
    }

    /// 设置 User-Agent
    pub fn user_agent(mut self, user_agent: &str) -> Self {
        self.config.user_agent = user_agent.to_string();
        self
    }

    /// 设置代理
    pub fn proxy(mut self, proxy_url: &str) -> Self {
        self.config.proxy_url = Some(proxy_url.to_string());
        self
    }

    /// 设置延迟
    pub fn delay(mut self, delay: Duration) -> Self {
        self.config.delay = delay;
        self
    }

    /// 构建爬虫引擎
    pub fn build(self) -> SpiderEngine {
        SpiderEngine::new(self.config)
    }
}

impl Default for SpiderBuilder {
    fn default() -> Self {
        Self::new()
    }
}

/// 简单爬虫
pub struct SimpleSpider {
    config: SpiderConfig,
    graph: GraphBuilder,
}

impl SimpleSpider {
    /// 创建简单爬虫
    pub fn new(config: SpiderConfig) -> Self {
        Self {
            config,
            graph: GraphBuilder::new(),
        }
    }

    /// 爬取 URL
    pub async fn crawl(&mut self, url: &str) -> Result<(), Error> {
        println!("Crawling: {}", url);

        // 创建请求
        let request = Request::new(url.to_string());

        // 发送请求
        let client = Client::builder()
            .timeout(self.config.request_timeout)
            .user_agent(&self.config.user_agent)
            .build()
            .unwrap_or_default();

        match client.get(&request.url).send().await {
            Ok(response) => {
                println!("Got response: {}", response.status());

                // 获取 HTML
                if let Ok(html) = response.text().await {
                    // 构建图结构
                    // TODO: 解析 HTML 并添加到图中
                    println!("Received {} bytes", html.len());
                }
            }
            Err(e) => {
                eprintln!("Error: {}", e);
                return Err(Error::new(&format!("Request failed: {}", e)));
            }
        }

        Ok(())
    }

    /// 获取图结构
    pub fn get_graph(&self) -> &GraphBuilder {
        &self.graph
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_spider_engine() {
        let config = SpiderConfig {
            name: "test".to_string(),
            concurrency: 2,
            max_requests: 10,
            ..Default::default()
        };

        let engine = SpiderEngine::new(config);

        // 添加请求
        engine.add_url("https://example.com").unwrap();
        engine.add_url("https://httpbin.org/get").unwrap();

        // 运行爬虫
        let result = engine.run().await;
        assert!(result.is_ok());

        // 获取统计
        let stats = engine.get_stats();
        println!("Stats: {}", stats);
    }

    #[tokio::test]
    async fn test_simple_spider() {
        let config = SpiderConfig::default();
        let mut spider = SimpleSpider::new(config);

        let result = spider.crawl("https://example.com").await;
        assert!(result.is_ok());
    }
}
