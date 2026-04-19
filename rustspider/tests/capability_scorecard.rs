use std::fs;
use std::io::{Read, Write};
use std::net::TcpListener;
use std::path::PathBuf;
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex, Once, OnceLock};
use std::thread;
use std::time::Duration;

use rustspider::{Proxy, ProxyPool, SpiderMonitor};

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

struct PreparedCargoCommand {
    inner: Command,
}

impl PreparedCargoCommand {
    fn args<I, S>(mut self, args: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: AsRef<std::ffi::OsStr>,
    {
        self.inner.args(args);
        self
    }

    fn current_dir<P>(mut self, dir: P) -> Self
    where
        P: AsRef<std::path::Path>,
    {
        self.inner.current_dir(dir);
        self
    }

    fn output(mut self) -> std::io::Result<std::process::Output> {
        static CARGO_COMMAND_LOCK: OnceLock<Mutex<()>> = OnceLock::new();
        let _guard = CARGO_COMMAND_LOCK
            .get_or_init(|| Mutex::new(()))
            .lock()
            .expect("cargo command lock should be available");
        self.inner.output()
    }
}

fn prepared_cargo_command(manifest_dir: &str) -> PreparedCargoCommand {
    static TARGET_DIR: OnceLock<PathBuf> = OnceLock::new();
    static PREPARE_TARGET: Once = Once::new();
    let target_dir = TARGET_DIR
        .get_or_init(|| {
            PathBuf::from(manifest_dir)
                .join("target")
                .join("capability-scorecard")
                .join(std::process::id().to_string())
        })
        .clone();
    PREPARE_TARGET.call_once(|| {
        let _ = fs::remove_dir_all(&target_dir);
        let _ = fs::create_dir_all(&target_dir);
    });
    let mut command = Command::new("cargo");
    command.current_dir(manifest_dir);
    command.env("CARGO_TARGET_DIR", target_dir);
    command.env("CARGO_INCREMENTAL", "0");
    command.env("CARGO_PROFILE_DEV_DEBUG", "0");
    command.env("CARGO_PROFILE_DEV_CODEGEN_UNITS", "16");
    PreparedCargoCommand { inner: command }
}

#[cfg(feature = "browser")]
use rustspider::browser::BrowserConfig;

#[cfg(feature = "browser")]
#[test]
fn browser_config_defaults_cover_headless_and_webdriver() {
    let cfg = BrowserConfig::default();
    assert!(cfg.headless);
    assert_eq!(cfg.webdriver_url, "http://localhost:4444");
    assert!(cfg.timeout.as_secs() >= 30);
}

#[test]
fn monitor_tracks_crawl_progress_and_dashboard() {
    let mut monitor = SpiderMonitor::new("scorecard");
    monitor.start();
    monitor.record_page_crawled("https://example.com", 200, 1024);
    monitor.record_item_extracted(2);
    monitor.record_response_time(150.0);
    monitor.stop();

    let stats = monitor.get_stats();
    assert_eq!(stats["spider_name"], "scorecard");
    assert_eq!(stats["stats"]["pages_crawled"], 1);
    assert_eq!(stats["stats"]["items_extracted"], 2);
}

#[test]
fn proxy_pool_rotates_and_records_failures() {
    let pool = ProxyPool::new("https://example.com", 1_000);
    pool.add_proxy(Proxy::new("127.0.0.1", 8080));
    pool.add_proxy(Proxy::new("127.0.0.2", 8081));

    let first = pool.get_proxy().expect("expected first proxy");
    assert!(first.host.starts_with("127.0.0."));

    pool.record_failure(&first);
    assert!(pool.available_count() >= 1);
    assert_eq!(pool.count(), 2);
}

#[test]
fn deploy_assets_exist_and_describe_binary_and_docker_paths() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let build_script = fs::read_to_string(root.join("build.sh")).expect("build.sh should exist");
    let dockerfile = fs::read_to_string(root.join("docker").join("Dockerfile"))
        .expect("Dockerfile should exist");

