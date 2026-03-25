//! RustSpider 反反爬模块
//!
//! 特性:
//! 1. ✅ User-Agent 轮换
//! 2. ✅ IP 代理池
//! 3. ✅ Cookie 管理
//! 4. ✅ 请求头随机化
//! 5. ✅ 访问延迟模拟

use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::time::{Duration, Instant};
use rand::Rng;
use tokio::time::sleep;

/// User-Agent 轮换器
pub struct UserAgentRotator {
    chrome_uas: Vec<String>,
    firefox_uas: Vec<String>,
    safari_uas: Vec<String>,
    edge_uas: Vec<String>,
    mobile_uas: Vec<String>,
    ua_pool: Vec<String>,
    usage_count: Arc<RwLock<HashMap<String, usize>>>,
}

impl UserAgentRotator {
    /// 创建新的轮换器
    pub fn new() -> Self {
        let mut rotator = Self {
            chrome_uas: vec![
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36".to_string(),
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36".to_string(),
            ],
            firefox_uas: vec![
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0".to_string(),
            ],
            safari_uas: vec![
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15".to_string(),
            ],
            edge_uas: vec![
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0".to_string(),
            ],
            mobile_uas: vec![
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1".to_string(),
            ],
            ua_pool: Vec::new(),
            usage_count: Arc::new(RwLock::new(HashMap::new())),
        };
        
        rotator.initialize_pool();
        rotator
    }
    
    fn initialize_pool(&mut self) {
        self.ua_pool.extend_from_slice(&self.chrome_uas);
        self.ua_pool.extend_from_slice(&self.firefox_uas);
        self.ua_pool.extend_from_slice(&self.safari_uas);
        self.ua_pool.extend_from_slice(&self.edge_uas);
        self.ua_pool.extend_from_slice(&self.mobile_uas);
        
        let mut count = self.usage_count.write().unwrap();
        for ua in &self.ua_pool {
            count.insert(ua.clone(), 0);
        }
    }
    
    /// 获取随机 User-Agent
    pub fn get_random_user_agent(&self) -> String {
        let mut rng = rand::thread_rng();
        let index = rng.gen_range(0..self.ua_pool.len());
        let ua = self.ua_pool[index].clone();
        
        if let Ok(mut count) = self.usage_count.write() {
            *count.entry(ua.clone()).or_insert(0) += 1;
        }
        
        ua
    }
    
    /// 获取指定浏览器的 User-Agent
    pub fn get_browser_user_agent(&self, browser: &str) -> String {
        let pool = match browser.to_lowercase().as_str() {
            "chrome" => &self.chrome_uas,
            "firefox" => &self.firefox_uas,
            "safari" => &self.safari_uas,
            "edge" => &self.edge_uas,
            "mobile" => &self.mobile_uas,
            _ => &self.ua_pool,
        };
        
        let mut rng = rand::thread_rng();
        let index = rng.gen_range(0..pool.len());
        pool[index].clone()
    }
}

impl Default for UserAgentRotator {
    fn default() -> Self {
        Self::new()
    }
}

/// 代理信息
#[derive(Debug, Clone)]
pub struct ProxyInfo {
    pub ip: String,
    pub port: u16,
    pub protocol: String,
    pub username: Option<String>,
    pub password: Option<String>,
    pub country: String,
    pub is_healthy: bool,
    pub last_check: Option<Instant>,
}

impl ProxyInfo {
    /// 创建新的代理信息
    pub fn new(ip: String, port: u16, protocol: String) -> Self {
        Self {
            ip,
            port,
            protocol,
            username: None,
            password: None,
            country: "Unknown".to_string(),
            is_healthy: true,
            last_check: None,
        }
    }
    
    /// 转换为代理 URL
    pub fn to_url(&self) -> String {
        if let (Some(username), Some(password)) = (&self.username, &self.password) {
            format!("{}://{}:{}@{}:{}", self.protocol, username, password, self.ip, self.port)
        } else {
            format!("{}://{}:{}", self.protocol, self.ip, self.port)
        }
    }
}

