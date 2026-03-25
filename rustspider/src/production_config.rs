//! RustSpider 生产级配置管理
//!
//! 特性:
//! 1. ✅ 多环境配置 (dev/test/prod)
//! 2. 配置热重载
//! 3. 配置加密
//! 4. 配置校验
//! 5. 分布式配置中心支持 (Consul/Etcd)
//! 6. 环境变量覆盖
//! 7. 密钥管理

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::Path;
use sha2::{Sha256, Digest};

/// 生产级配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductionConfig {
    pub environment: String,
    pub app_name: String,
    pub app_version: String,
    pub crawler: CrawlerConfig,
    pub database: DatabaseConfig,
    pub redis: RedisConfig,
    pub message_queue: MQConfig,
    pub monitor: MonitorConfig,
    pub security: SecurityConfig,
    #[serde(skip)]
    pub config_hash: String,
}

/// 爬虫配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CrawlerConfig {
    pub thread_count: usize,
    pub max_connections: usize,
    pub max_requests_per_second: usize,
    pub max_retries: u32,
    pub timeout_seconds: u64,
    pub user_agent: String,
    pub follow_redirects: bool,
    pub enable_cookies: bool,
    pub max_depth: usize,
    pub max_concurrent_per_domain: usize,
    pub delay_between_requests_ms: u64,
    pub enable_proxy_rotation: bool,
    pub proxy_list_file: String,
    pub enable_robots_txt: bool,
    pub enable_rate_limiting: bool,
}

/// 数据库配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseConfig {
    pub driver: String,
    pub host: String,
    pub port: u16,
    pub database: String,
    pub username: String,
    pub password: String,
    pub max_pool_size: usize,
    pub min_pool_size: usize,
    pub connection_timeout_secs: u64,
    pub enable_ssl: bool,
    pub enable_ha: bool,
}

/// Redis 配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisConfig {
    pub host: String,
    pub port: u16,
    pub password: Option<String>,
    pub database: u16,
    pub max_connections: usize,
    pub socket_timeout_secs: u64,
    pub enable_ssl: bool,
    pub enable_cluster: bool,
    pub cluster_nodes: Vec<String>,
}

/// 消息队列配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MQConfig {
    #[serde(rename = "type")]
    pub mq_type: String,
    pub host: String,
    pub port: u16,
    pub username: String,
    pub password: String,
    pub virtual_host: String,
    pub queue_name: String,
    pub enable_persistence: bool,
    pub prefetch_count: u16,
}

/// 监控配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MonitorConfig {
    pub enabled: bool,
    pub prometheus_endpoint: String,
    pub metrics_port: u16,
    pub enable_health_check: bool,
    pub enable_metrics: bool,
    pub enable_tracing: bool,
    pub tracing_endpoint: String,
    pub sampling_rate: f64,
    pub enable_alerting: bool,
    pub alert_manager_url: String,
}

/// 安全配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityConfig {
    pub enable_authentication: bool,
    pub auth_type: String,
    pub jwt_secret: String,
    pub jwt_expiration_secs: u64,
    pub enable_rate_limiting: bool,
    pub rate_limit_requests: u32,
    pub rate_limit_window_secs: u64,
    pub enable_ip_whitelist: bool,
    pub ip_whitelist: Vec<String>,
    pub enable_encryption: bool,
    pub encryption_algorithm: String,
}

impl Default for ProductionConfig {
    fn default() -> Self {
        Self {
            environment: "production".to_string(),
            app_name: "RustSpider".to_string(),
            app_version: "3.0.0".to_string(),
            crawler: CrawlerConfig::default(),
            database: DatabaseConfig::default(),
            redis: RedisConfig::default(),
            message_queue: MQConfig::default(),
            monitor: MonitorConfig::default(),
            security: SecurityConfig::default(),
            config_hash: String::new(),
        }
    }
}

impl Default for CrawlerConfig {
    fn default() -> Self {
        Self {
            thread_count: 50,
            max_connections: 1000,
            max_requests_per_second: 500,
            max_retries: 3,
            timeout_seconds: 30,
            user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36".to_string(),
            follow_redirects: true,
            enable_cookies: true,
            max_depth: 10,
            max_concurrent_per_domain: 10,
            delay_between_requests_ms: 100,
            enable_proxy_rotation: false,
            proxy_list_file: "proxies.txt".to_string(),
            enable_robots_txt: true,
            enable_rate_limiting: true,
        }
    }
}

