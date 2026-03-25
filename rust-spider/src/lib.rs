//! RustSpider - 高性能 Web 爬虫框架
//!
//! # 特性
//!
//! - 🚀 **高性能**: 基于 tokio 异步运行时，支持高并发爬取
//! - 🔒 **内存安全**: Rust 所有权系统保证内存安全
//! - 🛠️ **易于使用**: 简洁的 API，快速上手
//! - 🔄 **可扩展**: 模块化设计，易于扩展
//! - 🖥️ **可视化界面**: Web 控制台用于配置和监控
//! - 📊 **实时监控**: 内置性能指标和健康检查
//!
//! # 快速开始
//!
//! ```rust,no_run
//! use rust_spider::{Spider, Request, Page};
//!
//! #[tokio::main]
//! async fn main() {
//!     let mut spider = Spider::new("example_spider");
//!     spider
//!         .add_start_url("https://example.com")
//!         .set_thread_count(10)
//!         .add_pipeline(|page: &Page| {
//!             println!("URL: {}", page.url);
//!             println!("Title: {:?}", page.title);
//!         });
//!
//!     spider.run().await.unwrap();
//! }
//! ```
//!
//! # 核心组件
//!
//! - [`Spider`]: 爬虫引擎，负责调度和管理整个爬取过程
//! - [`Request`]: 请求对象，包含 URL 和爬取配置
//! - [`Response`]: 响应对象，包含 HTTP 响应数据
//! - [`Page`]: 页面对象，包含解析后的页面数据
//! - [`Pipeline`]: 数据管道，处理爬取结果
//! - [`WebServer`]: Web 服务器，提供可视化界面和 API
//! - [`MetricsCollector`]: 指标收集器，用于性能监控

pub mod core;
pub mod downloader;
pub mod parser;
pub mod scheduler;
pub mod pipeline;
pub mod model;
pub mod proxy;
pub mod distributed;
pub mod error;
pub mod monitor;
pub mod web;

pub use core::Spider;
pub use model::{Request, Response, Page, Site, Config};
pub use downloader::HttpDownloader;
pub use parser::HtmlParser;
pub use scheduler::{Scheduler, QueueScheduler};
pub use pipeline::{Pipeline, ConsolePipeline};
pub use error::{SpiderError, SpiderResult};
pub use monitor::MetricsCollector;
pub use web::WebServer;

/// 框架版本
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// 初始化日志
pub fn init_logging() {
    env_logger::Builder::from_env(
        env_logger::Env::default().default_filter_or("info")
    ).init();
}
