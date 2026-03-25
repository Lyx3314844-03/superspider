//! Web 服务器
//! 
//! 提供 HTTP 服务

use axum::{Router, response::Html};
use tokio::net::TcpListener;
use log::info;
use crate::web::handlers::{create_router, AppState};
use crate::monitor::MetricsCollector;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Web 服务器
pub struct WebServer {
    host: String,
    port: u16,
    metrics: MetricsCollector,
    spider_name: Arc<RwLock<String>>,
    is_running: Arc<RwLock<bool>>,
}

impl WebServer {
    /// 创建新服务器
    pub fn new(host: impl Into<String>, port: u16, spider_name: impl Into<String>) -> Self {
        Self {
            host: host.into(),
            port,
            metrics: MetricsCollector::new(spider_name.as_ref()),
            spider_name: Arc::new(RwLock::new(spider_name.into())),
            is_running: Arc::new(RwLock::new(false)),
        }
    }
    
    /// 获取 API 地址
    pub fn api_url(&self) -> String {
        format!("http://{}:{}", self.host, self.port)
    }
    
    /// 获取 Web UI 地址
    pub fn ui_url(&self) -> String {
        format!("http://{}:{}/ui", self.host, self.port)
    }
    
    /// 获取指标收集器
    pub fn metrics(&self) -> &MetricsCollector {
        &self.metrics
    }
    
    /// 获取运行状态
    pub fn is_running(&self) -> Arc<RwLock<bool>> {
        self.is_running.clone()
    }
    
    /// 运行服务器
    pub async fn run(&self) -> Result<(), Box<dyn std::error::Error>> {
        let state = AppState {
            metrics: self.metrics.clone(),
            spider_name: self.spider_name.clone(),
            is_running: self.is_running.clone(),
        };
        
        let app = create_router(state)
            .route("/", get(root_handler))
            .route("/ui", get(ui_handler))
            .fallback(not_found_handler);
        
        let addr = format!("{}:{}", self.host, self.port);
        let listener = TcpListener::bind(&addr).await?;
        
        info!("🌐 Web 服务器启动于：{}", self.api_url());
        info!("📊 Web UI 访问于：{}", self.ui_url());
        
        axum::serve(listener, app).await?;
        
        Ok(())
    }
}

/// 根路径处理器
async fn root_handler() -> Html<&'static str> {
    Html(include_str!("../../static/index.html"))
}

/// UI 处理器
async fn ui_handler() -> Html<&'static str> {
    Html(include_str!("../../static/index.html"))
}

/// 404 处理器
async fn not_found_handler() -> Html<&'static str> {
    Html("<h1>404 Not Found</h1>")
}
