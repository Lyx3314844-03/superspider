//! rustspider 使用示例

use rustspider::SpiderBuilder;

fn main() {
    env_logger::init();

    let spider = SpiderBuilder::new()
        .name("ExampleSpider")
        .concurrency(3)
        .max_requests(10)
        .build()
        .expect("failed to build spider");

    spider
        .add_url("https://www.example.com")
        .expect("failed to enqueue start URL");

    let runtime = tokio::runtime::Runtime::new().expect("failed to create tokio runtime");
    if let Err(error) = runtime.block_on(spider.run()) {
        eprintln!("Spider failed: {}", error);
    }

    println!("{}", spider.get_stats());
}