    assert!(build_script.contains("cargo build --release"));
    assert!(build_script.contains("docker build -t rustspider:latest"));
    assert!(dockerfile.contains("COPY --from=builder /build/target/release/rustspider"));
    assert!(dockerfile.contains("ENTRYPOINT [\"rustspider\"]"));
}

#[test]
fn cli_capabilities_and_help_surface_ultimate_entrypoint() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");

    let capabilities = prepared_cargo_command(manifest_dir)
        .args(["run", "--quiet", "--", "capabilities"])
        .current_dir(manifest_dir)
        .output()
        .expect("capabilities command should run");
    assert!(
        capabilities.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&capabilities.stderr)
    );
    let capabilities_stdout = String::from_utf8_lossy(&capabilities.stdout);
    assert!(capabilities_stdout.contains("\"command\": \"capabilities\""));
    assert!(capabilities_stdout.contains("\"runtime\": \"rust\""));
    assert!(capabilities_stdout.contains("\"ultimate\""));
    assert!(capabilities_stdout.contains("\"scrapy\""));
    assert!(capabilities_stdout.contains("\"curl\""));
    assert!(capabilities_stdout.contains("\"run\""));
    assert!(capabilities_stdout.contains("\"jobdir\""));
    assert!(capabilities_stdout.contains("\"async-job\""));
    assert!(capabilities_stdout.contains("\"workflow\""));
    assert!(capabilities_stdout.contains("\"http-cache\""));
    assert!(capabilities_stdout.contains("\"console\""));
    assert!(capabilities_stdout.contains("\"audit\""));
    assert!(capabilities_stdout.contains("\"web\""));
    assert!(capabilities_stdout.contains("\"preflight\""));
    assert!(capabilities_stdout.contains("\"research\""));
    assert!(capabilities_stdout.contains("\"node-reverse\""));
    assert!(capabilities_stdout.contains("\"anti-bot\""));
    assert!(capabilities_stdout.contains("\"shared_contracts\""));
    assert!(capabilities_stdout.contains("\"kernel_contracts\""));
    assert!(capabilities_stdout.contains("\"operator_products\""));
    assert!(capabilities_stdout.contains("\"browser_compatibility\""));
    assert!(capabilities_stdout.contains("\"queue_backends\""));
    assert!(capabilities_stdout.contains("\"node_discovery\""));
    assert!(capabilities_stdout.contains("\"night_mode\""));
    assert!(capabilities_stdout.contains("\"security\""));
    assert!(capabilities_stdout.contains("\"event_system\""));
    assert!(capabilities_stdout.contains("\"storage_backends\""));
    assert!(capabilities_stdout.contains("\"observability\""));
    assert!(capabilities_stdout.contains("\"research.ResearchRuntime\""));
    assert!(capabilities_stdout.contains("\"feature_gates\""));
    assert!(capabilities_stdout.contains("\"crawlee_bridge\""));
    assert!(capabilities_stdout.contains("\"connectors\""));
    assert!(capabilities_stdout.contains("\"event_system\""));

    let help = prepared_cargo_command(manifest_dir)
        .args(["run", "--quiet", "--", "help"])
        .current_dir(manifest_dir)
        .output()
        .expect("help command should run");
    assert!(
        help.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&help.stderr)
    );
    let help_stdout = String::from_utf8_lossy(&help.stdout);
    assert!(help_stdout.contains("ultimate"));
    assert!(help_stdout.contains("scrapy"));
    assert!(help_stdout.contains("curl"));
    assert!(help_stdout.contains("run"));
    assert!(help_stdout.contains("jobdir"));
    assert!(help_stdout.contains("async-job"));
    assert!(help_stdout.contains("workflow"));
    assert!(help_stdout.contains("http-cache"));
    assert!(help_stdout.contains("console"));
    assert!(help_stdout.contains("audit"));
    assert!(help_stdout.contains("web"));
    assert!(help_stdout.contains("preflight"));
    assert!(help_stdout.contains("research"));
    assert!(help_stdout.contains("node-reverse"));
    assert!(help_stdout.contains("anti-bot"));
}

