use std::fs;

#[test]
fn job_schema_lists_all_supported_runtimes() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("workspace root");
    let schema_path = root.join("contracts").join("job.schema.json");
    let raw = fs::read_to_string(schema_path).expect("schema file should exist");
    let value: serde_json::Value = serde_json::from_str(&raw).expect("schema should parse");

    assert_eq!(
        value["properties"]["runtime"]["enum"],
        serde_json::json!(["http", "browser", "media", "ai"])
    );
}

#[test]
fn rust_cli_job_command_accepts_schema_shaped_payload() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let job_path = temp_dir.path().join("job.json");
    fs::write(
        &job_path,
        r#"{
  "name": "rust-schema-job",
  "runtime": "media",
  "target": {
    "url": "https://example.com",
    "body": "playlist.m3u8"
  },
  "output": {
    "format": "json"
  }
}"#,
    )
    .expect("job file should be written");

    let output = std::process::Command::new("cargo")
        .args(["run", "--quiet", "--", "job", "--file"])
        .arg(&job_path)
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("job command should run");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"runtime\": \"media\""));
    assert!(stdout.contains("\"hls\""));
}

#[test]
fn rust_cli_job_command_surfaces_extended_contract_fields() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let job_path = temp_dir.path().join("extended-job.json");
    fs::write(
        &job_path,
        r##"{
  "name": "rust-extended-job",
  "runtime": "ai",
  "target": {
    "url": "https://example.com",
    "headers": { "User-Agent": "rustspider-test" },
    "cookies": { "session": "abc" },
    "allowed_domains": ["example.com"]
  },
  "extract": [
    { "field": "title", "type": "ai" }
  ],
  "browser": {
    "profile": "chrome-stealth",
    "actions": [
      { "type": "click", "selector": "#submit" }
    ],
    "capture": ["html", "har"]
  },
  "resources": {
    "retries": 2,
    "timeout_ms": 1200
  },
  "anti_bot": {
    "session_mode": "sticky",
    "stealth": true,
    "proxy_pool": "residential"
  },
  "policy": {
    "same_domain_only": true,
    "budget": { "bytes_in": 4096 }
  },
  "schedule": {
    "mode": "queued",
    "queue_name": "critical",
    "delay_seconds": 5
  },
  "output": {
    "format": "json"
  },
  "metadata": {
    "content": "<html><title>Rust Extended Title</title></html>"
  }
}"##,
    )
    .expect("job file should be written");

    let output = std::process::Command::new("cargo")
        .args(["run", "--quiet", "--", "job", "--file"])
        .arg(&job_path)
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("job command should run");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"title\": \"Rust Extended Title\""));
    assert!(stdout.contains("\"session_mode\": \"sticky\""));
    assert!(stdout.contains("\"queue_name\": \"critical\""));
    assert!(stdout.contains("\"same_domain_only\": true"));
    assert!(stdout.contains("browser.actions are parsed but not executed by rust native reactor"));
}

#[test]
fn rust_cli_browser_job_routes_into_browser_runtime() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let job_path = temp_dir.path().join("browser-job.json");
    let output_path = temp_dir.path().join("browser-job-output.json");
    fs::write(
        &job_path,
        r##"{
  "name": "rust-browser-job",
  "runtime": "browser",
  "target": {
    "url": "https://example.com"
  },
  "browser": {
    "actions": [
      { "type": "eval", "value": "(()=>{ console.log('helper-log'); return 'ok'; })()", "save_as": "eval_ok" },
      { "type": "listen_network", "save_as": "network_events" }
    ],
    "capture": ["html", "screenshot", "console"]
  },
  "extract": [
    { "field": "title", "type": "ai" }
  ],
  "output": {
    "format": "json",
    "path": "__OUTPUT_PATH__"
  }
}"##
        .replace("__OUTPUT_PATH__", &output_path.to_string_lossy().replace('\\', "\\\\")),
    )
    .expect("job file should be written");

    let output = std::process::Command::new("cargo")
        .args(["run", "--quiet", "--", "job", "--file"])
        .arg(&job_path)
        .env("RUSTSPIDER_BROWSER_ENGINE", "playwright-helper")
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("job command should run");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"runtime\": \"browser\""));
    assert!(stdout.contains("\"state\": \"succeeded\""));
    assert!(stdout.contains("\"title\": \"Example Domain\""));
    assert!(stdout.contains("\"browser_engine\": \"playwright-helper\""));
    assert!(stdout.contains("\"eval_ok\": \"ok\""));
    assert!(stdout.contains("\"network_events\""));
    assert!(stdout.contains("\"console_messages\""));
    assert!(stdout.contains("helper-log"));
    assert!(stdout.contains("browser runtime executed via shared Playwright helper"));
    assert!(output_path.exists());
    let persisted = fs::read_to_string(output_path).expect("output file");
    assert!(persisted.contains("\"state\": \"succeeded\""));
    assert!(persisted.contains("\"network_events\""));
}

