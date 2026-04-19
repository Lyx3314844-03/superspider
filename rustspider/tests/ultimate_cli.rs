use std::fs;
use std::io::{Read, Write};
use std::net::TcpListener;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::Duration;

struct MockServer {
    addr: String,
    shutdown: Arc<AtomicBool>,
    handle: Option<thread::JoinHandle<()>>,
}

impl MockServer {
    fn url(&self) -> String {
        format!("http://{}", self.addr)
    }
}

impl Drop for MockServer {
    fn drop(&mut self) {
        self.shutdown.store(true, Ordering::SeqCst);
        let _ = std::net::TcpStream::connect(&self.addr);
        if let Some(handle) = self.handle.take() {
            let _ = handle.join();
        }
    }
}

fn start_mock_server<F>(handler: F) -> MockServer
where
    F: Fn(&str, &str) -> (u16, String, String) + Send + Sync + 'static,
{
    let listener = TcpListener::bind("127.0.0.1:0").expect("listener should bind");
    listener
        .set_nonblocking(true)
        .expect("listener should be non-blocking");
    let addr = listener.local_addr().expect("local addr");
    let shutdown = Arc::new(AtomicBool::new(false));
    let shutdown_flag = shutdown.clone();
    let handler = Arc::new(handler);

    let join_handle = thread::spawn(move || {
        while !shutdown_flag.load(Ordering::SeqCst) {
            match listener.accept() {
                Ok((mut stream, _)) => {
                    let mut buffer = [0_u8; 8192];
                    let size = stream.read(&mut buffer).unwrap_or(0);
                    let request = String::from_utf8_lossy(&buffer[..size]).to_string();
                    let mut lines = request.lines();
                    let request_line = lines.next().unwrap_or_default();
                    let mut parts = request_line.split_whitespace();
                    let method = parts.next().unwrap_or_default();
                    let path = parts.next().unwrap_or("/");
                    let (status, content_type, body) = handler(method, path);
                    let response = format!(
                        "HTTP/1.1 {} OK\r\nContent-Type: {}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                        status,
                        content_type,
                        body.len(),
                        body
                    );
                    let _ = stream.write_all(response.as_bytes());
                    let _ = stream.flush();
                }
                Err(err) if err.kind() == std::io::ErrorKind::WouldBlock => {
                    thread::sleep(Duration::from_millis(20));
                }
                Err(_) => break,
            }
        }
    });

    MockServer {
        addr: addr.to_string(),
        shutdown,
        handle: Some(join_handle),
    }
}