#[test]
fn curl_convert_command_surfaces_rust_code_template() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");

    let output = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "curl",
            "convert",
            "--command",
            r#"curl -X GET "https://example.com/api" -H "Accept: application/json""#,
            "--target",
            "ureq",
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("curl convert should run");

    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"command\": \"curl convert\""));
    assert!(stdout.contains("\"target\": \"ureq\""));
    assert!(stdout.contains("ureq::get"));
    assert!(stdout.contains("https://example.com/api"));
}

#[test]
fn scrapy_demo_command_exports_results_from_html_fixture() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let temp_dir = std::env::temp_dir().join("rustspider-scrapy-cli");
    let _ = fs::create_dir_all(&temp_dir);
    let html_path = temp_dir.join("page.html");
    let output_path = temp_dir.join("scrapy-demo.json");
    fs::write(&html_path, "<html><title>Demo</title></html>").expect("fixture should be written");

    let run = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "demo",
            "--url",
            "https://example.com",
            "--html-file",
            html_path.to_string_lossy().as_ref(),
            "--output",
            output_path.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy demo should run");

    assert!(
        run.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&run.stderr)
    );
    let stdout = String::from_utf8_lossy(&run.stdout);
    assert!(stdout.contains("\"command\": \"scrapy demo\""));
    let exported = fs::read_to_string(&output_path).expect("export file should exist");
    assert!(exported.contains("Demo"));
}

#[test]
fn scrapy_run_command_reads_project_manifest() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let temp_dir = std::env::temp_dir().join("rustspider-scrapy-project-cli");
    let _ = fs::create_dir_all(&temp_dir);
    let html_path = temp_dir.join("page.html");
    let output_path = temp_dir
        .join("artifacts")
        .join("exports")
        .join("items.json");
    fs::write(&html_path, "<html><title>Manifest Demo</title></html>")
        .expect("fixture should be written");
    fs::write(
        temp_dir.join("scrapy-project.json"),
        r#"{
  "name": "demo-project",
  "runtime": "rust",
  "entry": "src/main.rs",
  "runner": "dist/rustspider-project",
  "url": "https://example.com",
  "output": "artifacts/exports/items.json"
}"#,
    )
    .expect("manifest should be written");

    let run = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "run",
            "--project",
            temp_dir.to_string_lossy().as_ref(),
            "--html-file",
            html_path.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy run should execute");

    assert!(
        run.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&run.stderr)
    );
    let stdout = String::from_utf8_lossy(&run.stdout);
    assert!(stdout.contains("\"command\": \"scrapy run\""));
    assert!(stdout.contains("\"project_runner\": \"built-in-metadata-runner\""));
    assert!(stdout.contains("\"runner\": \"http\""));
    assert!(stdout.contains("\"plugins\": ["));
    assert!(stdout.contains("\"settings_source\":"));
    assert!(stdout.contains("\"pipeline_count\":"));
    let exported = fs::read_to_string(&output_path).expect("export file should exist");
    assert!(exported.contains("Manifest Demo"));
}

#[test]
fn scrapy_init_command_creates_project() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let project_dir = std::env::temp_dir().join("rustspider-init-project");
    let _ = fs::remove_dir_all(&project_dir);

    let run = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "init",
            "--path",
            project_dir.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy init should execute");

    assert!(
        run.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&run.stderr)
    );
    let stdout = String::from_utf8_lossy(&run.stdout);
    assert!(stdout.contains("\"command\": \"scrapy init\""));
    assert!(project_dir.join("scrapy-project.json").exists());
    assert!(project_dir.join("src").join("main.rs").exists());
    assert!(project_dir.join("spider-framework.yaml").exists());
}

