use rustspider::advanced::{create_ultimate_spider, UltimateConfig};
use rustspider::antibot::antibot::AntiBotHandler;
use rustspider::node_reverse::client::{AntiBotProfileRequest, NodeReverseClient};
use rustspider::parser::HTMLParser;
use rustspider::scrapy::{
    FeedExporter as ScrapyFeedExporter, Item as ScrapyItem, Output as ScrapyOutput,
    Response as ScrapyResponse, Spider as ScrapySpider,
};
use rustspider::{
    run_preflight, BudgetSpec, KernelExecutor, MediaPlan, NativeCrawlPlan, NativeReactor,
    ParsePlan, PreflightOptions, SpiderBuilder, TargetSpec, TransportPolicy,
};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap};
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::sync::Arc;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ContractConfig {
    version: u32,
    project: ProjectSection,
    runtime: String,
    crawl: CrawlSection,
    sitemap: SitemapSection,
    #[serde(default)]
    browser: BrowserSection,
    #[serde(default)]
    anti_bot: AntiBotConfigSection,
    #[serde(default)]
    node_reverse: NodeReverseConfigSection,
    middleware: MiddlewareConfigSection,
    pipeline: PipelineConfigSection,
    auto_throttle: AutoThrottleConfigSection,
    #[serde(default)]
    frontier: FrontierConfigSection,
    #[serde(default)]
    observability: ObservabilityConfigSection,
    #[serde(default)]
    cache: CacheConfigSection,
    plugins: PluginConfigSection,
    #[serde(default)]
    scrapy: ScrapyConfigSection,
    storage: StorageSection,
    export: ExportSection,
    #[serde(default)]
    doctor: DoctorSection,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ProjectSection {
    name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct CrawlSection {
    urls: Vec<String>,
    concurrency: usize,
    max_requests: usize,
    max_depth: usize,
    timeout_seconds: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct SitemapSection {
    enabled: bool,
    url: String,
    max_urls: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
struct BrowserSection {
    enabled: bool,
    headless: bool,
    timeout_seconds: u64,
    user_agent: String,
    screenshot_path: String,
    html_path: String,
    storage_state_file: String,
    cookies_file: String,
    auth_file: String,
}

impl Default for BrowserSection {
    fn default() -> Self {
        Self {
            enabled: true,
            headless: true,
            timeout_seconds: 30,
            user_agent: String::new(),
            screenshot_path: "artifacts/browser/page.png".to_string(),
            html_path: "artifacts/browser/page.html".to_string(),
            storage_state_file: String::new(),
            cookies_file: String::new(),
            auth_file: String::new(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
struct AntiBotConfigSection {
    enabled: bool,
    profile: String,
    proxy_pool: String,
    session_mode: String,
    stealth: bool,
    challenge_policy: String,
    captcha_provider: String,
    captcha_api_key: String,
}

impl Default for AntiBotConfigSection {
    fn default() -> Self {
        Self {
            enabled: true,
            profile: "chrome-stealth".to_string(),
            proxy_pool: "local".to_string(),
            session_mode: "sticky".to_string(),
            stealth: true,
            challenge_policy: "browser".to_string(),
            captcha_provider: "2captcha".to_string(),
            captcha_api_key: String::new(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
struct NodeReverseConfigSection {
    enabled: bool,
    base_url: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct MiddlewareConfigSection {
    user_agent_rotation: bool,
    respect_robots_txt: bool,
    min_request_interval_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct PipelineConfigSection {
    console: bool,
    dataset: bool,
    jsonl_path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct AutoThrottleConfigSection {
    enabled: bool,
    start_delay_ms: u64,
    max_delay_ms: u64,
    target_response_time_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
struct FrontierConfigSection {
    enabled: bool,
    autoscale: bool,
    min_concurrency: usize,
    max_concurrency: usize,
    lease_ttl_seconds: u64,
    max_inflight_per_domain: usize,
    checkpoint_id: String,
    checkpoint_dir: String,
}

impl Default for FrontierConfigSection {
    fn default() -> Self {
        Self {
            enabled: true,
            autoscale: true,
            min_concurrency: 1,
            max_concurrency: 16,
            lease_ttl_seconds: 30,
            max_inflight_per_domain: 2,
            checkpoint_id: "runtime-frontier".to_string(),
            checkpoint_dir: "artifacts/checkpoints/frontier".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
struct ObservabilityConfigSection {
    structured_logs: bool,
    metrics: bool,
    trace: bool,
    failure_classification: bool,
    artifact_dir: String,
}

impl Default for ObservabilityConfigSection {
    fn default() -> Self {
        Self {
            structured_logs: true,
            metrics: true,
            trace: true,
            failure_classification: true,
            artifact_dir: "artifacts/observability".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
struct CacheConfigSection {
    enabled: bool,
    store_path: String,
    delta_fetch: bool,
    revalidate_seconds: u64,
}

impl Default for CacheConfigSection {
    fn default() -> Self {
        Self {
            enabled: true,
            store_path: "artifacts/cache/incremental.json".to_string(),
            delta_fetch: true,
            revalidate_seconds: 3600,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct PluginConfigSection {
    enabled: bool,
    manifest: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
struct ScrapyConfigSection {
    #[serde(default)]
    runner: String,
    #[serde(default)]
    plugins: Vec<String>,
    #[serde(default)]
    pipelines: Vec<String>,
    #[serde(default)]
    spider_middlewares: Vec<String>,
    #[serde(default)]
    downloader_middlewares: Vec<String>,
    #[serde(default)]
    component_config: BTreeMap<String, serde_json::Value>,
    #[serde(default)]
    spiders: HashMap<String, ScrapySpiderConfigSection>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
struct ScrapySpiderConfigSection {
    #[serde(default)]
    runner: String,
    #[serde(default)]
    url: String,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pipelines: Vec<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    spider_middlewares: Vec<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    downloader_middlewares: Vec<String>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    component_config: BTreeMap<String, serde_json::Value>,
}

impl Default for NodeReverseConfigSection {
    fn default() -> Self {
        Self {
            enabled: true,
            base_url: "http://localhost:3000".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct StorageSection {
    checkpoint_dir: String,
    dataset_dir: String,
    export_dir: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ExportSection {
    format: String,
    output_path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
struct DoctorSection {
    #[serde(default)]
    network_targets: Vec<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    redis_url: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct RuntimeJobSpec {
    name: String,
    runtime: String,
    #[serde(default)]
    priority: Option<u32>,
    target: RuntimeTargetSection,
    #[serde(default)]
    extract: Vec<RuntimeExtractSpec>,
    output: RuntimeOutputSection,
    #[serde(default)]
    resources: Option<RuntimeResourceSection>,
    #[serde(default)]
    browser: Option<RuntimeBrowserSection>,
    #[serde(default)]
    anti_bot: Option<RuntimeAntiBotSection>,
    #[serde(default)]
    policy: Option<RuntimePolicySection>,
    #[serde(default)]
    schedule: Option<RuntimeScheduleSection>,
    #[serde(default)]
    metadata: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize, Serialize)]
struct RuntimeTargetSection {
    url: String,
    #[serde(default = "default_method")]
    method: String,
    #[serde(default)]
    headers: HashMap<String, String>,
    #[serde(default)]
    cookies: HashMap<String, String>,
    #[serde(default)]
    body: Option<String>,
    #[serde(default)]
    proxy: Option<String>,
    #[serde(default)]
    timeout_ms: Option<u64>,
    #[serde(default)]
    allowed_domains: Vec<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct RuntimeOutputSection {
    format: String,
    #[serde(default)]
    path: Option<String>,
    #[serde(default)]
    directory: Option<String>,
    #[serde(default)]
    artifact_prefix: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct RuntimeResourceSection {
    #[serde(default)]
    concurrency: Option<u64>,
    #[serde(default)]
    retries: Option<u32>,
    #[serde(default)]
    timeout_ms: Option<u64>,
    #[serde(default)]
    rate_limit_per_sec: Option<f64>,
    #[serde(default)]
    download_dir: Option<String>,
    #[serde(default)]
    temp_dir: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct RuntimeExtractSpec {
    field: String,
    #[serde(rename = "type")]
    extract_type: String,
    #[serde(default)]
    expr: Option<String>,
    #[serde(default)]
    attr: Option<String>,
    #[serde(default)]
    path: Option<String>,
    #[serde(default)]
    required: Option<bool>,
    #[serde(default)]
    schema: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize, Serialize)]
struct RuntimeBrowserSection {
    #[serde(default)]
    headless: Option<bool>,
    #[serde(default)]
    profile: Option<String>,
    #[serde(default)]
    capture: Vec<String>,
    #[serde(default)]
    actions: Vec<RuntimeBrowserAction>,
}

#[derive(Debug, Deserialize, Serialize)]
struct RuntimeBrowserAction {
    #[serde(rename = "type")]
    action_type: String,
    #[serde(default)]
    selector: Option<String>,
    #[serde(default)]
    value: Option<String>,
    #[serde(default)]
    url: Option<String>,
    #[serde(default)]
    timeout_ms: Option<u64>,
    #[serde(default)]
    save_as: Option<String>,
    #[serde(default)]
    extra: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize, Serialize)]
struct RuntimeAntiBotSection {
    #[serde(default)]
    identity_profile: Option<String>,
    #[serde(default)]
    proxy_pool: Option<String>,
    #[serde(default)]
    session_mode: Option<String>,
    #[serde(default)]
    stealth: Option<bool>,
    #[serde(default)]
    fallback_runtime: Option<String>,
    #[serde(default)]
    challenge_policy: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct RuntimePolicySection {
    #[serde(default)]
    max_pages: Option<u64>,
    #[serde(default)]
    max_depth: Option<u64>,
    #[serde(default)]
    respect_robots_txt: Option<bool>,
    #[serde(default)]
    same_domain_only: Option<bool>,
    #[serde(default)]
    budget: Option<RuntimeBudgetSection>,
}

#[derive(Debug, Deserialize, Serialize)]
struct RuntimeBudgetSection {
    #[serde(default)]
    requests: Option<u64>,
    #[serde(default)]
    bytes_in: Option<u64>,
    #[serde(default)]
    wall_time_ms: Option<u64>,
}

#[derive(Debug, Deserialize, Serialize)]
struct RuntimeScheduleSection {
    #[serde(default)]
    mode: Option<String>,
    #[serde(default)]
    cron: Option<String>,
    #[serde(default)]
    queue_name: Option<String>,
    #[serde(default)]
    delay_seconds: Option<u64>,
}

fn default_method() -> String {
    "GET".to_string()
}

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        print_help();
        return;
    }

    let exit_code = match args[1].as_str() {
        "config" => handle_config(&args[2..]),
        "crawl" => handle_crawl(&args[2..]),
        "browser" => handle_browser(&args[2..]),
        "ai" => handle_ai(&args[2..]),
        "doctor" => handle_doctor(&args[2..], "doctor"),
        "preflight" => handle_doctor(&args[2..], "preflight"),
        "export" => handle_export(&args[2..]),
        "curl" => handle_curl(&args[2..]),
        "run" => handle_run(&args[2..]),
        "job" => handle_job(&args[2..]),
        "async-job" => handle_async_job(&args[2..]),
        "workflow" => handle_workflow(&args[2..]),
        "jobdir" => handle_jobdir(&args[2..]),
        "http-cache" => handle_http_cache(&args[2..]),
        "console" => handle_console(&args[2..]),
        "audit" => handle_audit(&args[2..]),
        "web" => handle_web(&args[2..]),
        "media" => handle_media(&args[2..]),
        "ultimate" => handle_ultimate(&args[2..]),
        "sitemap-discover" => handle_sitemap_discover(&args[2..]),
        "plugins" => handle_plugins(&args[2..]),
        "selector-studio" => handle_selector_studio(&args[2..]),
        "scrapy" => handle_scrapy(&args[2..]),
        "profile-site" => handle_profile_site(&args[2..]),
        "research" => handle_research(&args[2..]),
        "node-reverse" => handle_node_reverse(&args[2..]),
        "anti-bot" | "antibot" => handle_antibot(&args[2..]),
        "capabilities" => {
            print_capabilities();
            0
        }
        "version" | "-v" | "--version" => {
            println!("rustspider {}", env!("CARGO_PKG_VERSION"));
            0
        }
        "help" | "-h" | "--help" => {
            print_help();
            0
        }
        unknown => {
            eprintln!("unknown command: {unknown}");
            print_help();
            2
        }
    };

    if exit_code != 0 {
        std::process::exit(exit_code);
    }
}

fn print_help() {
    println!("rustspider {}", env!("CARGO_PKG_VERSION"));
    println!("usage: rustspider <command> [options]");
    println!();
    println!("commands:");
    println!("  config   write a shared contract config");
    println!("           usage: config init [--output <path>]");
    println!("  crawl   run a real crawl against a URL");
    println!("          usage: crawl --url <url> [--config <path>] [--concurrency <n>] [--max-requests <n>]");
    println!("  browser fetch or instrument a dynamic page");
    println!("          usage: browser fetch --url <url> [--config <path>] [--screenshot <path>]");
    println!("          usage: browser trace|mock|codegen ...");
    println!("  ai      run AI-assisted extraction, understanding, or spider generation");
    println!("          usage: ai --url <url> [--instructions <text>] [--schema-json <json>]");
    println!("  doctor  run runtime preflight checks");
    println!("          usage: doctor [--json] [--config <path>] [--writable-path <path>] [--network-target <host:port>]");
    println!("  preflight run runtime preflight checks through the main CLI surface");
    println!("          usage: preflight [--json] [--config <path>] [--writable-path <path>] [--network-target <host:port>]");
    println!("  export  export contract-aligned data");
    println!("          usage: export --input <path> --format <json|jsonl|csv|md> --output <path>");
    println!("  curl    convert curl commands into Rust code");
    println!("          usage: curl convert --command <curl> [--target <rust|reqwest|ureq>]");
    println!("  run     execute an inline pyspider-style URL job");
    println!("          usage: run <url> [--runtime <http|browser|media|ai>] [--output <path>]");
    println!("  job     execute a normalized JobSpec JSON file");
    println!("          usage: job --file <job.json>");
    println!("  async-job execute a normalized JobSpec through the async parity surface");
    println!("          usage: async-job --file <job.json>");
    println!("  workflow execute the lightweight workflow orchestration surface");
    println!("          usage: workflow run --file <workflow.json>");
    println!("  jobdir  manage a shared pause/resume job directory");
    println!("          usage: jobdir <init|status|pause|resume|clear> --path <jobdir>");
    println!("  http-cache inspect or seed the shared HTTP cache store");
    println!("          usage: http-cache <status|clear|seed> --path <cache.json>");
    println!("  console inspect shared control-plane and jobdir artifacts");
    println!("          usage: console <snapshot|tail> --control-plane <dir>");
    println!("  audit   inspect audit/event traces through the shared control-plane view");
    println!("          usage: audit <snapshot|tail> --control-plane <dir>");
    println!("  web     launch the embedded web surface");
    println!("          usage: web [--mode <ui|api>] [--host <host>] [--port <port>]");
    println!("  media   inspect or download media resources");
    println!("          usage: media --url <url> [--output <dir>] [--download]");
    println!("  ultimate run the advanced ultimate spider");
    println!(
        "          usage: ultimate --url <url> [--config <path>] [--reverse-service-url <url>]"
    );
    println!("  sitemap-discover discover sitemap URLs before crawling");
    println!("          usage: sitemap-discover --url <url> [--sitemap-file <path>]");
    println!("  plugins inspect shared plugin/integration manifests");
    println!("          usage: plugins list [--manifest <path>]");
    println!("  selector-studio test selectors and extraction expressions");
    println!("          usage: selector-studio --html-file <path> --type <css|css_attr|xpath|regex> --expr <expr>");
    println!("  scrapy run scrapy-style demo authoring flow");
    println!("          usage: scrapy demo [--url <url>] [--html-file <path>] [--output <path>]");
    println!("          usage: scrapy shell [--url <url>] [--html-file <path>] [--type <css|css_attr|xpath|regex>] --expr <expr>");
    println!("          usage: scrapy contracts <init|validate> --project <dir>");
    println!("          usage: scrapy plan-ai|sync-ai|auth-validate|auth-capture|scaffold-ai --project <dir> [--url <url>]");
    println!("  profile-site analyze a target before crawling");
    println!("          usage: profile-site --url <url> [--html-file <path>] [--base-url <url>]");
    println!("  research run the pyspider-style research runtime surfaces");
    println!("          usage: research <run|async|soak> ...");
    println!("  node-reverse call the NodeReverse service directly");
    println!("          usage: node-reverse <health|profile|detect|fingerprint-spoof|tls-fingerprint|canvas-fingerprint|analyze-crypto|signature-reverse|ast|webpack|function-call|browser-simulate> [options]");
    println!("  anti-bot run anti-bot utilities and local block profiling");
    println!("          usage: anti-bot <headers|profile> [options]");
    println!("  capabilities  print integrated runtime capabilities");
    println!("  version show version");
    println!("  help    show help");
}

fn default_contract_config() -> ContractConfig {
    ContractConfig {
        version: 1,
        project: ProjectSection {
            name: "rustspider-project".to_string(),
        },
        runtime: "rust".to_string(),
        crawl: CrawlSection {
            urls: vec!["https://example.com".to_string()],
            concurrency: 5,
            max_requests: 100,
            max_depth: 3,
            timeout_seconds: 30,
        },
        sitemap: SitemapSection {
            enabled: false,
            url: "https://example.com/sitemap.xml".to_string(),
            max_urls: 50,
        },
        browser: BrowserSection {
            enabled: true,
            headless: true,
            timeout_seconds: 30,
            user_agent: String::new(),
            screenshot_path: "artifacts/browser/page.png".to_string(),
            html_path: "artifacts/browser/page.html".to_string(),
            storage_state_file: String::new(),
            cookies_file: String::new(),
            auth_file: String::new(),
        },
        anti_bot: AntiBotConfigSection::default(),
        node_reverse: NodeReverseConfigSection::default(),
        middleware: MiddlewareConfigSection {
            user_agent_rotation: true,
            respect_robots_txt: true,
            min_request_interval_ms: 200,
        },
        pipeline: PipelineConfigSection {
            console: true,
            dataset: true,
            jsonl_path: "artifacts/exports/results.jsonl".to_string(),
        },
        auto_throttle: AutoThrottleConfigSection {
            enabled: true,
            start_delay_ms: 200,
            max_delay_ms: 5000,
            target_response_time_ms: 2000,
        },
        frontier: FrontierConfigSection {
            enabled: true,
            autoscale: true,
            min_concurrency: 1,
            max_concurrency: 16,
            lease_ttl_seconds: 30,
            max_inflight_per_domain: 2,
            checkpoint_id: "runtime-frontier".to_string(),
            checkpoint_dir: "artifacts/checkpoints/frontier".to_string(),
        },
        observability: ObservabilityConfigSection {
            structured_logs: true,
            metrics: true,
            trace: true,
            failure_classification: true,
            artifact_dir: "artifacts/observability".to_string(),
        },
        cache: CacheConfigSection {
            enabled: true,
            store_path: "artifacts/cache/incremental.json".to_string(),
            delta_fetch: true,
            revalidate_seconds: 3600,
        },
        plugins: PluginConfigSection {
            enabled: true,
            manifest: "contracts/integration-catalog.json".to_string(),
        },
        scrapy: ScrapyConfigSection {
            runner: "http".to_string(),
            plugins: vec![],
            pipelines: vec![],
            spider_middlewares: vec![],
            downloader_middlewares: vec![],
            component_config: BTreeMap::from([
                (
                    "field_injector".to_string(),
                    serde_json::json!({"fields": {}}),
                ),
                (
                    "request_headers".to_string(),
                    serde_json::json!({"headers": {}}),
                ),
            ]),
            spiders: HashMap::from([(
                "demo".to_string(),
                ScrapySpiderConfigSection {
                    runner: "http".to_string(),
                    url: "https://example.com".to_string(),
                    pipelines: vec![],
                    spider_middlewares: vec![],
                    downloader_middlewares: vec![],
                    component_config: BTreeMap::new(),
                },
            )]),
        },
        storage: StorageSection {
            checkpoint_dir: "artifacts/checkpoints".to_string(),
            dataset_dir: "artifacts/datasets".to_string(),
            export_dir: "artifacts/exports".to_string(),
        },
        export: ExportSection {
            format: "json".to_string(),
            output_path: "artifacts/exports/results.json".to_string(),
        },
        doctor: DoctorSection {
            network_targets: vec!["https://example.com".to_string()],
            redis_url: None,
        },
    }
}

struct DeclarativeResponseContextSpiderMiddleware;

impl rustspider::scrapy::SpiderMiddleware for DeclarativeResponseContextSpiderMiddleware {
    fn process_spider_output(
        &self,
        response: &rustspider::scrapy::Response,
        result: Vec<rustspider::scrapy::Output>,
        _spider: &rustspider::scrapy::Spider,
    ) -> Result<Vec<rustspider::scrapy::Output>, String> {
        Ok(result
            .into_iter()
            .map(|output| match output {
                rustspider::scrapy::Output::Item(item) => rustspider::scrapy::Output::Item(
                    item.set("response_url", response.url.clone())
                        .set("response_status", response.status_code),
                ),
                other => other,
            })
            .collect())
    }
}

struct DeclarativeRequestHeadersMiddleware {
    headers: BTreeMap<String, String>,
}

impl rustspider::scrapy::DownloaderMiddleware for DeclarativeRequestHeadersMiddleware {
    fn process_request(
        &self,
        mut request: rustspider::scrapy::Request,
        _spider: &rustspider::scrapy::Spider,
    ) -> Result<rustspider::scrapy::Request, String> {
        for (key, value) in &self.headers {
            request.headers.insert(key.clone(), value.clone());
        }
        Ok(request)
    }

    fn process_response(
        &self,
        response: rustspider::scrapy::Response,
        _spider: &rustspider::scrapy::Spider,
    ) -> Result<rustspider::scrapy::Response, String> {
        Ok(response)
    }
}

fn build_declarative_scrapy_pipelines(
    cfg: &ContractConfig,
    spider_name: &str,
) -> Vec<rustspider::scrapy::ItemPipeline> {
    let mut pipelines = Vec::new();
    let component_config = merged_scrapy_component_config_for_spider(cfg, spider_name);
    for name in configured_scrapy_pipelines_for_spider(cfg, spider_name) {
        if name.trim() == "field-injector" {
            let fields = component_config
                .get("field_injector")
                .and_then(|value| value.get("fields"))
                .and_then(|value| value.as_object())
                .map(|value| {
                    value
                        .iter()
                        .map(|(key, value)| (key.clone(), value.clone()))
                        .collect::<BTreeMap<_, _>>()
                })
                .unwrap_or_default();
            pipelines.push(Arc::new(move |item: rustspider::scrapy::Item| {
                let mut current = item;
                for (key, value) in &fields {
                    current = current.set(key, value.clone());
                }
                Ok(current)
            }) as rustspider::scrapy::ItemPipeline);
        }
    }
    pipelines
}

fn build_declarative_scrapy_spider_middlewares(
    cfg: &ContractConfig,
    spider_name: &str,
) -> Vec<rustspider::scrapy::SpiderMiddlewareHandle> {
    let mut middlewares = Vec::new();
    for name in configured_scrapy_spider_middlewares_for_spider(cfg, spider_name) {
        if name.trim() == "response-context" {
            middlewares.push(Arc::new(DeclarativeResponseContextSpiderMiddleware)
                as rustspider::scrapy::SpiderMiddlewareHandle);
        }
    }
    middlewares
}

fn build_declarative_scrapy_downloader_middlewares(
    cfg: &ContractConfig,
    spider_name: &str,
) -> Vec<rustspider::scrapy::DownloaderMiddlewareHandle> {
    let mut middlewares = Vec::new();
    let component_config = merged_scrapy_component_config_for_spider(cfg, spider_name);
    for name in configured_scrapy_downloader_middlewares_for_spider(cfg, spider_name) {
        if name.trim() == "request-headers" {
            let headers = component_config
                .get("request_headers")
                .and_then(|value| value.get("headers"))
                .and_then(|value| value.as_object())
                .map(|value| {
                    value
                        .iter()
                        .map(|(key, value)| {
                            (key.clone(), value.as_str().unwrap_or_default().to_string())
                        })
                        .collect::<BTreeMap<_, _>>()
                })
                .unwrap_or_default();
            middlewares.push(Arc::new(DeclarativeRequestHeadersMiddleware { headers })
                as rustspider::scrapy::DownloaderMiddlewareHandle);
        }
    }
    middlewares
}

fn rust_component_name<T: ?Sized>(_: &T) -> String {
    let raw = std::any::type_name::<T>();
    raw.rsplit("::").next().unwrap_or(raw).to_string()
}

fn string_list(values: &[String]) -> Vec<String> {
    values
        .iter()
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
        .collect()
}

fn merge_unique_strings(base: &[String], overlay: &[String]) -> Vec<String> {
    let mut merged = Vec::new();
    for value in base.iter().chain(overlay.iter()) {
        let trimmed = value.trim();
        if trimmed.is_empty() {
            continue;
        }
        if merged.iter().any(|existing: &String| existing == trimmed) {
            continue;
        }
        merged.push(trimmed.to_string());
    }
    merged
}

fn merge_unique_json_string_values(
    base: &[String],
    spiders: &[serde_json::Value],
    field: &str,
) -> Vec<String> {
    let mut merged = string_list(base);
    for spider in spiders {
        if let Some(values) = spider.get(field).and_then(|value| value.as_array()) {
            for value in values {
                let Some(text) = value.as_str() else {
                    continue;
                };
                let trimmed = text.trim();
                if trimmed.is_empty() {
                    continue;
                }
                if merged.iter().any(|existing| existing == trimmed) {
                    continue;
                }
                merged.push(trimmed.to_string());
            }
        }
    }
    merged
}

fn merge_json_values(base: &serde_json::Value, overlay: &serde_json::Value) -> serde_json::Value {
    match (base, overlay) {
        (serde_json::Value::Object(base_map), serde_json::Value::Object(overlay_map)) => {
            let mut merged = base_map.clone();
            for (key, value) in overlay_map {
                let next = merged
                    .get(key)
                    .map(|existing| merge_json_values(existing, value))
                    .unwrap_or_else(|| value.clone());
                merged.insert(key.clone(), next);
            }
            serde_json::Value::Object(merged)
        }
        (_, value) => value.clone(),
    }
}

fn configured_scrapy_pipelines_for_spider(cfg: &ContractConfig, spider_name: &str) -> Vec<String> {
    cfg.scrapy
        .spiders
        .get(spider_name)
        .map(|spider| merge_unique_strings(&cfg.scrapy.pipelines, &spider.pipelines))
        .unwrap_or_else(|| string_list(&cfg.scrapy.pipelines))
}

fn configured_scrapy_spider_middlewares_for_spider(
    cfg: &ContractConfig,
    spider_name: &str,
) -> Vec<String> {
    cfg.scrapy
        .spiders
        .get(spider_name)
        .map(|spider| {
            merge_unique_strings(&cfg.scrapy.spider_middlewares, &spider.spider_middlewares)
        })
        .unwrap_or_else(|| string_list(&cfg.scrapy.spider_middlewares))
}

fn configured_scrapy_downloader_middlewares_for_spider(
    cfg: &ContractConfig,
    spider_name: &str,
) -> Vec<String> {
    cfg.scrapy
        .spiders
        .get(spider_name)
        .map(|spider| {
            merge_unique_strings(
                &cfg.scrapy.downloader_middlewares,
                &spider.downloader_middlewares,
            )
        })
        .unwrap_or_else(|| string_list(&cfg.scrapy.downloader_middlewares))
}

fn merged_scrapy_component_config_for_spider(
    cfg: &ContractConfig,
    spider_name: &str,
) -> BTreeMap<String, serde_json::Value> {
    let mut merged = cfg.scrapy.component_config.clone();
    if let Some(spider) = cfg.scrapy.spiders.get(spider_name) {
        for (key, value) in &spider.component_config {
            let next = merged
                .get(key)
                .map(|existing| merge_json_values(existing, value))
                .unwrap_or_else(|| value.clone());
            merged.insert(key.clone(), next);
        }
    }
    merged
}

fn append_rust_declarative_component_checks(
    checks: &mut Vec<serde_json::Value>,
    cfg: &ContractConfig,
) {
    let pipelines = string_list(&cfg.scrapy.pipelines);
    let spider_middlewares = string_list(&cfg.scrapy.spider_middlewares);
    let downloader_middlewares = string_list(&cfg.scrapy.downloader_middlewares);
    checks.push(serde_json::json!({
        "name": "components",
        "status": "passed",
        "details": format!(
            "pipelines={} spider_middlewares={} downloader_middlewares={}",
            pipelines.len(),
            spider_middlewares.len(),
            downloader_middlewares.len()
        )
    }));
    for name in pipelines {
        checks.push(serde_json::json!({"name": format!("pipeline:{name}"), "status": "passed", "details": "declarative pipeline"}));
    }
    for name in spider_middlewares {
        checks.push(serde_json::json!({"name": format!("spider_middleware:{name}"), "status": "passed", "details": "declarative spider middleware"}));
    }
    for name in downloader_middlewares {
        checks.push(serde_json::json!({"name": format!("downloader_middleware:{name}"), "status": "passed", "details": "declarative downloader middleware"}));
    }
}

fn resolve_config_path(explicit: Option<&String>) -> Option<PathBuf> {
    if let Some(path) = explicit {
        let p = PathBuf::from(path);
        if p.exists() {
            return Some(p);
        }
    }
    for candidate in [
        "spider-framework.yaml",
        "spider-framework.yml",
        "spider-framework.json",
        "config.yaml",
    ] {
        let p = PathBuf::from(candidate);
        if p.exists() {
            return Some(p);
        }
    }
    None
}

fn load_contract_config(explicit: Option<&String>) -> Result<ContractConfig, String> {
    if let Some(path) = explicit {
        let explicit_path = PathBuf::from(path);
        if !explicit_path.exists() {
            return Err(format!(
                "config file not found: {}",
                explicit_path.display()
            ));
        }
    }

    let Some(path) = resolve_config_path(explicit) else {
        return validate_contract_config(default_contract_config(), "rust");
    };
    let content = fs::read_to_string(&path)
        .map_err(|err| format!("failed to read config {}: {err}", path.display()))?;
    let config = if path.extension().map(|s| s == "json").unwrap_or(false) {
        serde_json::from_str(&content).map_err(|err| format!("invalid json config: {err}"))?
    } else {
        serde_yaml::from_str(&content).map_err(|err| format!("invalid yaml config: {err}"))?
    };
    validate_contract_config(config, "rust")
}

fn validate_contract_config(
    config: ContractConfig,
    expected_runtime: &str,
) -> Result<ContractConfig, String> {
    let mut errors = Vec::new();
    if config.version < 1 {
        errors.push("version must be an integer >= 1".to_string());
    }
    if config.project.name.trim().is_empty() {
        errors.push("project.name must be a non-empty string".to_string());
    }
    if config.runtime != expected_runtime {
        errors.push(format!(
            "runtime mismatch: expected {expected_runtime:?}, got {:?}",
            config.runtime
        ));
    }
    if config.crawl.urls.is_empty() {
        errors.push("crawl.urls must be a non-empty string array".to_string());
    }
    if config.crawl.concurrency < 1 {
        errors.push("crawl.concurrency must be an integer >= 1".to_string());
    }
    if config.crawl.max_requests < 1 {
        errors.push("crawl.max_requests must be an integer >= 1".to_string());
    }
    if config.crawl.timeout_seconds < 1 {
        errors.push("crawl.timeout_seconds must be an integer >= 1".to_string());
    }
    if config.browser.timeout_seconds < 1 {
        errors.push("browser.timeout_seconds must be an integer >= 1".to_string());
    }
    if config.browser.screenshot_path.trim().is_empty() {
        errors.push("browser.screenshot_path must be a non-empty string".to_string());
    }
    if config.browser.html_path.trim().is_empty() {
        errors.push("browser.html_path must be a non-empty string".to_string());
    }
    if config.anti_bot.profile.trim().is_empty() {
        errors.push("anti_bot.profile must be a non-empty string".to_string());
    }
    if config.node_reverse.base_url.trim().is_empty() {
        errors.push("node_reverse.base_url must be a non-empty string".to_string());
    }
    if config.storage.checkpoint_dir.trim().is_empty() {
        errors.push("storage.checkpoint_dir must be a non-empty string".to_string());
    }
    if config.storage.dataset_dir.trim().is_empty() {
        errors.push("storage.dataset_dir must be a non-empty string".to_string());
    }
    if config.storage.export_dir.trim().is_empty() {
        errors.push("storage.export_dir must be a non-empty string".to_string());
    }
    if !matches!(config.export.format.as_str(), "json" | "csv" | "md") {
        errors.push("export.format must be one of [json, jsonl, csv, md]".to_string());
    }
    if config.export.output_path.trim().is_empty() {
        errors.push("export.output_path must be a non-empty string".to_string());
    }
    if config.frontier.min_concurrency < 1 {
        errors.push("frontier.min_concurrency must be an integer >= 1".to_string());
    }
    if config.frontier.max_concurrency < config.frontier.min_concurrency {
        errors.push("frontier.max_concurrency must be >= frontier.min_concurrency".to_string());
    }
    if config.frontier.lease_ttl_seconds < 1 {
        errors.push("frontier.lease_ttl_seconds must be an integer >= 1".to_string());
    }
    if config.frontier.max_inflight_per_domain < 1 {
        errors.push("frontier.max_inflight_per_domain must be an integer >= 1".to_string());
    }
    if config.frontier.checkpoint_id.trim().is_empty() {
        errors.push("frontier.checkpoint_id must be a non-empty string".to_string());
    }
    if config.frontier.checkpoint_dir.trim().is_empty() {
        errors.push("frontier.checkpoint_dir must be a non-empty string".to_string());
    }
    if config.observability.artifact_dir.trim().is_empty() {
        errors.push("observability.artifact_dir must be a non-empty string".to_string());
    }
    if config.cache.store_path.trim().is_empty() {
        errors.push("cache.store_path must be a non-empty string".to_string());
    }
    if config.cache.revalidate_seconds < 1 {
        errors.push("cache.revalidate_seconds must be an integer >= 1".to_string());
    }
    if config
        .doctor
        .network_targets
        .iter()
        .any(|target| target.trim().is_empty())
    {
        errors.push("doctor.network_targets must only contain non-empty strings".to_string());
    }
    validate_named_components(
        &config.scrapy.pipelines,
        "scrapy.pipelines",
        &["field-injector"],
        &mut errors,
    );
    validate_named_components(
        &config.scrapy.spider_middlewares,
        "scrapy.spider_middlewares",
        &["response-context"],
        &mut errors,
    );
    validate_named_components(
        &config.scrapy.downloader_middlewares,
        "scrapy.downloader_middlewares",
        &["request-headers"],
        &mut errors,
    );
    for (spider_name, spider_cfg) in &config.scrapy.spiders {
        let prefix = format!("scrapy.spiders.{spider_name}");
        validate_named_components(
            &spider_cfg.pipelines,
            &(prefix.clone() + ".pipelines"),
            &["field-injector"],
            &mut errors,
        );
        validate_named_components(
            &spider_cfg.spider_middlewares,
            &(prefix.clone() + ".spider_middlewares"),
            &["response-context"],
            &mut errors,
        );
        validate_named_components(
            &spider_cfg.downloader_middlewares,
            &(prefix.clone() + ".downloader_middlewares"),
            &["request-headers"],
            &mut errors,
        );
    }

    if errors.is_empty() {
        Ok(config)
    } else {
        Err(errors.join("; "))
    }
}

fn validate_named_components(
    values: &[String],
    name: &str,
    allowed: &[&str],
    errors: &mut Vec<String>,
) {
    for value in values {
        let trimmed = value.trim();
        if trimmed.is_empty() {
            errors.push(format!("{name} must be a string array"));
            return;
        }
        if !allowed.iter().any(|candidate| candidate == &trimmed) {
            errors.push(format!("{name} contains unsupported component: {trimmed}"));
        }
    }
}

fn handle_config(args: &[String]) -> i32 {
    if args.first().map(|s| s.as_str()) != Some("init") {
        eprintln!("usage: rustspider config init [--output <path>]");
        return 2;
    }
    let mut output = "spider-framework.yaml".to_string();
    let mut i = 1usize;
    while i < args.len() {
        match args[i].as_str() {
            "--output" => {
                if let Some(value) = args.get(i + 1) {
                    output = value.clone();
                    i += 2;
                } else {
                    eprintln!("missing value for --output");
                    return 2;
                }
            }
            unknown => {
                eprintln!("unknown config argument: {unknown}");
                return 2;
            }
        }
    }
    let target = PathBuf::from(&output);
    if let Some(parent) = target.parent() {
        let _ = fs::create_dir_all(parent);
    }
    match serde_yaml::to_string(&default_contract_config()) {
        Ok(yaml) => {
            if fs::write(&target, yaml).is_err() {
                eprintln!("failed to write config: {}", target.display());
                return 1;
            }
            println!("Wrote shared config: {}", target.display());
            0
        }
        Err(err) => {
            eprintln!("failed to render config: {err}");
            1
        }
    }
}

fn handle_crawl(args: &[String]) -> i32 {
    let mut url: Option<String> = None;
    let mut concurrency = 5usize;
    let mut max_requests = 100usize;
    let mut config_path: Option<String> = None;

    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--config" => {
                if let Some(value) = args.get(i + 1) {
                    config_path = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --config");
                    return 2;
                }
            }
            "--url" | "-u" => {
                if let Some(value) = args.get(i + 1) {
                    url = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --url");
                    return 2;
                }
            }
            "--concurrency" | "-c" => {
                if let Some(value) = args.get(i + 1) {
                    match value.parse::<usize>() {
                        Ok(parsed) => concurrency = parsed,
                        Err(err) => {
                            eprintln!("invalid concurrency value: {err}");
                            return 2;
                        }
                    }
                    i += 2;
                } else {
                    eprintln!("missing value for --concurrency");
                    return 2;
                }
            }
            "--max-requests" | "-m" => {
                if let Some(value) = args.get(i + 1) {
                    match value.parse::<usize>() {
                        Ok(parsed) => max_requests = parsed,
                        Err(err) => {
                            eprintln!("invalid max-requests value: {err}");
                            return 2;
                        }
                    }
                    i += 2;
                } else {
                    eprintln!("missing value for --max-requests");
                    return 2;
                }
            }
            other => {
                if url.is_none() {
                    url = Some(other.to_string());
                    i += 1;
                } else {
                    eprintln!("unknown crawl argument: {other}");
                    return 2;
                }
            }
        }
    }

    let cfg = match load_contract_config(config_path.as_ref()) {
        Ok(cfg) => cfg,
        Err(err) => {
            eprintln!("config error: {err}");
            return 2;
        }
    };
    let mut targets = cfg.crawl.urls.clone();
    if url.is_none() {
        url = targets.first().cloned();
    }
    concurrency = if cfg.crawl.concurrency > 0 {
        cfg.crawl.concurrency
    } else {
        concurrency
    };
    max_requests = if cfg.crawl.max_requests > 0 {
        cfg.crawl.max_requests
    } else {
        max_requests
    };

    let Some(url) = url else {
        eprintln!("crawl requires a URL");
        return 2;
    };
    targets = if url.trim().is_empty() {
        targets
    } else {
        vec![url.clone()]
    };
    if cfg.sitemap.enabled {
        targets = merge_unique_targets(targets, discover_sitemap_targets(&url, &cfg.sitemap));
    }

    let anti_bot_handler = AntiBotHandler::new();
    let configured_user_agent = if !cfg.browser.user_agent.trim().is_empty() {
        cfg.browser.user_agent.clone()
    } else if cfg.anti_bot.enabled {
        anti_bot_handler
            .get_random_headers()
            .get("User-Agent")
            .cloned()
            .unwrap_or_else(|| {
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36".to_string()
            })
    } else {
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36".to_string()
    };
    let configured_proxy =
        if cfg.anti_bot.proxy_pool.trim().is_empty() || cfg.anti_bot.proxy_pool == "local" {
            None
        } else {
            cfg.anti_bot
                .proxy_pool
                .split(',')
                .map(|item| item.trim().to_string())
                .find(|item| !item.is_empty())
        };

    if cfg.node_reverse.enabled && !cfg.node_reverse.base_url.trim().is_empty() {
        if let Ok(response) = reqwest::blocking::get(&url) {
            let status = response.status().as_u16();
            if let Ok(body) = response.text() {
                if let Ok(runtime) = tokio::runtime::Builder::new_current_thread()
                    .enable_all()
                    .build()
                {
                    let client = NodeReverseClient::new(cfg.node_reverse.base_url.clone());
                    if let Ok(profile) =
                        runtime.block_on(client.profile_anti_bot(&AntiBotProfileRequest {
                            html: body,
                            js: String::new(),
                            headers: std::collections::HashMap::new(),
                            cookies: String::new(),
                            status_code: Some(status),
                            url: url.clone(),
                        }))
                    {
                        if profile.success {
                            println!(
                                "anti-bot: level={} signals={}",
                                profile.level,
                                profile.signals.join(",")
                            );
                        }
                    }
                }
            }
        }
    }

    let delay_ms = std::cmp::max(
        cfg.middleware.min_request_interval_ms,
        if cfg.auto_throttle.enabled {
            cfg.auto_throttle.start_delay_ms
        } else {
            0
        },
    );
    let mut builder = SpiderBuilder::new()
        .name("rustspider-cli")
        .concurrency(concurrency)
        .max_requests(max_requests)
        .user_agent(&configured_user_agent)
        .delay(Duration::from_millis(delay_ms));
    if let Some(proxy) = configured_proxy.as_deref() {
        builder = builder.proxy(proxy);
    }

    let spider = match builder.build() {
        Ok(spider) => spider,
        Err(err) => {
            eprintln!("failed to build spider: {err}");
            return 1;
        }
    };

    for target in &targets {
        if let Err(err) = spider.add_url(target) {
            eprintln!("failed to enqueue url: {err}");
            return 1;
        }
    }

    let runtime = match tokio::runtime::Runtime::new() {
        Ok(runtime) => runtime,
        Err(err) => {
            eprintln!("failed to create tokio runtime: {err}");
            return 1;
        }
    };

    if let Err(err) = runtime.block_on(spider.run()) {
        eprintln!("crawl failed: {err}");
        return 1;
    }

    println!("{}", spider.get_stats());
    0
}

fn handle_browser(args: &[String]) -> i32 {
    match args.first().map(|s| s.as_str()) {
        Some("fetch") => {}
        Some("trace") | Some("mock") | Some("codegen") => {
            return handle_browser_tooling(args[0].as_str(), &args[1..]);
        }
        _ => {
            eprintln!("usage: rustspider browser <fetch|trace|mock|codegen> ...");
            return 2;
        }
    }

    let mut url: Option<String> = None;
    let mut config_path: Option<String> = None;
    let mut screenshot: Option<String> = None;
    let mut html_path: Option<String> = None;
    let mut i = 1usize;
    while i < args.len() {
        match args[i].as_str() {
            "--config" => {
                if let Some(value) = args.get(i + 1) {
                    config_path = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --config");
                    return 2;
                }
            }
            "--url" | "-u" => {
                if let Some(value) = args.get(i + 1) {
                    url = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --url");
                    return 2;
                }
            }
            "--screenshot" => {
                if let Some(value) = args.get(i + 1) {
                    screenshot = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --screenshot");
                    return 2;
                }
            }
            "--html" => {
                if let Some(value) = args.get(i + 1) {
                    html_path = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --html");
                    return 2;
                }
            }
            other => {
                if url.is_none() {
                    url = Some(other.to_string());
                    i += 1;
                } else {
                    eprintln!("unknown browser argument: {other}");
                    return 2;
                }
            }
        }
    }

    let cfg = match load_contract_config(config_path.as_ref()) {
        Ok(cfg) => cfg,
        Err(err) => {
            eprintln!("config error: {err}");
            return 2;
        }
    };
    if url.is_none() {
        url = cfg.crawl.urls.first().cloned();
    }
    let Some(url) = url else {
        eprintln!("browser fetch requires a URL");
        return 2;
    };

    let screenshot = screenshot.unwrap_or(cfg.browser.screenshot_path.clone());
    let html_path = html_path.unwrap_or(cfg.browser.html_path.clone());

    match run_playwright_fetch(&url, &screenshot, &html_path, &cfg) {
        Ok((title, resolved_url)) => {
            println!("title: {title}");
            println!("url: {resolved_url}");
            0
        }
        Err(err) => {
            eprintln!("browser fetch failed: {err}");
            1
        }
    }
}

fn handle_browser_tooling(tooling: &str, args: &[String]) -> i32 {
    let mut url = String::new();
    let mut trace_path = String::new();
    let mut har_path = String::new();
    let mut route_manifest = String::new();
    let mut html_path = String::new();
    let mut screenshot = String::new();
    let mut output = String::new();
    let mut language = String::from("python");
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--url" if i + 1 < args.len() => {
                url = args[i + 1].clone();
                i += 2;
            }
            "--trace-path" if i + 1 < args.len() => {
                trace_path = args[i + 1].clone();
                i += 2;
            }
            "--har-path" if i + 1 < args.len() => {
                har_path = args[i + 1].clone();
                i += 2;
            }
            "--route-manifest" if i + 1 < args.len() => {
                route_manifest = args[i + 1].clone();
                i += 2;
            }
            "--html" if i + 1 < args.len() => {
                html_path = args[i + 1].clone();
                i += 2;
            }
            "--screenshot" if i + 1 < args.len() => {
                screenshot = args[i + 1].clone();
                i += 2;
            }
            "--output" if i + 1 < args.len() => {
                output = args[i + 1].clone();
                i += 2;
            }
            "--language" if i + 1 < args.len() => {
                language = args[i + 1].clone();
                i += 2;
            }
            other => {
                eprintln!("unknown browser {} argument: {}", tooling, other);
                return 2;
            }
        }
    }

    if url.trim().is_empty() {
        eprintln!("browser {} requires --url", tooling);
        return 2;
    }
    if tooling == "trace" && trace_path.trim().is_empty() {
        eprintln!("browser trace requires --trace-path");
        return 2;
    }
    if tooling == "mock" && route_manifest.trim().is_empty() {
        eprintln!("browser mock requires --route-manifest");
        return 2;
    }
    if tooling == "codegen" && output.trim().is_empty() {
        eprintln!("browser codegen requires --output");
        return 2;
    }

    let mut tool_args = vec![
        "--tooling-command".to_string(),
        tooling.to_string(),
        "--url".to_string(),
        url,
    ];
    if !trace_path.trim().is_empty() {
        tool_args.push("--trace-path".to_string());
        tool_args.push(trace_path);
    }
    if !har_path.trim().is_empty() {
        tool_args.push("--har-path".to_string());
        tool_args.push(har_path);
    }
    if !route_manifest.trim().is_empty() {
        tool_args.push("--route-manifest".to_string());
        tool_args.push(route_manifest);
    }
    if !html_path.trim().is_empty() {
        tool_args.push("--html".to_string());
        tool_args.push(html_path);
    }
    if !screenshot.trim().is_empty() {
        tool_args.push("--screenshot".to_string());
        tool_args.push(screenshot);
    }
    if !output.trim().is_empty() {
        tool_args.push("--codegen-out".to_string());
        tool_args.push(output);
    }
    if !language.trim().is_empty() {
        tool_args.push("--codegen-language".to_string());
        tool_args.push(language);
    }
    run_shared_python_tool("playwright_fetch.py", &tool_args)
}

fn handle_jobdir(args: &[String]) -> i32 {
    let Some(subcommand) = args.first().map(|value| value.as_str()) else {
        eprintln!("usage: rustspider jobdir <init|status|pause|resume|clear> --path <jobdir>");
        return 2;
    };
    if !matches!(subcommand, "init" | "status" | "pause" | "resume" | "clear") {
        eprintln!("usage: rustspider jobdir <init|status|pause|resume|clear> --path <jobdir>");
        return 2;
    }

    let mut path = String::new();
    let mut runtime = String::from("rust");
    let mut urls: Vec<String> = Vec::new();
    let mut i = 1usize;
    while i < args.len() {
        match args[i].as_str() {
            "--path" if i + 1 < args.len() => {
                path = args[i + 1].clone();
                i += 2;
            }
            "--runtime" if i + 1 < args.len() => {
                runtime = args[i + 1].clone();
                i += 2;
            }
            "--url" if i + 1 < args.len() => {
                urls.push(args[i + 1].clone());
                i += 2;
            }
            other => {
                eprintln!("unknown jobdir argument: {other}");
                return 2;
            }
        }
    }

    if path.trim().is_empty() {
        eprintln!("jobdir requires --path");
        return 2;
    }

    let mut tool_args = vec![subcommand.to_string(), "--path".to_string(), path];
    if subcommand == "init" {
        tool_args.push("--runtime".to_string());
        tool_args.push(runtime);
        for url in urls {
            tool_args.push("--url".to_string());
            tool_args.push(url);
        }
    }
    run_shared_python_tool("jobdir_tool.py", &tool_args)
}

fn handle_http_cache(args: &[String]) -> i32 {
    let Some(subcommand) = args.first().map(|value| value.as_str()) else {
        eprintln!("usage: rustspider http-cache <status|clear|seed> --path <cache.json>");
        return 2;
    };
    if !matches!(subcommand, "status" | "clear" | "seed") {
        eprintln!("usage: rustspider http-cache <status|clear|seed> --path <cache.json>");
        return 2;
    }

    let mut path = String::new();
    let mut url = String::new();
    let mut status_code = String::from("200");
    let mut etag = String::new();
    let mut last_modified = String::new();
    let mut content_hash = String::new();
    let mut i = 1usize;
    while i < args.len() {
        match args[i].as_str() {
            "--path" if i + 1 < args.len() => {
                path = args[i + 1].clone();
                i += 2;
            }
            "--url" if i + 1 < args.len() => {
                url = args[i + 1].clone();
                i += 2;
            }
            "--status-code" if i + 1 < args.len() => {
                status_code = args[i + 1].clone();
                i += 2;
            }
            "--etag" if i + 1 < args.len() => {
                etag = args[i + 1].clone();
                i += 2;
            }
            "--last-modified" if i + 1 < args.len() => {
                last_modified = args[i + 1].clone();
                i += 2;
            }
            "--content-hash" if i + 1 < args.len() => {
                content_hash = args[i + 1].clone();
                i += 2;
            }
            other => {
                eprintln!("unknown http-cache argument: {other}");
                return 2;
            }
        }
    }

    if path.trim().is_empty() {
        eprintln!("http-cache requires --path");
        return 2;
    }

    let mut tool_args = vec![subcommand.to_string(), "--path".to_string(), path];
    if subcommand == "seed" {
        if url.trim().is_empty() {
            eprintln!("http-cache seed requires --url");
            return 2;
        }
        tool_args.push("--url".to_string());
        tool_args.push(url);
        tool_args.push("--status-code".to_string());
        tool_args.push(status_code);
        if !etag.trim().is_empty() {
            tool_args.push("--etag".to_string());
            tool_args.push(etag);
        }
        if !last_modified.trim().is_empty() {
            tool_args.push("--last-modified".to_string());
            tool_args.push(last_modified);
        }
        if !content_hash.trim().is_empty() {
            tool_args.push("--content-hash".to_string());
            tool_args.push(content_hash);
        }
    }
    run_shared_python_tool("http_cache_tool.py", &tool_args)
}

fn handle_console(args: &[String]) -> i32 {
    let Some(subcommand) = args.first().map(|value| value.as_str()) else {
        eprintln!("usage: rustspider console <snapshot|tail> --control-plane <dir>");
        return 2;
    };
    if !matches!(subcommand, "snapshot" | "tail") {
        eprintln!("usage: rustspider console <snapshot|tail> --control-plane <dir>");
        return 2;
    }

    let mut control_plane = String::from("artifacts/control-plane");
    let mut jobdir = String::new();
    let mut stream = String::from("both");
    let mut lines = String::from("20");
    let mut i = 1usize;
    while i < args.len() {
        match args[i].as_str() {
            "--control-plane" if i + 1 < args.len() => {
                control_plane = args[i + 1].clone();
                i += 2;
            }
            "--jobdir" if i + 1 < args.len() => {
                jobdir = args[i + 1].clone();
                i += 2;
            }
            "--stream" if i + 1 < args.len() => {
                stream = args[i + 1].clone();
                i += 2;
            }
            "--lines" if i + 1 < args.len() => {
                lines = args[i + 1].clone();
                i += 2;
            }
            other => {
                eprintln!("unknown console argument: {other}");
                return 2;
            }
        }
    }

    let mut tool_args = vec![
        subcommand.to_string(),
        "--control-plane".to_string(),
        control_plane,
        "--lines".to_string(),
        lines,
    ];
    if subcommand == "snapshot" && !jobdir.trim().is_empty() {
        tool_args.push("--jobdir".to_string());
        tool_args.push(jobdir);
    }
    if subcommand == "tail" {
        tool_args.push("--stream".to_string());
        tool_args.push(stream);
    }
    run_shared_python_tool("runtime_console.py", &tool_args)
}

fn handle_audit(args: &[String]) -> i32 {
    let Some(subcommand) = args.first().map(|value| value.as_str()) else {
        eprintln!("usage: rustspider audit <snapshot|tail> --control-plane <dir>");
        return 2;
    };
    if subcommand != "snapshot" && subcommand != "tail" {
        eprintln!("usage: rustspider audit <snapshot|tail> --control-plane <dir>");
        return 2;
    }

    let mut control_plane = String::from("artifacts/control-plane");
    let mut job_name = String::new();
    let mut stream = String::from("all");
    let mut lines = String::from("20");
    let mut i = 1usize;
    while i < args.len() {
        match args[i].as_str() {
            "--control-plane" if i + 1 < args.len() => {
                control_plane = args[i + 1].clone();
                i += 2;
            }
            "--job-name" if i + 1 < args.len() => {
                job_name = args[i + 1].clone();
                i += 2;
            }
            "--stream" if i + 1 < args.len() => {
                stream = args[i + 1].clone();
                i += 2;
            }
            "--lines" if i + 1 < args.len() => {
                lines = args[i + 1].clone();
                i += 2;
            }
            other => {
                eprintln!("unknown audit argument: {other}");
                return 2;
            }
        }
    }

    let mut tool_args = vec![
        subcommand.to_string(),
        "--control-plane".to_string(),
        control_plane,
        "--job-name".to_string(),
        job_name,
        "--lines".to_string(),
        lines,
    ];
    if subcommand == "tail" {
        tool_args.push("--stream".to_string());
        tool_args.push(stream);
    }
    run_shared_python_tool("audit_console.py", &tool_args)
}

fn handle_web(args: &[String]) -> i32 {
    let mut host = String::from("0.0.0.0");
    let mut port: u16 = 9090;
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--host" if i + 1 < args.len() => {
                host = args[i + 1].clone();
                i += 2;
            }
            "--port" if i + 1 < args.len() => {
                match args[i + 1].parse::<u16>() {
                    Ok(value) => port = value,
                    Err(err) => {
                        eprintln!("invalid port: {err}");
                        return 2;
                    }
                }
                i += 2;
            }
            "--mode" if i + 1 < args.len() => {
                i += 2;
            }
            other => {
                eprintln!("unknown web argument: {other}");
                return 2;
            }
        }
    }

    #[cfg(feature = "web")]
    {
        match tokio::runtime::Runtime::new() {
            Ok(runtime) => match runtime.block_on(rustspider::web::run_server(&host, port)) {
                Ok(()) => 0,
                Err(err) => {
                    eprintln!("web server failed: {err}");
                    1
                }
            },
            Err(err) => {
                eprintln!("failed to initialize async runtime: {err}");
                1
            }
        }
    }

    #[cfg(not(feature = "web"))]
    {
        let _ = (host, port);
        eprintln!("rustspider web server requires the `web` feature");
        1
    }
}

fn handle_research(args: &[String]) -> i32 {
    let Some(subcommand) = args.first().map(|value| value.as_str()) else {
        eprintln!("usage: rustspider research <run|async|soak> ...");
        return 2;
    };
    match subcommand {
        "run" => {
            let mut url = String::new();
            let mut content = String::new();
            let mut schema_json = String::from("{}");
            let mut output = String::new();
            let mut i = 1usize;
            while i < args.len() {
                match args[i].as_str() {
                    "--url" if i + 1 < args.len() => {
                        url = args[i + 1].clone();
                        i += 2;
                    }
                    "--content" if i + 1 < args.len() => {
                        content = args[i + 1].clone();
                        i += 2;
                    }
                    "--schema-json" if i + 1 < args.len() => {
                        schema_json = args[i + 1].clone();
                        i += 2;
                    }
                    "--output" if i + 1 < args.len() => {
                        output = args[i + 1].clone();
                        i += 2;
                    }
                    other if !other.starts_with("--") && url.is_empty() => {
                        url = other.to_string();
                        i += 1;
                    }
                    other => {
                        eprintln!("unknown research run argument: {other}");
                        return 2;
                    }
                }
            }
            if url.trim().is_empty() {
                eprintln!("research run requires --url");
                return 2;
            }
            let job = match build_research_job(
                vec![url],
                &schema_json,
                if output.is_empty() {
                    None
                } else {
                    Some(output)
                },
            ) {
                Ok(job) => job,
                Err(err) => {
                    eprintln!("invalid research schema: {err}");
                    return 2;
                }
            };
            match rustspider::research::ResearchRuntime::new().run(&job, Some(&content)) {
                Ok(payload) => print_json_payload(&payload),
                Err(err) => {
                    eprintln!("research run failed: {err}");
                    1
                }
            }
        }
        "async" | "soak" => {
            let mut urls = Vec::new();
            let mut content = String::new();
            let mut schema_json = String::from("{}");
            let mut rounds: usize = 1;
            let mut concurrency: usize = 5;
            let mut i = 1usize;
            while i < args.len() {
                match args[i].as_str() {
                    "--url" if i + 1 < args.len() => {
                        urls.push(args[i + 1].clone());
                        i += 2;
                    }
                    "--content" if i + 1 < args.len() => {
                        content = args[i + 1].clone();
                        i += 2;
                    }
                    "--schema-json" if i + 1 < args.len() => {
                        schema_json = args[i + 1].clone();
                        i += 2;
                    }
                    "--rounds" if i + 1 < args.len() => {
                        rounds = args[i + 1].parse::<usize>().unwrap_or(1);
                        i += 2;
                    }
                    "--concurrency" if i + 1 < args.len() => {
                        concurrency = args[i + 1].parse::<usize>().unwrap_or(5);
                        i += 2;
                    }
                    other => {
                        eprintln!("unknown research {} argument: {other}", subcommand);
                        return 2;
                    }
                }
            }
            if urls.is_empty() {
                eprintln!("research async/soak requires at least one --url");
                return 2;
            }
            let mut jobs = Vec::new();
            let mut contents = Vec::new();
            for (index, url) in urls.iter().enumerate() {
                match build_research_job(vec![url.clone()], &schema_json, None) {
                    Ok(job) => jobs.push(job),
                    Err(err) => {
                        eprintln!("invalid research schema: {err}");
                        return 2;
                    }
                }
                if content.trim().is_empty() {
                    contents.push(format!("<title>Research {}</title>", index + 1));
                } else {
                    contents.push(content.clone());
                }
            }
            let runtime = rustspider::async_research::AsyncResearchRuntime::new(Some(
                rustspider::async_research::AsyncResearchConfig {
                    max_concurrent: concurrency.max(1),
                    timeout_seconds: 30.0,
                    enable_streaming: false,
                },
            ));
            match tokio::runtime::Runtime::new() {
                Ok(rt) => {
                    if subcommand == "soak" {
                        let payload = rt.block_on(runtime.run_soak(jobs, Some(contents), rounds));
                        print_json_payload(&payload)
                    } else {
                        let results = rt.block_on(runtime.run_multiple(jobs, Some(contents)));
                        let payload = serde_json::json!({
                            "command": "research async",
                            "runtime": "rust",
                            "results": results,
                            "metrics": runtime.snapshot_metrics(),
                        });
                        print_json_payload(&payload)
                    }
                }
                Err(err) => {
                    eprintln!("failed to initialize async runtime: {err}");
                    1
                }
            }
        }
        _ => {
            eprintln!("usage: rustspider research <run|async|soak> ...");
            2
        }
    }
}

fn build_research_job(
    seed_urls: Vec<String>,
    schema_json: &str,
    output: Option<String>,
) -> Result<rustspider::research::ResearchJob, String> {
    let schema_value: serde_json::Value = serde_json::from_str(if schema_json.trim().is_empty() {
        "{}"
    } else {
        schema_json
    })
    .map_err(|err| format!("invalid schema json: {err}"))?;
    let extract_schema = schema_value
        .as_object()
        .cloned()
        .unwrap_or_else(serde_json::Map::new);
    let mut output_map = serde_json::Map::new();
    if let Some(path) = output.filter(|value| !value.trim().is_empty()) {
        output_map.insert("path".to_string(), serde_json::Value::String(path));
    }
    Ok(rustspider::research::ResearchJob {
        seed_urls,
        extract_schema,
        output: output_map,
        ..rustspider::research::ResearchJob::default()
    })
}

fn print_json_payload(payload: &serde_json::Value) -> i32 {
    match serde_json::to_string_pretty(payload) {
        Ok(text) => {
            println!("{text}");
            0
        }
        Err(err) => {
            eprintln!("failed to render json: {err}");
            1
        }
    }
}

fn handle_run(args: &[String]) -> i32 {
    let mut url = String::new();
    let mut runtime_name = String::from("http");
    let mut name = String::new();
    let mut output_path = String::new();
    let mut content = String::new();
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--url" if i + 1 < args.len() => {
                url = args[i + 1].clone();
                i += 2;
            }
            "--runtime" if i + 1 < args.len() => {
                runtime_name = args[i + 1].clone();
                i += 2;
            }
            "--name" if i + 1 < args.len() => {
                name = args[i + 1].clone();
                i += 2;
            }
            "--output" if i + 1 < args.len() => {
                output_path = args[i + 1].clone();
                i += 2;
            }
            "--content" if i + 1 < args.len() => {
                content = args[i + 1].clone();
                i += 2;
            }
            other if !other.starts_with("--") && url.is_empty() => {
                url = other.to_string();
                i += 1;
            }
            other => {
                eprintln!("unknown run argument: {other}");
                return 2;
            }
        }
    }

    if url.trim().is_empty() {
        eprintln!(
            "usage: rustspider run <url> [--runtime <http|browser|media|ai>] [--output <path>]"
        );
        return 2;
    }

    let job_name = if name.trim().is_empty() {
        format!(
            "rust-inline-{}",
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|value| value.as_millis())
                .unwrap_or_default()
        )
    } else {
        name
    };
    let output_path = if output_path.trim().is_empty() {
        format!("artifacts/exports/{job_name}.json")
    } else {
        output_path
    };
    let metadata = if content.trim().is_empty() {
        None
    } else {
        Some(serde_json::json!({ "content": content }))
    };
    let job = RuntimeJobSpec {
        name: job_name,
        runtime: runtime_name,
        priority: None,
        target: RuntimeTargetSection {
            url,
            method: default_method(),
            headers: HashMap::new(),
            cookies: HashMap::new(),
            body: None,
            proxy: None,
            timeout_ms: None,
            allowed_domains: Vec::new(),
        },
        extract: Vec::new(),
        output: RuntimeOutputSection {
            format: "json".to_string(),
            path: Some(output_path),
            directory: None,
            artifact_prefix: None,
        },
        resources: None,
        browser: None,
        anti_bot: None,
        policy: None,
        schedule: None,
        metadata,
    };
    run_inline_job(job)
}

fn handle_async_job(args: &[String]) -> i32 {
    handle_job(args)
}

fn handle_workflow(args: &[String]) -> i32 {
    let Some(subcommand) = args.first().map(|value| value.as_str()) else {
        eprintln!("usage: rustspider workflow run --file <workflow.json>");
        return 2;
    };
    if subcommand != "run" {
        eprintln!("usage: rustspider workflow run --file <workflow.json>");
        return 2;
    }

    let mut file_path = String::new();
    let mut index = 1usize;
    while index < args.len() {
        match args[index].as_str() {
            "--file" if index + 1 < args.len() => {
                file_path = args[index + 1].clone();
                index += 2;
            }
            other => {
                eprintln!("unknown workflow argument: {other}");
                return 2;
            }
        }
    }

    if file_path.trim().is_empty() {
        eprintln!("rustspider workflow run requires --file");
        return 2;
    }

    let raw = match fs::read_to_string(&file_path) {
        Ok(value) => value,
        Err(err) => {
            eprintln!("failed to read workflow spec: {err}");
            return 1;
        }
    };
    let job: rustspider::workflow::FlowJob = match serde_json::from_str(&raw) {
        Ok(value) => value,
        Err(err) => {
            eprintln!("failed to parse workflow spec: {err}");
            return 1;
        }
    };

    let spec_path = PathBuf::from(&file_path);
    let control_plane = spec_path
        .parent()
        .unwrap_or_else(|| std::path::Path::new("."))
        .join("artifacts")
        .join("control-plane");
    let event_path = control_plane.join(format!("{}-workflow-events.jsonl", job.name));
    let connector_path = control_plane.join(format!("{}-workflow-connector.jsonl", job.name));
    let runner = rustspider::workflow::WorkflowRunner::new()
        .with_event_bus(rustspider::event_bus::FileEventBus::new(event_path.clone()))
        .add_connector(rustspider::connector::FileConnector::new(
            connector_path.clone(),
        ));

    match runner.execute(&job) {
        Ok(result) => {
            println!(
                "{}",
                serde_json::to_string_pretty(&serde_json::json!({
                    "command": "workflow run",
                    "runtime": "rust",
                    "job_id": result.job_id,
                    "run_id": result.run_id,
                    "extract": result.extracted,
                    "artifacts": result.artifacts,
                    "events_path": event_path,
                    "connector_path": connector_path,
                }))
                .unwrap_or_default()
            );
            0
        }
        Err(err) => {
            eprintln!("workflow execution failed: {err}");
            1
        }
    }
}

fn run_inline_job(job: RuntimeJobSpec) -> i32 {
    let temp_path = env::temp_dir().join(format!(
        "rustspider-run-{}-{}.json",
        std::process::id(),
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|value| value.as_millis())
            .unwrap_or_default()
    ));
    let encoded = match serde_json::to_vec_pretty(&job) {
        Ok(value) => value,
        Err(err) => {
            eprintln!("failed to encode inline job: {err}");
            return 1;
        }
    };
    if let Err(err) = fs::write(&temp_path, encoded) {
        eprintln!("failed to write inline job spec: {err}");
        return 1;
    }
    let result = handle_job(&[
        "--file".to_string(),
        temp_path.to_string_lossy().to_string(),
    ]);
    let _ = fs::remove_file(temp_path);
    result
}

fn handle_curl(args: &[String]) -> i32 {
    let Some(subcommand) = args.first().map(|value| value.as_str()) else {
        eprintln!("usage: rustspider curl convert --command <curl> [--target <rust|reqwest|ureq>]");
        return 2;
    };
    if subcommand != "convert" {
        eprintln!("usage: rustspider curl convert --command <curl> [--target <rust|reqwest|ureq>]");
        return 2;
    }

    let mut curl_command = String::new();
    let mut target = String::from("ureq");
    let mut i = 1usize;
    while i < args.len() {
        match args[i].as_str() {
            "--command" | "-c" if i + 1 < args.len() => {
                curl_command = args[i + 1].clone();
                i += 2;
            }
            "--target" if i + 1 < args.len() => {
                target = args[i + 1].to_ascii_lowercase();
                i += 2;
            }
            other => {
                if curl_command.trim().is_empty() {
                    curl_command = other.to_string();
                    i += 1;
                } else {
                    eprintln!("unknown curl argument: {other}");
                    return 2;
                }
            }
        }
    }

    if curl_command.trim().is_empty() {
        eprintln!("rustspider curl convert requires --command");
        return 2;
    }

    let converter = rustspider::CurlToRustConverter::new();
    let mut resolved_target = target.clone();
    let code = match target.as_str() {
        "rust" => match rustspider::curl_to_rust(&curl_command) {
            Ok(code) => code,
            Err(_) => {
                resolved_target = "ureq".to_string();
                converter.convert_to_ureq(&curl_command)
            }
        },
        "reqwest" => match converter.convert_to_reqwest(&curl_command) {
            Ok(code) => code,
            Err(_) => {
                resolved_target = "ureq".to_string();
                converter.convert_to_ureq(&curl_command)
            }
        },
        "ureq" => converter.convert_to_ureq(&curl_command),
        other => {
            eprintln!("unsupported curl target: {other}");
            return 2;
        }
    };

    let payload = serde_json::json!({
        "command": "curl convert",
        "runtime": "rust",
        "target": resolved_target,
        "curl": curl_command,
        "code": code,
    });
    println!(
        "{}",
        serde_json::to_string_pretty(&payload).unwrap_or_default()
    );
    0
}

fn handle_media(args: &[String]) -> i32 {
    let mut url: Option<String> = None;
    let mut output_dir = "downloads".to_string();
    let mut download = false;
    let mut mode = "info".to_string();
    let mut artifact_dir = String::new();
    let mut html_file = String::new();
    let mut network_file = String::new();
    let mut har_file = String::new();
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "download" | "info" | "artifact" => {
                mode = args[i].clone();
                i += 1;
            }
            "--url" | "-u" => {
                if let Some(value) = args.get(i + 1) {
                    url = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --url");
                    return 2;
                }
            }
            "--output" | "-o" => {
                if let Some(value) = args.get(i + 1) {
                    output_dir = value.clone();
                    i += 2;
                } else {
                    eprintln!("missing value for --output");
                    return 2;
                }
            }
            "--artifact-dir" if i + 1 < args.len() => {
                artifact_dir = args[i + 1].clone();
                i += 2;
            }
            "--html-file" if i + 1 < args.len() => {
                html_file = args[i + 1].clone();
                i += 2;
            }
            "--network-file" if i + 1 < args.len() => {
                network_file = args[i + 1].clone();
                i += 2;
            }
            "--har-file" if i + 1 < args.len() => {
                har_file = args[i + 1].clone();
                i += 2;
            }
            "--download" => {
                download = true;
                i += 1;
            }
            other => {
                if url.is_none() {
                    url = Some(other.to_string());
                    i += 1;
                } else {
                    eprintln!("unknown media argument: {other}");
                    return 2;
                }
            }
        }
    }

    let Some(url) = url else {
        eprintln!("media requires --url");
        return 2;
    };

    let (html_file, network_file, har_file) =
        resolve_media_artifact_bundle(&artifact_dir, &html_file, &network_file, &har_file);
    let artifact_parsed = if !html_file.trim().is_empty()
        || !network_file.trim().is_empty()
        || !har_file.trim().is_empty()
        || mode == "artifact"
    {
        match parse_media_artifacts(&url, &html_file, &network_file, &har_file) {
            Ok(parsed) => parsed,
            Err(err) => {
                eprintln!("failed to parse media artifacts: {err}");
                return 1;
            }
        }
    } else {
        None
    };

    let platform = detect_media_platform(&url);
    if mode == "info" && !download {
        let parsed = artifact_parsed.or_else(|| {
            rustspider::media::UniversalParser::new()
                .ok()
                .and_then(|parser| parser.parse(&url))
        });
        let payload = serde_json::json!({
            "command": "media",
            "runtime": "rust",
            "mode": "info",
            "url": url,
            "platform": platform,
            "artifact_dir": artifact_dir,
            "html_file": html_file,
            "network_file": network_file,
            "har_file": har_file,
            "parsed": parsed,
            "download_supported": true,
        });
        println!(
            "{}",
            serde_json::to_string_pretty(&payload).unwrap_or_default()
        );
        return 0;
    }

    if mode == "artifact" {
        let Some(parsed) = artifact_parsed.or_else(|| {
            rustspider::media::UniversalParser::new()
                .ok()
                .and_then(|parser| parser.parse(&url))
        }) else {
            eprintln!("no media discovered from artifact inputs");
            return 1;
        };

        let mut download_output = String::new();
        let mut exit_code = 0;
        if download {
            if let Err(err) = fs::create_dir_all(&output_dir) {
                eprintln!("failed to create media output directory: {err}");
                return 1;
            }
            let media_url = first_media_download_url(&parsed).unwrap_or_else(|| url.clone());
            let runtime = match tokio::runtime::Runtime::new() {
                Ok(runtime) => runtime,
                Err(err) => {
                    eprintln!("failed to initialize async runtime: {err}");
                    return 1;
                }
            };
            let downloader = rustspider::media::MediaDownloader::new();
            let filename = media_filename_from_url(&media_url);
            let output_path = PathBuf::from(&output_dir).join(filename);
            match runtime.block_on(
                downloader.download_file(&media_url, output_path.to_string_lossy().as_ref()),
            ) {
                Ok(_) => download_output = output_path.to_string_lossy().to_string(),
                Err(err) => {
                    eprintln!("media artifact download failed: {err}");
                    exit_code = 1;
                }
            }
        }

        let payload = serde_json::json!({
            "command": "media artifact",
            "runtime": "rust",
            "url": url,
            "platform": detect_media_platform(&url),
            "artifact_dir": artifact_dir,
            "html_file": html_file,
            "network_file": network_file,
            "har_file": har_file,
            "video": parsed,
            "download": {
                "requested": download,
                "output": download_output,
            },
        });
        println!(
            "{}",
            serde_json::to_string_pretty(&payload).unwrap_or_default()
        );
        return exit_code;
    }

    if let Err(err) = fs::create_dir_all(&output_dir) {
        eprintln!("failed to create media output directory: {err}");
        return 1;
    }

    let download_url = artifact_parsed
        .as_ref()
        .and_then(first_media_download_url)
        .unwrap_or_else(|| url.clone());
    let filename = media_filename_from_url(&download_url);
    let output_path = PathBuf::from(&output_dir).join(filename);
    let runtime = match tokio::runtime::Runtime::new() {
        Ok(runtime) => runtime,
        Err(err) => {
            eprintln!("failed to initialize async runtime: {err}");
            return 1;
        }
    };
    let downloader = rustspider::media::MediaDownloader::new();
    match runtime
        .block_on(downloader.download_file(&download_url, output_path.to_string_lossy().as_ref()))
    {
        Ok(_) => {
            let payload = serde_json::json!({
                "command": "media",
                "runtime": "rust",
                "mode": "download",
                "url": url,
                "artifact_dir": artifact_dir,
                "html_file": html_file,
                "network_file": network_file,
                "har_file": har_file,
                "platform": platform,
                "parsed": artifact_parsed,
                "download_url": download_url,
                "output": output_path.to_string_lossy(),
            });
            println!(
                "{}",
                serde_json::to_string_pretty(&payload).unwrap_or_default()
            );
            0
        }
        Err(err) => {
            eprintln!("media download failed: {err}");
            1
        }
    }
}

fn resolve_media_artifact_bundle(
    artifact_dir: &str,
    html_file: &str,
    network_file: &str,
    har_file: &str,
) -> (String, String, String) {
    fn matches_pattern(name: &str, pattern: &str) -> bool {
        let lower_name = name.to_ascii_lowercase();
        let lower_pattern = pattern.to_ascii_lowercase();
        let parts = lower_pattern
            .split('*')
            .filter(|part| !part.is_empty())
            .collect::<Vec<_>>();
        if parts.is_empty() {
            return lower_name == lower_pattern;
        }
        let mut cursor = 0usize;
        for part in parts {
            let Some(offset) = lower_name[cursor..].find(part) else {
                return false;
            };
            cursor += offset + part.len();
        }
        if !lower_pattern.starts_with('*') {
            let first = lower_pattern.split('*').next().unwrap_or_default();
            if !lower_name.starts_with(first) {
                return false;
            }
        }
        if !lower_pattern.ends_with('*') {
            let last = lower_pattern.rsplit('*').next().unwrap_or_default();
            if !lower_name.ends_with(last) {
                return false;
            }
        }
        true
    }

    fn discover(
        current: &str,
        artifact_dir: &str,
        candidates: &[&str],
        patterns: &[&str],
    ) -> String {
        if !current.trim().is_empty() {
            return current.to_string();
        }
        if artifact_dir.trim().is_empty() {
            return String::new();
        }
        let root = PathBuf::from(artifact_dir);
        if !root.is_dir() {
            return String::new();
        }
        for candidate in candidates {
            let path = root.join(candidate);
            if path.is_file() {
                return path.to_string_lossy().to_string();
            }
        }
        if let Ok(entries) = fs::read_dir(&root) {
            let mut files = entries
                .flatten()
                .map(|entry| entry.path())
                .filter(|path| path.is_file())
                .collect::<Vec<_>>();
            files.sort();
            for file in files {
                let Some(name) = file.file_name().and_then(|value| value.to_str()) else {
                    continue;
                };
                if patterns
                    .iter()
                    .any(|pattern| matches_pattern(name, pattern))
                {
                    return file.to_string_lossy().to_string();
                }
            }
        }
        String::new()
    }

    (
        discover(
            html_file,
            artifact_dir,
            &[
                "page.html",
                "content.html",
                "document.html",
                "browser.html",
                "response.html",
                "index.html",
            ],
            &["*page*.html", "*content*.html", "*.html"],
        ),
        discover(
            network_file,
            artifact_dir,
            &[
                "network.json",
                "requests.json",
                "trace.json",
                "network.log",
                "network.txt",
            ],
            &[
                "*network*.json",
                "*request*.json",
                "*trace*.json",
                "*network*.txt",
            ],
        ),
        discover(
            har_file,
            artifact_dir,
            &[
                "trace.har",
                "network.har",
                "session.har",
                "browser.har",
                "page.har",
            ],
            &["*.har"],
        ),
    )
}

fn parse_media_artifacts(
    page_url: &str,
    html_file: &str,
    network_file: &str,
    har_file: &str,
) -> Result<Option<rustspider::media::VideoData>, String> {
    let read_artifact = |path: &str| -> Result<Option<String>, String> {
        if path.trim().is_empty() {
            return Ok(None);
        }
        fs::read_to_string(path)
            .map(Some)
            .map_err(|err| format!("failed to read artifact {path}: {err}"))
    };

    let html = read_artifact(html_file)?;
    let network = read_artifact(network_file)?;
    let har = read_artifact(har_file)?;
    let artifact_texts = [network, har].into_iter().flatten().collect::<Vec<_>>();

    if html.is_none() && artifact_texts.is_empty() {
        return Ok(None);
    }
    let parser = rustspider::media::UniversalParser::new()
        .map_err(|err| format!("failed to initialize media parser: {err}"))?;
    Ok(parser.parse_artifacts(page_url, html.as_deref(), &artifact_texts))
}

fn first_media_download_url(video: &rustspider::media::VideoData) -> Option<String> {
    video
        .m3u8_url
        .clone()
        .or(video.mp4_url.clone())
        .or(video.dash_url.clone())
        .or(video.download_url.clone())
}

fn media_filename_from_url(url: &str) -> String {
    url.split('/')
        .next_back()
        .filter(|value| !value.trim().is_empty())
        .unwrap_or("download.bin")
        .to_string()
}

fn detect_media_platform(url: &str) -> &'static str {
    let lower = url.to_ascii_lowercase();
    if lower.contains("youtube.com") || lower.contains("youtu.be") {
        "youtube"
    } else if lower.contains("youku.com") {
        "youku"
    } else if lower.contains("iqiyi.com") {
        "iqiyi"
    } else if lower.contains("qq.com") || lower.contains("v.qq.com") {
        "tencent"
    } else if lower.contains("bilibili.com") {
        "bilibili"
    } else if lower.contains("douyin.com") {
        "douyin"
    } else if url
        .split("/video/")
        .nth(1)
        .map(|tail| {
            tail.chars()
                .take_while(|ch| ch.is_ascii_alphanumeric())
                .collect::<String>()
        })
        .map(|token| token.starts_with("BV") || token.starts_with("av"))
        .unwrap_or(false)
    {
        "bilibili"
    } else if url
        .split("/video/")
        .nth(1)
        .map(|tail| {
            let token = tail
                .chars()
                .take_while(|ch| ch.is_ascii_digit())
                .collect::<String>();
            !token.is_empty()
        })
        .unwrap_or(false)
    {
        "douyin"
    } else if lower.contains("tiktok.com") {
        "tiktok"
    } else if lower.contains(".m3u8") {
        "hls"
    } else if lower.contains(".mpd") {
        "dash"
    } else {
        "generic"
    }
}

fn prepare_browser_artifact_paths(screenshot_path: &str, html_path: &str) -> Result<(), String> {
    if let Some(parent) = PathBuf::from(&screenshot_path).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    if let Some(parent) = PathBuf::from(&html_path).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn playwright_helper_script() -> PathBuf {
    if let Ok(path) = env::var("RUSTSPIDER_PLAYWRIGHT_HELPER") {
        if !path.trim().is_empty() {
            return PathBuf::from(path);
        }
    }
    if let Ok(path) = env::var("SPIDER_PLAYWRIGHT_HELPER") {
        if !path.trim().is_empty() {
            return PathBuf::from(path);
        }
    }
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("workspace root should exist")
        .join("tools")
        .join("playwright_fetch.py")
}

fn native_playwright_helper_script() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("workspace root should exist")
        .join("tools")
        .join("playwright_fetch.mjs")
}

fn run_native_playwright_fetch(
    url: &str,
    screenshot_path: &str,
    html_path: &str,
    cfg: &ContractConfig,
) -> Result<(String, String), String> {
    prepare_browser_artifact_paths(screenshot_path, html_path)?;
    let script = native_playwright_helper_script();
    if !script.exists() {
        return Err(format!(
            "missing native helper script: {}",
            script.display()
        ));
    }

    let mut command = Command::new("node");
    command
        .arg(script)
        .arg("--url")
        .arg(url)
        .arg("--screenshot")
        .arg(screenshot_path)
        .arg("--html")
        .arg(html_path)
        .arg("--timeout-seconds")
        .arg(cfg.browser.timeout_seconds.to_string());
    if !cfg.browser.user_agent.is_empty() {
        command.arg("--user-agent").arg(&cfg.browser.user_agent);
    }
    if !cfg.browser.storage_state_file.is_empty() {
        command
            .arg("--save-storage-state")
            .arg(&cfg.browser.storage_state_file);
    }
    if !cfg.browser.cookies_file.is_empty() {
        command
            .arg("--save-cookies-file")
            .arg(&cfg.browser.cookies_file);
    }
    if cfg.browser.headless {
        command.arg("--headless");
    }

    let output = command
        .output()
        .map_err(|e| format!("failed to launch native playwright helper: {e}"))?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!(
            "native playwright helper failed: {}",
            stderr.trim()
        ));
    }
    let payload: serde_json::Value = serde_json::from_slice(&output.stdout)
        .map_err(|e| format!("invalid native helper json: {e}"))?;
    let title = payload
        .get("title")
        .and_then(|value| value.as_str())
        .unwrap_or_default()
        .to_string();
    let resolved_url = payload
        .get("url")
        .and_then(|value| value.as_str())
        .unwrap_or(url)
        .to_string();
    Ok((title, resolved_url))
}

fn run_native_playwright_job_helper(job_path: &str) -> Result<serde_json::Value, String> {
    let script = native_playwright_helper_script();
    if !script.exists() {
        return Err(format!(
            "missing native helper script: {}",
            script.display()
        ));
    }
    let output = Command::new("node")
        .arg(script)
        .arg("--job-file")
        .arg(job_path)
        .output()
        .map_err(|e| format!("failed to launch native playwright helper: {e}"))?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!(
            "native playwright helper failed: {}",
            stderr.trim()
        ));
    }
    serde_json::from_slice(&output.stdout).map_err(|e| format!("invalid native helper json: {e}"))
}

fn shared_tool_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("workspace root should exist")
        .join("tools")
        .join(name)
}

fn default_auth_action_examples() -> serde_json::Value {
    serde_json::json!([
        {"type":"goto","url":"https://example.com/login"},
        {"type":"type","selector":"#username","value":"demo"},
        {"type":"type","selector":"#password","value":"secret"},
        {"type":"if","when":{"selector_exists":"#otp"},"then":[{"type":"mfa_totp","selector":"#otp","totp_env":"SPIDER_AUTH_TOTP_SECRET"}]},
        {"type":"if","when":{"selector_exists":".cf-turnstile,[data-sitekey]"},"then":[{"type":"captcha_solve","challenge":"turnstile","selector":".cf-turnstile,[data-sitekey]","provider":"anticaptcha","save_as":"captcha_token"}]},
        {"type":"submit","selector":"#password"},
        {"type":"wait_network_idle"},
        {"type":"reverse_profile","save_as":"reverse_runtime"},
        {"type":"assert","url_contains":"/dashboard"},
        {"type":"save_as","value":"url","save_as":"final_url"}
    ])
}

fn python_command() -> String {
    if let Ok(value) = env::var("SPIDER_PYTHON") {
        return value;
    }

    let repo_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("workspace root should exist")
        .to_path_buf();

    let candidates = [
        repo_root.join(".venv").join("Scripts").join("python.exe"),
        repo_root.join(".venv").join("bin").join("python"),
        repo_root
            .parent()
            .map(|p| p.join(".venv").join("Scripts").join("python.exe"))
            .unwrap_or_else(|| PathBuf::from(".venv/Scripts/python.exe")),
        repo_root
            .parent()
            .map(|p| p.join(".venv").join("bin").join("python"))
            .unwrap_or_else(|| PathBuf::from(".venv/bin/python")),
    ];

    for candidate in candidates {
        if candidate.exists() {
            return candidate.to_string_lossy().to_string();
        }
    }

    env::var("PYTHON").unwrap_or_else(|_| "python".to_string())
}

fn run_shared_python_tool(script_name: &str, tool_args: &[String]) -> i32 {
    let script = shared_tool_path(script_name);
    if !script.exists() {
        eprintln!("missing shared tool: {}", script.display());
        return 1;
    }

    let status = Command::new(python_command())
        .arg(script)
        .args(tool_args)
        .status();
    match status {
        Ok(status) => status.code().unwrap_or(1),
        Err(err) => {
            eprintln!("failed to launch shared tool {}: {}", script_name, err);
            1
        }
    }
}

fn run_playwright_fetch(
    url: &str,
    screenshot_path: &str,
    html_path: &str,
    cfg: &ContractConfig,
) -> Result<(String, String), String> {
    prepare_browser_artifact_paths(screenshot_path, html_path)?;

    let script = playwright_helper_script();
    if !script.exists() {
        return Err(format!("missing helper script: {}", script.display()));
    }

    let mut command = Command::new(python_command());
    command
        .arg(script)
        .arg("--url")
        .arg(url)
        .arg("--screenshot")
        .arg(screenshot_path)
        .arg("--html")
        .arg(html_path)
        .arg("--timeout-seconds")
        .arg(cfg.browser.timeout_seconds.to_string());

    if !cfg.browser.user_agent.is_empty() {
        command.arg("--user-agent").arg(&cfg.browser.user_agent);
    }
    if !cfg.browser.storage_state_file.is_empty() {
        if std::path::Path::new(&cfg.browser.storage_state_file).exists() {
            command
                .arg("--storage-state")
                .arg(&cfg.browser.storage_state_file);
        }
        command
            .arg("--save-storage-state")
            .arg(&cfg.browser.storage_state_file);
    }
    if !cfg.browser.cookies_file.is_empty() {
        if std::path::Path::new(&cfg.browser.cookies_file).exists() {
            command.arg("--cookies-file").arg(&cfg.browser.cookies_file);
        }
        command
            .arg("--save-cookies-file")
            .arg(&cfg.browser.cookies_file);
    }
    if !cfg.browser.auth_file.is_empty() {
        command.arg("--auth-file").arg(&cfg.browser.auth_file);
    }
    if cfg.browser.headless {
        command.arg("--headless");
    }

    let output = command
        .output()
        .map_err(|e| format!("failed to launch helper: {e}"))?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("playwright helper failed: {}", stderr.trim()));
    }

    let payload: serde_json::Value =
        serde_json::from_slice(&output.stdout).map_err(|e| format!("invalid helper json: {e}"))?;
    let title = payload
        .get("title")
        .and_then(|value| value.as_str())
        .unwrap_or_default()
        .to_string();
    let resolved_url = payload
        .get("url")
        .and_then(|value| value.as_str())
        .unwrap_or(url)
        .to_string();
    Ok((title, resolved_url))
}

fn run_playwright_job_helper(job_path: &str) -> Result<serde_json::Value, String> {
    let script = playwright_helper_script();
    if !script.exists() {
        return Err(format!("missing helper script: {}", script.display()));
    }

    let output = Command::new(python_command())
        .arg(script)
        .arg("--job-file")
        .arg(job_path)
        .output()
        .map_err(|e| format!("failed to launch playwright helper: {e}"))?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("playwright helper failed: {}", stderr.trim()));
    }

    serde_json::from_slice(&output.stdout).map_err(|e| format!("invalid helper json: {e}"))
}

fn handle_doctor(args: &[String], command_name: &'static str) -> i32 {
    let mut json_output = false;
    let mut options = PreflightOptions::new();
    let mut config_path: Option<String> = None;

    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--json" => {
                json_output = true;
                i += 1;
            }
            "--config" => {
                if let Some(path) = args.get(i + 1) {
                    config_path = Some(path.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --config");
                    return 2;
                }
            }
            "--writable-path" => {
                if let Some(path) = args.get(i + 1) {
                    options = options.with_writable_path(PathBuf::from(path));
                    i += 2;
                } else {
                    eprintln!("missing value for --writable-path");
                    return 2;
                }
            }
            "--network-target" => {
                if let Some(target) = args.get(i + 1) {
                    options = options.with_network_target(target.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --network-target");
                    return 2;
                }
            }
            "--redis-url" => {
                if let Some(redis_url) = args.get(i + 1) {
                    options = options.with_redis_url(redis_url.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --redis-url");
                    return 2;
                }
            }
            "--require-ffmpeg" => {
                options = options.require_ffmpeg();
                i += 1;
            }
            "--require-browser" => {
                options = options.require_browser();
                i += 1;
            }
            "--require-yt-dlp" => {
                options = options.require_yt_dlp();
                i += 1;
            }
            unknown => {
                eprintln!("unknown {command_name} argument: {unknown}");
                return 2;
            }
        }
    }

    let cfg = match load_contract_config(config_path.as_ref()) {
        Ok(cfg) => cfg,
        Err(err) => {
            eprintln!("config error: {err}");
            return 2;
        }
    };
    options = options
        .with_writable_path(PathBuf::from(cfg.storage.checkpoint_dir))
        .with_writable_path(PathBuf::from(cfg.storage.dataset_dir))
        .with_writable_path(PathBuf::from(cfg.storage.export_dir))
        .require_browser();
    for target in cfg.doctor.network_targets {
        options = options.with_network_target(target);
    }
    let redis_configured = cfg.doctor.redis_url.is_some();
    if let Some(redis_url) = cfg.doctor.redis_url.as_ref() {
        options = options.with_redis_url(redis_url);
    }

    let mut report = run_preflight(&options);
    if !redis_configured {
        report.checks.push(rustspider::preflight::PreflightCheck {
            name: "redis".to_string(),
            status: rustspider::preflight::CheckStatus::Skipped,
            details: "not configured".to_string(),
        });
    }
    if json_output {
        match report.to_json_with_command(command_name) {
            Ok(json) => println!("{json}"),
            Err(err) => {
                eprintln!("failed to render {command_name} JSON: {err}");
                return 1;
            }
        }
    } else {
        println!("rustspider {command_name}");
        println!("=================");
        for check in &report.checks {
            println!("[{:?}] {}: {}", check.status, check.name, check.details);
        }
        println!("summary: {}", report.summary());
    }

    if report.is_success() {
        0
    } else {
        1
    }
}

fn load_runtime_job(path: &str) -> Result<RuntimeJobSpec, String> {
    let content =
        fs::read_to_string(path).map_err(|err| format!("failed to read job {}: {err}", path))?;
    serde_json::from_str(&content).map_err(|err| format!("invalid job json: {err}"))
}

fn runtime_timeout_ms(job: &RuntimeJobSpec) -> u64 {
    job.target
        .timeout_ms
        .or_else(|| {
            job.resources
                .as_ref()
                .and_then(|resources| resources.timeout_ms)
        })
        .unwrap_or(30_000)
}

fn runtime_retries(job: &RuntimeJobSpec) -> u32 {
    job.resources
        .as_ref()
        .and_then(|resources| resources.retries)
        .unwrap_or(2)
        .max(1)
}

fn runtime_user_agent(job: &RuntimeJobSpec) -> String {
    job.target
        .headers
        .get("User-Agent")
        .or_else(|| job.target.headers.get("user-agent"))
        .cloned()
        .unwrap_or_else(|| "rustspider-x1".to_string())
}

fn runtime_budget(job: &RuntimeJobSpec) -> BudgetSpec {
    let max_bytes = job
        .policy
        .as_ref()
        .and_then(|policy| policy.budget.as_ref())
        .and_then(|budget| budget.bytes_in)
        .map(|value| value.min(usize::MAX as u64) as usize)
        .unwrap_or(0);
    let max_wall_time_ms = job
        .policy
        .as_ref()
        .and_then(|policy| policy.budget.as_ref())
        .and_then(|budget| budget.wall_time_ms)
        .unwrap_or(0);
    BudgetSpec {
        max_bytes,
        max_wall_time_ms,
    }
}

fn runtime_request_delay(job: &RuntimeJobSpec) -> Option<std::time::Duration> {
    let per_sec = job
        .resources
        .as_ref()
        .and_then(|resources| resources.rate_limit_per_sec)
        .filter(|value| *value > 0.0)?;
    Some(std::time::Duration::from_secs_f64(1.0 / per_sec))
}

fn runtime_respect_robots(job: &RuntimeJobSpec) -> bool {
    job.policy
        .as_ref()
        .and_then(|policy| policy.respect_robots_txt)
        .unwrap_or(false)
}

fn runtime_allowed_domains(job: &RuntimeJobSpec) -> Vec<String> {
    if !job.target.allowed_domains.is_empty() {
        return job.target.allowed_domains.clone();
    }
    if job
        .policy
        .as_ref()
        .and_then(|policy| policy.same_domain_only)
        .unwrap_or(false)
    {
        if let Ok(parsed) = url::Url::parse(&job.target.url) {
            if let Some(host) = parsed.host_str() {
                return vec![host.to_string()];
            }
        }
    }
    Vec::new()
}

fn build_runtime_plan(job: &RuntimeJobSpec) -> NativeCrawlPlan {
    let inline_body = job
        .metadata
        .as_ref()
        .and_then(|value| value.get("content"))
        .and_then(|value| value.as_str())
        .map(String::from)
        .or_else(|| job.target.body.clone());

    NativeCrawlPlan {
        target: TargetSpec {
            url: job.target.url.clone(),
            method: job.target.method.clone(),
            headers: job.target.headers.clone(),
            inline_body,
            cookies: job.target.cookies.clone(),
            proxy: job.target.proxy.clone(),
            allowed_domains: runtime_allowed_domains(job),
        },
        transport: TransportPolicy {
            timeout: std::time::Duration::from_millis(runtime_timeout_ms(job)),
            retries: runtime_retries(job),
            user_agent: runtime_user_agent(job),
            request_delay: runtime_request_delay(job),
            respect_robots_txt: runtime_respect_robots(job),
        },
        parse: ParsePlan { capture_body: true },
        media: MediaPlan {
            detect_media: job.runtime == "media",
        },
        budget: runtime_budget(job),
    }
}

fn extract_title(body: &str) -> Option<String> {
    let lower = body.to_lowercase();
    let start = lower.find("<title>")?;
    let end = lower[start + "<title>".len()..].find("</title>")?;
    let raw = &body[start + "<title>".len()..start + "<title>".len() + end];
    let title = raw.trim();
    if title.is_empty() {
        None
    } else {
        Some(title.to_string())
    }
}

fn build_extract_payload(job: &RuntimeJobSpec, body: &str, final_url: &str) -> serde_json::Value {
    if job.extract.is_empty() {
        return serde_json::json!({});
    }
    let mut payload = serde_json::Map::new();
    let html_parser = rustspider::HTMLParser::new(body);
    let json_parser = rustspider::JSONParser::new(body);
    for spec in &job.extract {
        let value = match evaluate_runtime_extract(
            spec,
            &html_parser,
            json_parser.as_ref(),
            body,
            final_url,
        ) {
            Ok(value) => value,
            Err(err) => {
                payload.insert(
                    format!("{}_error", spec.field),
                    serde_json::Value::String(err),
                );
                continue;
            }
        };
        if let Some(json_value) = value {
            if validate_extract_schema(spec, &json_value).is_ok() {
                payload.insert(spec.field.clone(), json_value);
            }
        } else if spec.required.unwrap_or(false) {
            payload.insert(
                format!("{}_error", spec.field),
                serde_json::Value::String(
                    "required extract field could not be resolved".to_string(),
                ),
            );
        }
    }
    serde_json::Value::Object(payload)
}

fn evaluate_runtime_extract(
    spec: &RuntimeExtractSpec,
    html_parser: &rustspider::HTMLParser,
    json_parser: Option<&rustspider::JSONParser>,
    body: &str,
    final_url: &str,
) -> Result<Option<serde_json::Value>, String> {
    match spec.extract_type.as_str() {
        "css" => Ok(spec.expr.as_deref().and_then(|expr| {
            if expr == "title" {
                extract_title(body).map(serde_json::Value::String)
            } else {
                html_parser.css_first(expr).map(serde_json::Value::String)
            }
        })),
        "css_attr" => match (spec.expr.as_deref(), spec.attr.as_deref()) {
            (Some(expr), Some(attr)) => Ok(html_parser
                .css_attr_first(expr, attr)
                .map(serde_json::Value::String)),
            _ => Ok(None),
        },
        "xpath" => match spec.expr.as_deref() {
            Some(expr) => html_parser
                .xpath_first_strict(expr)
                .map(|value| value.map(serde_json::Value::String)),
            None => Ok(None),
        },
        "json_path" => {
            let Some(path) = spec.path.as_deref().or(spec.expr.as_deref()) else {
                return Ok(None);
            };
            Ok(json_parser
                .and_then(|parser| parser.get(path))
                .map(|value| {
                    if value.is_string() {
                        serde_json::Value::String(value.as_str().unwrap_or_default().to_string())
                    } else {
                        value.clone()
                    }
                }))
        }
        "regex" => Ok(spec.expr.as_deref().and_then(|expr| {
            regex::Regex::new(expr).ok().and_then(|compiled| {
                compiled
                    .captures(body)
                    .and_then(|captures| captures.get(1).or_else(|| captures.get(0)))
                    .map(|capture| serde_json::Value::String(capture.as_str().to_string()))
            })
        })),
        "ai" => Ok(ai_extract_value(spec, html_parser, body, final_url)),
        _ if spec.field == "url" => Ok(Some(serde_json::Value::String(final_url.to_string()))),
        _ if spec.field == "html" || spec.field == "dom" => {
            Ok(Some(serde_json::Value::String(body.to_string())))
        }
        _ => Ok(None),
    }
}

fn ai_extract_value(
    spec: &RuntimeExtractSpec,
    html_parser: &rustspider::HTMLParser,
    body: &str,
    final_url: &str,
) -> Option<serde_json::Value> {
    let field = spec.field.to_lowercase();
    let schema_type = spec
        .schema
        .as_ref()
        .and_then(|schema| schema.get("type"))
        .and_then(|value| value.as_str())
        .unwrap_or("");

    let description = html_parser
        .css_attr_first("meta[name=description]", "content")
        .or_else(|| html_parser.css_attr_first("meta[property='og:description']", "content"));
    let images = html_parser
        .images()
        .into_iter()
        .map(|value| absolutize_media_url(final_url, &value))
        .collect::<Vec<_>>();
    let links = html_parser
        .links()
        .into_iter()
        .map(|value| absolutize_media_url(final_url, &value))
        .collect::<Vec<_>>();
    let title = extract_title(body).or_else(|| html_parser.css_first("h1"));

    let inferred = if field.contains("title") || field.contains("headline") {
        title.map(serde_json::Value::String)
    } else if field.contains("description") || field.contains("summary") || field.contains("desc") {
        description
            .or_else(|| html_parser.css_first("p"))
            .map(serde_json::Value::String)
    } else if field == "url" || field.contains("link") {
        Some(values_to_json(schema_type, links))
    } else if field.contains("image") || field.contains("cover") || field.contains("thumbnail") {
        Some(values_to_json(schema_type, images))
    } else if field.contains("content") || field.contains("body") || field == "text" {
        Some(serde_json::Value::String(html_parser.text()))
    } else if field == "html" || field == "dom" {
        Some(serde_json::Value::String(body.to_string()))
    } else if field.contains("author") {
        html_parser
            .css_attr_first("meta[name=author]", "content")
            .or_else(|| html_parser.css_attr_first("meta[property='article:author']", "content"))
            .or_else(|| html_parser.css_first("[rel='author']"))
            .map(serde_json::Value::String)
    } else if field.contains("date") || field.contains("published") || field.contains("time") {
        html_parser
            .css_attr_first("meta[property='article:published_time']", "content")
            .or_else(|| html_parser.css_attr_first("time", "datetime"))
            .map(serde_json::Value::String)
    } else if field.contains("price") {
        regex::Regex::new(r"[$¥€£]\s?\d+(?:[.,]\d+)?")
            .ok()
            .and_then(|compiled| compiled.find(body))
            .map(|capture| serde_json::Value::String(capture.as_str().to_string()))
    } else {
        title.map(serde_json::Value::String)
    };

    inferred.map(|value| coerce_ai_value(schema_type, value))
}

fn absolutize_media_url(page_url: &str, candidate: &str) -> String {
    url::Url::parse(candidate)
        .map(|parsed| parsed.to_string())
        .or_else(|_| {
            url::Url::parse(page_url)
                .and_then(|base| base.join(candidate))
                .map(|joined| joined.to_string())
        })
        .unwrap_or_else(|_| candidate.to_string())
}

fn values_to_json(expected_type: &str, values: Vec<String>) -> serde_json::Value {
    if expected_type == "string" {
        return values
            .into_iter()
            .next()
            .map(serde_json::Value::String)
            .unwrap_or(serde_json::Value::Null);
    }
    serde_json::Value::Array(
        values
            .into_iter()
            .map(serde_json::Value::String)
            .collect::<Vec<_>>(),
    )
}

fn coerce_ai_value(expected_type: &str, value: serde_json::Value) -> serde_json::Value {
    match (expected_type, value) {
        ("array", serde_json::Value::String(text)) => {
            serde_json::Value::Array(vec![serde_json::Value::String(text)])
        }
        ("string", serde_json::Value::Array(values)) => values
            .into_iter()
            .next()
            .unwrap_or(serde_json::Value::String(String::new())),
        (_, value) => value,
    }
}

fn validate_extract_schema(
    spec: &RuntimeExtractSpec,
    value: &serde_json::Value,
) -> Result<(), String> {
    let expected_type = spec
        .schema
        .as_ref()
        .and_then(|schema| schema.get("type"))
        .and_then(|value| value.as_str())
        .unwrap_or("");
    if expected_type.is_empty() {
        return Ok(());
    }
    let valid = match expected_type {
        "string" => value.is_string(),
        "number" => value.is_number(),
        "integer" => value.as_i64().is_some() || value.as_u64().is_some(),
        "boolean" => value.is_boolean(),
        "object" => value.is_object(),
        "array" => value.is_array(),
        _ => true,
    };
    if valid {
        Ok(())
    } else {
        Err(format!(
            "extract field {} violates schema.type={}",
            spec.field, expected_type
        ))
    }
}

fn json_or_null<T: Serialize>(value: &Option<T>) -> serde_json::Value {
    value
        .as_ref()
        .and_then(|inner| serde_json::to_value(inner).ok())
        .unwrap_or(serde_json::Value::Null)
}

fn merge_anti_bot(job: &RuntimeJobSpec) -> serde_json::Value {
    let explicit = json_or_null(&job.anti_bot);
    let mocked = job
        .metadata
        .as_ref()
        .and_then(|value| value.get("mock_antibot"))
        .cloned()
        .unwrap_or(serde_json::Value::Null);
    match (explicit, mocked) {
        (serde_json::Value::Object(mut left), serde_json::Value::Object(right)) => {
            for (key, value) in right {
                left.insert(key, value);
            }
            serde_json::Value::Object(left)
        }
        (serde_json::Value::Null, right) => right,
        (left, serde_json::Value::Null) => left,
        (_, right) => right,
    }
}

fn combined_warnings(job: &RuntimeJobSpec, browser_runtime_active: bool) -> serde_json::Value {
    let mut warnings = Vec::<String>::new();
    if let Some(browser) = &job.browser {
        if !browser.actions.is_empty() && !browser_runtime_active {
            warnings.push(
                "browser.actions are parsed but not executed by rust native reactor".to_string(),
            );
        }
        let unsupported_capture = browser
            .capture
            .iter()
            .filter(|item| {
                if browser_runtime_active {
                    !matches!(
                        item.as_str(),
                        "html" | "dom" | "screenshot" | "realtime" | "websocket" | "sse"
                    )
                } else {
                    !matches!(item.as_str(), "html" | "dom")
                }
            })
            .cloned()
            .collect::<Vec<_>>();
        if !unsupported_capture.is_empty() {
            warnings.push(format!(
                "browser.capture values are noted but not produced by current rust runtime: {}",
                unsupported_capture.join(", ")
            ));
        }
    }
    if let Some(mocked) = job
        .metadata
        .as_ref()
        .and_then(|value| value.get("mock_warnings"))
        .and_then(|value| value.as_array())
    {
        warnings.extend(
            mocked
                .iter()
                .filter_map(|value| value.as_str().map(ToString::to_string)),
        );
    }
    serde_json::Value::Array(
        warnings
            .into_iter()
            .map(serde_json::Value::String)
            .collect::<Vec<_>>(),
    )
}

fn output_json_path(job: &RuntimeJobSpec) -> Option<&str> {
    job.output.path.as_deref()
}

fn persist_job_payload(job: &RuntimeJobSpec, payload: &serde_json::Value) {
    if let Some(path) = output_json_path(job) {
        let output_path = PathBuf::from(path);
        if let Some(parent) = output_path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        let _ = fs::write(
            &output_path,
            serde_json::to_string_pretty(payload).unwrap_or_default(),
        );
    }
    if let Some(store) = configured_driver_result_store() {
        let id = job.name.trim().to_string();
        let _ = store.put_json(&id, payload);
    } else if let Some(store) = configured_process_result_store() {
        let id = job.name.trim().to_string();
        let _ = store.put_json(&id, payload);
    }
}

fn configured_process_result_store() -> Option<rustspider::ProcessResultStore> {
    let backend = env::var("RUSTSPIDER_STORAGE_BACKEND")
        .ok()?
        .trim()
        .to_lowercase();
    let endpoint = env::var("RUSTSPIDER_STORAGE_ENDPOINT")
        .ok()?
        .trim()
        .to_string();
    if endpoint.is_empty() {
        return None;
    }
    let kind = match backend.as_str() {
        "postgres" | "postgresql" => rustspider::StorageBackendKind::Postgres,
        "mysql" => rustspider::StorageBackendKind::MySql,
        "mongo" | "mongodb" => rustspider::StorageBackendKind::MongoDb,
        _ => return None,
    };
    Some(rustspider::ProcessResultStore::new(
        rustspider::StorageBackendConfig {
            kind,
            endpoint,
            table: env::var("RUSTSPIDER_STORAGE_TABLE")
                .ok()
                .filter(|v| !v.trim().is_empty()),
            collection: env::var("RUSTSPIDER_STORAGE_COLLECTION")
                .ok()
                .filter(|v| !v.trim().is_empty()),
        },
    ))
}

fn configured_driver_result_store() -> Option<rustspider::DriverResultStore> {
    let mode = env::var("RUSTSPIDER_STORAGE_MODE")
        .ok()?
        .trim()
        .to_lowercase();
    if mode != "driver" {
        return None;
    }
    let backend = env::var("RUSTSPIDER_STORAGE_BACKEND")
        .ok()?
        .trim()
        .to_lowercase();
    let endpoint = env::var("RUSTSPIDER_STORAGE_ENDPOINT")
        .ok()?
        .trim()
        .to_string();
    if endpoint.is_empty() {
        return None;
    }
    let kind = match backend.as_str() {
        "postgres" | "postgresql" => rustspider::StorageBackendKind::Postgres,
        "mysql" => rustspider::StorageBackendKind::MySql,
        "mongo" | "mongodb" => rustspider::StorageBackendKind::MongoDb,
        _ => return None,
    };
    Some(rustspider::DriverResultStore::new(
        rustspider::StorageBackendConfig {
            kind,
            endpoint,
            table: env::var("RUSTSPIDER_STORAGE_TABLE")
                .ok()
                .filter(|v| !v.trim().is_empty()),
            collection: env::var("RUSTSPIDER_STORAGE_COLLECTION")
                .ok()
                .filter(|v| !v.trim().is_empty()),
        },
    ))
}

fn preferred_browser_engine(job: &RuntimeJobSpec) -> String {
    if let Some(value) = job
        .metadata
        .as_ref()
        .and_then(|metadata| metadata.get("browser_engine"))
        .and_then(|value| value.as_str())
    {
        return value.to_string();
    }
    env::var("RUSTSPIDER_BROWSER_ENGINE").unwrap_or_else(|_| "auto".to_string())
}

fn browser_artifact_base(job: &RuntimeJobSpec) -> String {
    if let Some(prefix) = job
        .output
        .artifact_prefix
        .as_ref()
        .filter(|value| !value.trim().is_empty())
    {
        return prefix.clone();
    }
    job.name.clone()
}

fn browser_artifact_dir(job: &RuntimeJobSpec) -> PathBuf {
    if let Some(directory) = job
        .output
        .directory
        .as_ref()
        .filter(|value| !value.trim().is_empty())
    {
        return PathBuf::from(directory);
    }
    PathBuf::from("artifacts").join("browser")
}

fn browser_screenshot_path(job: &RuntimeJobSpec, label: &str) -> PathBuf {
    browser_artifact_dir(job).join(format!("{}-{}.png", browser_artifact_base(job), label))
}

fn browser_graph_path(job: &RuntimeJobSpec, label: &str) -> PathBuf {
    browser_artifact_dir(job).join(format!(
        "{}-{}.graph.json",
        browser_artifact_base(job),
        label
    ))
}

fn persist_browser_graph_artifact(job: &RuntimeJobSpec, html: &str, label: &str) -> Option<String> {
    if html.trim().is_empty() {
        return None;
    }
    let mut graph = rustspider::GraphBuilder::new();
    graph.rebuild_from_html(html);
    let payload = serde_json::json!({
        "root_id": graph.root_id,
        "nodes": graph.nodes,
        "edges": graph.edges,
        "stats": graph.stats(),
    });
    let path = browser_graph_path(job, label);
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let encoded = serde_json::to_vec_pretty(&payload).ok()?;
    fs::write(&path, encoded).ok()?;
    Some(path.to_string_lossy().to_string())
}

fn runtime_graph_path(job: &RuntimeJobSpec, label: &str) -> PathBuf {
    if let Some(directory) = job
        .output
        .directory
        .as_ref()
        .filter(|value| !value.trim().is_empty())
    {
        return PathBuf::from(directory).join(format!(
            "{}-{}.graph.json",
            browser_artifact_base(job),
            label
        ));
    }
    if let Some(path) = job
        .output
        .path
        .as_ref()
        .filter(|value| !value.trim().is_empty())
    {
        let output = PathBuf::from(path);
        if let Some(parent) = output.parent() {
            return parent.join(format!(
                "{}-{}.graph.json",
                browser_artifact_base(job),
                label
            ));
        }
    }
    PathBuf::from("artifacts").join("exports").join(format!(
        "{}-{}.graph.json",
        browser_artifact_base(job),
        label
    ))
}

fn persist_runtime_graph_artifact(job: &RuntimeJobSpec, body: &str, label: &str) -> Option<String> {
    let lower = body.to_ascii_lowercase();
    if body.trim().is_empty() || (!lower.contains("<html") && !lower.contains("<title")) {
        return None;
    }
    let mut graph = rustspider::GraphBuilder::new();
    graph.rebuild_from_html(body);
    let payload = serde_json::json!({
        "root_id": graph.root_id,
        "nodes": graph.nodes,
        "edges": graph.edges,
        "stats": graph.stats(),
    });
    let path = runtime_graph_path(job, label);
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let encoded = serde_json::to_vec_pretty(&payload).ok()?;
    fs::write(&path, encoded).ok()?;
    Some(path.to_string_lossy().to_string())
}

fn artifact_envelope_from_paths(paths: &[String]) -> serde_json::Value {
    let mut envelope = serde_json::Map::new();
    let mut counter = 1usize;
    for path_value in paths {
        if path_value.trim().is_empty() {
            continue;
        }
        let path = PathBuf::from(path_value);
        let file_name = path
            .file_name()
            .and_then(|value| value.to_str())
            .unwrap_or(path_value);
        let lower = file_name.to_ascii_lowercase();
        let key = if lower.ends_with(".graph.json") || lower.contains("-graph.json") {
            "graph".to_string()
        } else {
            let value = format!("artifact_{counter}");
            counter += 1;
            value
        };
        let kind = if lower.ends_with(".png") {
            "screenshot"
        } else if lower.ends_with(".html") {
            "html"
        } else if lower.ends_with(".graph.json")
            || (lower.ends_with(".json") && lower.contains("graph"))
        {
            "graph"
        } else {
            "artifact"
        };

        let mut artifact = serde_json::Map::new();
        artifact.insert("kind".to_string(), serde_json::json!(kind));
        artifact.insert("path".to_string(), serde_json::json!(path_value));
        if key == "graph" {
            if let Ok(raw) = fs::read_to_string(&path) {
                if let Ok(graph_payload) = serde_json::from_str::<serde_json::Value>(&raw) {
                    if let Some(root_id) = graph_payload.get("root_id") {
                        artifact.insert("root_id".to_string(), root_id.clone());
                    }
                    if let Some(stats) = graph_payload.get("stats") {
                        artifact.insert("stats".to_string(), stats.clone());
                    }
                }
            }
        }
        envelope
            .entry(key)
            .or_insert(serde_json::Value::Object(artifact));
    }
    serde_json::Value::Object(envelope)
}

#[cfg(feature = "browser")]
fn browser_config_for_job(job: &RuntimeJobSpec) -> rustspider::browser::BrowserConfig {
    let mut config = rustspider::browser::BrowserConfig {
        headless: job
            .browser
            .as_ref()
            .and_then(|browser| browser.headless)
            .unwrap_or(true),
        timeout: std::time::Duration::from_millis(runtime_timeout_ms(job)),
        user_agent: Some(runtime_user_agent(job)),
        proxy: job.target.proxy.clone(),
        ..rustspider::browser::BrowserConfig::default()
    };
    if let Some(url) = job
        .metadata
        .as_ref()
        .and_then(|value| value.get("webdriver_url"))
        .and_then(|value| value.as_str())
    {
        config.webdriver_url = url.to_string();
    } else if let Ok(url) = env::var("RUSTSPIDER_WEBDRIVER_URL") {
        if !url.trim().is_empty() {
            config.webdriver_url = url;
        }
    }
    config
}

#[cfg(feature = "browser")]
async fn apply_browser_cookies(
    browser: &rustspider::browser::BrowserManager,
    job: &RuntimeJobSpec,
) -> Result<(), String> {
    for (name, value) in &job.target.cookies {
        browser
            .set_cookie(name, value, None)
            .await
            .map_err(|err| err.to_string())?;
    }
    if !job.target.cookies.is_empty() {
        browser
            .refresh()
            .await
            .map_err(|err| format!("browser refresh after cookie injection failed: {err}"))?;
    }
    Ok(())
}

#[cfg(feature = "browser")]
fn action_extra_string(action: &RuntimeBrowserAction, key: &str) -> Option<String> {
    action
        .extra
        .as_ref()
        .and_then(|extra| extra.get(key))
        .and_then(|value| value.as_str())
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(ToOwned::to_owned)
}

#[cfg(feature = "browser")]
fn action_shadow_path(action: &RuntimeBrowserAction) -> Result<Vec<String>, String> {
    if let Some(extra) = action
        .extra
        .as_ref()
        .and_then(|extra| extra.get("shadow_path"))
    {
        if let Some(path) = extra.as_array() {
            let selectors: Vec<String> = path
                .iter()
                .filter_map(|value| value.as_str())
                .map(str::trim)
                .filter(|value| !value.is_empty())
                .map(ToOwned::to_owned)
                .collect();
            if selectors.len() == path.len() && !selectors.is_empty() {
                return Ok(selectors);
            }
            return Err("extra.shadow_path must be a non-empty string array".to_string());
        }
        if let Some(path) = extra.as_str() {
            let selectors = split_shadow_path(path);
            if !selectors.is_empty() {
                return Ok(selectors);
            }
        }
        return Err("extra.shadow_path must be a string or string array".to_string());
    }

    let selector = action
        .selector
        .as_deref()
        .ok_or_else(|| "shadow action requires selector or extra.shadow_path".to_string())?;
    let selectors = split_shadow_path(selector);
    if selectors.is_empty() {
        return Err("shadow action selector path cannot be empty".to_string());
    }
    Ok(selectors)
}

#[cfg(feature = "browser")]
fn split_shadow_path(path: &str) -> Vec<String> {
    path.split(">>>")
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(ToOwned::to_owned)
        .collect()
}

#[cfg(feature = "browser")]
async fn run_browser_actions(
    browser: &rustspider::browser::BrowserManager,
    job: &RuntimeJobSpec,
    extracted: &mut serde_json::Map<String, serde_json::Value>,
    artifacts: &mut Vec<String>,
    warnings: &mut Vec<String>,
) -> Result<(), String> {
    let Some(browser_spec) = &job.browser else {
        return Ok(());
    };

    for (index, action) in browser_spec.actions.iter().enumerate() {
        let timeout = action
            .timeout_ms
            .map(std::time::Duration::from_millis)
            .or(Some(std::time::Duration::from_millis(runtime_timeout_ms(
                job,
            ))));
        match action.action_type.as_str() {
            "goto" => {
                let target = action.url.as_deref().unwrap_or(&job.target.url);
                browser
                    .navigate(target)
                    .await
                    .map_err(|err| format!("browser goto failed: {err}"))?;
                browser
                    .wait_for_page_load(timeout)
                    .await
                    .map_err(|err| format!("browser wait after goto failed: {err}"))?;
            }
            "wait" => {
                if let Some(selector) = action.selector.as_deref() {
                    browser
                        .wait_for_element(selector, timeout)
                        .await
                        .map_err(|err| format!("browser wait for element failed: {err}"))?;
                } else if let Some(delay) = action.timeout_ms {
                    tokio::time::sleep(std::time::Duration::from_millis(delay)).await;
                } else {
                    browser
                        .wait_for_page_load(timeout)
                        .await
                        .map_err(|err| format!("browser wait for page load failed: {err}"))?;
                }
            }
            "click" => {
                let selector = action
                    .selector
                    .as_deref()
                    .ok_or_else(|| "browser click requires selector".to_string())?;
                let frame_selector = action_extra_string(action, "frame_selector");
                if let Some(frame) = frame_selector.as_deref() {
                    browser
                        .enter_frame(frame)
                        .await
                        .map_err(|err| format!("browser enter frame failed: {err}"))?;
                }
                let click_result = browser
                    .click(selector)
                    .await
                    .map_err(|err| format!("browser click failed: {err}"));
                if frame_selector.is_some() {
                    browser
                        .enter_parent_frame()
                        .await
                        .map_err(|err| format!("browser leave frame failed: {err}"))?;
                }
                click_result?;
            }
            "type" => {
                let selector = action
                    .selector
                    .as_deref()
                    .ok_or_else(|| "browser type requires selector".to_string())?;
                let value = action.value.as_deref().unwrap_or("");
                let frame_selector = action_extra_string(action, "frame_selector");
                if let Some(frame) = frame_selector.as_deref() {
                    browser
                        .enter_frame(frame)
                        .await
                        .map_err(|err| format!("browser enter frame failed: {err}"))?;
                }
                let type_result = browser
                    .fill_clear(selector, value)
                    .await
                    .map_err(|err| format!("browser type failed: {err}"));
                if frame_selector.is_some() {
                    browser
                        .enter_parent_frame()
                        .await
                        .map_err(|err| format!("browser leave frame failed: {err}"))?;
                }
                type_result?;
            }
            "upload" => {
                let selector = action
                    .selector
                    .as_deref()
                    .ok_or_else(|| "browser upload requires selector".to_string())?;
                let value = action
                    .value
                    .as_deref()
                    .ok_or_else(|| "browser upload requires value file path".to_string())?;
                let frame_selector = action_extra_string(action, "frame_selector");
                if let Some(frame) = frame_selector.as_deref() {
                    browser
                        .enter_frame(frame)
                        .await
                        .map_err(|err| format!("browser enter frame failed: {err}"))?;
                }
                let upload_result = browser
                    .upload_file(selector, value)
                    .await
                    .map_err(|err| format!("browser upload failed: {err}"));
                if frame_selector.is_some() {
                    browser
                        .enter_parent_frame()
                        .await
                        .map_err(|err| format!("browser leave frame failed: {err}"))?;
                }
                upload_result?;
            }
            "enter_frame" => {
                let selector = action
                    .selector
                    .as_deref()
                    .ok_or_else(|| "browser enter_frame requires selector".to_string())?;
                browser
                    .enter_frame(selector)
                    .await
                    .map_err(|err| format!("browser enter_frame failed: {err}"))?;
            }
            "enter_parent_frame" | "leave_frame" => {
                browser
                    .enter_parent_frame()
                    .await
                    .map_err(|err| format!("browser enter_parent_frame failed: {err}"))?;
            }
            "select" => {
                let selector = action
                    .selector
                    .as_deref()
                    .ok_or_else(|| "browser select requires selector".to_string())?;
                let value = action.value.as_deref().unwrap_or("");
                browser
                    .select_option_by_value(selector, value)
                    .await
                    .map_err(|err| format!("browser select failed: {err}"))?;
            }
            "hover" => {
                let selector = action
                    .selector
                    .as_deref()
                    .ok_or_else(|| "browser hover requires selector".to_string())?;
                browser
                    .hover(selector)
                    .await
                    .map_err(|err| format!("browser hover failed: {err}"))?;
            }
            "scroll" => {
                if let Some(selector) = action.selector.as_deref() {
                    browser
                        .scroll_to_element(selector)
                        .await
                        .map_err(|err| format!("browser scroll to element failed: {err}"))?;
                } else if matches!(action.value.as_deref(), Some("top")) {
                    browser
                        .scroll_to_top()
                        .await
                        .map_err(|err| format!("browser scroll to top failed: {err}"))?;
                } else {
                    browser
                        .scroll_to_bottom()
                        .await
                        .map_err(|err| format!("browser scroll to bottom failed: {err}"))?;
                }
            }
            "eval" => {
                let script = action.value.as_deref().unwrap_or("");
                let value = browser
                    .execute_script_value(script)
                    .await
                    .map_err(|err| format!("browser eval failed: {err}"))?;
                if let Some(field) = action.save_as.as_deref() {
                    extracted.insert(field.to_string(), value);
                }
            }
            "shadow_text" | "shadow_html" | "shadow_extract" => {
                let selector_path = action_shadow_path(action)?;
                let selector_refs: Vec<&str> = selector_path.iter().map(String::as_str).collect();
                let expression = action.value.as_deref().unwrap_or_else(|| {
                    if action.action_type == "shadow_html" {
                        "target.outerHTML || target.textContent || ''"
                    } else {
                        "target.textContent || ''"
                    }
                });
                let value = browser
                    .execute_shadow_dom(&selector_refs, expression)
                    .await
                    .map_err(|err| format!("browser shadow dom action failed: {err}"))?;
                if let Some(field) = action.save_as.as_deref() {
                    extracted.insert(field.to_string(), value);
                }
            }
            "install_realtime_capture" => {
                browser
                    .install_realtime_capture()
                    .await
                    .map_err(|err| format!("browser realtime capture install failed: {err}"))?;
            }
            "listen_realtime" | "capture_realtime" => {
                if let Some(delay) = action.timeout_ms {
                    tokio::time::sleep(std::time::Duration::from_millis(delay)).await;
                }
                let entries = browser
                    .get_realtime_messages()
                    .await
                    .map_err(|err| format!("browser realtime capture failed: {err}"))?;
                extracted.insert(
                    action
                        .save_as
                        .as_deref()
                        .unwrap_or("realtime_messages")
                        .to_string(),
                    serde_json::Value::Array(entries),
                );
            }
            "listen_network" => {
                browser
                    .wait_for_network_idle(timeout)
                    .await
                    .map_err(|err| format!("browser wait for network idle failed: {err}"))?;
                let entries = browser
                    .get_network_requests()
                    .await
                    .map_err(|err| format!("browser listen_network failed: {err}"))?;
                extracted.insert(
                    action
                        .save_as
                        .as_deref()
                        .unwrap_or("network_requests")
                        .to_string(),
                    serde_json::Value::Array(entries),
                );
            }
            "screenshot" => {
                let path =
                    action.value.as_ref().map(PathBuf::from).unwrap_or_else(|| {
                        browser_screenshot_path(job, &format!("action-{index}"))
                    });
                if let Some(parent) = path.parent() {
                    let _ = fs::create_dir_all(parent);
                }
                browser
                    .screenshot_to_file(path.to_string_lossy().as_ref())
                    .await
                    .map_err(|err| format!("browser screenshot failed: {err}"))?;
                artifacts.push(path.to_string_lossy().to_string());
            }
            unsupported => warnings.push(format!(
                "unsupported browser action in rust browser runtime: {unsupported}"
            )),
        }
    }
    Ok(())
}

#[cfg(feature = "browser")]
async fn run_browser_extracts(
    browser: &rustspider::browser::BrowserManager,
    job: &RuntimeJobSpec,
    html: &str,
    current_url: &str,
    title: &str,
    extracted: &mut serde_json::Map<String, serde_json::Value>,
    warnings: &mut Vec<String>,
) {
    for spec in &job.extract {
        let value = match spec.extract_type.as_str() {
            "ai" => ai_extract_value(spec, &rustspider::HTMLParser::new(html), html, current_url)
                .or_else(|| {
                    Some(serde_json::Value::String(title.to_string()))
                        .filter(|_| spec.field == "title")
                }),
            "css" => match spec.expr.as_deref() {
                Some("title") => Some(serde_json::Value::String(title.to_string())),
                Some(expr) => browser
                    .get_element_text(expr)
                    .await
                    .ok()
                    .map(serde_json::Value::String),
                None => None,
            },
            "css_attr" => match (spec.expr.as_deref(), spec.attr.as_deref()) {
                (Some(expr), Some(attr)) => browser
                    .get_element_attribute(expr, attr)
                    .await
                    .ok()
                    .map(serde_json::Value::String),
                _ => None,
            },
            "xpath" => match spec.expr.as_deref() {
                Some(expr) => match rustspider::HTMLParser::new(html).xpath_first_strict(expr) {
                    Ok(value) => value.map(serde_json::Value::String),
                    Err(err) => {
                        warnings.push(err);
                        None
                    }
                },
                None => None,
            },
            "json_path" => {
                let path = spec.path.as_deref().or(spec.expr.as_deref());
                match (rustspider::JSONParser::new(html), path) {
                    (Some(parser), Some(path)) => parser.get(path).map(|value| {
                        if value.is_string() {
                            serde_json::Value::String(
                                value.as_str().unwrap_or_default().to_string(),
                            )
                        } else {
                            value.clone()
                        }
                    }),
                    _ => None,
                }
            }
            "regex" => {
                if let Some(expr) = spec.expr.as_deref() {
                    regex::Regex::new(expr).ok().and_then(|compiled| {
                        compiled
                            .captures(html)
                            .and_then(|captures| captures.get(1).or_else(|| captures.get(0)))
                            .map(|capture| serde_json::Value::String(capture.as_str().to_string()))
                    })
                } else {
                    None
                }
            }
            _ if spec.field == "url" => Some(serde_json::Value::String(current_url.to_string())),
            _ if spec.field == "html" || spec.field == "dom" => {
                Some(serde_json::Value::String(html.to_string()))
            }
            unsupported => {
                warnings.push(format!(
                    "unsupported extract type in rust browser runtime: {unsupported}"
                ));
                None
            }
        };
        if let Some(value) = value {
            if let Err(err) = validate_extract_schema(spec, &value) {
                warnings.push(err);
                continue;
            }
            extracted.insert(spec.field.clone(), value);
        } else if spec.required.unwrap_or(false) {
            warnings.push(format!(
                "required extract field could not be resolved in rust browser runtime: {}",
                spec.field
            ));
        }
    }
}

#[cfg(feature = "browser")]
async fn execute_browser_job(
    job: &RuntimeJobSpec,
    anti_bot: &serde_json::Value,
    recovery: &serde_json::Value,
    warning_seed: &serde_json::Value,
    started: std::time::Instant,
) -> Result<serde_json::Value, String> {
    let browser = rustspider::browser::BrowserManager::new(browser_config_for_job(job))
        .await
        .map_err(|err| format!("browser runtime initialization failed: {err}"))?;

    let outcome = async {
        browser
            .navigate(&job.target.url)
            .await
            .map_err(|err| format!("browser navigate failed: {err}"))?;
        browser
            .wait_for_page_load(Some(std::time::Duration::from_millis(runtime_timeout_ms(
                job,
            ))))
            .await
            .map_err(|err| format!("browser wait for page load failed: {err}"))?;
        apply_browser_cookies(&browser, job).await?;

        let mut extracted = serde_json::Map::new();
        let mut artifacts = Vec::<String>::new();
        let mut warnings = warning_seed
            .as_array()
            .cloned()
            .unwrap_or_default()
            .into_iter()
            .filter_map(|value| value.as_str().map(ToString::to_string))
            .collect::<Vec<_>>();

        run_browser_actions(&browser, job, &mut extracted, &mut artifacts, &mut warnings).await?;

        let current_url = browser
            .get_url()
            .await
            .map_err(|err| format!("browser get url failed: {err}"))?;
        let title = browser
            .get_title()
            .await
            .map_err(|err| format!("browser get title failed: {err}"))?;
        let html = browser
            .get_html()
            .await
            .map_err(|err| format!("browser get html failed: {err}"))?;

        run_browser_extracts(
            &browser,
            job,
            &html,
            &current_url,
            &title,
            &mut extracted,
            &mut warnings,
        )
        .await;

        if let Some(browser_spec) = &job.browser {
            for capture in &browser_spec.capture {
                match capture.as_str() {
                    "html" | "dom" => {
                        extracted
                            .insert(capture.to_string(), serde_json::Value::String(html.clone()));
                    }
                    "screenshot" => {
                        let path = browser_screenshot_path(job, "capture");
                        if let Some(parent) = path.parent() {
                            let _ = fs::create_dir_all(parent);
                        }
                        browser
                            .screenshot_to_file(path.to_string_lossy().as_ref())
                            .await
                            .map_err(|err| format!("browser capture screenshot failed: {err}"))?;
                        artifacts.push(path.to_string_lossy().to_string());
                    }
                    "realtime" | "websocket" | "sse" => {
                        let entries = browser
                            .get_realtime_messages()
                            .await
                            .map_err(|err| format!("browser realtime capture failed: {err}"))?;
                        extracted.insert(capture.to_string(), serde_json::Value::Array(entries));
                    }
                    "console" | "har" => warnings.push(format!(
                        "unsupported browser.capture value in rust browser runtime: {capture}"
                    )),
                    _ => {}
                }
            }
        }
        if let Some(path) = persist_browser_graph_artifact(job, &html, "graph") {
            artifacts.push(path);
        }

        let artifact_envelope = artifact_envelope_from_paths(&artifacts);
        Ok(serde_json::json!({
            "job_name": job.name,
            "runtime": job.runtime,
            "priority": job.priority,
            "state": "succeeded",
            "browser_engine": "webdriver",
            "url": current_url,
            "title": title,
            "status_code": 200,
            "body": html.clone(),
            "extract": serde_json::Value::Object(extracted),
            "detected_media": if html.contains(".m3u8") { vec!["hls"] } else { Vec::<&str>::new() },
            "artifacts": artifact_envelope.clone(),
            "artifact_refs": artifact_envelope,
            "output": {
                "format": job.output.format,
                "path": job.output.path,
                "directory": job.output.directory,
                "artifact_prefix": job.output.artifact_prefix,
            },
            "browser": json_or_null(&job.browser),
            "resources": json_or_null(&job.resources),
            "policy": json_or_null(&job.policy),
            "schedule": json_or_null(&job.schedule),
            "anti_bot": anti_bot.clone(),
            "recovery": recovery.clone(),
            "warnings": warnings,
            "error": "",
            "metrics": {
                "latency_ms": started.elapsed().as_millis() as u64,
            }
        }))
    }
    .await;

    let _ = browser.close().await;
    outcome
}

fn decorate_playwright_helper_payload(
    mut payload: serde_json::Value,
    job: &RuntimeJobSpec,
    anti_bot: &serde_json::Value,
    recovery: &serde_json::Value,
    warnings: &serde_json::Value,
    started: std::time::Instant,
    fallback: bool,
) -> serde_json::Value {
    if let Some(obj) = payload.as_object_mut() {
        let artifact_paths = obj
            .get("artifacts")
            .and_then(|value| value.as_array())
            .cloned()
            .unwrap_or_default()
            .into_iter()
            .filter_map(|value| value.as_str().map(ToString::to_string))
            .collect::<Vec<_>>();
        let artifact_envelope = artifact_envelope_from_paths(&artifact_paths);
        obj.insert("job_name".to_string(), serde_json::json!(job.name));
        obj.insert("runtime".to_string(), serde_json::json!(job.runtime));
        obj.insert("priority".to_string(), serde_json::json!(job.priority));
        obj.insert("state".to_string(), serde_json::json!("succeeded"));
        obj.insert(
            "browser_engine".to_string(),
            serde_json::json!(if fallback {
                "playwright-helper"
            } else {
                "playwright-node"
            }),
        );
        obj.insert(
            "output".to_string(),
            serde_json::json!({
                "format": job.output.format,
                "path": job.output.path,
                "directory": job.output.directory,
                "artifact_prefix": job.output.artifact_prefix,
            }),
        );
        obj.insert("browser".to_string(), json_or_null(&job.browser));
        obj.insert("resources".to_string(), json_or_null(&job.resources));
        obj.insert("policy".to_string(), json_or_null(&job.policy));
        obj.insert("schedule".to_string(), json_or_null(&job.schedule));
        obj.insert("anti_bot".to_string(), anti_bot.clone());
        obj.insert("recovery".to_string(), recovery.clone());
        let helper_warnings = obj
            .get("warnings")
            .and_then(|value| value.as_array())
            .cloned()
            .unwrap_or_default();
        let mut merged_warnings = warnings.as_array().cloned().unwrap_or_default();
        merged_warnings.extend(helper_warnings);
        merged_warnings.push(serde_json::json!(if fallback {
            "browser runtime fell back to shared Playwright helper"
        } else {
            "browser runtime executed via native Playwright process"
        }));
        obj.insert(
            "warnings".to_string(),
            serde_json::Value::Array(merged_warnings),
        );
        obj.insert("artifacts".to_string(), artifact_envelope.clone());
        obj.insert("artifact_refs".to_string(), artifact_envelope);
        obj.insert("error".to_string(), serde_json::json!(""));
        obj.insert(
            "metrics".to_string(),
            serde_json::json!({
                "latency_ms": started.elapsed().as_millis() as u64,
            }),
        );
    }
    payload
}

fn handle_job(args: &[String]) -> i32 {
    if args.len() < 2 || args[0] != "--file" {
        eprintln!("usage: rustspider job --file <job.json>");
        return 2;
    }

    let job_path = args[1].clone();

    let job = match load_runtime_job(&job_path) {
        Ok(job) => job,
        Err(err) => {
            eprintln!("{err}");
            return 1;
        }
    };
    let started = std::time::Instant::now();
    let anti_bot = merge_anti_bot(&job);
    let recovery = job
        .metadata
        .as_ref()
        .and_then(|value| value.get("mock_recovery"))
        .cloned()
        .unwrap_or(serde_json::Value::Null);
    let browser_runtime_active = job.runtime == "browser";
    let warnings = combined_warnings(&job, browser_runtime_active);
    if let Some(message) = job
        .metadata
        .as_ref()
        .and_then(|value| value.get("fail_job"))
        .and_then(|value| value.as_str())
    {
        let payload = serde_json::json!({
            "job_name": job.name,
            "runtime": job.runtime,
            "state": "failed",
            "url": job.target.url,
            "extract": {},
            "artifacts": {},
            "artifact_refs": {},
            "output": {
                "format": job.output.format,
                "path": job.output.path,
                "directory": job.output.directory,
                "artifact_prefix": job.output.artifact_prefix,
            },
            "browser": json_or_null(&job.browser),
            "resources": json_or_null(&job.resources),
            "policy": json_or_null(&job.policy),
            "schedule": json_or_null(&job.schedule),
            "anti_bot": anti_bot.clone(),
            "recovery": recovery.clone(),
            "warnings": warnings.clone(),
            "error": format!("injected failure: {message}"),
            "metrics": {
                "latency_ms": started.elapsed().as_millis() as u64,
            }
        });
        println!(
            "{}",
            serde_json::to_string_pretty(&payload).unwrap_or_default()
        );
        eprintln!("job failed: injected failure: {message}");
        return 1;
    }

    #[cfg(feature = "browser")]
    if browser_runtime_active {
        let preferred_engine = preferred_browser_engine(&job).to_lowercase();
        if matches!(
            preferred_engine.as_str(),
            "playwright" | "playwright-node" | "node-playwright" | "native-playwright"
        ) {
            match run_native_playwright_job_helper(&job_path) {
                Ok(payload) => {
                    let payload = decorate_playwright_helper_payload(
                        payload, &job, &anti_bot, &recovery, &warnings, started, false,
                    );
                    persist_job_payload(&job, &payload);
                    println!(
                        "{}",
                        serde_json::to_string_pretty(&payload).unwrap_or_default()
                    );
                    return 0;
                }
                Err(_) => {}
            }
        }

        if matches!(
            preferred_engine.as_str(),
            "playwright-helper"
                | "helper"
                | "playwright"
                | "playwright-node"
                | "node-playwright"
                | "native-playwright"
        ) {
            match run_playwright_job_helper(&job_path) {
                Ok(payload) => {
                    let payload = decorate_playwright_helper_payload(
                        payload, &job, &anti_bot, &recovery, &warnings, started, false,
                    );
                    persist_job_payload(&job, &payload);
                    println!(
                        "{}",
                        serde_json::to_string_pretty(&payload).unwrap_or_default()
                    );
                    return 0;
                }
                Err(helper_err) => {
                    let payload = serde_json::json!({
                        "job_name": job.name,
                        "runtime": job.runtime,
                        "priority": job.priority,
                        "state": "failed",
                        "url": job.target.url,
                        "extract": {},
                        "detected_media": [],
                        "artifacts": {},
                        "artifact_refs": {},
                        "output": {
                            "format": job.output.format,
                            "path": job.output.path,
                            "directory": job.output.directory,
                            "artifact_prefix": job.output.artifact_prefix,
                        },
                        "browser": json_or_null(&job.browser),
                        "resources": json_or_null(&job.resources),
                        "policy": json_or_null(&job.policy),
                        "schedule": json_or_null(&job.schedule),
                        "anti_bot": anti_bot.clone(),
                        "recovery": recovery.clone(),
                        "warnings": warnings.clone(),
                        "error": format!("preferred playwright helper execution failed: {helper_err}"),
                        "metrics": {
                            "latency_ms": started.elapsed().as_millis() as u64,
                        }
                    });
                    persist_job_payload(&job, &payload);
                    println!(
                        "{}",
                        serde_json::to_string_pretty(&payload).unwrap_or_default()
                    );
                    eprintln!(
                        "job failed: {}",
                        payload["error"].as_str().unwrap_or("browser job failed")
                    );
                    return 1;
                }
            }
        }

        match tokio::runtime::Runtime::new() {
            Ok(runtime) => match runtime.block_on(execute_browser_job(
                &job, &anti_bot, &recovery, &warnings, started,
            )) {
                Ok(payload) => {
                    persist_job_payload(&job, &payload);
                    println!(
                        "{}",
                        serde_json::to_string_pretty(&payload).unwrap_or_default()
                    );
                    return 0;
                }
                Err(err) => match run_playwright_job_helper(&job_path) {
                    Ok(payload) => {
                        let payload = decorate_playwright_helper_payload(
                            payload, &job, &anti_bot, &recovery, &warnings, started, true,
                        );
                        persist_job_payload(&job, &payload);
                        println!(
                            "{}",
                            serde_json::to_string_pretty(&payload).unwrap_or_default()
                        );
                        return 0;
                    }
                    Err(helper_err) => {
                        let payload = serde_json::json!({
                            "job_name": job.name,
                            "runtime": job.runtime,
                            "priority": job.priority,
                            "state": "failed",
                            "url": job.target.url,
                            "extract": {},
                            "detected_media": [],
                            "artifacts": {},
                            "artifact_refs": {},
                            "output": {
                                "format": job.output.format,
                                "path": job.output.path,
                                "directory": job.output.directory,
                                "artifact_prefix": job.output.artifact_prefix,
                            },
                            "browser": json_or_null(&job.browser),
                            "resources": json_or_null(&job.resources),
                            "policy": json_or_null(&job.policy),
                            "schedule": json_or_null(&job.schedule),
                            "anti_bot": anti_bot.clone(),
                            "recovery": recovery.clone(),
                            "warnings": warnings.clone(),
                            "error": format!("{err}; fallback failed: {helper_err}"),
                            "metrics": {
                                "latency_ms": started.elapsed().as_millis() as u64,
                            }
                        });
                        persist_job_payload(&job, &payload);
                        println!(
                            "{}",
                            serde_json::to_string_pretty(&payload).unwrap_or_default()
                        );
                        eprintln!(
                            "job failed: {}",
                            payload["error"].as_str().unwrap_or("browser job failed")
                        );
                        return 1;
                    }
                },
            },
            Err(err) => {
                eprintln!("job failed: failed to create tokio runtime for browser job: {err}");
                return 1;
            }
        }
    }

    let reactor = NativeReactor::new();
    let plan = build_runtime_plan(&job);
    match reactor.execute(plan) {
        Ok(result) => {
            let extract = build_extract_payload(&job, &result.body, &result.url);
            let mut artifacts = Vec::<String>::new();
            if let Some(path) = persist_runtime_graph_artifact(&job, &result.body, "graph") {
                artifacts.push(path);
            }
            let artifact_envelope = artifact_envelope_from_paths(&artifacts);
            let payload = serde_json::json!({
                "job_name": job.name,
                "runtime": job.runtime,
                "priority": job.priority,
                "state": "succeeded",
                "url": result.url,
                "status_code": result.status_code,
                "body": result.body,
                "extract": extract,
                "detected_media": result.detected_media,
                "artifacts": artifact_envelope.clone(),
                "artifact_refs": artifact_envelope,
                "output": {
                    "format": job.output.format,
                    "path": job.output.path,
                    "directory": job.output.directory,
                    "artifact_prefix": job.output.artifact_prefix,
                },
                "browser": json_or_null(&job.browser),
                "resources": json_or_null(&job.resources),
                "policy": json_or_null(&job.policy),
                "schedule": json_or_null(&job.schedule),
                "anti_bot": anti_bot.clone(),
                "recovery": recovery.clone(),
                "warnings": warnings.clone(),
                "error": "",
                "metrics": {
                    "latency_ms": started.elapsed().as_millis() as u64,
                }
            });
            persist_job_payload(&job, &payload);
            println!(
                "{}",
                serde_json::to_string_pretty(&payload).unwrap_or_default()
            );
            0
        }
        Err(err) => {
            let payload = serde_json::json!({
                "job_name": job.name,
                "runtime": job.runtime,
                "priority": job.priority,
                "state": "failed",
                "url": job.target.url,
                "extract": {},
                "detected_media": [],
                "artifacts": {},
                "artifact_refs": {},
                "output": {
                    "format": job.output.format,
                    "path": job.output.path,
                    "directory": job.output.directory,
                    "artifact_prefix": job.output.artifact_prefix,
                },
                "browser": json_or_null(&job.browser),
                "resources": json_or_null(&job.resources),
                "policy": json_or_null(&job.policy),
                "schedule": json_or_null(&job.schedule),
                "anti_bot": anti_bot.clone(),
                "recovery": recovery.clone(),
                "warnings": warnings.clone(),
                "error": err.to_string(),
                "metrics": {
                    "latency_ms": started.elapsed().as_millis() as u64,
                }
            });
            persist_job_payload(&job, &payload);
            println!(
                "{}",
                serde_json::to_string_pretty(&payload).unwrap_or_default()
            );
            eprintln!("job failed: {err}");
            1
        }
    }
}

fn print_capabilities() {
    let payload = serde_json::json!({
        "command": "capabilities",
        "framework": "rustspider",
        "runtime": "rust",
        "version": env!("CARGO_PKG_VERSION"),
        "entrypoints": ["config", "crawl", "browser", "ai", "doctor", "preflight", "export", "curl", "run", "job", "async-job", "workflow", "jobdir", "http-cache", "console", "audit", "web", "media", "ultimate", "sitemap-discover", "plugins", "selector-studio", "scrapy", "profile-site", "research", "node-reverse", "anti-bot", "capabilities", "version"],
        "runtimes": ["http", "browser", "media", "ai"],
        "modules": [
            "reactor.NativeReactor",
            "artifact.MemoryArtifactStore",
            "contracts.AutoscaledFrontier",
            "incremental.IncrementalCrawler",
            "curlconverter.CurlToRustConverter",
            "audit.FileAuditTrail",
            "workflow.WorkflowRunner",
            "connector.FileConnector",
            "event_bus.FileEventBus",
            "storage_backends.ProcessResultStore",
            "storage_backends.ProcessDatasetStore",
            "storage_backends.DriverResultStore",
            "storage_backends.DriverDatasetStore",
            "feature_gates",
            "bridge.CrawleeBridgeClient",
            "xpath_suggestions",
            "preflight",
            "research.ResearchJob",
            "research.ResearchRuntime",
            "async_research.AsyncResearchRuntime",
            "notebook_output.ExperimentTracker",
            "ai.sentiment.SentimentAnalyzer",
            "ai.summarizer.ContentSummarizer",
            "ai.entity_extractor.EntityExtractor",
            "browser",
            "media",
            "proxy",
            "retry",
            "antibot",
            "antibot.night_mode",
            "events.EventBus",
            "node_reverse",
            "node_discovery",
            "ssrf_protection",
            "site_profiler"
            ,
            "sitemap_discovery",
            "plugin_manifest",
            "selector_studio"
        ],
        "shared_contracts": [
            "shared-cli",
            "shared-config",
            "runtime-core",
            "autoscaled-frontier",
            "incremental-cache",
            "observability-envelope",
            "scrapy-project",
            "scrapy-plugins-manifest",
            "web-control-plane"
        ],
        "feature_gates": rustspider::feature_gates::catalog(),
        "operator_products": {
            "jobdir": {
                "pause_resume": true,
                "state_file": "job-state.json"
            },
            "http_cache": {
                "status_seed_clear": true,
                "backends": ["file-json", "memory"],
                "strategies": ["revalidate", "delta-fetch"]
            },
            "queue_backends": rustspider::queue_backends::queue_backend_support(),
            "browser_tooling": {
                "trace": true,
                "har": true,
                "route_mocking": true,
                "codegen": true
            },
            "antibot": {
                "behavior_randomization": true,
                "night_mode": {
                    "enabled": true,
                    "start_hour": 23,
                    "end_hour": 6,
                    "delay_multiplier": 1.5,
                    "rate_limit_factor": 0.5
                }
            },
            "node_discovery": {
                "providers": ["env", "file", "consul-http", "etcd-http"],
                "adapter_engine": "blocking-http"
            },
            "event_system": {
                "topics": [
                    "task:created",
                    "task:queued",
                    "task:running",
                    "task:succeeded",
                    "task:failed",
                    "task:cancelled",
                    "task:deleted",
                    "task:result"
                ],
                "pubsub": "crossbeam-channel",
                "jsonl_sink": true
            },
            "security": {
                "ssrf_guard": true,
                "validator": "ssrf_protection::SSRFProtection"
            },
            "storage_backends": rustspider::storage_backends::storage_backend_support(),
            "autoscaling_pools": {
                "frontier": true,
                "request_queue": "priority-queue",
                "session_pool": true,
                "browser_pool": true
            },
            "debug_console": {
                "snapshot": true,
                "tail": true,
                "control_plane_jsonl": true
            },
            "audit_console": {
                "snapshot": true,
                "tail": true,
                "job_filter": true
            },
            "event_system": {
                "topics": ["workflow.job.started", "workflow.step.started", "workflow.step.succeeded", "workflow.job.completed"],
                "storage": "jsonl+memory"
            },
            "connectors": {
                "native": ["memory", "jsonl"]
            },
            "workflow": {
                "step_types": ["goto", "wait", "click", "type", "select", "hover", "scroll", "eval", "listen_network", "extract", "download", "screenshot"],
                "connectors": true,
                "events": true
            },
            "crawlee_bridge": {
                "client": true,
                "endpoint": "/api/crawl"
            }
        },
        "ai_capabilities": {
            "providers": ["openai", "anthropic", "claude"],
            "few_shot": true,
            "sentiment_analysis": true,
            "summarization": true,
            "entity_extraction_specialized": true
        },
        "browser_compatibility": rustspider::browser::browser_compatibility_matrix(),
        "control_plane": {
            "task_api": true,
            "result_envelope": true,
            "artifact_refs": true,
            "graph_artifact": true,
            "graph_extract": true
        },
        "kernel_contracts": {
            "request": ["models.Request"],
            "fingerprint": ["contracts.RequestFingerprint"],
            "frontier": ["contracts.AutoscaledFrontier"],
            "scheduler": ["queue.PersistentPriorityQueue"],
            "middleware": ["contracts.Middleware"],
            "artifact_store": ["artifact.ArtifactStore", "contracts.FileArtifactStore"],
            "session_pool": ["contracts.SessionPool"],
            "proxy_policy": ["contracts.ProxyPolicy"],
            "observability": ["contracts.ObservabilityCollector"],
            "cache": ["incremental.IncrementalCrawler"]
        },
        "observability": [
            "doctor",
            "preflight",
            "audit",
            "profile-site",
            "selector-studio",
            "scrapy doctor",
            "scrapy profile",
            "scrapy bench",
            "prometheus",
            "opentelemetry-json"
        ]
    });
    println!(
        "{}",
        serde_json::to_string_pretty(&payload).unwrap_or_default()
    );
}

fn handle_scrapy(args: &[String]) -> i32 {
    if args.first().map(|value| value.as_str()) != Some("demo")
        && args.first().map(|value| value.as_str()) != Some("run")
        && args.first().map(|value| value.as_str()) != Some("export")
        && args.first().map(|value| value.as_str()) != Some("plan-ai")
        && args.first().map(|value| value.as_str()) != Some("sync-ai")
        && args.first().map(|value| value.as_str()) != Some("auth-validate")
        && args.first().map(|value| value.as_str()) != Some("auth-capture")
        && args.first().map(|value| value.as_str()) != Some("scaffold-ai")
        && args.first().map(|value| value.as_str()) != Some("profile")
        && args.first().map(|value| value.as_str()) != Some("doctor")
        && args.first().map(|value| value.as_str()) != Some("bench")
        && args.first().map(|value| value.as_str()) != Some("init")
        && args.first().map(|value| value.as_str()) != Some("shell")
        && args.first().map(|value| value.as_str()) != Some("list")
        && args.first().map(|value| value.as_str()) != Some("validate")
        && args.first().map(|value| value.as_str()) != Some("genspider")
        && args.first().map(|value| value.as_str()) != Some("contracts")
    {
        eprintln!("usage: scrapy <demo|run|plan-ai|sync-ai|auth-validate|auth-capture|scaffold-ai|contracts> ...");
        return 2;
    }
    let subcommand = args[0].clone();

    if subcommand == "contracts" {
        let Some(action) = args.get(1).map(|value| value.as_str()) else {
            eprintln!("usage: scrapy contracts <init|validate> --project <dir>");
            return 2;
        };
        if action != "init" && action != "validate" {
            eprintln!("usage: scrapy contracts <init|validate> --project <dir>");
            return 2;
        }
        let mut project = String::new();
        let mut i = 2usize;
        while i < args.len() {
            match args[i].as_str() {
                "--project" if i + 1 < args.len() => {
                    project = args[i + 1].clone();
                    i += 2;
                }
                other => {
                    eprintln!("unknown scrapy contracts argument: {other}");
                    return 2;
                }
            }
        }
        if project.trim().is_empty() {
            eprintln!("scrapy contracts requires --project");
            return 2;
        }
        return run_shared_python_tool(
            "spider_contracts.py",
            &[action.to_string(), "--project".to_string(), project],
        );
    }

    let mut url = String::from("https://example.com");
    let mut project = String::new();
    let mut selected_spider = String::new();
    let mut init_path = String::new();
    let mut html_file = String::new();
    let mut output = String::from("artifacts/exports/rustspider-scrapy-demo.json");
    let mut export_format = String::from("json");
    let mut spider_name = String::new();
    let mut spider_domain = String::new();
    let mut session_name = String::from("auth");
    let mut ai_template = false;
    let mut mode = String::from("css");
    let mut expr = String::new();
    let mut attr = String::new();
    let mut i = 1usize;
    while i < args.len() {
        match args[i].as_str() {
            "--url" if i + 1 < args.len() => {
                url = args[i + 1].clone();
                i += 2;
            }
            "--project" if i + 1 < args.len() => {
                project = args[i + 1].clone();
                i += 2;
            }
            "--spider" if i + 1 < args.len() => {
                selected_spider = args[i + 1].clone();
                i += 2;
            }
            "--path" if i + 1 < args.len() => {
                init_path = args[i + 1].clone();
                i += 2;
            }
            "--html-file" if i + 1 < args.len() => {
                html_file = args[i + 1].clone();
                i += 2;
            }
            "--output" if i + 1 < args.len() => {
                output = args[i + 1].clone();
                i += 2;
            }
            "--format" if i + 1 < args.len() => {
                export_format = args[i + 1].clone();
                i += 2;
            }
            "--type" if i + 1 < args.len() => {
                mode = args[i + 1].clone();
                i += 2;
            }
            "--expr" if i + 1 < args.len() => {
                expr = args[i + 1].clone();
                i += 2;
            }
            "--attr" if i + 1 < args.len() => {
                attr = args[i + 1].clone();
                i += 2;
            }
            "--name" if i + 1 < args.len() => {
                spider_name = args[i + 1].clone();
                i += 2;
            }
            "--domain" if i + 1 < args.len() => {
                spider_domain = args[i + 1].clone();
                i += 2;
            }
            "--session" if i + 1 < args.len() => {
                session_name = args[i + 1].clone();
                i += 2;
            }
            "--ai" => {
                ai_template = true;
                i += 1;
            }
            unknown => {
                eprintln!("unknown scrapy argument: {unknown}");
                return 2;
            }
        }
    }

    let read_manifest = |project_root: &str| -> Result<serde_json::Value, String> {
        let manifest_path = PathBuf::from(project_root).join("scrapy-project.json");
        let manifest_raw = fs::read_to_string(&manifest_path)
            .map_err(|err| format!("failed to read scrapy project manifest: {err}"))?;
        let manifest: serde_json::Value = serde_json::from_str(&manifest_raw)
            .map_err(|err| format!("invalid scrapy project manifest: {err}"))?;
        if manifest.get("runtime").and_then(|value| value.as_str()) != Some("rust") {
            return Err(format!(
                "runtime mismatch in {}: expected rust",
                manifest_path.display()
            ));
        }
        Ok(manifest)
    };
    let parse_spider_metadata = |path: &PathBuf| -> std::collections::HashMap<String, String> {
        let mut metadata = std::collections::HashMap::new();
        let Ok(content) = fs::read_to_string(path) else {
            return metadata;
        };
        for line in content.lines().take(5) {
            let trimmed = line.trim();
            if !trimmed.starts_with("// scrapy:") {
                continue;
            }
            let payload = trimmed.trim_start_matches("// scrapy:").trim();
            for part in payload.split_whitespace() {
                if let Some((key, value)) = part.split_once('=') {
                    metadata.insert(key.trim().to_string(), value.trim().to_string());
                }
            }
        }
        metadata
    };
    let discover_spiders = |project_root: &str,
                            manifest: &serde_json::Value|
     -> Vec<serde_json::Value> {
        let mut spiders = Vec::new();
        if let Some(entry) = manifest.get("entry").and_then(|value| value.as_str()) {
            let path = PathBuf::from(project_root).join(entry);
            let mut item = serde_json::json!({
                "name": PathBuf::from(entry).file_stem().and_then(|value| value.to_str()).unwrap_or("main"),
                "path": entry
            });
            if let Some(object) = item.as_object_mut() {
                for (key, value) in parse_spider_metadata(&path) {
                    object.insert(key, serde_json::Value::String(value));
                }
            }
            spiders.push(item);
        }
        for spiders_dir in [
            PathBuf::from(project_root).join("src").join("spiders"),
            PathBuf::from(project_root).join("spiders"),
        ] {
            if let Ok(entries) = fs::read_dir(&spiders_dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.extension().and_then(|value| value.to_str()) != Some("rs") {
                        continue;
                    }
                    let relative = path
                        .strip_prefix(project_root)
                        .ok()
                        .and_then(|value| value.to_str())
                        .unwrap_or_default()
                        .to_string();
                    let mut item = serde_json::json!({
                        "name": path.file_stem().and_then(|value| value.to_str()).unwrap_or_default(),
                        "path": relative
                    });
                    if let Some(object) = item.as_object_mut() {
                        for (key, value) in parse_spider_metadata(&path) {
                            object.insert(key, serde_json::Value::String(value));
                        }
                    }
                    spiders.push(item);
                }
            }
        }
        spiders
    };
    let resolve_project_output =
        |project_root: &str, manifest: &serde_json::Value, spider: &str| -> PathBuf {
            let default_output = manifest
                .get("output")
                .and_then(|value| value.as_str())
                .unwrap_or("artifacts/exports/items.json");
            if !spider.trim().is_empty() && default_output.ends_with("items.json") {
                return PathBuf::from(project_root)
                    .join("artifacts")
                    .join("exports")
                    .join(format!("{spider}.json"));
            }
            PathBuf::from(project_root).join(default_output)
        };
    let resolve_scrapy_runner_detail =
        |cfg: &ContractConfig, spider: &str, metadata: &serde_json::Value| -> (String, String) {
            let normalize = |value: Option<&str>| -> Option<String> {
                let value = value?.trim().to_ascii_lowercase();
                match value.as_str() {
                    "browser" | "http" | "hybrid" => Some(value),
                    _ => None,
                }
            };
            if let Some(runner) = metadata
                .get("runner")
                .and_then(|value| value.as_str())
                .and_then(|value| normalize(Some(value)))
            {
                return (runner, "metadata".to_string());
            }
            if let Some(spider_cfg) = cfg.scrapy.spiders.get(spider) {
                if let Some(runner) = normalize(Some(&spider_cfg.runner)) {
                    return (runner, "scrapy.spiders".to_string());
                }
            }
            if let Some(runner) = normalize(Some(&cfg.scrapy.runner)) {
                return (runner, "scrapy.runner".to_string());
            }
            ("http".to_string(), "default".to_string())
        };
    let resolve_scrapy_runner =
        |cfg: &ContractConfig, spider: &str, metadata: &serde_json::Value| -> String {
            resolve_scrapy_runner_detail(cfg, spider, metadata).0
        };
    let resolve_scrapy_url_detail = |cfg: &ContractConfig,
                                     spider: &str,
                                     metadata: &serde_json::Value,
                                     manifest_url: &str|
     -> (String, String) {
        if let Some(spider_cfg) = cfg.scrapy.spiders.get(spider) {
            if !spider_cfg.url.trim().is_empty() {
                return (
                    spider_cfg.url.trim().to_string(),
                    "scrapy.spiders".to_string(),
                );
            }
        }
        if let Some(url) = metadata.get("url").and_then(|value| value.as_str()) {
            if !url.trim().is_empty() {
                return (url.trim().to_string(), "metadata".to_string());
            }
        }
        if !manifest_url.trim().is_empty() {
            return (manifest_url.trim().to_string(), "manifest".to_string());
        }
        ("https://example.com".to_string(), "default".to_string())
    };
    let resolve_spider_display = |project_root: &str,
                                  manifest: &serde_json::Value,
                                  cfg: &ContractConfig|
     -> Vec<serde_json::Value> {
        let mut spiders = discover_spiders(project_root, manifest);
        for spider in &mut spiders {
            let name = spider
                .get("name")
                .and_then(|value| value.as_str())
                .unwrap_or_default()
                .to_string();
            let (runner, runner_source) = resolve_scrapy_runner_detail(cfg, &name, spider);
            let (url, url_source) = resolve_scrapy_url_detail(
                cfg,
                &name,
                spider,
                manifest
                    .get("url")
                    .and_then(|value| value.as_str())
                    .unwrap_or_default(),
            );
            if let Some(object) = spider.as_object_mut() {
                object.insert("runner".to_string(), serde_json::Value::String(runner));
                object.insert(
                    "runner_source".to_string(),
                    serde_json::Value::String(runner_source),
                );
                object.insert("url".to_string(), serde_json::Value::String(url));
                object.insert(
                    "url_source".to_string(),
                    serde_json::Value::String(url_source),
                );
                object.insert(
                    "pipelines".to_string(),
                    serde_json::Value::Array(
                        configured_scrapy_pipelines_for_spider(cfg, &name)
                            .into_iter()
                            .map(serde_json::Value::String)
                            .collect(),
                    ),
                );
                object.insert(
                    "spider_middlewares".to_string(),
                    serde_json::Value::Array(
                        configured_scrapy_spider_middlewares_for_spider(cfg, &name)
                            .into_iter()
                            .map(serde_json::Value::String)
                            .collect(),
                    ),
                );
                object.insert(
                    "downloader_middlewares".to_string(),
                    serde_json::Value::Array(
                        configured_scrapy_downloader_middlewares_for_spider(cfg, &name)
                            .into_iter()
                            .map(serde_json::Value::String)
                            .collect(),
                    ),
                );
            }
        }
        spiders
    };
    let browser_fetch_for_scrapy = |request: &rustspider::scrapy::Request,
                                    cfg: &ContractConfig|
     -> Result<rustspider::scrapy::Response, String> {
        let mut current_cfg = cfg.clone();
        if let Some(timeout) = request
            .meta
            .get("browser_timeout_seconds")
            .and_then(|value| value.as_u64())
        {
            current_cfg.browser.timeout_seconds = timeout;
        }
        if let Some(html_path) = request
            .meta
            .get("browser_html_path")
            .and_then(|value| value.as_str())
        {
            if !html_path.trim().is_empty() {
                current_cfg.browser.html_path = html_path.to_string();
            }
        }
        if let Some(screenshot_path) = request
            .meta
            .get("browser_screenshot_path")
            .and_then(|value| value.as_str())
        {
            if !screenshot_path.trim().is_empty() {
                current_cfg.browser.screenshot_path = screenshot_path.to_string();
            }
        }
        if let Some(browser_meta) = request
            .meta
            .get("browser")
            .and_then(|value| value.as_object())
        {
            if let Some(timeout) = browser_meta
                .get("timeout_seconds")
                .and_then(|value| value.as_u64())
            {
                current_cfg.browser.timeout_seconds = timeout;
            }
            if let Some(html_path) = browser_meta
                .get("html_path")
                .and_then(|value| value.as_str())
            {
                if !html_path.trim().is_empty() {
                    current_cfg.browser.html_path = html_path.to_string();
                }
            }
            if let Some(screenshot_path) = browser_meta
                .get("screenshot_path")
                .and_then(|value| value.as_str())
            {
                if !screenshot_path.trim().is_empty() {
                    current_cfg.browser.screenshot_path = screenshot_path.to_string();
                }
            }
            if let Some(storage_state_file) = browser_meta
                .get("storage_state_file")
                .and_then(|value| value.as_str())
            {
                if !storage_state_file.trim().is_empty() {
                    current_cfg.browser.storage_state_file = storage_state_file.to_string();
                }
            }
            if let Some(cookies_file) = browser_meta
                .get("cookies_file")
                .and_then(|value| value.as_str())
            {
                if !cookies_file.trim().is_empty() {
                    current_cfg.browser.cookies_file = cookies_file.to_string();
                }
            }
        }
        let html_path = if current_cfg.browser.html_path.trim().is_empty() {
            let temp = std::env::temp_dir().join("rustspider-scrapy-browser.html");
            temp.to_string_lossy().to_string()
        } else {
            current_cfg.browser.html_path.clone()
        };
        let preferred_engine = env::var("RUSTSPIDER_BROWSER_ENGINE")
            .unwrap_or_else(|_| "auto".to_string())
            .to_lowercase();
        let (title, resolved_url) = if matches!(
            preferred_engine.as_str(),
            "playwright" | "playwright-node" | "node-playwright" | "native-playwright"
        ) {
            run_native_playwright_fetch(
                &request.url,
                &current_cfg.browser.screenshot_path,
                &html_path,
                &current_cfg,
            )
            .or_else(|_| {
                run_playwright_fetch(
                    &request.url,
                    &current_cfg.browser.screenshot_path,
                    &html_path,
                    &current_cfg,
                )
            })?
        } else {
            run_playwright_fetch(
                &request.url,
                &current_cfg.browser.screenshot_path,
                &html_path,
                &current_cfg,
            )?
        };
        let text = fs::read_to_string(&html_path).map_err(|err| err.to_string())?;
        let mut headers = std::collections::BTreeMap::new();
        headers.insert("x-browser-runner".to_string(), "playwright".to_string());
        headers.insert("x-browser-title".to_string(), title);
        Ok(rustspider::scrapy::Response {
            url: resolved_url,
            status_code: 200,
            headers,
            text,
            request: Some(request.clone()),
        })
    };

    if subcommand == "shell" {
        let (html, source) = if !html_file.trim().is_empty() {
            match fs::read_to_string(&html_file) {
                Ok(html) => (html, html_file.clone()),
                Err(err) => {
                    eprintln!("failed to read html file: {err}");
                    return 1;
                }
            }
        } else if !url.trim().is_empty() {
            match reqwest::blocking::get(&url) {
                Ok(response) => match response.text() {
                    Ok(text) => (text, url.clone()),
                    Err(err) => {
                        eprintln!("failed to read response body: {err}");
                        return 1;
                    }
                },
                Err(err) => {
                    eprintln!("failed to fetch url: {err}");
                    return 1;
                }
            }
        } else {
            eprintln!("scrapy shell requires --url or --html-file");
            return 2;
        };

        let parser = HTMLParser::new(&html);
        let values = match mode.as_str() {
            "css" => parser.css(&expr),
            "css_attr" => parser.css_attr(&expr, &attr),
            "xpath" => parser.xpath_first(&expr).into_iter().collect(),
            "regex" => {
                let mut values = Vec::new();
                if let Ok(compiled) = regex::Regex::new(&expr) {
                    for capture in compiled.captures_iter(&html) {
                        if let Some(value) = capture.get(1).or_else(|| capture.get(0)) {
                            values.push(value.as_str().to_string());
                        }
                    }
                }
                values
            }
            _ => Vec::new(),
        };

        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "command": "scrapy shell",
                "runtime": "rust",
                "source": source,
                "type": mode,
                "expr": expr,
                "attr": attr,
                "count": values.len(),
                "values": values
            }))
            .unwrap_or_default()
        );
        return 0;
    }

    if subcommand == "profile" {
        let mut profile_runner = "http".to_string();
        let mut profile_runner_source = "default".to_string();
        let mut profile_url_source = "default".to_string();
        let (html, source) = if !project.trim().is_empty() {
            let manifest = match read_manifest(&project) {
                Ok(manifest) => manifest,
                Err(err) => {
                    eprintln!("{err}");
                    return 2;
                }
            };
            let project_cfg_path = PathBuf::from(&project).join("spider-framework.yaml");
            let project_cfg_path_string = project_cfg_path.to_string_lossy().to_string();
            let project_cfg = load_contract_config(Some(&project_cfg_path_string))
                .unwrap_or_else(|_| default_contract_config());
            if !selected_spider.trim().is_empty() {
                let spiders = resolve_spider_display(&project, &manifest, &project_cfg);
                let selected = spiders.iter().find(|spider| {
                    spider.get("name").and_then(|value| value.as_str())
                        == Some(selected_spider.as_str())
                });
                if let Some(selected) = selected {
                    if let Some(spider_url) = selected.get("url").and_then(|value| value.as_str()) {
                        if !spider_url.trim().is_empty() {
                            url = spider_url.to_string();
                        }
                    }
                    profile_runner = selected
                        .get("runner")
                        .and_then(|value| value.as_str())
                        .unwrap_or("http")
                        .to_string();
                    profile_runner_source = selected
                        .get("runner_source")
                        .and_then(|value| value.as_str())
                        .unwrap_or("default")
                        .to_string();
                    profile_url_source = selected
                        .get("url_source")
                        .and_then(|value| value.as_str())
                        .unwrap_or("default")
                        .to_string();
                } else {
                    eprintln!("unknown spider in {}: {}", project, selected_spider);
                    return 2;
                }
            } else if let Some(project_url) = manifest.get("url").and_then(|value| value.as_str()) {
                if !project_url.trim().is_empty() && url.trim() == "https://example.com" {
                    url = project_url.to_string();
                }
                let detail = resolve_scrapy_url_detail(
                    &project_cfg,
                    "",
                    &serde_json::Value::Null,
                    project_url,
                );
                profile_url_source = detail.1;
                let runner_detail =
                    resolve_scrapy_runner_detail(&project_cfg, "", &serde_json::Value::Null);
                profile_runner = runner_detail.0;
                profile_runner_source = runner_detail.1;
            }

            if !html_file.trim().is_empty() {
                match fs::read_to_string(&html_file) {
                    Ok(html) => (html, html_file.clone()),
                    Err(err) => {
                        eprintln!("failed to read html file: {err}");
                        return 1;
                    }
                }
            } else if !url.trim().is_empty() {
                match reqwest::blocking::get(&url) {
                    Ok(response) => match response.text() {
                        Ok(text) => (text, url.clone()),
                        Err(err) => {
                            eprintln!("failed to read response body: {err}");
                            return 1;
                        }
                    },
                    Err(err) => {
                        eprintln!("failed to fetch url: {err}");
                        return 1;
                    }
                }
            } else {
                eprintln!("scrapy profile requires --project, --url, or --html-file");
                return 2;
            }
        } else if !html_file.trim().is_empty() {
            match fs::read_to_string(&html_file) {
                Ok(html) => (html, html_file.clone()),
                Err(err) => {
                    eprintln!("failed to read html file: {err}");
                    return 1;
                }
            }
        } else if !url.trim().is_empty() {
            match reqwest::blocking::get(&url) {
                Ok(response) => match response.text() {
                    Ok(text) => (text, url.clone()),
                    Err(err) => {
                        eprintln!("failed to read response body: {err}");
                        return 1;
                    }
                },
                Err(err) => {
                    eprintln!("failed to fetch url: {err}");
                    return 1;
                }
            }
        } else {
            eprintln!("scrapy profile requires --project, --url, or --html-file");
            return 2;
        };
        let parser = HTMLParser::new(&html);
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "command": "scrapy profile",
                "runtime": "rust",
                "project": if project.trim().is_empty() { serde_json::Value::Null } else { serde_json::Value::String(project.clone()) },
                "spider": if selected_spider.trim().is_empty() { serde_json::Value::Null } else { serde_json::Value::String(selected_spider.clone()) },
                "source": source,
                "resolved_runner": profile_runner,
                "runner_source": if !html_file.trim().is_empty() { "html-fixture".to_string() } else { profile_runner_source },
                "resolved_url": url,
                "url_source": if !html_file.trim().is_empty() { "html-fixture".to_string() } else { profile_url_source },
                "title": parser.title().unwrap_or_default(),
                "link_count": parser.links().len(),
                "image_count": parser.images().len(),
                "text_length": parser.text().len(),
                "html_length": html.len(),
            }))
            .unwrap_or_default()
        );
        return 0;
    }

    if subcommand == "plan-ai" || subcommand == "sync-ai" {
        if subcommand == "sync-ai" && project.trim().is_empty() {
            eprintln!("scrapy sync-ai requires --project");
            return 2;
        }
        let (html, source) = if !project.trim().is_empty() {
            let manifest = match read_manifest(&project) {
                Ok(manifest) => manifest,
                Err(err) => {
                    eprintln!("{err}");
                    return 2;
                }
            };
            let project_cfg_path = PathBuf::from(&project).join("spider-framework.yaml");
            let project_cfg_path_string = project_cfg_path.to_string_lossy().to_string();
            let project_cfg = load_contract_config(Some(&project_cfg_path_string))
                .unwrap_or_else(|_| default_contract_config());
            if !selected_spider.trim().is_empty() {
                let spiders = resolve_spider_display(&project, &manifest, &project_cfg);
                let selected = spiders.iter().find(|spider| {
                    spider.get("name").and_then(|value| value.as_str())
                        == Some(selected_spider.as_str())
                });
                if let Some(selected) = selected {
                    if let Some(spider_url) = selected.get("url").and_then(|value| value.as_str()) {
                        if !spider_url.trim().is_empty() {
                            url = spider_url.to_string();
                        }
                    }
                } else {
                    eprintln!("unknown spider in {}: {}", project, selected_spider);
                    return 2;
                }
            } else if let Some(project_url) = manifest.get("url").and_then(|value| value.as_str()) {
                if !project_url.trim().is_empty() && url.trim() == "https://example.com" {
                    url = project_url.to_string();
                }
            }

            if !html_file.trim().is_empty() {
                match fs::read_to_string(&html_file) {
                    Ok(html) => (html, html_file.clone()),
                    Err(err) => {
                        eprintln!("failed to read html file: {err}");
                        return 1;
                    }
                }
            } else if !url.trim().is_empty() {
                match reqwest::blocking::get(&url) {
                    Ok(response) => match response.text() {
                        Ok(text) => (text, url.clone()),
                        Err(err) => {
                            eprintln!("failed to read response body: {err}");
                            return 1;
                        }
                    },
                    Err(err) => {
                        eprintln!("failed to fetch url: {err}");
                        return 1;
                    }
                }
            } else {
                eprintln!(
                    "scrapy {} requires --project, --url, or --html-file",
                    subcommand
                );
                return 2;
            }
        } else if !html_file.trim().is_empty() {
            match fs::read_to_string(&html_file) {
                Ok(html) => (html, html_file.clone()),
                Err(err) => {
                    eprintln!("failed to read html file: {err}");
                    return 1;
                }
            }
        } else if !url.trim().is_empty() {
            match reqwest::blocking::get(&url) {
                Ok(response) => match response.text() {
                    Ok(text) => (text, url.clone()),
                    Err(err) => {
                        eprintln!("failed to read response body: {err}");
                        return 1;
                    }
                },
                Err(err) => {
                    eprintln!("failed to fetch url: {err}");
                    return 1;
                }
            }
        } else {
            eprintln!(
                "scrapy {} requires --project, --url, or --html-file",
                subcommand
            );
            return 2;
        };
        let resolved_url = if !url.trim().is_empty() {
            url.clone()
        } else {
            format!("file://{}", html_file.replace('\\', "/"))
        };
        let profile = local_site_profile_payload(&resolved_url, &html);
        let candidate_fields = profile["candidate_fields"]
            .as_array()
            .cloned()
            .unwrap_or_default()
            .into_iter()
            .filter_map(|value| value.as_str().map(|item| item.to_string()))
            .collect::<Vec<_>>();
        let schema = schema_from_candidate_fields(&candidate_fields);
        let spider_plan_name = if spider_name.trim().is_empty() {
            "ai_spider".to_string()
        } else {
            spider_name.clone()
        };
        let blueprint =
            build_rust_ai_blueprint(&resolved_url, &spider_plan_name, &profile, &schema, &html);
        let mut payload = serde_json::json!({
            "command": format!("scrapy {}", subcommand),
            "runtime": "rust",
            "project": if project.trim().is_empty() { serde_json::Value::Null } else { serde_json::Value::String(project.clone()) },
            "spider": if selected_spider.trim().is_empty() { serde_json::Value::Null } else { serde_json::Value::String(selected_spider.clone()) },
            "spider_name": spider_plan_name,
            "source": source,
            "resolved_url": resolved_url,
            "recommended_runtime": profile["recommended_runtime"].clone(),
            "page_profile": profile,
            "schema": schema,
            "blueprint": blueprint,
            "suggested_commands": [
                format!(
                    "rustspider scrapy genspider --name {} --domain {} --project {} --ai",
                    spider_plan_name,
                    derive_domain_from_url_rust(&url),
                    if project.trim().is_empty() { "." } else { project.as_str() }
                ),
                format!(
                    "rustspider ai --url {} --instructions {:?} --schema-file ai-schema.json",
                    resolved_url,
                    "提取核心字段"
                )
            ],
            "written_files": []
        });
        let mut written_files = Vec::new();
        if !project.trim().is_empty() {
            let project_root = PathBuf::from(&project);
            let schema_path = project_root.join("ai-schema.json");
            let blueprint_path = project_root.join("ai-blueprint.json");
            let prompt_path = project_root.join("ai-extract-prompt.txt");
            let auth_path = project_root.join("ai-auth.json");
            let plan_path = if output.trim().is_empty()
                || output == "artifacts/exports/rustspider-scrapy-demo.json"
            {
                project_root.join("ai-plan.json")
            } else {
                PathBuf::from(&output)
            };
            let schema_text =
                serde_json::to_string_pretty(&payload["schema"]).unwrap_or_default() + "\n";
            let _ = fs::write(&schema_path, schema_text);
            let blueprint_text =
                serde_json::to_string_pretty(&payload["blueprint"]).unwrap_or_default() + "\n";
            let _ = fs::write(&blueprint_path, blueprint_text);
            let _ = fs::write(
                &prompt_path,
                payload["blueprint"]["extraction_prompt"]
                    .as_str()
                    .unwrap_or_default()
                    .to_string()
                    + "\n",
            );
            let _ = fs::write(
                &auth_path,
                serde_json::to_string_pretty(&serde_json::json!({
                    "headers": {},
                    "cookies": {},
                    "storage_state_file": "",
                    "cookies_file": "",
                    "session": "auth",
                    "actions": [],
                    "action_examples": default_auth_action_examples(),
                    "node_reverse_base_url": "http://localhost:3000",
                    "capture_reverse_profile": false,
                    "notes": "Fill session headers/cookies here when authentication is required."
                }))
                .unwrap_or_default()
                    + "\n",
            );
            written_files.push(schema_path.to_string_lossy().to_string());
            written_files.push(blueprint_path.to_string_lossy().to_string());
            written_files.push(prompt_path.to_string_lossy().to_string());
            written_files.push(auth_path.to_string_lossy().to_string());
            written_files.push(plan_path.to_string_lossy().to_string());
            payload["written_files"] = serde_json::json!(written_files);
            if subcommand == "sync-ai" {
                let ai_job_path = project_root.join("ai-job.json");
                let extract = schema["properties"]
                    .as_object()
                    .map(|props| {
                        props
                            .keys()
                            .map(|field| serde_json::json!({"field": field, "type": "ai"}))
                            .collect::<Vec<_>>()
                    })
                    .unwrap_or_default();
                let job_payload = serde_json::json!({
                    "name": format!("{}-ai-job", spider_plan_name),
                    "runtime": "ai",
                    "target": { "url": resolved_url },
                    "extract": extract,
                    "output": { "format": "json", "path": "artifacts/exports/ai-job-output.json" },
                    "metadata": { "schema_file": "ai-schema.json" }
                });
                let _ = fs::write(
                    &ai_job_path,
                    serde_json::to_string_pretty(&job_payload).unwrap_or_default() + "\n",
                );
                written_files.push(ai_job_path.to_string_lossy().to_string());
                payload["written_files"] = serde_json::json!(written_files);
            }
            let plan_text = serde_json::to_string_pretty(&payload).unwrap_or_default() + "\n";
            let _ = fs::write(&plan_path, plan_text);
        } else if !output.trim().is_empty() {
            let output_path = PathBuf::from(&output);
            if let Some(parent) = output_path.parent() {
                let _ = fs::create_dir_all(parent);
            }
            written_files.push(output_path.to_string_lossy().to_string());
            payload["written_files"] = serde_json::json!(written_files);
            let plan_text = serde_json::to_string_pretty(&payload).unwrap_or_default() + "\n";
            let _ = fs::write(&output_path, plan_text);
        }
        println!(
            "{}",
            serde_json::to_string_pretty(&payload).unwrap_or_default()
        );
        return 0;
    }

    if subcommand == "auth-validate" {
        if project.trim().is_empty() {
            eprintln!("scrapy auth-validate requires --project");
            return 2;
        }
        let manifest = match read_manifest(&project) {
            Ok(manifest) => manifest,
            Err(err) => {
                eprintln!("{err}");
                return 2;
            }
        };
        let project_cfg_path = PathBuf::from(&project).join("spider-framework.yaml");
        let project_cfg_path_string = project_cfg_path.to_string_lossy().to_string();
        let project_cfg = load_contract_config(Some(&project_cfg_path_string))
            .unwrap_or_else(|_| default_contract_config());
        if !selected_spider.trim().is_empty() {
            let spiders = resolve_spider_display(&project, &manifest, &project_cfg);
            let selected = spiders.iter().find(|spider| {
                spider.get("name").and_then(|value| value.as_str())
                    == Some(selected_spider.as_str())
            });
            if let Some(selected) = selected {
                if let Some(spider_url) = selected.get("url").and_then(|value| value.as_str()) {
                    if !spider_url.trim().is_empty() {
                        url = spider_url.to_string();
                    }
                }
            } else {
                eprintln!("unknown spider in {}: {}", project, selected_spider);
                return 2;
            }
        } else if let Some(project_url) = manifest.get("url").and_then(|value| value.as_str()) {
            if !project_url.trim().is_empty() && url.trim() == "https://example.com" {
                url = project_url.to_string();
            }
        }

        let assets =
            rustspider::scrapy::project::load_ai_project_assets(std::path::Path::new(&project));
        let (html, source, resolved_url, runner_used) = if !html_file.trim().is_empty() {
            match fs::read_to_string(&html_file) {
                Ok(html) => {
                    let resolved = if !url.trim().is_empty() {
                        url.clone()
                    } else {
                        format!("file://{}", html_file.replace('\\', "/"))
                    };
                    (html, html_file.clone(), resolved, "fixture".to_string())
                }
                Err(err) => {
                    eprintln!("failed to read html file: {err}");
                    return 1;
                }
            }
        } else if !url.trim().is_empty() {
            if assets.recommended_runner == "browser" {
                let mut browser_cfg = project_cfg.clone();
                browser_cfg.browser.storage_state_file = assets.storage_state_file.clone();
                browser_cfg.browser.cookies_file = assets.cookies_file.clone();
                let screenshot = browser_cfg.browser.screenshot_path.clone();
                let html_path = browser_cfg.browser.html_path.clone();
                match run_playwright_fetch(&url, &screenshot, &html_path, &browser_cfg) {
                    Ok((_, final_url)) => match fs::read_to_string(&html_path) {
                        Ok(text) => (text, url.clone(), final_url, "browser".to_string()),
                        Err(err) => {
                            eprintln!("failed to read browser html output: {err}");
                            return 1;
                        }
                    },
                    Err(err) => {
                        eprintln!("browser auth validate failed: {err}");
                        return 1;
                    }
                }
            } else {
                match reqwest::blocking::get(&url) {
                    Ok(response) => match response.text() {
                        Ok(text) => (text, url.clone(), url.clone(), "http".to_string()),
                        Err(err) => {
                            eprintln!("failed to read response body: {err}");
                            return 1;
                        }
                    },
                    Err(err) => {
                        eprintln!("failed to fetch url: {err}");
                        return 1;
                    }
                }
            }
        } else {
            eprintln!(
                "scrapy auth-validate requires --project plus --url, manifest url, or --html-file"
            );
            return 2;
        };
        let (authenticated, indicators) = auth_validation_status_rust(&html);
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "command": "scrapy auth-validate",
                "runtime": "rust",
                "project": project,
                "spider": if selected_spider.trim().is_empty() { serde_json::Value::Null } else { serde_json::Value::String(selected_spider.clone()) },
                "source": source,
                "resolved_url": resolved_url,
                "authentication_required": assets.auth_required,
                "recommended_runner": assets.recommended_runner,
                "runner_used": runner_used,
                "authenticated": authenticated,
                "indicators": indicators,
                "auth_assets": {
                    "has_headers": !assets.request_headers.is_empty(),
                    "storage_state_file": assets.storage_state_file,
                    "cookies_file": assets.cookies_file
                }
            }))
            .unwrap_or_default()
        );
        return 0;
    }

    if subcommand == "auth-capture" {
        if project.trim().is_empty() {
            eprintln!("scrapy auth-capture requires --project");
            return 2;
        }
        let manifest = match read_manifest(&project) {
            Ok(manifest) => manifest,
            Err(err) => {
                eprintln!("{err}");
                return 2;
            }
        };
        let project_cfg_path = PathBuf::from(&project).join("spider-framework.yaml");
        let project_cfg_path_string = project_cfg_path.to_string_lossy().to_string();
        let mut project_cfg = load_contract_config(Some(&project_cfg_path_string))
            .unwrap_or_else(|_| default_contract_config());
        if !selected_spider.trim().is_empty() {
            let spiders = resolve_spider_display(&project, &manifest, &project_cfg);
            let selected = spiders.iter().find(|spider| {
                spider.get("name").and_then(|value| value.as_str())
                    == Some(selected_spider.as_str())
            });
            if let Some(selected) = selected {
                if let Some(spider_url) = selected.get("url").and_then(|value| value.as_str()) {
                    if !spider_url.trim().is_empty() {
                        url = spider_url.to_string();
                    }
                }
            } else {
                eprintln!("unknown spider in {}: {}", project, selected_spider);
                return 2;
            }
        } else if let Some(project_url) = manifest.get("url").and_then(|value| value.as_str()) {
            if !project_url.trim().is_empty() && url.trim() == "https://example.com" {
                url = project_url.to_string();
            }
        }
        if !html_file.trim().is_empty() && url.trim().is_empty() {
            url = format!("file://{}", html_file.replace('\\', "/"));
        }
        if url.trim().is_empty() {
            eprintln!(
                "scrapy auth-capture requires --project plus --url, manifest url, or --html-file"
            );
            return 2;
        }
        let auth_dir = PathBuf::from(&project).join("artifacts").join("auth");
        let _ = fs::create_dir_all(&auth_dir);
        let state_path = auth_dir.join(format!("{}-state.json", session_name));
        let cookies_path = auth_dir.join(format!("{}-cookies.json", session_name));
        let auth_path = PathBuf::from(&project).join("ai-auth.json");
        project_cfg.browser.storage_state_file = state_path.to_string_lossy().to_string();
        project_cfg.browser.cookies_file = cookies_path.to_string_lossy().to_string();
        project_cfg.browser.auth_file = auth_path.to_string_lossy().to_string();
        let screenshot = project_cfg.browser.screenshot_path.clone();
        let html_path = project_cfg.browser.html_path.clone();
        let resolved_url = match run_playwright_fetch(&url, &screenshot, &html_path, &project_cfg) {
            Ok((_, final_url)) => final_url,
            Err(err) => {
                eprintln!("auth capture failed: {err}");
                return 1;
            }
        };
        let mut auth_payload = fs::read_to_string(&auth_path)
            .ok()
            .and_then(|raw| serde_json::from_str::<serde_json::Value>(&raw).ok())
            .unwrap_or_else(|| serde_json::json!({}));
        auth_payload["headers"] = serde_json::json!({});
        auth_payload["cookies"] = serde_json::json!({});
        auth_payload["storage_state_file"] =
            serde_json::json!(format!("artifacts/auth/{}-state.json", session_name));
        auth_payload["cookies_file"] =
            serde_json::json!(format!("artifacts/auth/{}-cookies.json", session_name));
        auth_payload["session"] = serde_json::json!(session_name);
        if auth_payload.get("actions").is_none() {
            auth_payload["actions"] = serde_json::json!([]);
        }
        if auth_payload.get("action_examples").is_none() {
            auth_payload["action_examples"] = default_auth_action_examples();
        }
        if auth_payload.get("node_reverse_base_url").is_none() {
            auth_payload["node_reverse_base_url"] = serde_json::json!("http://localhost:3000");
        }
        if auth_payload.get("capture_reverse_profile").is_none() {
            auth_payload["capture_reverse_profile"] = serde_json::json!(false);
        }
        if auth_payload["capture_reverse_profile"] == serde_json::json!(true) {
            if let Some(base_url) = auth_payload
                .get("node_reverse_base_url")
                .and_then(|v| v.as_str())
            {
                let summary = rustspider::scrapy::project::collect_reverse_summary(
                    base_url,
                    &url,
                    &project_cfg.browser.html_path,
                );
                if !summary.is_null() {
                    auth_payload["reverse_runtime"] = summary;
                }
            }
        }
        auth_payload["notes"] =
            serde_json::json!("Fill session headers/cookies here when authentication is required.");
        let _ = fs::write(
            &auth_path,
            serde_json::to_string_pretty(&auth_payload).unwrap_or_default() + "\n",
        );
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "command": "scrapy auth-capture",
                "runtime": "rust",
                "project": project,
                "spider": if selected_spider.trim().is_empty() { serde_json::Value::Null } else { serde_json::Value::String(selected_spider.clone()) },
                "session": session_name,
                "resolved_url": resolved_url,
                "written_files": [
                    auth_path.to_string_lossy().to_string(),
                    state_path.to_string_lossy().to_string(),
                    cookies_path.to_string_lossy().to_string()
                ]
            }))
            .unwrap_or_default()
        );
        return 0;
    }

    if subcommand == "scaffold-ai" {
        if project.trim().is_empty() {
            eprintln!("scrapy scaffold-ai requires --project");
            return 2;
        }
        let manifest = match read_manifest(&project) {
            Ok(manifest) => manifest,
            Err(err) => {
                eprintln!("{err}");
                return 2;
            }
        };
        let project_cfg_path = PathBuf::from(&project).join("spider-framework.yaml");
        let project_cfg_path_string = project_cfg_path.to_string_lossy().to_string();
        let project_cfg = load_contract_config(Some(&project_cfg_path_string))
            .unwrap_or_else(|_| default_contract_config());
        if !selected_spider.trim().is_empty() {
            let spiders = resolve_spider_display(&project, &manifest, &project_cfg);
            let selected = spiders.iter().find(|spider| {
                spider.get("name").and_then(|value| value.as_str())
                    == Some(selected_spider.as_str())
            });
            if let Some(selected) = selected {
                if let Some(spider_url) = selected.get("url").and_then(|value| value.as_str()) {
                    if !spider_url.trim().is_empty() {
                        url = spider_url.to_string();
                    }
                }
            } else {
                eprintln!("unknown spider in {}: {}", project, selected_spider);
                return 2;
            }
        } else if let Some(project_url) = manifest.get("url").and_then(|value| value.as_str()) {
            if !project_url.trim().is_empty() && url.trim() == "https://example.com" {
                url = project_url.to_string();
            }
        }

        let (html, source) = if !html_file.trim().is_empty() {
            match fs::read_to_string(&html_file) {
                Ok(html) => (html, html_file.clone()),
                Err(err) => {
                    eprintln!("failed to read html file: {err}");
                    return 1;
                }
            }
        } else if !url.trim().is_empty() {
            match reqwest::blocking::get(&url) {
                Ok(response) => match response.text() {
                    Ok(text) => (text, url.clone()),
                    Err(err) => {
                        eprintln!("failed to read response body: {err}");
                        return 1;
                    }
                },
                Err(err) => {
                    eprintln!("failed to fetch url: {err}");
                    return 1;
                }
            }
        } else {
            eprintln!(
                "scrapy scaffold-ai requires --project plus --url, manifest url, or --html-file"
            );
            return 2;
        };
        let resolved_url = if !url.trim().is_empty() {
            url.clone()
        } else {
            format!("file://{}", html_file.replace('\\', "/"))
        };
        let profile = local_site_profile_payload(&resolved_url, &html);
        let candidate_fields = profile["candidate_fields"]
            .as_array()
            .cloned()
            .unwrap_or_default()
            .into_iter()
            .filter_map(|value| value.as_str().map(|item| item.to_string()))
            .collect::<Vec<_>>();
        let schema = schema_from_candidate_fields(&candidate_fields);
        let planned_name = if spider_name.trim().is_empty() {
            "ai_spider".to_string()
        } else {
            spider_name.clone()
        };
        let blueprint =
            build_rust_ai_blueprint(&resolved_url, &planned_name, &profile, &schema, &html);
        let domain = derive_domain_from_url_rust(&resolved_url);
        let spider_path = PathBuf::from(&project)
            .join("src")
            .join("spiders")
            .join(format!("{planned_name}.rs"));
        if let Some(parent) = spider_path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        if let Err(err) = fs::write(
            &spider_path,
            render_rust_ai_spider_template(&planned_name, &domain),
        ) {
            eprintln!("failed to write ai spider template: {err}");
            return 1;
        }
        let schema_path = PathBuf::from(&project).join("ai-schema.json");
        let _ = fs::write(
            &schema_path,
            serde_json::to_string_pretty(&schema).unwrap_or_default() + "\n",
        );
        let blueprint_path = PathBuf::from(&project).join("ai-blueprint.json");
        let _ = fs::write(
            &blueprint_path,
            serde_json::to_string_pretty(&blueprint).unwrap_or_default() + "\n",
        );
        let prompt_path = PathBuf::from(&project).join("ai-extract-prompt.txt");
        let _ = fs::write(
            &prompt_path,
            blueprint["extraction_prompt"]
                .as_str()
                .unwrap_or_default()
                .to_string()
                + "\n",
        );
        let auth_path = PathBuf::from(&project).join("ai-auth.json");
        let _ = fs::write(
            &auth_path,
            serde_json::to_string_pretty(&serde_json::json!({
                "headers": {},
                "cookies": {},
                "storage_state_file": "",
                "cookies_file": "",
                "session": "auth",
                "actions": [],
                "action_examples": default_auth_action_examples(),
                "node_reverse_base_url": "http://localhost:3000",
                "capture_reverse_profile": false,
                "notes": "Fill session headers/cookies here when authentication is required."
            }))
            .unwrap_or_default()
                + "\n",
        );
        let plan_path = if output.trim().is_empty()
            || output == "artifacts/exports/rustspider-scrapy-demo.json"
        {
            PathBuf::from(&project).join("ai-plan.json")
        } else {
            PathBuf::from(&output)
        };
        let payload = serde_json::json!({
            "command": "scrapy scaffold-ai",
            "runtime": "rust",
            "project": project,
            "spider": if selected_spider.trim().is_empty() { serde_json::Value::Null } else { serde_json::Value::String(selected_spider.clone()) },
            "spider_name": planned_name,
            "source": source,
            "resolved_url": resolved_url,
            "recommended_runtime": profile["recommended_runtime"].clone(),
            "page_profile": profile,
            "schema": schema,
            "blueprint": blueprint,
            "written_files": [
                schema_path.to_string_lossy().to_string(),
                blueprint_path.to_string_lossy().to_string(),
                prompt_path.to_string_lossy().to_string(),
                auth_path.to_string_lossy().to_string(),
                plan_path.to_string_lossy().to_string(),
                spider_path.to_string_lossy().to_string()
            ],
            "suggested_commands": [
                format!("rustspider scrapy run --project {} --spider {}", project, planned_name),
                format!("rustspider ai --url {} --instructions {:?} --schema-file ai-schema.json", resolved_url, "提取核心字段")
            ]
        });
        let plan_text = serde_json::to_string_pretty(&payload).unwrap_or_default() + "\n";
        if let Some(parent) = plan_path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        let _ = fs::write(&plan_path, plan_text);
        println!(
            "{}",
            serde_json::to_string_pretty(&payload).unwrap_or_default()
        );
        return 0;
    }

    if subcommand == "doctor" {
        if project.trim().is_empty() {
            eprintln!("scrapy doctor requires --project");
            return 2;
        }
        let project_root = PathBuf::from(&project);
        let mut project_cfg_for_checks = default_contract_config();
        let manifest_path = project_root.join("scrapy-project.json");
        let mut checks = Vec::new();
        checks.push(serde_json::json!({
            "name": "manifest",
            "status": if manifest_path.exists() { "passed" } else { "failed" },
            "details": manifest_path.to_string_lossy()
        }));
        let manifest = read_manifest(&project);
        match manifest {
            Ok(manifest) => {
                checks.push(
                    serde_json::json!({"name": "runtime", "status": "passed", "details": "rust"}),
                );
                let project_cfg_path = project_root.join("spider-framework.yaml");
                let project_cfg_path_string = project_cfg_path.to_string_lossy().to_string();
                let project_cfg = load_contract_config(Some(&project_cfg_path_string))
                    .unwrap_or_else(|_| default_contract_config());
                project_cfg_for_checks = project_cfg.clone();
                let runner_path = manifest
                    .get("runner")
                    .and_then(|value| value.as_str())
                    .map(|value| project_root.join(value))
                    .filter(|value| !value.as_os_str().is_empty());
                checks.push(serde_json::json!({
                    "name": "runner_artifact",
                    "status": if runner_path.as_ref().map(|value| value.exists()).unwrap_or(false) { "passed" } else { "warning" },
                    "details": runner_path.map(|value| value.to_string_lossy().to_string()).unwrap_or_else(|| "project runner artifact not configured; built-in metadata runner will be used".to_string())
                }));
                let spiders = resolve_spider_display(&project, &manifest, &project_cfg);
                if spiders.is_empty() {
                    checks.push(serde_json::json!({"name": "spider_loader", "status": "warning", "details": "no spider files discovered"}));
                } else {
                    checks.push(serde_json::json!({"name": "spider_loader", "status": "passed", "details": format!("{} spiders discovered", spiders.len())}));
                    for spider in spiders {
                        checks.push(serde_json::json!({
                            "name": format!("spider:{}", spider.get("name").and_then(|value| value.as_str()).unwrap_or_default()),
                            "status": "passed",
                            "details": format!(
                                "{} runner={} runner_source={} url={} url_source={} pipelines={} spider_middlewares={} downloader_middlewares={}",
                                spider.get("path").and_then(|value| value.as_str()).unwrap_or_default(),
                                spider.get("runner").and_then(|value| value.as_str()).unwrap_or("http"),
                                spider.get("runner_source").and_then(|value| value.as_str()).unwrap_or("default"),
                                spider.get("url").and_then(|value| value.as_str()).unwrap_or_default(),
                                spider.get("url_source").and_then(|value| value.as_str()).unwrap_or("default"),
                                spider.get("pipelines").map(|value| value.to_string()).unwrap_or_default(),
                                spider.get("spider_middlewares").map(|value| value.to_string()).unwrap_or_default(),
                                spider.get("downloader_middlewares").map(|value| value.to_string()).unwrap_or_default()
                            )
                        }));
                    }
                }
            }
            Err(err) => checks
                .push(serde_json::json!({"name": "runtime", "status": "failed", "details": err})),
        }
        let config_path = project_root.join("spider-framework.yaml");
        checks.push(serde_json::json!({
            "name": "config",
            "status": if config_path.exists() { "passed" } else { "warning" },
            "details": config_path.to_string_lossy()
        }));
        append_rust_declarative_component_checks(&mut checks, &project_cfg_for_checks);
        let plugin_manifest_path = project_root.join("scrapy-plugins.json");
        let (plugin_manifest_status, plugin_manifest_details) = if plugin_manifest_path.exists() {
            match validate_scrapy_plugin_manifest(&plugin_manifest_path) {
                Ok(()) => ("passed", plugin_manifest_path.to_string_lossy().to_string()),
                Err(err) => ("failed", err),
            }
        } else {
            (
                "warning",
                plugin_manifest_path.to_string_lossy().to_string(),
            )
        };
        checks.push(serde_json::json!({
            "name": "plugin_manifest",
            "status": plugin_manifest_status,
            "details": plugin_manifest_details
        }));
        let exports_dir = project_root.join("artifacts").join("exports");
        checks.push(serde_json::json!({
            "name": "exports_dir",
            "status": if exports_dir.is_dir() { "passed" } else { "warning" },
            "details": exports_dir.to_string_lossy()
        }));
        let summary = if checks
            .iter()
            .any(|check| check.get("status").and_then(|value| value.as_str()) == Some("failed"))
        {
            "failed"
        } else if checks
            .iter()
            .any(|check| check.get("status").and_then(|value| value.as_str()) == Some("warning"))
        {
            "warning"
        } else {
            "passed"
        };
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "command": "scrapy doctor",
                "runtime": "rust",
                "project": project,
                "summary": summary,
                "checks": checks,
            }))
            .unwrap_or_default()
        );
        return if summary == "failed" { 1 } else { 0 };
    }

    if subcommand == "bench" {
        let mut fetch_ms = 0.0f64;
        let mut bench_runner = "http".to_string();
        let mut bench_runner_source = "default".to_string();
        let mut bench_url_source = "default".to_string();
        let (html, source) = if !project.trim().is_empty() {
            let manifest = match read_manifest(&project) {
                Ok(manifest) => manifest,
                Err(err) => {
                    eprintln!("{err}");
                    return 2;
                }
            };
            let project_cfg_path = PathBuf::from(&project).join("spider-framework.yaml");
            let project_cfg_path_string = project_cfg_path.to_string_lossy().to_string();
            let project_cfg = load_contract_config(Some(&project_cfg_path_string))
                .unwrap_or_else(|_| default_contract_config());
            if !selected_spider.trim().is_empty() {
                let spiders = resolve_spider_display(&project, &manifest, &project_cfg);
                let selected = spiders.iter().find(|spider| {
                    spider.get("name").and_then(|value| value.as_str())
                        == Some(selected_spider.as_str())
                });
                if let Some(selected) = selected {
                    if let Some(spider_url) = selected.get("url").and_then(|value| value.as_str()) {
                        if !spider_url.trim().is_empty() {
                            url = spider_url.to_string();
                        }
                    }
                    bench_runner = selected
                        .get("runner")
                        .and_then(|value| value.as_str())
                        .unwrap_or("http")
                        .to_string();
                    bench_runner_source = selected
                        .get("runner_source")
                        .and_then(|value| value.as_str())
                        .unwrap_or("default")
                        .to_string();
                    bench_url_source = selected
                        .get("url_source")
                        .and_then(|value| value.as_str())
                        .unwrap_or("default")
                        .to_string();
                } else {
                    eprintln!("unknown spider in {}: {}", project, selected_spider);
                    return 2;
                }
            } else if let Some(project_url) = manifest.get("url").and_then(|value| value.as_str()) {
                if !project_url.trim().is_empty() && url.trim() == "https://example.com" {
                    url = project_url.to_string();
                }
                let detail = resolve_scrapy_url_detail(
                    &project_cfg,
                    "",
                    &serde_json::Value::Null,
                    project_url,
                );
                bench_url_source = detail.1;
                let runner_detail =
                    resolve_scrapy_runner_detail(&project_cfg, "", &serde_json::Value::Null);
                bench_runner = runner_detail.0;
                bench_runner_source = runner_detail.1;
            }

            if !html_file.trim().is_empty() {
                match fs::read_to_string(&html_file) {
                    Ok(html) => (html, html_file.clone()),
                    Err(err) => {
                        eprintln!("failed to read html file: {err}");
                        return 1;
                    }
                }
            } else if !url.trim().is_empty() {
                let started = std::time::Instant::now();
                match reqwest::blocking::get(&url) {
                    Ok(response) => match response.text() {
                        Ok(text) => {
                            fetch_ms = started.elapsed().as_secs_f64() * 1000.0;
                            (text, url.clone())
                        }
                        Err(err) => {
                            eprintln!("failed to read response body: {err}");
                            return 1;
                        }
                    },
                    Err(err) => {
                        eprintln!("failed to fetch url: {err}");
                        return 1;
                    }
                }
            } else {
                eprintln!("scrapy bench requires --project, --url, or --html-file");
                return 2;
            }
        } else if !html_file.trim().is_empty() {
            match fs::read_to_string(&html_file) {
                Ok(html) => (html, html_file.clone()),
                Err(err) => {
                    eprintln!("failed to read html file: {err}");
                    return 1;
                }
            }
        } else if !url.trim().is_empty() {
            let started = std::time::Instant::now();
            match reqwest::blocking::get(&url) {
                Ok(response) => match response.text() {
                    Ok(text) => {
                        fetch_ms = started.elapsed().as_secs_f64() * 1000.0;
                        (text, url.clone())
                    }
                    Err(err) => {
                        eprintln!("failed to read response body: {err}");
                        return 1;
                    }
                },
                Err(err) => {
                    eprintln!("failed to fetch url: {err}");
                    return 1;
                }
            }
        } else {
            eprintln!("scrapy bench requires --project, --url, or --html-file");
            return 2;
        };

        let started = std::time::Instant::now();
        let parser = HTMLParser::new(&html);
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "command": "scrapy bench",
                "runtime": "rust",
                "project": if project.trim().is_empty() { serde_json::Value::Null } else { serde_json::Value::String(project.clone()) },
                "spider": if selected_spider.trim().is_empty() { serde_json::Value::Null } else { serde_json::Value::String(selected_spider.clone()) },
                "source": source,
                "resolved_runner": bench_runner,
                "runner_source": if !html_file.trim().is_empty() { "html-fixture".to_string() } else { bench_runner_source },
                "resolved_url": url,
                "url_source": if !html_file.trim().is_empty() { "html-fixture".to_string() } else { bench_url_source },
                "elapsed_ms": started.elapsed().as_secs_f64() * 1000.0,
                "fetch_ms": fetch_ms,
                "title": parser.title().unwrap_or_default(),
                "link_count": parser.links().len(),
                "image_count": parser.images().len(),
                "text_length": parser.text().len(),
                "html_length": html.len(),
            }))
            .unwrap_or_default()
        );
        return 0;
    }

    if subcommand == "export" {
        if project.trim().is_empty() {
            eprintln!("scrapy export requires --project");
            return 2;
        }
        let manifest = match read_manifest(&project) {
            Ok(manifest) => manifest,
            Err(err) => {
                eprintln!("{err}");
                return 2;
            }
        };
        let project_cfg_path = PathBuf::from(&project).join("spider-framework.yaml");
        let project_cfg_path_string = project_cfg_path.to_string_lossy().to_string();
        let project_cfg = load_contract_config(Some(&project_cfg_path_string))
            .unwrap_or_else(|_| default_contract_config());
        if !selected_spider.trim().is_empty() {
            let spiders = resolve_spider_display(&project, &manifest, &project_cfg);
            if spiders.iter().all(|spider| {
                spider.get("name").and_then(|value| value.as_str())
                    != Some(selected_spider.as_str())
            }) {
                eprintln!("unknown spider in {}: {}", project, selected_spider);
                return 2;
            }
        }
        let input_path = resolve_project_output(&project, &manifest, &selected_spider);
        let raw = match fs::read_to_string(&input_path) {
            Ok(raw) => raw,
            Err(err) => {
                eprintln!("missing scrapy project output: {err}");
                return 2;
            }
        };
        let value: serde_json::Value = match serde_json::from_str(&raw) {
            Ok(value) => value,
            Err(err) => {
                eprintln!("invalid scrapy project output: {err}");
                return 1;
            }
        };
        let items = value.as_array().cloned().unwrap_or_default();
        let records = items
            .into_iter()
            .map(|item| rustspider::ExportData {
                title: item
                    .get("title")
                    .and_then(|v| v.as_str())
                    .unwrap_or_default()
                    .to_string(),
                url: item
                    .get("url")
                    .and_then(|v| v.as_str())
                    .unwrap_or_default()
                    .to_string(),
                snippet: item
                    .get("snippet")
                    .and_then(|v| v.as_str())
                    .unwrap_or_default()
                    .to_string(),
                source: item
                    .get("source")
                    .and_then(|v| v.as_str())
                    .unwrap_or_default()
                    .to_string(),
                time: item
                    .get("time")
                    .and_then(|v| v.as_str())
                    .unwrap_or_default()
                    .to_string(),
            })
            .collect::<Vec<_>>();
        let output_path = if output == "artifacts/exports/rustspider-scrapy-demo.json" {
            input_path.with_extension(&export_format)
        } else {
            PathBuf::from(&output)
        };
        let export_dir = output_path
            .parent()
            .unwrap_or(PathBuf::from(".").as_path())
            .to_path_buf();
        let filename = output_path
            .file_name()
            .and_then(|value| value.to_str())
            .unwrap_or("export.json");
        let exporter = rustspider::Exporter::new(export_dir.to_string_lossy().as_ref());
        let result = match export_format.as_str() {
            "json" => exporter.export_json(&records, filename),
            "jsonl" => exporter.export_jsonl(&records, filename),
            "csv" => exporter.export_csv(&records, filename),
            "md" => exporter.export_markdown(&records, filename),
            other => Err(format!("unsupported scrapy export format: {other}")),
        };
        if let Err(err) = result {
            eprintln!("scrapy export failed: {err}");
            return 1;
        }
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "command": "scrapy export",
                "runtime": "rust",
                "project": project,
                "spider": if selected_spider.trim().is_empty() { serde_json::Value::Null } else { serde_json::Value::String(selected_spider.clone()) },
                "input": input_path.to_string_lossy(),
                "output": output_path.to_string_lossy(),
                "format": export_format,
            }))
            .unwrap_or_default()
        );
        return 0;
    }

    if subcommand == "list" {
        if project.trim().is_empty() {
            eprintln!("scrapy list requires --project");
            return 2;
        }
        let manifest = match read_manifest(&project) {
            Ok(manifest) => manifest,
            Err(err) => {
                eprintln!("{err}");
                return 2;
            }
        };
        let project_cfg_path = PathBuf::from(&project).join("spider-framework.yaml");
        let project_cfg_path_string = project_cfg_path.to_string_lossy().to_string();
        let project_cfg = load_contract_config(Some(&project_cfg_path_string))
            .unwrap_or_else(|_| default_contract_config());
        let spiders = resolve_spider_display(&project, &manifest, &project_cfg);
        let mut plugin_specs = rustspider::scrapy::project::load_plugin_specs_from_manifest(
            PathBuf::from(&project).as_path(),
        );
        if plugin_specs.is_empty() {
            plugin_specs = project_cfg
                .scrapy
                .plugins
                .iter()
                .map(|name| rustspider::scrapy::project::PluginSpec {
                    name: name.trim().to_string(),
                    enabled: true,
                    priority: 0,
                    config: BTreeMap::new(),
                })
                .collect();
        }
        let plugin_names = if plugin_specs.is_empty() {
            rustspider::scrapy::project::plugin_names()
        } else {
            plugin_specs
                .iter()
                .filter(|spec| spec.enabled && !spec.name.trim().is_empty())
                .map(|spec| spec.name.clone())
                .collect::<Vec<_>>()
        };
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "command": "scrapy list",
                "runtime": "rust",
                "project": project,
                "spiders": spiders,
                "plugins": plugin_names,
                "pipelines": merge_unique_json_string_values(&project_cfg.scrapy.pipelines, &spiders, "pipelines"),
                "spider_middlewares": merge_unique_json_string_values(&project_cfg.scrapy.spider_middlewares, &spiders, "spider_middlewares"),
                "downloader_middlewares": merge_unique_json_string_values(&project_cfg.scrapy.downloader_middlewares, &spiders, "downloader_middlewares"),
            }))
            .unwrap_or_default()
        );
        return 0;
    }

    if subcommand == "validate" {
        if project.trim().is_empty() {
            eprintln!("scrapy validate requires --project");
            return 2;
        }
        let project_root = PathBuf::from(&project);
        let mut project_cfg_for_checks = default_contract_config();
        let manifest_path = project_root.join("scrapy-project.json");
        let mut checks = Vec::new();
        checks.push(serde_json::json!({
            "name": "manifest",
            "status": if manifest_path.exists() { "passed" } else { "failed" },
            "details": manifest_path.to_string_lossy()
        }));
        let manifest = read_manifest(&project);
        match manifest {
            Ok(manifest) => {
                checks.push(
                    serde_json::json!({"name": "runtime", "status": "passed", "details": "rust"}),
                );
                let project_cfg_path = project_root.join("spider-framework.yaml");
                let project_cfg_path_string = project_cfg_path.to_string_lossy().to_string();
                let project_cfg = load_contract_config(Some(&project_cfg_path_string))
                    .unwrap_or_else(|_| default_contract_config());
                project_cfg_for_checks = project_cfg.clone();
                let entry = manifest
                    .get("entry")
                    .and_then(|value| value.as_str())
                    .unwrap_or("src/main.rs");
                let entry_path = project_root.join(entry);
                checks.push(serde_json::json!({
                    "name": "entry",
                    "status": if entry_path.exists() { "passed" } else { "failed" },
                    "details": entry_path.to_string_lossy()
                }));
                let runner_path = manifest
                    .get("runner")
                    .and_then(|value| value.as_str())
                    .map(|value| project_root.join(value))
                    .filter(|value| !value.as_os_str().is_empty());
                checks.push(serde_json::json!({
                    "name": "runner_artifact",
                    "status": if runner_path.as_ref().map(|value| value.exists()).unwrap_or(false) { "passed" } else { "warning" },
                    "details": runner_path.map(|value| value.to_string_lossy().to_string()).unwrap_or_else(|| "project runner artifact not configured; built-in metadata runner will be used".to_string())
                }));
                for spider in resolve_spider_display(&project, &manifest, &project_cfg) {
                    checks.push(serde_json::json!({
                        "name": format!("spider:{}", spider.get("name").and_then(|value| value.as_str()).unwrap_or_default()),
                        "status": "passed",
                        "details": format!(
                            "{} runner={} runner_source={} url={} url_source={} pipelines={} spider_middlewares={} downloader_middlewares={}",
                            spider.get("path").and_then(|value| value.as_str()).unwrap_or_default(),
                            spider.get("runner").and_then(|value| value.as_str()).unwrap_or("http"),
                            spider.get("runner_source").and_then(|value| value.as_str()).unwrap_or("default"),
                            spider.get("url").and_then(|value| value.as_str()).unwrap_or_default(),
                            spider.get("url_source").and_then(|value| value.as_str()).unwrap_or("default"),
                            spider.get("pipelines").map(|value| value.to_string()).unwrap_or_default(),
                            spider.get("spider_middlewares").map(|value| value.to_string()).unwrap_or_default(),
                            spider.get("downloader_middlewares").map(|value| value.to_string()).unwrap_or_default()
                        )
                    }));
                }
            }
            Err(err) => checks
                .push(serde_json::json!({"name": "runtime", "status": "failed", "details": err})),
        }
        let config_path = project_root.join("spider-framework.yaml");
        checks.push(serde_json::json!({
            "name": "config",
            "status": if config_path.exists() { "passed" } else { "warning" },
            "details": config_path.to_string_lossy()
        }));
        append_rust_declarative_component_checks(&mut checks, &project_cfg_for_checks);
        let plugin_manifest_path = project_root.join("scrapy-plugins.json");
        let (plugin_manifest_status, plugin_manifest_details) = if plugin_manifest_path.exists() {
            match validate_scrapy_plugin_manifest(&plugin_manifest_path) {
                Ok(()) => ("passed", plugin_manifest_path.to_string_lossy().to_string()),
                Err(err) => ("failed", err),
            }
        } else {
            (
                "warning",
                plugin_manifest_path.to_string_lossy().to_string(),
            )
        };
        checks.push(serde_json::json!({
            "name": "plugin_manifest",
            "status": plugin_manifest_status,
            "details": plugin_manifest_details
        }));
        let summary = if checks
            .iter()
            .any(|check| check.get("status").and_then(|value| value.as_str()) == Some("failed"))
        {
            "failed"
        } else {
            "passed"
        };
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "command": "scrapy validate",
                "runtime": "rust",
                "project": project,
                "summary": summary,
                "checks": checks
            }))
            .unwrap_or_default()
        );
        return if summary == "passed" { 0 } else { 1 };
    }

    if subcommand == "genspider" {
        if project.trim().is_empty() {
            eprintln!("scrapy genspider requires --project");
            return 2;
        }
        if spider_name.trim().is_empty() || spider_domain.trim().is_empty() {
            eprintln!("scrapy genspider requires --name and --domain");
            return 2;
        }
        if let Err(err) = read_manifest(&project) {
            eprintln!("{err}");
            return 2;
        }
        let spiders_dir = PathBuf::from(&project).join("src").join("spiders");
        if let Err(err) = fs::create_dir_all(&spiders_dir) {
            eprintln!("failed to create spiders dir: {err}");
            return 1;
        }
        let target = spiders_dir.join(format!("{spider_name}.rs"));
        let content = if ai_template {
            render_rust_ai_spider_template(&spider_name, &spider_domain)
        } else {
            format!(
                "// scrapy: url=https://{domain}\n// Generated spider template for {domain}\n",
                domain = spider_domain
            )
        };
        if let Err(err) = fs::write(&target, content) {
            eprintln!("failed to write spider template: {err}");
            return 1;
        }
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "command": "scrapy genspider",
                "runtime": "rust",
                "project": project,
                "spider": spider_name,
                "path": target.to_string_lossy(),
                "template": if ai_template { "ai" } else { "standard" }
            }))
            .unwrap_or_default()
        );
        return 0;
    }

    if subcommand == "init" {
        if init_path.trim().is_empty() {
            eprintln!("scrapy init requires --path");
            return 2;
        }
        let project_root = PathBuf::from(&init_path);
        if let Err(err) = fs::create_dir_all(&project_root) {
            eprintln!("failed to create project directory: {err}");
            return 1;
        }
        let mut cfg = default_contract_config();
        cfg.project.name = project_root
            .file_name()
            .and_then(|value| value.to_str())
            .unwrap_or("rustspider-project")
            .to_string();
        let manifest = serde_json::json!({
            "name": cfg.project.name,
            "runtime": "rust",
            "entry": "src/main.rs",
            "runner": "dist/rustspider-project",
            "url": "https://example.com",
            "output": "artifacts/exports/items.json",
        });
        let files = vec![
            ("scrapy-project.json", serde_json::to_string_pretty(&manifest).unwrap_or_default() + "\n"),
            ("Cargo.toml", "[package]\nname = \"rustspider-project\"\nversion = \"0.1.0\"\nedition = \"2021\"\n\n[dependencies]\nrustspider = \"1.0.0\"\n".to_string()),
            ("src/main.rs", "mod plugins;\nmod spiders;\n\nuse rustspider::scrapy::{CrawlerProcess, FeedExporter};\nuse rustspider::scrapy::project as projectruntime;\n\nfn main() -> Result<(), String> {\n    spiders::register();\n    plugins::register();\n    if projectruntime::run_from_env()? {\n        return Ok(());\n    }\n    let spider = projectruntime::resolve_spider(\"\")?;\n    let plugins = projectruntime::resolve_plugins(&[])?;\n    let mut process = CrawlerProcess::new(spider);\n    for plugin in plugins {\n        process = process.with_plugin(plugin);\n    }\n    let items = process.run()?;\n    let mut exporter = FeedExporter::new(\"json\", \"artifacts/exports/items.json\");\n    for item in items { exporter.export_item(item); }\n    exporter.close()?;\n    Ok(())\n}\n".to_string()),
            ("src/spiders/mod.rs", "pub mod demo;\n\npub fn register() {\n    demo::register();\n}\n".to_string()),
            ("src/spiders/demo.rs", "// scrapy: url=https://example.com\nuse std::sync::Arc;\n\nuse rustspider::scrapy::{Item, Output, Response, Spider};\nuse rustspider::scrapy::project as projectruntime;\n\npub fn make_demo_spider() -> Spider {\n    Spider::new(\n        \"demo\",\n        Arc::new(|response: &Response| {\n            vec![Output::Item(Item::new().set(\"title\", response.css(\"title\").get().unwrap_or_default()).set(\"url\", response.url.clone()).set(\"framework\", \"rustspider\"))]\n        }),\n    )\n    .add_start_url(\"https://example.com\")\n}\n\npub fn register() {\n    projectruntime::register_spider(\"demo\", make_demo_spider);\n}\n".to_string()),
            ("src/plugins/mod.rs", "pub mod default;\n\npub fn register() {\n    default::register();\n}\n".to_string()),
            ("src/plugins/default.rs", "use std::sync::Arc;\n\nuse rustspider::scrapy::{Item, PluginHandle, ScrapyPlugin, Spider};\nuse rustspider::scrapy::project as projectruntime;\n\npub struct ProjectPlugin;\n\nimpl ScrapyPlugin for ProjectPlugin {\n    fn process_item(&self, item: Item, _spider: &Spider) -> Result<Item, String> {\n        Ok(item)\n    }\n}\n\npub fn make_project_plugin() -> PluginHandle {\n    Arc::new(ProjectPlugin)\n}\n\npub fn register() {\n    projectruntime::register_plugin(\"project-plugin\", make_project_plugin);\n}\n".to_string()),
            ("scrapy-plugins.json", "{\n  \"plugins\": [\n    {\n      \"name\": \"field-injector\",\n      \"priority\": 10,\n      \"config\": {\n        \"fields\": {\n          \"plugin\": \"project-plugin\"\n        }\n      }\n    }\n  ]\n}\n".to_string()),
            ("run-scrapy.sh", "#!/usr/bin/env bash\nset -euo pipefail\n\nrustspider scrapy run --project .\n".to_string()),
            ("run-scrapy.ps1", "rustspider scrapy run --project .\n".to_string()),
            ("README.md", format!("# {}\n\n## Quick Start\n\n```bash\nrustspider scrapy run --project .\nrustspider scrapy run --project . --spider demo\ncargo build --release\ncp target/release/rustspider-project dist/rustspider-project\n```\n\n`scrapy run --project` 会优先执行 `scrapy-project.json` 里配置的 project runner artifact；如果 artifact 尚未构建，会回退到 built-in metadata runner。\n\n## AI Starter\n\n```bash\nrustspider ai --url https://example.com --instructions \"提取标题和摘要\" --schema-file ai-schema.json\nrustspider job --file ai-job.json\n```\n\n## Plugin SDK\n\n`src/plugins/` 中的注册型插件用于 project runner artifact，`scrapy-plugins.json` 用于 built-in metadata runner 和内置插件。\n", cfg.project.name)),
            ("ai-schema.json", "{\n  \"type\": \"object\",\n  \"properties\": {\n    \"title\": { \"type\": \"string\" },\n    \"summary\": { \"type\": \"string\" },\n    \"url\": { \"type\": \"string\" }\n  }\n}\n".to_string()),
            ("ai-job.json", "{\n  \"name\": \"rustspider-ai-job\",\n  \"runtime\": \"ai\",\n  \"target\": { \"url\": \"https://example.com\" },\n  \"extract\": [\n    { \"field\": \"title\", \"type\": \"ai\" },\n    { \"field\": \"summary\", \"type\": \"ai\" },\n    { \"field\": \"url\", \"type\": \"ai\" }\n  ],\n  \"output\": { \"format\": \"json\", \"path\": \"artifacts/exports/ai-job-output.json\" },\n  \"metadata\": { \"content\": \"<title>Demo</title>\", \"schema_file\": \"ai-schema.json\" }\n}\n".to_string()),
            ("job.json", "{\n  \"name\": \"rustspider-job\",\n  \"runtime\": \"http\",\n  \"target\": { \"url\": \"https://example.com\" },\n  \"output\": { \"format\": \"json\", \"path\": \"artifacts/exports/job-output.json\" }\n}\n".to_string()),
            ("spider-framework.yaml", serde_yaml::to_string(&cfg).unwrap_or_default()),
        ];
        for (relative, content) in files {
            let path = project_root.join(relative);
            if let Some(parent) = path.parent() {
                if let Err(err) = fs::create_dir_all(parent) {
                    eprintln!("failed to prepare {}: {err}", path.display());
                    return 1;
                }
            }
            if let Err(err) = fs::write(&path, content) {
                eprintln!("failed to write {}: {err}", path.display());
                return 1;
            }
        }
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "command": "scrapy init",
                "runtime": "rust",
                "project": project_root.to_string_lossy()
            }))
            .unwrap_or_default()
        );
        return 0;
    }

    let mut project_cfg = None;
    let mut runner_source = "default".to_string();
    let mut url_source = "default".to_string();
    if subcommand == "run" {
        if project.trim().is_empty() {
            eprintln!("scrapy run requires --project");
            return 2;
        }
        let manifest_path = PathBuf::from(&project).join("scrapy-project.json");
        let manifest_raw = match fs::read_to_string(&manifest_path) {
            Ok(raw) => raw,
            Err(err) => {
                eprintln!("failed to read scrapy project manifest: {err}");
                return 2;
            }
        };
        let manifest: serde_json::Value = match serde_json::from_str(&manifest_raw) {
            Ok(value) => value,
            Err(err) => {
                eprintln!("invalid scrapy project manifest: {err}");
                return 2;
            }
        };
        if manifest.get("runtime").and_then(|value| value.as_str()) != Some("rust") {
            eprintln!(
                "runtime mismatch in {}: expected rust",
                manifest_path.display()
            );
            return 2;
        }
        let mut selected_metadata = None;
        let project_cfg_path = PathBuf::from(&project).join("spider-framework.yaml");
        let project_cfg_path_string = project_cfg_path.to_string_lossy().to_string();
        let resolved_project_cfg = load_contract_config(Some(&project_cfg_path_string))
            .unwrap_or_else(|_| default_contract_config());
        if !selected_spider.trim().is_empty() {
            let spiders = resolve_spider_display(&project, &manifest, &resolved_project_cfg);
            selected_metadata = spiders.into_iter().find(|spider| {
                spider.get("name").and_then(|value| value.as_str())
                    == Some(selected_spider.as_str())
            });
            if selected_metadata.is_none() {
                eprintln!("unknown spider in {}: {}", project, selected_spider);
                return 2;
            }
        }
        let url_detail = resolve_scrapy_url_detail(
            &resolved_project_cfg,
            &selected_spider,
            selected_metadata
                .as_ref()
                .unwrap_or(&serde_json::Value::Null),
            manifest
                .get("url")
                .and_then(|value| value.as_str())
                .unwrap_or_default(),
        );
        url = url_detail.0;
        url_source = url_detail.1;
        if output == "artifacts/exports/rustspider-scrapy-demo.json" {
            output = resolve_project_output(&project, &manifest, &selected_spider)
                .to_string_lossy()
                .to_string();
        }
        project_cfg = Some(resolved_project_cfg.clone());
        let selected_runner_detail = project_cfg
            .as_ref()
            .map(|cfg| {
                resolve_scrapy_runner_detail(
                    cfg,
                    &selected_spider,
                    selected_metadata
                        .as_ref()
                        .unwrap_or(&serde_json::Value::Null),
                )
            })
            .unwrap_or_else(|| ("http".to_string(), "default".to_string()));
        let selected_runner = selected_runner_detail.0;
        runner_source = selected_runner_detail.1;
        if selected_runner == "http" {
            if let Some(runner) = manifest.get("runner").and_then(|value| value.as_str()) {
                let runner_path = PathBuf::from(&project).join(runner);
                if runner_path.exists() {
                    let mut command = Command::new(&runner_path);
                    command.current_dir(&project);
                    command.env("RUSTSPIDER_SCRAPY_RUNNER", "1");
                    command.env("RUSTSPIDER_SCRAPY_PROJECT", &project);
                    command.env("RUSTSPIDER_SCRAPY_URL", &url);
                    command.env("RUSTSPIDER_SCRAPY_OUTPUT", &output);
                    if let Some(cfg) = &project_cfg {
                        if cfg.node_reverse.enabled && !cfg.node_reverse.base_url.trim().is_empty()
                        {
                            command
                                .env("RUSTSPIDER_SCRAPY_REVERSE_URL", &cfg.node_reverse.base_url);
                        }
                    }
                    if !selected_spider.trim().is_empty() {
                        command.env("RUSTSPIDER_SCRAPY_SPIDER", &selected_spider);
                    }
                    if !html_file.trim().is_empty() {
                        command.env("RUSTSPIDER_SCRAPY_HTML_FILE", &html_file);
                    }
                    let status = match command.status() {
                        Ok(status) => status,
                        Err(err) => {
                            eprintln!("failed to execute scrapy project artifact: {err}");
                            return 1;
                        }
                    };
                    return status.code().unwrap_or(1);
                }
            }
        }
    }

    let callback = std::sync::Arc::new(|response: &ScrapyResponse| {
        vec![ScrapyOutput::Item(
            ScrapyItem::new()
                .set("title", response.css("title").get().unwrap_or_default())
                .set("url", response.url.clone())
                .set("framework", "rustspider"),
        )]
    });

    let plugin_specs = if !project.trim().is_empty() {
        let mut specs = rustspider::scrapy::project::load_plugin_specs_from_manifest(
            PathBuf::from(&project).as_path(),
        );
        if specs.is_empty() {
            if let Some(cfg) = &project_cfg {
                specs = cfg
                    .scrapy
                    .plugins
                    .iter()
                    .map(|name| rustspider::scrapy::project::PluginSpec {
                        name: name.trim().to_string(),
                        enabled: true,
                        priority: 0,
                        config: BTreeMap::new(),
                    })
                    .collect();
            }
        }
        specs
    } else {
        Vec::new()
    };
    let resolved_plugin_names = if plugin_specs.is_empty() {
        rustspider::scrapy::project::plugin_names()
    } else {
        plugin_specs
            .iter()
            .filter(|spec| spec.enabled && !spec.name.trim().is_empty())
            .map(|spec| spec.name.clone())
            .collect::<Vec<_>>()
    };
    let plugins = match rustspider::scrapy::project::resolve_plugin_specs(&plugin_specs) {
        Ok(plugins) => plugins,
        Err(err) => {
            eprintln!("failed to resolve scrapy project plugins: {err}");
            return 1;
        }
    };
    let declarative_pipeline_count = project_cfg
        .as_ref()
        .map(|cfg| build_declarative_scrapy_pipelines(cfg, &selected_spider).len())
        .unwrap_or(0);
    let declarative_spider_middleware_count = project_cfg
        .as_ref()
        .map(|cfg| build_declarative_scrapy_spider_middlewares(cfg, &selected_spider).len())
        .unwrap_or(0);
    let declarative_downloader_middleware_count = project_cfg
        .as_ref()
        .map(|cfg| build_declarative_scrapy_downloader_middlewares(cfg, &selected_spider).len())
        .unwrap_or(0);
    let pipeline_count = declarative_pipeline_count
        + plugins
            .iter()
            .map(|plugin| plugin.provide_pipelines().len())
            .sum::<usize>();
    let spider_middleware_count = declarative_spider_middleware_count
        + plugins
            .iter()
            .map(|plugin| plugin.provide_spider_middlewares().len())
            .sum::<usize>();
    let downloader_middleware_count = declarative_downloader_middleware_count
        + plugins
            .iter()
            .map(|plugin| plugin.provide_downloader_middlewares().len())
            .sum::<usize>();
    let mut config = std::collections::BTreeMap::new();
    if let Some(cfg) = &project_cfg {
        config.insert(
            "runner".to_string(),
            serde_json::Value::String(resolve_scrapy_runner(
                cfg,
                &selected_spider,
                &serde_json::Value::Null,
            )),
        );
    }
    if !html_file.trim().is_empty() {
        config.insert(
            "runner".to_string(),
            serde_json::Value::String("browser".to_string()),
        );
    }
    let spider = ScrapySpider::new("rustspider-scrapy-demo", callback).add_start_url(url.clone());
    let mut process = rustspider::scrapy::CrawlerProcess::new(spider).with_config(config);
    if !html_file.trim().is_empty() {
        let html_fixture = html_file.clone();
        process = process.with_browser_fetcher(Arc::new(move |request, _spider| {
            let text = fs::read_to_string(&html_fixture).map_err(|err| err.to_string())?;
            Ok(rustspider::scrapy::Response {
                url: request.url.clone(),
                status_code: 200,
                headers: Default::default(),
                text,
                request: Some(request.clone()),
            })
        }));
    }
    if let Some(cfg) = project_cfg.clone() {
        let runner = resolve_scrapy_runner(&cfg, &selected_spider, &serde_json::Value::Null);
        if matches!(runner.as_str(), "browser" | "hybrid") {
            process = process.with_browser_fetcher(Arc::new(move |request, _spider| {
                browser_fetch_for_scrapy(request, &cfg)
            }));
        }
    }
    for plugin in &plugins {
        process = process.with_plugin(plugin.clone());
    }
    let pipeline_names = if let Some(cfg) = &project_cfg {
        let mut names = configured_scrapy_pipelines_for_spider(cfg, &selected_spider);
        for plugin in &plugins {
            for pipeline in plugin.provide_pipelines() {
                names.push(rust_component_name(&*pipeline));
            }
        }
        names
    } else {
        Vec::new()
    };
    let spider_middleware_names = if let Some(cfg) = &project_cfg {
        let mut names = configured_scrapy_spider_middlewares_for_spider(cfg, &selected_spider);
        for plugin in &plugins {
            for middleware in plugin.provide_spider_middlewares() {
                names.push(rust_component_name(&*middleware));
            }
        }
        names
    } else {
        Vec::new()
    };
    let downloader_middleware_names = if let Some(cfg) = &project_cfg {
        let mut names = configured_scrapy_downloader_middlewares_for_spider(cfg, &selected_spider);
        for plugin in &plugins {
            for middleware in plugin.provide_downloader_middlewares() {
                names.push(rust_component_name(&*middleware));
            }
        }
        names
    } else {
        Vec::new()
    };
    if let Some(cfg) = &project_cfg {
        for pipeline in build_declarative_scrapy_pipelines(cfg, &selected_spider) {
            process = process.with_pipeline(pipeline);
        }
        for middleware in build_declarative_scrapy_spider_middlewares(cfg, &selected_spider) {
            process = process.with_spider_middleware(middleware);
        }
        for middleware in build_declarative_scrapy_downloader_middlewares(cfg, &selected_spider) {
            process = process.with_downloader_middleware(middleware);
        }
    }
    let items = match process.run() {
        Ok(items) => items,
        Err(err) => {
            eprintln!("scrapy demo failed: {err}");
            return 1;
        }
    };

    let mut exporter = ScrapyFeedExporter::new("json", &output);
    for item in items.iter().cloned() {
        exporter.export_item(item);
    }
    if let Err(err) = exporter.close() {
        eprintln!("failed to export scrapy demo items: {err}");
        return 1;
    }

    let reverse_summary = if let Some(cfg) = &project_cfg {
        if cfg.node_reverse.enabled && !cfg.node_reverse.base_url.trim().is_empty() {
            rustspider::scrapy::project::collect_reverse_summary(
                &cfg.node_reverse.base_url,
                &url,
                &html_file,
            )
        } else {
            serde_json::Value::Null
        }
    } else {
        serde_json::Value::Null
    };

    let resolved_runner = project_cfg
        .as_ref()
        .map(|cfg| resolve_scrapy_runner(cfg, &selected_spider, &serde_json::Value::Null))
        .unwrap_or_else(|| "http".to_string());
    let settings_source = if !project.trim().is_empty() {
        let candidate = PathBuf::from(&project).join("spider-framework.yaml");
        if candidate.exists() {
            serde_json::Value::String(candidate.to_string_lossy().to_string())
        } else {
            serde_json::Value::Null
        }
    } else {
        serde_json::Value::Null
    };

    println!(
        "{}",
        serde_json::to_string_pretty(&serde_json::json!({
            "command": format!("scrapy {}", subcommand),
            "runtime": "rust",
            "project_runner": "built-in-metadata-runner",
            "runner": resolved_runner,
            "resolved_runner": resolved_runner,
            "runner_source": if !html_file.trim().is_empty() { "html-fixture".to_string() } else { runner_source },
            "resolved_url": url,
            "url_source": if !html_file.trim().is_empty() { "html-fixture".to_string() } else { url_source },
            "spider": if selected_spider.trim().is_empty() { serde_json::Value::Null } else { serde_json::Value::String(selected_spider.clone()) },
            "item_count": items.len(),
            "output": output,
            "settings_source": settings_source,
            "plugins": resolved_plugin_names,
            "pipeline_count": pipeline_count,
            "spider_middleware_count": spider_middleware_count,
            "downloader_middleware_count": downloader_middleware_count,
            "runtime_features": {
                "browser": !html_file.trim().is_empty() || matches!(resolved_runner.as_str(), "browser" | "hybrid"),
                "anti_bot": project_cfg.as_ref().map(|cfg| cfg.anti_bot.enabled).unwrap_or(true),
                "node_reverse": project_cfg.as_ref().map(|cfg| cfg.node_reverse.enabled && !cfg.node_reverse.base_url.trim().is_empty()).unwrap_or(false),
                "distributed": true,
            },
            "pipelines": pipeline_names,
            "spider_middlewares": spider_middleware_names,
            "downloader_middlewares": downloader_middleware_names,
            "reverse": reverse_summary,
        }))
        .unwrap_or_default()
    );
    0
}

fn handle_ultimate(args: &[String]) -> i32 {
    let mut url: Option<String> = None;
    let mut config_path: Option<String> = None;
    let mut reverse_service_url: Option<String> = None;
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--url" => {
                if let Some(value) = args.get(i + 1) {
                    url = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --url");
                    return 2;
                }
            }
            "--config" => {
                if let Some(value) = args.get(i + 1) {
                    config_path = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --config");
                    return 2;
                }
            }
            "--reverse-service-url" => {
                if let Some(value) = args.get(i + 1) {
                    reverse_service_url = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --reverse-service-url");
                    return 2;
                }
            }
            unknown => {
                eprintln!("unknown ultimate argument: {unknown}");
                return 2;
            }
        }
    }

    let cfg = match load_contract_config(config_path.as_ref()) {
        Ok(cfg) => cfg,
        Err(err) => {
            eprintln!("config error: {err}");
            return 2;
        }
    };

    let mut urls = cfg.crawl.urls.clone();
    if let Some(explicit) = url {
        urls = vec![explicit];
    }
    if urls.is_empty() {
        eprintln!("ultimate requires --url or a config with crawl.urls");
        return 2;
    }

    let reverse_url = reverse_service_url
        .or_else(|| {
            if cfg.node_reverse.enabled {
                Some(cfg.node_reverse.base_url.clone())
            } else {
                None
            }
        })
        .or_else(|| env::var("SPIDER_REVERSE_SERVICE_URL").ok())
        .unwrap_or_else(|| "http://localhost:3000".to_string());

    let proxy_servers =
        if cfg.anti_bot.proxy_pool.trim().is_empty() || cfg.anti_bot.proxy_pool == "local" {
            vec![]
        } else {
            cfg.anti_bot
                .proxy_pool
                .split(',')
                .map(|item| item.trim().to_string())
                .filter(|item| !item.is_empty())
                .collect()
        };

    let runtime = match tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(err) => {
            eprintln!("failed to initialize runtime: {err}");
            return 1;
        }
    };

    let spider = create_ultimate_spider(Some(UltimateConfig {
        reverse_service_url: reverse_url,
        max_concurrency: cfg.crawl.concurrency.max(1),
        max_retries: 3,
        timeout: Duration::from_secs(cfg.crawl.timeout_seconds.max(1)),
        user_agent: if cfg.browser.user_agent.trim().is_empty() {
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36".to_string()
        } else {
            cfg.browser.user_agent.clone()
        },
        proxy_servers,
        output_format: cfg.export.format.clone(),
        monitor_port: 8080,
        checkpoint_dir: cfg.storage.checkpoint_dir.clone(),
        enable_ai: true,
        enable_browser: cfg.browser.enabled,
        enable_distributed: false,
        captcha_provider: cfg.anti_bot.captcha_provider.clone(),
        captcha_api_key: if cfg.anti_bot.captcha_api_key.trim().is_empty() {
            match cfg.anti_bot.captcha_provider.trim() {
                "anticaptcha" => env::var("ANTI_CAPTCHA_API_KEY").unwrap_or_default(),
                _ => env::var("TWO_CAPTCHA_API_KEY")
                    .or_else(|_| env::var("CAPTCHA_API_KEY"))
                    .unwrap_or_default(),
            }
        } else {
            cfg.anti_bot.captcha_api_key.clone()
        },
        captcha_fallback_provider: env::var("RUSTSPIDER_CAPTCHA_FALLBACK_PROVIDER")
            .or_else(|_| env::var("CAPTCHA_FALLBACK_PROVIDER"))
            .ok()
            .filter(|value| !value.trim().is_empty()),
        captcha_fallback_api_key: env::var("RUSTSPIDER_CAPTCHA_FALLBACK_API_KEY")
            .or_else(|_| env::var("CAPTCHA_FALLBACK_API_KEY"))
            .ok()
            .filter(|value| !value.trim().is_empty()),
    }));

    match runtime.block_on(spider.start(urls)) {
        Ok(results) => {
            let failed_count = results.iter().filter(|result| !result.success).count();
            let normalized_results: Vec<serde_json::Value> = results
                .iter()
                .map(|result| {
                    serde_json::json!({
                        "task_id": result.task_id,
                        "url": result.url,
                        "success": result.success,
                        "error": result.error,
                        "duration": format!("{:?}", result.duration),
                        "anti_bot_level": result.anti_bot_level,
                        "anti_bot_signals": result.anti_bot_signals,
                        "proxy_used": result.proxy_used,
                        "reverse": result.reverse_runtime,
                    })
                })
                .collect();
            let payload = serde_json::json!({
                "command": "ultimate",
                "runtime": "rust",
                "summary": if failed_count == 0 { "passed" } else { "failed" },
                "summary_text": format!("{} results, {} failed", results.len(), failed_count),
                "exit_code": if failed_count == 0 { 0 } else { 1 },
                "url_count": results.len(),
                "result_count": results.len(),
                "results": normalized_results,
            });
            println!(
                "{}",
                serde_json::to_string_pretty(&payload).unwrap_or_default()
            );
            if failed_count == 0 {
                0
            } else {
                1
            }
        }
        Err(err) => {
            eprintln!("ultimate failed: {err}");
            1
        }
    }
}

fn handle_ai(args: &[String]) -> i32 {
    let mut url: Option<String> = None;
    let mut html_file: Option<String> = None;
    let mut config_path: Option<String> = None;
    let mut instructions: Option<String> = None;
    let mut schema_file: Option<String> = None;
    let mut schema_json: Option<String> = None;
    let mut question: Option<String> = None;
    let mut description: Option<String> = None;
    let mut output: Option<String> = None;
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--url" => {
                if let Some(value) = args.get(i + 1) {
                    url = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --url");
                    return 2;
                }
            }
            "--html-file" => {
                if let Some(value) = args.get(i + 1) {
                    html_file = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --html-file");
                    return 2;
                }
            }
            "--config" => {
                if let Some(value) = args.get(i + 1) {
                    config_path = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --config");
                    return 2;
                }
            }
            "--instructions" => {
                if let Some(value) = args.get(i + 1) {
                    instructions = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --instructions");
                    return 2;
                }
            }
            "--schema-file" => {
                if let Some(value) = args.get(i + 1) {
                    schema_file = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --schema-file");
                    return 2;
                }
            }
            "--schema-json" => {
                if let Some(value) = args.get(i + 1) {
                    schema_json = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --schema-json");
                    return 2;
                }
            }
            "--question" => {
                if let Some(value) = args.get(i + 1) {
                    question = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --question");
                    return 2;
                }
            }
            "--description" => {
                if let Some(value) = args.get(i + 1) {
                    description = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --description");
                    return 2;
                }
            }
            "--output" => {
                if let Some(value) = args.get(i + 1) {
                    output = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --output");
                    return 2;
                }
            }
            unknown => {
                eprintln!("unknown ai argument: {unknown}");
                return 2;
            }
        }
    }

    let cfg = match load_contract_config(config_path.as_ref()) {
        Ok(cfg) => cfg,
        Err(err) => {
            eprintln!("config error: {err}");
            return 2;
        }
    };

    let mode = detect_ai_mode(
        instructions.as_deref(),
        question.as_deref(),
        description.as_deref(),
        schema_file.as_deref(),
        schema_json.as_deref(),
    );
    let mut warnings = Vec::new();
    let mut engine = "heuristic-fallback".to_string();
    let mut source = "description".to_string();
    let mut resolved_url = String::new();

    let result = if mode == "generate-config" {
        let description_text = description.clone().unwrap_or_default();
        let mut result = heuristic_ai_generate_config(&description_text);
        if let Some(ai_config) = ai_request_config() {
            match ai_chat_completion(
                &ai_config,
                &format!(
                    "根据以下自然语言描述，生成爬虫配置（JSON 格式）。只返回 JSON。\n\n描述：{}",
                    description_text
                ),
            ) {
                Ok(content) => {
                    if let Ok(value) = parse_json_candidate(&content) {
                        result = value;
                        engine = "llm".to_string();
                    } else {
                        warnings.push(
                            "llm response was not valid JSON; used heuristic fallback".to_string(),
                        );
                    }
                }
                Err(err) => warnings.push(err),
            }
        } else {
            warnings
                .push("AI_API_KEY / OPENAI_API_KEY not set; used heuristic fallback".to_string());
        }
        result
    } else {
        let target_url = url.clone().or_else(|| cfg.crawl.urls.first().cloned());
        let html = if let Some(path) = html_file.clone() {
            source = "html-file".to_string();
            resolved_url = target_url
                .clone()
                .unwrap_or_else(|| format!("file://{}", path.replace('\\', "/")));
            match fs::read_to_string(&path) {
                Ok(text) => text,
                Err(err) => {
                    eprintln!("failed to read html file: {err}");
                    return 1;
                }
            }
        } else if let Some(target) = target_url.clone() {
            source = if url.is_some() { "url" } else { "config" }.to_string();
            resolved_url = target.clone();
            match reqwest::blocking::get(&target) {
                Ok(response) => match response.text() {
                    Ok(text) => text,
                    Err(err) => {
                        eprintln!("failed to read response body: {err}");
                        return 1;
                    }
                },
                Err(err) => {
                    eprintln!("failed to fetch url: {err}");
                    return 1;
                }
            }
        } else {
            eprintln!("ai requires --url, --html-file, or a config with crawl.urls");
            return 2;
        };

        match mode.as_str() {
            "extract" => {
                let schema = match load_ai_schema(schema_file.as_deref(), schema_json.as_deref()) {
                    Ok(value) => value,
                    Err(err) => {
                        eprintln!("invalid ai schema: {err}");
                        return 2;
                    }
                };
                let instructions_text = instructions
                    .clone()
                    .unwrap_or_else(|| "提取页面中的核心结构化字段".to_string());
                let mut result = heuristic_ai_extract(&resolved_url, &html, &schema);
                if let Some(ai_config) = ai_request_config() {
                    let prompt = format!(
                        "请从以下内容中提取结构化数据。\n\n提取要求：{}\n\n期望的输出格式（JSON Schema）：\n{}\n\n页面内容：\n{}\n\n请直接返回 JSON。",
                        instructions_text,
                        serde_json::to_string_pretty(&schema).unwrap_or_default(),
                        truncate_ai_content(&html, 12000)
                    );
                    match ai_chat_completion(&ai_config, &prompt) {
                        Ok(content) => match parse_json_candidate(&content) {
                            Ok(value) => {
                                result = value;
                                engine = "llm".to_string();
                            }
                            Err(err) => warnings.push(err),
                        },
                        Err(err) => warnings.push(err),
                    }
                } else {
                    warnings.push(
                        "AI_API_KEY / OPENAI_API_KEY not set; used heuristic fallback".to_string(),
                    );
                }
                result
            }
            "understand" => {
                let question_text = question
                    .clone()
                    .unwrap_or_else(|| "请总结页面类型、核心内容和推荐提取字段。".to_string());
                let fallback = heuristic_ai_understand(&resolved_url, &html, &question_text);
                let mut result = fallback.clone();
                if let Some(ai_config) = ai_request_config() {
                    let prompt = format!(
                        "请分析以下网页内容并回答问题。\n\n问题：{}\n\n页面内容：\n{}",
                        question_text,
                        truncate_ai_content(&html, 12000)
                    );
                    match ai_chat_completion(&ai_config, &prompt) {
                        Ok(answer) => {
                            result = serde_json::json!({
                                "answer": answer,
                                "page_profile": fallback["page_profile"].clone()
                            });
                            engine = "llm".to_string();
                        }
                        Err(err) => warnings.push(err),
                    }
                } else {
                    warnings.push(
                        "AI_API_KEY / OPENAI_API_KEY not set; used heuristic fallback".to_string(),
                    );
                }
                result
            }
            other => {
                eprintln!("unsupported ai mode: {other}");
                return 2;
            }
        }
    };

    let mut payload = serde_json::json!({
        "command": "ai",
        "runtime": "rust",
        "mode": mode,
        "summary": "passed",
        "summary_text": format!("{} mode completed with engine {}", mode, engine),
        "exit_code": 0,
        "engine": engine,
        "source": source,
        "warnings": warnings,
        "result": result,
    });
    if !resolved_url.is_empty() {
        payload["url"] = serde_json::Value::String(resolved_url);
    }
    let encoded = serde_json::to_string_pretty(&payload).unwrap_or_default();
    if let Some(path) = output {
        let output_path = PathBuf::from(path);
        if let Some(parent) = output_path.parent() {
            if let Err(err) = fs::create_dir_all(parent) {
                eprintln!("failed to create ai output dir: {err}");
                return 1;
            }
        }
        if let Err(err) = fs::write(&output_path, &encoded) {
            eprintln!("failed to write ai output: {err}");
            return 1;
        }
    }
    println!("{encoded}");
    0
}

fn handle_node_reverse(args: &[String]) -> i32 {
    if args.is_empty() {
        eprintln!("usage: node-reverse <health|profile|detect|fingerprint-spoof|tls-fingerprint|canvas-fingerprint|analyze-crypto|signature-reverse|ast|webpack|function-call|browser-simulate> [options]");
        return 2;
    }
    match args[0].as_str() {
        "health" => handle_node_reverse_health(&args[1..]),
        "profile" => handle_node_reverse_profile(&args[1..]),
        "detect" => handle_node_reverse_detect(&args[1..]),
        "fingerprint-spoof" => handle_node_reverse_fingerprint_spoof(&args[1..]),
        "tls-fingerprint" => handle_node_reverse_tls_fingerprint(&args[1..]),
        "canvas-fingerprint" => handle_node_reverse_canvas_fingerprint(&args[1..]),
        "analyze-crypto" => handle_node_reverse_analyze_crypto(&args[1..]),
        "signature-reverse" => handle_node_reverse_signature_reverse(&args[1..]),
        "ast" => handle_node_reverse_ast(&args[1..]),
        "webpack" => handle_node_reverse_webpack(&args[1..]),
        "function-call" => handle_node_reverse_function_call(&args[1..]),
        "browser-simulate" => handle_node_reverse_browser_simulate(&args[1..]),
        other => {
            eprintln!("unknown node-reverse subcommand: {other}");
            2
        }
    }
}

fn handle_node_reverse_health(args: &[String]) -> i32 {
    let mut base_url = String::from("http://localhost:3000");
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--base-url" if i + 1 < args.len() => {
                base_url = args[i + 1].clone();
                i += 2;
            }
            unknown => {
                eprintln!("unknown node-reverse health argument: {unknown}");
                return 2;
            }
        }
    }
    let runtime = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(err) => {
            eprintln!("failed to initialize tokio runtime: {err}");
            return 1;
        }
    };
    let client = NodeReverseClient::new(base_url.clone());
    let healthy = runtime.block_on(client.health_check()).unwrap_or(false);
    println!(
        "{}",
        serde_json::to_string_pretty(&serde_json::json!({
            "command": "node-reverse health",
            "runtime": "rust",
            "base_url": base_url,
            "healthy": healthy
        }))
        .unwrap_or_default()
    );
    if healthy {
        0
    } else {
        1
    }
}

fn handle_node_reverse_profile(args: &[String]) -> i32 {
    let mut base_url = String::from("http://localhost:3000");
    let mut url = String::new();
    let mut html_file = String::new();
    let mut status_code: Option<u16> = None;
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--base-url" if i + 1 < args.len() => {
                base_url = args[i + 1].clone();
                i += 2;
            }
            "--url" if i + 1 < args.len() => {
                url = args[i + 1].clone();
                i += 2;
            }
            "--html-file" if i + 1 < args.len() => {
                html_file = args[i + 1].clone();
                i += 2;
            }
            "--status-code" if i + 1 < args.len() => {
                status_code = args[i + 1].parse::<u16>().ok();
                i += 2;
            }
            unknown => {
                eprintln!("unknown node-reverse profile argument: {unknown}");
                return 2;
            }
        }
    }

    let (html, resolved_url) = match load_html_input(&url, &html_file) {
        Ok(value) => value,
        Err(err) => {
            eprintln!("{err}");
            return 2;
        }
    };

    let runtime = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(err) => {
            eprintln!("failed to initialize tokio runtime: {err}");
            return 1;
        }
    };
    let client = NodeReverseClient::new(base_url);
    let response = runtime.block_on(client.profile_anti_bot(&AntiBotProfileRequest {
        html,
        js: String::new(),
        headers: std::collections::HashMap::new(),
        cookies: String::new(),
        status_code,
        url: resolved_url,
    }));
    match response {
        Ok(payload) => {
            println!(
                "{}",
                serde_json::to_string_pretty(&payload).unwrap_or_default()
            );
            if payload.success {
                0
            } else {
                1
            }
        }
        Err(err) => {
            eprintln!("node-reverse profile failed: {err}");
            1
        }
    }
}

fn handle_node_reverse_detect(args: &[String]) -> i32 {
    let mut base_url = String::from("http://localhost:3000");
    let mut url = String::new();
    let mut html_file = String::new();
    let mut status_code: Option<u16> = None;
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--base-url" if i + 1 < args.len() => {
                base_url = args[i + 1].clone();
                i += 2;
            }
            "--url" if i + 1 < args.len() => {
                url = args[i + 1].clone();
                i += 2;
            }
            "--html-file" if i + 1 < args.len() => {
                html_file = args[i + 1].clone();
                i += 2;
            }
            "--status-code" if i + 1 < args.len() => {
                status_code = args[i + 1].parse::<u16>().ok();
                i += 2;
            }
            unknown => {
                eprintln!("unknown node-reverse detect argument: {unknown}");
                return 2;
            }
        }
    }

    let (html, resolved_url) = match load_html_input(&url, &html_file) {
        Ok(value) => value,
        Err(err) => {
            eprintln!("{err}");
            return 2;
        }
    };

    let runtime = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(err) => {
            eprintln!("failed to initialize tokio runtime: {err}");
            return 1;
        }
    };
    let client = NodeReverseClient::new(base_url);
    let response = runtime.block_on(client.detect_anti_bot(&AntiBotProfileRequest {
        html,
        js: String::new(),
        headers: std::collections::HashMap::new(),
        cookies: String::new(),
        status_code,
        url: resolved_url,
    }));
    match response {
        Ok(payload) => {
            println!(
                "{}",
                serde_json::to_string_pretty(&payload).unwrap_or_default()
            );
            if payload.success {
                0
            } else {
                1
            }
        }
        Err(err) => {
            eprintln!("node-reverse detect failed: {err}");
            1
        }
    }
}

fn handle_node_reverse_fingerprint_spoof(args: &[String]) -> i32 {
    let mut base_url = String::from("http://localhost:3000");
    let mut browser = String::from("chrome");
    let mut platform = String::from("windows");
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--base-url" if i + 1 < args.len() => {
                base_url = args[i + 1].clone();
                i += 2;
            }
            "--browser" if i + 1 < args.len() => {
                browser = args[i + 1].clone();
                i += 2;
            }
            "--platform" if i + 1 < args.len() => {
                platform = args[i + 1].clone();
                i += 2;
            }
            unknown => {
                eprintln!("unknown node-reverse fingerprint-spoof argument: {unknown}");
                return 2;
            }
        }
    }

    let runtime = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(err) => {
            eprintln!("failed to initialize tokio runtime: {err}");
            return 1;
        }
    };
    let client = NodeReverseClient::new(base_url);
    let response = runtime.block_on(client.spoof_fingerprint(&browser, &platform));
    match response {
        Ok(payload) => {
            println!(
                "{}",
                serde_json::to_string_pretty(&payload).unwrap_or_default()
            );
            if payload.success {
                0
            } else {
                1
            }
        }
        Err(err) => {
            eprintln!("node-reverse fingerprint-spoof failed: {err}");
            1
        }
    }
}

fn handle_node_reverse_tls_fingerprint(args: &[String]) -> i32 {
    let mut base_url = String::from("http://localhost:3000");
    let mut browser = String::from("chrome");
    let mut version = String::from("120");
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--base-url" if i + 1 < args.len() => {
                base_url = args[i + 1].clone();
                i += 2;
            }
            "--browser" if i + 1 < args.len() => {
                browser = args[i + 1].clone();
                i += 2;
            }
            "--version" if i + 1 < args.len() => {
                version = args[i + 1].clone();
                i += 2;
            }
            unknown => {
                eprintln!("unknown node-reverse tls-fingerprint argument: {unknown}");
                return 2;
            }
        }
    }

    let runtime = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(err) => {
            eprintln!("failed to initialize tokio runtime: {err}");
            return 1;
        }
    };
    let client = NodeReverseClient::new(base_url);
    let response = runtime.block_on(client.tls_fingerprint(&browser, &version));
    match response {
        Ok(payload) => {
            println!(
                "{}",
                serde_json::to_string_pretty(&payload).unwrap_or_default()
            );
            if payload.success {
                0
            } else {
                1
            }
        }
        Err(err) => {
            eprintln!("node-reverse tls-fingerprint failed: {err}");
            1
        }
    }
}

fn handle_node_reverse_canvas_fingerprint(args: &[String]) -> i32 {
    let mut base_url = String::from("http://localhost:3000");
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--base-url" if i + 1 < args.len() => {
                base_url = args[i + 1].clone();
                i += 2;
            }
            unknown => {
                eprintln!("unknown node-reverse canvas-fingerprint argument: {unknown}");
                return 2;
            }
        }
    }
    let runtime = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(err) => {
            eprintln!("failed to initialize tokio runtime: {err}");
            return 1;
        }
    };
    let client = NodeReverseClient::new(base_url);
    let response = runtime.block_on(client.canvas_fingerprint());
    match response {
        Ok(payload) => {
            let success = payload
                .get("success")
                .and_then(|value| value.as_bool())
                .unwrap_or(false);
            println!(
                "{}",
                serde_json::to_string_pretty(&payload).unwrap_or_default()
            );
            if success {
                0
            } else {
                1
            }
        }
        Err(err) => {
            eprintln!("node-reverse canvas-fingerprint failed: {err}");
            1
        }
    }
}

fn handle_node_reverse_analyze_crypto(args: &[String]) -> i32 {
    let mut base_url = String::from("http://localhost:3000");
    let mut code_file = String::new();
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--base-url" if i + 1 < args.len() => {
                base_url = args[i + 1].clone();
                i += 2;
            }
            "--code-file" if i + 1 < args.len() => {
                code_file = args[i + 1].clone();
                i += 2;
            }
            unknown => {
                eprintln!("unknown node-reverse analyze-crypto argument: {unknown}");
                return 2;
            }
        }
    }
    if code_file.trim().is_empty() {
        eprintln!("node-reverse analyze-crypto requires --code-file");
        return 2;
    }
    let code = match fs::read_to_string(&code_file) {
        Ok(code) => code,
        Err(err) => {
            eprintln!("failed to read code file: {err}");
            return 1;
        }
    };
    let runtime = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(err) => {
            eprintln!("failed to initialize tokio runtime: {err}");
            return 1;
        }
    };
    let client = NodeReverseClient::new(base_url);
    let response = runtime.block_on(client.analyze_crypto(&code));
    match response {
        Ok(payload) => {
            println!(
                "{}",
                serde_json::to_string_pretty(&payload).unwrap_or_default()
            );
            if payload.success {
                0
            } else {
                1
            }
        }
        Err(err) => {
            eprintln!("node-reverse analyze-crypto failed: {err}");
            1
        }
    }
}

fn handle_node_reverse_signature_reverse(args: &[String]) -> i32 {
    let mut base_url = String::from("http://localhost:3000");
    let mut code_file = String::new();
    let mut input_data = String::new();
    let mut expected_output = String::new();
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--base-url" if i + 1 < args.len() => {
                base_url = args[i + 1].clone();
                i += 2;
            }
            "--code-file" if i + 1 < args.len() => {
                code_file = args[i + 1].clone();
                i += 2;
            }
            "--input-data" if i + 1 < args.len() => {
                input_data = args[i + 1].clone();
                i += 2;
            }
            "--expected-output" if i + 1 < args.len() => {
                expected_output = args[i + 1].clone();
                i += 2;
            }
            unknown => {
                eprintln!("unknown node-reverse signature-reverse argument: {unknown}");
                return 2;
            }
        }
    }
    if code_file.trim().is_empty()
        || input_data.trim().is_empty()
        || expected_output.trim().is_empty()
    {
        eprintln!("node-reverse signature-reverse requires --code-file, --input-data, and --expected-output");
        return 2;
    }
    let code = match fs::read_to_string(&code_file) {
        Ok(code) => code,
        Err(err) => {
            eprintln!("failed to read code file: {err}");
            return 1;
        }
    };
    let runtime = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(err) => {
            eprintln!("failed to initialize tokio runtime: {err}");
            return 1;
        }
    };
    let client = NodeReverseClient::new(base_url);
    let response = runtime.block_on(client.reverse_signature(&code, &input_data, &expected_output));
    match response {
        Ok(payload) => {
            let success = payload
                .get("success")
                .and_then(|value| value.as_bool())
                .unwrap_or(false);
            println!(
                "{}",
                serde_json::to_string_pretty(&payload).unwrap_or_default()
            );
            if success {
                0
            } else {
                1
            }
        }
        Err(err) => {
            eprintln!("node-reverse signature-reverse failed: {err}");
            1
        }
    }
}

fn handle_node_reverse_ast(args: &[String]) -> i32 {
    let mut base_url = String::from("http://localhost:3000");
    let mut code_file = String::new();
    let mut analysis = String::from("crypto,obfuscation,anti-debug");
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--base-url" if i + 1 < args.len() => {
                base_url = args[i + 1].clone();
                i += 2;
            }
            "--code-file" if i + 1 < args.len() => {
                code_file = args[i + 1].clone();
                i += 2;
            }
            "--analysis" if i + 1 < args.len() => {
                analysis = args[i + 1].clone();
                i += 2;
            }
            unknown => {
                eprintln!("unknown node-reverse ast argument: {unknown}");
                return 2;
            }
        }
    }
    if code_file.trim().is_empty() {
        eprintln!("node-reverse ast requires --code-file");
        return 2;
    }
    let code = match fs::read_to_string(&code_file) {
        Ok(code) => code,
        Err(err) => {
            eprintln!("failed to read code file: {err}");
            return 1;
        }
    };
    let analysis_types = analysis
        .split(',')
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .collect::<Vec<_>>();
    let runtime = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(err) => {
            eprintln!("failed to initialize tokio runtime: {err}");
            return 1;
        }
    };
    let client = NodeReverseClient::new(base_url);
    let response = runtime.block_on(client.analyze_ast(&code, Some(analysis_types)));
    match response {
        Ok(payload) => {
            println!(
                "{}",
                serde_json::to_string_pretty(&payload).unwrap_or_default()
            );
            if payload.success {
                0
            } else {
                1
            }
        }
        Err(err) => {
            eprintln!("node-reverse ast failed: {err}");
            1
        }
    }
}

fn handle_node_reverse_webpack(args: &[String]) -> i32 {
    let mut base_url = String::from("http://localhost:3000");
    let mut code_file = String::new();
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--base-url" if i + 1 < args.len() => {
                base_url = args[i + 1].clone();
                i += 2;
            }
            "--code-file" if i + 1 < args.len() => {
                code_file = args[i + 1].clone();
                i += 2;
            }
            unknown => {
                eprintln!("unknown node-reverse webpack argument: {unknown}");
                return 2;
            }
        }
    }
    if code_file.trim().is_empty() {
        eprintln!("node-reverse webpack requires --code-file");
        return 2;
    }
    let code = match fs::read_to_string(&code_file) {
        Ok(code) => code,
        Err(err) => {
            eprintln!("failed to read code file: {err}");
            return 1;
        }
    };
    let runtime = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(err) => {
            eprintln!("failed to initialize tokio runtime: {err}");
            return 1;
        }
    };
    let client = NodeReverseClient::new(base_url);
    let response = runtime.block_on(client.analyze_webpack(&code));
    match response {
        Ok(payload) => {
            let success = payload
                .get("success")
                .and_then(|value| value.as_bool())
                .unwrap_or(false);
            println!(
                "{}",
                serde_json::to_string_pretty(&payload).unwrap_or_default()
            );
            if success {
                0
            } else {
                1
            }
        }
        Err(err) => {
            eprintln!("node-reverse webpack failed: {err}");
            1
        }
    }
}

fn handle_node_reverse_function_call(args: &[String]) -> i32 {
    let mut base_url = String::from("http://localhost:3000");
    let mut code_file = String::new();
    let mut function_name = String::new();
    let mut fn_args = Vec::new();
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--base-url" if i + 1 < args.len() => {
                base_url = args[i + 1].clone();
                i += 2;
            }
            "--code-file" if i + 1 < args.len() => {
                code_file = args[i + 1].clone();
                i += 2;
            }
            "--function-name" if i + 1 < args.len() => {
                function_name = args[i + 1].clone();
                i += 2;
            }
            "--arg" if i + 1 < args.len() => {
                fn_args.push(serde_json::json!(args[i + 1].clone()));
                i += 2;
            }
            unknown => {
                eprintln!("unknown node-reverse function-call argument: {unknown}");
                return 2;
            }
        }
    }
    if code_file.trim().is_empty() || function_name.trim().is_empty() {
        eprintln!("node-reverse function-call requires --code-file and --function-name");
        return 2;
    }
    let code = match fs::read_to_string(&code_file) {
        Ok(code) => code,
        Err(err) => {
            eprintln!("failed to read code file: {err}");
            return 1;
        }
    };
    let runtime = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(err) => {
            eprintln!("failed to initialize tokio runtime: {err}");
            return 1;
        }
    };
    let client = NodeReverseClient::new(base_url);
    let response = runtime.block_on(client.call_function(&function_name, fn_args, &code));
    match response {
        Ok(payload) => {
            println!(
                "{}",
                serde_json::to_string_pretty(&payload).unwrap_or_default()
            );
            if payload.success {
                0
            } else {
                1
            }
        }
        Err(err) => {
            eprintln!("node-reverse function-call failed: {err}");
            1
        }
    }
}

fn handle_node_reverse_browser_simulate(args: &[String]) -> i32 {
    let mut base_url = String::from("http://localhost:3000");
    let mut code_file = String::new();
    let mut user_agent =
        String::from("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36");
    let mut language = String::from("zh-CN");
    let mut platform = String::from("Win32");
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--base-url" if i + 1 < args.len() => {
                base_url = args[i + 1].clone();
                i += 2;
            }
            "--code-file" if i + 1 < args.len() => {
                code_file = args[i + 1].clone();
                i += 2;
            }
            "--user-agent" if i + 1 < args.len() => {
                user_agent = args[i + 1].clone();
                i += 2;
            }
            "--language" if i + 1 < args.len() => {
                language = args[i + 1].clone();
                i += 2;
            }
            "--platform" if i + 1 < args.len() => {
                platform = args[i + 1].clone();
                i += 2;
            }
            unknown => {
                eprintln!("unknown node-reverse browser-simulate argument: {unknown}");
                return 2;
            }
        }
    }
    if code_file.trim().is_empty() {
        eprintln!("node-reverse browser-simulate requires --code-file");
        return 2;
    }
    let code = match fs::read_to_string(&code_file) {
        Ok(code) => code,
        Err(err) => {
            eprintln!("failed to read code file: {err}");
            return 1;
        }
    };
    let runtime = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(err) => {
            eprintln!("failed to initialize tokio runtime: {err}");
            return 1;
        }
    };
    let client = NodeReverseClient::new(base_url);
    let response = runtime.block_on(client.simulate_browser(
        &code,
        Some(serde_json::json!({
            "userAgent": user_agent,
            "language": language,
            "platform": platform,
        })),
    ));
    match response {
        Ok(payload) => {
            println!(
                "{}",
                serde_json::to_string_pretty(&payload).unwrap_or_default()
            );
            if payload.success {
                0
            } else {
                1
            }
        }
        Err(err) => {
            eprintln!("node-reverse browser-simulate failed: {err}");
            1
        }
    }
}

fn handle_antibot(args: &[String]) -> i32 {
    if args.is_empty() {
        eprintln!("usage: anti-bot <headers|profile> [options]");
        return 2;
    }
    match args[0].as_str() {
        "headers" => handle_antibot_headers(),
        "profile" => handle_antibot_profile(&args[1..]),
        other => {
            eprintln!("unknown anti-bot subcommand: {other}");
            2
        }
    }
}

fn handle_profile_site(args: &[String]) -> i32 {
    let mut url = String::new();
    let mut html_file = String::new();
    let mut base_url = String::from("http://localhost:3000");
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--url" if i + 1 < args.len() => {
                url = args[i + 1].clone();
                i += 2;
            }
            "--html-file" if i + 1 < args.len() => {
                html_file = args[i + 1].clone();
                i += 2;
            }
            "--base-url" if i + 1 < args.len() => {
                base_url = args[i + 1].clone();
                i += 2;
            }
            unknown => {
                eprintln!("unknown profile-site argument: {unknown}");
                return 2;
            }
        }
    }
    let (html, resolved_url) = match load_html_input(&url, &html_file) {
        Ok(value) => value,
        Err(err) => {
            eprintln!("{err}");
            return 2;
        }
    };
    let payload = local_site_profile_payload(&resolved_url, &html);
    let mut json_payload = serde_json::json!(payload);
    json_payload["framework"] = serde_json::json!("rustspider");
    json_payload["version"] = serde_json::json!(env!("CARGO_PKG_VERSION"));
    let reverse =
        rustspider::scrapy::project::collect_reverse_summary(&base_url, &resolved_url, &html_file);
    if !reverse.is_null() {
        json_payload["reverse"] = reverse.clone();
        let focus = build_reverse_focus(&reverse);
        if !focus.is_null() {
            json_payload["reverse_focus"] = focus;
        }
        if let Some(profile) = reverse.get("profile") {
            let signals = profile
                .get("signals")
                .and_then(|value| value.as_array())
                .cloned()
                .unwrap_or_default();
            let success = profile
                .get("success")
                .and_then(|value| value.as_bool())
                .unwrap_or(false);
            if success {
                json_payload["anti_bot_level"] = serde_json::json!(profile
                    .get("level")
                    .and_then(|value| value.as_str())
                    .unwrap_or(""));
                json_payload["anti_bot_signals"] = serde_json::Value::Array(signals.clone());
                json_payload["node_reverse_recommended"] = serde_json::json!(!signals.is_empty());
            }
        }
    }
    println!(
        "{}",
        serde_json::to_string_pretty(&json_payload).unwrap_or_default()
    );
    0
}

fn build_reverse_focus(reverse: &serde_json::Value) -> serde_json::Value {
    let Some(chains) = reverse
        .get("crypto_analysis")
        .and_then(|value| value.get("analysis"))
        .and_then(|value| value.get("keyFlowChains"))
        .and_then(|value| value.as_array())
    else {
        return serde_json::Value::Null;
    };
    let top = chains
        .iter()
        .filter(|item| item.is_object())
        .max_by(|left, right| {
            let left_confidence = left
                .get("confidence")
                .and_then(|value| value.as_f64())
                .unwrap_or(0.0);
            let right_confidence = right
                .get("confidence")
                .and_then(|value| value.as_f64())
                .unwrap_or(0.0);
            left_confidence
                .partial_cmp(&right_confidence)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| {
                    left.get("sinks")
                        .and_then(|value| value.as_array())
                        .map(|value| value.len())
                        .unwrap_or(0)
                        .cmp(
                            &right
                                .get("sinks")
                                .and_then(|value| value.as_array())
                                .map(|value| value.len())
                                .unwrap_or(0),
                        )
                })
                .then_with(|| {
                    left.get("derivations")
                        .and_then(|value| value.as_array())
                        .map(|value| value.len())
                        .unwrap_or(0)
                        .cmp(
                            &right
                                .get("derivations")
                                .and_then(|value| value.as_array())
                                .map(|value| value.len())
                                .unwrap_or(0),
                        )
                })
        });
    let Some(top) = top else {
        return serde_json::Value::Null;
    };
    let source_kind = top
        .get("source")
        .and_then(|value| value.get("kind"))
        .and_then(|value| value.as_str())
        .unwrap_or("unknown");
    let primary_sink = top
        .get("sinks")
        .and_then(|value| value.as_array())
        .and_then(|values| values.first())
        .and_then(|value| value.as_str())
        .unwrap_or("unknown-sink");
    let mut next_steps = Vec::new();
    if source_kind.starts_with("storage.") {
        next_steps.push(serde_json::json!("instrument browser storage reads first"));
    }
    if source_kind.starts_with("network.") {
        next_steps.push(serde_json::json!(
            "capture response body before key derivation"
        ));
    }
    if primary_sink.contains("crypto.subtle.") {
        next_steps.push(serde_json::json!("hook WebCrypto at the sink boundary"));
    }
    if primary_sink.starts_with("jwt.") || reverse.to_string().contains("HMAC") {
        next_steps.push(serde_json::json!(
            "rebuild canonical signing input before reproducing the sink"
        ));
    }
    if next_steps.is_empty() {
        next_steps.push(serde_json::json!(
            "trace the chain from source through derivations into the first sink"
        ));
    }
    serde_json::json!({
        "priority_chain": top,
        "summary": format!(
            "trace `{}` from `{}` into `{}`",
            top.get("variable").and_then(|value| value.as_str()).unwrap_or(""),
            source_kind,
            primary_sink
        ),
        "next_steps": next_steps,
    })
}

fn handle_sitemap_discover(args: &[String]) -> i32 {
    let mut url = String::new();
    let mut sitemap_file = String::new();
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--url" if i + 1 < args.len() => {
                url = args[i + 1].clone();
                i += 2;
            }
            "--sitemap-file" if i + 1 < args.len() => {
                sitemap_file = args[i + 1].clone();
                i += 2;
            }
            unknown => {
                eprintln!("unknown sitemap-discover argument: {unknown}");
                return 2;
            }
        }
    }
    let (content, source) = if !sitemap_file.trim().is_empty() {
        match fs::read_to_string(&sitemap_file) {
            Ok(data) => (data, sitemap_file),
            Err(err) => {
                eprintln!("failed to read sitemap file: {err}");
                return 1;
            }
        }
    } else if !url.trim().is_empty() {
        let candidate = format!("{}/sitemap.xml", url.trim_end_matches('/'));
        match reqwest::blocking::get(&candidate) {
            Ok(response) => match response.text() {
                Ok(data) => (data, candidate),
                Err(err) => {
                    eprintln!("failed to read sitemap response: {err}");
                    return 1;
                }
            },
            Err(err) => {
                eprintln!("failed to fetch sitemap: {err}");
                return 1;
            }
        }
    } else {
        eprintln!("sitemap-discover requires --url or --sitemap-file");
        return 2;
    };
    let urls = extract_sitemap_urls(&content);
    println!(
        "{}",
        serde_json::to_string_pretty(&serde_json::json!({
            "command": "sitemap-discover",
            "runtime": "rust",
            "source": source,
            "url_count": urls.len(),
            "urls": urls
        }))
        .unwrap_or_default()
    );
    0
}

fn handle_plugins(args: &[String]) -> i32 {
    if args.is_empty() || (args[0] != "list" && args[0] != "run") {
        eprintln!("usage: plugins <list|run> ...");
        return 2;
    }
    if args[0] == "run" {
        return handle_plugins_run(&args[1..]);
    }
    let mut manifest = String::from("contracts/integration-catalog.json");
    let mut i = 1usize;
    while i < args.len() {
        match args[i].as_str() {
            "--manifest" if i + 1 < args.len() => {
                manifest = args[i + 1].clone();
                i += 2;
            }
            unknown => {
                eprintln!("unknown plugins argument: {unknown}");
                return 2;
            }
        }
    }
    let content = match fs::read_to_string(&manifest) {
        Ok(content) => content,
        Err(err) => {
            eprintln!("failed to read manifest: {err}");
            return 1;
        }
    };
    let payload: serde_json::Value = match serde_json::from_str(&content) {
        Ok(payload) => payload,
        Err(err) => {
            eprintln!("invalid manifest json: {err}");
            return 1;
        }
    };
    println!("{}", serde_json::to_string_pretty(&serde_json::json!({
        "command": "plugins list",
        "runtime": "rust",
        "manifest": manifest,
        "plugins": payload.get("plugins").cloned().unwrap_or_else(|| payload.get("entrypoints").cloned().unwrap_or_default())
    })).unwrap_or_default());
    0
}

fn handle_plugins_run(args: &[String]) -> i32 {
    let mut plugin = String::new();
    let mut plugin_args: Vec<String> = Vec::new();
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--plugin" if i + 1 < args.len() => {
                plugin = args[i + 1].clone();
                i += 2;
            }
            "--" => {
                plugin_args = args[i + 1..].to_vec();
                break;
            }
            other => {
                plugin_args.push(other.to_string());
                i += 1;
            }
        }
    }
    if plugin.trim().is_empty() {
        eprintln!("plugins run requires --plugin");
        return 2;
    }
    match plugin.as_str() {
        "profile-site" => handle_profile_site(&plugin_args),
        "sitemap-discover" => handle_sitemap_discover(&plugin_args),
        "selector-studio" => handle_selector_studio(&plugin_args),
        "anti-bot" => handle_antibot(&plugin_args),
        "node-reverse" => handle_node_reverse(&plugin_args),
        other => {
            eprintln!("unknown plugin id: {other}");
            2
        }
    }
}

fn handle_selector_studio(args: &[String]) -> i32 {
    let mut url = String::new();
    let mut html_file = String::new();
    let mut mode = String::from("css");
    let mut expr = String::new();
    let mut attr = String::new();
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--url" if i + 1 < args.len() => {
                url = args[i + 1].clone();
                i += 2;
            }
            "--html-file" if i + 1 < args.len() => {
                html_file = args[i + 1].clone();
                i += 2;
            }
            "--type" if i + 1 < args.len() => {
                mode = args[i + 1].clone();
                i += 2;
            }
            "--expr" if i + 1 < args.len() => {
                expr = args[i + 1].clone();
                i += 2;
            }
            "--attr" if i + 1 < args.len() => {
                attr = args[i + 1].clone();
                i += 2;
            }
            unknown => {
                eprintln!("unknown selector-studio argument: {unknown}");
                return 2;
            }
        }
    }
    let (html, source) = match load_html_input(&url, &html_file) {
        Ok(value) => value,
        Err(err) => {
            eprintln!("{err}");
            return 2;
        }
    };
    let parser = HTMLParser::new(&html);
    let values = match mode.as_str() {
        "css" => parser.css(&expr),
        "css_attr" => parser.css_attr(&expr, &attr),
        "xpath" => parser.xpath_first(&expr).into_iter().collect(),
        "regex" => {
            let mut values = Vec::new();
            if let Ok(compiled) = regex::Regex::new(&expr) {
                for capture in compiled.captures_iter(&html) {
                    if let Some(value) = capture.get(1).or_else(|| capture.get(0)) {
                        values.push(value.as_str().to_string());
                    }
                }
            }
            values
        }
        _ => Vec::new(),
    };
    println!(
        "{}",
        serde_json::to_string_pretty(&serde_json::json!({
            "command": "selector-studio",
            "runtime": "rust",
            "framework": "rustspider",
            "version": env!("CARGO_PKG_VERSION"),
            "source": source,
            "type": mode,
            "expr": expr,
            "attr": attr,
            "count": values.len(),
            "values": values,
            "suggested_xpaths": rustspider::suggest_smart_xpath(&mode, &expr, &attr)
        }))
        .unwrap_or_default()
    );
    0
}

fn handle_antibot_headers() -> i32 {
    let handler = AntiBotHandler::new();
    let headers = handler.get_random_headers();
    let fingerprint = handler.generate_fingerprint();
    println!(
        "{}",
        serde_json::to_string_pretty(&serde_json::json!({
            "command": "anti-bot headers",
            "runtime": "rust",
            "headers": headers,
            "fingerprint": fingerprint
        }))
        .unwrap_or_default()
    );
    0
}

fn handle_antibot_profile(args: &[String]) -> i32 {
    let mut url = String::new();
    let mut html_file = String::new();
    let mut status_code: u16 = 200;
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--url" if i + 1 < args.len() => {
                url = args[i + 1].clone();
                i += 2;
            }
            "--html-file" if i + 1 < args.len() => {
                html_file = args[i + 1].clone();
                i += 2;
            }
            "--status-code" if i + 1 < args.len() => {
                if let Ok(value) = args[i + 1].parse::<u16>() {
                    status_code = value;
                }
                i += 2;
            }
            unknown => {
                eprintln!("unknown anti-bot profile argument: {unknown}");
                return 2;
            }
        }
    }
    let (html, resolved_url) = match load_html_input(&url, &html_file) {
        Ok(value) => value,
        Err(err) => {
            eprintln!("{err}");
            return 2;
        }
    };
    let handler = AntiBotHandler::new();
    let blocked = handler.is_blocked(&html, status_code);
    let level = if blocked { "medium" } else { "low" };
    let signals = local_antibot_signals(&html, status_code);
    println!(
        "{}",
        serde_json::to_string_pretty(&serde_json::json!({
            "command": "anti-bot profile",
            "runtime": "rust",
            "url": resolved_url,
            "blocked": blocked,
            "status_code": status_code,
            "level": level,
            "signals": signals,
            "fingerprint": handler.generate_fingerprint()
        }))
        .unwrap_or_default()
    );
    if blocked {
        1
    } else {
        0
    }
}

fn load_html_input(url: &str, html_file: &str) -> Result<(String, String), String> {
    if !html_file.trim().is_empty() {
        let html = fs::read_to_string(html_file)
            .map_err(|err| format!("failed to read html file: {err}"))?;
        return Ok((html, url.to_string()));
    }
    if url.trim().is_empty() {
        return Err("anti-bot/node-reverse profile requires --url or --html-file".to_string());
    }
    let response =
        reqwest::blocking::get(url).map_err(|err| format!("failed to fetch url: {err}"))?;
    let text = response
        .text()
        .map_err(|err| format!("failed to read response body: {err}"))?;
    Ok((text, url.to_string()))
}

fn local_antibot_signals(html: &str, status_code: u16) -> Vec<String> {
    let lower = html.to_ascii_lowercase();
    let mut signals = Vec::new();
    if lower.contains("captcha") {
        signals.push("captcha".to_string());
    }
    if lower.contains("cf-ray") || lower.contains("just a moment") {
        signals.push("vendor:cloudflare".to_string());
    }
    if lower.contains("datadome") {
        signals.push("vendor:datadome".to_string());
    }
    if lower.contains("akamai") {
        signals.push("vendor:akamai".to_string());
    }
    if status_code == 403 {
        signals.push("status:403".to_string());
    }
    if status_code == 429 {
        signals.push("status:429".to_string());
    }
    if signals.is_empty() {
        signals.push("clear".to_string());
    }
    signals
}

fn local_site_profile_payload(url: &str, html: &str) -> serde_json::Value {
    let lower = html.to_ascii_lowercase();
    let compact = lower.replace(' ', "");
    let url_lower = url.to_ascii_lowercase();
    let site_family = resolve_local_site_family(&url_lower);
    let has_search_query = ["/search", "search?", "keyword=", "q=", "query=", "wd="]
        .iter()
        .any(|token| url_lower.contains(token));
    let page_signals = serde_json::json!({
        "has_form": lower.contains("<form"),
        "has_pagination": lower.contains("next") || lower.contains("page=") || lower.contains("pagination") || html.contains("下一页"),
        "has_list": lower.contains("<li") || lower.contains("<ul") || lower.contains("<ol") || lower.contains("product-list") || lower.contains("goods-list") || lower.contains("sku-item"),
        "has_detail": lower.contains("<article") || lower.contains("<h1"),
        "has_captcha": lower.contains("captcha") || lower.contains("verify") || lower.contains("human verification") || html.contains("滑块") || html.contains("验证码"),
        "has_price": lower.contains("price") || lower.contains("\"price\"") || html.contains("￥") || html.contains("¥") || html.contains("价格"),
        "has_search": has_search_query || lower.contains("type=\"search\"") || html.contains("搜索") || lower.contains("search-input"),
        "has_login": lower.contains("type=\"password\"") || lower.contains("sign in") || lower.contains("signin") || html.contains("登录"),
        "has_hydration": lower.contains("__next_data__") || lower.contains("__next_f") || lower.contains("__nuxt__") || lower.contains("__apollo_state__") || lower.contains("__initial_state__") || lower.contains("__preloaded_state__") || lower.contains("window.__initial_data__"),
        "has_api_bootstrap": lower.contains("__initial_state__") || lower.contains("__preloaded_state__") || lower.contains("__next_data__") || lower.contains("__apollo_state__") || lower.contains("application/json") || lower.contains("window.__initial_data__"),
        "has_infinite_scroll": lower.contains("load more") || lower.contains("infinite") || lower.contains("intersectionobserver") || lower.contains("onscroll") || lower.contains("virtual-list") || html.contains("加载更多"),
        "has_graphql": lower.contains("graphql"),
        "has_reviews": lower.contains("review") || html.contains("评价") || lower.contains("comments"),
        "has_product_schema": compact.contains("\"@type\":\"product\"") || compact.contains("\"@type\":\"offer\""),
        "has_cart": lower.contains("add to cart") || html.contains("购物车") || lower.contains("buy-now") || html.contains("立即购买"),
        "has_sku": lower.contains("sku") || html.contains("商品编号") || url_lower.contains("item.jd.com") || url_lower.contains("/item.htm"),
        "has_image": lower.contains("<img") || lower.contains("og:image")
    });
    let crawler_type = resolve_local_crawler_type(&page_signals, &url_lower);
    let page_type = match crawler_type.as_str() {
        "static_listing" | "search_results" | "ecommerce_search" | "infinite_scroll_listing" => "list",
        "static_detail" | "ecommerce_detail" => "detail",
        _ if page_signals["has_list"].as_bool() == Some(true) && page_signals["has_detail"].as_bool() != Some(true) => "list",
        _ if page_signals["has_detail"].as_bool() == Some(true) => "detail",
        _ => "generic",
    };
    let mut candidate_fields = Vec::new();
    for (token, field) in [
        ("<title", "title"),
        ("price", "price"),
        ("author", "author"),
        ("date", "date"),
        ("shop", "shop"),
        ("seller", "shop"),
        ("description", "description"),
    ] {
        if lower.contains(token) {
            candidate_fields.push(field);
        }
    }
    if page_signals["has_sku"].as_bool() == Some(true) {
        candidate_fields.push("sku");
    }
    if page_signals["has_reviews"].as_bool() == Some(true) {
        candidate_fields.push("rating");
    }
    if page_signals["has_search"].as_bool() == Some(true) {
        candidate_fields.push("keyword");
    }
    if page_signals["has_image"].as_bool() == Some(true) {
        candidate_fields.push("image");
    }
    candidate_fields.sort();
    candidate_fields.dedup();
    let anti_bot_signals = local_antibot_signals(html, 200);
    let risk_level = if anti_bot_signals
        .iter()
        .any(|item| item == "captcha" || item == "vendor:cloudflare")
        || page_signals["has_captcha"].as_bool() == Some(true)
    {
        "high"
    } else if url_lower.starts_with("https://")
        && (page_signals["has_form"].as_bool() == Some(true)
            || page_signals["has_login"].as_bool() == Some(true)
            || page_signals["has_hydration"].as_bool() == Some(true)
            || page_signals["has_graphql"].as_bool() == Some(true))
    {
        "medium"
    } else {
        "low"
    };
    let runner_order = resolve_local_runner_order(&crawler_type, &page_signals);
    let recommended_runtime = recommended_framework_for_profile(
        runner_order.first().map(String::as_str).unwrap_or("http"),
        page_type,
        risk_level,
    );
    serde_json::json!({
        "command": "profile-site",
        "runtime": "rust",
        "framework": "rustspider",
        "url": url,
        "page_type": page_type,
        "site_family": site_family,
        "crawler_type": crawler_type,
        "candidate_fields": candidate_fields,
        "signals": page_signals,
        "anti_bot_signals": anti_bot_signals,
        "risk_level": risk_level,
        "recommended_runtime": recommended_runtime,
        "recommended_framework": recommended_runtime,
        "runner_order": runner_order,
        "strategy_hints": resolve_local_strategy_hints(&crawler_type),
        "job_templates": resolve_local_job_templates(&crawler_type, &url_lower),
        "anti_bot_recommended": risk_level != "low",
        "node_reverse_recommended": crawler_type == "hydrated_spa" || crawler_type == "api_bootstrap" || crawler_type == "ecommerce_search"
    })
}

fn resolve_local_site_family(url_lower: &str) -> &'static str {
    if url_lower.contains("jd.com") || url_lower.contains("3.cn") {
        "jd"
    } else if url_lower.contains("taobao.com") {
        "taobao"
    } else if url_lower.contains("tmall.com") {
        "tmall"
    } else if url_lower.contains("pinduoduo.com") || url_lower.contains("yangkeduo.com") {
        "pinduoduo"
    } else if url_lower.contains("xiaohongshu.com") || url_lower.contains("xhslink.com") {
        "xiaohongshu"
    } else if url_lower.contains("douyin.com") || url_lower.contains("jinritemai.com") {
        "douyin-shop"
    } else {
        "generic"
    }
}

fn resolve_local_crawler_type(signals: &serde_json::Value, url_lower: &str) -> String {
    if signals["has_login"].as_bool() == Some(true) && signals["has_detail"].as_bool() != Some(true)
    {
        return "login_session".to_string();
    }
    if signals["has_infinite_scroll"].as_bool() == Some(true)
        && (signals["has_list"].as_bool() == Some(true) || signals["has_search"].as_bool() == Some(true))
    {
        return "infinite_scroll_listing".to_string();
    }
    if signals["has_price"].as_bool() == Some(true)
        && (signals["has_cart"].as_bool() == Some(true)
            || signals["has_sku"].as_bool() == Some(true)
            || signals["has_product_schema"].as_bool() == Some(true))
        && (signals["has_search"].as_bool() == Some(true)
            || (signals["has_list"].as_bool() == Some(true) && url_lower.contains("search")))
    {
        return "ecommerce_search".to_string();
    }
    if signals["has_price"].as_bool() == Some(true)
        && (signals["has_cart"].as_bool() == Some(true)
            || signals["has_sku"].as_bool() == Some(true)
            || signals["has_product_schema"].as_bool() == Some(true))
        && signals["has_list"].as_bool() == Some(true)
        && signals["has_detail"].as_bool() != Some(true)
    {
        return "ecommerce_search".to_string();
    }
    if signals["has_price"].as_bool() == Some(true)
        && (signals["has_cart"].as_bool() == Some(true)
            || signals["has_sku"].as_bool() == Some(true)
            || signals["has_product_schema"].as_bool() == Some(true))
    {
        return "ecommerce_detail".to_string();
    }
    if signals["has_hydration"].as_bool() == Some(true)
        && (signals["has_list"].as_bool() == Some(true)
            || signals["has_detail"].as_bool() == Some(true)
            || signals["has_search"].as_bool() == Some(true))
    {
        return "hydrated_spa".to_string();
    }
    if signals["has_api_bootstrap"].as_bool() == Some(true)
        || signals["has_graphql"].as_bool() == Some(true)
    {
        return "api_bootstrap".to_string();
    }
    if signals["has_search"].as_bool() == Some(true)
        && (signals["has_list"].as_bool() == Some(true)
            || signals["has_pagination"].as_bool() == Some(true))
    {
        return "search_results".to_string();
    }
    if signals["has_list"].as_bool() == Some(true) && signals["has_detail"].as_bool() != Some(true)
    {
        return "static_listing".to_string();
    }
    if signals["has_detail"].as_bool() == Some(true) {
        return "static_detail".to_string();
    }
    "generic_http".to_string()
}

fn resolve_local_runner_order(
    crawler_type: &str,
    signals: &serde_json::Value,
) -> Vec<String> {
    match crawler_type {
        "hydrated_spa" | "infinite_scroll_listing" | "login_session" | "ecommerce_search" => {
            vec!["browser".to_string(), "http".to_string()]
        }
        "ecommerce_detail" if signals["has_hydration"].as_bool() == Some(true) => {
            vec!["browser".to_string(), "http".to_string()]
        }
        "ecommerce_detail" => vec!["http".to_string(), "browser".to_string()],
        _ => vec!["http".to_string(), "browser".to_string()],
    }
}

fn resolve_local_strategy_hints(crawler_type: &str) -> Vec<String> {
    match crawler_type {
        "ecommerce_search" => vec![
            "start with browser rendering, capture HTML and network payloads, then promote stable fields into HTTP follow-up jobs".to_string(),
            "split listing fields from detail fields so sku and price can be validated independently".to_string(),
        ],
        "hydrated_spa" => vec![
            "render the page in browser mode and inspect embedded hydration data before DOM scraping".to_string(),
            "capture network responses and promote repeatable JSON endpoints into secondary HTTP jobs".to_string(),
        ],
        "infinite_scroll_listing" => vec![
            "drive a bounded scroll loop and stop when repeated snapshots stop changing".to_string(),
            "persist network and DOM artifacts so load-more behavior can be replayed without guessing".to_string(),
        ],
        "login_session" => vec![
            "bootstrap an authenticated session once, then reuse cookies or storage state for follow-up jobs".to_string(),
            "validate the post-login page shape before starting extraction".to_string(),
        ],
        "ecommerce_detail" => vec![
            "extract embedded product JSON and schema blocks before relying on brittle selectors".to_string(),
            "keep screenshot and HTML artifacts together for price and title regression checks".to_string(),
        ],
        "api_bootstrap" => vec![
            "inspect script tags and bootstrap JSON before adding browser interactions".to_string(),
            "extract stable JSON blobs into dedicated parsing rules so DOM churn matters less".to_string(),
        ],
        _ => vec![
            "start with plain HTTP fetch and fall back to browser only if selectors are empty".to_string(),
            "prefer stable title, meta, schema, and bootstrap data before brittle DOM selectors".to_string(),
        ],
    }
}

fn resolve_local_job_templates(crawler_type: &str, url_lower: &str) -> Vec<String> {
    let mut templates = match crawler_type {
        "hydrated_spa" => vec!["examples/crawler-types/hydrated-spa-browser.json".to_string()],
        "infinite_scroll_listing" => vec!["examples/crawler-types/infinite-scroll-browser.json".to_string()],
        "ecommerce_search" => vec!["examples/crawler-types/ecommerce-search-browser.json".to_string()],
        "ecommerce_detail" => vec![
            "examples/crawler-types/ecommerce-search-browser.json".to_string(),
            "examples/crawler-types/api-bootstrap-http.json".to_string(),
        ],
        "login_session" => vec!["examples/crawler-types/login-session-browser.json".to_string()],
        _ => vec!["examples/crawler-types/api-bootstrap-http.json".to_string()],
    };
    match resolve_local_site_family(url_lower) {
        "jd" if crawler_type == "ecommerce_detail" => {
            templates.push("examples/site-presets/jd-detail-browser.json".to_string())
        }
        "taobao" if crawler_type == "ecommerce_detail" => {
            templates.push("examples/site-presets/taobao-detail-browser.json".to_string())
        }
        "jd" => templates.push("examples/site-presets/jd-search-browser.json".to_string()),
        "taobao" => templates.push("examples/site-presets/taobao-search-browser.json".to_string()),
        "tmall" => templates.push("examples/site-presets/tmall-search-browser.json".to_string()),
        "pinduoduo" => templates.push("examples/site-presets/pinduoduo-search-browser.json".to_string()),
        "xiaohongshu" => templates.push("examples/site-presets/xiaohongshu-feed-browser.json".to_string()),
        "douyin-shop" => templates.push("examples/site-presets/douyin-shop-browser.json".to_string()),
        _ => {}
    }
    templates.sort();
    templates.dedup();
    templates
}

fn recommended_framework_for_profile(
    first_runner: &str,
    page_type: &str,
    risk_level: &str,
) -> &'static str {
    if first_runner == "browser" && risk_level == "high" {
        "java"
    } else if first_runner == "browser" {
        "python"
    } else if page_type == "list" {
        "go"
    } else {
        "python"
    }
}

fn detect_ai_mode(
    instructions: Option<&str>,
    question: Option<&str>,
    description: Option<&str>,
    schema_file: Option<&str>,
    schema_json: Option<&str>,
) -> String {
    if description.is_some_and(|value| !value.trim().is_empty()) {
        return "generate-config".to_string();
    }
    if question.is_some_and(|value| !value.trim().is_empty()) {
        return "understand".to_string();
    }
    if instructions.is_some_and(|value| !value.trim().is_empty())
        || schema_file.is_some_and(|value| !value.trim().is_empty())
        || schema_json.is_some_and(|value| !value.trim().is_empty())
    {
        return "extract".to_string();
    }
    "understand".to_string()
}

fn load_ai_schema(
    schema_file: Option<&str>,
    schema_json: Option<&str>,
) -> Result<serde_json::Value, String> {
    if let Some(path) = schema_file.filter(|value| !value.trim().is_empty()) {
        let raw =
            fs::read_to_string(path).map_err(|err| format!("failed to read schema file: {err}"))?;
        return serde_json::from_str(&raw).map_err(|err| format!("invalid schema json: {err}"));
    }
    if let Some(raw) = schema_json.filter(|value| !value.trim().is_empty()) {
        return serde_json::from_str(raw).map_err(|err| format!("invalid schema json: {err}"));
    }
    Ok(default_ai_schema())
}

fn default_ai_schema() -> serde_json::Value {
    serde_json::json!({
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "url": {"type": "string"},
            "summary": {"type": "string"}
        }
    })
}

struct AIRequestConfig {
    api_key: String,
    endpoint: String,
    model: String,
}

fn ai_request_config() -> Option<AIRequestConfig> {
    let api_key = env::var("OPENAI_API_KEY")
        .or_else(|_| env::var("AI_API_KEY"))
        .ok()
        .filter(|value| !value.trim().is_empty())?;
    let base_url = env::var("OPENAI_BASE_URL")
        .or_else(|_| env::var("AI_BASE_URL"))
        .ok()
        .filter(|value| !value.trim().is_empty())
        .unwrap_or_else(|| "https://api.openai.com/v1".to_string());
    let model = env::var("OPENAI_MODEL")
        .or_else(|_| env::var("AI_MODEL"))
        .ok()
        .filter(|value| !value.trim().is_empty())
        .unwrap_or_else(|| "gpt-5.2".to_string());
    Some(AIRequestConfig {
        api_key,
        endpoint: format!("{}/chat/completions", base_url.trim_end_matches('/')),
        model,
    })
}

fn ai_chat_completion(config: &AIRequestConfig, prompt: &str) -> Result<String, String> {
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(60))
        .build()
        .map_err(|err| format!("failed to initialize ai client: {err}"))?;
    let response = client
        .post(&config.endpoint)
        .bearer_auth(&config.api_key)
        .json(&serde_json::json!({
            "model": config.model,
            "messages": [
                {"role": "system", "content": "You are an expert web scraping assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }))
        .send()
        .map_err(|err| format!("ai request failed: {err}"))?;
    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().unwrap_or_default();
        return Err(format!("ai request failed: {status} {body}"));
    }
    let payload: serde_json::Value = response
        .json()
        .map_err(|err| format!("failed to parse ai response: {err}"))?;
    payload["choices"][0]["message"]["content"]
        .as_str()
        .map(|value| value.to_string())
        .ok_or_else(|| "ai response did not include message content".to_string())
}

fn parse_json_candidate(raw: &str) -> Result<serde_json::Value, String> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Err("ai response was empty".to_string());
    }
    if let Ok(value) = serde_json::from_str::<serde_json::Value>(trimmed) {
        return Ok(value);
    }
    let object_start = trimmed.find('{');
    let object_end = trimmed.rfind('}');
    if let (Some(start), Some(end)) = (object_start, object_end) {
        if end > start {
            if let Ok(value) = serde_json::from_str::<serde_json::Value>(&trimmed[start..=end]) {
                return Ok(value);
            }
        }
    }
    let array_start = trimmed.find('[');
    let array_end = trimmed.rfind(']');
    if let (Some(start), Some(end)) = (array_start, array_end) {
        if end > start {
            if let Ok(value) = serde_json::from_str::<serde_json::Value>(&trimmed[start..=end]) {
                return Ok(value);
            }
        }
    }
    Err("llm response was not valid JSON; used heuristic fallback".to_string())
}

fn heuristic_ai_generate_config(description: &str) -> serde_json::Value {
    let lower = description.to_ascii_lowercase();
    let mut fields = vec![
        "title".to_string(),
        "url".to_string(),
        "summary".to_string(),
    ];
    if lower.contains("price") || description.contains("价格") {
        fields.push("price".to_string());
    }
    if lower.contains("author") || description.contains("作者") {
        fields.push("author".to_string());
    }
    if lower.contains("date") || description.contains("时间") || description.contains("日期") {
        fields.push("published_at".to_string());
    }
    if lower.contains("content") || description.contains("正文") {
        fields.push("content".to_string());
    }
    let mut start_urls = vec!["https://example.com".to_string()];
    for token in description.split_whitespace() {
        let cleaned = token.trim_matches(|ch: char| " \t\r\n,.;'\"()[]{}".contains(ch));
        if cleaned.starts_with("http://") || cleaned.starts_with("https://") {
            start_urls = vec![cleaned.to_string()];
            break;
        }
    }
    serde_json::json!({
        "start_urls": start_urls,
        "rules": [
            {
                "name": "auto-generated",
                "pattern": ".*",
                "extract": fields,
                "follow_links": true
            }
        ],
        "settings": {
            "concurrency": 3,
            "max_depth": 2,
            "delay": 500
        },
        "source_description": description
    })
}

fn heuristic_ai_understand(url: &str, html: &str, question: &str) -> serde_json::Value {
    let profile = local_site_profile_payload(url, html);
    let question_text = if question.trim().is_empty() {
        "请总结页面类型、核心内容和推荐提取字段。"
    } else {
        question
    };
    serde_json::json!({
        "answer": format!(
            "页面类型={}，站点家族={}，爬虫类型={}，候选字段={:?}，风险等级={}，优先 runner={:?}。问题：{}",
            profile["page_type"].as_str().unwrap_or("generic"),
            profile["site_family"].as_str().unwrap_or("generic"),
            profile["crawler_type"].as_str().unwrap_or("generic_http"),
            profile["candidate_fields"].as_array().cloned().unwrap_or_default(),
            profile["risk_level"].as_str().unwrap_or("low"),
            profile["runner_order"].as_array().cloned().unwrap_or_default(),
            question_text
        ),
        "page_profile": profile
    })
}

fn heuristic_ai_extract(url: &str, html: &str, schema: &serde_json::Value) -> serde_json::Value {
    let properties = schema
        .get("properties")
        .and_then(|value| value.as_object())
        .cloned()
        .unwrap_or_else(|| {
            default_ai_schema()
                .get("properties")
                .and_then(|value| value.as_object())
                .cloned()
                .unwrap_or_default()
        });
    let parser = HTMLParser::new(html);
    let text = compact_ai_text(&strip_html_tags(html));
    let mut result = serde_json::Map::new();
    for (field_name, spec) in properties {
        let expected_type = spec
            .get("type")
            .and_then(|value| value.as_str())
            .unwrap_or("string");
        result.insert(
            field_name.clone(),
            heuristic_ai_field_value(&field_name, expected_type, url, &text, &parser, html),
        );
    }
    serde_json::Value::Object(result)
}

fn schema_from_candidate_fields(fields: &[String]) -> serde_json::Value {
    let mut ordered = vec![
        "title".to_string(),
        "summary".to_string(),
        "url".to_string(),
    ];
    for field in fields {
        if !ordered.contains(field) {
            ordered.push(field.clone());
        }
    }
    let mut properties = serde_json::Map::new();
    for field in ordered {
        let lower = field.to_ascii_lowercase();
        let value = if lower.contains("price")
            || lower.contains("amount")
            || lower.contains("score")
            || lower.contains("rating")
        {
            serde_json::json!({"type":"number"})
        } else if lower.contains("count") || lower.contains("total") {
            serde_json::json!({"type":"integer"})
        } else if lower.contains("images")
            || lower.contains("links")
            || lower.contains("tags")
            || lower.contains("items")
        {
            serde_json::json!({"type":"array","items":{"type":"string"}})
        } else {
            serde_json::json!({"type":"string"})
        };
        properties.insert(field, value);
    }
    serde_json::json!({"type":"object","properties": properties})
}

fn derive_domain_from_url_rust(raw: &str) -> String {
    reqwest::Url::parse(raw)
        .ok()
        .and_then(|value| value.host_str().map(|host| host.to_string()))
        .filter(|value| !value.trim().is_empty())
        .unwrap_or_else(|| "example.com".to_string())
}

fn auth_validation_status_rust(html: &str) -> (bool, Vec<String>) {
    let lower = html.to_ascii_lowercase();
    let mut indicators = Vec::new();
    if lower.contains("type=\"password\"") || lower.contains("type='password'") {
        indicators.push("password-input".to_string());
    }
    if lower.contains("login")
        || lower.contains("sign in")
        || lower.contains("signin")
        || lower.contains("登录")
    {
        indicators.push("login-marker".to_string());
    }
    (indicators.is_empty(), indicators)
}

fn build_rust_ai_blueprint(
    resolved_url: &str,
    spider_name: &str,
    profile: &serde_json::Value,
    schema: &serde_json::Value,
    html: &str,
) -> serde_json::Value {
    let candidate_fields = profile["candidate_fields"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    let runner_order = profile["runner_order"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    let strategy_hints = profile["strategy_hints"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    let job_templates = profile["job_templates"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    let mut field_names = schema["properties"]
        .as_object()
        .map(|value| value.keys().cloned().collect::<Vec<_>>())
        .unwrap_or_default();
    field_names.sort();
    let lower = html.to_ascii_lowercase();
    let crawler_type = profile["crawler_type"]
        .as_str()
        .unwrap_or("generic_http")
        .to_string();
    let anti_bot_runner = runner_order
        .first()
        .and_then(|value| value.as_str())
        .unwrap_or("http");
    serde_json::json!({
        "version": 1,
        "spider_name": spider_name,
        "resolved_url": resolved_url,
        "page_type": profile["page_type"].clone(),
        "site_family": profile["site_family"].clone(),
        "crawler_type": crawler_type,
        "candidate_fields": candidate_fields,
        "schema": schema,
        "extraction_prompt": format!("请从页面中提取以下字段，并只返回 JSON：{}。缺失字段返回空字符串或空数组。", field_names.join(", ")),
        "runner_order": runner_order,
        "strategy_hints": strategy_hints,
        "job_templates": job_templates,
        "follow_rules": [
            {
                "name": "same-domain-content",
                "enabled": true,
                "description": "优先跟进同域详情页和内容页链接"
            }
        ],
        "pagination": {
            "enabled": matches!(profile["page_type"].as_str(), Some("list") | Some("generic")) || lower.contains("rel=\"next\"") || lower.contains("pagination") || lower.contains("page=") || lower.contains("next page") || lower.contains("下一页"),
            "strategy": if crawler_type == "infinite_scroll_listing" { "bounded scroll batches with repeated DOM and network snapshot checks" } else { "follow next page or numbered pagination links" },
            "selectors": ["a[rel='next']", ".next", ".pagination a"]
        },
        "authentication": {
            "required": lower.contains("type=\"password\"") || lower.contains("type='password'") || lower.contains("login") || lower.contains("sign in") || lower.contains("signin") || lower.contains("登录"),
            "strategy": if lower.contains("type=\"password\"") || lower.contains("type='password'") || lower.contains("login") || lower.contains("sign in") || lower.contains("signin") || lower.contains("登录") { "capture session/login flow before crawl" } else { "not required" }
        },
        "javascript_runtime": {
            "required": lower.contains("__next_data__") || lower.contains("window.__") || lower.contains("webpack") || lower.contains("fetch(") || lower.contains("graphql") || lower.contains("xhr") || crawler_type == "hydrated_spa" || crawler_type == "infinite_scroll_listing" || crawler_type == "ecommerce_search",
            "recommended_runner": if anti_bot_runner == "browser" || lower.contains("__next_data__") || lower.contains("window.__") || lower.contains("webpack") || lower.contains("fetch(") || lower.contains("graphql") || lower.contains("xhr") { "browser" } else { "http" }
        },
        "reverse_engineering": {
            "required": lower.contains("crypto") || lower.contains("signature") || lower.contains("token") || lower.contains("webpack") || lower.contains("obfusc") || lower.contains("encrypt") || lower.contains("decrypt"),
            "notes": if lower.contains("crypto") || lower.contains("signature") || lower.contains("token") || lower.contains("webpack") || lower.contains("obfusc") || lower.contains("encrypt") || lower.contains("decrypt") { "inspect network/API signing or obfuscated scripts" } else { "not required" }
        },
        "anti_bot_strategy": {
            "risk_level": profile["risk_level"].clone(),
            "signals": profile["signals"].clone(),
            "recommended_runner": anti_bot_runner,
            "notes": "高风险页面建议先走浏览器模式并降低抓取速率"
        }
    })
}

fn render_rust_ai_spider_template(name: &str, domain: &str) -> String {
    format!(
        r##"// scrapy: url=https://{domain}
use std::sync::Arc;

use rustspider::extractor::AIExtractor;
use rustspider::scrapy::project as projectruntime;
use rustspider::scrapy::{{Item, Output, Response, Spider}};

fn ai_fields(response: &Response, assets: &projectruntime::AIProjectAssets) -> std::collections::HashMap<String, String> {{
    let mut data = std::collections::HashMap::from([
        ("title".to_string(), response.css("title").get().unwrap_or_default()),
        (
            "summary".to_string(),
            response
                .xpath("//meta[@name='description']/@content")
                .get()
                .unwrap_or_default(),
        ),
        ("url".to_string(), response.url.clone()),
    ]);
    if let Ok(api_key) = std::env::var("OPENAI_API_KEY").or_else(|_| std::env::var("AI_API_KEY")) {{
        if !api_key.trim().is_empty() {{
            let extractor = AIExtractor::openai(&api_key);
            let prompt = if assets.extraction_prompt.trim().is_empty() {{ "提取标题、摘要和 URL" }} else {{ assets.extraction_prompt.as_str() }};
            let payload = format!("{{}}\\n\\n页面内容：\\n{{}}", prompt, response.text);
            if let Ok(extracted) = extractor.extract(&payload, &assets.schema.to_string()) {{
                for (key, value) in extracted {{
                    let text = value
                        .as_str()
                        .map(|item| item.to_string())
                        .unwrap_or_else(|| value.to_string());
                    data.insert(key, text);
                }}
            }}
        }}
    }}
    data
}}

pub fn make_{name}_spider() -> Spider {{
    let assets = Arc::new(projectruntime::load_ai_project_assets(std::path::Path::new(".")));
    let parse: Arc<dyn Fn(&Response) -> Vec<Output> + Send + Sync> = Arc::new_cyclic(|weak| {{
        let assets = Arc::clone(&assets);
        Arc::new(move |response: &Response| {{
            let fields = ai_fields(response, &assets);
            let mut item = Item::new().set("framework", "rustspider-ai");
            for (key, value) in fields {{
                item = item.set(&key, value);
            }}
            let mut outputs = vec![Output::Item(item)];
            for request in projectruntime::collect_ai_pagination_requests(response, weak.upgrade(), &assets) {{
                outputs.push(Output::Request(request));
            }}
            outputs
        }})
    }});
    let spider = Spider::new("{name}", parse).add_start_url("https://{domain}");
    projectruntime::apply_ai_start_meta(spider, &assets)
}}

pub fn register() {{
    projectruntime::register_spider("{name}", make_{name}_spider);
}}
"##,
        name = name,
        domain = domain
    )
}

fn heuristic_ai_field_value(
    field_name: &str,
    expected_type: &str,
    url: &str,
    text: &str,
    parser: &HTMLParser,
    html: &str,
) -> serde_json::Value {
    let lower = field_name.to_ascii_lowercase();
    if lower.contains("title") || lower.contains("headline") {
        return serde_json::Value::String(first_non_empty_string(&[
            extract_meta_content(html, "property", "og:title"),
            parser.title().unwrap_or_default(),
            extract_tag_content(html, "h1"),
        ]));
    }
    if lower == "url" || lower.contains("link") {
        return if expected_type == "array" {
            serde_json::json!([url])
        } else {
            serde_json::Value::String(url.to_string())
        };
    }
    if lower.contains("summary") || lower.contains("description") || lower == "desc" {
        return serde_json::Value::String(first_non_empty_string(&[
            extract_meta_content(html, "name", "description"),
            extract_meta_content(html, "property", "og:description"),
            truncate_ai_text(text, 220),
        ]));
    }
    if lower.contains("content") || lower.contains("body") || lower == "text" {
        return serde_json::Value::String(truncate_ai_text(text, 1200));
    }
    if lower.contains("author") {
        return serde_json::Value::String(first_non_empty_string(&[
            extract_meta_content(html, "name", "author"),
            extract_meta_content(html, "property", "article:author"),
        ]));
    }
    if lower.contains("date") || lower.contains("time") || lower.contains("published") {
        return serde_json::Value::String(first_non_empty_string(&[
            extract_meta_content(html, "property", "article:published_time"),
            extract_meta_content(html, "name", "pubdate"),
            extract_attribute(html, "time", "datetime"),
        ]));
    }
    if lower.contains("image") || lower.contains("thumbnail") || lower.contains("cover") {
        return serde_json::Value::String(first_non_empty_string(&[
            extract_meta_content(html, "property", "og:image"),
            extract_attribute(html, "img", "src"),
        ]));
    }
    if lower.contains("price") {
        return serde_json::Value::String(find_token(text, &["¥", "￥", "$", "usd", "rmb"]));
    }
    if expected_type == "array" {
        serde_json::json!([])
    } else {
        serde_json::Value::String(String::new())
    }
}

fn compact_ai_text(value: &str) -> String {
    value.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn truncate_ai_text(value: &str, limit: usize) -> String {
    let compact = compact_ai_text(value);
    if compact.len() <= limit {
        compact
    } else {
        format!("{}...", compact[..limit].trim_end())
    }
}

fn truncate_ai_content(value: &str, limit: usize) -> String {
    if value.len() <= limit {
        value.to_string()
    } else {
        value[..limit].to_string()
    }
}

fn strip_html_tags(input: &str) -> String {
    let mut output = String::new();
    let mut in_tag = false;
    for ch in input.chars() {
        match ch {
            '<' => in_tag = true,
            '>' => {
                in_tag = false;
                output.push(' ');
            }
            _ if !in_tag => output.push(ch),
            _ => {}
        }
    }
    output
}

fn extract_tag_content(html: &str, tag: &str) -> String {
    let lower = html.to_ascii_lowercase();
    let open = format!("<{}", tag.to_ascii_lowercase());
    let close = format!("</{}>", tag.to_ascii_lowercase());
    if let Some(start) = lower.find(&open) {
        let after_open = &html[start..];
        if let Some(content_start) = after_open.find('>') {
            let content = &after_open[content_start + 1..];
            let lower_content = &lower[start + content_start + 1..];
            if let Some(end) = lower_content.find(&close) {
                return compact_ai_text(&content[..end]);
            }
        }
    }
    String::new()
}

fn extract_meta_content(html: &str, attr: &str, name: &str) -> String {
    let lower = html.to_ascii_lowercase();
    let needle = format!(
        r#"{attr}="{name}""#,
        attr = attr.to_ascii_lowercase(),
        name = name.to_ascii_lowercase()
    );
    if let Some(index) = lower.find(&needle) {
        let tail = &html[index..];
        let lower_tail = &lower[index..];
        if let Some(content_index) = lower_tail.find(r#"content=""#) {
            let value_start = content_index + 9;
            if let Some(value_end) = tail[value_start..].find('"') {
                return tail[value_start..value_start + value_end]
                    .trim()
                    .to_string();
            }
        }
    }
    String::new()
}

fn extract_attribute(html: &str, tag: &str, attr: &str) -> String {
    let lower = html.to_ascii_lowercase();
    let open = format!("<{}", tag.to_ascii_lowercase());
    if let Some(index) = lower.find(&open) {
        let tail = &html[index..];
        let lower_tail = &lower[index..];
        let needle = format!(r#"{attr}=""#, attr = attr.to_ascii_lowercase());
        if let Some(value_index) = lower_tail.find(&needle) {
            let start = value_index + needle.len();
            if let Some(end) = tail[start..].find('"') {
                return tail[start..start + end].trim().to_string();
            }
        }
    }
    String::new()
}

fn first_non_empty_string(values: &[String]) -> String {
    values
        .iter()
        .find(|value| !value.trim().is_empty())
        .cloned()
        .unwrap_or_default()
}

fn find_token(text: &str, tokens: &[&str]) -> String {
    for item in text.to_ascii_lowercase().split_whitespace() {
        if tokens
            .iter()
            .any(|token| item.contains(&token.to_ascii_lowercase()))
        {
            return item
                .trim_matches(|ch: char| ".,;:!?()[]{}\"'".contains(ch))
                .to_string();
        }
    }
    String::new()
}

fn extract_sitemap_urls(content: &str) -> Vec<String> {
    let mut urls = Vec::new();
    let mut remaining = content;
    loop {
        let Some(start) = remaining.find("<loc>") else {
            break;
        };
        let tail = &remaining[start + 5..];
        let Some(end) = tail.find("</loc>") else {
            break;
        };
        let value = tail[..end].trim();
        if !value.is_empty() {
            urls.push(value.to_string());
        }
        remaining = &tail[end + 6..];
    }
    urls
}

fn validate_scrapy_plugin_manifest(path: &PathBuf) -> Result<(), String> {
    let raw = fs::read_to_string(path).map_err(|err| err.to_string())?;
    let payload: serde_json::Value =
        serde_json::from_str(&raw).map_err(|err| format!("invalid plugin manifest json: {err}"))?;
    let object = payload
        .as_object()
        .ok_or_else(|| "plugin manifest must be an object".to_string())?;
    if let Some(version) = object.get("version") {
        let number = version
            .as_i64()
            .ok_or_else(|| "plugin manifest version must be an integer >= 1".to_string())?;
        if number < 1 {
            return Err("plugin manifest version must be an integer >= 1".to_string());
        }
    }
    let items = object
        .get("plugins")
        .and_then(|value| value.as_array())
        .ok_or_else(|| "plugin manifest must contain a plugins array".to_string())?;
    for item in items {
        match item {
            serde_json::Value::String(name) => {
                if name.trim().is_empty() {
                    return Err("plugin name must be a non-empty string".to_string());
                }
            }
            serde_json::Value::Object(object) => {
                let name = object
                    .get("name")
                    .and_then(|value| value.as_str())
                    .ok_or_else(|| "plugin object must include a non-empty name".to_string())?;
                if name.trim().is_empty() {
                    return Err("plugin object must include a non-empty name".to_string());
                }
                if let Some(enabled) = object.get("enabled") {
                    if !enabled.is_boolean() {
                        return Err("plugin enabled must be a boolean".to_string());
                    }
                }
                if let Some(priority) = object.get("priority") {
                    if priority.as_i64().is_none() {
                        return Err("plugin priority must be an integer".to_string());
                    }
                }
                if let Some(config) = object.get("config") {
                    if !config.is_object() {
                        return Err("plugin config must be an object".to_string());
                    }
                }
            }
            _ => return Err("plugin entries must be strings or objects".to_string()),
        }
    }
    Ok(())
}

fn discover_sitemap_targets(seed_url: &str, sitemap: &SitemapSection) -> Vec<String> {
    let source = if !sitemap.url.trim().is_empty() {
        sitemap.url.clone()
    } else if !seed_url.trim().is_empty() {
        format!("{}/sitemap.xml", seed_url.trim_end_matches('/'))
    } else {
        return Vec::new();
    };
    let response = match reqwest::blocking::get(&source) {
        Ok(response) => response,
        Err(_) => return Vec::new(),
    };
    let content = match response.text() {
        Ok(content) => content,
        Err(_) => return Vec::new(),
    };
    let mut urls = extract_sitemap_urls(&content);
    if sitemap.max_urls > 0 && urls.len() > sitemap.max_urls {
        urls.truncate(sitemap.max_urls);
    }
    urls
}

fn merge_unique_targets(base: Vec<String>, extra: Vec<String>) -> Vec<String> {
    let mut seen = std::collections::HashSet::new();
    let mut merged = Vec::new();
    for target in base.into_iter().chain(extra.into_iter()) {
        if target.trim().is_empty() || seen.contains(&target) {
            continue;
        }
        seen.insert(target.clone());
        merged.push(target);
    }
    merged
}

fn handle_export(args: &[String]) -> i32 {
    let mut input: Option<String> = None;
    let mut format = "json".to_string();
    let mut output: Option<String> = None;
    let mut i = 0usize;
    while i < args.len() {
        match args[i].as_str() {
            "--input" => {
                if let Some(value) = args.get(i + 1) {
                    input = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --input");
                    return 2;
                }
            }
            "--format" => {
                if let Some(value) = args.get(i + 1) {
                    format = value.clone();
                    i += 2;
                } else {
                    eprintln!("missing value for --format");
                    return 2;
                }
            }
            "--output" => {
                if let Some(value) = args.get(i + 1) {
                    output = Some(value.clone());
                    i += 2;
                } else {
                    eprintln!("missing value for --output");
                    return 2;
                }
            }
            unknown => {
                eprintln!("unknown export argument: {unknown}");
                return 2;
            }
        }
    }

    let Some(input) = input else {
        eprintln!("export requires --input");
        return 2;
    };
    let Some(output) = output else {
        eprintln!("export requires --output");
        return 2;
    };

    let raw = match fs::read_to_string(&input) {
        Ok(content) => content,
        Err(err) => {
            eprintln!("failed to read input: {err}");
            return 1;
        }
    };

    let value: serde_json::Value = match serde_json::from_str(&raw) {
        Ok(value) => value,
        Err(err) => {
            eprintln!("failed to parse input json: {err}");
            return 1;
        }
    };
    let items = value
        .get("items")
        .or_else(|| value.get("data"))
        .cloned()
        .unwrap_or(value);

    let records = items
        .as_array()
        .cloned()
        .unwrap_or_default()
        .into_iter()
        .map(|item| rustspider::ExportData {
            title: item
                .get("title")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string(),
            url: item
                .get("url")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string(),
            snippet: item
                .get("snippet")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string(),
            source: item
                .get("source")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string(),
            time: item
                .get("time")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string(),
        })
        .collect::<Vec<_>>();

    let output_path = PathBuf::from(&output);
    let export_dir = output_path
        .parent()
        .unwrap_or(PathBuf::from(".").as_path())
        .to_path_buf();
    let filename = output_path
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("export.json");
    let exporter = rustspider::Exporter::new(export_dir.to_string_lossy().as_ref());
    let result = match format.as_str() {
        "json" => exporter.export_json(&records, filename),
        "jsonl" => exporter.export_jsonl(&records, filename),
        "csv" => exporter.export_csv(&records, filename),
        "md" => exporter.export_markdown(&records, filename),
        other => Err(format!("unsupported export format: {other}")),
    };
    match result {
        Ok(path) => {
            println!("exported: {path}");
            0
        }
        Err(err) => {
            eprintln!("export failed: {err}");
            1
        }
    }
}

#[cfg(test)]
mod contract_tests {
    use super::*;

    #[test]
    fn default_contract_config_uses_shared_paths() {
        let cfg = default_contract_config();
        assert_eq!(cfg.runtime, "rust");
        assert_eq!(cfg.storage.checkpoint_dir, "artifacts/checkpoints");
        assert_eq!(cfg.storage.dataset_dir, "artifacts/datasets");
        assert_eq!(cfg.storage.export_dir, "artifacts/exports");
        assert_eq!(cfg.anti_bot.profile, "chrome-stealth");
        assert_eq!(cfg.node_reverse.base_url, "http://localhost:3000");
        assert_eq!(
            cfg.doctor.network_targets,
            vec!["https://example.com".to_string()]
        );
    }

    #[test]
    fn config_init_writes_shared_contract() {
        let temp_dir = std::env::temp_dir().join("rustspider-contract-test");
        let _ = fs::create_dir_all(&temp_dir);
        let output = temp_dir.join("spider-framework.yaml");
        let yaml = serde_yaml::to_string(&default_contract_config()).expect("yaml should render");
        fs::write(&output, yaml).expect("config should be written");
        let content = fs::read_to_string(&output).expect("config should be readable");
        assert!(content.contains("runtime: rust"));
        assert!(content.contains("checkpoint_dir: artifacts/checkpoints"));
        assert!(content.contains("network_targets"));
        assert!(content.contains("anti_bot:"));
        assert!(content.contains("node_reverse:"));
        let _ = fs::remove_file(output);
    }

    #[test]
    fn prepare_browser_artifact_paths_creates_directories() {
        let dir = std::env::temp_dir().join("rustspider-browser-artifacts");
        let screenshot = dir.join("page.png");
        let html = dir.join("page.html");
        let result = prepare_browser_artifact_paths(
            screenshot.to_string_lossy().as_ref(),
            html.to_string_lossy().as_ref(),
        );
        assert!(result.is_ok());
        assert!(dir.exists());
    }

    #[test]
    fn persist_browser_graph_artifact_writes_graph_json() {
        let job = RuntimeJobSpec {
            name: "graph-job".to_string(),
            runtime: "browser".to_string(),
            priority: Some(1),
            target: RuntimeTargetSection {
                url: "https://example.com".to_string(),
                method: "GET".to_string(),
                headers: HashMap::new(),
                cookies: HashMap::new(),
                body: None,
                proxy: None,
                timeout_ms: None,
                allowed_domains: Vec::new(),
            },
            extract: Vec::new(),
            output: RuntimeOutputSection {
                format: "json".to_string(),
                path: None,
                directory: Some(
                    std::env::temp_dir()
                        .join("rustspider-graph-artifacts")
                        .to_string_lossy()
                        .to_string(),
                ),
                artifact_prefix: Some("graph-job".to_string()),
            },
            resources: None,
            browser: None,
            anti_bot: None,
            policy: None,
            schedule: None,
            metadata: None,
        };

        let path = persist_browser_graph_artifact(&job, "<html><head><title>Rust CLI Graph</title></head><body><a href='https://example.com'>A</a></body></html>", "graph")
            .expect("graph artifact should be written");
        assert!(PathBuf::from(path).exists());
    }

    #[test]
    fn persist_runtime_graph_artifact_writes_graph_json() {
        let job = RuntimeJobSpec {
            name: "runtime-graph-job".to_string(),
            runtime: "http".to_string(),
            priority: Some(1),
            target: RuntimeTargetSection {
                url: "https://example.com".to_string(),
                method: "GET".to_string(),
                headers: HashMap::new(),
                cookies: HashMap::new(),
                body: None,
                proxy: None,
                timeout_ms: None,
                allowed_domains: Vec::new(),
            },
            extract: Vec::new(),
            output: RuntimeOutputSection {
                format: "json".to_string(),
                path: None,
                directory: Some(
                    std::env::temp_dir()
                        .join("rustspider-runtime-graph-artifacts")
                        .to_string_lossy()
                        .to_string(),
                ),
                artifact_prefix: Some("runtime-graph-job".to_string()),
            },
            resources: None,
            browser: None,
            anti_bot: None,
            policy: None,
            schedule: None,
            metadata: None,
        };

        let path = persist_runtime_graph_artifact(
            &job,
            "<html><head><title>Rust Runtime Graph</title></head><body><a href='https://example.com'>A</a></body></html>",
            "graph",
        )
        .expect("runtime graph artifact should be written");
        assert!(PathBuf::from(path).exists());
    }

    #[test]
    fn playwright_helper_script_exists() {
        assert!(playwright_helper_script().exists());
    }

    #[test]
    fn native_playwright_helper_script_exists() {
        assert!(native_playwright_helper_script().exists());
    }

    #[test]
    fn load_contract_config_rejects_runtime_mismatch() {
        let temp_dir = std::env::temp_dir().join("rustspider-invalid-runtime");
        let _ = fs::create_dir_all(&temp_dir);
        let path = temp_dir.join("wrong-runtime.yaml");
        fs::write(
            &path,
            "version: 1\nproject:\n  name: bad-runtime\nruntime: python\ncrawl:\n  urls:\n    - https://example.com\n  concurrency: 5\n  max_requests: 100\n  max_depth: 3\n  timeout_seconds: 30\nsitemap:\n  enabled: false\n  url: https://example.com/sitemap.xml\n  max_urls: 50\nbrowser:\n  enabled: true\n  headless: true\n  timeout_seconds: 30\n  user_agent: ''\n  screenshot_path: artifacts/browser/page.png\n  html_path: artifacts/browser/page.html\nanti_bot:\n  enabled: true\n  profile: chrome-stealth\n  proxy_pool: local\n  session_mode: sticky\n  stealth: true\n  challenge_policy: browser\n  captcha_provider: 2captcha\n  captcha_api_key: ''\nnode_reverse:\n  enabled: true\n  base_url: http://localhost:3000\nmiddleware:\n  user_agent_rotation: true\n  respect_robots_txt: true\n  min_request_interval_ms: 200\npipeline:\n  console: true\n  dataset: true\n  jsonl_path: artifacts/exports/results.jsonl\nauto_throttle:\n  enabled: true\n  start_delay_ms: 200\n  max_delay_ms: 5000\n  target_response_time_ms: 2000\nplugins:\n  enabled: true\n  manifest: contracts/integration-catalog.json\nstorage:\n  checkpoint_dir: artifacts/checkpoints\n  dataset_dir: artifacts/datasets\n  export_dir: artifacts/exports\nexport:\n  format: json\n  output_path: artifacts/exports/results.json\n",
        )
        .expect("config should be written");

        let explicit = path.to_string_lossy().to_string();
        let result = load_contract_config(Some(&explicit));
        assert!(result.is_err());
        assert!(result.err().unwrap().contains("runtime mismatch"));

        let _ = fs::remove_file(path);
    }

    #[test]
    fn load_contract_config_backfills_missing_browser_auth_artifact_fields() {
        let temp_dir = std::env::temp_dir().join("rustspider-legacy-browser-config");
        let _ = fs::create_dir_all(&temp_dir);
        let path = temp_dir.join("legacy-browser.yaml");
        fs::write(
            &path,
            "version: 1\nproject:\n  name: legacy-browser\nruntime: rust\ncrawl:\n  urls:\n    - https://example.com\n  concurrency: 5\n  max_requests: 100\n  max_depth: 3\n  timeout_seconds: 30\nsitemap:\n  enabled: false\n  url: https://example.com/sitemap.xml\n  max_urls: 50\nbrowser:\n  enabled: true\n  headless: true\n  timeout_seconds: 30\n  user_agent: ''\n  screenshot_path: artifacts/browser/page.png\n  html_path: artifacts/browser/page.html\nanti_bot:\n  enabled: true\n  profile: chrome-stealth\n  proxy_pool: local\n  session_mode: sticky\n  stealth: true\n  challenge_policy: browser\n  captcha_provider: 2captcha\n  captcha_api_key: ''\nnode_reverse:\n  enabled: true\n  base_url: http://localhost:3000\nmiddleware:\n  user_agent_rotation: true\n  respect_robots_txt: true\n  min_request_interval_ms: 200\npipeline:\n  console: true\n  dataset: true\n  jsonl_path: artifacts/exports/results.jsonl\nauto_throttle:\n  enabled: true\n  start_delay_ms: 200\n  max_delay_ms: 5000\n  target_response_time_ms: 2000\nplugins:\n  enabled: true\n  manifest: contracts/integration-catalog.json\nstorage:\n  checkpoint_dir: artifacts/checkpoints\n  dataset_dir: artifacts/datasets\n  export_dir: artifacts/exports\nexport:\n  format: json\n  output_path: artifacts/exports/results.json\n",
        )
        .expect("config should be written");

        let explicit = path.to_string_lossy().to_string();
        let result =
            load_contract_config(Some(&explicit)).expect("legacy browser config should load");

        assert_eq!(result.browser.storage_state_file, "");
        assert_eq!(result.browser.cookies_file, "");
        assert_eq!(result.browser.auth_file, "");

        let _ = fs::remove_file(path);
    }

    #[test]
    fn validate_contract_config_rejects_unsupported_declarative_component() {
        let mut cfg = default_contract_config();
        cfg.scrapy.pipelines = vec!["unknown-component".to_string()];

        let result = validate_contract_config(cfg, "rust");
        assert!(result.is_err());
        assert!(result
            .err()
            .unwrap()
            .contains("scrapy.pipelines contains unsupported component"));
    }
}
