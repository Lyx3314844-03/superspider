use rustspider::{run_preflight, PreflightOptions};

#[test]
fn preflight_reports_passed_for_writable_directory() {
    let temp_dir = tempfile::tempdir().expect("tempdir");
    let report = run_preflight(&PreflightOptions::new().with_writable_path(temp_dir.path()));

    assert!(report.is_success());
    assert_eq!(report.summary(), "passed");
    assert!(report.summary_text().contains("passed"));
}

#[test]
fn preflight_serializes_command_shape() {
    let temp_dir = tempfile::tempdir().expect("tempdir");
    let report = run_preflight(&PreflightOptions::new().with_writable_path(temp_dir.path()));
    let json = report.to_json_with_command("doctor").expect("json");

    assert!(json.contains("\"command\": \"doctor\""));
    assert!(json.contains("\"summary\": \"passed\""));
}
