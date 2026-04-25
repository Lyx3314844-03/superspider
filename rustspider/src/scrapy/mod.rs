use regex::Regex;
use serde::Serialize;
use serde_json::Value;
use std::collections::{BTreeMap, HashSet, VecDeque};
use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::Arc;

use crate::parser::HTMLParser;

pub mod project;

pub type Callback = Arc<dyn Fn(&Response) -> Vec<Output> + Send + Sync>;
pub type ItemPipeline = Arc<dyn Fn(Item) -> Result<Item, String> + Send + Sync>;
pub type PluginHandle = Arc<dyn ScrapyPlugin>;
pub type BrowserFetchFn = Arc<dyn Fn(&Request, &Spider) -> Result<Response, String> + Send + Sync>;
pub type SpiderMiddlewareHandle = Arc<dyn SpiderMiddleware>;
pub type DownloaderMiddlewareHandle = Arc<dyn DownloaderMiddleware>;

pub trait ScrapyPlugin: Send + Sync {
    fn configure(&self, _config: &BTreeMap<String, Value>) -> Result<(), String> {
        Ok(())
    }

    fn prepare_spider(&self, _spider: &Spider) -> Result<(), String> {
        Ok(())
    }

    fn provide_pipelines(&self) -> Vec<ItemPipeline> {
        Vec::new()
    }

    fn provide_spider_middlewares(&self) -> Vec<SpiderMiddlewareHandle> {
        Vec::new()
    }

    fn provide_downloader_middlewares(&self) -> Vec<DownloaderMiddlewareHandle> {
        Vec::new()
    }

    fn on_spider_opened(&self, _spider: &Spider) -> Result<(), String> {
        Ok(())
    }

    fn on_spider_closed(&self, _spider: &Spider) -> Result<(), String> {
        Ok(())
    }

    fn process_item(&self, item: Item, _spider: &Spider) -> Result<Item, String> {
        Ok(item)
    }
}

pub trait SpiderMiddleware: Send + Sync {
    fn process_spider_output(
        &self,
        response: &Response,
        result: Vec<Output>,
        spider: &Spider,
    ) -> Result<Vec<Output>, String>;
}

pub trait DownloaderMiddleware: Send + Sync {
    fn process_request(&self, request: Request, spider: &Spider) -> Result<Request, String>;

    fn process_response(&self, response: Response, spider: &Spider) -> Result<Response, String>;
}

#[derive(Clone)]
pub struct Request {
    pub url: String,
    pub method: String,
    pub headers: BTreeMap<String, String>,
    pub body: Option<String>,
    pub meta: BTreeMap<String, Value>,
    pub priority: i32,
    pub callback: Option<Callback>,
}

impl Request {
    pub fn new(url: impl Into<String>, callback: Option<Callback>) -> Self {
        Self {
            url: url.into(),
            method: "GET".to_string(),
            headers: BTreeMap::new(),
            body: None,
            meta: BTreeMap::new(),
            priority: 0,
            callback,
        }
    }

    pub fn header(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.headers.insert(key.into(), value.into());
        self
    }

    pub fn meta<T: Serialize>(mut self, key: &str, value: T) -> Self {
        self.meta.insert(
            key.to_string(),
            serde_json::to_value(value).unwrap_or(Value::Null),
        );
        self
    }
}

#[derive(Clone)]
pub struct Response {
    pub url: String,
    pub status_code: u16,
    pub headers: BTreeMap<String, String>,
    pub text: String,
    pub request: Option<Request>,
}

impl Response {
    pub fn selector(&self) -> Selector {
        Selector::new(self.text.clone())
    }

    pub fn css(&self, query: &str) -> SelectorList {
        self.selector().css(query)
    }

    pub fn xpath(&self, expr: &str) -> SelectorList {
        self.selector().xpath(expr)
    }

    pub fn follow(&self, target: &str, callback: Option<Callback>) -> Request {
        let resolved = reqwest::Url::parse(&self.url)
            .ok()
            .and_then(|base| base.join(target).ok())
            .map(|value| value.to_string())
            .unwrap_or_else(|| target.to_string());
        Request::new(resolved, callback)
    }
}

#[derive(Debug, Clone, Default)]
pub struct Item {
    values: BTreeMap<String, Value>,
}

