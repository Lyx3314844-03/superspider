// RustSpider 浏览器自动化示例。

#[cfg(feature = "browser")]
use rustspider::browser::{BrowserConfig, BrowserManager};

#[cfg(feature = "browser")]
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("===== RustSpider Browser 示例 =====");

    let config = BrowserConfig::default();
    let browser = BrowserManager::new(config).await?;

    browser.navigate("https://www.example.com").await?;

    let title = browser.get_title().await?;
    println!("页面标题：{}", title);

    let content = browser.get_html().await?;
    println!("页面内容长度：{}", content.len());

    browser.screenshot_to_file("downloads/example.png").await?;
    browser.close().await?;

    println!("===== 示例完成 =====");
    Ok(())
}

#[cfg(not(feature = "browser"))]
fn main() {
    eprintln!("This example requires `cargo run --example playwright_example --features browser`.");
}
