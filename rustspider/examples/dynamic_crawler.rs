//! 动态网页爬虫示例
//! 
//! 演示如何使用浏览器自动化爬取 JavaScript 渲染的页面
//! 
//! 运行：cargo run --bin dynamic_crawler --features browser

use rustspider::browser::{BrowserBuilder, BrowserManager};
use rustspider::parser::HTMLParser;
use std::time::Duration;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🕷️  动态网页爬虫\n");

    // 创建浏览器
    let browser = BrowserBuilder::new()
        .headless(true)
        .timeout(Duration::from_secs(30))
        .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        .build()
        .await?;

    println!("✓ 浏览器初始化完成\n");

    // 爬取 GitHub Trending
    crawl_github_trending(&browser).await?;

    // 爬取 Hacker News
    crawl_hacker_news(&browser).await?;

    // 爬取动态加载的评论
    crawl_dynamic_comments(&browser).await?;

    println!("\n✅ 爬取完成！");

    browser.close().await?;

    Ok(())
}

/// 爬取 GitHub Trending
async fn crawl_github_trending(browser: &BrowserManager) -> Result<(), Box<dyn std::error::Error>> {
    println!("📊 爬取 GitHub Trending...\n");

    // 导航
    browser.navigate("https://github.com/trending").await?;
    browser.wait_for_page_load(None).await?;

    // 等待内容加载
    browser.wait_for_element(".Box-row", Some(Duration::from_secs(10))).await?;

    // 获取所有项目
    let repos = browser.get_all_texts("h2 a").await?;
    let descriptions = browser.get_all_texts(".Box-row p").await?;
    let stars = browser.get_all_texts(".Box-row a[href*='stargazers']").await?;

    println!("  Top {} 仓库:\n", repos.len().min(10));

    for i in 0..repos.len().min(10) {
        println!("  {}. {}", i + 1, repos[i].trim());
        
        if i < descriptions.len() && !descriptions[i].trim().is_empty() {
            println!("     {}", descriptions[i].trim());
        }
        
        if i < stars.len() {
            println!("     ⭐ {}", stars[i].trim());
        }
        
        println!();
    }

    Ok(())
}

/// 爬取 Hacker News
async fn crawl_hacker_news(browser: &BrowserManager) -> Result<(), Box<dyn std::error::Error>> {
    println!("📰 爬取 Hacker News...\n");

    browser.navigate("https://news.ycombinator.com").await?;
    browser.wait_for_page_load(None).await?;

    // 获取所有新闻标题
    let titles = browser.get_all_texts(".titleline a").await?;
    
    // 获取分数
    let scores = browser.get_all_texts(".score").await?;
    
    // 获取评论数
    let comments = browser.get_all_texts("a[href*='item?id=']").await?;

    println!("  Top {} 新闻:\n", titles.len().min(10));

    for i in 0..titles.len().min(15) {
        let title = titles.get(i).map(|s| s.as_str()).unwrap_or("");
        if title.is_empty() || title == "More" {
            continue;
        }

        println!("  {}. {}", i + 1, title);
        
        if let Some(score) = scores.get(i) {
            println!("     {}", score.trim());
        }
        
        println!();
    }

    Ok(())
}

/// 爬取动态加载的评论（模拟滚动加载）
async fn crawl_dynamic_comments(browser: &BrowserManager) -> Result<(), Box<dyn std::error::Error>> {
    println!("💬 爬取动态加载内容...\n");

    // 使用 Wikipedia（有丰富内容）
    browser.navigate("https://zh.wikipedia.org/wiki/Rust").await?;
    browser.wait_for_page_load(None).await?;

    // 获取页面高度
    let height: f64 = browser.execute_script_with_result(
        "return document.body.scrollHeight"
    ).await?;
    println!("  页面高度：{:.0}px", height);

    // 滚动到底部触发懒加载
    println!("  滚动加载更多内容...");
    browser.scroll_to_bottom().await?;
    tokio::time::sleep(Duration::from_secs(2)).await;

    // 获取所有章节标题
    let headings = browser.get_all_texts(".mw-headline").await?;
    
    println!("\n  页面章节:");
    for heading in headings.iter().take(15) {
        println!("    • {}", heading.trim());
    }

    // 获取所有段落数量
    let para_count = browser.count_elements("p").await?;
    println!("\n  段落总数：{}", para_count);

    // 获取简介部分
    if let Ok(intro) = browser.get_element_text("#firstHeading").await {
        println!("\n  标题：{}", intro);
    }

    Ok(())
}

/// 表单提交示例
async fn form_submission_demo(browser: &BrowserManager) -> Result<(), Box<dyn std::error::Error>> {
    println!("📝 表单提交示例...\n");

    browser.navigate("https://www.google.com").await?;
    browser.wait_for_page_load(None).await?;

    // 查找搜索框
    if browser.element_exists("textarea[name='q']").await? {
        // 输入搜索词
        browser.fill("textarea[name='q']", "Rust programming language").await?;
        println!("  ✓ 输入搜索词");

        // 获取建议
        let suggestions = browser.get_all_texts("[role='option'] div[role='option']").await.unwrap_or_default();
        if !suggestions.is_empty() {
            println!("  搜索建议:");
            for suggestion in suggestions.iter().take(5) {
                println!("    • {}", suggestion.trim());
            }
        }

        // 提交搜索
        // browser.press_key("Enter").await?;
    }

    Ok(())
}

/// 截图示例
async fn screenshot_example(browser: &BrowserManager) -> Result<(), Box<dyn std::error::Error>> {
    println!("📸 截图示例...\n");

    browser.navigate("https://www.rust-lang.org").await?;
    browser.wait_for_page_load(None).await?;

    // 全屏截图
    browser.screenshot_to_file("rust_lang_full.png").await?;
    println!("  ✓ 全屏截图：rust_lang_full.png");

    // 导航栏截图
    if browser.element_exists("nav").await? {
        let nav_img = browser.screenshot_element("nav").await?;
        std::fs::write("rust_nav.png", &nav_img)?;
        println!("  ✓ 导航栏截图：rust_nav.png");
    }

    Ok(())
}