#[test]
fn scrapy_list_validate_and_genspider_commands_work() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let project_dir = std::env::temp_dir().join("rustspider-project-tools");
    let _ = fs::remove_dir_all(&project_dir);

    let init = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "init",
            "--path",
            project_dir.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy init should execute");
    assert!(
        init.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&init.stderr)
    );

    let list = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "list",
            "--project",
            project_dir.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy list should execute");
    assert!(String::from_utf8_lossy(&list.stdout).contains("\"command\": \"scrapy list\""));
    assert!(String::from_utf8_lossy(&list.stdout).contains("\"runner\": \"http\""));
    assert!(String::from_utf8_lossy(&list.stdout).contains("\"url_source\": \"scrapy.spiders\""));

    let validate = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "validate",
            "--project",
            project_dir.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy validate should execute");
    assert!(String::from_utf8_lossy(&validate.stdout).contains("\"summary\": \"passed\""));

    let genspider = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "genspider",
            "--name",
            "news",
            "--domain",
            "example.com",
            "--project",
            project_dir.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy genspider should execute");
    assert!(
        String::from_utf8_lossy(&genspider.stdout).contains("\"command\": \"scrapy genspider\"")
    );
    assert!(project_dir
        .join("src")
        .join("spiders")
        .join("news.rs")
        .exists());

    let html_path = project_dir.join("page.html");
    fs::write(&html_path, "<html><title>Selected Spider</title></html>")
        .expect("fixture should be written");
    let run = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "run",
            "--project",
            project_dir.to_string_lossy().as_ref(),
            "--spider",
            "news",
            "--html-file",
            html_path.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy run with spider should execute");
    let run_stdout = String::from_utf8_lossy(&run.stdout);
    assert!(run_stdout.contains("\"spider\": \"news\""));
    assert!(run_stdout.contains("\"project_runner\": \"built-in-metadata-runner\""));
    assert!(run_stdout.contains("\"runner\": \"http\""));
    assert!(run_stdout.contains("\"resolved_runner\": \"http\""));
    assert!(run_stdout.contains("\"url_source\": \"html-fixture\""));
}

#[test]
fn scrapy_shell_command_extracts_values() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let temp_dir = std::env::temp_dir().join("rustspider-shell-cli");
    let _ = fs::create_dir_all(&temp_dir);
    let html_path = temp_dir.join("page.html");
    fs::write(&html_path, "<html><title>Shell Demo</title></html>")
        .expect("fixture should be written");

    let run = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "shell",
            "--html-file",
            html_path.to_string_lossy().as_ref(),
            "--type",
            "css",
            "--expr",
            "title",
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy shell should execute");

    assert!(
        run.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&run.stderr)
    );
    let stdout = String::from_utf8_lossy(&run.stdout);
    assert!(stdout.contains("\"command\": \"scrapy shell\""));
    assert!(stdout.contains("Shell Demo"));
}

#[test]
fn scrapy_export_command_uses_project_output() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let project_dir = std::env::temp_dir().join("rustspider-export-project");
    let _ = fs::remove_dir_all(&project_dir);
    fs::create_dir_all(project_dir.join("artifacts").join("exports")).expect("dirs");
    fs::write(
        project_dir.join("scrapy-project.json"),
        r#"{
  "name": "demo-project",
  "runtime": "rust",
  "entry": "src/main.rs",
  "runner": "dist/rustspider-project",
  "url": "https://example.com",
  "output": "artifacts/exports/items.json"
}"#,
    )
    .expect("manifest");
    fs::write(
        project_dir
            .join("artifacts")
            .join("exports")
            .join("items.json"),
        r#"[{"title":"Demo","url":"https://example.com"}]"#,
    )
    .expect("data");

    let run = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "export",
            "--project",
            project_dir.to_string_lossy().as_ref(),
            "--format",
            "csv",
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy export should execute");

    assert!(
        run.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&run.stderr)
    );
    let stdout = String::from_utf8_lossy(&run.stdout);
    assert!(stdout.contains("\"command\": \"scrapy export\""));
    assert!(project_dir
        .join("artifacts")
        .join("exports")
        .join("items.csv")
        .exists());
}

