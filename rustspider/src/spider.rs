// Rustspider 爬虫核心模块

//! 爬虫核心实现
//!
//! 吸收 Crawlee 的爬虫设计理念

use reqwest::Client;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tokio::time::sleep;

use crate::async_runtime::{Error, Request as AsyncRequest};
use crate::contracts::{
    AutoscaledFrontier, FileArtifactStore, FrontierConfig, ObservabilityCollector,
};
use crate::graph::GraphBuilder;
use crate::models::Request as CoreRequest;

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
    frontier: Arc<Mutex<AutoscaledFrontier>>,
    observability: Arc<Mutex<ObservabilityCollector>>,
    artifact_store: Arc<Mutex<FileArtifactStore>>,
    client: Client,
    running: Arc<Mutex<bool>>,
    requested: Arc<Mutex<usize>>,
    handled: Arc<Mutex<usize>>,
    failed: Arc<Mutex<usize>>,
}

impl SpiderEngine {
    /// 创建爬虫引擎
    pub fn new(config: SpiderConfig) -> Result<Self, Error> {
        let client = Client::builder()
            .timeout(config.request_timeout)
            .user_agent(&config.user_agent)
            .build()
            .map_err(|e| Error::new(&format!("Failed to build HTTP client: {}", e)))?;

        Ok(Self {
            config,
            frontier: Arc::new(Mutex::new(AutoscaledFrontier::new(
                FrontierConfig::default(),
            ))),
            observability: Arc::new(Mutex::new(ObservabilityCollector::default())),
            artifact_store: Arc::new(Mutex::new(FileArtifactStore::new(
                "artifacts/observability",
            ))),
            client,
            running: Arc::new(Mutex::new(false)),
            requested: Arc::new(Mutex::new(0)),
            handled: Arc::new(Mutex::new(0)),
            failed: Arc::new(Mutex::new(0)),
        })
    }

    /// 添加请求
    pub fn add_request(&self, request: AsyncRequest) -> Result<(), Error> {
        self.frontier
            .lock()
            .map_err(|_| Error::new("Frontier lock poisoned"))?
            .push(core_request_from_async(&request));
        Ok(())
    }

    /// 添加多个请求
    pub fn add_requests(&self, requests: Vec<AsyncRequest>) -> Result<(), Error> {
        for request in requests {
            self.add_request(request)?;
        }
        Ok(())
    }