impl Item {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn set<T: Serialize>(mut self, key: &str, value: T) -> Self {
        let serialized = serde_json::to_value(value).unwrap_or(Value::Null);
        self.values.insert(key.to_string(), serialized);
        self
    }

    pub fn get(&self, key: &str) -> Option<&Value> {
        self.values.get(key)
    }

    pub fn to_map(&self) -> BTreeMap<String, Value> {
        self.values.clone()
    }
}

pub struct Selector {
    html: String,
    parser: HTMLParser,
}

impl Selector {
    pub fn new(html: impl Into<String>) -> Self {
        let html = html.into();
        Self {
            parser: HTMLParser::new(&html),
            html,
        }
    }

    pub fn css(&self, query: &str) -> SelectorList {
        SelectorList::new(self.parser.css(query))
    }

    pub fn xpath(&self, expr: &str) -> SelectorList {
        SelectorList::new(run_xpath_all(&self.html, expr).unwrap_or_default())
    }

    pub fn re(&self, pattern: &str) -> Vec<String> {
        let compiled = match Regex::new(pattern) {
            Ok(compiled) => compiled,
            Err(_) => return Vec::new(),
        };
        compiled
            .captures_iter(&self.html)
            .filter_map(|capture| {
                capture
                    .get(1)
                    .or_else(|| capture.get(0))
                    .map(|value| value.as_str().to_string())
            })
            .collect()
    }

    pub fn re_first(&self, pattern: &str) -> Option<String> {
        self.re(pattern).into_iter().next()
    }
}

pub struct SelectorList {
    values: Vec<String>,
}

impl SelectorList {
    fn new(values: Vec<String>) -> Self {
        Self { values }
    }

    pub fn get(&self) -> Option<String> {
        self.values.first().cloned()
    }

    pub fn get_all(&self) -> Vec<String> {
        self.values.clone()
    }

    pub fn len(&self) -> usize {
        self.values.len()
    }

    pub fn is_empty(&self) -> bool {
        self.values.is_empty()
    }
}

pub struct FeedExporter {
    format: String,
    output_path: PathBuf,
    items: Vec<BTreeMap<String, Value>>,
}

impl FeedExporter {
    pub fn new(format: impl Into<String>, output_path: impl Into<PathBuf>) -> Self {
        Self {
            format: format.into().to_ascii_lowercase(),
            output_path: output_path.into(),
            items: Vec::new(),
        }
    }

    pub fn export_item(&mut self, item: Item) {
        self.items.push(item.to_map());
    }

    pub fn close(&self) -> Result<PathBuf, String> {
        if let Some(parent) = self.output_path.parent() {
            fs::create_dir_all(parent).map_err(|err| err.to_string())?;
        }
        match self.format.as_str() {
            "json" => {
                let payload =
                    serde_json::to_string_pretty(&self.items).map_err(|err| err.to_string())?;
                fs::write(&self.output_path, payload).map_err(|err| err.to_string())?;
            }
            "jsonlines" => {
                let mut lines = String::new();
                for item in &self.items {
                    let row = serde_json::to_string(item).map_err(|err| err.to_string())?;
                    lines.push_str(&row);
                    lines.push('\n');
                }
                fs::write(&self.output_path, lines).map_err(|err| err.to_string())?;
            }
            "csv" => {
                let headers = ordered_headers(&self.items);
                let mut buffer = String::new();
                buffer.push_str(&headers.join(","));
                buffer.push('\n');
                for item in &self.items {
                    let record = headers
                        .iter()
                        .map(|key| {
                            csv_escape(&item.get(key).cloned().unwrap_or(Value::Null).to_string())
                        })
                        .collect::<Vec<_>>();
                    buffer.push_str(&record.join(","));
                    buffer.push('\n');
                }
                fs::write(&self.output_path, buffer).map_err(|err| err.to_string())?;
            }
            other => return Err(format!("unsupported feed format: {other}")),
        }
        Ok(self.output_path.clone())
    }
}

pub enum Output {
    Item(Item),
    Request(Request),
}

pub struct Spider {
    pub name: String,
    pub start_urls: Vec<String>,
    pub start_meta: BTreeMap<String, Value>,
    pub start_headers: BTreeMap<String, String>,
    pub parse: Callback,
}

