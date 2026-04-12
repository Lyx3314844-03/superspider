use std::collections::HashMap;

use rustspider::{ArtifactRecord, ArtifactStore, MemoryArtifactStore};

#[test]
fn memory_artifact_store_roundtrips_html_record() {
    let store = MemoryArtifactStore::new();
    let id = store
        .put(ArtifactRecord {
            name: "page".to_string(),
            kind: "html".to_string(),
            uri: None,
            path: Some("artifacts/page.html".to_string()),
            size: 32,
            metadata: HashMap::new(),
        })
        .expect("put");

    let records = store.list().expect("list");
    assert_eq!(id, "artifact-page");
    assert_eq!(records.len(), 1);
    assert_eq!(records[0].path.as_deref(), Some("artifacts/page.html"));
}
