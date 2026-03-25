//! 队列调度器
//! 
//! 基于优先级队列的请求调度器

use std::collections::{HashMap, HashSet, VecDeque};
use log::debug;

use crate::model::Request;
use crate::scheduler::{Scheduler, BloomFilter};

/// 队列调度器
/// 
/// 基于优先级队列的调度器，支持 URL 去重
pub struct QueueScheduler {
    /// 请求队列（按优先级）
    queues: Vec<VecDeque<Request>>,
    /// 布隆过滤器用于去重
    bloom_filter: BloomFilter,
    /// 已处理的 URL（精确去重）
    processed_urls: HashSet<String>,
    /// 待处理的 URL
    pending_urls: HashSet<String>,
    /// 最大队列大小
    max_queue_size: usize,
    /// 是否启用去重
    dedup_enabled: bool,
}

impl QueueScheduler {
    /// 创建新调度器
    /// 
    /// # Arguments
    /// 
    /// * `priority_levels` - 优先级级别数量
    pub fn new(priority_levels: usize) -> Self {
        let levels = if priority_levels == 0 { 3 } else { priority_levels };
        
        Self {
            queues: (0..levels).map(|_| VecDeque::new()).collect(),
            bloom_filter: BloomFilter::default(),
            processed_urls: HashSet::new(),
            pending_urls: HashSet::new(),
            max_queue_size: 100_000,
            dedup_enabled: true,
        }
    }
    
    /// 创建带配置的调度器
    pub fn with_config(
        priority_levels: usize,
        expected_items: usize,
        dedup_enabled: bool,
    ) -> Self {
        Self {
            queues: (0..priority_levels).map(|_| VecDeque::new()).collect(),
            bloom_filter: BloomFilter::new(expected_items, 0.01),
            processed_urls: HashSet::new(),
            pending_urls: HashSet::new(),
            max_queue_size: 100_000,
            dedup_enabled,
        }
    }
    
    /// 获取队列数量
    pub fn queue_count(&self) -> usize {
        self.queues.len()
    }
    
    /// 获取总队列大小
    pub fn total_len(&self) -> usize {
        self.queues.iter().map(|q| q.len()).sum()
    }
    
    /// 检查 URL 是否已处理
    pub fn is_processed(&self, url: &str) -> bool {
        if !self.dedup_enabled {
            return false;
        }
        
        self.processed_urls.contains(url) || self.bloom_filter.contains(url)
    }
    
    /// 添加 URL 到已处理集合
    fn mark_processed(&mut self, url: &str) {
        if self.dedup_enabled {
            self.processed_urls.insert(url.to_string());
            self.bloom_filter.insert(url);
        }
    }
}

impl Scheduler for QueueScheduler {
    /// 添加请求
    fn add_request(
        &mut self,
        request: Request,
        _parent: Option<Request>,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        // 检查去重
        if self.dedup_enabled && request.deduplicate {
            if self.is_processed(&request.url) {
                debug!("Skipping duplicate URL: {}", request.url);
                return Ok(());
            }
            
            // 检查是否已在队列中
            if self.pending_urls.contains(&request.url) {
                debug!("URL already pending: {}", request.url);
                return Ok(());
            }
        }
        
        // 检查队列大小
        if self.total_len() >= self.max_queue_size {
            return Err("Queue is full".into());
        }
        
        // 标记为待处理
        if self.dedup_enabled {
            self.pending_urls.insert(request.url.clone());
        }
        
        // 根据优先级添加到对应队列
        let priority = request.priority as usize;
        let queue_index = if priority >= self.queues.len() {
            self.queues.len() - 1
        } else {
            priority
        };
        
        self.queues[queue_index].push_back(request);
        
        Ok(())
    }
    
    /// 获取下一个请求
    fn poll(&mut self) -> Result<Option<Request>, Box<dyn std::error::Error + Send + Sync>> {
        // 从高优先级到低优先级查找
        for queue in self.queues.iter_mut().rev() {
            if let Some(request) = queue.pop_front() {
                // 从待处理集合中移除
                self.pending_urls.remove(&request.url);
                
                // 标记为已处理
                self.mark_processed(&request.url);
                
                debug!("Polling request: {}", request.url);
                return Ok(Some(request));
            }
        }
        
        Ok(None)
    }
    
    /// 检查是否为空
    fn is_empty(&self) -> bool {
        self.queues.iter().all(|q| q.is_empty())
    }
    
    /// 获取队列大小
    fn len(&self) -> usize {
        self.total_len()
    }
    
    /// 清空队列
    fn clear(&mut self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        for queue in &mut self.queues {
            queue.clear();
        }
        self.pending_urls.clear();
        Ok(())
    }
    
    /// 重置去重器
    fn reset_dedup(&mut self) {
        self.bloom_filter.clear();
        self.processed_urls.clear();
        self.pending_urls.clear();
    }
}

impl Default for QueueScheduler {
    fn default() -> Self {
        Self::new(3)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Priority;
    
    #[test]
    fn test_add_and_poll() {
        let mut scheduler = QueueScheduler::new(3);
        
        let request = Request::new("https://example.com");
        scheduler.add_request(request, None).unwrap();
        
        assert!(!scheduler.is_empty());
        assert_eq!(scheduler.len(), 1);
        
        let polled = scheduler.poll().unwrap();
        assert!(polled.is_some());
        assert_eq!(polled.unwrap().url, "https://example.com");
        
        assert!(scheduler.is_empty());
    }
    
    #[test]
    fn test_deduplication() {
        let mut scheduler = QueueScheduler::new(3);
        
        let request1 = Request::new("https://example.com");
        scheduler.add_request(request1, None).unwrap();
        
        let request2 = Request::new("https://example.com");
        scheduler.add_request(request2, None).unwrap();
        
        // 第二个请求应该被去重
        assert_eq!(scheduler.len(), 1);
    }
    
    #[test]
    fn test_priority() {
        let mut scheduler = QueueScheduler::new(3);
        
        // 添加低优先级请求
        let low_priority = Request::new("https://low.com")
            .with_priority(Priority::Low);
        scheduler.add_request(low_priority, None).unwrap();
        
        // 添加高优先级请求
        let high_priority = Request::new("https://high.com")
            .with_priority(Priority::High);
        scheduler.add_request(high_priority, None).unwrap();
        
        // 应该先获取高优先级
        let polled = scheduler.poll().unwrap().unwrap();
        assert_eq!(polled.url, "https://high.com");
    }
}
