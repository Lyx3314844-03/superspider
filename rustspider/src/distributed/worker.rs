use crate::distributed::redis_client::DistributedCoordinator;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::thread::{self, JoinHandle};
use std::time::Duration;

/// 分布式 Worker
pub struct DistributedWorker {
    pub id: String,
    coordinator: Arc<DistributedCoordinator>,
    running: Arc<AtomicBool>,
    tasks_processed: Arc<AtomicU64>,
    handle: Option<JoinHandle<()>>,
}

impl DistributedWorker {
    /// 创建新的 Worker
    pub fn new(id: String, coordinator: Arc<DistributedCoordinator>) -> Self {
        Self {
            id: id.clone(),
            coordinator,
            running: Arc::new(AtomicBool::new(false)),
            tasks_processed: Arc::new(AtomicU64::new(0)),
            handle: None,
        }
    }

    /// 启动 Worker
    pub fn start(&mut self) {
        self.running.store(true, Ordering::SeqCst);

        // 注册到 Redis
        self.coordinator.register_worker(&self.id).ok();
        println!("✅ Worker {} started", self.id);

        let coordinator = Arc::clone(&self.coordinator);
        let running = Arc::clone(&self.running);
        let tasks_count = Arc::clone(&self.tasks_processed);
        let worker_id = self.id.clone();

        let handle = thread::spawn(move || {
            while running.load(Ordering::SeqCst) {
                // 从队列获取任务 (阻塞 5 秒)
                if let Some(task) = coordinator.pop_task("spider_queue", 5) {
                    println!("📥 Worker {} processing task: {}", worker_id, task);

                    // 模拟处理任务 (实际逻辑应替换为爬虫执行)
                    thread::sleep(Duration::from_millis(100));

                    // 标记完成
                    coordinator.mark_task_done(&task).ok();
                    tasks_count.fetch_add(1, Ordering::SeqCst);
                }
            }

            // 注销 Worker
            coordinator.deregister_worker(&worker_id).ok();
            println!("🛑 Worker {} stopped", worker_id);
        });

        self.handle = Some(handle);
    }

    /// 停止 Worker 并等待线程退出
    pub fn stop(&mut self) {
        self.running.store(false, Ordering::SeqCst);

        if let Some(handle) = self.handle.take() {
            // 等待线程退出，最多等待 10 秒
            let deadline = std::time::Instant::now() + Duration::from_secs(10);
            while !handle.is_finished() && std::time::Instant::now() < deadline {
                std::thread::sleep(Duration::from_millis(100));
            }
            // 如果线程仍未退出，放弃等待
            if !handle.is_finished() {
                eprintln!("⚠️  Worker thread did not exit within timeout");
            }
            let _ = handle.join();
        }
    }

    /// 获取已处理任务数
    pub fn get_tasks_processed(&self) -> u64 {
        self.tasks_processed.load(Ordering::SeqCst)
    }
}
