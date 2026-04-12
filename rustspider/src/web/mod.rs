//! RustSpider Web UI - 基于 Actix-web
//!
//! 提供可运行的任务生命周期控制面：创建、启动、停止、结果、日志与统计。

use crate::graph::GraphBuilder;
use actix_web::{delete, get, post, web, App, HttpRequest, HttpResponse, HttpServer, Responder};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::sync::{Arc, RwLock};
use std::time::Duration;
use tokio::sync::watch;

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum TaskStatus {
    Pending,
    Running,
    Completed,
    Failed,
    Stopped,
}

#[derive(Debug, Clone, Serialize)]
pub struct TaskInfo {
    pub id: String,
    pub name: String,
    pub url: String,
    pub status: TaskStatus,
    pub config: serde_json::Value,
    pub created_at: String,
    pub started_at: Option<String>,
    pub finished_at: Option<String>,
    pub stats: TaskStats,
}

#[derive(Debug, Clone, Serialize, Default)]
pub struct TaskStats {
    pub total_requests: u64,
    pub success_requests: u64,
    pub failed_requests: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct TaskResult {
    pub id: String,
    pub task_id: String,
    pub url: String,
    pub final_url: String,
    pub status: String,
    pub http_status: u16,
    pub content_type: String,
    pub title: String,
    pub bytes: usize,
    pub duration_ms: i64,
    pub created_at: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub artifacts: Option<HashMap<String, TaskArtifact>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub artifact_refs: Option<HashMap<String, TaskArtifact>>,
}

#[derive(Debug, Clone, Serialize)]
pub struct TaskLog {
    pub id: String,
    pub task_id: String,
    pub level: String,
    pub message: String,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct TaskArtifact {
    pub kind: String,
    pub path: String,
    pub root_id: String,
    pub stats: serde_json::Value,
}

pub struct TaskManager {
    tasks: RwLock<HashMap<String, TaskInfo>>,
    results: RwLock<HashMap<String, Vec<TaskResult>>>,
    logs: RwLock<HashMap<String, Vec<TaskLog>>>,
    cancels: RwLock<HashMap<String, watch::Sender<bool>>>,
}

impl Default for TaskManager {
    fn default() -> Self {
        Self::new()
    }
}

impl TaskManager {
    pub fn new() -> Self {
        Self {
            tasks: RwLock::new(HashMap::new()),
            results: RwLock::new(HashMap::new()),
            logs: RwLock::new(HashMap::new()),
            cancels: RwLock::new(HashMap::new()),
        }
    }

    pub fn list(&self) -> Vec<TaskInfo> {
        self.tasks.read().unwrap().values().cloned().collect()
    }

    pub fn get(&self, id: &str) -> Option<TaskInfo> {
        self.tasks.read().unwrap().get(id).cloned()
    }

    pub fn create(&self, task: TaskInfo) {
        self.tasks.write().unwrap().insert(task.id.clone(), task);
    }

    pub fn update(&self, id: &str, task: TaskInfo) {
        self.tasks.write().unwrap().insert(id.to_string(), task);
    }

    pub fn delete(&self, id: &str) {
        self.tasks.write().unwrap().remove(id);
        self.results.write().unwrap().remove(id);
        self.logs.write().unwrap().remove(id);
        self.cancels.write().unwrap().remove(id);
    }

    pub fn add_result(&self, id: &str, result: TaskResult) {
        persist_control_plane_record("results.jsonl", &result);
        self.results
            .write()
            .unwrap()
            .entry(id.to_string())
            .or_default()
            .push(result);
    }

    pub fn list_results(&self, id: &str) -> Vec<TaskResult> {
        self.results
            .read()
            .unwrap()
            .get(id)
            .cloned()
            .unwrap_or_default()
    }

    pub fn add_log(&self, id: &str, level: &str, message: impl Into<String>) {
        let record = TaskLog {
            id: format!(
                "log-{}",
                Utc::now().timestamp_nanos_opt().unwrap_or_default()
            ),
            task_id: id.to_string(),
            level: level.to_string(),
            message: message.into(),
            created_at: timestamp_string(Utc::now()),
        };
        persist_control_plane_record("events.jsonl", &record);
        self.logs
            .write()
            .unwrap()
            .entry(id.to_string())
            .or_default()
            .push(record);
    }

