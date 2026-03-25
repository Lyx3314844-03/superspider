use std::fs;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[test]
fn preflight_binary_can_render_json() {
    let temp_dir = std::env::temp_dir().join(format!(
        "rustspider-preflight-cli-{}",
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("time should be valid")
            .as_nanos()
    ));
    fs::create_dir_all(&temp_dir).expect("temp dir should be created");
    let binary = env!("CARGO_BIN_EXE_preflight");

    let output = Command::new(binary)
        .args([
            "--json",
            "--writable-path",
            temp_dir.to_str().expect("temp dir should be valid utf-8"),
        ])
        .output()
        .expect("preflight binary should run");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    let value: serde_json::Value =
        serde_json::from_slice(&output.stdout).expect("output should be valid json");

    assert_eq!(value["command"], "preflight");
    assert_eq!(value["runtime"], "rust");
    assert_eq!(value["exit_code"], 0);
    assert_eq!(value["summary"], "passed");
    assert_eq!(value["checks"][0]["status"], "passed");

    let _ = fs::remove_dir_all(temp_dir);
}
