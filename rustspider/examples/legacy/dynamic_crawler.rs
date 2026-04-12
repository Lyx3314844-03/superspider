// RustSpider 动态页面抓取示例。

#[cfg(feature = "browser")]
use rustspider::browser::{BrowserConfig, BrowserManager};

#[cfg(feature = "browser")]
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let browser = BrowserManager::new(BrowserConfig::default()).await?;
    browser.navigate("https://www.example.com").await?;

    let title = browser.get_title().await?;
    println!("title: {}", title);

    browser.close().await?;
    Ok(())
}

#[cfg(not(feature = "browser"))]
fn main() {
    eprintln!("This example requires `cargo run --example dynamic_crawler --features browser`.");
}
