//! Cookie 管理模块

use std::collections::HashMap;
use std::fs;
use std::path::Path;

/// Cookie 对象
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, PartialEq, Eq)]
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
                if let Ok(content) = fs::read_to_string(file) {
                    if let Ok(cookies) =
                        serde_json::from_str::<HashMap<String, HashMap<String, Cookie>>>(&content)
                    {
                        self.cookies = cookies;
                    }
                }
            }
        }
    }

    pub fn save(&self) {
        if let Some(file) = &self.persist_file {
            if let Some(parent) = Path::new(file).parent() {
                let _ = fs::create_dir_all(parent);
            }
            if let Ok(content) = serde_json::to_string_pretty(&self.cookies) {
                let _ = fs::write(file, content);
            }
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
    use tempfile::tempdir;

    #[test]
    fn test_cookie_jar() {
        let mut jar = CookieJar::new();
        jar.set(Cookie::new("session", "abc123", "example.com"));

        assert_eq!(jar.count(), 1);
    }

    #[test]
    fn test_cookie_jar_persistence_round_trip() {
        let temp_dir = tempdir().unwrap();
        let path = temp_dir.path().join("cookies.json");
        let path_str = path.to_string_lossy().to_string();

        let mut jar = CookieJar::with_persistence(&path_str);
        let mut cookie = Cookie::new("session", "abc123", "example.com");
        cookie.secure = true;
        jar.set(cookie.clone());
        jar.save();

        let loaded = CookieJar::with_persistence(&path_str);
        let restored = loaded
            .get("session", "example.com")
            .expect("cookie should load");
        assert_eq!(restored, &cookie);
    }
}