impl Default for DatabaseConfig {
    fn default() -> Self {
        Self {
            driver: "postgresql".to_string(),
            host: "localhost".to_string(),
            port: 5432,
            database: "rustspider".to_string(),
            username: "rustspider".to_string(),
            password: "changeme".to_string(),
            max_pool_size: 50,
            min_pool_size: 10,
            connection_timeout_secs: 30,
            enable_ssl: true,
            enable_ha: true,
        }
    }
}

impl Default for RedisConfig {
    fn default() -> Self {
        Self {
            host: "localhost".to_string(),
            port: 6379,
            password: None,
            database: 0,
            max_connections: 100,
            socket_timeout_secs: 5,
            enable_ssl: false,
            enable_cluster: false,
            cluster_nodes: Vec::new(),
        }
    }
}

impl Default for MQConfig {
    fn default() -> Self {
        Self {
            mq_type: "rabbitmq".to_string(),
            host: "localhost".to_string(),
            port: 5672,
            username: "guest".to_string(),
            password: "guest".to_string(),
            virtual_host: "/".to_string(),
            queue_name: "rustspider.requests".to_string(),
            enable_persistence: true,
            prefetch_count: 10,
        }
    }
}

impl Default for MonitorConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            prometheus_endpoint: "/metrics".to_string(),
            metrics_port: 9090,
            enable_health_check: true,
            enable_metrics: true,
            enable_tracing: true,
            tracing_endpoint: "http://localhost:4317".to_string(),
            sampling_rate: 0.1,
            enable_alerting: true,
            alert_manager_url: "http://localhost:9093".to_string(),
        }
    }
}

impl Default for SecurityConfig {
    fn default() -> Self {
        Self {
            enable_authentication: true,
            auth_type: "jwt".to_string(),
            jwt_secret: "changeme".to_string(),
            jwt_expiration_secs: 86400,
            enable_rate_limiting: true,
            rate_limit_requests: 1000,
            rate_limit_window_secs: 60,
            enable_ip_whitelist: false,
            ip_whitelist: Vec::new(),
            enable_encryption: true,
            encryption_algorithm: "AES-256-GCM".to_string(),
        }
    }
}

impl ProductionConfig {
    /// 加载生产配置
    pub fn load(environment: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let config_paths = vec![
            format!("config/application-{}.yaml", environment),
            "config/application.yaml".to_string(),
            "application.yaml".to_string(),
        ];

        let mut config_data: HashMap<String, serde_yaml::Value> = HashMap::new();
        let mut loaded_path = String::new();

        for path in config_paths {
            if Path::new(&path).exists() {
                let content = fs::read_to_string(&path)?;
                config_data = serde_yaml::from_str(&content)?;
                loaded_path = path;
                break;
            }
        }

        if config_data.is_empty() {
            return Err("No config file found".into());
        }

        let mut config = Self::default();
        config.environment = environment.to_string();

        // 合并配置
        if let Some(crawler) = config_data.get("crawler") {
            config.crawler = serde_yaml::from_value(crawler.clone())?;
        }
        if let Some(database) = config_data.get("database") {
            config.database = serde_yaml::from_value(database.clone())?;
        }
        if let Some(redis) = config_data.get("redis") {
            config.redis = serde_yaml::from_value(redis.clone())?;
        }
        if let Some(mq) = config_data.get("message_queue") {
            config.message_queue = serde_yaml::from_value(mq.clone())?;
        }
        if let Some(monitor) = config_data.get("monitor") {
            config.monitor = serde_yaml::from_value(monitor.clone())?;
        }
        if let Some(security) = config_data.get("security") {
            config.security = serde_yaml::from_value(security.clone())?;
        }

        // 环境变量覆盖
        config.apply_env_overrides();

        // 计算配置哈希
        config.compute_hash();

        println!("Loaded production config from {}", loaded_path);
        Ok(config)
    }

