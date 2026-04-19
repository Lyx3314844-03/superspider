use std::fs;

#[test]
fn rust_cli_job_uses_native_playwright_process_when_requested() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let page_path = temp_dir.path().join("page.html");
    let output_path = temp_dir.path().join("output.json");
    fs::write(
        &page_path,
        "<html><head><title>Native Node Playwright</title></head><body><h1>ok</h1></body></html>",
    )
    .expect("page fixture should be written");
    let file_url = format!("file:///{}", page_path.to_string_lossy().replace('\\', "/"));

    let job_path = temp_dir.path().join("native-playwright-job.json");
    fs::write(
        &job_path,
        format!(
            r#"{{
  "name": "rust-native-playwright-job",
  "runtime": "browser",
  "target": {{
    "url": "{url}"
  }},
  "extract": [
    {{ "field": "title", "type": "ai" }}
  ],
  "output": {{
    "format": "json",
    "path": "{output}"
  }}
}}"#,
            url = file_url,
            output = output_path.to_string_lossy().replace('\\', "\\\\")
        ),
    )
    .expect("job file should be written");

    let output = std::process::Command::new("cargo")
        .args(["run", "--quiet", "--", "job", "--file"])
        .arg(&job_path)
        .env("RUSTSPIDER_BROWSER_ENGINE", "playwright")
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("job command should run");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"browser_engine\": \"playwright-node\""));
    assert!(stdout.contains("Native Node Playwright"));
    assert!(stdout.contains("browser runtime executed via native Playwright process"));
}
