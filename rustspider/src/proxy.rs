//! 代理管理模块

use rand::seq::SliceRandom;
use std::sync::{Arc, Mutex};

/// 代理对象
#[derive(Debug, Clone)]
pub struct Proxy {
    pub host: String,
    pub port: u16,
    pub username: Option<String>,
    pub password: Option<String>,
    pub protocol: String,
    pub response_time: f64,
    pub success_count: usize,
    pub fail_count: usize,
    pub available: bool,
}

impl Proxy {
    pub fn new(host: &str, port: u16) -> Self {
        Self {
            host: host.to_string(),
            port,
            username: None,
            password: None,
            protocol: "http".to_string(),
            response_time: 0.0,
            success_count: 0,
            fail_count: 0,
            available: true,
        }
    }

    pub fn url(&self) -> String {
        if let (Some(username), Some(password)) = (&self.username, &self.password) {
            format!(
                "{}://{}:{}@{}:{}",
                self.protocol, username, password, self.host, self.port
            )
        } else {
            format!("{}://{}:{}", self.protocol, self.host, self.port)
        }
    }

    pub fn success_rate(&self) -> f64 {
        let total = self.success_count + self.fail_count;
        if total == 0 {
            0.0
        } else {
            self.success_count as f64 / total as f64
        }
    }

    pub fn score(&self) -> f64 {
        let success_score = self.success_rate() * 70.0;
        let time_score = if self.response_time > 0.0 {
            (30.0 - (self.response_time / 100.0)).max(0.0)
        } else {
            0.0
        };
        (success_score + time_score).min(100.0)
    }
}

/// 代理池
pub struct ProxyPool {
    proxies: Arc<Mutex<Vec<Proxy>>>,
    #[allow(dead_code)]
    validate_url: String,
    #[allow(dead_code)]
    validate_timeout: u64,
}

impl ProxyPool {
    pub fn new(validate_url: &str, validate_timeout: u64) -> Self {
        Self {
            proxies: Arc::new(Mutex::new(Vec::new())),
            validate_url: validate_url.to_string(),
            validate_timeout,
        }
    }

    pub fn add_proxy(&self, proxy: Proxy) -> bool {
        let mut proxies = self.proxies.lock().unwrap();

        // 检查是否已存在
        for p in proxies.iter() {
            if p.host == proxy.host && p.port == proxy.port {
                return false;
            }
        }

        proxies.push(proxy);
        true
    }

    pub fn add_proxies(&self, proxies: Vec<Proxy>) -> usize {
        let mut count = 0;
        for proxy in proxies {
            if self.add_proxy(proxy) {
                count += 1;
            }
        }
        count
    }

    pub fn get_proxy(&self) -> Option<Proxy> {
        let proxies = self.proxies.lock().unwrap();
        let available: Vec<_> = proxies.iter().filter(|p| p.available).collect();

        if available.is_empty() {
            None
        } else {
            // 获取最佳代理
            available
                .into_iter()
                .max_by(|a, b| a.score().partial_cmp(&b.score()).unwrap())
                .cloned()
        }
    }

    pub fn get_random_proxy(&self) -> Option<Proxy> {
        let proxies = self.proxies.lock().unwrap();
        let available: Vec<_> = proxies.iter().filter(|p| p.available).collect();

        if available.is_empty() {
            None
        } else {
            let mut rng = rand::thread_rng();
            available.choose(&mut rng).cloned().cloned()
        }
    }

    pub fn record_success(&self, proxy: &Proxy, response_time: f64) {
        let mut proxies = self.proxies.lock().unwrap();
        if let Some(p) = proxies
            .iter_mut()
            .find(|p| p.host == proxy.host && p.port == proxy.port)
        {
            p.success_count += 1;
            p.response_time = (p.response_time * 0.8) + (response_time * 0.2);
        }
    }

    pub fn record_failure(&self, proxy: &Proxy) {
        let mut proxies = self.proxies.lock().unwrap();
        if let Some(p) = proxies
            .iter_mut()
            .find(|p| p.host == proxy.host && p.port == proxy.port)
        {
            p.fail_count += 1;
            if p.fail_count >= 10 {
                p.available = false;
            }
        }
    }

    pub fn count(&self) -> usize {
        self.proxies.lock().unwrap().len()
    }

    pub fn available_count(&self) -> usize {
        self.proxies
            .lock()
            .unwrap()
            .iter()
            .filter(|p| p.available)
            .count()
    }

    pub fn load_from_file(&self, path: &str) -> Result<(), Box<dyn std::error::Error>> {
        use std::fs::File;
        use std::io::{BufRead, BufReader};

        let file = File::open(path)?;
        let reader = BufReader::new(file);

        for line in reader.lines() {
            let line = line?;
            let line = line.trim();

            if line.is_empty() || line.starts_with('#') {
                continue;
            }

            if let Some(proxy) = parse_proxy_line(line) {
                self.add_proxy(proxy);
            }
        }

        Ok(())
    }

    pub fn to_reqwest_proxy(&self) -> Option<reqwest::Proxy> {
        self.get_proxy().and_then(|proxy| {
            let proxy_url = proxy.url();
            reqwest::Proxy::http(proxy_url.clone())
                .or_else(|_| reqwest::Proxy::https(proxy_url))
                .ok()
        })
    }
}

impl Default for ProxyPool {
    fn default() -> Self {
        Self::new("https://www.google.com", 10)
    }
}

fn parse_proxy_line(line: &str) -> Option<Proxy> {
    let parts: Vec<&str> = line.split(':').collect();

    if parts.len() >= 2 {
        let host = parts[0].to_string();
        let port = parts[1].parse().ok()?;

        let mut proxy = Proxy::new(&host, port);

        if parts.len() >= 3 {
            proxy.username = Some(parts[2].to_string());
        }
        if parts.len() >= 4 {
            proxy.password = Some(parts[3].to_string());
        }

        Some(proxy)
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_proxy_pool() {
        let pool = ProxyPool::default();

        pool.add_proxy(Proxy::new("127.0.0.1", 8080));
        pool.add_proxy(Proxy::new("192.168.1.1", 3128));

        assert_eq!(pool.count(), 2);

        if let Some(proxy) = pool.get_proxy() {
            assert!(!proxy.host.is_empty());
        }
    }
}
