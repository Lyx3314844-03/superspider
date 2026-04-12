// Rustspider 异步运行时模块

//! 异步运行时支持
//!
//! 基于 Tokio 的异步爬虫实现

use std::sync::{Arc, Mutex};
use tokio::time::{sleep, Duration};

/// 异步爬虫 trait
pub trait AsyncSpider: Send + Sync {
    fn start(&self) -> Result<(), Error>;
    fn stop(&self) -> Result<(), Error>;
    fn is_running(&self) -> bool;
}

/// 请求队列 trait
pub trait RequestQueue: Send + Sync {
    fn push(&self, request: Request) -> Result<(), Error>;
    fn pop(&self) -> Option<Request>;
    fn is_empty(&self) -> bool;
    fn size(&self) -> usize;
}

/// 请求结构
#[derive(Debug, Clone)]
pub struct Request {
    pub url: String,
    pub method: String,
    pub headers: std::collections::HashMap<String, String>,
    pub priority: i32,
    pub meta: std::collections::HashMap<String, String>,
}

impl Request {
    pub fn new(url: String) -> Self {
        Self {
            url,
            method: "GET".to_string(),
            headers: std::collections::HashMap::new(),
            priority: 0,
            meta: std::collections::HashMap::new(),
        }
    }

    pub fn fingerprint(&self) -> String {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();
        self.url.hash(&mut hasher);
        format!("{:x}", hasher.finish())
    }
}

/// 错误类型
#[derive(Debug)]
pub struct Error {
    message: String,
}

impl Error {
    pub fn new(message: &str) -> Self {
        Self {
            message: message.to_string(),
        }
    }
}

impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "{}", self.message)
    }
}

impl std::error::Error for Error {}

/// 优先级队列
pub struct PriorityQueue {
    heap: Arc<Mutex<std::collections::BinaryHeap<PrioritizedRequest>>>,
}

struct PrioritizedRequest {
    priority: i32,
    request: Request,
}

impl Ord for PrioritizedRequest {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.priority.cmp(&other.priority)
    }
}

impl PartialOrd for PrioritizedRequest {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

impl PartialEq for PrioritizedRequest {
    fn eq(&self, other: &Self) -> bool {
        self.priority == other.priority
    }
}

impl Eq for PrioritizedRequest {}

impl PriorityQueue {
    pub fn new() -> Self {
        Self {
            heap: Arc::new(Mutex::new(std::collections::BinaryHeap::new())),
        }
    }
}

impl Default for PriorityQueue {
    fn default() -> Self {
        Self::new()
    }
}

impl RequestQueue for PriorityQueue {
    fn push(&self, request: Request) -> Result<(), Error> {
        let mut heap = self.heap.lock().map_err(|_| Error::new("Lock poisoned"))?;
        heap.push(PrioritizedRequest {
            priority: request.priority,
            request,
        });
        Ok(())
    }

    fn pop(&self) -> Option<Request> {
        let mut heap = self.heap.lock().ok()?;
        heap.pop().map(|p| p.request)
    }

    fn is_empty(&self) -> bool {
        match self.heap.lock() {
            Ok(heap) => heap.is_empty(),
            Err(_) => true,
        }
    }

    fn size(&self) -> usize {
        match self.heap.lock() {
            Ok(heap) => heap.len(),
            Err(_) => 0,
        }
    }
}

/// 去重队列
pub struct DedupQueue {
    queue: Arc<dyn RequestQueue>,
    seen: Arc<Mutex<std::collections::HashSet<String>>>,
}

impl DedupQueue {
    pub fn new(queue: Arc<dyn RequestQueue>) -> Self {
        Self {
            queue,
            seen: Arc::new(Mutex::new(std::collections::HashSet::new())),
        }
    }
}

impl RequestQueue for DedupQueue {
    fn push(&self, request: Request) -> Result<(), Error> {
        let fingerprint = request.fingerprint();
        let mut seen = self.seen.lock().map_err(|_| Error::new("Lock poisoned"))?;

        if seen.contains(&fingerprint) {
            return Ok(()); // 已存在，跳过
        }

        self.queue.push(request)?;
        seen.insert(fingerprint);
        Ok(())
    }

    fn pop(&self) -> Option<Request> {
        self.queue.pop()
    }

    fn is_empty(&self) -> bool {
        self.queue.is_empty()
    }

    fn size(&self) -> usize {
        self.queue.size()
    }
}

/// 异步爬虫引擎
pub struct AsyncSpiderEngine {
    running: Arc<Mutex<bool>>,
    queue: Arc<dyn RequestQueue>,
    worker_count: usize,
}

impl AsyncSpiderEngine {
    pub fn new(queue: Arc<dyn RequestQueue>, worker_count: usize) -> Self {
        Self {
            running: Arc::new(Mutex::new(false)),
            queue,
            worker_count,
        }
    }

    pub async fn run(&self) -> Result<(), Error> {
        {
            let mut running = self
                .running
                .lock()
                .map_err(|_| Error::new("Lock poisoned"))?;
            *running = true;
        }

        // 启动工作线程
        let mut handles = Vec::new();

        for i in 0..self.worker_count {
            let queue = Arc::clone(&self.queue);
            let running = Arc::clone(&self.running);

            let handle = tokio::spawn(async move {
                while let Some(request) = queue.pop() {
                    // 检查是否停止
                    {
                        let running = running.lock().unwrap();
                        if !*running {
                            break;
                        }
                    }

                    // 处理请求
                    println!("Worker {} processing: {}", i, request.url);

                    // 模拟处理延迟
                    sleep(Duration::from_millis(100)).await;
                }
            });

            handles.push(handle);
        }

        // 等待所有工作线程完成
        for handle in handles {
            let _ = handle.await;
        }

        Ok(())
    }

    pub fn stop(&self) -> Result<(), Error> {
        let mut running = self
            .running
            .lock()
            .map_err(|_| Error::new("Lock poisoned"))?;
        *running = false;
        Ok(())
    }

    pub fn is_running(&self) -> bool {
        let running = self.running.lock().unwrap();
        *running
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_priority_queue() {
        let queue = PriorityQueue::new();

        let req1 = Request::new("http://example.com/1".to_string());
        let req2 = Request::new("http://example.com/2".to_string());

        queue.push(req1).unwrap();
        queue.push(req2).unwrap();

        assert_eq!(queue.size(), 2);
        assert!(!queue.is_empty());
    }
}
