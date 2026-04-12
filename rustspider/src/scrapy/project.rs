use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::path::Path;
use std::sync::{Arc, Mutex, OnceLock};

use serde::Deserialize;
use serde_json::json;
use serde_json::Value;

use super::{
    Callback, CrawlerProcess, FeedExporter, Item, Output, PluginHandle, Request, Response, Spider,
};
use crate::parser::HTMLParser;

pub type SpiderFactory = fn() -> Spider;
pub type PluginFactory = fn() -> PluginHandle;

#[derive(Clone, Default)]
pub struct PluginSpec {
    pub name: String,
    pub enabled: bool,
    pub priority: i32,
    pub config: BTreeMap<String, Value>,
}

#[derive(Clone, Default, Deserialize)]
struct ArtifactProjectConfig {
    #[serde(default)]
    scrapy: ArtifactScrapyConfig,
    #[serde(default)]
    node_reverse: ArtifactNodeReverseConfig,
}

#[derive(Clone, Default, Deserialize)]
struct ArtifactScrapyConfig {
    #[serde(default)]
    plugins: Vec<String>,
    #[serde(default)]
    pipelines: Vec<String>,
    #[serde(default)]
    spider_middlewares: Vec<String>,
    #[serde(default)]
    downloader_middlewares: Vec<String>,
    #[serde(default)]
    component_config: BTreeMap<String, Value>,
}

#[derive(Clone, Default, Deserialize)]
struct ArtifactNodeReverseConfig {
    #[serde(default)]
    base_url: String,
}

#[derive(Clone, Default)]
pub struct AIProjectAssets {
    pub schema: Value,
    pub blueprint: Value,
    pub extraction_prompt: String,
    pub pagination_enabled: bool,
    pub pagination_selectors: Vec<String>,
    pub recommended_runner: String,
    pub request_headers: BTreeMap<String, String>,
    pub auth_required: bool,
    pub storage_state_file: String,
    pub cookies_file: String,
}

fn spider_registry() -> &'static Mutex<BTreeMap<String, SpiderFactory>> {
    static REGISTRY: OnceLock<Mutex<BTreeMap<String, SpiderFactory>>> = OnceLock::new();
    REGISTRY.get_or_init(|| Mutex::new(BTreeMap::new()))
}

fn plugin_registry() -> &'static Mutex<BTreeMap<String, PluginFactory>> {
    static REGISTRY: OnceLock<Mutex<BTreeMap<String, PluginFactory>>> = OnceLock::new();
    REGISTRY.get_or_init(|| Mutex::new(BTreeMap::new()))
}

