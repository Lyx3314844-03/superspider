//! RustSpider - 高性能 Web 爬虫框架
//! 
//! 这是一个示例程序，展示如何使用 RustSpider 爬虫框架

use rust_spider::{Spider, Page, HtmlParser};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 初始化日志
    env_logger::init();
    
    println!("🕷️  RustSpider v{}", rust_spider::VERSION);
    println!("=====================================");
    
    // 创建爬虫
    let mut spider = Spider::new("example_spider")
        .add_start_url("https://www.rust-lang.org")
        .add_start_url("https://github.com/rust-lang")
        .set_thread_count(5)
        .set_sleep_time(100)
        .add_pipeline(rust_spider::ConsolePipeline::new());
    
    // 添加自定义处理器
    spider = spider.add_handler(|page: &Page| {
        // 使用 HtmlParser 解析页面
        let parser = HtmlParser::new(&page.html);
        
        // 提取标题
        if let Some(title) = parser.title() {
            println!("📄 标题：{}", title);
        }
        
        // 提取所有链接
        let links = parser.links();
        println!("🔗 找到 {} 个链接", links.len());
        
        // 提取前 5 个链接
        for link in links.iter().take(5) {
            println!("   - {}", link);
        }
        
        // 添加新发现的链接到爬取队列
        for link in links.iter().take(3) {
            if link.starts_with("http") {
                page.add_target_url(link.clone());
            }
        }
    });
    
    println!("🚀 开始爬取...");
    println!();
    
    // 运行爬虫
    spider.run().await?;
    
    println!();
    println!("✅ 爬取完成！共爬取 {} 个页面", spider.crawled_count().await);
    
    Ok(())
}
