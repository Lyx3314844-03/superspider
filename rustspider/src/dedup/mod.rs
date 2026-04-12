use std::collections::HashSet;
use std::sync::{Arc, Mutex};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FingerprintRecord {
    pub url_hash: String,
    pub content_hash: String,
}

#[derive(Debug, Default, Clone)]
pub struct FingerprintIndex {
    seen: Arc<Mutex<HashSet<String>>>,
}

impl FingerprintIndex {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert(&self, record: &FingerprintRecord) -> bool {
        let mut seen = self.seen.lock().unwrap();
        seen.insert(format!("{}:{}", record.url_hash, record.content_hash))
    }

    pub fn contains(&self, record: &FingerprintRecord) -> bool {
        let seen = self.seen.lock().unwrap();
        seen.contains(&format!("{}:{}", record.url_hash, record.content_hash))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fingerprint_index_deduplicates_records() {
        let index = FingerprintIndex::new();
        let record = FingerprintRecord {
            url_hash: "u1".to_string(),
            content_hash: "c1".to_string(),
        };

        assert!(index.insert(&record));
        assert!(index.contains(&record));
        assert!(!index.insert(&record));
    }
}
