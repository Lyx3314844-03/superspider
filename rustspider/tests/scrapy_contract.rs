use std::sync::{Arc, Mutex};

use rustspider::scrapy::project;
use rustspider::scrapy::{
    CrawlerProcess, DownloaderMiddleware, FeedExporter, Item, Output, Response, ScrapyPlugin,
    Selector, Spider, SpiderMiddleware,
};

#[test]
fn selector_supports_css_xpath_and_regex() {
    let selector = Selector::new("<html><body><h1>Demo</h1><a href='/next'>Next</a></body></html>");

    assert_eq!(selector.css("h1").get().as_deref(), Some("Demo"));
    assert_eq!(selector.xpath("//a/@href").get().as_deref(), Some("/next"));
    assert_eq!(
        selector.re_first(r"<h1>([^<]+)</h1>").as_deref(),
        Some("Demo")
    );
}

#[test]
fn response_follow_resolves_relative_urls() {
    let response = Response {
        url: "https://example.com/root".to_string(),
        status_code: 200,
        headers: Default::default(),
        text: "<html></html>".to_string(),
        request: None,
    };

    let request = response.follow("/next", None);
    assert_eq!(request.url, "https://example.com/next");
}

#[test]
fn feed_exporter_writes_json_items() {
    let path = std::env::temp_dir().join("rustspider-scrapy-items.json");
    let mut exporter = FeedExporter::new("json", &path);
    exporter.export_item(Item::new().set("title", "Demo"));
    let output = exporter.close().expect("export should succeed");

    let content = std::fs::read_to_string(&output).expect("output should exist");
    assert!(content.contains("Demo"));

    let _ = std::fs::remove_file(output);
}

struct TestPlugin {
    opened: Arc<Mutex<bool>>,
    closed: Arc<Mutex<bool>>,
}

impl ScrapyPlugin for TestPlugin {
    fn provide_pipelines(&self) -> Vec<rustspider::scrapy::ItemPipeline> {
        vec![Arc::new(|item| Ok(item.set("pipeline", "active")))]
    }

    fn on_spider_opened(&self, _spider: &Spider) -> Result<(), String> {
        *self.opened.lock().expect("lock") = true;
        Ok(())
    }

    fn on_spider_closed(&self, _spider: &Spider) -> Result<(), String> {
        *self.closed.lock().expect("lock") = true;
        Ok(())
    }

    fn process_item(&self, item: Item, _spider: &Spider) -> Result<Item, String> {
        Ok(item.set("plugin", "yes"))
    }
}

#[test]
fn crawler_process_runs_plugin_hooks_and_injected_pipelines() {
    let server = std::net::TcpListener::bind("127.0.0.1:0").expect("bind");
    let addr = server.local_addr().expect("addr");
    let opened = Arc::new(Mutex::new(false));
    let closed = Arc::new(Mutex::new(false));

    std::thread::spawn(move || {
        if let Ok((mut stream, _)) = server.accept() {
            let mut buffer = [0u8; 1024];
            let _ = std::io::Read::read(&mut stream, &mut buffer);
            let body = "<html><title>Demo</title></html>";
            let response = format!(
                "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n{}",
                body.len(),
                body
            );
            let _ = std::io::Write::write_all(&mut stream, response.as_bytes());
        }
    });

    let spider = Spider::new(
        "demo",
        Arc::new(|response| {
            vec![Output::Item(Item::new().set(
                "title",
                response.css("title").get().unwrap_or_default(),
            ))]
        }),
    )
    .add_start_url(format!("http://{}", addr));

    let plugin = Arc::new(TestPlugin {
        opened: opened.clone(),
        closed: closed.clone(),
    });

    let items = CrawlerProcess::new(spider)
        .with_plugin(plugin)
        .run()
        .expect("crawler run");

    assert!(*opened.lock().expect("lock"));
    assert!(*closed.lock().expect("lock"));
    assert_eq!(items.len(), 1);
    assert_eq!(
        items[0].get("pipeline").and_then(|value| value.as_str()),
        Some("active")
    );
    assert_eq!(
        items[0].get("plugin").and_then(|value| value.as_str()),
        Some("yes")
    );
}

