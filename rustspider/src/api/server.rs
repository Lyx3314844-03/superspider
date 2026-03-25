//! REST API 服务器

use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::Json,
    routing::{get, post, delete},
    Router,
};
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};

use crate::monitor::monitor::{MonitorCenter, SpiderMonitor};

/// API 状态
#[derive(Clone)]
pub struct ApiState {
    pub monitors: Arc<RwLock<std::collections::HashMap<String, Arc<RwLock<SpiderMonitor>>>>>,
    pub start_time: f64,
    pub requests_total: Arc<RwLock<usize>>,
    pub requests_by_endpoint: Arc<RwLock<std::collections::HashMap<String, usize>>>,
}

impl ApiState {
    pub fn new() -> Self {
        Self {
            monitors: Arc::new(RwLock::new(std::collections::HashMap::new())),
            start_time: current_timestamp(),
            requests_total: Arc::new(RwLock::new(0)),
            requests_by_endpoint: Arc::new(RwLock::new(std::collections::HashMap::new())),
        }
    }

    pub fn register_monitor(&self, name: &str, monitor: SpiderMonitor) {
        let mut monitors = self.monitors.blocking_write();
        monitors.insert(name.to_string(), Arc::new(RwLock::new(monitor)));
    }
}

impl Default for ApiState {
    fn default() -> Self {
        Self::new()
    }
}

/// 健康检查响应
#[derive(Serialize)]
pub struct HealthResponse {
    pub status: String,
    pub timestamp: f64,
    pub version: String,
}

/// 系统状态响应
#[derive(Serialize)]
pub struct StatusResponse {
    pub status: String,
    pub uptime_seconds: f64,
    pub spiders_count: usize,
    pub api_requests: usize,
}

/// 创建路由器
pub fn create_router(state: ApiState) -> Router {
    Router::new()
        // 健康检查
        .route("/health", get(health_check))
        .route("/api/v1/status", get(get_status))
        
        // 爬虫管理
        .route("/api/v1/spiders", get(list_spiders))
        .route("/api/v1/spiders/:name", get(get_spider))
        .route("/api/v1/spiders/:name/start", post(start_spider))
        .route("/api/v1/spiders/:name/stop", post(stop_spider))
        .route("/api/v1/spiders/:name/stats", get(get_spider_stats))
        
        // 监控
        .route("/api/v1/monitors", get(list_monitors))
        .route("/api/v1/monitors/:name/dashboard", get(get_dashboard))
        .route("/api/v1/metrics", get(get_metrics))
        
        // 统计
        .route("/api/v1/stats", get(get_api_stats))
        
        .with_state(state)
}

/// 健康检查
async fn health_check() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "healthy".to_string(),
        timestamp: current_timestamp(),
        version: "1.0.0".to_string(),
    })
}

/// 获取系统状态
async fn get_status(State(state): State<ApiState>) -> Json<StatusResponse> {
    let uptime = current_timestamp() - state.start_time;
    let monitors = state.monitors.read().await;
    let requests_total = *state.requests_total.read().await;

    Json(StatusResponse {
        status: "running".to_string(),
        uptime_seconds: uptime,
        spiders_count: monitors.len(),
        api_requests: requests_total,
    })
}

/// 获取爬虫列表
async fn list_spiders(State(state): State<ApiState>) -> Json<serde_json::Value> {
    let monitors = state.monitors.read().await;
    
    let spiders: serde_json::Map<String, _> = monitors
        .iter()
        .map(|(name, monitor)| {
            let m = monitor.blocking_read();
            (
                name.clone(),
                serde_json::json!({
                    "name": name,
                    "status": if m.running { "running" } else { "stopped" },
                    "stats": {
                        "pages_crawled": m.stats.pages_crawled,
                        "pages_failed": m.stats.pages_failed,
                    },
                }),
            )
        })
        .collect();

    Json(serde_json::json!({
        "spiders": spiders,
        "total": monitors.len(),
    }))
}