impl Spider {
    pub fn new(name: impl Into<String>, parse: Callback) -> Self {
        Self {
            name: name.into(),
            start_urls: Vec::new(),
            start_meta: BTreeMap::new(),
            start_headers: BTreeMap::new(),
            parse,
        }
    }

    pub fn add_start_url(mut self, url: impl Into<String>) -> Self {
        self.start_urls.push(url.into());
        self
    }

    pub fn with_start_meta<T: Serialize>(mut self, key: &str, value: T) -> Self {
        self.start_meta.insert(
            key.to_string(),
            serde_json::to_value(value).unwrap_or(Value::Null),
        );
        self
    }

    pub fn with_start_header(mut self, key: &str, value: impl Into<String>) -> Self {
        self.start_headers.insert(key.to_string(), value.into());
        self
    }

    pub fn start_requests(&self) -> Vec<Request> {
        self.start_urls
            .iter()
            .cloned()
            .map(|url| {
                let mut request = Request::new(url, Some(self.parse.clone()));
                request.headers.extend(self.start_headers.clone());
                request.meta.extend(self.start_meta.clone());
                request
            })
            .collect()
    }
}

pub struct CrawlerProcess {
    spider: Spider,
    client: reqwest::blocking::Client,
    pipelines: Vec<ItemPipeline>,
    spider_middlewares: Vec<SpiderMiddlewareHandle>,
    downloader_middlewares: Vec<DownloaderMiddlewareHandle>,
    plugins: Vec<PluginHandle>,
    seen: HashSet<String>,
    config: BTreeMap<String, Value>,
    browser_fetcher: Option<BrowserFetchFn>,
}

impl CrawlerProcess {
    pub fn new(spider: Spider) -> Self {
        Self {
            spider,
            client: reqwest::blocking::Client::new(),
            pipelines: Vec::new(),
            spider_middlewares: Vec::new(),
            downloader_middlewares: Vec::new(),
            plugins: Vec::new(),
            seen: HashSet::new(),
            config: BTreeMap::new(),
            browser_fetcher: None,
        }
    }

    pub fn with_pipeline(mut self, pipeline: ItemPipeline) -> Self {
        self.pipelines.push(pipeline);
        self
    }

    pub fn with_spider_middleware(mut self, middleware: SpiderMiddlewareHandle) -> Self {
        self.spider_middlewares.push(middleware);
        self
    }

    pub fn with_downloader_middleware(mut self, middleware: DownloaderMiddlewareHandle) -> Self {
        self.downloader_middlewares.push(middleware);
        self
    }

    pub fn with_plugin(mut self, plugin: PluginHandle) -> Self {
        self.plugins.push(plugin);
        self
    }

    pub fn with_config(mut self, config: BTreeMap<String, Value>) -> Self {
        self.config = config;
        self
    }

    pub fn with_browser_fetcher(mut self, fetcher: BrowserFetchFn) -> Self {
        self.browser_fetcher = Some(fetcher);
        self
    }

    pub fn run(mut self) -> Result<Vec<Item>, String> {
        let mut queue: VecDeque<Request> = self.spider.start_requests().into();
        let mut items = Vec::new();
        let mut active_pipelines = self.pipelines.clone();
        let mut spider_middlewares = self.spider_middlewares.clone();
        let mut downloader_middlewares = self.downloader_middlewares.clone();

        for plugin in &self.plugins {
            plugin.configure(&self.config)?;
            plugin.prepare_spider(&self.spider)?;
            active_pipelines.extend(plugin.provide_pipelines());
            spider_middlewares.extend(plugin.provide_spider_middlewares());
            downloader_middlewares.extend(plugin.provide_downloader_middlewares());
            plugin.on_spider_opened(&self.spider)?;
        }

        while let Some(request) = queue.pop_front() {
            let mut request = request;
            for middleware in &downloader_middlewares {
                request = middleware.process_request(request, &self.spider)?;
            }
            if self.seen.contains(&request.url) {
                continue;
            }
            self.seen.insert(request.url.clone());
            let mut wrapped = self.fetch_response(&request)?;
            for middleware in &downloader_middlewares {
                wrapped = middleware.process_response(wrapped, &self.spider)?;
            }

            let callback = request
                .callback
                .clone()
                .unwrap_or_else(|| self.spider.parse.clone());
            let mut outputs = callback(&wrapped);
            for middleware in &spider_middlewares {
                outputs = middleware.process_spider_output(&wrapped, outputs, &self.spider)?;
            }
            for output in outputs {
                match output {
                    Output::Request(next) => {
                        if !self.seen.contains(&next.url) {
                            queue.push_back(next);
                        }
                    }
                    Output::Item(item) => {
                        let mut current = item;
                        for pipeline in &active_pipelines {
                            current = pipeline(current)?;
                        }
                        for plugin in &self.plugins {
                            current = plugin.process_item(current, &self.spider)?;
                        }
                        items.push(current);
                    }
                }
            }
        }

        for plugin in &self.plugins {
            plugin.on_spider_closed(&self.spider)?;
        }

        Ok(items)
    }