pub fn load_ai_project_assets(project_root: &Path) -> AIProjectAssets {
    let mut assets = AIProjectAssets {
        schema: json!({
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "url": {"type": "string"}
            }
        }),
        blueprint: Value::Null,
        extraction_prompt: "提取标题、摘要和 URL".to_string(),
        pagination_enabled: false,
        pagination_selectors: Vec::new(),
        recommended_runner: "http".to_string(),
        request_headers: BTreeMap::new(),
        auth_required: false,
        storage_state_file: String::new(),
        cookies_file: String::new(),
    };

    if let Ok(raw) = fs::read_to_string(project_root.join("ai-schema.json")) {
        if let Ok(value) = serde_json::from_str::<Value>(&raw) {
            assets.schema = value;
        }
    }
    if let Ok(raw) = fs::read_to_string(project_root.join("ai-blueprint.json")) {
        if let Ok(value) = serde_json::from_str::<Value>(&raw) {
            assets.blueprint = value.clone();
            if let Some(prompt) = value
                .get("extraction_prompt")
                .and_then(|item| item.as_str())
            {
                if !prompt.trim().is_empty() {
                    assets.extraction_prompt = prompt.to_string();
                }
            }
            if let Some(enabled) = value
                .pointer("/pagination/enabled")
                .and_then(|item| item.as_bool())
            {
                assets.pagination_enabled = enabled;
            }
            if let Some(selectors) = value
                .pointer("/pagination/selectors")
                .and_then(|item| item.as_array())
            {
                assets.pagination_selectors = selectors
                    .iter()
                    .filter_map(|item| item.as_str().map(|value| value.to_string()))
                    .collect();
            }
            if let Some(required) = value
                .pointer("/authentication/required")
                .and_then(|item| item.as_bool())
            {
                assets.auth_required = required;
            }
            if let Some(runner) = value
                .pointer("/javascript_runtime/recommended_runner")
                .and_then(|item| item.as_str())
            {
                if !runner.trim().is_empty() {
                    assets.recommended_runner = runner.to_string();
                }
            }
            if assets.recommended_runner == "http" {
                if let Some(runner) = value
                    .pointer("/anti_bot_strategy/recommended_runner")
                    .and_then(|item| item.as_str())
                {
                    if !runner.trim().is_empty() {
                        assets.recommended_runner = runner.to_string();
                    }
                }
            }
        }
    }
    if assets.extraction_prompt.trim().is_empty() {
        if let Ok(raw) = fs::read_to_string(project_root.join("ai-extract-prompt.txt")) {
            if !raw.trim().is_empty() {
                assets.extraction_prompt = raw.trim().to_string();
            }
        }
    }
    if let Ok(raw) = fs::read_to_string(project_root.join("ai-auth.json")) {
        if let Ok(value) = serde_json::from_str::<Value>(&raw) {
            if let Some(headers) = value.get("headers").and_then(|item| item.as_object()) {
                for (key, value) in headers {
                    if let Some(text) = value.as_str() {
                        assets.request_headers.insert(key.clone(), text.to_string());
                    }
                }
            }
            if let Some(path) = value
                .get("storage_state_file")
                .and_then(|item| item.as_str())
            {
                assets.storage_state_file = path.to_string();
            }
            if let Some(path) = value.get("cookies_file").and_then(|item| item.as_str()) {
                assets.cookies_file = path.to_string();
            }
        }
    }
    if let Ok(cookie) = env::var("SPIDER_AUTH_COOKIE") {
        if !cookie.trim().is_empty() {
            assets
                .request_headers
                .insert("Cookie".to_string(), cookie.to_string());
        }
    }
    if let Ok(raw) = env::var("SPIDER_AUTH_HEADERS_JSON") {
        if let Ok(value) = serde_json::from_str::<Value>(&raw) {
            if let Some(headers) = value.as_object() {
                for (key, value) in headers {
                    if let Some(text) = value.as_str() {
                        assets.request_headers.insert(key.clone(), text.to_string());
                    }
                }
            }
        }
    }
    if assets.auth_required && assets.recommended_runner == "http" {
        assets.recommended_runner = "browser".to_string();
    }
    assets
}

pub fn apply_ai_start_meta(spider: Spider, assets: &AIProjectAssets) -> Spider {
    let mut spider = spider;
    if assets.recommended_runner != "http" {
        spider = spider.with_start_meta("runner", assets.recommended_runner.clone());
    }
    if !assets.storage_state_file.trim().is_empty() || !assets.cookies_file.trim().is_empty() {
        let mut browser_meta = serde_json::Map::new();
        if !assets.storage_state_file.trim().is_empty() {
            browser_meta.insert(
                "storage_state_file".to_string(),
                Value::String(assets.storage_state_file.clone()),
            );
        }
        if !assets.cookies_file.trim().is_empty() {
            browser_meta.insert(
                "cookies_file".to_string(),
                Value::String(assets.cookies_file.clone()),
            );
        }
        spider = spider.with_start_meta("browser", Value::Object(browser_meta));
    }
    for (key, value) in &assets.request_headers {
        spider = spider.with_start_header(key, value.clone());
    }
    spider
}

pub fn apply_ai_request_strategy(mut request: Request, assets: &AIProjectAssets) -> Request {
    if assets.recommended_runner != "http" {
        request = request.meta("runner", assets.recommended_runner.clone());
    }
    if !assets.storage_state_file.trim().is_empty() || !assets.cookies_file.trim().is_empty() {
        let mut browser_meta = request
            .meta
            .get("browser")
            .and_then(|value| value.as_object())
            .cloned()
            .unwrap_or_default();
        if !assets.storage_state_file.trim().is_empty() {
            browser_meta.insert(
                "storage_state_file".to_string(),
                Value::String(assets.storage_state_file.clone()),
            );
        }
        if !assets.cookies_file.trim().is_empty() {
            browser_meta.insert(
                "cookies_file".to_string(),
                Value::String(assets.cookies_file.clone()),
            );
        }
        request = request.meta("browser", Value::Object(browser_meta));
    }
    request.headers.extend(assets.request_headers.clone());
    request
}