/// 获取爬虫详情
async fn get_spider(
    State(state): State<ApiState>,
    Path(name): Path<String>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let monitors = state.monitors.read().await;
    
    if let Some(monitor) = monitors.get(&name) {
        let m = monitor.read().await;
        Ok(Json(m.get_stats()))
    } else {
        Err(StatusCode::NOT_FOUND)
    }
}

/// 启动爬虫
async fn start_spider(
    State(state): State<ApiState>,
    Path(name): Path<String>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let monitors = state.monitors.read().await;
    
    if let Some(monitor) = monitors.get(&name) {
        let mut m = monitor.write().await;
        m.start();
        Ok(Json(serde_json::json!({
            "status": "started",
            "spider": name,
        })))
    } else {
        Err(StatusCode::NOT_FOUND)
    }
}

/// 停止爬虫
async fn stop_spider(
    State(state): State<ApiState>,
    Path(name): Path<String>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let monitors = state.monitors.read().await;
    
    if let Some(monitor) = monitors.get(&name) {
        let mut m = monitor.write().await;
        m.stop();
        Ok(Json(serde_json::json!({
            "status": "stopped",
            "spider": name,
        })))
    } else {
        Err(StatusCode::NOT_FOUND)
    }
}

/// 获取爬虫统计
async fn get_spider_stats(
    State(state): State<ApiState>,
    Path(name): Path<String>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let monitors = state.monitors.read().await;
    
    if let Some(monitor) = monitors.get(&name) {
        let m = monitor.read().await;
        Ok(Json(m.get_stats()))
    } else {
        Err(StatusCode::NOT_FOUND)
    }
}

/// 获取监控器列表
async fn list_monitors(State(state): State<ApiState>) -> Json<serde_json::Value> {
    let monitors = state.monitors.read().await;
    
    let monitors_info: serde_json::Map<String, _> = monitors
        .iter()
        .map(|(name, monitor)| {
            let m = monitor.blocking_read();
            (
                name.clone(),
                serde_json::json!({
                    "name": name,
                    "status": if m.running { "running" } else { "stopped" },
                }),
            )
        })
        .collect();

    Json(serde_json::json!({
        "monitors": monitors_info,
        "total": monitors.len(),
    }))
}

/// 获取仪表盘数据
async fn get_dashboard(
    State(state): State<ApiState>,
    Path(name): Path<String>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let monitors = state.monitors.read().await;
    
    if let Some(monitor) = monitors.get(&name) {
        let m = monitor.read().await;
        Ok(Json(m.get_dashboard_data()))
    } else {
        Err(StatusCode::NOT_FOUND)
    }
}

/// 获取性能指标
async fn get_metrics(State(state): State<ApiState>) -> Json<serde_json::Value> {
    let monitors = state.monitors.read().await;
    
    let metrics: serde_json::Map<String, _> = monitors
        .iter()
        .map(|(name, monitor)| {
            let m = monitor.blocking_read();
            let stats = m.get_stats();
            (
                name.clone(),
                serde_json::json!({
                    "performance": stats.get("performance"),
                    "resources": stats.get("resources"),
                }),
            )
        })
        .collect();

    Json(serde_json::json!({
        "metrics": metrics,
    }))
}

/// 获取 API 统计
async fn get_api_stats(State(state): State<ApiState>) -> Json<serde_json::Value> {
    let uptime = current_timestamp() - state.start_time;
    let requests_total = *state.requests_total.read().await;
    let requests_by_endpoint = state.requests_by_endpoint.read().await;
    let monitors = state.monitors.read().await;

    Json(serde_json::json!({
        "api": {
            "uptime_seconds": uptime,
            "total_requests": requests_total,
            "requests_by_endpoint": *requests_by_endpoint,
        },
        "spiders": monitors.len(),
    }))
}

/// 运行 API 服务器
pub async fn run_server(host: &str, port: u16) -> Result<(), Box<dyn std::error::Error>> {
    let state = ApiState::new();
    let app = create_router(state);

    let addr = format!("{}:{}", host, port);
    println!("Starting API server on {}", addr);

    let listener = tokio::net::TcpListener::bind(&addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

fn current_timestamp() -> f64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs_f64()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_health_check() {
        let response = health_check().await;
        assert_eq!(response.status, "healthy");
    }
}