    fn fetch_response(&self, request: &Request) -> Result<Response, String> {
        let runner = resolve_runner(&request.meta, &self.config);
        if runner == "browser" {
            if let Some(fetcher) = &self.browser_fetcher {
                return fetcher(request, &self.spider);
            }
        }
        let mut http_request = self.client.request(
            request
                .method
                .parse::<reqwest::Method>()
                .unwrap_or(reqwest::Method::GET),
            &request.url,
        );
        for (key, value) in &request.headers {
            http_request = http_request.header(key, value);
        }
        if let Some(body) = &request.body {
            http_request = http_request.body(body.clone());
        }

        let response = http_request.send().map_err(|err| err.to_string())?;
        let status_code = response.status().as_u16();
        let headers = response
            .headers()
            .iter()
            .map(|(key, value)| {
                (
                    key.to_string(),
                    value.to_str().unwrap_or_default().to_string(),
                )
            })
            .collect::<BTreeMap<_, _>>();
        let text = response.text().map_err(|err| err.to_string())?;
        Ok(Response {
            url: request.url.clone(),
            status_code,
            headers,
            text,
            request: Some(request.clone()),
        })
    }
}

fn ordered_headers(items: &[BTreeMap<String, Value>]) -> Vec<String> {
    let mut headers = Vec::new();
    let mut seen = HashSet::new();
    for item in items {
        for key in item.keys() {
            if seen.insert(key.clone()) {
                headers.push(key.clone());
            }
        }
    }
    headers
}

fn csv_escape(value: &str) -> String {
    if value.contains(',') || value.contains('"') || value.contains('\n') {
        return format!("\"{}\"", value.replace('"', "\"\""));
    }
    value.to_string()
}

fn resolve_runner(
    meta: &BTreeMap<String, Value>,
    config: &BTreeMap<String, Value>,
) -> &'static str {
    let normalize = |value: Option<&Value>| -> Option<&'static str> {
        let text = value?.as_str()?.trim().to_ascii_lowercase();
        match text.as_str() {
            "browser" => Some("browser"),
            "http" => Some("http"),
            "hybrid" => Some("hybrid"),
            _ => None,
        }
    };
    if let Some(runner) = normalize(meta.get("runner")) {
        return runner;
    }
    if let Some(runner) = normalize(config.get("runner")) {
        return runner;
    }
    "http"
}

fn run_xpath_all(html: &str, xpath: &str) -> Result<Vec<String>, String> {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or_else(|| "failed to resolve workspace root".to_string())?
        .join("tools")
        .join("xpath_extract.py");
    if !root.exists() {
        return Err(format!("missing helper script: {}", root.display()));
    }

    let mut child = Command::new("python")
        .arg(root)
        .arg(xpath)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|err| err.to_string())?;

    if let Some(stdin) = child.stdin.as_mut() {
        stdin
            .write_all(html.as_bytes())
            .map_err(|err| err.to_string())?;
    }

    let output = child.wait_with_output().map_err(|err| err.to_string())?;
    if !output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        if let Ok(payload) = serde_json::from_str::<Value>(&stdout) {
            if let Some(error) = payload.get("error").and_then(|value| value.as_str()) {
                return Err(error.to_string());
            }
        }
        return Err(String::from_utf8_lossy(&output.stderr).trim().to_string());
    }
    let payload: Value = serde_json::from_slice(&output.stdout).map_err(|err| err.to_string())?;
    let values = payload
        .get("values")
        .and_then(|value| value.as_array())
        .cloned()
        .unwrap_or_default()
        .into_iter()
        .filter_map(|value| value.as_str().map(|item| item.to_string()))
        .collect();
    Ok(values)
}