/// 代理池
pub struct ProxyPool {
    proxies: Arc<RwLock<Vec<ProxyInfo>>>,
    usage_count: Arc<RwLock<HashMap<String, usize>>>,
    health_status: Arc<RwLock<HashMap<String, bool>>>,
    health_check_interval: Duration,
    timeout: Duration,
}

impl ProxyPool {
    /// 创建新的代理池
    pub fn new(health_check_interval: Duration, timeout: Duration) -> Self {
        Self {
            proxies: Arc::new(RwLock::new(Vec::new())),
            usage_count: Arc::new(RwLock::new(HashMap::new())),
            health_status: Arc::new(RwLock::new(HashMap::new())),
            health_check_interval,
            timeout,
        }
    }
    
    /// 添加代理
    pub fn add_proxy(&self, proxy: ProxyInfo) {
        let mut proxies = self.proxies.write().unwrap();
        let key = format!("{}:{}", proxy.ip, proxy.port);
        
        proxies.push(proxy.clone());
        self.usage_count.write().unwrap().insert(key.clone(), 0);
        self.health_status.write().unwrap().insert(key, true);
    }
    
    /// 获取随机代理
    pub fn get_random_proxy(&self) -> Option<ProxyInfo> {
        let proxies = self.proxies.read().unwrap();
        let healthy: Vec<_> = proxies.iter()
            .filter(|p| {
                let key = format!("{}:{}", p.ip, p.port);
                *self.health_status.read().unwrap().get(&key).unwrap_or(&true)
            })
            .cloned()
            .collect();
        
        if healthy.is_empty() {
            None
        } else {
            let mut rng = rand::thread_rng();
            let proxy = healthy[rng.gen_range(0..healthy.len())].clone();
            
            let key = format!("{}:{}", proxy.ip, proxy.port);
            let mut count = self.usage_count.write().unwrap();
            *count.entry(key).or_insert(0) += 1;
            
            Some(proxy)
        }
    }
    
    /// 标记代理为不健康
    pub fn mark_unhealthy(&self, ip: &str, port: u16) {
        let key = format!("{}:{}", ip, port);
        if let Ok(mut status) = self.health_status.write() {
            status.insert(key, false);
        }
    }
    
    /// 获取统计信息
    pub fn get_stats(&self) -> HashMap<String, usize> {
        let proxies = self.proxies.read().unwrap();
        let health = self.health_status.read().unwrap();
        
        let healthy = proxies.iter()
            .filter(|p| {
                let key = format!("{}:{}", p.ip, p.port);
                *health.get(&key).unwrap_or(&true)
            })
            .count();
        
        let mut stats = HashMap::new();
        stats.insert("total".to_string(), proxies.len());
        stats.insert("healthy".to_string(), healthy);
        stats.insert("unhealthy".to_string(), proxies.len() - healthy);
        
        stats
    }
}

impl Default for ProxyPool {
    fn default() -> Self {
        Self::new(Duration::from_secs(300), Duration::from_secs(5))
    }
}

/// 请求头生成器
pub struct RequestHeadersGenerator {
    ua_rotator: UserAgentRotator,
    accept_headers: Vec<String>,
    accept_languages: Vec<String>,
}

impl RequestHeadersGenerator {
    /// 创建新的请求头生成器
    pub fn new() -> Self {
        Self {
            ua_rotator: UserAgentRotator::new(),
            accept_headers: vec![
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8".to_string(),
                "text/html,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8".to_string(),
            ],
            accept_languages: vec![
                "en-US,en;q=0.9".to_string(),
                "zh-CN,zh;q=0.9,en;q=0.8".to_string(),
            ],
        }
    }
    
