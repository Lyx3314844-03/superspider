//! Web 处理器
//! 
//! 处理 HTTP 请求

use axum::{
    routing::{get, post},
    Json, Router,
    extract::State,
    response::Html,
};
use std::sync::Arc;
use tokio::sync::RwLock;
use crate::web::models::{ApiResponse, HealthResponse, SpiderConfigRequest, SpiderStatusResponse, MetricsResponse};
use crate::monitor::MetricsCollector;

/// 应用状态
#[derive(Clone)]
pub struct AppState {
    pub metrics: MetricsCollector,
    pub spider_name: Arc<RwLock<String>>,
    pub is_running: Arc<RwLock<bool>>,
}

/// 创建路由
pub fn create_router(state: AppState) -> Router {
    Router::new()
        .route("/api/health", get(health_handler))
        .route("/api/metrics", get(metrics_handler))
        .route("/api/status", get(status_handler))
        .route("/api/spider/start", post(start_spider_handler))
        .route("/api/spider/stop", post(stop_spider_handler))
        .route("/api/spider/config", post(config_spider_handler))
        .with_state(state)
}

/// 健康检查处理器
async fn health_handler(
    State(state): State<AppState>,
) -> Json<ApiResponse<HealthResponse>> {
    let spider_name = state.spider_name.read().await;
    let is_running = state.is_running.read().await;
    
    let snapshot = state.metrics.snapshot();
    
    let response = HealthResponse {
        status: if *is_running { "running" } else { "stopped" }.to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        uptime_secs: snapshot.duration_secs,
    };
    
    drop(spider_name);
    drop(is_running);
    
    Json(ApiResponse::ok(response))
}

/// 指标处理器
async fn metrics_handler(
    State(state): State<AppState>,
) -> Json<ApiResponse<MetricsResponse>> {
    let snapshot = state.metrics.snapshot();
    
    let success_rate = if snapshot.pages_crawled > 0 {
        snapshot.pages_success as f64 / snapshot.pages_crawled as f64
    } else {
        0.0
    };
    
    let response = MetricsResponse {
        spider_name: snapshot.spider_name,
        health_status: snapshot.health_status().to_string(),
        pages_crawled: snapshot.pages_crawled,
        success_rate,
        avg_response_time_ms: snapshot.avg_response_time_ms,
        requests_per_second: snapshot.requests_per_second,
        total_bytes: snapshot.total_bytes,
        duration_secs: snapshot.duration_secs,
    };
    
    Json(ApiResponse::ok(response))
}

/// 状态处理器
async fn status_handler(
    State(state): State<AppState>,
) -> Json<ApiResponse<SpiderStatusResponse>> {
    let spider_name = state.spider_name.read().await;
    let is_running = state.is_running.read().await;
    let snapshot = state.metrics.snapshot();
    
    let response = SpiderStatusResponse {
        name: spider_name.clone(),
        status: if *is_running { "running" } else { "stopped" }.to_string(),
        pages_crawled: snapshot.pages_crawled,
        pages_success: snapshot.pages_success,
        pages_failed: snapshot.pages_failed,
        queue_size: snapshot.queue_size,
        active_threads: snapshot.active_threads,
        start_time: snapshot.start_time.clone(),
        uptime_secs: snapshot.duration_secs,
    };
    
    Json(ApiResponse::ok(response))
}

/// 启动爬虫处理器
async fn start_spider_handler(
    State(state): State<AppState>,
) -> Json<ApiResponse<String>> {
    let mut is_running = state.is_running.write().await;
    
    if *is_running {
        return Json(ApiResponse::error("Spider is already running"));
    }
    
    *is_running = true;
    state.metrics.start();
    
    Json(ApiResponse::ok("Spider started".to_string()))
}

/// 停止爬虫处理器
async fn stop_spider_handler(
    State(state): State<AppState>,
) -> Json<ApiResponse<String>> {
    let mut is_running = state.is_running.write().await;
    
    if !*is_running {
        return Json(ApiResponse::error("Spider is not running"));
    }
    
    *is_running = false;
    state.metrics.stop();
    
    Json(ApiResponse::ok("Spider stopped".to_string()))
}

/// 配置爬虫处理器
async fn config_spider_handler(
    State(state): State<AppState>,
    Json(config): Json<SpiderConfigRequest>,
) -> Json<ApiResponse<String>> {
    let mut spider_name = state.spider_name.write().await;
    *spider_name = config.name;
    
    Json(ApiResponse::ok(format!("Spider configured: {}", config.name)))
}
