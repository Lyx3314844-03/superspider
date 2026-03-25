//! 爬虫指标
//! 
//! 收集和存储爬虫性能指标

use std::sync::atomic::{AtomicU64, AtomicU32, Ordering};
use std::time::{Duration, Instant};
use parking_lot::RwLock;
use serde::{Serialize, Deserialize};

/// 爬虫指标
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Metrics {
    /// 爬虫名称
    pub spider_name: String,
    /// 已爬取页面数
    pub pages_crawled: u64,
    /// 成功页面数
    pub pages_success: u64,
    /// 失败页面数
    pub pages_failed: u64,
    /// 总请求数
    pub total_requests: u64,
    /// 重试次数
    pub retry_count: u64,
    /// 去重跳过数
    pub dedup_skipped: u64,
    /// 平均响应时间（毫秒）
    pub avg_response_time_ms: f64,
    /// 最大响应时间（毫秒）
    pub max_response_time_ms: u64,
    /// 最小响应时间（毫秒）
    pub min_response_time_ms: u64,
    /// 总数据量（字节）
    pub total_bytes: u64,
    /// 开始时间
    pub start_time: Option<String>,
    /// 结束时间
    pub end_time: Option<String>,
    /// 运行时长（秒）
    pub duration_secs: f64,
    /// 每秒请求数
    pub requests_per_second: f64,
    /// 当前队列大小
    pub queue_size: u64,
    /// 活跃线程数
    pub active_threads: u32,
}

impl Metrics {
    /// 创建新指标
    pub fn new(spider_name: impl Into<String>) -> Self {
        Self {
            spider_name: spider_name.into(),
            pages_crawled: 0,
            pages_success: 0,
            pages_failed: 0,
            total_requests: 0,
            retry_count: 0,
            dedup_skipped: 0,
            avg_response_time_ms: 0.0,
            max_response_time_ms: 0,
            min_response_time_ms: u64::MAX,
            total_bytes: 0,
            start_time: None,
            end_time: None,
            duration_secs: 0.0,
            requests_per_second: 0.0,
            queue_size: 0,
            active_threads: 0,
        }
    }
    
    /// 获取健康状态
    pub fn health_status(&self) -> HealthStatus {
        let success_rate = if self.pages_crawled > 0 {
            self.pages_success as f64 / self.pages_crawled as f64
        } else {
            1.0
        };
        
        if success_rate >= 0.95 {
            HealthStatus::Healthy
        } else if success_rate >= 0.80 {
            HealthStatus::Degraded
        } else {
            HealthStatus::Unhealthy
        }
    }
}

/// 健康状态
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum HealthStatus {
    Healthy,
    Degraded,
    Unhealthy,
}

impl std::fmt::Display for HealthStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            HealthStatus::Healthy => write!(f, "Healthy"),
            HealthStatus::Degraded => write!(f, "Degraded"),
            HealthStatus::Unhealthy => write!(f, "Unhealthy"),
        }
    }
}

/// 原子指标收集器（线程安全）
pub struct AtomicMetrics {
    spider_name: String,
    pages_crawled: AtomicU64,
    pages_success: AtomicU64,
    pages_failed: AtomicU64,
    total_requests: AtomicU64,
    retry_count: AtomicU64,
    dedup_skipped: AtomicU64,
    total_response_time_ms: AtomicU64,
    max_response_time_ms: AtomicU64,
    min_response_time_ms: AtomicU64,
    total_bytes: AtomicU64,
    start_time: RwLock<Option<Instant>>,
    end_time: RwLock<Option<Instant>>,
    queue_size: AtomicU64,
    active_threads: AtomicU32,
}

impl AtomicMetrics {
    /// 创建新指标收集器
    pub fn new(spider_name: impl Into<String>) -> Self {
        Self {
            spider_name: spider_name.into(),
            pages_crawled: AtomicU64::new(0),
            pages_success: AtomicU64::new(0),
            pages_failed: AtomicU64::new(0),
            total_requests: AtomicU64::new(0),
            retry_count: AtomicU64::new(0),
            dedup_skipped: AtomicU64::new(0),
            total_response_time_ms: AtomicU64::new(0),
            max_response_time_ms: AtomicU64::new(0),
            min_response_time_ms: AtomicU64::new(u64::MAX),
            total_bytes: AtomicU64::new(0),
            start_time: RwLock::new(None),
            end_time: RwLock::new(None),
            queue_size: AtomicU64::new(0),
            active_threads: AtomicU32::new(0),
        }
    }
    
