//! 代理提供者
//! 
//! 管理代理池

use std::collections::VecDeque;
use log::debug;

/// 代理信息
#[derive(Debug, Clone)]
pub struct Proxy {
    /// 代理地址
    pub host: String,
    /// 代理端口
    pub port: u16,
    /// 用户名（可选）
    pub username: Option<String>,
    /// 密码（可选）
    pub password: Option<String>,
    /// 协议
    pub protocol: String,
}

impl Proxy {
    /// 创建 HTTP 代理
    pub fn http(host: impl Into<String>, port: u16) -> Self {
        Self {
            host: host.into(),
            port,
            username: None,
            password: None,
            protocol: "http".to_string(),
        }
    }
    
    /// 创建带认证的 HTTP 代理
    pub fn http_auth(host: impl Into<String>, port: u16, username: impl Into<String>, password: impl Into<String>) -> Self {
        Self {
            host: host.into(),
            port,
            username: Some(username.into()),
            password: Some(password.into()),
            protocol: "http".to_string(),
        }
    }
    
    /// 创建 HTTPS 代理
    pub fn https(host: impl Into<String>, port: u16) -> Self {
        Self {
            host: host.into(),
            port,
            username: None,
            password: None,
            protocol: "https".to_string(),
        }
    }
    
    /// 获取代理 URL
    pub fn url(&self) -> String {
        if let (Some(username), Some(password)) = (&self.username, &self.password) {
            format!("{}://{}:{}@{}:{}", self.protocol, username, password, self.host, self.port)
        } else {
            format!("{}://{}:{}", self.protocol, self.host, self.port)
        }
    }
}

/// 代理提供者
/// 
/// 管理代理池，提供代理轮换功能
pub struct ProxyProvider {
    /// 代理列表
    proxies: VecDeque<Proxy>,
    /// 当前代理索引
    current_index: usize,
    /// 是否启用
    enabled: bool,
}

impl ProxyProvider {
    /// 创建新代理提供者
    pub fn new() -> Self {
        Self {
            proxies: VecDeque::new(),
            current_index: 0,
            enabled: false,
        }
    }
    
    /// 添加代理
    pub fn add_proxy(&mut self, proxy: Proxy) {
        self.proxies.push_back(proxy);
        self.enabled = true;
        debug!("Added proxy: {}", self.proxies.back().unwrap().url());
    }
    
    /// 从列表添加多个代理
    pub fn add_proxies(&mut self, proxies: Vec<Proxy>) {
        for proxy in proxies {
            self.add_proxy(proxy);
        }
    }
    
    /// 从文件加载代理
    /// 
    /// 文件格式：每行一个代理，格式为 host:port 或 protocol://host:port
    pub fn load_from_file(file_path: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let content = std::fs::read_to_string(file_path)?;
        let mut provider = Self::new();
        
        for line in content.lines() {
            let line = line.trim();
            if line.is_empty() || line.starts_with('#') {
                continue;
            }
            
            // 解析代理
            let proxy = if line.starts_with("http://") || line.starts_with("https://") {
                let parts: Vec<&str> = line.split("://").collect();
                if parts.len() == 2 {
                    let protocol = parts[0];
                    let host_port: Vec<&str> = parts[1].split(':').collect();
                    if host_port.len() == 2 {
                        let port = host_port[1].parse().unwrap_or(80);
                        let mut p = Proxy::http(host_port[0], port);
                        p.protocol = protocol.to_string();
                        p
                    } else {
                        continue;
                    }
                } else {
                    continue;
                }
            } else {
                let host_port: Vec<&str> = line.split(':').collect();
                if host_port.len() == 2 {
                    let port = host_port[1].parse().unwrap_or(80);
                    Proxy::http(host_port[0], port)
                } else {
                    continue;
                }
            };
            
            provider.add_proxy(proxy);
        }
        
        Ok(provider)
    }
    
    /// 获取下一个代理
    pub fn get_proxy(&mut self) -> Option<&Proxy> {
        if !self.enabled || self.proxies.is_empty() {
            return None;
        }
        
        let proxy = &self.proxies[self.current_index];
        self.current_index = (self.current_index + 1) % self.proxies.len();
        
        Some(proxy)
    }
    
    /// 获取当前代理
    pub fn current(&self) -> Option<&Proxy> {
        if self.proxies.is_empty() {
            None
        } else {
            Some(&self.proxies[self.current_index])
        }
    }
    
    /// 检查是否启用
    pub fn is_enabled(&self) -> bool {
        self.enabled && !self.proxies.is_empty()
    }
    
    /// 禁用代理
    pub fn disable(&mut self) {
        self.enabled = false;
    }
    
    /// 启用代理
    pub fn enable(&mut self) {
        if !self.proxies.is_empty() {
            self.enabled = true;
        }
    }
    
    /// 获取代理数量
    pub fn len(&self) -> usize {
        self.proxies.len()
    }
    
    /// 检查是否为空
    pub fn is_empty(&self) -> bool {
        self.proxies.is_empty()
    }
    
    /// 移除当前代理（标记为失效）
    pub fn remove_current(&mut self) -> Option<Proxy> {
        if self.proxies.is_empty() {
            return None;
        }
        
        let proxy = self.proxies.remove(self.current_index);
        
        if self.current_index >= self.proxies.len() && !self.proxies.is_empty() {
            self.current_index = 0;
        }
        
        if self.proxies.is_empty() {
            self.enabled = false;
        }
        
        proxy
    }
}

impl Default for ProxyProvider {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_proxy_provider() {
        let mut provider = ProxyProvider::new();
        
        provider.add_proxy(Proxy::http("127.0.0.1", 8080));
        provider.add_proxy(Proxy::http("192.168.1.1", 3128));
        
        assert_eq!(provider.len(), 2);
        assert!(provider.is_enabled());
        
        let proxy1 = provider.get_proxy();
        let proxy2 = provider.get_proxy();
        let proxy3 = provider.get_proxy();
        
        // 应该循环
        assert_eq!(proxy1, proxy3);
        assert_ne!(proxy1, proxy2);
    }
    
    #[test]
    fn test_proxy_url() {
        let proxy = Proxy::http("127.0.0.1", 8080);
        assert_eq!(proxy.url(), "http://127.0.0.1:8080");
        
        let auth_proxy = Proxy::http_auth("127.0.0.1", 8080, "user", "pass");
        assert_eq!(auth_proxy.url(), "http://user:pass@127.0.0.1:8080");
    }
}
