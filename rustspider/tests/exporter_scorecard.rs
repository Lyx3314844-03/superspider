use std::fs;

use rustspider::exporter::{ExportData, Exporter};

#[test]
fn exporter_writes_json_and_markdown_outputs() {
    let temp_dir = tempfile::tempdir().expect("tempdir");
    let exporter = Exporter::new(temp_dir.path().to_string_lossy().as_ref());
    let items = vec![ExportData {
        title: "Example".to_string(),
        url: "https://example.com".to_string(),
        snippet: "snippet".to_string(),
        source: "fixture".to_string(),
        time: "2026-04-09T00:00:00Z".to_string(),
    }];

    let json_path = exporter.export_json(&items, "items").expect("json export");
    let markdown_path = exporter
        .export_markdown(&items, "items")
        .expect("markdown export");

    let json = fs::read_to_string(json_path).expect("json file");
    let markdown = fs::read_to_string(markdown_path).expect("markdown file");

    assert!(json.contains("\"runtime\": \"rust\""));
    assert!(json.contains("\"item_count\": 1"));
    assert!(markdown.contains("# 爬取结果"));
    assert!(markdown.contains("Example"));
}