    pub fn list_logs(&self, id: &str) -> Vec<TaskLog> {
        self.logs
            .read()
            .unwrap()
            .get(id)
            .cloned()
            .unwrap_or_default()
    }

    pub fn set_cancel(&self, id: &str, tx: watch::Sender<bool>) {
        self.cancels.write().unwrap().insert(id.to_string(), tx);
    }

    pub fn cancel(&self, id: &str) {
        if let Some(tx) = self.cancels.write().unwrap().remove(id) {
            let _ = tx.send(true);
        }
    }
}

pub struct AppState {
    pub task_manager: Arc<TaskManager>,
    pub api_token: String,
}

fn resolve_api_token() -> String {
    std::env::var("RUSTSPIDER_API_TOKEN")
        .or_else(|_| std::env::var("SPIDER_API_TOKEN"))
        .unwrap_or_default()
        .trim()
        .to_string()
}

fn auth_enabled(state: &AppState) -> bool {
    !state.api_token.trim().is_empty()
}

fn auth_token(req: &HttpRequest) -> String {
    let authorization = req
        .headers()
        .get("Authorization")
        .and_then(|value| value.to_str().ok())
        .unwrap_or_default()
        .trim()
        .to_string();
    if let Some(bearer) = authorization.strip_prefix("Bearer ") {
        let trimmed = bearer.trim();
        if !trimmed.is_empty() {
            return trimmed.to_string();
        }
    }
    if !authorization.is_empty() {
        return authorization;
    }
    req.headers()
        .get("X-API-Token")
        .and_then(|value| value.to_str().ok())
        .unwrap_or_default()
        .trim()
        .to_string()
}

fn ensure_authorized(req: &HttpRequest, data: &web::Data<AppState>) -> Option<HttpResponse> {
    if !auth_enabled(data) {
        return None;
    }
    let token = auth_token(req);
    if token == data.api_token {
        return None;
    }
    Some(HttpResponse::Unauthorized().json(ApiResponse::<serde_json::Value>::error("unauthorized")))
}

fn control_plane_dir() -> PathBuf {
    PathBuf::from("artifacts").join("control-plane")
}

fn persist_control_plane_record<T: Serialize>(filename: &str, payload: &T) {
    let path = control_plane_dir().join(filename);
    if let Some(parent) = path.parent() {
        if fs::create_dir_all(parent).is_err() {
            return;
        }
    }
    let Ok(json) = serde_json::to_string(payload) else {
        return;
    };
    let Ok(mut handle) = OpenOptions::new().create(true).append(true).open(&path) else {
        return;
    };
    let _ = writeln!(handle, "{}", json);
}

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

#[derive(Debug, Deserialize)]
pub struct GraphExtractRequest {
    pub html: Option<String>,
    pub url: Option<String>,
}

fn default_page() -> u32 {
    1
}

fn default_per_page() -> u32 {
    20
}

#[get("/api/tasks")]
async fn list_tasks(
    req: HttpRequest,
    data: web::Data<AppState>,
    query: web::Query<PaginationParams>,
) -> impl Responder {
    if let Some(response) = ensure_authorized(&req, &data) {
        return response;
    }
    let tasks = data.task_manager.list();
    let (data_slice, total) = paginate(&tasks, query.page, query.per_page);
    HttpResponse::Ok().json(serde_json::json!({
        "success": true,
        "data": data_slice,
        "pagination": {
            "page": query.page,
            "per_page": query.per_page,
            "total": total,
        }
    }))
}

#[post("/api/tasks")]
async fn create_task(
    req: HttpRequest,
    data: web::Data<AppState>,
    body: web::Json<CreateTaskRequest>,
) -> impl Responder {
    if let Some(response) = ensure_authorized(&req, &data) {
        return response;
    }
    if body.url.trim().is_empty() {
        return HttpResponse::BadRequest().json(ApiResponse::<()>::error("URL is required"));
    }

    let id = format!(
        "task-{}",
        Utc::now().timestamp_nanos_opt().unwrap_or_default()
    );
    let task = TaskInfo {
        id: id.clone(),
        name: body
            .name
            .clone()
            .unwrap_or_else(|| "Unnamed Task".to_string()),
        url: body.url.clone(),
        status: TaskStatus::Pending,
        config: body.config.clone().unwrap_or_else(|| serde_json::json!({})),
        created_at: timestamp_string(Utc::now()),
        started_at: None,
        finished_at: None,
        stats: TaskStats::default(),
    };
    data.task_manager.create(task);
    data.task_manager.add_log(&id, "info", "task created");

    HttpResponse::Ok().json(ApiResponse::success(serde_json::json!({ "id": id })))
}

#[get("/api/tasks/{id}")]
async fn get_task(
    req: HttpRequest,
    data: web::Data<AppState>,
    path: web::Path<String>,
) -> impl Responder {
    if let Some(response) = ensure_authorized(&req, &data) {
        return response;
    }
    match data.task_manager.get(&path.into_inner()) {
        Some(task) => HttpResponse::Ok().json(ApiResponse::success(task)),
        None => HttpResponse::NotFound().json(ApiResponse::<()>::error("Task not found")),
    }
}

#[post("/api/tasks/{id}/start")]
async fn start_task(
    req: HttpRequest,
    data: web::Data<AppState>,
    path: web::Path<String>,
) -> impl Responder {
    if let Some(response) = ensure_authorized(&req, &data) {
        return response;
    }
    let id = path.into_inner();
    let Some(mut task) = data.task_manager.get(&id) else {
        return HttpResponse::NotFound().json(ApiResponse::<()>::error("Task not found"));
    };
    if task.status == TaskStatus::Running {
        return HttpResponse::Conflict().json(ApiResponse::<()>::error("Task is already running"));
    }

    task.status = TaskStatus::Running;
    task.started_at = Some(timestamp_string(Utc::now()));
    task.finished_at = None;
    task.stats = TaskStats::default();
    data.task_manager.update(&id, task.clone());
    data.task_manager.add_log(&id, "info", "task started");

    let (cancel_tx, cancel_rx) = watch::channel(false);
    data.task_manager.set_cancel(&id, cancel_tx);

    let manager = data.task_manager.clone();
    let task_id = id.clone();
    let target_url = task.url.clone();
    tokio::spawn(async move {
        run_task(manager, task_id, target_url, cancel_rx).await;
    });

    HttpResponse::Ok().json(ApiResponse::success(
        serde_json::json!({ "message": "Task started" }),
    ))
}

#[post("/api/tasks/{id}/stop")]
async fn stop_task(
    req: HttpRequest,
    data: web::Data<AppState>,
    path: web::Path<String>,
) -> impl Responder {
    if let Some(response) = ensure_authorized(&req, &data) {
        return response;
    }
    let id = path.into_inner();
    let Some(mut task) = data.task_manager.get(&id) else {
        return HttpResponse::NotFound().json(ApiResponse::<()>::error("Task not found"));
    };

    data.task_manager.cancel(&id);
    task.status = TaskStatus::Stopped;
    task.finished_at = Some(timestamp_string(Utc::now()));
    data.task_manager.update(&id, task);
    data.task_manager
        .add_log(&id, "warning", "task stop requested");

    HttpResponse::Ok().json(ApiResponse::success(
        serde_json::json!({ "message": "Task stopped" }),
    ))
}

#[delete("/api/tasks/{id}")]
async fn delete_task(
    req: HttpRequest,
    data: web::Data<AppState>,
    path: web::Path<String>,
) -> impl Responder {
    if let Some(response) = ensure_authorized(&req, &data) {
        return response;
    }
    let id = path.into_inner();
    data.task_manager.cancel(&id);
    data.task_manager.delete(&id);
    HttpResponse::Ok().json(ApiResponse::success(
        serde_json::json!({ "message": "Task deleted" }),
    ))
}

#[get("/api/tasks/{id}/results")]
async fn get_task_results(
    req: HttpRequest,
    data: web::Data<AppState>,
    path: web::Path<String>,
    query: web::Query<PaginationParams>,
) -> impl Responder {
    if let Some(response) = ensure_authorized(&req, &data) {
        return response;
    }
    let results = data.task_manager.list_results(&path.into_inner());
    let (data_slice, total) = paginate(&results, query.page, query.per_page);
    HttpResponse::Ok().json(serde_json::json!({
        "success": true,
        "data": data_slice,
        "pagination": {
            "page": query.page,
            "per_page": query.per_page,
            "total": total,
        }
    }))
}

#[get("/api/tasks/{id}/logs")]
async fn get_task_logs(
    req: HttpRequest,
    data: web::Data<AppState>,
    path: web::Path<String>,
    query: web::Query<PaginationParams>,
) -> impl Responder {
    if let Some(response) = ensure_authorized(&req, &data) {
        return response;
    }
    let logs = data.task_manager.list_logs(&path.into_inner());
    let (data_slice, total) = paginate(&logs, query.page, query.per_page);
    HttpResponse::Ok().json(serde_json::json!({
        "success": true,
        "data": data_slice,
        "pagination": {
            "page": query.page,
            "per_page": query.per_page,
            "total": total,
        }
    }))
}

#[get("/api/tasks/{id}/artifacts")]
async fn get_task_artifacts(data: web::Data<AppState>, path: web::Path<String>) -> impl Responder {
    let results = data.task_manager.list_results(&path.into_inner());
    let mut artifacts = HashMap::<String, TaskArtifact>::new();
    for result in results {
        if let Some(current) = result.artifacts {
            for (name, artifact) in current {
                artifacts.entry(name).or_insert(artifact);
            }
        }
    }
    HttpResponse::Ok().json(ApiResponse::success(artifacts))
}

#[get("/api/stats")]
async fn get_stats(req: HttpRequest, data: web::Data<AppState>) -> impl Responder {
    if let Some(response) = ensure_authorized(&req, &data) {
        return response;
    }
    let tasks = data.task_manager.list();
    let total = tasks.len();
    let running = tasks
        .iter()
        .filter(|task| matches!(task.status, TaskStatus::Running))
        .count();
    let completed = tasks
        .iter()
        .filter(|task| matches!(task.status, TaskStatus::Completed))
        .count();

    HttpResponse::Ok().json(ApiResponse::success(serde_json::json!({
        "total_tasks": total,
        "running_tasks": running,
        "completed_tasks": completed,
    })))
}

async fn extract_graph_impl(body: GraphExtractRequest) -> HttpResponse {
    let html = if let Some(html) = body.html.as_ref().filter(|value| !value.trim().is_empty()) {
        html.clone()
    } else if let Some(url) = body.url.as_ref().filter(|value| !value.trim().is_empty()) {
        match reqwest::get(url).await {
            Ok(response) => match response.text().await {
                Ok(text) => text,
                Err(err) => {
                    return HttpResponse::BadRequest().json(ApiResponse::<()>::error(&format!(
                        "failed to read graph url body: {err}"
                    )));
                }
            },
            Err(err) => {
                return HttpResponse::BadRequest().json(ApiResponse::<()>::error(&format!(
                    "failed to fetch graph url: {err}"
                )));
            }
        }
    } else {
        return HttpResponse::BadRequest()
            .json(ApiResponse::<()>::error("html or url is required"));
    };

    let mut graph = GraphBuilder::new();
    graph.rebuild_from_html(&html);
    HttpResponse::Ok().json(ApiResponse::success(serde_json::json!({
        "root_id": graph.root_id,
        "nodes": graph.nodes,
        "edges": graph.edges,
        "stats": graph.stats(),
    })))
}

#[post("/api/graph/extract")]
async fn extract_graph(
    req: HttpRequest,
    data: web::Data<AppState>,
    body: web::Json<GraphExtractRequest>,
) -> impl Responder {
    if let Some(response) = ensure_authorized(&req, &data) {
        return response;
    }
    extract_graph_impl(body.into_inner()).await
}

#[post("/api/v1/graph/extract")]
async fn extract_graph_v1(
    req: HttpRequest,
    data: web::Data<AppState>,
    body: web::Json<GraphExtractRequest>,
) -> impl Responder {
    if let Some(response) = ensure_authorized(&req, &data) {
        return response;
    }
    extract_graph_impl(body.into_inner()).await
}

async fn index_page() -> impl Responder {
    let html = r#"<!DOCTYPE html><html><head><title>RustSpider Web UI</title></head><body><h1>RustSpider Web UI</h1><p>Visit /api/tasks for the task control plane.</p></body></html>"#;
    HttpResponse::Ok().content_type("text/html").body(html)
}

async fn tasks_page() -> impl Responder {
    index_page().await
}

async fn task_detail_page(path: web::Path<String>) -> impl Responder {
    let html = format!(
        "<!DOCTYPE html><html><head><title>RustSpider Task</title></head><body><h1>Task {}</h1></body></html>",
        path.into_inner()
    );
    HttpResponse::Ok().content_type("text/html").body(html)
}

pub fn configure_routes(cfg: &mut web::ServiceConfig) {
    cfg.service(list_tasks)
        .service(create_task)
        .service(get_task)
        .service(start_task)
        .service(stop_task)
        .service(delete_task)
        .service(get_task_results)
        .service(get_task_logs)
        .service(get_task_artifacts)
        .service(get_stats)
        .service(extract_graph)
        .service(extract_graph_v1);
}

pub async fn run_server(host: &str, port: u16) -> std::io::Result<()> {
    let task_manager = Arc::new(TaskManager::new());
    let app_state = web::Data::new(AppState {
        task_manager,
        api_token: resolve_api_token(),
    });

    println!("Starting web UI at http://{}:{}", host, port);

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .configure(configure_routes)
            .route("/", web::get().to(index_page))
            .route("/tasks", web::get().to(tasks_page))
            .route("/tasks/{id}", web::get().to(task_detail_page))
    })
    .bind(format!("{}:{}", host, port))?
    .run()
    .await
}

