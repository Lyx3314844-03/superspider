//! 高级示例：带有数据提取和存储的爬虫
//! 
//! 这个示例展示了如何使用高级功能：
//! - 自定义配置
//! - 多管道输出
//! - 数据提取
//! - 错误处理

use rust_spider::{Spider, Page, HtmlParser, Config, Site, ConsolePipeline, JsonFilePipeline};
use std::collections::HashMap;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 初始化日志
    env_logger::Builder::from_env(
        env_logger::Env::default().default_filter_or("debug")
    ).init();
    
    println!("🕷️  RustSpider - 高级示例");
    println!("=====================================");
    
    // 创建配置
    let config = Config::create("advanced_spider")
        .with_thread_count(10)
        .with_deduplication(true)
        .with_log_level("info")
        .with_max_pages(100);
    
    // 创建站点配置
    let site = Site::create()
        .add_start_url("https://www.rust-lang.org")
        .add_start_url("https://github.com/rust-lang")
        .set_user_agent("Mozilla/5.0 (compatible; RustSpider/1.0)")
        .set_sleep_time(50)
        .set_retry_times(3);
    
    // 创建爬虫
    let mut spider = Spider::with_config(config)
        .site(site)
        .add_pipeline(ConsolePipeline::verbose())
        .add_pipeline(JsonFilePipeline::new("output/rust_spider.json")?);
    
    // 添加自定义处理器
    spider = spider.add_handler(|page: &Page| {
        let parser = HtmlParser::new(&page.html);
        
        // 提取数据
        let mut data = HashMap::new();
        
        // 标题
        if let Some(title) = parser.title() {
            data.insert("title".to_string(), title);
            println!("📄 标题：{}", title);
        }
        
        // 元描述
        if let Some(description) = parser.meta("description") {
            data.insert("description".to_string(), description);
        }
        
        // Open Graph 数据
        if let Some(og_title) = parser.og("og:title") {
            data.insert("og_title".to_string(), og_title);
        }
        
        // 提取所有链接
        let links = parser.links();
        data.insert("link_count".to_string(), links.len().to_string());
        
        // 提取内部链接和外部链接
        let mut internal_links = Vec::new();
        let mut external_links = Vec::new();
        
        for link in &links {
            if link.contains("rust-lang.org") || link.contains("github.com/rust-lang") {
                internal_links.push(link.clone());
            } else {
                external_links.push(link.clone());
            }
        }
        
        println!("🔗 内部链接：{}, 外部链接：{}", internal_links.len(), external_links.len());
        
        // 添加新链接到爬取队列（限制数量）
        for link in internal_links.iter().take(5) {
            page.add_target_url(link.clone());
        }
        
        // 存储提取的数据
        for (key, value) in &data {
            page.put_field(key.clone(), value.clone());
        }
    });
    
    println!("\n🚀 开始爬取...");
    println!("📁 输出文件：output/rust_spider.json");
    println!();
    
    // 运行爬虫
    match spider.run().await {
        Ok(_) => {
            println!();
            println!("✅ 爬取完成！共爬取 {} 个页面", spider.crawled_count().await);
        }
        Err(e) => {
            eprintln!("❌ 爬取失败：{}", e);
        }
    }
    
    Ok(())
}
