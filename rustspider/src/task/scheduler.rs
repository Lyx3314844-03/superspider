//! 定时任务模块

use std::thread;
use std::time::Duration;
use std::sync::{Arc, atomic::{AtomicBool, Ordering}};

/// 任务
pub struct Task {
    name: String,
    interval: Duration,
    handler: Box<dyn Fn() + Send + Sync>,
    running: Arc<AtomicBool>,
    stop_flag: Arc<AtomicBool>,
}

impl Task {
    /// 创建任务
    pub fn new<F>(name: &str, interval: Duration, handler: F) -> Self
    where
        F: Fn() + Send + Sync + 'static,
    {
        Task {
            name: name.to_string(),
            interval,
            handler: Box::new(handler),
            running: Arc::new(AtomicBool::new(false)),
            stop_flag: Arc::new(AtomicBool::new(false)),
        }
    }
    
    /// 启动任务
    pub fn start(&self) {
        self.running.store(true, Ordering::SeqCst);
        self.stop_flag.store(false, Ordering::SeqCst);
        
        let handler = self.handler.clone();
        let interval = self.interval;
        let running = self.running.clone();
        let stop_flag = self.stop_flag.clone();
        let name = self.name.clone();
        
        thread::spawn(move || {
            while running.load(Ordering::SeqCst) && !stop_flag.load(Ordering::SeqCst) {
                handler();
                
                // 使用可中断的睡眠
                let mut elapsed = Duration::from_millis(0);
                while elapsed < interval && !stop_flag.load(Ordering::SeqCst) {
                    thread::sleep(Duration::from_millis(100));
                    elapsed += Duration::from_millis(100);
                }
            }
            
            println!("[{}] Task stopped", name);
        });
    }
    
    /// 停止任务
    pub fn stop(&self) {
        self.running.store(false, Ordering::SeqCst);
        self.stop_flag.store(true, Ordering::SeqCst);
    }
    
    /// 检查是否运行中
    pub fn is_running(&self) -> bool {
        self.running.load(Ordering::SeqCst)
    }
}

/// 调度器
pub struct Scheduler {
    tasks: Vec<Task>,
    running: Arc<AtomicBool>,
}

impl Scheduler {
    /// 创建调度器
    pub fn new() -> Self {
        Scheduler {
            tasks: Vec::new(),
            running: Arc::new(AtomicBool::new(false)),
        }
    }
    
    /// 添加任务
    pub fn add_task<F>(&mut self, name: &str, interval: Duration, handler: F) -> &Task
    where
        F: Fn() + Send + Sync + 'static,
    {
        let task = Task::new(name, interval, handler);
        self.tasks.push(task);
        self.tasks.last().unwrap()
    }
    
    /// 启动所有任务
    pub fn start(&self) {
        self.running.store(true, Ordering::SeqCst);
        
        for task in &self.tasks {
            task.start();
        }
    }
    
    /// 停止所有任务
    pub fn stop(&self) {
        self.running.store(false, Ordering::SeqCst);
        
        for task in &self.tasks {
            task.stop();
        }
    }
    
    /// 获取统计
    pub fn get_stats(&self) -> SchedulerStats {
        let running_count = self.tasks.iter().filter(|t| t.is_running()).count();
        
        SchedulerStats {
            total_tasks: self.tasks.len(),
            running_tasks: running_count,
        }
    }
}

impl Default for Scheduler {
    fn default() -> Self {
        Self::new()
    }
}

/// 调度器统计
pub struct SchedulerStats {
    pub total_tasks: usize,
    pub running_tasks: usize,
}

/// 延时任务
pub struct TimedTask {
    delay: Duration,
    handler: Box<dyn FnOnce() + Send>,
    cancelled: Arc<AtomicBool>,
}

impl TimedTask {
    /// 创建延时任务
    pub fn new<F>(delay: Duration, handler: F) -> Self
    where
        F: FnOnce() + Send + 'static,
    {
        TimedTask {
            delay,
            handler: Box::new(handler),
            cancelled: Arc::new(AtomicBool::new(false)),
        }
    }
    
    /// 启动任务
    pub fn start(self) {
        let handler = self.handler;
        let cancelled = self.cancelled;
        
        thread::spawn(move || {
            thread::sleep(self.delay);
            
            if !cancelled.load(Ordering::SeqCst) {
                handler();
            }
        });
    }
    
    /// 取消任务
    pub fn cancel(&self) {
        self.cancelled.store(true, Ordering::SeqCst);
    }
}

/// 调度延时任务
pub fn schedule_task<F>(delay: Duration, handler: F) -> TimedTask
where
    F: FnOnce() + Send + 'static,
{
    let task = TimedTask::new(delay, handler);
    task.start();
    task
}

/// Cron 任务
pub struct CronTask {
    interval: Duration,
    handler: Box<dyn Fn() + Send + Sync>,
    running: Arc<AtomicBool>,
    stop_flag: Arc<AtomicBool>,
}

impl CronTask {
    /// 创建 Cron 任务
    pub fn new<F>(interval: Duration, handler: F) -> Self
    where
        F: Fn() + Send + Sync + 'static,
    {
        CronTask {
            interval,
            handler: Box::new(handler),
            running: Arc::new(AtomicBool::new(false)),
            stop_flag: Arc::new(AtomicBool::new(false)),
        }
    }
    
    /// 启动
    pub fn start(&self) {
        self.running.store(true, Ordering::SeqCst);
        
        let handler = self.handler.clone();
        let interval = self.interval;
        let running = self.running.clone();
        let stop_flag = self.stop_flag.clone();
        
        thread::spawn(move || {
            while running.load(Ordering::SeqCst) && !stop_flag.load(Ordering::SeqCst) {
                handler();
                
                let mut elapsed = Duration::from_millis(0);
                while elapsed < interval && !stop_flag.load(Ordering::SeqCst) {
                    thread::sleep(Duration::from_millis(100));
                    elapsed += Duration::from_millis(100);
                }
            }
        });
    }
    
    /// 停止
    pub fn stop(&self) {
        self.running.store(false, Ordering::SeqCst);
        self.stop_flag.store(true, Ordering::SeqCst);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::AtomicUsize;
    
    #[test]
    fn test_scheduler() {
        let mut scheduler = Scheduler::new();
        let counter = Arc::new(AtomicUsize::new(0));
        
        let counter_clone = counter.clone();
        scheduler.add_task("test", Duration::from_millis(100), move || {
            counter_clone.fetch_add(1, Ordering::SeqCst);
        });
        
        scheduler.start();
        thread::sleep(Duration::from_millis(250));
        scheduler.stop();
        
        assert!(counter.load(Ordering::SeqCst) >= 2);
    }
}