#[test]
fn project_registry_registers_spiders_and_plugins() {
    fn make_spider() -> Spider {
        Spider::new("registry-demo", Arc::new(|_| vec![]))
    }

    struct EmptyPlugin;
    impl ScrapyPlugin for EmptyPlugin {}

    fn make_plugin() -> Arc<dyn ScrapyPlugin> {
        Arc::new(EmptyPlugin)
    }

    project::register_spider("registry-demo", make_spider);
    project::register_plugin("registry-plugin", make_plugin);

    let spider = project::resolve_spider("registry-demo").expect("registered spider");
    let plugins =
        project::resolve_plugins(&["registry-plugin".to_string()]).expect("registered plugin");

    assert_eq!(spider.name, "registry-demo");
    assert_eq!(plugins.len(), 1);
}

struct RunnerPlugin {
    configured: Arc<Mutex<bool>>,
}

impl ScrapyPlugin for RunnerPlugin {
    fn configure(
        &self,
        config: &std::collections::BTreeMap<String, serde_json::Value>,
    ) -> Result<(), String> {
        *self.configured.lock().expect("lock") =
            config.get("runner").and_then(|value| value.as_str()) == Some("browser");
        Ok(())
    }

    fn provide_spider_middlewares(&self) -> Vec<rustspider::scrapy::SpiderMiddlewareHandle> {
        vec![Arc::new(TestSpiderMiddleware)]
    }

    fn provide_downloader_middlewares(
        &self,
    ) -> Vec<rustspider::scrapy::DownloaderMiddlewareHandle> {
        vec![Arc::new(TestDownloaderMiddleware)]
    }

    fn process_item(&self, item: Item, _spider: &Spider) -> Result<Item, String> {
        Ok(item.set("configured", *self.configured.lock().expect("lock")))
    }
}

struct TestSpiderMiddleware;

impl SpiderMiddleware for TestSpiderMiddleware {
    fn process_spider_output(
        &self,
        _response: &Response,
        mut result: Vec<Output>,
        _spider: &Spider,
    ) -> Result<Vec<Output>, String> {
        result.push(Output::Item(Item::new().set("middleware", "spider")));
        Ok(result)
    }
}

struct TestDownloaderMiddleware;

impl DownloaderMiddleware for TestDownloaderMiddleware {
    fn process_request(
        &self,
        request: rustspider::scrapy::Request,
        _spider: &Spider,
    ) -> Result<rustspider::scrapy::Request, String> {
        Ok(request.header("x-test", "active"))
    }

    fn process_response(&self, response: Response, _spider: &Spider) -> Result<Response, String> {
        Ok(response)
    }
}

#[test]
fn crawler_process_supports_config_middleware_and_browser_runner() {
    let configured = Arc::new(Mutex::new(false));
    let spider = Spider::new(
        "demo",
        Arc::new(|response| {
            vec![Output::Item(Item::new().set(
                "title",
                response.css("title").get().unwrap_or_default(),
            ))]
        }),
    )
    .add_start_url("https://example.com");

    let mut config = std::collections::BTreeMap::new();
    config.insert(
        "runner".to_string(),
        serde_json::Value::String("browser".to_string()),
    );

    let items = CrawlerProcess::new(spider)
        .with_config(config)
        .with_browser_fetcher(Arc::new(|request, _spider| {
            Ok(Response {
                url: request.url.clone(),
                status_code: 200,
                headers: Default::default(),
                text: "<html><title>Browser Demo</title></html>".to_string(),
                request: Some(request.clone()),
            })
        }))
        .with_plugin(Arc::new(RunnerPlugin { configured }))
        .run()
        .expect("crawler run");

    assert_eq!(items.len(), 2);
    assert_eq!(
        items[0].get("title").and_then(|value| value.as_str()),
        Some("Browser Demo")
    );
    assert_eq!(
        items[0].get("configured").and_then(|value| value.as_bool()),
        Some(true)
    );
    assert_eq!(
        items[1].get("middleware").and_then(|value| value.as_str()),
        Some("spider")
    );
}