async fn run_task(
    manager: Arc<TaskManager>,
    task_id: String,
    target_url: String,
    mut cancel_rx: watch::Receiver<bool>,
) {
    if *cancel_rx.borrow() {
        manager.add_log(&task_id, "warning", "task cancelled before request");
        return;
    }
    manager.add_log(&task_id, "info", format!("fetching {}", target_url));
    let started = Utc::now();
    let client = match reqwest::Client::builder()
        .timeout(Duration::from_secs(15))
        .build()
    {
        Ok(client) => client,
        Err(err) => {
            finish_failed_task(
                manager,
                &task_id,
                &target_url,
                started,
                format!("client build failed: {err}"),
            );
            return;
        }
    };

    let response = tokio::select! {
        _ = cancel_rx.changed() => {
            manager.add_log(&task_id, "warning", "task cancelled during request");
            return;
        }
        response = client.get(&target_url).send() => response
    };

    let response = match response {
        Ok(response) => response,
        Err(err) => {
            finish_failed_task(
                manager,
                &task_id,
                &target_url,
                started,
                format!("request failed: {err}"),
            );
            return;
        }
    };

    let status_code = response.status().as_u16();
    let final_url = response.url().to_string();
    let content_type = response
        .headers()
        .get(reqwest::header::CONTENT_TYPE)
        .and_then(|value| value.to_str().ok())
        .unwrap_or("")
        .to_string();

    let body = match response.text().await {
        Ok(body) => body,
        Err(err) => {
            finish_failed_task(
                manager,
                &task_id,
                &target_url,
                started,
                format!("read body failed: {err}"),
            );
            return;
        }
    };

    if matches!(
        manager.get(&task_id).map(|task| task.status),
        Some(TaskStatus::Stopped)
    ) {
        manager.add_log(
            &task_id,
            "warning",
            "task finished after stop request; result discarded",
        );
        return;
    }

    let completed = (200..400).contains(&status_code);
    let finished_at = Utc::now();
    let mut task = match manager.get(&task_id) {
        Some(task) => task,
        None => return,
    };
    task.status = if completed {
        TaskStatus::Completed
    } else {
        TaskStatus::Failed
    };
    task.finished_at = Some(timestamp_string(finished_at));
    task.stats.total_requests = 1;
    task.stats.success_requests = if completed { 1 } else { 0 };
    task.stats.failed_requests = if completed { 0 } else { 1 };
    manager.update(&task_id, task);

    let graph_artifacts = persist_graph_artifact("rust", &task_id, &body, finished_at);
    manager.add_result(
        &task_id,
        TaskResult {
            id: format!(
                "result-{}",
                finished_at.timestamp_nanos_opt().unwrap_or_default()
            ),
            task_id: task_id.clone(),
            url: target_url.clone(),
            final_url,
            status: if completed { "completed" } else { "failed" }.to_string(),
            http_status: status_code,
            content_type,
            title: extract_title(&body),
            bytes: body.len(),
            duration_ms: (finished_at - started).num_milliseconds(),
            created_at: timestamp_string(finished_at),
            artifacts: graph_artifacts.clone(),
            artifact_refs: graph_artifacts,
        },
    );
    manager.add_log(
        &task_id,
        "info",
        format!(
            "task finished with status {} in {}ms",
            status_code,
            (finished_at - started).num_milliseconds()
        ),
    );
    manager.cancel(&task_id);
}

