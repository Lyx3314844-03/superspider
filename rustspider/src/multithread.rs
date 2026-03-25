//! 多线程增强模块
//! 支持线程池、并发控制、异步执行

use crossbeam_channel::{bounded, Receiver, Sender};
use parking_lot::Mutex as ParkingMutex;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

type Job = Box<dyn FnOnce() + Send + 'static>;
type JobSender = Sender<Job>;
type JobReceiver = Receiver<Job>;

/// 信号量包装器
pub struct Semaphore {
    inner: Arc<ParkingMutex<usize>>,
    #[allow(dead_code)]
    max: usize,
}

impl Semaphore {
    pub fn new(max: usize) -> Self {
        Semaphore {
            inner: Arc::new(ParkingMutex::new(max)),
            max,
        }
    }

    pub fn acquire(&self) -> SemaphorePermit<'_> {
        loop {
            {
                let mut count = self.inner.lock();
                if *count > 0 {
                    *count -= 1;
                    return SemaphorePermit { semaphore: self };
                }
            }
            std::thread::sleep(Duration::from_millis(10));
        }
    }
}

pub struct SemaphorePermit<'a> {
    semaphore: &'a Semaphore,
}

impl<'a> Drop for SemaphorePermit<'a> {
    fn drop(&mut self) {
        let mut count = self.semaphore.inner.lock();
        *count += 1;
    }
}

/// 工作池
pub struct WorkerPool {
    workers: usize,
    task_sender: JobSender,
    active_count: Arc<Mutex<usize>>,
    pending_count: Arc<AtomicUsize>,
    shutdown: Arc<Mutex<bool>>,
}

impl WorkerPool {
    /// 创建工作池
    pub fn new(workers: usize, queue_size: usize) -> Self {
        let (tx, rx): (JobSender, JobReceiver) = bounded(queue_size);
        let rx = Arc::new(Mutex::new(rx));
        let active_count = Arc::new(Mutex::new(0));
        let pending_count = Arc::new(AtomicUsize::new(0));
        let shutdown = Arc::new(Mutex::new(false));

        for _ in 0..workers {
            let rx_clone = Arc::clone(&rx);
            let active_clone = Arc::clone(&active_count);
            let pending_clone = Arc::clone(&pending_count);
            let shutdown_clone = Arc::clone(&shutdown);

            thread::spawn(move || loop {
                let task = {
                    let rx_lock = rx_clone.lock().unwrap();
                    if *shutdown_clone.lock().unwrap() {
                        break;
                    }
                    rx_lock.recv().ok()
                };

                if let Some(task) = task {
                    {
                        let mut active = active_clone.lock().unwrap();
                        *active += 1;
                    }

                    task();

                    {
                        let mut active = active_clone.lock().unwrap();
                        *active -= 1;
                    }
                    pending_clone.fetch_sub(1, Ordering::SeqCst);
                } else {
                    break;
                }
            });
        }

        WorkerPool {
            workers,
            task_sender: tx,
            active_count,
            pending_count,
            shutdown,
        }
    }

    /// 提交任务
    pub fn submit<F>(&self, task: F) -> bool
    where
        F: FnOnce() + Send + 'static,
    {
        if *self.shutdown.lock().unwrap() {
            return false;
        }
        self.pending_count.fetch_add(1, Ordering::SeqCst);
        if self.task_sender.send(Box::new(task)).is_ok() {
            true
        } else {
            self.pending_count.fetch_sub(1, Ordering::SeqCst);
            false
        }
    }

    /// 提交任务（等待）
    pub fn submit_wait<F>(&self, task: F)
    where
        F: FnOnce() + Send + 'static,
    {
        self.pending_count.fetch_add(1, Ordering::SeqCst);
        if self.task_sender.send(Box::new(task)).is_err() {
            self.pending_count.fetch_sub(1, Ordering::SeqCst);
        }
    }

    /// 获取活跃线程数
    pub fn active_count(&self) -> usize {
        *self.active_count.lock().unwrap()
    }

    /// 关闭工作池
    pub fn shutdown(&self) {
        *self.shutdown.lock().unwrap() = true;
    }

    /// 等待所有任务完成
    pub fn wait_all(&self) {
        while self.pending_count.load(Ordering::SeqCst) > 0 {
            thread::sleep(Duration::from_millis(100));
        }
    }

    /// 获取统计信息
    pub fn get_stats(&self) -> PoolStats {
        PoolStats {
            workers: self.workers,
            active: self.active_count(),
            is_shutdown: *self.shutdown.lock().unwrap(),
        }
    }
}

/// 池统计
pub struct PoolStats {
    pub workers: usize,
    pub active: usize,
    pub is_shutdown: bool,
}

/// 并发执行器
pub struct ConcurrentExecutor {
    #[allow(dead_code)]
    max_concurrent: usize,
    semaphore: Arc<Semaphore>,
}