#[test]
fn scrapy_profile_command_uses_project_and_spider() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let project_dir = std::env::temp_dir().join("rustspider-profile-project");
    let _ = fs::remove_dir_all(&project_dir);
    fs::create_dir_all(project_dir.join("src").join("spiders")).expect("dirs");
    fs::write(
        project_dir.join("scrapy-project.json"),
        r#"{
  "name": "demo-project",
  "runtime": "rust",
  "entry": "src/main.rs",
  "runner": "dist/rustspider-project",
  "url": "https://example.com",
  "output": "artifacts/exports/items.json"
}"#,
    )
    .expect("manifest");
    fs::write(
        project_dir.join("src").join("spiders").join("news.rs"),
        "// scrapy: url=https://example.com/news\n",
    )
    .expect("spider meta");
    let html_path = project_dir.join("page.html");
    fs::write(
        &html_path,
        "<html><title>Profile Demo</title><a href='/a'>A</a><img src='x.png'></html>",
    )
    .expect("fixture");

    let run = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "profile",
            "--project",
            project_dir.to_string_lossy().as_ref(),
            "--spider",
            "news",
            "--html-file",
            html_path.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy profile should execute");

    assert!(
        run.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&run.stderr)
    );
    let stdout = String::from_utf8_lossy(&run.stdout);
    assert!(stdout.contains("\"command\": \"scrapy profile\""));
    assert!(stdout.contains("\"spider\": \"news\""));
    assert!(stdout.contains("\"link_count\": 1"));
    assert!(stdout.contains("\"url_source\": \"html-fixture\""));
}

#[test]
fn rust_project_runner_loads_registered_plugin() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let project_dir = std::env::temp_dir().join("rustspider-plugin-project");
    let _ = fs::remove_dir_all(&project_dir);

    let init = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "init",
            "--path",
            project_dir.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy init should execute");
    assert!(
        init.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&init.stderr)
    );

    fs::write(
        project_dir.join("src").join("plugins").join("default.rs"),
        "use std::sync::Arc;\n\nuse rustspider::scrapy::{PluginHandle, ScrapyPlugin};\nuse rustspider::scrapy::project as projectruntime;\n\npub struct ProjectPlugin;\n\nimpl ScrapyPlugin for ProjectPlugin {}\n\npub fn make_project_plugin() -> PluginHandle { Arc::new(ProjectPlugin) }\n\npub fn register() { projectruntime::register_plugin(\"project-plugin\", make_project_plugin); }\n",
    )
    .expect("plugin should be written");
    fs::write(
        project_dir.join("scrapy-plugins.json"),
        "{\n  \"plugins\": [\n    {\n      \"name\": \"field-injector\",\n      \"priority\": 5,\n      \"config\": {\n        \"fields\": {\n          \"plugin\": \"yes\"\n        }\n      }\n    }\n  ]\n}\n",
    )
    .expect("plugin manifest should be written");

    let html_path = project_dir.join("page.html");
    fs::write(&html_path, "<html><title>Plugin Demo</title></html>").expect("fixture");

    let run = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "run",
            "--project",
            project_dir.to_string_lossy().as_ref(),
            "--spider",
            "demo",
            "--html-file",
            html_path.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy run should execute");

    assert!(
        run.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&run.stderr)
    );
    let stdout = String::from_utf8_lossy(&run.stdout);
    assert!(stdout.contains("\"project_runner\": \"built-in-metadata-runner\""));
    assert!(stdout.contains("\"runner\": \"http\""));
    let exported = fs::read_to_string(
        project_dir
            .join("artifacts")
            .join("exports")
            .join("demo.json"),
    )
    .expect("export should exist");
    assert!(exported.contains("\"plugin\": \"yes\""));
}