fn finish_failed_task(
    manager: Arc<TaskManager>,
    task_id: &str,
    target_url: &str,
    started: DateTime<Utc>,
    message: String,
) {
    let finished_at = Utc::now();
    if let Some(mut task) = manager.get(task_id) {
        if task.status != TaskStatus::Stopped {
            task.status = TaskStatus::Failed;
            task.finished_at = Some(timestamp_string(finished_at));
            task.stats.total_requests = 1;
            task.stats.failed_requests = 1;
            manager.update(task_id, task);
            manager.add_result(
                task_id,
                TaskResult {
                    id: format!(
                        "result-{}",
                        finished_at.timestamp_nanos_opt().unwrap_or_default()
                    ),
                    task_id: task_id.to_string(),
                    url: target_url.to_string(),
                    final_url: target_url.to_string(),
                    status: "failed".to_string(),
                    http_status: 0,
                    content_type: String::new(),
                    title: String::new(),
                    bytes: 0,
                    duration_ms: (finished_at - started).num_milliseconds(),
                    created_at: timestamp_string(finished_at),
                    artifacts: None,
                    artifact_refs: None,
                },
            );
            manager.add_log(task_id, "error", message);
        }
    }
    manager.cancel(task_id);
}

fn extract_title(body: &str) -> String {
    let lower = body.to_ascii_lowercase();
    let Some(start) = lower.find("<title>") else {
        return String::new();
    };
    let Some(end) = lower.find("</title>") else {
        return String::new();
    };
    if end <= start + 7 {
        return String::new();
    }
    body[start + 7..end].trim().to_string()
}