    /// 生成随机请求头
    pub fn generate_headers(&self, browser: &str) -> HashMap<String, String> {
        let mut rng = rand::thread_rng();
        let mut headers = HashMap::new();
        
        headers.insert("User-Agent".to_string(), self.ua_rotator.get_browser_user_agent(browser));
        headers.insert("Accept".to_string(), self.accept_headers[rng.gen_range(0..self.accept_headers.len())].clone());
        headers.insert("Accept-Language".to_string(), self.accept_languages[rng.gen_range(0..self.accept_languages.len())].clone());
        headers.insert("Accept-Encoding".to_string(), "gzip, deflate, br".to_string());
        headers.insert("Connection".to_string(), "keep-alive".to_string());
        
        headers
    }
}

impl Default for RequestHeadersGenerator {
    fn default() -> Self {
        Self::new()
    }
}

/// 反反爬管理器
pub struct AntiBotManager {
    pub ua_rotator: UserAgentRotator,
    pub proxy_pool: ProxyPool,
    pub headers_gen: RequestHeadersGenerator,
    pub min_delay: Duration,
    pub max_delay: Duration,
    cookies: Arc<RwLock<HashMap<String, HashMap<String, String>>>>,
}

impl AntiBotManager {
    /// 创建新的反反爬管理器
    pub fn new() -> Self {
        Self {
            ua_rotator: UserAgentRotator::new(),
            proxy_pool: ProxyPool::default(),
            headers_gen: RequestHeadersGenerator::new(),
            min_delay: Duration::from_secs(1),
            max_delay: Duration::from_secs(3),
            cookies: Arc::new(RwLock::new(HashMap::new())),
        }
    }
    
    /// 获取随机请求头
    pub fn get_random_headers(&self, browser: &str) -> HashMap<String, String> {
        self.headers_gen.generate_headers(browser)
    }
    
    /// 获取代理
    pub fn get_proxy(&self) -> Option<ProxyInfo> {
        self.proxy_pool.get_random_proxy()
    }
    
    /// 添加随机延迟
    pub async fn add_random_delay(&self) {
        let mut rng = rand::thread_rng();
        let delay_ms = rng.gen_range(self.min_delay.as_millis()..=self.max_delay.as_millis()) as u64;
        sleep(Duration::from_millis(delay_ms)).await;
    }
    
    /// 设置延迟范围
    pub fn set_delay(&mut self, min: Duration, max: Duration) {
        self.min_delay = min;
        self.max_delay = max;
    }
    
    /// 获取 Cookie
    pub fn get_cookies(&self, domain: &str) -> Option<HashMap<String, String>> {
        let cookies = self.cookies.read().unwrap();
        cookies.get(domain).cloned()
    }
    
    /// 设置 Cookie
    pub fn set_cookies(&self, domain: String, cookies: HashMap<String, String>) {
        let mut cookie_map = self.cookies.write().unwrap();
        cookie_map.insert(domain, cookies);
    }
    
    /// 获取统计信息
    pub fn get_stats(&self) -> HashMap<String, HashMap<String, usize>> {
        let mut stats = HashMap::new();
        stats.insert("proxy".to_string(), self.proxy_pool.get_stats());
        stats
    }
}

impl Default for AntiBotManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_user_agent_rotator() {
        let rotator = UserAgentRotator::new();
        let ua = rotator.get_random_user_agent();
        assert!(!ua.is_empty());
        assert!(ua.starts_with("Mozilla"));
    }
    
    #[test]
    fn test_proxy_pool() {
        let pool = ProxyPool::default();
        pool.add_proxy(ProxyInfo::new("1.2.3.4".to_string(), 8080, "http".to_string()));
        
        let proxy = pool.get_random_proxy();
        assert!(proxy.is_some());
        assert_eq!(proxy.unwrap().ip, "1.2.3.4");
    }
    
    #[tokio::test]
    async fn test_antibot_manager() {
        let manager = AntiBotManager::new();
        let headers = manager.get_random_headers("chrome");
        assert!(headers.contains_key("User-Agent"));
        
        manager.add_random_delay().await;
    }
}
