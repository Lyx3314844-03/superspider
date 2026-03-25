//! 基础示例：简单的网页爬虫
//! 
//! 这个示例展示了如何创建一个基本的爬虫

use rust_spider::{Spider, Page, HtmlParser, ConsolePipeline};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 初始化日志
    env_logger::Builder::from_env(
        env_logger::Env::default().default_filter_or("info")
    ).init();
    
    println!("🕷️  RustSpider - 基础示例");
    println!("=====================================");
    
    // 创建爬虫
    let mut spider = Spider::new("basic_spider")
        .add_start_url("https://www.example.com")
        .set_thread_count(3)
        .add_pipeline(ConsolePipeline::new());
    
    // 添加页面处理器
    spider = spider.add_handler(|page: &Page| {
        let parser = HtmlParser::new(&page.html);
        
        // 提取标题
        if let Some(title) = parser.title() {
            println!("📄 页面标题：{}", title);
        }
        
        // 提取所有链接
        let links = parser.links();
        println!("🔗 找到 {} 个链接", links.len());
        
        // 提取所有图片
        let images = parser.images();
        println!("🖼️  找到 {} 张图片", images.len());
        
        // 提取段落
        let paragraphs = parser.paragraphs();
        println!("📝 找到 {} 个段落", paragraphs.len());
    });
    
    println!("\n🚀 开始爬取 https://www.example.com ...");
    println!();
    
    // 运行爬虫
    spider.run().await?;
    
    println!();
    println!("✅ 爬取完成！共爬取 {} 个页面", spider.crawled_count().await);
    
    Ok(())
}
