#![allow(dead_code)]
#![allow(unused_variables)]

//! rustspider - Rust Web Crawler Framework
//!
//! 功能完整的爬虫框架

pub mod ai;
pub mod antibot; // 反爬模块
pub mod artifact;
pub mod async_research;
pub mod async_runtime;
pub mod audit;
pub mod behavior;
pub mod browser;
pub mod connector;
pub mod cookie;
pub mod dedup;
pub mod downloader;
pub mod dynamic;
pub mod enhanced;
pub mod error;
pub mod event_bus;
pub mod events;
pub mod exporter;
pub mod feature_gates;
pub mod graph;
pub mod media;
pub mod models;
pub mod node_discovery;
pub mod notebook_output;
pub mod parser;
pub mod performance;
pub mod preflight;
pub mod proxy;
pub mod queue;
pub mod queue_backends;
pub mod reactor;
pub mod research;
pub mod retry;
pub mod scrapy;
pub mod security;
pub mod spider;
pub mod ssrf_protection;
pub mod storage_backends;
pub mod worker;
pub mod workflow;
pub mod xpath_suggestions;

#[cfg(feature = "web")]
pub mod web;

// 分布式模块（完整版）
pub mod distributed;

// 监控模块（完整版）
pub mod monitor;

// API 模块（简化版）
pub mod api;

pub mod multithread;
pub mod scheduler;

// 加密网站爬取模块
pub mod encrypted;
pub mod extractor;

// Node.js 逆向模块
pub mod node_reverse;

// 终极增强模块
pub mod advanced;

// Crawlee 桥接模块
pub mod bridge;
pub mod captcha;
pub mod checkpoint;
pub mod contracts;
pub mod incremental;

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
pub use artifact::{ArtifactRecord, ArtifactStore, MemoryArtifactStore};
pub use async_runtime::{DedupQueue, Error as AsyncError, PriorityQueue, Request as AsyncRequest};
pub use audit::{AuditEvent, AuditTrail, CompositeAuditTrail, FileAuditTrail, MemoryAuditTrail};

#[cfg(feature = "browser")]
pub use browser::{BrowserBuilder, BrowserConfig, BrowserError, BrowserManager, FormHandler};

pub use ai::entity_extractor::{EntityExtractionResult, EntityExtractor};
pub use ai::sentiment::{SentimentAnalyzer, SentimentResult};
pub use ai::summarizer::{ContentSummarizer, SummaryResult};
pub use antibot::night_mode::NightModePolicy;
pub use captcha::{
    AkamaiBypass as CaptchaAkamaiBypass, CaptchaSolver,
    CloudflareBypass as CaptchaCloudflareBypass, SolveResult,
};
pub use checkpoint::{CheckpointManager, CheckpointState};
pub use connector::{Connector, FileConnector, InMemoryConnector, OutputEnvelope};
pub use contracts::{
    classify_failure, ensure_frontier_persisted, AutoscaledFrontier, FileArtifactStore,
    FrontierConfig, Middleware, MiddlewareChain, ObservabilityCollector, ProxyPolicy,
    RequestFingerprint, RuntimeSession, SessionPool,
};
pub use cookie::{Cookie, CookieJar};
pub use dedup::{FingerprintIndex, FingerprintRecord};
pub use distributed::node_discovery::{
    discover_nodes_from_dns_srv, discover_nodes_from_dns_srv_records, discover_nodes_from_env,
    discover_nodes_from_file, DiscoveredNode,
};
pub use downloader::HTTPDownloader;
pub use dynamic::{DynamicWait, FormInteractor, ScrollLoader};
pub use enhanced::{CrawlStats, VideoItem};
pub use error::{ErrorHandler, ErrorLevel, ErrorType, SpiderError};
pub use event_bus::{
    EventBus as WorkflowEventBus, EventEnvelope as WorkflowEventEnvelope, FileEventBus,
    InMemoryEventBus,
};
pub use events::{
    ArtifactRef as EventArtifactRef, Event as RuntimeEvent, EventBus, TaskDeletedPayload,
    TaskLifecyclePayload, TaskResultPayload, TOPIC_TASK_CANCELLED, TOPIC_TASK_CREATED,
    TOPIC_TASK_DELETED, TOPIC_TASK_FAILED, TOPIC_TASK_QUEUED, TOPIC_TASK_RESULT,
    TOPIC_TASK_RUNNING, TOPIC_TASK_SUCCEEDED,
};
pub use exporter::{ExportData, Exporter};
pub use feature_gates::catalog as feature_gate_catalog;
pub use graph::{Edge, GraphBuilder, Node};
pub use incremental::{IncrementalCrawler, PageCacheEntry};
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
pub use queue_backends::{
    queue_backend_support, NativeQueueClient, QueueBackendConfig, QueueBackendKind,
    QueueBridgeClient, QueueCommandSpec,
};
pub use reactor::{
    BudgetSpec, KernelExecutor, KernelResult, MediaPlan, NativeCrawlPlan, NativeReactor, ParsePlan,
    TargetSpec, TransportPolicy,
};
pub use retry::{RetryConfig, RetryHandler, RetryStrategy};
pub use scrapy::{
    CrawlerProcess as ScrapyCrawlerProcess, FeedExporter as ScrapyFeedExporter, Item as ScrapyItem,
    Output as ScrapyOutput, PluginHandle as ScrapyPluginHandle, Request as ScrapyRequest,
    Response as ScrapyResponse, ScrapyPlugin, Selector as ScrapySelector,
    SelectorList as ScrapySelectorList, Spider as ScrapySpider,
};
pub use spider::{SimpleSpider, SpiderBuilder, SpiderConfig, SpiderEngine, SpiderStats};
pub use ssrf_protection::SSRFProtection;
pub use storage_backends::{
    storage_backend_support, DriverDatasetStore, DriverResultStore, ProcessDatasetStore,
    ProcessResultStore, StorageBackendConfig, StorageBackendKind, StorageCommandSpec,
};
pub use worker::DistributedWorker;
pub use workflow::{FlowJob, FlowResult, FlowStep, MemoryWorkflowContext, WorkflowRunner};
pub use xpath_suggestions::suggest_smart_xpath;

// 分布式简化导出（条件编译）
#[cfg(feature = "distributed")]
pub use distributed::redis_distributed::CrawlTask;

// 监控简化导出
pub use monitor::{SpiderMonitor, SpiderStats as MonitorStats};

// curlconverter 集成模块
pub mod curlconverter;
pub use curlconverter::{curl_to_rust, CurlToRustConverter};
