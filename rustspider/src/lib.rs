//! rustspider - Rust Web Crawler Framework
//!
//! 功能完整的爬虫框架

pub mod ai;
pub mod async_runtime;
pub mod browser;
pub mod config;
pub mod cookie;
pub mod downloader;
pub mod dynamic;
pub mod enhanced;
pub mod error;
pub mod graph;
pub mod media;
pub mod models;
pub mod parser;
pub mod performance;
pub mod preflight;
pub mod proxy;
pub mod queue;
pub mod retry;
pub mod spider;

// 分布式模块（完整版）
pub mod distributed;

// 监控模块（完整版）
pub mod monitor;

// API 模块（简化版）
pub mod api;

pub mod multithread;
pub mod scheduler;

// 视频下载模块（需要单独创建）
// #[cfg(feature = "video")]
// pub mod video {
//     pub mod hls_downloader;
//     pub mod ffmpeg_tools;
//     pub mod video_parser;
//     pub mod drm_detector;
// }

// CLI（需要 video 特性）
// #[cfg(feature = "video")]
// pub mod cli;

// 基础导出
pub use async_runtime::{DedupQueue, Error as AsyncError, PriorityQueue, Request as AsyncRequest};

#[cfg(feature = "browser")]
pub use browser::{
    BrowserBuilder, BrowserConfig, BrowserError, BrowserManager, FormHandler,
};

pub use config::{CompleteConfig, ConfigLoader};
pub use cookie::{Cookie, CookieJar};
pub use downloader::HTTPDownloader;
pub use dynamic::{DynamicWait, FormInteractor, ScrollLoader};
pub use enhanced::{CrawlStats, VideoItem};
pub use error::{ErrorHandler, ErrorLevel, ErrorType, SpiderError};
pub use graph::{Edge, GraphBuilder, Node};
pub use models::{Page, Request, Response};
pub use parser::{HTMLParser, JSONParser};
pub use performance::{
    AdaptiveRateLimiter, CircuitBreaker, CircuitState, ContentFingerprinter, RateLimiter,
};
pub use preflight::{
    run_preflight, CheckStatus as PreflightCheckStatus, CommandRequirement, PreflightCheck,
    PreflightOptions, PreflightReport,
};
pub use proxy::{Proxy, ProxyPool};
pub use queue::{PersistentPriorityQueue, QueueItem, RetryQueue};
pub use retry::{RetryConfig, RetryHandler, RetryStrategy};
pub use spider::{SimpleSpider, SpiderBuilder, SpiderConfig, SpiderEngine, SpiderStats};

// 分布式简化导出
pub use distributed::redis_distributed::CrawlTask;

// 监控简化导出
pub use monitor::{SpiderMonitor, SpiderStats as MonitorStats};
