use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use anyhow::Result;

#[derive(Debug, Clone, Default)]
pub struct ArtifactRecord {
    pub name: String,
    pub kind: String,
    pub uri: Option<String>,
    pub path: Option<String>,
    pub size: u64,
    pub metadata: HashMap<String, String>,
}

pub trait ArtifactStore {
    fn put(&self, artifact: ArtifactRecord) -> Result<String>;
    fn list(&self) -> Result<Vec<ArtifactRecord>>;
}

#[derive(Debug, Default, Clone)]
pub struct MemoryArtifactStore {
    artifacts: Arc<Mutex<Vec<ArtifactRecord>>>,
}

impl MemoryArtifactStore {
    pub fn new() -> Self {
        Self::default()
    }
}

impl ArtifactStore for MemoryArtifactStore {
    fn put(&self, artifact: ArtifactRecord) -> Result<String> {
        let id = format!("artifact-{}", artifact.name);
        self.artifacts.lock().unwrap().push(artifact);
        Ok(id)
    }

    fn list(&self) -> Result<Vec<ArtifactRecord>> {
        Ok(self.artifacts.lock().unwrap().clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn memory_artifact_store_round_trips_records() {
        let store = MemoryArtifactStore::new();
        let id = store
            .put(ArtifactRecord {
                name: "body".to_string(),
                kind: "html".to_string(),
                uri: None,
                path: Some("artifacts/body.html".to_string()),
                size: 12,
                metadata: HashMap::new(),
            })
            .expect("put artifact");

        let records = store.list().expect("list artifacts");
        assert_eq!(id, "artifact-body");
        assert_eq!(records.len(), 1);
        assert_eq!(records[0].kind, "html");
    }
}