    /// 添加 URL
    pub fn add_url(&self, url: &str) -> Result<(), Error> {
        let request = AsyncRequest::new(url.to_string());
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
        {
            let should_load = self
                .frontier
                .lock()
                .map_err(|_| Error::new("Frontier lock poisoned"))?
                .snapshot()
                .get("pending")
                .and_then(|value| value.as_array())
                .map(|items| items.is_empty())
                .unwrap_or(true);
            if should_load {
                let _ = self
                    .frontier
                    .lock()
                    .map_err(|_| Error::new("Frontier lock poisoned"))?
                    .load();
            }
        }

        // 启动工作线程
        let mut handles = Vec::new();
        let worker_count = self
            .frontier
            .lock()
            .map_err(|_| Error::new("Frontier lock poisoned"))?
            .recommended_concurrency()
            .max(1)
            .min(self.config.concurrency.max(1));

        for i in 0..worker_count {
            let frontier = Arc::clone(&self.frontier);
            let observability = Arc::clone(&self.observability);
            let client = self.client.clone();
            let running = Arc::clone(&self.running);
            let requested = Arc::clone(&self.requested);
            let handled = Arc::clone(&self.handled);
            let failed = Arc::clone(&self.failed);
            let max_requests = self.config.max_requests;
            let delay = self.config.delay;

            let handle = tokio::spawn(async move {
                loop {
                    let request = {
                        let mut frontier = frontier.lock().unwrap();
                        frontier
                            .lease()
                            .map(|request| async_request_from_core(&request))
                    };
                    let Some(request) = request else {
                        let pending = {
                            let frontier = frontier.lock().unwrap();
                            frontier
                                .snapshot()
                                .get("pending")
                                .and_then(|value| value.as_array())
                                .map(|items| items.len())
                                .unwrap_or_default()
                        };
                        if pending == 0 {
                            break;
                        }
                        sleep(Duration::from_millis(50)).await;
                        continue;
                    };
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
                    let trace_id = {
                        let mut collector = observability.lock().unwrap();
                        collector.start_trace("spider.request")
                    };
                    let started_at = std::time::Instant::now();

                    // 延迟
                    sleep(delay).await;

                    // 发送 HTTP 请求
                    match client.get(&request.url).send().await {
                        Ok(response) => {
                            println!("Worker {} got response: {}", i, response.status());
                            let status = response.status().as_u16();

                            // 读取响应 Body 以释放连接
                            if let Err(e) = response.bytes().await {
                                eprintln!("Worker {} failed to read response body: {}", i, e);
                                {
                                    let mut frontier = frontier.lock().unwrap();
                                    frontier.ack(
                                        &core_request_from_async(&request),
                                        false,
                                        started_at.elapsed().as_millis() as f64,
                                        Some(&e.to_string()),
                                        Some(status),
                                        3,
                                    );
                                }
                                {
                                    let mut collector = observability.lock().unwrap();
                                    collector.record_result(
                                        Some(&core_request_from_async(&request)),
                                        started_at.elapsed().as_millis() as f64,
                                        Some(status),
                                        Some(&e.to_string()),
                                        Some(trace_id.clone()),
                                    );
                                    collector.end_trace(
                                        &trace_id,
                                        std::collections::BTreeMap::from([(
                                            "status".to_string(),
                                            serde_json::Value::String("failed".to_string()),
                                        )]),
                                    );
                                }
                                *failed.lock().unwrap() += 1;
                                *requested.lock().unwrap() += 1;
                                continue;
                            }

                            *handled.lock().unwrap() += 1;
                            {
                                let mut frontier = frontier.lock().unwrap();
                                frontier.ack(
                                    &core_request_from_async(&request),
                                    true,
                                    started_at.elapsed().as_millis() as f64,
                                    None,
                                    Some(status),
                                    3,
                                );
                            }
                            {
                                let mut collector = observability.lock().unwrap();
                                collector.record_result(
                                    Some(&core_request_from_async(&request)),
                                    started_at.elapsed().as_millis() as f64,
                                    Some(status),
                                    None,
                                    Some(trace_id.clone()),
                                );
                                collector.end_trace(
                                    &trace_id,
                                    std::collections::BTreeMap::from([(
                                        "status".to_string(),
                                        serde_json::Value::String("ok".to_string()),
                                    )]),
                                );
                            }
                        }
                        Err(e) => {
                            eprintln!("Worker {} error: {}", i, e);
                            *failed.lock().unwrap() += 1;
                            {
                                let mut frontier = frontier.lock().unwrap();
                                frontier.ack(
                                    &core_request_from_async(&request),
                                    false,
                                    started_at.elapsed().as_millis() as f64,
                                    Some(&e.to_string()),
                                    None,
                                    3,
                                );
                            }
                            {
                                let mut collector = observability.lock().unwrap();
                                collector.record_result(
                                    Some(&core_request_from_async(&request)),
                                    started_at.elapsed().as_millis() as f64,
                                    None,
                                    Some(&e.to_string()),
                                    Some(trace_id.clone()),
                                );
                                collector.end_trace(
                                    &trace_id,
                                    std::collections::BTreeMap::from([(
                                        "status".to_string(),
                                        serde_json::Value::String("failed".to_string()),
                                    )]),
                                );
                            }
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
        {
            let frontier_snapshot = self
                .frontier
                .lock()
                .map_err(|_| Error::new("Frontier lock poisoned"))?
                .snapshot();
            let observability_summary = self
                .observability
                .lock()
                .map_err(|_| Error::new("Observability lock poisoned"))?
                .summary();
            let store = self
                .artifact_store
                .lock()
                .map_err(|_| Error::new("Artifact store lock poisoned"))?;
            let _ = self
                .frontier
                .lock()
                .map_err(|_| Error::new("Frontier lock poisoned"))?
                .persist();
            let _ = store.put_bytes(
                &format!("{}-frontier", self.config.name),
                "json",
                serde_json::to_vec_pretty(&frontier_snapshot)
                    .unwrap_or_default()
                    .as_slice(),
                HashMap::new(),
            );
            let _ = store.put_bytes(
                &format!("{}-observability", self.config.name),
                "json",
                serde_json::to_vec_pretty(&observability_summary)
                    .unwrap_or_default()
                    .as_slice(),
                HashMap::new(),
            );
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
        let frontier_snapshot = self
            .frontier
            .lock()
            .ok()
            .map(|frontier| frontier.snapshot())
            .unwrap_or(serde_json::Value::Null);
        let observability_summary = self
            .observability
            .lock()
            .ok()
            .map(|collector| collector.summary())
            .unwrap_or(serde_json::Value::Null);
        let queue_size = frontier_snapshot
            .get("pending")
            .and_then(|value| value.as_array())
            .map(|items| items.len())
            .unwrap_or_default();
        SpiderStats {
            name: self.config.name.clone(),
            running: self.is_running(),
            requested: *self.requested.lock().unwrap(),
            handled: *self.handled.lock().unwrap(),
            failed: *self.failed.lock().unwrap(),
            queue_size,
            recommended_concurrency: frontier_snapshot
                .get("recommended_concurrency")
                .and_then(|value| value.as_u64())
                .unwrap_or_default() as usize,
            dead_letters: frontier_snapshot
                .get("dead_letters")
                .and_then(|value| value.as_array())
                .map(|items| items.len())
                .unwrap_or_default(),
            observability_events: observability_summary
                .get("events")
                .and_then(|value| value.as_u64())
                .unwrap_or_default() as usize,
            observability_traces: observability_summary
                .get("traces")
                .and_then(|value| value.as_u64())
                .unwrap_or_default() as usize,
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
    pub recommended_concurrency: usize,
    pub dead_letters: usize,
    pub observability_events: usize,
    pub observability_traces: usize,
}

impl std::fmt::Display for SpiderStats {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(
            f,
            "SpiderStats {{ name: {}, running: {}, requested: {}, handled: {}, failed: {}, queue_size: {}, recommended_concurrency: {}, dead_letters: {}, observability_events: {}, observability_traces: {} }}",
            self.name, self.running, self.requested, self.handled, self.failed, self.queue_size, self.recommended_concurrency, self.dead_letters, self.observability_events, self.observability_traces
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
    pub fn build(self) -> Result<SpiderEngine, Error> {
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
        let request = AsyncRequest::new(url.to_string());

        // 发送请求
        let client = Client::builder()
            .timeout(self.config.request_timeout)
            .user_agent(&self.config.user_agent)
            .build()
            .map_err(|e| Error::new(&format!("Failed to build HTTP client: {}", e)))?;

        match client.get(&request.url).send().await {
            Ok(response) => {
                println!("Got response: {}", response.status());

                // 获取 HTML
                if let Ok(html) = response.text().await {
                    self.graph.rebuild_from_html(&html);
                    let stats = self.graph.stats();
                    println!("Received {} bytes", html.len());
                    println!(
                        "Graph extracted nodes={}, links={}, images={}",
                        stats.get("total_nodes").copied().unwrap_or_default(),
                        self.graph.get_links().len(),
                        self.graph.get_images().len(),
                    );
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

fn core_request_from_async(request: &AsyncRequest) -> CoreRequest {
    let mut req = CoreRequest::new(request.url.clone());
    req.method = request.method.clone();
    req.headers = request.headers.clone();
    req.priority = request.priority;
    req.meta = request.meta.clone();
    req
}

fn async_request_from_core(request: &CoreRequest) -> AsyncRequest {
    let mut req = AsyncRequest::new(request.url.clone());
    req.method = request.method.clone();
    req.headers = request.headers.clone();
    req.priority = request.priority;
    req.meta = request.meta.clone();
    req
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

        let engine = SpiderEngine::new(config).expect("Failed to create spider engine");

        // 添加请求
        engine.add_url("https://example.com").unwrap();
        engine.add_url("https://httpbin.org/get").unwrap();

        // 运行爬虫
        let result = engine.run().await;
        assert!(result.is_ok());

        // 获取统计
        let stats = engine.get_stats();
        println!("Stats: {}", stats);
        assert!(stats.observability_events >= 2);
    }

    #[tokio::test]
    async fn test_simple_spider() {
        let config = SpiderConfig::default();
        let mut spider = SimpleSpider::new(config);

        let result = spider.crawl("https://example.com").await;
        assert!(result.is_ok());
    }
}