#[test]
fn rust_cli_ultimate_command_runs_against_mock_services() {
    let page_server = start_mock_server(|_method, _path| {
        (
            200,
            "text/html; charset=utf-8".to_string(),
            "<html><title>Ultimate Rust</title><script>navigator.userAgent; CryptoJS.AES.encrypt('x','y')</script></html>".to_string(),
        )
    });

    let reverse_server = start_mock_server(|method, path| {
        let body = match (method, path) {
            ("GET", "/health") => r#"{"status":"ok"}"#.to_string(),
            ("POST", "/api/anti-bot/detect") => {
                r#"{"success":true,"signals":["vendor:test"],"level":"medium","detection":{"hasCloudflare":true}}"#.to_string()
            }
            ("POST", "/api/anti-bot/profile") => {
                r#"{"success":true,"detection":{},"vendors":[],"challenges":[],"signals":["vendor:test"],"score":5,"level":"medium","recommendations":["keep cookies"],"requestBlueprint":{},"mitigationPlan":{}}"#.to_string()
            }
            ("POST", "/api/fingerprint/spoof") => {
                r#"{"success":true,"browser":"chrome","platform":"windows","fingerprint":{"userAgent":"mock"}}"#.to_string()
            }
            ("POST", "/api/tls/fingerprint") => {
                r#"{"success":true,"browser":"chrome","version":"120","fingerprint":{"ja3":"mock-ja3"}}"#.to_string()
            }
            ("POST", "/api/canvas/fingerprint") => {
                r#"{"success":true,"hash":"mock-canvas"}"#.to_string()
            }
            ("POST", "/api/browser/simulate") => {
                r#"{"success":true,"result":{"ok":true},"cookies":"session=1","error":null}"#.to_string()
            }
            ("POST", "/api/crypto/analyze") => {
                r#"{"success":true,"crypto_types":[{"name":"AES","confidence":0.9,"modes":["CBC"]}],"keys":["secret"],"ivs":["iv"],"analysis":{}}"#.to_string()
            }
            _ => r#"{"success":false,"error":"not found"}"#.to_string(),
        };
        (200, "application/json".to_string(), body)
    });

    let temp_dir = tempfile::tempdir().expect("temp dir");
    let checkpoint_dir = temp_dir.path().join("checkpoints");
    let config_path = temp_dir.path().join("spider-framework.yaml");
    let config = format!(
        "version: 1\nproject:\n  name: rust-ultimate-test\nruntime: rust\ncrawl:\n  urls:\n    - {page_url}\n  concurrency: 1\n  max_requests: 1\n  max_depth: 1\n  timeout_seconds: 5\nsitemap:\n  enabled: false\n  url: https://example.com/sitemap.xml\n  max_urls: 50\nbrowser:\n  enabled: true\n  headless: true\n  timeout_seconds: 5\n  user_agent: RustUltimateTest\n  screenshot_path: artifacts/browser/page.png\n  html_path: artifacts/browser/page.html\nanti_bot:\n  enabled: true\n  profile: chrome-stealth\n  proxy_pool: local\n  session_mode: sticky\n  stealth: true\n  challenge_policy: browser\n  captcha_provider: 2captcha\n  captcha_api_key: ''\nnode_reverse:\n  enabled: true\n  base_url: {reverse_url}\nmiddleware:\n  user_agent_rotation: true\n  respect_robots_txt: true\n  min_request_interval_ms: 200\npipeline:\n  console: true\n  dataset: true\n  jsonl_path: {jsonl_path}\nauto_throttle:\n  enabled: true\n  start_delay_ms: 200\n  max_delay_ms: 5000\n  target_response_time_ms: 2000\nplugins:\n  enabled: true\n  manifest: contracts/integration-catalog.json\nstorage:\n  checkpoint_dir: {checkpoint_dir}\n  dataset_dir: {dataset_dir}\n  export_dir: {export_dir}\nexport:\n  format: json\n  output_path: {output_path}\ndoctor:\n  network_targets:\n    - https://example.com\n",
        page_url = page_server.url(),
        reverse_url = reverse_server.url(),
        jsonl_path = temp_dir
            .path()
            .join("exports")
            .join("results.jsonl")
            .to_string_lossy()
            .replace('\\', "/"),
        checkpoint_dir = checkpoint_dir.to_string_lossy().replace('\\', "/"),
        dataset_dir = temp_dir
            .path()
            .join("datasets")
            .to_string_lossy()
            .replace('\\', "/"),
        export_dir = temp_dir
            .path()
            .join("exports")
            .to_string_lossy()
            .replace('\\', "/"),
        output_path = temp_dir
            .path()
            .join("exports")
            .join("results.json")
            .to_string_lossy()
            .replace('\\', "/"),
    );
    fs::write(&config_path, config).expect("config should be written");

    let output = std::process::Command::new("cargo")
        .args([
            "run",
            "--quiet",
            "--",
            "ultimate",
            "--config",
            config_path.to_string_lossy().as_ref(),
            "--reverse-service-url",
            reverse_server.url().as_str(),
        ])
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .env(
            "CARGO_TARGET_DIR",
            PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join("target")
                .join("ultimate-cli")
                .join(std::process::id().to_string()),
        )
        .env("CARGO_INCREMENTAL", "0")
        .env("CARGO_PROFILE_DEV_DEBUG", "0")
        .env("CARGO_PROFILE_DEV_CODEGEN_UNITS", "16")
        .output()
        .expect("ultimate command should run");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"command\": \"ultimate\""));
    assert!(stdout.contains("\"runtime\": \"rust\""));
    assert!(stdout.contains("\"summary\": \"passed\""));
    assert!(stdout.contains("\"exit_code\": 0"));
    assert!(stdout.contains("\"result_count\": 1"));
    assert!(stdout.contains("\"reverse\""));
    assert!(stdout.contains("mock-ja3"));
    assert!(stdout.contains("mock-canvas"));
    assert!(stdout.contains("\"canvas_fingerprint\""));
    assert!(stdout.contains("\"crypto_analysis\""));
    assert!(stdout.contains("AES"));
    let checkpoint_file = checkpoint_dir.join("task_0.json");
    assert!(
        checkpoint_file.exists(),
        "missing checkpoint: {}",
        checkpoint_file.display()
    );
}