fn persist_graph_artifact(
    runtime: &str,
    task_id: &str,
    html: &str,
    finished_at: DateTime<Utc>,
) -> Option<HashMap<String, TaskArtifact>> {
    if html.trim().is_empty() {
        return None;
    }
    let mut graph = GraphBuilder::new();
    graph.rebuild_from_html(html);

    let payload = serde_json::json!({
        "root_id": graph.root_id,
        "nodes": graph.nodes,
        "edges": graph.edges,
        "stats": graph.stats(),
    });
    let path = control_plane_dir().join("graphs").join(format!(
        "{runtime}-{task_id}-{}.json",
        finished_at.timestamp_nanos_opt().unwrap_or_default()
    ));
    if let Some(parent) = path.parent() {
        if fs::create_dir_all(parent).is_err() {
            return None;
        }
    }
    let encoded = serde_json::to_vec_pretty(&payload).ok()?;
    fs::write(&path, encoded).ok()?;

    let mut artifacts = HashMap::new();
    artifacts.insert(
        "graph".to_string(),
        TaskArtifact {
            kind: "graph".to_string(),
            path: path.to_string_lossy().to_string(),
            root_id: graph
                .root_id
                .clone()
                .unwrap_or_else(|| "document".to_string()),
            stats: serde_json::to_value(graph.stats()).unwrap_or_else(|_| serde_json::json!({})),
        },
    );
    Some(artifacts)
}

