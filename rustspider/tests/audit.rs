use rustspider::{AuditEvent, AuditTrail, CompositeAuditTrail, FileAuditTrail, MemoryAuditTrail};
use std::path::PathBuf;
use std::sync::Arc;

#[test]
fn audit_trails_persist_and_replay_events() {
    let file = Arc::new(FileAuditTrail::new(
        PathBuf::from(std::env::temp_dir())
            .join(format!("rust-audit-{}.jsonl", std::process::id())),
    ));
    let memory = Arc::new(MemoryAuditTrail::default());
    let composite = CompositeAuditTrail::new(vec![memory.clone(), file.clone()]);

    composite
        .append(AuditEvent {
            timestamp: "2026-04-13T00:00:00Z".to_string(),
            job_id: "job-1".to_string(),
            step_id: "goto".to_string(),
            event_type: "step.started".to_string(),
            payload: serde_json::json!({"url": "https://example.com"}),
        })
        .expect("append should succeed");

    assert_eq!(memory.events().expect("memory events").len(), 1);
    assert_eq!(file.events().expect("file events").len(), 1);
}