impl ConcurrentExecutor {
    /// 创建并发执行器
    pub fn new(max_concurrent: usize) -> Self {
        ConcurrentExecutor {
            max_concurrent,
            semaphore: Arc::new(Semaphore::new(max_concurrent)),
        }
    }

    /// 执行任务
    pub fn execute<F, R>(&self, task: F) -> R
    where
        F: FnOnce() -> R + Send,
        R: Send,
    {
        let _permit = self.semaphore.acquire();
        task()
    }

    /// 执行多个任务
    pub fn execute_many<F, R>(&self, tasks: Vec<F>) -> Vec<R>
    where
        F: FnOnce() -> R + Send + 'static,
        R: Send + 'static,
    {
        let mut handles = Vec::new();

        for task in tasks {
            let semaphore = Arc::clone(&self.semaphore);
            let handle = thread::spawn(move || {
                let _permit = semaphore.acquire();
                task()
            });
            handles.push(handle);
        }

        handles.into_iter().filter_map(|h| h.join().ok()).collect()
    }
}

/// 限流执行器
pub struct RateLimitedExecutor {
    rate: usize,
    interval: Duration,
    tokens: Arc<Mutex<usize>>,
    last_refill: Arc<Mutex<std::time::Instant>>,
}

impl RateLimitedExecutor {
    /// 创建限流执行器
    pub fn new(rate: usize, interval_secs: u64) -> Self {
        RateLimitedExecutor {
            rate,
            interval: Duration::from_secs(interval_secs),
            tokens: Arc::new(Mutex::new(rate)),
            last_refill: Arc::new(Mutex::new(std::time::Instant::now())),
        }
    }

    /// 等待令牌
    pub fn wait(&self) {
        loop {
            self.refill();

            {
                let mut tokens = self.tokens.lock().unwrap();
                if *tokens > 0 {
                    *tokens -= 1;
                    break;
                }
            }

            thread::sleep(Duration::from_millis(100));
        }
    }

    fn refill(&self) {
        let mut last_refill = self.last_refill.lock().unwrap();
        let now = std::time::Instant::now();
        let elapsed = now.duration_since(*last_refill);

        let tokens_to_add =
            (elapsed.as_secs_f64() / self.interval.as_secs_f64()) as usize * self.rate;

        if tokens_to_add > 0 {
            let mut tokens = self.tokens.lock().unwrap();
            *tokens = std::cmp::min(self.rate, *tokens + tokens_to_add);
            *last_refill = now;
        }
    }

    /// 执行任务（带限流）
    pub fn execute<F, R>(&self, task: F) -> R
    where
        F: FnOnce() -> R,
    {
        self.wait();
        task()
    }
}

/// 优先级任务队列
pub struct PriorityTaskQueue<T> {
    queue: std::collections::BinaryHeap<PrioritizedTask<T>>,
}

struct PrioritizedTask<T> {
    priority: i32,
    task: T,
}

impl<T> PriorityTaskQueue<T> {
    /// 创建优先级队列
    pub fn new() -> Self {
        PriorityTaskQueue {
            queue: std::collections::BinaryHeap::new(),
        }
    }

    /// 添加任务
    pub fn push(&mut self, priority: i32, task: T) {
        self.queue.push(PrioritizedTask { priority, task });
    }

    /// 获取任务
    pub fn pop(&mut self) -> Option<T> {
        self.queue.pop().map(|pt| pt.task)
    }

    /// 是否为空
    pub fn is_empty(&self) -> bool {
        self.queue.is_empty()
    }

    /// 队列长度
    pub fn len(&self) -> usize {
        self.queue.len()
    }
}

impl<T> Default for PriorityTaskQueue<T> {
    fn default() -> Self {
        Self::new()
    }
}

impl<T> Ord for PrioritizedTask<T> {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.priority.cmp(&other.priority)
    }
}

impl<T> PartialOrd for PrioritizedTask<T> {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

impl<T> PartialEq for PrioritizedTask<T> {
    fn eq(&self, other: &Self) -> bool {
        self.priority == other.priority
    }
}

impl<T> Eq for PrioritizedTask<T> {}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    #[test]
    fn test_worker_pool() {
        let pool = WorkerPool::new(4, 100);
        let counter = Arc::new(AtomicUsize::new(0));

        for _ in 0..10 {
            let counter_clone = Arc::clone(&counter);
            pool.submit(move || {
                counter_clone.fetch_add(1, Ordering::SeqCst);
            });
        }

        pool.wait_all();
        assert_eq!(counter.load(Ordering::SeqCst), 10);
    }

    #[test]
    fn test_concurrent_executor() {
        let executor = ConcurrentExecutor::new(5);
        let results = executor.execute_many(
            vec![1, 2, 3, 4, 5]
                .into_iter()
                .map(|i| move || i * 2)
                .collect(),
        );

        assert_eq!(results.len(), 5);
    }
}
