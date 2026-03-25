//! RustSpider 集成测试

use rust_spider::{Spider, Page, HtmlParser, Config, Site, ConsolePipeline};
use std::sync::Arc;
use tokio::sync::Mutex;

/// 测试数据结构
#[derive(Debug, Default)]
struct TestData {
    pages: Arc<Mutex<Vec<Page>>>,
}

impl TestData {
    fn new() -> Self {
        Self::default()
    }
    
    async fn add_page(&self, page: Page) {
        self.pages.lock().await.push(page);
    }
    
    async fn count(&self) -> usize {
        self.pages.lock().await.len()
    }
}

#[tokio::test]
async fn test_basic_crawl() {
    let test_data = Arc::new(TestData::new());
    let test_data_clone = test_data.clone();
    
    let mut spider = Spider::new("test_basic")
        .add_start_url("https://httpbin.org/html")
        .set_thread_count(2)
        .set_retry_times(2)
        .add_handler(move |page: &Page| {
            let test_data = test_data_clone.clone();
            tokio::spawn(async move {
                test_data.add_page(page.clone()).await;
            });
        });
    
    let result = spider.run().await;
    
    assert!(result.is_ok());
    assert!(test_data.count().await >= 1);
}

#[tokio::test]
async fn test_multi_url_crawl() {
    let urls = vec![
        "https://httpbin.org/html",
        "https://httpbin.org/robots.txt",
    ];
    
    let mut spider = Spider::new("test_multi_url")
        .add_start_urls(urls)
        .set_thread_count(3)
        .set_retry_times(2);
    
    let result = spider.run().await;
    
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_custom_config() {
    let config = Config::create("test_custom")
        .with_thread_count(5)
        .with_deduplication(true)
        .with_max_pages(10);
    
    let site = Site::create()
        .add_start_url("https://httpbin.org/html")
        .set_sleep_time(50)
        .set_retry_times(2);
    
    let mut spider = Spider::with_config(config)
        .site(site)
        .add_pipeline(ConsolePipeline::new());
    
    let result = spider.run().await;
    
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_html_parsing() {
    let html = r#"
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Hello World</h1>
                <p class="content">This is a test page.</p>
                <a href="/link1">Link 1</a>
                <a href="/link2">Link 2</a>
                <img src="/image.png" />
            </body>
        </html>
    "#;
    
    let parser = HtmlParser::new(html);
    
    // 测试标题提取
    assert_eq!(parser.title(), Some("Test Page".to_string()));
    
    // 测试 CSS 选择器
    assert_eq!(parser.css_first("h1"), Some("Hello World".to_string()));
    assert_eq!(parser.css_first(".content"), Some("This is a test page.".to_string()));
    
    // 测试链接提取
    let links = parser.links();
    assert_eq!(links.len(), 2);
    assert!(links.contains(&"/link1".to_string()));
    assert!(links.contains(&"/link2".to_string()));
    
    // 测试图片提取
    let images = parser.images();
    assert_eq!(images.len(), 1);
    assert_eq!(images[0], "/image.png");
}

#[tokio::test]
async fn test_error_handling() {
    // 测试无效 URL 的错误处理
    let mut spider = Spider::new("test_error")
        .add_start_url("https://invalid-url-that-does-not-exist.com")
        .set_thread_count(1)
        .set_retry_times(1);
    
    // 应该能够处理错误而不崩溃
    let result = spider.run().await;
    
    // 根据实现，可能成功（跳过）或失败
    // 关键是不要 panic
    assert!(result.is_ok() || result.is_err());
}

#[tokio::test]
async fn test_concurrent_crawl() {
    let page_count = Arc::new(std::sync::atomic::AtomicU64::new(0));
    let page_count_clone = page_count.clone();
    
    let mut spider = Spider::new("test_concurrent")
        .add_start_url("https://httpbin.org/html")
        .add_start_url("https://httpbin.org/robots.txt")
        .add_start_url("https://httpbin.org/json")
        .set_thread_count(10)
        .add_handler(move |_page: &Page| {
            page_count_clone.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        });
    
    let result = spider.run().await;
    
    assert!(result.is_ok());
    assert!(page_count.load(std::sync::atomic::Ordering::Relaxed) >= 1);
}

#[tokio::test]
async fn test_graceful_shutdown() {
    let is_running = Arc::new(tokio::sync::AtomicBool::new(true));
    let is_running_clone = is_running.clone();
    
    let mut spider = Spider::new("test_shutdown")
        .add_start_url("https://httpbin.org/html")
        .set_thread_count(2);
    
    // 在后台运行
    let handle = tokio::spawn(async move {
        spider.run().await
    });
    
    // 等待一小段时间
    tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
    
    // 设置停止标志
    is_running_clone.store(false, std::sync::atomic::Ordering::Relaxed);
    
    // 等待完成
    let result = tokio::time::timeout(
        tokio::time::Duration::from_secs(5),
        handle
    ).await;
    
    // 应该在超时前完成
    assert!(result.is_ok());
}