pub fn collect_ai_pagination_requests(
    response: &Response,
    callback: Option<Callback>,
    assets: &AIProjectAssets,
) -> Vec<Request> {
    if !assets.pagination_enabled || assets.pagination_selectors.is_empty() {
        return Vec::new();
    }
    let parser = HTMLParser::new(&response.text);
    let mut seen = BTreeMap::new();
    let mut requests = Vec::new();
    for selector in &assets.pagination_selectors {
        for link in parser.css_attr(selector, "href") {
            if link.trim().is_empty() || seen.insert(link.clone(), true).is_some() {
                continue;
            }
            let request = response.follow(&link, callback.clone());
            requests.push(apply_ai_request_strategy(request, assets));
        }
    }
    requests
}

pub fn register_spider(name: &str, factory: SpiderFactory) {
    let trimmed = name.trim();
    if trimmed.is_empty() {
        return;
    }
    spider_registry()
        .lock()
        .expect("spider registry lock")
        .insert(trimmed.to_string(), factory);
}

pub fn register_plugin(name: &str, factory: PluginFactory) {
    let trimmed = name.trim();
    if trimmed.is_empty() {
        return;
    }
    plugin_registry()
        .lock()
        .expect("plugin registry lock")
        .insert(trimmed.to_string(), factory);
}

pub fn spider_names() -> Vec<String> {
    spider_registry()
        .lock()
        .expect("spider registry lock")
        .keys()
        .cloned()
        .collect()
}

pub fn plugin_names() -> Vec<String> {
    plugin_registry()
        .lock()
        .expect("plugin registry lock")
        .keys()
        .cloned()
        .collect()
}

pub fn resolve_spider(name: &str) -> Result<Spider, String> {
    let registry = spider_registry().lock().expect("spider registry lock");
    if registry.is_empty() {
        return Err("no registered scrapy spiders".to_string());
    }
    if name.trim().is_empty() {
        let first = registry
            .keys()
            .next()
            .cloned()
            .ok_or_else(|| "no registered scrapy spiders".to_string())?;
        return registry
            .get(&first)
            .copied()
            .map(|factory| factory())
            .ok_or_else(|| format!("unknown registered spider: {first}"));
    }
    registry
        .get(name)
        .copied()
        .map(|factory| factory())
        .ok_or_else(|| format!("unknown registered spider: {name}"))
}

pub fn resolve_plugins(selected: &[String]) -> Result<Vec<PluginHandle>, String> {
    if selected.is_empty() {
        return resolve_plugin_specs(&[]);
    }
    let specs = selected
        .iter()
        .map(|name| PluginSpec {
            name: name.trim().to_string(),
            enabled: true,
            priority: 0,
            config: BTreeMap::new(),
        })
        .collect::<Vec<_>>();
    resolve_plugin_specs(&specs)
}

pub fn resolve_plugin_specs(selected: &[PluginSpec]) -> Result<Vec<PluginHandle>, String> {
    let registry = plugin_registry().lock().expect("plugin registry lock");
    let mut specs = normalize_plugin_specs(selected);
    if specs.is_empty() {
        specs = registry
            .keys()
            .cloned()
            .map(|name| PluginSpec {
                name,
                enabled: true,
                priority: 0,
                config: BTreeMap::new(),
            })
            .collect();
    }
    let mut plugins = Vec::with_capacity(specs.len());
    for spec in specs {
        if !spec.enabled {
            continue;
        }
        if let Some(factory) = registry.get(&spec.name).copied() {
            plugins.push(factory());
            continue;
        }
        if let Some(plugin) = new_builtin_plugin(&spec) {
            plugins.push(plugin);
            continue;
        }
        return Err(format!("unknown registered plugin: {}", spec.name));
    }
    Ok(plugins)
}

