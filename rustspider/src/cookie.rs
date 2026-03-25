//! Cookie 管理模块

use std::collections::HashMap;
use std::fs;
use std::path::Path;

/// Cookie 对象
#[derive(Debug, Clone)]
pub struct Cookie {
    pub name: String,
    pub value: String,
    pub domain: String,
    pub path: String,
    pub expires: Option<i64>,
    pub secure: bool,
    pub http_only: bool,
}

impl Cookie {
    pub fn new(name: &str, value: &str, domain: &str) -> Self {
        Self {
            name: name.to_string(),
            value: value.to_string(),
            domain: domain.to_string(),
            path: "/".to_string(),
            expires: None,
            secure: false,
            http_only: false,
        }
    }

    pub fn is_expired(&self) -> bool {
        if let Some(expires) = self.expires {
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs() as i64;
            return now > expires;
        }
        false
    }
}

/// Cookie 容器
pub struct CookieJar {
    cookies: HashMap<String, HashMap<String, Cookie>>,
    persist_file: Option<String>,
}

impl CookieJar {
    pub fn new() -> Self {
        Self {
            cookies: HashMap::new(),
            persist_file: None,
        }
    }

    pub fn with_persistence(file: &str) -> Self {
        let mut jar = Self::new();
        jar.persist_file = Some(file.to_string());
        jar.load();
        jar
    }

    pub fn set(&mut self, cookie: Cookie) {
        let domain = if cookie.domain.is_empty() {
            "_default".to_string()
        } else {
            cookie.domain.clone()
        };

        self.cookies
            .entry(domain)
            .or_default()
            .insert(cookie.name.clone(), cookie);
    }

    pub fn get(&self, name: &str, domain: &str) -> Option<&Cookie> {
        self.cookies
            .get(domain)
            .and_then(|cookies| cookies.get(name))
            .filter(|c| !c.is_expired())
    }

    pub fn get_for_url(&self, url: &str) -> HashMap<String, String> {
        let mut result = HashMap::new();
        let domain = extract_domain(url);

        if let Some(cookies) = self.cookies.get(&domain) {
            for (name, cookie) in cookies {
                if !cookie.is_expired() {
                    result.insert(name.clone(), cookie.value.clone());
                }
            }
        }

        result
    }

    pub fn clear(&mut self) {
        self.cookies.clear();
    }

    pub fn count(&self) -> usize {
        self.cookies.values().map(|c| c.len()).sum()
    }

    fn load(&mut self) {
        if let Some(file) = &self.persist_file {
            if Path::new(file).exists() {
                // 简化实现：从 JSON 加载
                if let Ok(content) = fs::read_to_string(file) {
                    // TODO: 解析 JSON
                    let _ = content;
                }
            }
        }
    }

    pub fn save(&self) {
        if let Some(file) = &self.persist_file {
            // TODO: 保存为 JSON
            let _ = file;
        }
    }
}

impl Default for CookieJar {
    fn default() -> Self {
        Self::new()
    }
}

fn extract_domain(url: &str) -> String {
    if let Ok(parsed) = url::Url::parse(url) {
        parsed.host_str().unwrap_or("").to_string()
    } else {
        String::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cookie_jar() {
        let mut jar = CookieJar::new();
        jar.set(Cookie::new("session", "abc123", "example.com"));

        assert_eq!(jar.count(), 1);
    }
}
