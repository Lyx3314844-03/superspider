//! 配置管理模块
//! 支持 YAML 配置文件

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

/// 爬虫配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpiderConfig {
    pub name: String,
    pub max_requests: usize,
    pub max_depth: usize,
    pub retry_times: usize,
    pub request_timeout: u64,
    pub rate_limit: f64,
    pub thread_count: usize,
    pub enable_persistence: bool,
    pub persistence_path: Option<String>,
    pub log_level: String,
    pub log_file: Option<String>,
}

impl Default for SpiderConfig {
    fn default() -> Self {
        Self {
            name: "Spider".to_string(),
            max_requests: 10000,
            max_depth: 5,
            retry_times: 3,
            request_timeout: 30,
            rate_limit: 5.0,
            thread_count: 5,
            enable_persistence: true,
            persistence_path: Some("data/queue.db".to_string()),
            log_level: "INFO".to_string(),
            log_file: Some("logs/spider.log".to_string()),
        }
    }
}

/// 下载器配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DownloaderConfig {
    pub timeout: u64,
    pub retry_times: usize,
    pub pool_connections: usize,
    pub pool_maxsize: usize,
    pub rate_limit: f64,
    pub use_proxy: bool,
    pub proxy_file: Option<String>,
    pub use_cookie: bool,
    pub cookie_file: Option<String>,
    pub user_agent: String,
}

impl Default for DownloaderConfig {
    fn default() -> Self {
        Self {
            timeout: 30,
            retry_times: 3,
            pool_connections: 10,
            pool_maxsize: 50,
            rate_limit: 5.0,
            use_proxy: false,
            proxy_file: Some("proxies.txt".to_string()),
            use_cookie: true,
            cookie_file: Some("cookies.pkl".to_string()),
            user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36".to_string(),
        }
    }
}

/// 完整配置
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct CompleteConfig {
    pub spider: SpiderConfig,
    pub downloader: DownloaderConfig,
}

/// 配置加载器
pub struct ConfigLoader {
    config: CompleteConfig,
    #[allow(dead_code)]
    config_file: String,
}

impl ConfigLoader {
    pub fn new(config_file: &str) -> Self {
        let config = Self::load_from_file(config_file).unwrap_or_else(|_| {
            log::warn!("加载配置文件失败，使用默认配置");
            CompleteConfig::default()
        });

        Self {
            config,
            config_file: config_file.to_string(),
        }
    }

    fn load_from_file(path: &str) -> Result<CompleteConfig, Box<dyn std::error::Error>> {
        if !Path::new(path).exists() {
            return Err("配置文件不存在".into());
        }

        let content = fs::read_to_string(path)?;
        let config: CompleteConfig = serde_yaml::from_str(&content)?;
        Ok(config)
    }

    pub fn save(&self, path: &str) -> Result<(), Box<dyn std::error::Error>> {
        let content = serde_yaml::to_string(&self.config)?;
        fs::write(path, content)?;
        Ok(())
    }

    pub fn spider(&self) -> &SpiderConfig {
        &self.config.spider
    }

    pub fn downloader(&self) -> &DownloaderConfig {
        &self.config.downloader
    }

    pub fn get(&self, key: &str) -> Option<&dyn std::any::Any> {
        match key {
            "spider" => Some(&self.config.spider),
            "downloader" => Some(&self.config.downloader),
            _ => None,
        }
    }
}

/// 创建默认配置文件
pub fn create_default_config(path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let config = CompleteConfig::default();
    let content = serde_yaml::to_string(&config)?;
    fs::write(path, content)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = CompleteConfig::default();
        assert_eq!(config.spider.name, "Spider");
        assert_eq!(config.spider.max_requests, 10000);
    }
}
