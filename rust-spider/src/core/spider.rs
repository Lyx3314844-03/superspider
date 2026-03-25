//! Spider 爬虫引擎
//!
//! 核心爬虫引擎，负责调度、管理和执行整个爬取过程

use std::sync::Arc;
use tokio::sync::{mpsc, Mutex, RwLock};
use tokio::signal;
use log::{info, debug, error, warn};

use crate::model::{Request, Response, Page, Site, Config};
use crate::downloader::HttpDownloader;
use crate::scheduler::{Scheduler, QueueScheduler};
use crate::pipeline::Pipeline;
use crate::monitor::MetricsCollector;

/// 页面处理函数类型
pub type PageHandler = Arc<dyn Fn(&Page) + Send + Sync + 'static>;

/// 爬虫引擎
/// 
/// # Examples
/// 
/// ```rust,no_run
/// use rust_spider::Spider;
/// 
/// #[tokio::main]
/// async fn main() {
///     let mut spider = Spider::new("example");
///     spider
///         .add_start_url("https://example.com")
///         .set_thread_count(10);
///
///     spider.run().await.unwrap();
/// }
/// ```
pub struct Spider {
    /// 配置
    config: Config,
    /// 站点配置
    site: Site,
    /// 下载器
    downloader: HttpDownloader,
    /// 调度器
    scheduler: Arc<Mutex<QueueScheduler>>,
    /// 数据管道
    pipelines: Vec<Arc<dyn Pipeline>>,
    /// 页面处理器
    handlers: Vec<PageHandler>,
    /// 运行状态
    running: Arc<RwLock<bool>>,
    /// 已爬取页面数
    crawled_count: Arc<RwLock<u32>>,
    /// 指标收集器
    metrics: Option<MetricsCollector>,
    /// 关闭信号
    shutdown: Arc<tokio::sync::Notify>,
}

impl Spider {
    /// 创建新爬虫
    ///
    /// # Arguments
    ///
    /// * `name` - 爬虫名称
    ///
    /// # Examples
    ///
    /// ```
    /// use rust_spider::Spider;
    ///
    /// let spider = Spider::new("my_spider");
    /// ```
    pub fn new(name: impl Into<String>) -> Self {
        let config = Config::new(name);
        Self::with_config(config)
    }

    /// 使用配置创建爬虫
    pub fn with_config(config: Config) -> Self {
        let thread_count = config.thread_count;
        Self {
            config,
            site: Site::new(),
            downloader: HttpDownloader::new(),
            scheduler: Arc::new(Mutex::new(QueueScheduler::new(thread_count))),
            pipelines: Vec::new(),
            handlers: Vec::new(),
            running: Arc::new(RwLock::new(false)),
            crawled_count: Arc::new(RwLock::new(0)),
            metrics: None,
            shutdown: Arc::new(tokio::sync::Notify::new()),
        }
    }
    
    /// 设置指标收集器
    pub fn with_metrics(mut self, metrics: MetricsCollector) -> Self {
        self.metrics = Some(metrics);
        self
    }
    
    /// 添加起始 URL
    /// 
    /// # Examples
    /// 
    /// ```
    /// use rust_spider::Spider;
    /// 
    /// let mut spider = Spider::new("example")
    ///     .add_start_url("https://example.com")
    ///     .add_start_url("https://example.com/page2");
    /// ```
    pub fn add_start_url(mut self, url: impl Into<String>) -> Self {
        self.site = self.site.add_start_url(url);
        self
    }
    
    /// 添加多个起始 URL
    pub fn add_start_urls(mut self, urls: Vec<String>) -> Self {
        self.site = self.site.add_start_urls(urls);
        self
    }
    
    /// 设置线程数
    pub fn set_thread_count(mut self, count: usize) -> Self {
        self.config.thread_count = count;
        self
    }
    
    /// 设置用户代理
    pub fn set_user_agent(mut self, ua: impl Into<String>) -> Self {
        self.site = self.site.set_user_agent(ua);
        self
    }
    
    /// 设置请求间隔（毫秒）
    pub fn set_sleep_time(mut self, ms: u64) -> Self {
        self.site = self.site.set_sleep_time(ms);
        self
    }
    
    /// 设置重试次数
    pub fn set_retry_times(mut self, times: u32) -> Self {
        self.site = self.site.set_retry_times(times);
        self
    }
    
