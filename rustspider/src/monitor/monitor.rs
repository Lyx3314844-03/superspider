//! 实时监控模块（完整版）
//! 支持爬虫状态、性能、资源监控

use std::sync::{Arc, RwLock};
use std::time::{SystemTime, UNIX_EPOCH};
use std::collections::VecDeque;
use serde::{Serialize, Deserialize};

/// 爬虫统计
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpiderStats {
    pub spider_name: String,
    pub started_at: f64,
    pub stopped_at: f64,
    pub pages_crawled: usize,
    pub pages_failed: usize,
    pub items_extracted: usize,
    pub requests_made: usize,
    pub bytes_downloaded: usize,
    pub errors: Vec<ErrorRecord>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorRecord {
    pub url: String,
    pub error: String,
    pub timestamp: f64,
}

impl SpiderStats {
    pub fn new(spider_name: &str) -> Self {
        Self {
            spider_name: spider_name.to_string(),
            started_at: 0.0,
            stopped_at: 0.0,
            pages_crawled: 0,
            pages_failed: 0,
            items_extracted: 0,
            requests_made: 0,
            bytes_downloaded: 0,
            errors: Vec::new(),
        }
    }

    pub fn success_rate(&self) -> f64 {
        let total = self.pages_crawled + self.pages_failed;
        if total == 0 {
            0.0
        } else {
            self.pages_crawled as f64 / total as f64
        }
    }

    pub fn runtime(&self) -> f64 {
        let end = if self.stopped_at == 0.0 {
            current_timestamp()
        } else {
            self.stopped_at
        };
        end - self.started_at
    }

    pub fn pages_per_second(&self) -> f64 {
        let runtime = self.runtime();
        if runtime > 0.0 {
            self.pages_crawled as f64 / runtime
        } else {
            0.0
        }
    }
}

/// 性能指标
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceMetrics {
    pub timestamp: f64,
    pub response_time_avg: f64,
    pub response_time_p95: f64,
    pub response_time_p99: f64,
    pub requests_per_second: f64,
    pub errors_per_second: f64,
    pub queue_size: usize,
    pub active_threads: usize,
}

/// 资源指标
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceMetrics {
    pub timestamp: f64,
    pub cpu_percent: f64,
    pub memory_percent: f64,
    pub memory_used_mb: f64,
    pub memory_available_mb: f64,
}

/// 指标收集器
pub struct MetricsCollector {
    window_size: usize,
    response_times: Arc<RwLock<VecDeque<(f64, f64)>>>,
    request_times: Arc<RwLock<VecDeque<f64>>>,
    error_times: Arc<RwLock<VecDeque<f64>>>,
}

impl MetricsCollector {
    pub fn new(window_size: usize) -> Self {
        Self {
            window_size,
            response_times: Arc::new(RwLock::new(VecDeque::with_capacity(10000))),
            request_times: Arc::new(RwLock::new(VecDeque::with_capacity(10000))),
            error_times: Arc::new(RwLock::new(VecDeque::with_capacity(1000))),
        }
    }

    pub fn record_response_time(&self, response_time: f64) {
        let mut times = self.response_times.write().unwrap();
        let now = current_timestamp();
        times.push_back((now, response_time));
        while times.len() > 10000 {
            times.pop_front();
        }
    }

    pub fn record_request(&self) {
        let mut times = self.request_times.write().unwrap();
        times.push_back(current_timestamp());
        while times.len() > 10000 {
            times.pop_front();
        }
    }

    pub fn record_error(&self) {
        let mut times = self.error_times.write().unwrap();
        times.push_back(current_timestamp());
        while times.len() > 1000 {
            times.pop_front();
        }
    }

    pub fn get_metrics(&self) -> PerformanceMetrics {
        let now = current_timestamp();
        let window_start = now - self.window_size as f64;

        // 响应时间统计
        let times = self.response_times.read().unwrap();
        let recent_times: Vec<f64> = times
            .iter()
            .filter(|(t, _)| *t > window_start)
            .map(|(_, rt)| *rt)
            .collect();

        let (avg_time, p95, p99) = if recent_times.is_empty() {
            (0.0, 0.0, 0.0)
        } else {
            let mut sorted = recent_times.clone();
            sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
            
            let avg = sorted.iter().sum::<f64>() / sorted.len() as f64;
            let p95_idx = (sorted.len() as f64 * 0.95) as usize;
            let p99_idx = (sorted.len() as f64 * 0.99) as usize;
            
            (
                avg,
                *sorted.get(p95_idx.min(sorted.len() - 1)).unwrap_or(&0.0),
                *sorted.get(p99_idx.min(sorted.len() - 1)).unwrap_or(&0.0),
            )
        };
        drop(times);

        // 请求速率
        let request_times = self.request_times.read().unwrap();
        let recent_requests = request_times.iter().filter(|&&t| t > window_start).count();
        let rps = recent_requests as f64 / self.window_size as f64;
        drop(request_times);

        // 错误速率
        let error_times = self.error_times.read().unwrap();
        let recent_errors = error_times.iter().filter(|&&t| t > window_start).count();
        let eps = recent_errors as f64 / self.window_size as f64;
        drop(error_times);

        PerformanceMetrics {
            timestamp: now,
            response_time_avg: avg_time,
            response_time_p95: p95,
            response_time_p99: p99,
            requests_per_second: rps,
            errors_per_second: eps,
            queue_size: 0,
            active_threads: std::thread::available_parallelism().map(|p| p.get()).unwrap_or(1),
        }
    }
}

/// 爬虫监控器
pub struct SpiderMonitor {
    pub stats: SpiderStats,
    pub metrics_collector: MetricsCollector,
    pub running: bool,
}

impl SpiderMonitor {
    pub fn new(spider_name: &str) -> Self {
        Self {
            stats: SpiderStats::new(spider_name),
            metrics_collector: MetricsCollector::new(60),
            running: false,
        }
    }

    pub fn start(&mut self) {
        self.running = true;
        self.stats.started_at = current_timestamp();
        println!("监控启动：{}", self.stats.spider_name);
    }

    pub fn stop(&mut self) {
        self.running = false;
        self.stats.stopped_at = current_timestamp();
        println!("监控停止：{}", self.stats.spider_name);
    }

    pub fn record_page_crawled(&mut self, _url: &str, _status: i32, bytes: usize) {
        self.stats.pages_crawled += 1;
        self.stats.bytes_downloaded += bytes;
        self.stats.requests_made += 1;
        self.metrics_collector.record_request();
    }

    pub fn record_page_failed(&mut self, url: &str, error: &str) {
        self.stats.pages_failed += 1;
        self.stats.errors.push(ErrorRecord {
            url: url.to_string(),
            error: error.to_string(),
            timestamp: current_timestamp(),
        });
        self.metrics_collector.record_error();
    }

    pub fn record_item_extracted(&mut self, count: usize) {
        self.stats.items_extracted += count;
    }

    pub fn record_response_time(&self, response_time: f64) {
        self.metrics_collector.record_response_time(response_time);
    }

    pub fn get_stats(&self) -> serde_json::Value {
        let metrics = self.metrics_collector.get_metrics();

        serde_json::json!({
            "spider_name": self.stats.spider_name,
            "stats": {
                "pages_crawled": self.stats.pages_crawled,
                "pages_failed": self.stats.pages_failed,
                "items_extracted": self.stats.items_extracted,
                "bytes_downloaded": self.stats.bytes_downloaded,
                "success_rate": self.stats.success_rate(),
                "runtime": self.stats.runtime(),
                "pages_per_second": self.stats.pages_per_second(),
            },
            "performance": {
                "response_time_avg": metrics.response_time_avg,
                "response_time_p95": metrics.response_time_p95,
                "response_time_p99": metrics.response_time_p99,
                "requests_per_second": metrics.requests_per_second,
                "errors_per_second": metrics.errors_per_second,
            },
            "is_running": self.running,
        })
    }

    pub fn get_dashboard_data(&self) -> serde_json::Value {
        serde_json::json!({
            "spider_name": self.stats.spider_name,
            "status": if self.running { "running" } else { "stopped" },
            "pages_crawled": self.stats.pages_crawled,
            "pages_failed": self.stats.pages_failed,
            "success_rate": self.stats.success_rate() * 100.0,
            "items_extracted": self.stats.items_extracted,
            "runtime_seconds": self.stats.runtime(),
            "pages_per_second": self.stats.pages_per_second(),
            "timestamp": current_timestamp(),
        })
    }
}

/// 监控中心
pub struct MonitorCenter {
    monitors: Arc<RwLock<std::collections::HashMap<String, Arc<RwLock<SpiderMonitor>>>>>,
}

impl MonitorCenter {
    pub fn new() -> Self {
        Self {
            monitors: Arc::new(RwLock::new(std::collections::HashMap::new())),
        }
    }

    pub fn register(&self, spider_name: &str) -> Arc<RwLock<SpiderMonitor>> {
        let mut monitors = self.monitors.write().unwrap();
        
        if !monitors.contains_key(spider_name) {
            let monitor = SpiderMonitor::new(spider_name);
            monitors.insert(spider_name.to_string(), Arc::new(RwLock::new(monitor)));
        }

        Arc::clone(monitors.get(spider_name).unwrap())
    }

    pub fn get_all_stats(&self) -> serde_json::Value {
        let monitors = self.monitors.read().unwrap();
        let stats: serde_json::Map<String, _> = monitors
            .iter()
            .map(|(name, monitor)| {
                let m = monitor.read().unwrap();
                (name.clone(), m.get_stats())
            })
            .collect();
        serde_json::Value::Object(stats)
    }

    pub fn get_summary(&self) -> serde_json::Value {
        let monitors = self.monitors.read().unwrap();
        
        let total_crawled: usize = monitors.values().map(|m| m.read().unwrap().stats.pages_crawled).sum();
        let total_failed: usize = monitors.values().map(|m| m.read().unwrap().stats.pages_failed).sum();
        let total_items: usize = monitors.values().map(|m| m.read().unwrap().stats.items_extracted).sum();
        let running_count = monitors.values().filter(|m| m.read().unwrap().running).count();

        serde_json::json!({
            "total_spiders": monitors.len(),
            "running_spiders": running_count,
            "total_pages_crawled": total_crawled,
            "total_pages_failed": total_failed,
            "total_items_extracted": total_items,
            "timestamp": current_timestamp(),
        })
    }
}

impl Default for MonitorCenter {
    fn default() -> Self {
        Self::new()
    }
}

fn current_timestamp() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs_f64()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_monitor() {
        let mut monitor = SpiderMonitor::new("test_spider");
        monitor.start();

        for i in 0..100 {
            monitor.record_page_crawled(&format!("https://example.com/{}", i), 200, 1024);
            monitor.record_response_time(0.3 + i as f64 * 0.01);
            
            if i % 10 == 0 {
                monitor.record_item_extracted(5);
            }
        }

        let stats = monitor.get_stats();
        println!("Stats: {}", stats);

        monitor.stop();
    }
}
