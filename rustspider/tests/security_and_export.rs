use rustspider::security::validate_safe_url;
use rustspider::{ExportData, Exporter, SSRFProtection};

#[test]
fn ssrf_guard_blocks_loopback_and_allows_public_https() {
    assert!(validate_safe_url("https://example.com").is_ok());
    assert!(validate_safe_url("http://localhost:8080").is_err());
    assert!(validate_safe_url("http://169.254.169.254/latest/meta-data").is_err());
    assert_eq!(
        SSRFProtection::filter_safe_urls(["https://example.com", "http://localhost:8080"]),
        vec!["https://example.com/".to_string()]
    );
    assert!(SSRFProtection::validate_redirect_chain(
        "https://example.com",
        ["https://example.com/next"]
    ));
    assert!(!SSRFProtection::validate_redirect_chain(
        "https://example.com",
        ["http://localhost:8080"]
    ));
}

#[test]
fn exporter_supports_jsonl() {
    let dir = std::env::temp_dir().join(format!("rust-exporter-{}", std::process::id()));
    let exporter = Exporter::new(dir.to_string_lossy().as_ref());
    let path = exporter
        .export_jsonl(
            &[ExportData {
                title: "Demo".to_string(),
                url: "https://example.com".to_string(),
                snippet: "hello".to_string(),
                source: "test".to_string(),
                time: "now".to_string(),
            }],
            "items",
        )
        .expect("jsonl export should succeed");
    let content = std::fs::read_to_string(&path).expect("jsonl file should exist");
    assert!(content.contains("\"title\":\"Demo\""));
    let _ = std::fs::remove_file(path);
}
