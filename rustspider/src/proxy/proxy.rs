//! 代理管理模块

use std::sync::{Arc, Mutex};
use rand::Rng;
use std::time::{SystemTime, UNIX_EPOCH};

/// 代理
#[derive(Clone, Debug)]
pub struct Proxy {
    pub host: String,
    pub port: u16,
    pub username: Option<String>,
    pub password: Option<String>,
    pub last_used: u64,
    pub success_count: u32,
    pub fail_count: u32,
    pub available: bool,
}

impl Proxy {
    /// 创建代理
    pub fn new(host: String, port: u16) -> Self {
        Proxy {
            host,
            port,
            username: None,
            password: None,
            last_used: 0,
            success_count: 0,
            fail_count: 0,
            available: true,
        }
    }
    
    /// 创建带认证的代理
    pub fn with_auth(host: String, port: u16, username: String, password: String) -> Self {
        Proxy {
            host,
            port,
            username: Some(username),
            password: Some(password),
            ..Self::new(host, port)
        }
    }
    
    /// 获取代理 URL
    pub fn url(&self) -> String {
        if let (Some(username), Some(password)) = (&self.username, &self.password) {
            format!("http://{}:{}@{}:{}", username, password, self.host, self.port)
        } else {
            format!("http://{}:{}", self.host, self.port)
        }
    }
}

/// 代理池
pub struct ProxyPool {
    proxies: Arc<Mutex<Vec<Proxy>>>,
    current: Arc<Mutex<usize>>,
}

impl ProxyPool {
    /// 创建代理池
    pub fn new() -> Self {
        ProxyPool {
            proxies: Arc::new(Mutex::new(Vec::new())),
            current: Arc::new(Mutex::new(0)),
        }
    }
    
    /// 添加代理
    pub fn add_proxy(&self, proxy: Proxy) {
        let mut proxies = self.proxies.lock().unwrap();
        proxies.push(proxy);
    }
    
    /// 获取代理（轮询）
    pub fn get_proxy(&self) -> Option<Proxy> {
        let proxies = self.proxies.lock().unwrap();
        if proxies.is_empty() {
            return None;
        }
        
        let mut current = self.current.lock().unwrap();
        let proxy = proxies[*current % proxies.len()].clone();
        *current += 1;
        
        if !proxy.available {
            drop(proxies);
            drop(current);
            return self.get_proxy();
        }
        
        Some(proxy)
    }
    
    /// 获取随机代理
    pub fn get_random_proxy(&self) -> Option<Proxy> {
        let proxies = self.proxies.lock().unwrap();
        if proxies.is_empty() {
            return None;
        }
        
        let mut rng = rand::thread_rng();
        let proxy = proxies[rng.gen_range(0..proxies.len())].clone();
        
        if !proxy.available {
            drop(proxies);
            return self.get_random_proxy();
        }
        
        Some(proxy)
    }
    
    /// 记录成功
    pub fn record_success(&self, proxy: &Proxy) {
        let mut proxies = self.proxies.lock().unwrap();
        for p in proxies.iter_mut() {
            if p.host == proxy.host && p.port == proxy.port {
                p.success_count += 1;
                p.last_used = SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_secs();
                break;
            }
        }
    }
    
    /// 记录失败
    pub fn record_failure(&self, proxy: &Proxy) {
        let mut proxies = self.proxies.lock().unwrap();
        for p in proxies.iter_mut() {
            if p.host == proxy.host && p.port == proxy.port {
                p.fail_count += 1;
                if p.fail_count > 10 {
                    p.available = false;
                }
                break;
            }
        }
    }
    
    /// 移除代理
    pub fn remove_proxy(&self, proxy: &Proxy) {
        let mut proxies = self.proxies.lock().unwrap();
        proxies.retain(|p| p.host != proxy.host || p.port != proxy.port);
    }
    
    /// 获取代理数量
    pub fn proxy_count(&self) -> usize {
        self.proxies.lock().unwrap().len()
    }
    
    /// 获取可用代理数量
    pub fn available_count(&self) -> usize {
        self.proxies
            .lock()
            .unwrap()
            .iter()
            .filter(|p| p.available)
            .count()
    }
    
    /// 从文件加载代理
    pub fn load_from_file(&self, filename: &str) -> std::io::Result<()> {
        use std::fs::File;
        use std::io::BufRead;
        use std::io::BufReader;
        
        let file = File::open(filename)?;
        let reader = BufReader::new(file);
        
        for line in reader.lines() {
            let line = line?;
            let line = line.trim();
            
            if line.is_empty() || line.starts_with('#') {
                continue;
            }
            
            let parts: Vec<&str> = line.split(':').collect();
            if parts.len() >= 2 {
                let host = parts[0].to_string();
                let port = parts[1].parse().unwrap_or(8080);
                let username = parts.get(2).map(|s| s.to_string());
                let password = parts.get(3).map(|s| s.to_string());
                
                let mut proxy = Proxy::new(host, port);
                proxy.username = username;
                proxy.password = password;
                
                self.add_proxy(proxy);
            }
        }
        
        Ok(())
    }
    
    /// 保存代理到文件
    pub fn save_to_file(&self, filename: &str) -> std::io::Result<()> {
        use std::fs::File;
        use std::io::Write;
        
        let mut file = File::create(filename)?;
        let proxies = self.proxies.lock().unwrap();
        
        for proxy in proxies.iter() {
            if let (Some(username), Some(password)) = (&proxy.username, &proxy.password) {
                writeln!(
                    file,
                    "{}:{}:{}:{}",
                    proxy.host, proxy.port, username, password
                )?;
            } else {
                writeln!(file, "{}:{}", proxy.host, proxy.port)?;
            }
        }
        
        Ok(())
    }
}

impl Default for ProxyPool {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_proxy_pool() {
        let pool = ProxyPool::new();
        
        pool.add_proxy(Proxy::new("127.0.0.1".to_string(), 8080));
        pool.add_proxy(Proxy::new("192.168.1.1".to_string(), 3128));
        
        assert_eq!(pool.proxy_count(), 2);
        assert!(pool.get_proxy().is_some());
    }
}
