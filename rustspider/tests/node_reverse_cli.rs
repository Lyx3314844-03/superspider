use std::io::{Read, Write};
use std::net::TcpListener;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex, Once, OnceLock};
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

fn cargo_cli_lock() -> &'static Mutex<()> {
    static LOCK: OnceLock<Mutex<()>> = OnceLock::new();
    LOCK.get_or_init(|| Mutex::new(()))
}

fn run_cargo_cli(args: &[&str]) -> std::process::Output {
    static TARGET_DIR: OnceLock<PathBuf> = OnceLock::new();
    static PREPARE_TARGET: Once = Once::new();
    let _guard = cargo_cli_lock().lock().expect("cargo CLI lock");
    let target_dir = TARGET_DIR
        .get_or_init(|| {
            PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join("target")
                .join("node-reverse-cli")
                .join(std::process::id().to_string())
        })
        .clone();
    PREPARE_TARGET.call_once(|| {
        let _ = std::fs::remove_dir_all(&target_dir);
        let _ = std::fs::create_dir_all(&target_dir);
    });
    std::process::Command::new("cargo")
        .args(args)
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .env("CARGO_TARGET_DIR", target_dir)
        .env("CARGO_INCREMENTAL", "0")
        .env("CARGO_PROFILE_DEV_DEBUG", "0")
        .env("CARGO_PROFILE_DEV_CODEGEN_UNITS", "16")
        .output()
        .expect("cargo CLI command should run")
}

#[test]
fn rust_cli_node_reverse_health_command_runs_against_mock_service() {
    let server = start_mock_server(|method, path| {
        let body = match (method, path) {
            ("GET", "/health") => r#"{"status":"ok"}"#.to_string(),
            _ => r#"{"status":"missing"}"#.to_string(),
        };
        (200, "application/json".to_string(), body)
    });

    let output = run_cargo_cli(&[
        "run",
        "--quiet",
        "--",
        "node-reverse",
        "health",
        "--base-url",
        server.url().as_str(),
    ]);

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"command\": \"node-reverse health\""));
    assert!(stdout.contains("\"healthy\": true"));
}

#[test]
fn rust_cli_node_reverse_detect_command_runs_against_mock_service() {
    let server = start_mock_server(|method, path| {
        let body = match (method, path) {
            ("POST", "/api/anti-bot/detect") => {
                r#"{"success":true,"signals":["vendor:cloudflare"],"level":"high"}"#.to_string()
            }
            _ => r#"{"status":"missing"}"#.to_string(),
        };
        (200, "application/json".to_string(), body)
    });

    let temp_dir = tempfile::tempdir().expect("temp dir");
    let html_path = temp_dir.path().join("blocked.html");
    std::fs::write(&html_path, "<html><body>blocked</body></html>")
        .expect("fixture should be written");

    let output = run_cargo_cli(&[
        "run",
        "--quiet",
        "--",
        "node-reverse",
        "detect",
        "--base-url",
        server.url().as_str(),
        "--html-file",
        html_path.to_string_lossy().as_ref(),
        "--status-code",
        "403",
    ]);

    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("vendor:cloudflare"));
    assert!(stdout.contains("\"level\": \"high\""));
}

#[test]
fn rust_cli_node_reverse_fingerprint_spoof_command_runs_against_mock_service() {
    let server = start_mock_server(|method, path| {
        let body = match (method, path) {
            ("POST", "/api/fingerprint/spoof") => {
                r#"{"success":true,"browser":"chrome","platform":"windows","fingerprint":{"userAgent":"mock"}}"#.to_string()
            }
            _ => r#"{"status":"missing"}"#.to_string(),
        };
        (200, "application/json".to_string(), body)
    });

    let output = run_cargo_cli(&[
        "run",
        "--quiet",
        "--",
        "node-reverse",
        "fingerprint-spoof",
        "--base-url",
        server.url().as_str(),
        "--browser",
        "chrome",
        "--platform",
        "windows",
    ]);

    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"browser\": \"chrome\""));
    assert!(stdout.contains("\"platform\": \"windows\""));
}

