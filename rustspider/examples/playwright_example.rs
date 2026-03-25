// RustSpider Playwright 使用示例
use rustspider::playwright::{Browser, BrowserConfig};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("===== RustSpider Playwright 示例 =====");
    
    // 创建配置
    let config = BrowserConfig::default();
    
    // 创建浏览器
    let mut browser = Browser::new(config);
    
    // 启动浏览器
    browser.start().await?;
    
    // 导航到页面
    browser.navigate("https://www.example.com").await?;
    
    // 获取标题
    let title = browser.get_title().await?;
    println!("页面标题：{}", title);
    
    // 获取内容
    let content = browser.get_content().await?;
    println!("页面内容长度：{}", content.len());
    
    // 截图
    browser.screenshot("downloads/example.png").await?;
    
    // 执行 JavaScript
    let result = browser.evaluate("document.title").await?;
    println!("JS 结果：{}", result);
    
    // Cookie 管理
    browser.save_cookies_to_file("downloads/cookies.json").await?;
    
    // 打印统计
    browser.print_stats();
    
    // 关闭浏览器
    browser.close();
    
    println!("===== 示例完成 =====");
    
    Ok(())
}