pub fn run_from_env() -> Result<bool, String> {
    if env::var("RUSTSPIDER_SCRAPY_RUNNER").unwrap_or_default() != "1" {
        return Ok(false);
    }

    let selected_spider = env::var("RUSTSPIDER_SCRAPY_SPIDER").unwrap_or_default();
    let target_url = first_non_blank(&[
        env::var("RUSTSPIDER_SCRAPY_URL").unwrap_or_default(),
        "https://example.com".to_string(),
    ]);
    let html_file = env::var("RUSTSPIDER_SCRAPY_HTML_FILE").unwrap_or_default();
    let output_path = first_non_blank(&[
        env::var("RUSTSPIDER_SCRAPY_OUTPUT").unwrap_or_default(),
        "artifacts/exports/items.json".to_string(),
    ]);
    let mut reverse_url = env::var("RUSTSPIDER_SCRAPY_REVERSE_URL").unwrap_or_default();
    let selected_plugins = split_csv(&env::var("RUSTSPIDER_SCRAPY_PLUGINS").unwrap_or_default());
    let project_root = env::var("RUSTSPIDER_SCRAPY_PROJECT").unwrap_or_default();
    let (project_cfg, settings_source) = load_project_config(Path::new(&project_root));
    if reverse_url.trim().is_empty() {
        reverse_url = project_cfg.node_reverse.base_url.clone();
    }
    let selected_plugin_specs = if selected_plugins.is_empty() && !project_root.trim().is_empty() {
        let specs = load_plugin_specs_from_manifest(Path::new(&project_root));
        if specs.is_empty() {
            configured_plugin_specs(&project_cfg)
        } else {
            specs
        }
    } else {
        selected_plugins
            .iter()
            .map(|name| PluginSpec {
                name: name.trim().to_string(),
                enabled: true,
                priority: 0,
                config: BTreeMap::new(),
            })
            .collect::<Vec<_>>()
    };

    let mut spider = resolve_spider(&selected_spider)?;
    let spider_name = spider.name.clone();
    let plugins = resolve_plugin_specs(&selected_plugin_specs)?;

    if spider.start_urls.is_empty() && !target_url.trim().is_empty() {
        spider = spider.add_start_url(target_url.clone());
    }

    let declarative_pipelines = build_artifact_declarative_pipelines(&project_cfg);
    let declarative_spider_middlewares =
        build_artifact_declarative_spider_middlewares(&project_cfg);
    let declarative_downloader_middlewares =
        build_artifact_declarative_downloader_middlewares(&project_cfg);
    let items = run_spider_with_plugins(
        spider,
        &plugins,
        &target_url,
        &html_file,
        &declarative_pipelines,
        &declarative_spider_middlewares,
        &declarative_downloader_middlewares,
    )?;
    let item_count = items.len();
    let mut exporter = FeedExporter::new("json", &output_path);
    for item in items.iter().cloned() {
        exporter.export_item(item);
    }
    exporter.close()?;

    let applied_plugins = if selected_plugin_specs.is_empty() {
        plugin_names()
    } else {
        plugin_spec_names(&selected_plugin_specs)
    };
    let pipeline_count = declarative_pipelines.len()
        + plugins
            .iter()
            .map(|plugin| plugin.provide_pipelines().len())
            .sum::<usize>();
    let spider_middleware_count = declarative_spider_middlewares.len()
        + plugins
            .iter()
            .map(|plugin| plugin.provide_spider_middlewares().len())
            .sum::<usize>();
    let downloader_middleware_count = declarative_downloader_middlewares.len()
        + plugins
            .iter()
            .map(|plugin| plugin.provide_downloader_middlewares().len())
            .sum::<usize>();
    println!(
        "{}",
        serde_json::to_string_pretty(&json!({
            "command": "scrapy run",
            "runtime": "rust",
            "runner": "artifact-project",
            "spider": spider_name,
            "plugins": applied_plugins,
            "settings_source": settings_source,
            "pipelines": string_list(&project_cfg.scrapy.pipelines),
            "spider_middlewares": string_list(&project_cfg.scrapy.spider_middlewares),
            "downloader_middlewares": string_list(&project_cfg.scrapy.downloader_middlewares),
            "pipeline_count": pipeline_count,
            "spider_middleware_count": spider_middleware_count,
            "downloader_middleware_count": downloader_middleware_count,
            "item_count": item_count,
            "output": output_path,
            "reverse": collect_reverse_summary(&reverse_url, &target_url, &html_file),
        }))
        .unwrap_or_default()
    );
    Ok(true)
}