fn timestamp_string(value: DateTime<Utc>) -> String {
    value.to_rfc3339()
}

fn paginate<T: Clone>(items: &[T], page: u32, per_page: u32) -> (Vec<T>, usize) {
    let total = items.len();
    let start = page.saturating_sub(1) as usize * per_page as usize;
    if start >= total {
        return (Vec::new(), total);
    }
    let end = (start + per_page as usize).min(total);
    (items[start..end].to_vec(), total)
}

#[cfg(test)]
mod tests {
    use super::*;
    use actix_web::test;
    use serde_json::{json, Value};
    use std::io::{Read, Write};
    use std::net::TcpListener;
    use std::thread;

    fn spawn_stub_server(body: &'static str, delay: Duration) -> String {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind stub server");
        let addr = listener.local_addr().expect("local addr");
        thread::spawn(move || {
            if let Ok((mut stream, _)) = listener.accept() {
                let mut buffer = [0_u8; 1024];
                let _ = stream.read(&mut buffer);
                if delay > Duration::ZERO {
                    thread::sleep(delay);
                }
                let response = format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                    body.len(),
                    body
                );
                let _ = stream.write_all(response.as_bytes());
            }
        });
        format!("http://{}", addr)
    }

    #[actix_web::test]
    async fn task_lifecycle_produces_results_and_logs() {
        let upstream = spawn_stub_server("<title>Rust Demo</title>", Duration::ZERO);
        let data = web::Data::new(AppState {
            task_manager: Arc::new(TaskManager::new()),
            api_token: String::new(),
        });
        let app = test::init_service(
            App::new()
                .app_data(data.clone())
                .configure(configure_routes),
        )
        .await;

        let create_req = test::TestRequest::post()
            .uri("/api/tasks")
            .set_json(json!({"name": "demo", "url": upstream}))
            .to_request();
        let create_resp: Value = test::call_and_read_body_json(&app, create_req).await;
        let task_id = create_resp["data"]["id"].as_str().unwrap().to_string();

        let list_req = test::TestRequest::get().uri("/api/tasks").to_request();
        let list_resp: Value = test::call_and_read_body_json(&app, list_req).await;
        assert_eq!(list_resp["pagination"]["page"], 1);
        assert_eq!(list_resp["pagination"]["total"], 1);

        let start_req = test::TestRequest::post()
            .uri(&format!("/api/tasks/{task_id}/start"))
            .to_request();
        let start_resp: Value = test::call_and_read_body_json(&app, start_req).await;
        assert_eq!(start_resp["data"]["message"], "Task started");

        let mut completed = false;
        for _ in 0..40 {
            let task_req = test::TestRequest::get()
                .uri(&format!("/api/tasks/{task_id}"))
                .to_request();
            let task_resp: Value = test::call_and_read_body_json(&app, task_req).await;
            if task_resp["data"]["status"] == "completed" {
                completed = true;
                break;
            }
            tokio::time::sleep(Duration::from_millis(50)).await;
        }
        assert!(completed, "task did not complete");

        let results_req = test::TestRequest::get()
            .uri(&format!("/api/tasks/{task_id}/results"))
            .to_request();
        let results_resp: Value = test::call_and_read_body_json(&app, results_req).await;
        assert_eq!(results_resp["data"][0]["title"], "Rust Demo");
        assert_eq!(
            results_resp["data"][0]["artifacts"]["graph"]["kind"],
            "graph"
        );
        assert_eq!(
            results_resp["data"][0]["artifact_refs"]["graph"]["kind"],
            "graph"
        );
        let graph_path = results_resp["data"][0]["artifacts"]["graph"]["path"]
            .as_str()
            .unwrap();
        assert!(std::path::Path::new(graph_path).exists());
        let artifacts_req = test::TestRequest::get()
            .uri(&format!("/api/tasks/{task_id}/artifacts"))
            .to_request();
        let artifacts_resp: Value = test::call_and_read_body_json(&app, artifacts_req).await;
        assert_eq!(artifacts_resp["data"]["graph"]["kind"], "graph");

        let logs_req = test::TestRequest::get()
            .uri(&format!("/api/tasks/{task_id}/logs"))
            .to_request();
        let logs_resp: Value = test::call_and_read_body_json(&app, logs_req).await;
        assert!(logs_resp["pagination"]["total"].as_u64().unwrap() >= 2);
    }

    #[actix_web::test]
    async fn stop_marks_task_stopped() {
        let upstream = spawn_stub_server("<title>Slow Rust</title>", Duration::from_millis(500));
        let data = web::Data::new(AppState {
            task_manager: Arc::new(TaskManager::new()),
            api_token: String::new(),
        });
        let app = test::init_service(
            App::new()
                .app_data(data.clone())
                .configure(configure_routes),
        )
        .await;

        let create_req = test::TestRequest::post()
            .uri("/api/tasks")
            .set_json(json!({"name": "slow", "url": upstream}))
            .to_request();
        let create_resp: Value = test::call_and_read_body_json(&app, create_req).await;
        let task_id = create_resp["data"]["id"].as_str().unwrap().to_string();

        let start_req = test::TestRequest::post()
            .uri(&format!("/api/tasks/{task_id}/start"))
            .to_request();
        let _ = test::call_service(&app, start_req).await;

        let stop_req = test::TestRequest::post()
            .uri(&format!("/api/tasks/{task_id}/stop"))
            .to_request();
        let stop_resp: Value = test::call_and_read_body_json(&app, stop_req).await;
        assert_eq!(stop_resp["data"]["message"], "Task stopped");

        let mut stopped = false;
        for _ in 0..20 {
            let task_req = test::TestRequest::get()
                .uri(&format!("/api/tasks/{task_id}"))
                .to_request();
            let task_resp: Value = test::call_and_read_body_json(&app, task_req).await;
            if task_resp["data"]["status"] == "stopped" {
                stopped = true;
                break;
            }
            tokio::time::sleep(Duration::from_millis(25)).await;
        }
        assert!(stopped, "task did not stop");
    }

    #[actix_web::test]
    async fn graph_extract_returns_nodes_edges_and_stats() {
        let data = web::Data::new(AppState {
            task_manager: Arc::new(TaskManager::new()),
            api_token: String::new(),
        });
        let app = test::init_service(
            App::new()
                .app_data(data.clone())
                .configure(configure_routes),
        )
        .await;

        let request = test::TestRequest::post()
            .uri("/api/graph/extract")
            .set_json(json!({
                "html": "<html><head><title>Rust Graph API</title></head><body><a href='https://example.com/page'>Read</a><img src='https://example.com/image.png'/></body></html>"
            }))
            .to_request();
        let response: Value = test::call_and_read_body_json(&app, request).await;

        assert_eq!(response["success"], true);
        assert_eq!(response["data"]["root_id"], "document");
        assert!(response["data"]["stats"]["total_nodes"].as_u64().unwrap() >= 3);
        assert!(response["data"]["nodes"].as_object().unwrap().len() >= 3);
        assert!(response["data"]["edges"].as_object().unwrap().len() >= 2);
    }

    #[actix_web::test]
    async fn auth_protects_api_when_token_configured() {
        let data = web::Data::new(AppState {
            task_manager: Arc::new(TaskManager::new()),
            api_token: "secret-token".to_string(),
        });
        let app = test::init_service(
            App::new()
                .app_data(data.clone())
                .configure(configure_routes),
        )
        .await;

        let unauthorized = test::TestRequest::get().uri("/api/tasks").to_request();
        let unauthorized_resp = test::call_service(&app, unauthorized).await;
        assert_eq!(
            unauthorized_resp.status(),
            actix_web::http::StatusCode::UNAUTHORIZED
        );

        let authorized = test::TestRequest::get()
            .uri("/api/tasks")
            .insert_header(("Authorization", "Bearer secret-token"))
            .to_request();
        let authorized_resp = test::call_service(&app, authorized).await;
        assert_eq!(authorized_resp.status(), actix_web::http::StatusCode::OK);
    }
}
