use std::fs;

#[test]
fn rust_cli_ai_command_falls_back_to_heuristics_without_api_key() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let html_path = temp_dir.path().join("page.html");
    fs::write(
        &html_path,
        "<html><head><title>Rust AI Demo</title><meta name=\"description\" content=\"Rust summary\"></head><body><h1>Rust AI Demo</h1></body></html>",
    )
    .expect("html fixture should be written");

    let output = std::process::Command::new("cargo")
        .args([
            "run",
            "--quiet",
            "--",
            "ai",
            "--html-file",
            html_path.to_string_lossy().as_ref(),
            "--instructions",
            "提取标题和摘要",
            "--schema-json",
            "{\"type\":\"object\",\"properties\":{\"title\":{\"type\":\"string\"},\"summary\":{\"type\":\"string\"},\"url\":{\"type\":\"string\"}}}",
        ])
        .env_remove("OPENAI_API_KEY")
        .env_remove("AI_API_KEY")
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("ai command should run");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    let stdout = String::from_utf8_lossy(&output.stdout);
    let payload: serde_json::Value =
        serde_json::from_str(&stdout).expect("stdout should be a JSON payload");
    assert_eq!(payload["command"], "ai");
    assert_eq!(payload["runtime"], "rust");
    assert_eq!(payload["engine"], "heuristic-fallback");
    assert_eq!(payload["result"]["title"], "Rust AI Demo");
    assert_eq!(payload["result"]["summary"], "Rust summary");
}
