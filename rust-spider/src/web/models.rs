//! Web API 数据模型

use serde::{Deserialize, Serialize};

/// Spider 配置请求
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpiderConfigRequest {
    pub name: String,
    pub start_urls: Vec<String>,
    pub thread_count: usize,
    pub sleep_time_ms: u64,
    pub max_pages: Option<u32>,
    pub user_agent: Option<String>,
    pub allowed_domains: Option<Vec<String>>,
}

/// Spider 状态响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpiderStatusResponse {
    pub name: String,
    pub status: String,
    pub pages_crawled: u64,
    pub pages_success: u64,
    pub pages_failed: u64,
    pub queue_size: u64,
    pub active_threads: u32,
    pub start_time: Option<String>,
    pub uptime_secs: f64,
}

/// 指标响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricsResponse {
    pub spider_name: String,
    pub health_status: String,
    pub pages_crawled: u64,
    pub success_rate: f64,
    pub avg_response_time_ms: f64,
    pub requests_per_second: f64,
    pub total_bytes: u64,
    pub duration_secs: f64,
}

/// 健康检查响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub version: String,
    pub uptime_secs: f64,
}

/// 任务列表响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskListResponse {
    pub tasks: Vec<TaskInfo>,
    pub total: usize,
}

/// 任务信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskInfo {
    pub id: String,
    pub name: String,
    pub status: String,
    pub progress: f64,
    pub created_at: String,
}

/// API 响应包装器
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiResponse<T> {
    pub success: bool,
    pub data: Option<T>,
    pub error: Option<String>,
}

impl<T: Serialize> ApiResponse<T> {
    pub fn ok(data: T) -> Self {
        Self {
            success: true,
            data: Some(data),
            error: None,
        }
    }
    
    pub fn error(message: impl Into<String>) -> Self {
        Self {
            success: false,
            data: None,
            error: Some(message.into()),
        }
    }
}