    /// 记录页面爬取
    pub fn record_page(&self, response_time_ms: u64, bytes: u64, success: bool) {
        self.pages_crawled.fetch_add(1, Ordering::Relaxed);
        self.total_requests.fetch_add(1, Ordering::Relaxed);
        self.total_bytes.fetch_add(bytes, Ordering::Relaxed);
        self.total_response_time_ms.fetch_add(response_time_ms, Ordering::Relaxed);
        
        // 更新最大/最小响应时间
        let mut current_max = self.max_response_time_ms.load(Ordering::Relaxed);
        while response_time_ms > current_max {
            match self.max_response_time_ms.compare_exchange_weak(
                current_max,
                response_time_ms,
                Ordering::Relaxed,
                Ordering::Relaxed,
            ) {
                Ok(_) => break,
                Err(x) => current_max = x,
            }
        }
        
        let mut current_min = self.min_response_time_ms.load(Ordering::Relaxed);
        while response_time_ms < current_min {
            match self.min_response_time_ms.compare_exchange_weak(
                current_min,
                response_time_ms,
                Ordering::Relaxed,
                Ordering::Relaxed,
            ) {
                Ok(_) => break,
                Err(x) => current_min = x,
            }
        }
        
        if success {
            self.pages_success.fetch_add(1, Ordering::Relaxed);
        } else {
            self.pages_failed.fetch_add(1, Ordering::Relaxed);
        }
    }
    
    /// 记录重试
    pub fn record_retry(&self) {
        self.retry_count.fetch_add(1, Ordering::Relaxed);
    }
    
    /// 记录去重跳过
    pub fn record_dedup_skip(&self) {
        self.dedup_skipped.fetch_add(1, Ordering::Relaxed);
    }
    
    /// 设置开始时间
    pub fn start(&self) {
        *self.start_time.write() = Some(Instant::now());
    }
    
    /// 设置结束时间
    pub fn stop(&self) {
        *self.end_time.write() = Some(Instant::now());
    }
    
    /// 设置队列大小
    pub fn set_queue_size(&self, size: u64) {
        self.queue_size.store(size, Ordering::Relaxed);
    }
    
    /// 设置活跃线程数
    pub fn set_active_threads(&self, count: u32) {
        self.active_threads.store(count, Ordering::Relaxed);
    }
    
    /// 获取快照
    pub fn snapshot(&self) -> Metrics {
        let pages_crawled = self.pages_crawled.load(Ordering::Relaxed);
        let total_response_time = self.total_response_time_ms.load(Ordering::Relaxed);
        
        let avg_response_time = if pages_crawled > 0 {
            total_response_time as f64 / pages_crawled as f64
        } else {
            0.0
        };
        
        let max_response_time = self.max_response_time_ms.load(Ordering::Relaxed);
        let min_response_time = self.min_response_time_ms.load(Ordering::Relaxed);
        let min_response_time = if min_response_time == u64::MAX { 0 } else { min_response_time };
        
        let duration = match (*self.start_time.read(), *self.end_time.read()) {
            (Some(start), Some(end)) => end.duration_since(start).as_secs_f64(),
            (Some(start), None) => Instant::now().duration_since(start).as_secs_f64(),
            _ => 0.0,
        };
        
        let total_requests = self.total_requests.load(Ordering::Relaxed);
        let requests_per_second = if duration > 0.0 {
            total_requests as f64 / duration
        } else {
            0.0
        };
        
        Metrics {
            spider_name: self.spider_name.clone(),
            pages_crawled,
            pages_success: self.pages_success.load(Ordering::Relaxed),
            pages_failed: self.pages_failed.load(Ordering::Relaxed),
            total_requests,
            retry_count: self.retry_count.load(Ordering::Relaxed),
            dedup_skipped: self.dedup_skipped.load(Ordering::Relaxed),
            avg_response_time_ms: avg_response_time,
            max_response_time_ms: max_response_time,
            min_response_time_ms: min_response_time,
            total_bytes: self.total_bytes.load(Ordering::Relaxed),
            start_time: self.start_time.read().map(|i| format!("{:?}", i)),
            end_time: self.end_time.read().map(|i| format!("{:?}", i)),
            duration_secs: duration,
            requests_per_second,
            queue_size: self.queue_size.load(Ordering::Relaxed),
            active_threads: self.active_threads.load(Ordering::Relaxed),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_metrics_recording() {
        let metrics = AtomicMetrics::new("test_spider");
        
        metrics.record_page(100, 1024, true);
        metrics.record_page(200, 2048, true);
        metrics.record_page(50, 512, false);
        
        let snapshot = metrics.snapshot();
        
        assert_eq!(snapshot.pages_crawled, 3);
        assert_eq!(snapshot.pages_success, 2);
        assert_eq!(snapshot.pages_failed, 1);
        assert_eq!(snapshot.total_bytes, 3584);
        assert!((snapshot.avg_response_time_ms - 116.67).abs() < 0.1);
    }
    
    #[test]
    fn test_health_status() {
        let mut metrics = Metrics::new("test");
        
        metrics.pages_crawled = 100;
        metrics.pages_success = 98;
        assert_eq!(metrics.health_status(), HealthStatus::Healthy);
        
        metrics.pages_success = 85;
        assert_eq!(metrics.health_status(), HealthStatus::Degraded);
        
        metrics.pages_success = 70;
        assert_eq!(metrics.health_status(), HealthStatus::Unhealthy);
    }
}
