//! 爬虫配置对象
//! 
//! 配置爬虫的全局参数

use serde::{Deserialize, Serialize};

/// 爬虫配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// 爬虫名称
    pub name: String,
    /// 线程数
    pub thread_count: usize,
    /// 是否启用去重
    pub deduplication_enabled: bool,
    /// 是否启用代理
    pub proxy_enabled: bool,
    /// 代理地址
    pub proxy_url: Option<String>,
    /// 是否启用分布式
    pub distributed_enabled: bool,
    /// Redis 地址
    pub redis_url: Option<String>,
    /// 日志级别
    pub log_level: String,
    /// 输出目录
    pub output_dir: String,
    /// 最大爬取深度
    pub max_depth: u32,
    /// 最大爬取页面数
    pub max_pages: u32,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            name: "rust-spider".to_string(),
            thread_count: 10,
            deduplication_enabled: true,
            proxy_enabled: false,
            proxy_url: None,
            distributed_enabled: false,
            redis_url: None,
            log_level: "info".to_string(),
            output_dir: "./output".to_string(),
            max_depth: 10,
            max_pages: 10000,
        }
    }
}

impl Config {
    /// 创建新配置
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            ..Default::default()
        }
    }
    
    /// 创建配置（链式调用）
    pub fn create(name: impl Into<String>) -> Self {
        Self::new(name)
    }
    
    /// 设置线程数
    pub fn with_thread_count(mut self, count: usize) -> Self {
        self.thread_count = count;
        self
    }
    
    /// 启用去重
    pub fn with_deduplication(mut self, enabled: bool) -> Self {
        self.deduplication_enabled = enabled;
        self
    }
    
    /// 启用代理
    pub fn with_proxy(mut self, url: impl Into<String>) -> Self {
        self.proxy_enabled = true;
        self.proxy_url = Some(url.into());
        self
    }
    
    /// 启用分布式
    pub fn with_distributed(mut self, redis_url: impl Into<String>) -> Self {
        self.distributed_enabled = true;
        self.redis_url = Some(redis_url.into());
        self
    }
    
    /// 设置日志级别
    pub fn with_log_level(mut self, level: impl Into<String>) -> Self {
        self.log_level = level.into();
        self
    }
    
    /// 设置输出目录
    pub fn with_output_dir(mut self, dir: impl Into<String>) -> Self {
        self.output_dir = dir.into();
        self
    }
    
    /// 设置最大深度
    pub fn with_max_depth(mut self, depth: u32) -> Self {
        self.max_depth = depth;
        self
    }
    
    /// 设置最大页面数
    pub fn with_max_pages(mut self, count: u32) -> Self {
        self.max_pages = count;
        self
    }
}