#[test]
fn rust_project_runner_applies_declarative_components() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let project_dir = std::env::temp_dir().join("rustspider-component-project");
    let _ = fs::remove_dir_all(&project_dir);

    let init = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "init",
            "--path",
            project_dir.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy init should execute");
    assert!(
        init.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&init.stderr)
    );

    let config_path = project_dir.join("spider-framework.yaml");
    let updated = "version: 1\nproject:\n  name: rustspider-component-project\nruntime: rust\ncrawl:\n  urls:\n    - https://example.com\n  concurrency: 5\n  max_requests: 100\n  max_depth: 3\n  timeout_seconds: 30\nsitemap:\n  enabled: false\n  url: https://example.com/sitemap.xml\n  max_urls: 50\nbrowser:\n  enabled: true\n  headless: true\n  timeout_seconds: 30\n  user_agent: ''\n  screenshot_path: artifacts/browser/page.png\n  html_path: artifacts/browser/page.html\nanti_bot:\n  enabled: true\n  profile: chrome-stealth\n  proxy_pool: local\n  session_mode: sticky\n  stealth: true\n  challenge_policy: browser\n  captcha_provider: 2captcha\n  captcha_api_key: ''\nnode_reverse:\n  enabled: true\n  base_url: http://localhost:3000\nmiddleware:\n  user_agent_rotation: true\n  respect_robots_txt: true\n  min_request_interval_ms: 200\npipeline:\n  console: true\n  dataset: true\n  jsonl_path: artifacts/exports/results.jsonl\nauto_throttle:\n  enabled: true\n  start_delay_ms: 200\n  max_delay_ms: 5000\n  target_response_time_ms: 2000\nplugins:\n  enabled: true\n  manifest: contracts/integration-catalog.json\nscrapy:\n  runner: http\n  pipelines:\n    - field-injector\n  spider_middlewares:\n    - response-context\n  component_config:\n    field_injector:\n      fields:\n        component: configured\n  spiders:\n    demo:\n      runner: http\n      url: https://example.com\nstorage:\n  checkpoint_dir: artifacts/checkpoints\n  dataset_dir: artifacts/datasets\n  export_dir: artifacts/exports\nexport:\n  format: json\n  output_path: artifacts/exports/results.json\n";
    fs::write(&config_path, updated).expect("updated config");

    let html_path = project_dir.join("page.html");
    fs::write(&html_path, "<html><title>Component Demo</title></html>").expect("fixture");

    let run = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "run",
            "--project",
            project_dir.to_string_lossy().as_ref(),
            "--spider",
            "demo",
            "--html-file",
            html_path.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy run should execute");
    assert!(
        run.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&run.stderr)
    );
    let stdout = String::from_utf8_lossy(&run.stdout);
    assert!(stdout.contains("\"pipelines\""));
    assert!(stdout.contains("field-injector"));
    assert!(stdout.contains("response-context"));
    let exported = fs::read_to_string(
        project_dir
            .join("artifacts")
            .join("exports")
            .join("demo.json"),
    )
    .expect("export should exist");
    assert!(exported.contains("\"component\": \"configured\""));
    assert!(exported.contains("\"response_url\": \"https://example.com\""));
}

