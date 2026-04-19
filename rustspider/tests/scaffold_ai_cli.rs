use std::fs;
use std::io::{Read, Write};
use std::net::TcpListener;
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
    let listener = TcpListener::bind("127.0.0.1:0").expect("listener");
    listener.set_nonblocking(true).expect("non blocking");
    let addr = listener.local_addr().expect("addr");
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
fn rust_cli_scaffold_ai_generates_plan_schema_blueprint_and_spider() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let project_dir = temp_dir.path().join("project");
    fs::create_dir_all(&project_dir).expect("project dir");
    fs::write(
        project_dir.join("scrapy-project.json"),
        r#"{"name":"project","runtime":"rust","entry":"src/main.rs","url":"https://example.com"}"#,
    )
    .expect("manifest");
    let html_path = project_dir.join("page.html");
    fs::write(
        &html_path,
        "<html><head><title>Rust Scaffold</title><meta name=\"description\" content=\"Rust scaffold summary\"></head><body><article>hello</article></body></html>",
    )
    .expect("html");

    let output = std::process::Command::new("cargo")
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "scaffold-ai",
            "--project",
            project_dir.to_string_lossy().as_ref(),
            "--html-file",
            html_path.to_string_lossy().as_ref(),
            "--name",
            "scaffold_ai",
        ])
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("scaffold-ai should run");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    assert!(project_dir.join("ai-plan.json").exists());
    assert!(project_dir.join("ai-schema.json").exists());
    assert!(project_dir.join("ai-blueprint.json").exists());
    assert!(project_dir.join("ai-extract-prompt.txt").exists());
    assert!(project_dir.join("ai-auth.json").exists());
    assert!(project_dir
        .join("src")
        .join("spiders")
        .join("scaffold_ai.rs")
        .exists());
}

#[test]
fn rust_cli_auth_capture_writes_auth_assets() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let project_dir = temp_dir.path().join("project");
    fs::create_dir_all(&project_dir).expect("project dir");
    fs::write(
        project_dir.join("scrapy-project.json"),
        r#"{"name":"project","runtime":"rust","entry":"src/main.rs","url":"https://example.com"}"#,
    )
    .expect("manifest");
    fs::write(
        project_dir.join("ai-auth.json"),
        r##"{"actions":[{"type":"assert","url_contains":"/dashboard"},{"type":"save_as","value":"url","save_as":"final_url"}]}"##,
    )
    .expect("auth seed");
    let helper = temp_dir.path().join("fake_playwright_helper.py");
    fs::write(
        &helper,
        r#"
import json, sys, pathlib
args = sys.argv[1:]
def value(flag):
    if flag in args:
        i = args.index(flag)
        return args[i+1]
    return ""
for path in [value("--save-storage-state"), value("--save-cookies-file"), value("--html"), value("--screenshot")]:
    if path:
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}" if path.endswith(".json") else "<html><title>capture</title></html>", encoding="utf-8")
print(json.dumps({"title":"capture","url":value("--url"),"html_path":value("--html"),"screenshot_path":value("--screenshot")}))
"#,
    )
    .expect("helper script");

    let output = std::process::Command::new("cargo")
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "auth-capture",
            "--project",
            project_dir.to_string_lossy().as_ref(),
            "--url",
            "https://example.com",
        ])
        .env(
            "RUSTSPIDER_PLAYWRIGHT_HELPER",
            helper.to_string_lossy().to_string(),
        )
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("auth-capture should run");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    assert!(project_dir.join("ai-auth.json").exists());
    assert!(project_dir
        .join("artifacts")
        .join("auth")
        .join("auth-state.json")
        .exists());
    assert!(project_dir
        .join("artifacts")
        .join("auth")
        .join("auth-cookies.json")
        .exists());
    let auth_payload = fs::read_to_string(project_dir.join("ai-auth.json")).expect("auth payload");
    assert!(auth_payload.contains("\"actions\""));
    assert!(auth_payload.contains("\"action_examples\""));
    assert!(
        auth_payload.contains("\"final_url\"")
            || auth_payload.contains("\"save_as\": \"final_url\"")
    );
}

#[test]
fn rust_cli_auth_capture_can_store_reverse_runtime() {
    let temp_dir = tempfile::tempdir().expect("temp dir");
    let project_dir = temp_dir.path().join("project");
    fs::create_dir_all(&project_dir).expect("project dir");
    fs::write(
        project_dir.join("scrapy-project.json"),
        r#"{"name":"project","runtime":"rust","entry":"src/main.rs","url":"https://example.com"}"#,
    )
    .expect("manifest");
    let server = start_mock_server(|_method, path| {
        let body = match path {
            "/api/anti-bot/detect" => r#"{"success":true,"signals":["vendor:test"],"level":"medium"}"#.to_string(),
            "/api/anti-bot/profile" => r#"{"success":true,"signals":["vendor:test"],"level":"medium"}"#.to_string(),
            "/api/fingerprint/spoof" => r#"{"success":true,"fingerprint":{"ua":"mock"}}"#.to_string(),
            "/api/tls/fingerprint" => r#"{"success":true,"fingerprint":{"ja3":"mock-ja3"}}"#.to_string(),
            "/api/crypto/analyze" => r#"{"success":true,"cryptoTypes":[{"name":"AES","confidence":0.9}],"crypto_types":[{"name":"AES","confidence":0.9}]}"#.to_string(),
            _ => r#"{"success":false}"#.to_string(),
        };
        (200, "application/json".to_string(), body)
    });
    fs::write(
        project_dir.join("ai-auth.json"),
        format!(
            r##"{{"actions":[],"capture_reverse_profile":true,"node_reverse_base_url":"{}"}}"##,
            server.url()
        ),
    )
    .expect("auth seed");
    let helper = temp_dir.path().join("fake_playwright_helper.py");
    fs::write(
        &helper,
        r#"
import json, sys, pathlib
args = sys.argv[1:]
def value(flag):
    if flag in args:
        i = args.index(flag)
        return args[i+1]
    return ""
for path in [value("--save-storage-state"), value("--save-cookies-file"), value("--html"), value("--screenshot")]:
    if path:
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}" if path.endswith(".json") else "<html><title>capture</title></html>", encoding="utf-8")
print(json.dumps({"title":"capture","url":value("--url"),"html_path":value("--html"),"screenshot_path":value("--screenshot")}))
"#,
    )
    .expect("helper");

    let output = std::process::Command::new("cargo")
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "auth-capture",
            "--project",
            project_dir.to_string_lossy().as_ref(),
            "--url",
            "https://example.com",
        ])
        .env(
            "RUSTSPIDER_PLAYWRIGHT_HELPER",
            helper.to_string_lossy().to_string(),
        )
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("auth-capture should run");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    let auth_payload = fs::read_to_string(project_dir.join("ai-auth.json")).expect("auth payload");
    assert!(auth_payload.contains("\"reverse_runtime\""));
    assert!(auth_payload.contains("mock-ja3"));
    assert!(auth_payload.contains("\"crypto_analysis\""));
    assert!(auth_payload.contains("\"AES\""));
}