#[test]
fn rust_cli_node_reverse_tls_fingerprint_command_runs_against_mock_service() {
    let server = start_mock_server(|method, path| {
        let body = match (method, path) {
            ("POST", "/api/tls/fingerprint") => {
                r#"{"success":true,"browser":"chrome","version":"120","fingerprint":{"ja3":"mock-ja3"}}"#.to_string()
            }
            _ => r#"{"status":"missing"}"#.to_string(),
        };
        (200, "application/json".to_string(), body)
    });

    let output = run_cargo_cli(&[
        "run",
        "--quiet",
        "--",
        "node-reverse",
        "tls-fingerprint",
        "--base-url",
        server.url().as_str(),
        "--browser",
        "chrome",
        "--version",
        "120",
    ]);

    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"version\": \"120\""));
    assert!(stdout.contains("mock-ja3"));
}

#[test]
fn rust_cli_node_reverse_canvas_fingerprint_command_runs_against_mock_service() {
    let server = start_mock_server(|method, path| {
        let body = match (method, path) {
            ("POST", "/api/canvas/fingerprint") => {
                r#"{"success":true,"hash":"mock-canvas"}"#.to_string()
            }
            _ => r#"{"status":"missing"}"#.to_string(),
        };
        (200, "application/json".to_string(), body)
    });

    let output = run_cargo_cli(&[
        "run",
        "--quiet",
        "--",
        "node-reverse",
        "canvas-fingerprint",
        "--base-url",
        server.url().as_str(),
    ]);

    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("mock-canvas"));
}

#[test]
fn rust_cli_node_reverse_signature_reverse_command_runs_against_mock_service() {
    let server = start_mock_server(|method, path| {
        let body = match (method, path) {
            ("POST", "/api/signature/reverse") => {
                r#"{"success":true,"functionName":"sign"}"#.to_string()
            }
            _ => r#"{"status":"missing"}"#.to_string(),
        };
        (200, "application/json".to_string(), body)
    });

    let temp_dir = tempfile::tempdir().expect("temp dir");
    let code_path = temp_dir.path().join("sign.js");
    std::fs::write(&code_path, "function sign(v){return v;}").expect("fixture should be written");

    let output = run_cargo_cli(&[
        "run",
        "--quiet",
        "--",
        "node-reverse",
        "signature-reverse",
        "--base-url",
        server.url().as_str(),
        "--code-file",
        code_path.to_string_lossy().as_ref(),
        "--input-data",
        "left",
        "--expected-output",
        "left",
    ]);

    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"functionName\": \"sign\""));
}

#[test]
fn rust_cli_node_reverse_ast_command_runs_against_mock_service() {
    let server = start_mock_server(|method, path| {
        let body = match (method, path) {
            ("POST", "/api/ast/analyze") => {
                r#"{"success":true,"results":{"obfuscation":[{"type":"eval-packer"}]}}"#.to_string()
            }
            _ => r#"{"status":"missing"}"#.to_string(),
        };
        (200, "application/json".to_string(), body)
    });

    let temp_dir = tempfile::tempdir().expect("temp dir");
    let code_path = temp_dir.path().join("bundle.js");
    std::fs::write(&code_path, "eval(function(p,a,c,k,e,d){return p;})")
        .expect("fixture should be written");

    let output = run_cargo_cli(&[
        "run",
        "--quiet",
        "--",
        "node-reverse",
        "ast",
        "--base-url",
        server.url().as_str(),
        "--code-file",
        code_path.to_string_lossy().as_ref(),
        "--analysis",
        "obfuscation",
    ]);

    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("eval-packer"));
}

#[test]
fn rust_cli_node_reverse_webpack_command_runs_against_mock_service() {
    let server = start_mock_server(|method, path| {
        let body = match (method, path) {
            ("POST", "/api/webpack/analyze") => {
                r#"{"success":true,"entrypoints":["main"]}"#.to_string()
            }
            _ => r#"{"status":"missing"}"#.to_string(),
        };
        (200, "application/json".to_string(), body)
    });

    let temp_dir = tempfile::tempdir().expect("temp dir");
    let code_path = temp_dir.path().join("webpack.js");
    std::fs::write(&code_path, "__webpack_require__(1)").expect("fixture should be written");

    let output = run_cargo_cli(&[
        "run",
        "--quiet",
        "--",
        "node-reverse",
        "webpack",
        "--base-url",
        server.url().as_str(),
        "--code-file",
        code_path.to_string_lossy().as_ref(),
    ]);

    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"main\""));
}