#[test]
fn rust_project_runner_applies_spider_specific_declarative_overrides() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let project_dir = std::env::temp_dir().join("rustspider-spider-component-project");
    let _ = fs::remove_dir_all(&project_dir);

    let init = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "init",
            "--path",
            project_dir.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy init should execute");
    assert!(
        init.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&init.stderr)
    );

    let config_path = project_dir.join("spider-framework.yaml");
    let updated = "version: 1\nproject:\n  name: rustspider-spider-component-project\nruntime: rust\ncrawl:\n  urls:\n    - https://example.com\n  concurrency: 5\n  max_requests: 100\n  max_depth: 3\n  timeout_seconds: 30\nsitemap:\n  enabled: false\n  url: https://example.com/sitemap.xml\n  max_urls: 50\nbrowser:\n  enabled: true\n  headless: true\n  timeout_seconds: 30\n  user_agent: ''\n  screenshot_path: artifacts/browser/page.png\n  html_path: artifacts/browser/page.html\nanti_bot:\n  enabled: true\n  profile: chrome-stealth\n  proxy_pool: local\n  session_mode: sticky\n  stealth: true\n  challenge_policy: browser\n  captcha_provider: 2captcha\n  captcha_api_key: ''\nnode_reverse:\n  enabled: true\n  base_url: http://localhost:3000\nmiddleware:\n  user_agent_rotation: true\n  respect_robots_txt: true\n  min_request_interval_ms: 200\npipeline:\n  console: true\n  dataset: true\n  jsonl_path: artifacts/exports/results.jsonl\nauto_throttle:\n  enabled: true\n  start_delay_ms: 200\n  max_delay_ms: 5000\n  target_response_time_ms: 2000\nplugins:\n  enabled: true\n  manifest: contracts/integration-catalog.json\nscrapy:\n  runner: http\n  pipelines:\n    - field-injector\n  component_config:\n    field_injector:\n      fields:\n        scope: global\n  spiders:\n    demo:\n      runner: http\n      url: https://example.com\n      spider_middlewares:\n        - response-context\n      component_config:\n        field_injector:\n          fields:\n            scope: demo\n            spider_only: demo-only\nstorage:\n  checkpoint_dir: artifacts/checkpoints\n  dataset_dir: artifacts/datasets\n  export_dir: artifacts/exports\nexport:\n  format: json\n  output_path: artifacts/exports/results.json\n";
    fs::write(&config_path, updated).expect("updated config");

    let html_path = project_dir.join("page.html");
    fs::write(
        &html_path,
        "<html><title>Spider Override Demo</title></html>",
    )
    .expect("fixture");

    let run = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "run",
            "--project",
            project_dir.to_string_lossy().as_ref(),
            "--spider",
            "demo",
            "--html-file",
            html_path.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy run should execute");
    assert!(
        run.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&run.stderr)
    );
    let stdout = String::from_utf8_lossy(&run.stdout);
    assert!(stdout.contains("field-injector"));
    assert!(stdout.contains("response-context"));

    let list = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "list",
            "--project",
            project_dir.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy list should execute");
    assert!(
        list.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&list.stderr)
    );
    let list_stdout = String::from_utf8_lossy(&list.stdout);
    assert!(list_stdout.contains("\"pipelines\": ["));
    assert!(list_stdout.contains("\"spider_middlewares\": ["));

    let exported = fs::read_to_string(
        project_dir
            .join("artifacts")
            .join("exports")
            .join("demo.json"),
    )
    .expect("export should exist");
    assert!(exported.contains("\"scope\": \"demo\""));
    assert!(exported.contains("\"spider_only\": \"demo-only\""));
    assert!(exported.contains("\"response_url\": \"https://example.com\""));
}

#[test]
fn rust_project_runner_includes_reverse_summary_when_configured() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let project_dir = std::env::temp_dir().join("rustspider-project-reverse");
    let _ = fs::remove_dir_all(&project_dir);

    let init = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "init",
            "--path",
            project_dir.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy init should execute");
    assert!(
        init.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&init.stderr)
    );

    let reverse_server = start_mock_server(|method, path| {
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
            _ => r#"{"success":false}"#.to_string(),
        };
        (200, "application/json".to_string(), body)
    });

    let config_path = project_dir.join("spider-framework.yaml");
    let updated = fs::read_to_string(&config_path)
        .expect("config")
        .replace("http://localhost:3000", reverse_server.url().as_str());
    fs::write(&config_path, updated).expect("updated config");

    let html_path = project_dir.join("page.html");
    fs::write(&html_path, "<html><title>Reverse Demo</title></html>").expect("fixture");

    let run = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "run",
            "--project",
            project_dir.to_string_lossy().as_ref(),
            "--spider",
            "demo",
            "--html-file",
            html_path.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy run should execute");

    assert!(
        run.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&run.stderr)
    );
    let stdout = String::from_utf8_lossy(&run.stdout);
    assert!(stdout.contains("\"project_runner\": \"built-in-metadata-runner\""));
    assert!(stdout.contains("\"runner\": \"http\""));
    assert!(stdout.contains("\"reverse\""));
    assert!(stdout.contains("mock-ja3"));
}