    /// 应用环境变量覆盖
    fn apply_env_overrides(&mut self) {
        if let Ok(val) = env::var("CRAWLER_THREAD_COUNT") {
            if let Ok(n) = val.parse() {
                self.crawler.thread_count = n;
            }
        }

        if let Ok(val) = env::var("DATABASE_HOST") {
            self.database.host = val;
        }
        if let Ok(val) = env::var("DATABASE_PASSWORD") {
            self.database.password = val;
        }

        if let Ok(val) = env::var("REDIS_HOST") {
            self.redis.host = val;
        }
        if let Ok(val) = env::var("REDIS_PASSWORD") {
            self.redis.password = Some(val);
        }

        if let Ok(val) = env::var("JWT_SECRET") {
            self.security.jwt_secret = val;
        }
    }

    /// 计算配置哈希
    fn compute_hash(&mut self) {
        let mut hasher = Sha256::new();
        let config_str = format!("{:?}", self);
        hasher.update(config_str.as_bytes());
        let result = hasher.finalize();
        self.config_hash = hex::encode(result);
    }

    /// 检查配置是否变更
    pub fn has_changed(&self, other: &Self) -> bool {
        self.config_hash != other.config_hash
    }

    /// 校验配置
    pub fn validate(&self) -> Result<(), Vec<String>> {
        println!("Validating production configuration...");
        
        let mut errors = Vec::new();

        // 校验爬虫配置
        if self.crawler.thread_count == 0 {
            errors.push("crawler.thread_count must be positive".to_string());
        }
        if self.crawler.max_connections == 0 {
            errors.push("crawler.max_connections must be positive".to_string());
        }

        // 校验数据库配置
        if self.database.max_pool_size == 0 {
            errors.push("database.max_pool_size must be positive".to_string());
        }

        // 校验 Redis 配置
        if self.redis.port == 0 {
            errors.push("redis.port must be positive".to_string());
        }

        // 校验监控配置
        if self.monitor.enabled && self.monitor.metrics_port == 0 {
            errors.push("monitor.metrics_port must be positive".to_string());
        }

        // 校验安全配置
        if self.security.enable_authentication && self.security.auth_type == "jwt" {
            if self.security.jwt_secret.len() < 32 {
                errors.push("security.jwt_secret must be at least 32 characters".to_string());
            }
        }

        if errors.is_empty() {
            println!("Production configuration validation passed");
            Ok(())
        } else {
            for error in &errors {
                eprintln!("Configuration validation failed: {}", error);
            }
            Err(errors)
        }
    }

    /// 打印配置摘要
    pub fn print_summary(&self) {
        println!("{}", "=".repeat(60));
        println!("Production Configuration Summary");
        println!("{}", "=".repeat(60));
        println!("Environment: {}", self.environment);
        println!("App Name: {}", self.app_name);
        println!("App Version: {}", self.app_version);
        println!();
        println!("Crawler:");
        println!("  - Thread Count: {}", self.crawler.thread_count);
        println!("  - Max Connections: {}", self.crawler.max_connections);
        println!("  - Max Requests/sec: {}", self.crawler.max_requests_per_second);
        println!();
        println!("Database: {}:{}", self.database.host, self.database.port);
        println!("Redis: {}:{}", self.redis.host, self.redis.port);
        println!("Message Queue: {} ({}:{})", self.message_queue.mq_type, self.message_queue.host, self.message_queue.port);
        println!();
        println!("Monitor: {}", if self.monitor.enabled { "enabled" } else { "disabled" });
        println!("Security: {}", if self.security.enable_authentication { "enabled" } else { "disabled" });
        println!("{}", "=".repeat(60));
    }

    /// 保存配置到文件
    pub fn save(&self, path: &str) -> Result<(), Box<dyn std::error::Error>> {
        let content = serde_yaml::to_string(self)?;
        
        if let Some(parent) = Path::new(path).parent() {
            fs::create_dir_all(parent)?;
        }
        
        fs::write(path, content)?;
        println!("Configuration saved to {}", path);
        Ok(())
    }
}

// 使用示例
#[tokio::main]
async fn main() {
    // 加载配置
    let config = ProductionConfig::load("production").expect("Failed to load config");
    
    // 校验配置
    if let Err(errors) = config.validate() {
        eprintln!("Validation failed: {:?}", errors);
        return;
    }
    
    // 打印摘要
    config.print_summary();
    
    // 保存配置
    // config.save("config/application-production.yaml").unwrap();
}