#[test]
fn rust_cli_node_reverse_function_call_command_runs_against_mock_service() {
    let server = start_mock_server(|method, path| {
        let body = match (method, path) {
            ("POST", "/api/function/call") => {
                r#"{"success":true,"result":"left|right"}"#.to_string()
            }
            _ => r#"{"status":"missing"}"#.to_string(),
        };
        (200, "application/json".to_string(), body)
    });

    let temp_dir = tempfile::tempdir().expect("temp dir");
    let code_path = temp_dir.path().join("call.js");
    std::fs::write(&code_path, "function sign(a,b){return a+'|'+b;}")
        .expect("fixture should be written");

    let output = run_cargo_cli(&[
        "run",
        "--quiet",
        "--",
        "node-reverse",
        "function-call",
        "--base-url",
        server.url().as_str(),
        "--code-file",
        code_path.to_string_lossy().as_ref(),
        "--function-name",
        "sign",
        "--arg",
        "left",
        "--arg",
        "right",
    ]);

    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("left|right"));
}

#[test]
fn rust_cli_node_reverse_browser_simulate_command_runs_against_mock_service() {
    let server = start_mock_server(|method, path| {
        let body = match (method, path) {
            ("POST", "/api/browser/simulate") => {
                r#"{"success":true,"result":{"ok":true},"cookies":"session=1"}"#.to_string()
            }
            _ => r#"{"status":"missing"}"#.to_string(),
        };
        (200, "application/json".to_string(), body)
    });

    let temp_dir = tempfile::tempdir().expect("temp dir");
    let code_path = temp_dir.path().join("browser.js");
    std::fs::write(&code_path, "navigator.userAgent").expect("fixture should be written");

    let output = run_cargo_cli(&[
        "run",
        "--quiet",
        "--",
        "node-reverse",
        "browser-simulate",
        "--base-url",
        server.url().as_str(),
        "--code-file",
        code_path.to_string_lossy().as_ref(),
    ]);

    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("session=1"));
}

#[test]
fn rust_cli_antibot_profile_command_detects_blocked_fixture() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let html_path = temp_dir.path().join("blocked.html");
    std::fs::write(
        &html_path,
        "<html><body>Access denied captcha just a moment</body></html>",
    )
    .expect("fixture should be written");

    let output = run_cargo_cli(&[
        "run",
        "--quiet",
        "--",
        "anti-bot",
        "profile",
        "--html-file",
        html_path.to_string_lossy().as_ref(),
        "--status-code",
        "403",
    ]);

    assert_eq!(output.status.code(), Some(1));
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"command\": \"anti-bot profile\""));
    assert!(stdout.contains("\"blocked\": true"));
    assert!(stdout.contains("captcha"));
}