#[test]
fn rust_source_project_applies_declarative_components_from_project_config() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let project_dir = std::env::temp_dir().join("rustspider-project-components");
    let _ = fs::remove_dir_all(&project_dir);

    let init = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "init",
            "--path",
            project_dir.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy init should execute");
    assert!(
        init.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&init.stderr)
    );

    let config_path = project_dir.join("spider-framework.yaml");
    let updated = fs::read_to_string(&config_path)
        .expect("config")
        .replace("  pipelines: []", "  pipelines:\n    - field-injector")
        .replace(
            "  spider_middlewares: []",
            "  spider_middlewares:\n    - response-context",
        )
        .replace(
            "      fields: {}",
            "      fields:\n        component: configured",
        );
    fs::write(&config_path, updated).expect("updated config");

    let html_path = project_dir.join("page.html");
    fs::write(&html_path, "<html><title>Component Demo</title></html>").expect("fixture");

    let list = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "list",
            "--project",
            project_dir.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy list should execute");
    let list_stdout = String::from_utf8_lossy(&list.stdout);
    assert!(list_stdout.contains("\"pipelines\": ["));
    assert!(list_stdout.contains("\"field-injector\""));
    assert!(list_stdout.contains("\"spider_middlewares\": ["));
    assert!(list_stdout.contains("\"response-context\""));

    let validate = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "validate",
            "--project",
            project_dir.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy validate should execute");
    let validate_stdout = String::from_utf8_lossy(&validate.stdout);
    assert!(validate_stdout.contains("\"summary\": \"passed\""));
    assert!(validate_stdout.contains("pipeline:field-injector"));
    assert!(validate_stdout.contains("spider_middleware:response-context"));

    let run = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "run",
            "--project",
            project_dir.to_string_lossy().as_ref(),
            "--spider",
            "demo",
            "--html-file",
            html_path.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy run should execute");

    assert!(
        run.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&run.stderr)
    );
    let stdout = String::from_utf8_lossy(&run.stdout);
    assert!(stdout.contains("\"project_runner\": \"built-in-metadata-runner\""));
    assert!(stdout.contains("\"runner\": \"http\""));
    assert!(stdout.contains("\"pipeline_count\": 1"));
    assert!(stdout.contains("\"spider_middleware_count\": 1"));
    let exported = fs::read_to_string(
        project_dir
            .join("artifacts")
            .join("exports")
            .join("demo.json"),
    )
    .expect("export should exist");
    assert!(exported.contains("\"component\": \"configured\""));
    assert!(exported.contains("\"response_url\": \"https://example.com\""));
}

#[test]
fn scrapy_bench_command_uses_html_fixture() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let temp_dir = std::env::temp_dir().join("rustspider-bench-cli");
    let _ = fs::create_dir_all(&temp_dir);
    let html_path = temp_dir.join("page.html");
    fs::write(
        &html_path,
        "<html><title>Bench Demo</title><a href='/a'>A</a></html>",
    )
    .expect("fixture should be written");

    let run = prepared_cargo_command(manifest_dir)
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "bench",
            "--html-file",
            html_path.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy bench should execute");

    assert!(
        run.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&run.stderr)
    );
    let stdout = String::from_utf8_lossy(&run.stdout);
    assert!(stdout.contains("\"command\": \"scrapy bench\""));
    assert!(stdout.contains("Bench Demo"));
    assert!(stdout.contains("\"url_source\": \"html-fixture\""));
}

#[test]
fn scrapy_doctor_command_reports_project_health() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let project_dir = std::env::temp_dir().join("rustspider-doctor-project");
    let _ = fs::remove_dir_all(&project_dir);
    fs::create_dir_all(project_dir.join("src").join("spiders")).expect("dirs");
    fs::write(
        project_dir.join("scrapy-project.json"),
        r#"{
  "name": "demo-project",
  "runtime": "rust",
  "entry": "src/main.rs",
  "runner": "dist/rustspider-project",
  "url": "https://example.com",
  "output": "artifacts/exports/items.json"
}"#,
    )
    .expect("manifest");
    fs::write(
        project_dir.join("src").join("spiders").join("demo.rs"),
        "// scrapy: url=https://example.com\n",
    )
    .expect("spider");

    let run = Command::new("cargo")
        .args([
            "run",
            "--quiet",
            "--",
            "scrapy",
            "doctor",
            "--project",
            project_dir.to_string_lossy().as_ref(),
        ])
        .current_dir(manifest_dir)
        .output()
        .expect("scrapy doctor should execute");

    assert!(
        run.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&run.stderr)
    );
    let stdout = String::from_utf8_lossy(&run.stdout);
    assert!(stdout.contains("\"command\": \"scrapy doctor\""));
}
