//! 调度器模块
//! 支持优先级队列和 URL 去重

use crate::models::Request;
use std::cmp::Ordering;
use std::collections::{BinaryHeap, HashSet};
use std::sync::{Arc, Mutex};

/// 优先级请求
#[derive(Clone)]
struct PrioritizedRequest {
    request: Request,
    priority: i32,
}

impl PartialEq for PrioritizedRequest {
    fn eq(&self, other: &Self) -> bool {
        self.priority == other.priority
    }
}

impl Eq for PrioritizedRequest {}

impl PartialOrd for PrioritizedRequest {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for PrioritizedRequest {
    fn cmp(&self, other: &Self) -> Ordering {
        self.priority.cmp(&other.priority)
    }
}

/// 调度器
pub struct Scheduler {
    queue: Arc<Mutex<BinaryHeap<PrioritizedRequest>>>,
    visited: Arc<Mutex<HashSet<String>>>,
}

impl Scheduler {
    /// 创建调度器
    pub fn new() -> Self {
        Scheduler {
            queue: Arc::new(Mutex::new(BinaryHeap::new())),
            visited: Arc::new(Mutex::new(HashSet::new())),
        }
    }

    /// 添加请求
    pub fn add_request(&self, request: Request) {
        let url = request.url.clone();

        // 检查是否已访问
        {
            let mut visited = self.visited.lock().unwrap();
            if visited.contains(&url) {
                return;
            }
            visited.insert(url);
        }

        // 添加到队列
        let mut queue = self.queue.lock().unwrap();
        queue.push(PrioritizedRequest {
            priority: request.priority,
            request,
        });
    }

    /// 获取下一个请求
    pub fn next_request(&self) -> Option<Request> {
        let mut queue = self.queue.lock().unwrap();
        queue.pop().map(|pr| pr.request)
    }

    /// 检查是否已访问
    pub fn is_visited(&self, url: &str) -> bool {
        let visited = self.visited.lock().unwrap();
        visited.contains(url)
    }

    /// 获取队列长度
    pub fn queue_len(&self) -> usize {
        let queue = self.queue.lock().unwrap();
        queue.len()
    }

    /// 获取已访问数量
    pub fn visited_count(&self) -> usize {
        let visited = self.visited.lock().unwrap();
        visited.len()
    }

    /// 清空
    pub fn clear(&self) {
        self.queue.lock().unwrap().clear();
        self.visited.lock().unwrap().clear();
    }
}

impl Default for Scheduler {
    fn default() -> Self {
        Self::new()
    }
}

/// 布隆过滤器
pub struct BloomFilter {
    bit_array: Vec<bool>,
    size: usize,
    hash_count: usize,
}

impl BloomFilter {
    /// 创建布隆过滤器
    pub fn new(size: usize, hash_count: usize) -> Self {
        BloomFilter {
            bit_array: vec![false; size],
            size,
            hash_count,
        }
    }

    /// 哈希函数
    fn hashes(&self, item: &str) -> Vec<usize> {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hashes = Vec::with_capacity(self.hash_count);
        for i in 0..self.hash_count {
            let mut hasher = DefaultHasher::new();
            format!("{}{}", item, i).hash(&mut hasher);
            hashes.push(hasher.finish() as usize % self.size);
        }
        hashes
    }

    /// 添加元素
    pub fn add(&mut self, item: &str) {
        for hash in self.hashes(item) {
            self.bit_array[hash] = true;
        }
    }

    /// 检查元素是否存在
    pub fn contains(&self, item: &str) -> bool {
        self.hashes(item).iter().all(|&hash| self.bit_array[hash])
    }

    /// 清空
    pub fn clear(&mut self) {
        self.bit_array.fill(false);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_scheduler() {
        let scheduler = Scheduler::new();

        let req1 = Request::new("https://example.com/1".to_string());
        let req2 = Request::new("https://example.com/2".to_string());

        scheduler.add_request(req1);
        scheduler.add_request(req2);

        assert_eq!(scheduler.queue_len(), 2);
        assert!(scheduler.is_visited("https://example.com/1"));

        let next = scheduler.next_request();
        assert!(next.is_some());
    }

    #[test]
    fn test_bloom_filter() {
        let mut bf = BloomFilter::new(1000, 7);

        bf.add("test");
        assert!(bf.contains("test"));
        assert!(!bf.contains("not_added"));
    }
}