#[test]
fn rust_cli_profile_site_command_builds_profile() {
    let server = start_mock_server(|method, path| {
        let body = match (method, path) {
            ("POST", "/api/anti-bot/detect") => {
                r#"{"success":true,"signals":["vendor:test"]}"#.to_string()
            }
            ("POST", "/api/anti-bot/profile") => {
                r#"{"success":true,"signals":["vendor:test"],"level":"medium"}"#.to_string()
            }
            ("POST", "/api/fingerprint/spoof") => {
                r#"{"success":true,"browser":"chrome"}"#.to_string()
            }
            ("POST", "/api/tls/fingerprint") => {
                r#"{"success":true,"fingerprint":{"ja3":"mock-ja3"}}"#.to_string()
            }
            ("POST", "/api/canvas/fingerprint") => {
                r#"{"success":true,"hash":"mock-canvas"}"#.to_string()
            }
            ("POST", "/api/crypto/analyze") => {
                r#"{"success":true,"crypto_types":[{"name":"AES","confidence":0.9,"modes":["CBC"]}],"keys":[],"ivs":[],"analysis":{"keyFlowChains":[{"variable":"sessionKey","source":{"kind":"storage.localStorage","expression":"localStorage.getItem('session-key')"},"derivations":[{"variable":"derivedKey","kind":"hash","expression":"sha256(sessionKey)"}],"sinks":["crypto.subtle.encrypt"],"confidence":0.87}]}}"#.to_string()
            }
            _ => r#"{"status":"missing"}"#.to_string(),
        };
        (200, "application/json".to_string(), body)
    });

    let temp_dir = tempfile::tempdir().expect("temp dir");
    let html_path = temp_dir.path().join("detail.html");
    std::fs::write(
        &html_path,
        "<html><title>X</title><article>author price</article></html>",
    )
    .expect("fixture should be written");

    let output = run_cargo_cli(&[
        "run",
        "--quiet",
        "--",
        "profile-site",
        "--html-file",
        html_path.to_string_lossy().as_ref(),
        "--base-url",
        server.url().as_str(),
    ]);

    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"command\": \"profile-site\""));
    assert!(stdout.contains("\"page_type\": \"detail\""));
    assert!(stdout.contains("\"reverse\""));
    assert!(stdout.contains("mock-ja3"));
    assert!(stdout.contains("mock-canvas"));
    assert!(stdout.contains("\"canvas_fingerprint\""));
    assert!(stdout.contains("\"crypto_analysis\""));
    assert!(stdout.contains("AES"));
    assert!(stdout.contains("\"reverse_focus\""));
    assert!(stdout.contains("sessionKey"));
    assert!(stdout.contains("crypto.subtle.encrypt"));
}

#[test]
fn rust_cli_sitemap_discover_reads_local_file() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let sitemap_path = temp_dir.path().join("sitemap.xml");
    std::fs::write(&sitemap_path, r#"<?xml version="1.0"?><urlset><url><loc>https://example.com/a</loc></url><url><loc>https://example.com/b</loc></url></urlset>"#)
        .expect("fixture should be written");

    let output = run_cargo_cli(&[
        "run",
        "--quiet",
        "--",
        "sitemap-discover",
        "--sitemap-file",
        sitemap_path.to_string_lossy().as_ref(),
    ]);

    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"command\": \"sitemap-discover\""));
    assert!(stdout.contains("\"url_count\": 2"));
}

#[test]
fn rust_cli_plugins_list_reads_manifest() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let manifest_path = temp_dir.path().join("manifest.json");
    std::fs::write(&manifest_path, r#"{"entrypoints":[{"id":"shared-cli"}]}"#)
        .expect("fixture should be written");

    let output = run_cargo_cli(&[
        "run",
        "--quiet",
        "--",
        "plugins",
        "list",
        "--manifest",
        manifest_path.to_string_lossy().as_ref(),
    ]);

    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"command\": \"plugins list\""));
    assert!(stdout.contains("shared-cli"));
}

#[test]
fn rust_cli_plugins_run_dispatches_builtin_plugin() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let html_path = temp_dir.path().join("page.html");
    std::fs::write(&html_path, "<html><title>Demo</title></html>")
        .expect("fixture should be written");

    let output = run_cargo_cli(&[
        "run",
        "--quiet",
        "--",
        "plugins",
        "run",
        "--plugin",
        "selector-studio",
        "--",
        "--html-file",
        html_path.to_string_lossy().as_ref(),
        "--type",
        "css",
        "--expr",
        "title",
    ]);

    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"command\": \"selector-studio\""));
    assert!(stdout.contains("\"count\": 1"));
    assert!(stdout.contains("\"suggested_xpaths\""));
}

#[test]
fn rust_cli_selector_studio_extracts_values() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let html_path = temp_dir.path().join("page.html");
    std::fs::write(
        &html_path,
        "<html><title>Demo</title><article><h1>Title</h1></article></html>",
    )
    .expect("fixture should be written");

    let output = run_cargo_cli(&[
        "run",
        "--quiet",
        "--",
        "selector-studio",
        "--html-file",
        html_path.to_string_lossy().as_ref(),
        "--type",
        "css",
        "--expr",
        "title",
    ]);

    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"command\": \"selector-studio\""));
    assert!(stdout.contains("\"count\": 1"));
    assert!(stdout.contains("\"suggested_xpaths\""));
}
