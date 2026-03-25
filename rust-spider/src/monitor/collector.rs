//! 指标收集器
//! 
//! 收集和导出爬虫指标

use std::sync::Arc;
use crate::monitor::metrics::{AtomicMetrics, Metrics};

/// 指标收集器
#[derive(Clone)]
pub struct MetricsCollector {
    metrics: Arc<AtomicMetrics>,
}

impl MetricsCollector {
    /// 创建新收集器
    pub fn new(spider_name: impl Into<String>) -> Self {
        Self {
            metrics: Arc::new(AtomicMetrics::new(spider_name)),
        }
    }
    
    /// 获取内部指标引用
    pub fn inner(&self) -> &Arc<AtomicMetrics> {
        &self.metrics
    }
    
    /// 记录页面爬取
    pub fn record_page(&self, response_time_ms: u64, bytes: u64, success: bool) {
        self.metrics.record_page(response_time_ms, bytes, success);
    }
    
    /// 记录重试
    pub fn record_retry(&self) {
        self.metrics.record_retry();
    }
    
    /// 记录去重跳过
    pub fn record_dedup_skip(&self) {
        self.metrics.record_dedup_skip();
    }
    
    /// 开始收集
    pub fn start(&self) {
        self.metrics.start();
    }
    
    /// 停止收集
    pub fn stop(&self) {
        self.metrics.stop();
    }
    
    /// 获取指标快照
    pub fn snapshot(&self) -> Metrics {
        self.metrics.snapshot()
    }
    
    /// 打印指标到控制台
    pub fn print_summary(&self) {
        let m = self.snapshot();
        
        println!("\n📊 爬虫指标总结");
        println!("═══════════════════════════════════════");
        println!("爬虫名称：{}", m.spider_name);
        println!("健康状态：{}", m.health_status());
        println!("───────────────────────────────────────");
        println!("已爬取页面：{}", m.pages_crawled);
        println!("  - 成功：{}", m.pages_success);
        println!("  - 失败：{}", m.pages_failed);
        println!("  - 成功率：{:.1}%", (m.pages_success as f64 / m.pages_crawled.max(1) as f64) * 100.0);
        println!("───────────────────────────────────────");
        println!("总请求数：{}", m.total_requests);
        println!("重试次数：{}", m.retry_count);
        println!("去重跳过：{}", m.dedup_skipped);
        println!("───────────────────────────────────────");
        println!("响应时间:");
        println!("  - 平均：{:.1}ms", m.avg_response_time_ms);
        println!("  - 最大：{}ms", m.max_response_time_ms);
        println!("  - 最小：{}ms", m.min_response_time_ms);
        println!("───────────────────────────────────────");
        println!("总数据量：{:.2} KB", m.total_bytes as f64 / 1024.0);
        println!("运行时长：{:.2}s", m.duration_secs);
        println!("请求速度：{:.2} req/s", m.requests_per_second);
        println!("═══════════════════════════════════════\n");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_collector() {
        let collector = MetricsCollector::new("test_spider");
        
        collector.start();
        collector.record_page(100, 1024, true);
        collector.record_page(200, 2048, true);
        collector.record_retry();
        collector.stop();
        
        let snapshot = collector.snapshot();
        
        assert_eq!(snapshot.pages_crawled, 2);
        assert_eq!(snapshot.retry_count, 1);
    }
}