pub fn collect_reverse_summary(reverse_url: &str, target_url: &str, html_file: &str) -> Value {
    if reverse_url.trim().is_empty() {
        return Value::Null;
    }

    let (html, status_code) = if !html_file.trim().is_empty() {
        match fs::read_to_string(html_file) {
            Ok(html) => (html, 200_u16),
            Err(_) => return Value::Null,
        }
    } else {
        match reqwest::blocking::get(target_url) {
            Ok(response) => {
                let status = response.status().as_u16();
                match response.text() {
                    Ok(html) => (html, status),
                    Err(_) => return Value::Null,
                }
            }
            Err(_) => return Value::Null,
        }
    };

    let script_sample = extract_script_sample(&html);
    let runtime = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(_) => return Value::Null,
    };
    let client = crate::node_reverse::client::NodeReverseClient::new(reverse_url);
    let request = crate::node_reverse::client::AntiBotProfileRequest {
        html,
        js: String::new(),
        headers: std::collections::HashMap::new(),
        cookies: String::new(),
        status_code: Some(status_code),
        url: target_url.to_string(),
    };
    let detect = runtime.block_on(client.detect_anti_bot(&request)).ok();
    let profile = runtime.block_on(client.profile_anti_bot(&request)).ok();
    let spoof = runtime
        .block_on(client.spoof_fingerprint("chrome", "windows"))
        .ok();
    let tls = runtime
        .block_on(client.tls_fingerprint("chrome", "120"))
        .ok();

    let crypto = if script_sample.trim().is_empty() {
        None
    } else {
        runtime.block_on(client.analyze_crypto(&script_sample)).ok()
    };

    json!({
        "detect": detect,
        "profile": profile,
        "fingerprint_spoof": spoof,
        "tls_fingerprint": tls,
        "crypto_analysis": crypto,
    })
}

fn extract_script_sample(html: &str) -> String {
    let lowered = html.to_lowercase();
    let mut start = 0_usize;
    let mut parts = Vec::new();
    while let Some(open_rel) = lowered[start..].find("<script") {
        let open = start + open_rel;
        let Some(tag_end_rel) = lowered[open..].find('>') else {
            break;
        };
        let tag_end = open + tag_end_rel;
        let Some(close_rel) = lowered[tag_end..].find("</script>") else {
            break;
        };
        let close = tag_end + close_rel;
        let snippet = html[tag_end + 1..close].trim();
        if !snippet.is_empty() {
            parts.push(snippet.to_string());
        }
        start = close + "</script>".len();
    }
    let joined = parts.join("\n");
    if !joined.is_empty() {
        joined.chars().take(32_000).collect()
    } else {
        html.chars().take(32_000).collect()
    }
}

