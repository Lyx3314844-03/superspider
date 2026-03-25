//! RustSpider Web UI - 基于 Actix-web
//! 
//! 提供爬虫任务管理、监控和结果查看功能

use actix_web::{web, App, HttpResponse, HttpServer, Responder, get, post, delete};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use chrono::{DateTime, Utc};

/// 任务状态
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TaskStatus {
    Pending,
    Running,
    Completed,
    Failed,
    Stopped,
}

/// 任务信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskInfo {
    pub id: String,
    pub name: String,
    pub url: String,
    pub status: TaskStatus,
    pub config: serde_json::Value,
    pub created_at: DateTime<Utc>,
    pub started_at: Option<DateTime<Utc>>,
    pub finished_at: Option<DateTime<Utc>>,
    pub stats: TaskStats,
}

/// 任务统计
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TaskStats {
    pub total_requests: u64,
    pub success_requests: u64,
    pub failed_requests: u64,
}

/// 任务管理器
pub struct TaskManager {
    tasks: RwLock<HashMap<String, TaskInfo>>,
}

impl TaskManager {
    pub fn new() -> Self {
        Self {
            tasks: RwLock::new(HashMap::new()),
        }
    }

    pub fn list(&self) -> Vec<TaskInfo> {
        let tasks = self.tasks.read().unwrap();
        tasks.values().cloned().collect()
    }

    pub fn get(&self, id: &str) -> Option<TaskInfo> {
        let tasks = self.tasks.read().unwrap();
        tasks.get(id).cloned()
    }

    pub fn create(&self, task: TaskInfo) {
        let mut tasks = self.tasks.write().unwrap();
        tasks.insert(task.id.clone(), task);
    }

    pub fn update(&self, id: &str, task: TaskInfo) {
        let mut tasks = self.tasks.write().unwrap();
        tasks.insert(id.to_string(), task);
    }

    pub fn delete(&self, id: &str) {
        let mut tasks = self.tasks.write().unwrap();
        tasks.remove(id);
    }
}

/// 应用状态
pub struct AppState {
    pub task_manager: Arc<TaskManager>,
}

/// API 响应
#[derive(Debug, Serialize)]
pub struct ApiResponse<T> {
    pub success: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<T>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

impl<T: Serialize> ApiResponse<T> {
    pub fn success(data: T) -> Self {
        Self {
            success: true,
            data: Some(data),
            error: None,
        }
    }

    pub fn error(msg: &str) -> Self {
        Self {
            success: false,
            data: None,
            error: Some(msg.to_string()),
        }
    }
}

/// 请求参数
#[derive(Debug, Deserialize)]
pub struct CreateTaskRequest {
    pub name: Option<String>,
    pub url: String,
    pub config: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize)]
pub struct PaginationParams {
    #[serde(default = "default_page")]
    pub page: u32,
    #[serde(default = "default_per_page")]
    pub per_page: u32,
}

fn default_page() -> u32 { 1 }
fn default_per_page() -> u32 { 20 }

// ==================== API 路由 ====================

#[get("/api/tasks")]
async fn list_tasks(data: web::Data<AppState>) -> impl Responder {
    let tasks = data.task_manager.list();
    HttpResponse::Ok().json(ApiResponse::success(tasks))
}

#[post("/api/tasks")]
async fn create_task(
    data: web::Data<AppState>,
    body: web::Json<CreateTaskRequest>,
) -> impl Responder {
    if body.url.is_empty() {
        return HttpResponse::BadRequest().json(ApiResponse::<()>::error("URL is required"));
    }

    let id = Utc::now().format("%Y%m%d%H%M%S").to_string();
    let task = TaskInfo {
        id: id.clone(),
        name: body.name.clone().unwrap_or_else(|| "Unnamed Task".to_string()),
        url: body.url.clone(),
        status: TaskStatus::Pending,
        config: body.config.clone().unwrap_or(serde_json::json!({})),
        created_at: Utc::now(),
        started_at: None,
        finished_at: None,
        stats: TaskStats::default(),
    };

    data.task_manager.create(task);

    HttpResponse::Ok().json(ApiResponse::success(serde_json::json!({ "id": id })))
}

#[get("/api/tasks/{id}")]
async fn get_task(
    data: web::Data<AppState>,
    path: web::Path<String>,
) -> impl Responder {
    let id = path.into_inner();
    match data.task_manager.get(&id) {
        Some(task) => HttpResponse::Ok().json(ApiResponse::success(task)),
        None => HttpResponse::NotFound().json(ApiResponse::<()>::error("Task not found")),
    }
}

