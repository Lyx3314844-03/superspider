use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use md5::{Digest, Md5};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PageCacheEntry {
    pub url: String,
    pub etag: Option<String>,
    pub last_modified: Option<String>,
    pub content_hash: Option<String>,
    pub last_crawled_unix: u64,
    pub status_code: u16,
    pub content_changed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IncrementalCrawler {
    enabled: bool,
    min_change_interval_seconds: u64,
    #[serde(default)]
    cache: HashMap<String, PageCacheEntry>,
    #[serde(skip)]
    store_path: Option<PathBuf>,
}

impl IncrementalCrawler {
    pub fn new(enabled: bool, min_change_interval: Duration) -> Self {
        Self {
            enabled,
            min_change_interval_seconds: min_change_interval.as_secs(),
            cache: HashMap::new(),
            store_path: None,
        }
    }

    pub fn should_skip(&self, url: &str, etag: Option<&str>, last_modified: Option<&str>) -> bool {
        if !self.enabled {
            return false;
        }
        let Some(entry) = self.cache.get(url) else {
            return false;
        };
        let now = unix_now();
        if now.saturating_sub(entry.last_crawled_unix) < self.min_change_interval_seconds {
            return true;
        }
        if let (Some(current), Some(previous)) = (etag, entry.etag.as_deref()) {
            if current == previous {
                return true;
            }
        }
        if let (Some(current), Some(previous)) = (last_modified, entry.last_modified.as_deref()) {
            if current == previous {
                return true;
            }
        }
        false
    }

    pub fn get_conditional_headers(&self, url: &str) -> HashMap<String, String> {
        let mut headers = HashMap::new();
        if let Some(entry) = self.cache.get(url) {
            if let Some(etag) = &entry.etag {
                headers.insert("If-None-Match".to_string(), etag.clone());
            }
            if let Some(last_modified) = &entry.last_modified {
                headers.insert("If-Modified-Since".to_string(), last_modified.clone());
            }
        }
        headers
    }

    pub fn update_cache(
        &mut self,
        url: &str,
        etag: Option<&str>,
        last_modified: Option<&str>,
        content: &[u8],
        status_code: u16,
    ) -> bool {
        let content_hash = if content.is_empty() {
            None
        } else {
            let mut hasher = Md5::new();
            hasher.update(content);
            Some(format!("{:x}", hasher.finalize()))
        };
        if let Some(existing) = self.cache.get_mut(url) {
            if existing.content_hash == content_hash {
                existing.last_crawled_unix = unix_now();
                existing.content_changed = false;
                return false;
            }
        }
        let previous = self.cache.get(url).cloned().unwrap_or_default();
        self.cache.insert(
            url.to_string(),
            PageCacheEntry {
                url: url.to_string(),
                etag: etag.map(|value| value.to_string()).or(previous.etag),
                last_modified: last_modified
                    .map(|value| value.to_string())
                    .or(previous.last_modified),
                content_hash,
                last_crawled_unix: unix_now(),
                status_code,
                content_changed: true,
            },
        );
        true
    }

    pub fn delta_token(&self, url: &str) -> Option<String> {
        let entry = self.cache.get(url)?;
        let payload = format!(
            "{}:{}:{}:{}:{}",
            entry.url,
            entry.etag.clone().unwrap_or_default(),
            entry.last_modified.clone().unwrap_or_default(),
            entry.content_hash.clone().unwrap_or_default(),
            entry.status_code
        );
        let mut hasher = Md5::new();
        hasher.update(payload.as_bytes());
        Some(format!("{:x}", hasher.finalize()))
    }

    pub fn snapshot(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }

    pub fn restore(&mut self, snapshot: serde_json::Value) -> Result<(), String> {
        let decoded: IncrementalCrawler = serde_json::from_value(snapshot)
            .map_err(|error| format!("invalid incremental snapshot: {error}"))?;
        self.enabled = decoded.enabled;
        self.min_change_interval_seconds = decoded.min_change_interval_seconds;
        self.cache = decoded.cache;
        Ok(())
    }

    pub fn save(&mut self, path: impl AsRef<Path>) -> Result<PathBuf, String> {
        let target = path.as_ref().to_path_buf();
        if let Some(parent) = target.parent() {
            fs::create_dir_all(parent).map_err(|error| error.to_string())?;
        }
        fs::write(
            &target,
            serde_json::to_string_pretty(self).map_err(|error| error.to_string())?,
        )
        .map_err(|error| error.to_string())?;
        self.store_path = Some(target.clone());
        Ok(target)
    }

    pub fn load(&mut self, path: impl AsRef<Path>) -> Result<(), String> {
        let target = path.as_ref().to_path_buf();
        let raw = fs::read_to_string(&target).map_err(|error| error.to_string())?;
        let decoded: IncrementalCrawler = serde_json::from_str(&raw)
            .map_err(|error| format!("invalid incremental state: {error}"))?;
        self.enabled = decoded.enabled;
        self.min_change_interval_seconds = decoded.min_change_interval_seconds;
        self.cache = decoded.cache;
        self.store_path = Some(target);
        Ok(())
    }
}

fn unix_now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or(Duration::from_secs(0))
        .as_secs()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn incremental_crawler_persists_delta_state() {
        let temp = tempfile::tempdir().expect("tempdir");
        let path = temp.path().join("incremental.json");
        let mut crawler = IncrementalCrawler::new(true, Duration::from_secs(3600));
        assert!(crawler.update_cache(
            "https://example.com/a",
            Some("etag-1"),
            Some("Sat, 11 Apr 2026 00:00:00 GMT"),
            b"alpha",
            200,
        ));
        let token = crawler.delta_token("https://example.com/a").expect("token");
        crawler.save(&path).expect("save incremental");

        let mut restored = IncrementalCrawler::new(true, Duration::from_secs(3600));
        restored.load(&path).expect("load incremental");
        assert_eq!(restored.delta_token("https://example.com/a"), Some(token));
        assert_eq!(
            restored.get_conditional_headers("https://example.com/a"),
            HashMap::from([
                ("If-None-Match".to_string(), "etag-1".to_string()),
                (
                    "If-Modified-Since".to_string(),
                    "Sat, 11 Apr 2026 00:00:00 GMT".to_string(),
                ),
            ])
        );
    }
}