pub fn run_spider_with_plugins(
    spider: Spider,
    plugins: &[PluginHandle],
    target_url: &str,
    html_file: &str,
    declarative_pipelines: &[super::ItemPipeline],
    declarative_spider_middlewares: &[super::SpiderMiddlewareHandle],
    declarative_downloader_middlewares: &[super::DownloaderMiddlewareHandle],
) -> Result<Vec<Item>, String> {
    if !html_file.trim().is_empty() {
        let mut spider_middlewares = declarative_spider_middlewares.to_vec();
        let mut downloader_middlewares = declarative_downloader_middlewares.to_vec();
        for plugin in plugins {
            plugin.prepare_spider(&spider)?;
            spider_middlewares.extend(plugin.provide_spider_middlewares());
            downloader_middlewares.extend(plugin.provide_downloader_middlewares());
            plugin.on_spider_opened(&spider)?;
        }
        let html = fs::read_to_string(html_file).map_err(|err| err.to_string())?;
        let mut request = Request::new(target_url.to_string(), None);
        for middleware in &downloader_middlewares {
            request = middleware.process_request(request, &spider)?;
        }
        let mut response = Response {
            url: target_url.to_string(),
            status_code: 200,
            headers: Default::default(),
            text: html,
            request: Some(request),
        };
        for middleware in &downloader_middlewares {
            response = middleware.process_response(response, &spider)?;
        }
        let mut outputs = spider.parse.as_ref()(&response);
        for middleware in &spider_middlewares {
            outputs = middleware.process_spider_output(&response, outputs, &spider)?;
        }
        let mut pipelines = declarative_pipelines.to_vec();
        for plugin in plugins {
            pipelines.extend(plugin.provide_pipelines());
        }
        let mut items = Vec::new();
        for output in outputs {
            if let Output::Item(mut item) = output {
                for pipeline in &pipelines {
                    item = pipeline(item)?;
                }
                for plugin in plugins {
                    item = plugin.process_item(item, &spider)?;
                }
                items.push(item);
            }
        }
        for plugin in plugins {
            plugin.on_spider_closed(&spider)?;
        }
        return Ok(items);
    }

    let mut process = CrawlerProcess::new(spider);
    for pipeline in declarative_pipelines {
        process = process.with_pipeline(pipeline.clone());
    }
    for middleware in declarative_spider_middlewares {
        process = process.with_spider_middleware(middleware.clone());
    }
    for middleware in declarative_downloader_middlewares {
        process = process.with_downloader_middleware(middleware.clone());
    }
    for plugin in plugins {
        process = process.with_plugin(plugin.clone());
    }
    process.run()
}

fn split_csv(value: &str) -> Vec<String> {
    value
        .split(',')
        .map(str::trim)
        .filter(|item| !item.is_empty())
        .map(ToOwned::to_owned)
        .collect()
}

fn first_non_blank(values: &[String]) -> String {
    values
        .iter()
        .find(|value| !value.trim().is_empty())
        .cloned()
        .unwrap_or_default()
}

fn string_list(values: &[String]) -> Vec<String> {
    values
        .iter()
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
        .collect()
}

fn load_project_config(project_root: &Path) -> (ArtifactProjectConfig, Value) {
    let path = project_root.join("spider-framework.yaml");
    let Ok(raw) = fs::read_to_string(&path) else {
        return (ArtifactProjectConfig::default(), Value::Null);
    };
    let cfg = serde_yaml::from_str::<ArtifactProjectConfig>(&raw).unwrap_or_default();
    (cfg, Value::String(path.to_string_lossy().to_string()))
}

fn configured_plugin_specs(cfg: &ArtifactProjectConfig) -> Vec<PluginSpec> {
    cfg.scrapy
        .plugins
        .iter()
        .map(|name| name.trim().to_string())
        .filter(|name| !name.is_empty())
        .map(|name| PluginSpec {
            name,
            enabled: true,
            priority: 0,
            config: BTreeMap::new(),
        })
        .collect()
}

fn build_artifact_declarative_pipelines(cfg: &ArtifactProjectConfig) -> Vec<super::ItemPipeline> {
    let mut pipelines = Vec::new();
    for name in &cfg.scrapy.pipelines {
        if name.trim() == "field-injector" {
            let fields = cfg
                .scrapy
                .component_config
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
            pipelines.push(Arc::new(move |mut item: super::Item| {
                for (key, value) in &fields {
                    item = item.set(key, value.clone());
                }
                Ok(item)
            }) as super::ItemPipeline);
        }
    }
    pipelines
}

#[derive(Clone)]
struct ArtifactResponseContextSpiderMiddleware;

impl super::SpiderMiddleware for ArtifactResponseContextSpiderMiddleware {
    fn process_spider_output(
        &self,
        response: &Response,
        result: Vec<Output>,
        _spider: &Spider,
    ) -> Result<Vec<Output>, String> {
        let mut enriched = Vec::with_capacity(result.len());
        for entry in result {
            match entry {
                Output::Item(item) => {
                    enriched.push(Output::Item(
                        item.set("response_url", response.url.clone())
                            .set("response_status", response.status_code),
                    ));
                }
                other => enriched.push(other),
            }
        }
        Ok(enriched)
    }
}