#[post("/api/tasks/{id}/start")]
async fn start_task(
    data: web::Data<AppState>,
    path: web::Path<String>,
) -> impl Responder {
    let id = path.into_inner();
    
    if let Some(mut task) = data.task_manager.get(&id) {
        task.status = TaskStatus::Running;
        task.started_at = Some(Utc::now());
        data.task_manager.update(&id, task);
        HttpResponse::Ok().json(ApiResponse::success(serde_json::json!({ "message": "Task started" })))
    } else {
        HttpResponse::NotFound().json(ApiResponse::<()>::error("Task not found"))
    }
}

#[post("/api/tasks/{id}/stop")]
async fn stop_task(
    data: web::Data<AppState>,
    path: web::Path<String>,
) -> impl Responder {
    let id = path.into_inner();
    
    if let Some(mut task) = data.task_manager.get(&id) {
        task.status = TaskStatus::Stopped;
        task.finished_at = Some(Utc::now());
        data.task_manager.update(&id, task);
        HttpResponse::Ok().json(ApiResponse::success(serde_json::json!({ "message": "Task stopped" })))
    } else {
        HttpResponse::NotFound().json(ApiResponse::<()>::error("Task not found"))
    }
}

#[delete("/api/tasks/{id}")]
async fn delete_task(
    data: web::Data<AppState>,
    path: web::Path<String>,
) -> impl Responder {
    let id = path.into_inner();
    data.task_manager.delete(&id);
    HttpResponse::Ok().json(ApiResponse::success(serde_json::json!({ "message": "Task deleted" })))
}

#[get("/api/tasks/{id}/results")]
async fn get_task_results(
    _data: web::Data<AppState>,
    _path: web::Path<String>,
    _query: web::Query<PaginationParams>,
) -> impl Responder {
    // TODO: 实现结果查询
    HttpResponse::Ok().json(ApiResponse::success(Vec::<serde_json::Value>::new()))
}

#[get("/api/tasks/{id}/logs")]
async fn get_task_logs(
    _data: web::Data<AppState>,
    _path: web::Path<String>,
    _query: web::Query<PaginationParams>,
) -> impl Responder {
    // TODO: 实现日志查询
    HttpResponse::Ok().json(ApiResponse::success(Vec::<serde_json::Value>::new()))
}

#[get("/api/stats")]
async fn get_stats(data: web::Data<AppState>) -> impl Responder {
    let tasks = data.task_manager.list();
    
    let total = tasks.len();
    let running = tasks.iter().filter(|t| matches!(t.status, TaskStatus::Running)).count();
    let completed = tasks.iter().filter(|t| matches!(t.status, TaskStatus::Completed)).count();

    HttpResponse::Ok().json(ApiResponse::success(serde_json::json!({
        "total_tasks": total,
        "running_tasks": running,
        "completed_tasks": completed,
    })))
}

// ==================== 页面路由 ====================

async fn index_page() -> impl Responder {
    HttpResponse::Ok().content_type("text/html").body(include_str!("../templates/index.html"))
}

async fn tasks_page() -> impl Responder {
    HttpResponse::Ok().content_type("text/html").body(include_str!("../templates/tasks.html"))
}

async fn task_detail_page(path: web::Path<String>) -> impl Responder {
    let task_id = path.into_inner();
    let html = include_str!("../templates/task_detail.html")
        .replace("{{task_id}}", &task_id);
    HttpResponse::Ok().content_type("text/html").body(html)
}

// ==================== 服务器启动 ====================

pub async fn run_server(host: &str, port: u16) -> std::io::Result<()> {
    let task_manager = Arc::new(TaskManager::new());
    let app_state = web::Data::new(AppState { task_manager });

    println!("🚀 Starting web UI at http://{}:{}", host, port);

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .configure(|cfg| {
                cfg.service(list_tasks)
                    .service(create_task)
                    .service(get_task)
                    .service(start_task)
                    .service(stop_task)
                    .service(delete_task)
                    .service(get_task_results)
                    .service(get_task_logs)
                    .service(get_stats);
            })
            .route("/", web::get().to(index_page))
            .route("/tasks", web::get().to(tasks_page))
            .route("/tasks/{id}", web::get().to(task_detail_page))
    })
    .bind(format!("{}:{}", host, port))?
    .run()
    .await
}
