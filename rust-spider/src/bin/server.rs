//! RustSpider Web 服务器
//! 
//! 提供可视化 Web 界面和 REST API

use rust_spider::web::WebServer;
use rust_spider::init_logging;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 初始化日志
    init_logging();
    
    println!("🕷️  RustSpider Web Server v{}", env!("CARGO_PKG_VERSION"));
    println!("═══════════════════════════════════════════════");
    
    // 创建 Web 服务器
    let server = WebServer::new("0.0.0.0", 8080, "web_spider");
    
    println!("📡 API 地址：{}", server.api_url());
    println!("🖥️  Web UI 地址：{}", server.ui_url());
    println!("═══════════════════════════════════════════════");
    println!();
    println!("按 Ctrl+C 停止服务器...");
    println!();
    
    // 运行服务器
    server.run().await?;
    
    Ok(())
}
