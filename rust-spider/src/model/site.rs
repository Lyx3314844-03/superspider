//! 站点配置对象
//! 
//! 配置爬虫的站点相关参数

use std::collections::HashMap;
use std::time::Duration;

/// 站点配置
#[derive(Debug, Clone)]
pub struct Site {
    /// 起始 URL 列表
    pub start_urls: Vec<String>,
    /// 允许的域名
    pub allowed_domains: Vec<String>,
    /// 请求头
    pub headers: HashMap<String, String>,
    /// Cookie
    pub cookies: HashMap<String, String>,
    /// 请求间隔（毫秒）
    pub sleep_time_ms: u64,
    /// 重试次数
    pub retry_times: u32,
    /// 用户代理
    pub user_agent: String,
    /// URL 排除模式（正则）
    pub url_exclude_patterns: Vec<String>,
    /// 是否跟随重定向
    pub follow_redirects: bool,
    /// 请求超时（秒）
    pub timeout_secs: u64,
}

impl Default for Site {
    fn default() -> Self {
        Self {
            start_urls: Vec::new(),
            allowed_domains: Vec::new(),
            headers: HashMap::new(),
            cookies: HashMap::new(),
            sleep_time_ms: 0,
            retry_times: 3,
            user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36".to_string(),
            url_exclude_patterns: Vec::new(),
            follow_redirects: true,
            timeout_secs: 30,
        }
    }
}

impl Site {
    /// 创建新站点配置
    pub fn new() -> Self {
        Self::default()
    }
    
    /// 创建站点配置（链式调用）
    /// 
    /// # Examples
    /// 
    /// ```
    /// use rust_spider::Site;
    /// 
    /// let site = Site::create()
    ///     .add_start_url("https://example.com")
    ///     .set_user_agent("MyBot/1.0");
    /// ```
    pub fn create() -> Self {
        Self::new()
    }
    
    /// 添加起始 URL
    pub fn add_start_url(mut self, url: impl Into<String>) -> Self {
        self.start_urls.push(url.into());
        self
    }
    
    /// 添加多个起始 URL
    pub fn add_start_urls(mut self, urls: Vec<String>) -> Self {
        self.start_urls.extend(urls);
        self
    }
    
    /// 添加允许的域名
    pub fn add_allowed_domain(mut self, domain: impl Into<String>) -> Self {
        self.allowed_domains.push(domain.into());
        self
    }
    
    /// 设置请求头
    pub fn with_header(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.headers.insert(key.into(), value.into());
        self
    }
    
    /// 设置 Cookie
    pub fn with_cookie(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.cookies.insert(key.into(), value.into());
        self
    }
    
    /// 设置请求间隔（毫秒）
    pub fn set_sleep_time(mut self, ms: u64) -> Self {
        self.sleep_time_ms = ms;
        self
    }
    
    /// 设置重试次数
    pub fn set_retry_times(mut self, times: u32) -> Self {
        self.retry_times = times;
        self
    }
    
    /// 设置用户代理
    pub fn set_user_agent(mut self, ua: impl Into<String>) -> Self {
        self.user_agent = ua.into();
        self
    }
    
    /// 添加 URL 排除模式
    pub fn add_url_exclude_pattern(mut self, pattern: impl Into<String>) -> Self {
        self.url_exclude_patterns.push(pattern.into());
        self
    }
    
    /// 设置是否跟随重定向
    pub fn set_follow_redirects(mut self, follow: bool) -> Self {
        self.follow_redirects = follow;
        self
    }
    
    /// 设置超时时间
    pub fn set_timeout(mut self, secs: u64) -> Self {
        self.timeout_secs = secs;
        self
    }
    
    /// 获取超时 Duration
    pub fn timeout_duration(&self) -> Duration {
        Duration::from_secs(self.timeout_secs)
    }
}