    /// 添加数据管道
    pub fn add_pipeline<P: Pipeline + 'static>(mut self, pipeline: P) -> Self {
        self.pipelines.push(Arc::new(pipeline));
        self
    }
    
    /// 添加页面处理器
    pub fn add_handler<F>(mut self, handler: F) -> Self 
    where
        F: Fn(&Page) + Send + Sync + 'static,
    {
        self.handlers.push(Arc::new(handler));
        self
    }
    
    /// 设置站点配置
    pub fn site(mut self, site: Site) -> Self {
        self.site = site;
        self
    }
    
    /// 运行爬虫
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use rust_spider::Spider;
    ///
    /// #[tokio::main]
    /// async fn main() {
    ///     let mut spider = Spider::new("example")
    ///         .add_start_url("https://example.com");
    ///
    ///     spider.run().await.unwrap();
    /// }
    /// ```
    pub async fn run(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        info!("Starting spider: {}", self.config.name);

        // 初始化日志
        if std::env::var("RUST_LOG").is_err() {
            std::env::set_var("RUST_LOG", &self.config.log_level);
        }
        env_logger::try_init().ok();

        // 启动指标收集
        if let Some(metrics) = &self.metrics {
            metrics.start();
        }

        // 添加起始请求
        for url in &self.site.start_urls {
            let request = Request::new(url.clone());
            let mut scheduler = self.scheduler.lock().await;
            scheduler.add_request(request, None)?;
        }

        // 设置运行状态
        {
            let mut running = self.running.write().await;
            *running = true;
        }

        let shutdown = self.shutdown.clone();
        
        // 创建工作线程
        let mut handles = Vec::new();

        for i in 0..self.config.thread_count {
            let scheduler = Arc::clone(&self.scheduler);
            let downloader = self.downloader.clone();
            let pipelines = self.pipelines.clone();
            let handlers = self.handlers.clone();
            let running = Arc::clone(&self.running);
            let crawled_count = Arc::clone(&self.crawled_count);
            let sleep_time = self.site.sleep_time_ms;
            let metrics = self.metrics.clone();
            let shutdown = shutdown.clone();

            let handle = tokio::spawn(async move {
                Self::worker(
                    i,
                    scheduler,
                    downloader,
                    pipelines,
                    handlers,
                    running,
                    crawled_count,
                    sleep_time,
                    metrics,
                    shutdown,
                ).await
            });

            handles.push(handle);
        }

        // 等待关闭信号或所有任务完成
        let shutdown_wait = tokio::spawn(async move {
            shutdown.notified().await;
        });

        tokio::select! {
            _ = shutdown_wait => {
                info!("Received shutdown signal");
            }
            _ = async {
                for handle in handles {
                    let _ = handle.await;
                }
            } => {
                info!("All workers completed");
            }
            _ = signal::ctrl_c() => {
                info!("Received Ctrl+C, shutting down gracefully...");
            }
        }

        // 设置运行状态为 false
        {
            let mut running = self.running.write().await;
            *running = false;
        }
        
        // 停止指标收集
        if let Some(metrics) = &self.metrics {
            metrics.stop();
            metrics.print_summary();
        }

        let count = *self.crawled_count.read().await;
        info!("Spider finished: {} crawled {} pages", self.config.name, count);

        Ok(())
    }
    
    /// 优雅关闭
    pub async fn shutdown(&self) {
        info!("Initiating graceful shutdown...");
        self.shutdown.notify_one();
        
        // 等待运行状态变为 false
        while *self.running.read().await {
            tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
        }
        
        info!("Graceful shutdown complete");
    }

    /// 工作线程
    async fn worker(
        worker_id: usize,
        scheduler: Arc<Mutex<QueueScheduler>>,
        downloader: HttpDownloader,
        pipelines: Vec<Arc<dyn Pipeline>>,
        handlers: Vec<PageHandler>,
        running: Arc<RwLock<bool>>,
        crawled_count: Arc<RwLock<u32>>,
        sleep_time: u64,
        metrics: Option<MetricsCollector>,
        _shutdown: Arc<tokio::sync::Notify>,
    ) {
        debug!("Worker {} started", worker_id);

        loop {
            // 检查运行状态
            {
                let running = running.read().await;
                if !*running {
                    break;
                }
            }

            // 获取请求
            let request = {
                let mut scheduler = scheduler.lock().await;
                match scheduler.poll().await {
                    Ok(Some(req)) => Some(req),
                    Ok(None) => None,
                    Err(e) => {
                        error!("Worker {} scheduler error: {}", worker_id, e);
                        None
                    }
                }
            };

            match request {
                Some(req) => {
                    // 下载页面
                    let url = req.url.clone();
                    debug!("Worker {} crawling: {}", worker_id, url);

                    match downloader.download(&req).await {
                        Ok(response) => {
                            // 记录指标
                            if let Some(m) = &metrics {
                                m.record_page(
                                    response.elapsed_ms,
                                    response.bytes.len() as u64,
                                    response.is_success(),
                                );
                            }
                            
                            // 创建页面
                            let mut page = Page::from_response(response);

                            // 执行处理器
                            for handler in &handlers {
                                handler(&page);
                            }

                            // 执行管道
                            for pipeline in &pipelines {
                                if let Err(e) = pipeline.process(&mut page) {
                                    error!("Pipeline error: {}", e);
                                }
                            }

                            // 更新计数
                            {
                                let mut count = crawled_count.write().await;
                                *count += 1;
                            }
                            
                            // 添加新发现的链接
                            {
                                let mut scheduler = scheduler.lock().await;
                                for target_url in &page.target_urls {
                                    let new_request = Request::new(target_url.clone());
                                    let _ = scheduler.add_request(new_request, Some(req.clone()));
                                }
                            }
                        }
                        Err(e) => {
                            error!("Worker {} download error: {}", worker_id, e);
                        }
                    }
                    
                    // 睡眠
                    if sleep_time > 0 {
                        tokio::time::sleep(tokio::time::Duration::from_millis(sleep_time)).await;
                    }
                }
                None => {
                    // 没有请求，等待
                    tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
                }
            }
        }
        
        debug!("Worker {} finished", worker_id);
    }
    
    /// 停止爬虫
    pub async fn stop(&self) {
        let mut running = self.running.write().await;
        *running = false;
        info!("Stopping spider: {}", self.config.name);
    }
    
    /// 检查是否运行中
    pub async fn is_running(&self) -> bool {
        *self.running.read().await
    }
    
    /// 获取已爬取页面数
    pub async fn crawled_count(&self) -> u32 {
        *self.crawled_count.read().await
    }
}

impl Default for Spider {
    fn default() -> Self {
        Self::new("default")
    }
}