fn build_artifact_declarative_spider_middlewares(
    cfg: &ArtifactProjectConfig,
) -> Vec<super::SpiderMiddlewareHandle> {
    let mut middlewares = Vec::new();
    for name in &cfg.scrapy.spider_middlewares {
        if name.trim() == "response-context" {
            middlewares
                .push(Arc::new(ArtifactResponseContextSpiderMiddleware)
                    as super::SpiderMiddlewareHandle);
        }
    }
    middlewares
}

#[derive(Clone)]
struct ArtifactRequestHeadersMiddleware {
    headers: BTreeMap<String, String>,
}

impl super::DownloaderMiddleware for ArtifactRequestHeadersMiddleware {
    fn process_request(&self, mut request: Request, _spider: &Spider) -> Result<Request, String> {
        for (key, value) in &self.headers {
            request.headers.insert(key.clone(), value.clone());
        }
        Ok(request)
    }

    fn process_response(&self, response: Response, _spider: &Spider) -> Result<Response, String> {
        Ok(response)
    }
}

fn build_artifact_declarative_downloader_middlewares(
    cfg: &ArtifactProjectConfig,
) -> Vec<super::DownloaderMiddlewareHandle> {
    let mut middlewares = Vec::new();
    for name in &cfg.scrapy.downloader_middlewares {
        if name.trim() == "request-headers" {
            let headers = cfg
                .scrapy
                .component_config
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
            middlewares.push(Arc::new(ArtifactRequestHeadersMiddleware { headers })
                as super::DownloaderMiddlewareHandle);
        }
    }
    middlewares
}

pub fn load_plugin_specs_from_manifest(project_root: &Path) -> Vec<PluginSpec> {
    let path = project_root.join("scrapy-plugins.json");
    let Ok(raw) = fs::read_to_string(path) else {
        return Vec::new();
    };
    let Ok(payload) = serde_json::from_str::<Value>(&raw) else {
        return Vec::new();
    };
    let items = match payload {
        Value::Array(items) => items,
        Value::Object(object) => object
            .get("plugins")
            .and_then(|value| value.as_array())
            .cloned()
            .unwrap_or_default(),
        _ => Vec::new(),
    };
    let specs = items
        .into_iter()
        .filter_map(|item| match item {
            Value::String(name) if !name.trim().is_empty() => Some(PluginSpec {
                name: name.trim().to_string(),
                enabled: true,
                priority: 0,
                config: BTreeMap::new(),
            }),
            Value::Object(object) => {
                let name = object
                    .get("name")
                    .and_then(|value| value.as_str())
                    .map(|value| value.trim().to_string())
                    .filter(|value| !value.is_empty())?;
                let enabled = object
                    .get("enabled")
                    .and_then(|value| value.as_bool())
                    .unwrap_or(true);
                let priority = object
                    .get("priority")
                    .and_then(|value| value.as_i64())
                    .unwrap_or_default() as i32;
                let config = object
                    .get("config")
                    .and_then(|value| value.as_object())
                    .map(|value| {
                        value
                            .iter()
                            .map(|(key, value)| (key.clone(), value.clone()))
                            .collect::<BTreeMap<_, _>>()
                    })
                    .unwrap_or_default();
                Some(PluginSpec {
                    name,
                    enabled,
                    priority,
                    config,
                })
            }
            _ => None,
        })
        .collect::<Vec<_>>();
    normalize_plugin_specs(&specs)
}

fn plugin_spec_names(specs: &[PluginSpec]) -> Vec<String> {
    normalize_plugin_specs(specs)
        .into_iter()
        .filter(|spec| spec.enabled && !spec.name.is_empty())
        .map(|spec| spec.name)
        .collect()
}

fn normalize_plugin_specs(specs: &[PluginSpec]) -> Vec<PluginSpec> {
    let mut normalized = specs
        .iter()
        .filter_map(|spec| {
            let name = spec.name.trim();
            if name.is_empty() {
                return None;
            }
            Some(PluginSpec {
                name: name.to_string(),
                enabled: spec.enabled,
                priority: spec.priority,
                config: spec.config.clone(),
            })
        })
        .collect::<Vec<_>>();
    normalized.sort_by(|left, right| {
        left.priority
            .cmp(&right.priority)
            .then_with(|| left.name.cmp(&right.name))
    });
    normalized
}

