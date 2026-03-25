//! Web Spider 示例：带可视化界面的爬虫
//! 
//! 这个示例展示了如何启动带 Web UI 的爬虫

use rust_spider::{Spider, Page, HtmlParser, WebServer, MetricsCollector};
use std::sync::Arc;
use tokio::sync::RwLock;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 初始化日志
    rust_spider::init_logging();
    
    println!("🕷️  RustSpider - Web 可视化示例");
    println!("═══════════════════════════════════════════════");
    
    // 创建 Web 服务器
    let web_server = WebServer::new("0.0.0.0", 8080, "web_spider");
    
    println!("📡 API 地址：http://0.0.0.0:8080");
    println!("🖥️  Web UI 地址：http://0.0.0.0:8080/ui");
    println!("═══════════════════════════════════════════════");
    println!();
    
    // 获取指标收集器
    let metrics = web_server.metrics().clone();
    let is_running = web_server.is_running();
    
    // 创建爬虫
    let mut spider = Spider::new("web_spider")
        .add_start_url("https://www.rust-lang.org")
        .add_start_url("https://github.com/rust-lang")
        .set_thread_count(10)
        .set_sleep_time(100)
        .add_pipeline(rust_spider::ConsolePipeline::new());
    
    // 添加自定义处理器（带指标记录）
    let metrics_clone = metrics.clone();
    spider = spider.add_handler(move |page: &Page| {
        let parser = HtmlParser::new(&page.html);
        
        // 提取标题
        if let Some(title) = parser.title() {
            println!("📄 标题：{}", title);
        }
        
        // 提取链接
        let links = parser.links();
        println!("🔗 找到 {} 个链接", links.len());
        
        // 记录指标
        metrics_clone.record_page(
            page.response.elapsed_ms,
            page.response.bytes.len() as u64,
            page.response.is_success(),
        );
    });
    
    // 在后台运行爬虫
    let spider_handle = tokio::spawn(async move {
        println!("🚀 爬虫启动...");
        metrics.start();
        
        {
            let mut running = is_running.write().await;
            *running = true;
        }
        
        match spider.run().await {
            Ok(_) => println!("✅ 爬虫完成"),
            Err(e) => eprintln!("❌ 爬虫失败：{}", e),
        }
        
        metrics.stop();
        
        {
            let mut running = is_running.write().await;
            *running = false;
        }
    });
    
    // 运行 Web 服务器
    println!("按 Ctrl+C 停止...\n");
    
    tokio::select! {
        _ = web_server.run() => {
            println!("Web 服务器已停止");
        }
        _ = spider_handle => {
            println!("爬虫任务已完成");
        }
        _ = tokio::signal::ctrl_c() => {
            println!("\n收到停止信号...");
            
            // 优雅关闭
            metrics.stop();
            {
                let mut running = is_running.write().await;
                *running = false;
            }
            
            // 打印指标总结
            metrics.print_summary();
        }
    }
    
    Ok(())
}