#[test]
fn rust_cli_job_command_enforces_allowed_domains() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let job_path = temp_dir.path().join("blocked-domain-job.json");
    fs::write(
        &job_path,
        r#"{
  "name": "rust-blocked-domain-job",
  "runtime": "http",
  "target": {
    "url": "https://example.com",
    "allowed_domains": ["blocked.com"]
  },
  "output": {
    "format": "json"
  }
}"#,
    )
    .expect("job file should be written");

    let output = std::process::Command::new("cargo")
        .args(["run", "--quiet", "--", "job", "--file"])
        .arg(&job_path)
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("job command should run");

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("allowed_domains"));
}

#[test]
fn rust_cli_job_command_enforces_byte_budget() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let job_path = temp_dir.path().join("budget-job.json");
    fs::write(
        &job_path,
        r#"{
  "name": "rust-budget-job",
  "runtime": "ai",
  "target": {
    "url": "https://example.com"
  },
  "policy": {
    "budget": { "bytes_in": 8 }
  },
  "output": {
    "format": "json"
  },
  "metadata": {
    "content": "<html><title>Too Large</title></html>"
  }
}"#,
    )
    .expect("job file should be written");

    let output = std::process::Command::new("cargo")
        .args(["run", "--quiet", "--", "job", "--file"])
        .arg(&job_path)
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("job command should run");

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("exceeded budget"));
}

#[test]
fn rust_cli_job_command_enforces_wall_time_budget() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let job_path = temp_dir.path().join("wall-time-job.json");
    fs::write(
        &job_path,
        r#"{
  "name": "rust-wall-time-job",
  "runtime": "ai",
  "target": {
    "url": "https://example.com"
  },
  "resources": {
    "rate_limit_per_sec": 1
  },
  "policy": {
    "budget": { "wall_time_ms": 10 }
  },
  "output": {
    "format": "json"
  },
  "metadata": {
    "content": "<html><title>Slow Enough</title></html>"
  }
}"#,
    )
    .expect("job file should be written");

    let output = std::process::Command::new("cargo")
        .args(["run", "--quiet", "--", "job", "--file"])
        .arg(&job_path)
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("job command should run");

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("budget.wall_time_ms"));
}

#[test]
fn rust_cli_job_command_extracts_json_path_fields() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let job_path = temp_dir.path().join("json-extract-job.json");
    fs::write(
        &job_path,
        r#"{
  "name": "rust-json-extract",
  "runtime": "ai",
  "target": {
    "url": "https://example.com",
    "body": "{\"product\":{\"name\":\"Capsule\",\"price\":199}}"
  },
  "extract": [
    { "field": "name", "type": "json_path", "path": "product.name", "required": true, "schema": { "type": "string" } },
    { "field": "price", "type": "json_path", "path": "product.price", "required": true, "schema": { "type": "number" } }
  ],
  "output": {
    "format": "json"
  }
}"#,
    )
    .expect("job file should be written");

    let output = std::process::Command::new("cargo")
        .args(["run", "--quiet", "--", "job", "--file"])
        .arg(&job_path)
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("job command should run");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"name\": \"Capsule\""));
    assert!(stdout.contains("\"price\": 199"));
}

#[test]
fn rust_cli_job_command_ai_extracts_structured_fields_from_html() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let job_path = temp_dir.path().join("ai-structured-job.json");
    fs::write(
        &job_path,
        r#"{
  "name": "rust-ai-structured",
  "runtime": "ai",
  "target": {
    "url": "https://example.com/article"
  },
  "extract": [
    { "field": "title", "type": "ai", "schema": { "type": "string" } },
    { "field": "description", "type": "ai", "schema": { "type": "string" } },
    { "field": "links", "type": "ai", "schema": { "type": "array" } },
    { "field": "images", "type": "ai", "schema": { "type": "array" } }
  ],
  "output": {
    "format": "json"
  },
  "metadata": {
    "content": "<html><head><title>Structured Rust Title</title><meta name='description' content='Structured Rust Description'/></head><body><a href='/a'>A</a><img src='/cover.png'/></body></html>"
  }
}"#,
    )
    .expect("job file should be written");

    let output = std::process::Command::new("cargo")
        .args(["run", "--quiet", "--", "job", "--file"])
        .arg(&job_path)
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("job command should run");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"title\": \"Structured Rust Title\""));
    assert!(stdout.contains("\"description\": \"Structured Rust Description\""));
    assert!(stdout.contains("\"links\": ["));
    assert!(stdout.contains("https://example.com/a"));
    assert!(stdout.contains("\"images\": ["));
    assert!(stdout.contains("https://example.com/cover.png"));
}