fn new_builtin_plugin(spec: &PluginSpec) -> Option<PluginHandle> {
    match spec.name.as_str() {
        "field-injector" => Some(Arc::new(FieldInjectorPlugin::from_spec(spec))),
        _ => None,
    }
}

struct FieldInjectorPlugin {
    fields: BTreeMap<String, Value>,
}

impl FieldInjectorPlugin {
    fn from_spec(spec: &PluginSpec) -> Self {
        let fields = spec
            .config
            .get("fields")
            .and_then(|value| value.as_object())
            .map(|value| {
                value
                    .iter()
                    .map(|(key, value)| (key.clone(), value.clone()))
                    .collect::<BTreeMap<_, _>>()
            })
            .unwrap_or_default();
        Self { fields }
    }
}

impl super::ScrapyPlugin for FieldInjectorPlugin {
    fn process_item(&self, item: Item, _spider: &Spider) -> Result<Item, String> {
        let mut current = item;
        for (key, value) in &self.fields {
            current = current.set(key, value.clone());
        }
        Ok(current)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn set_env(key: &str, value: &str) -> Option<String> {
        let original = env::var(key).ok();
        unsafe {
            env::set_var(key, value);
        }
        original
    }

    fn restore_env(key: &str, original: Option<String>) {
        unsafe {
            match original {
                Some(value) => env::set_var(key, value),
                None => env::remove_var(key),
            }
        }
    }

    #[test]
    fn run_from_env_applies_declarative_components_from_project_config() {
        let project_dir = std::env::temp_dir().join("rustspider-artifact-project-runtime");
        let _ = fs::remove_dir_all(&project_dir);
        fs::create_dir_all(project_dir.join("artifacts").join("exports")).expect("exports dir");

        let html_path = project_dir.join("page.html");
        fs::write(&html_path, "<html><title>Artifact Component</title></html>").expect("fixture");
        fs::write(
            project_dir.join("spider-framework.yaml"),
            "scrapy:\n  pipelines:\n    - field-injector\n  spider_middlewares:\n    - response-context\n  component_config:\n    field_injector:\n      fields:\n        component: configured\n",
        )
        .expect("config");

        register_spider("artifact-components", || {
            Spider::new(
                "artifact-components",
                Arc::new(|response: &Response| {
                    vec![Output::Item(
                        Item::new()
                            .set("title", response.css("title").get().unwrap_or_default())
                            .set("url", response.url.clone()),
                    )]
                }),
            )
        });

        let output_path = project_dir
            .join("artifacts")
            .join("exports")
            .join("items.json");
        let originals = vec![
            (
                "RUSTSPIDER_SCRAPY_RUNNER",
                set_env("RUSTSPIDER_SCRAPY_RUNNER", "1"),
            ),
            (
                "RUSTSPIDER_SCRAPY_PROJECT",
                set_env(
                    "RUSTSPIDER_SCRAPY_PROJECT",
                    project_dir.to_string_lossy().as_ref(),
                ),
            ),
            (
                "RUSTSPIDER_SCRAPY_SPIDER",
                set_env("RUSTSPIDER_SCRAPY_SPIDER", "artifact-components"),
            ),
            (
                "RUSTSPIDER_SCRAPY_URL",
                set_env("RUSTSPIDER_SCRAPY_URL", "https://example.com"),
            ),
            (
                "RUSTSPIDER_SCRAPY_HTML_FILE",
                set_env(
                    "RUSTSPIDER_SCRAPY_HTML_FILE",
                    html_path.to_string_lossy().as_ref(),
                ),
            ),
            (
                "RUSTSPIDER_SCRAPY_OUTPUT",
                set_env(
                    "RUSTSPIDER_SCRAPY_OUTPUT",
                    output_path.to_string_lossy().as_ref(),
                ),
            ),
        ];

        let result = run_from_env();
        for (key, original) in originals {
            restore_env(key, original);
        }

        assert!(matches!(result, Ok(true)));
        let exported = fs::read_to_string(output_path).expect("export should exist");
        assert!(exported.contains("\"component\""));
        assert!(exported.contains("configured"));
        assert!(exported.contains("\"response_url\""));
        assert!(exported.contains("https://example.com"));
    }
}
