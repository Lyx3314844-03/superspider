//! 布隆过滤器
//! 
//! 用于高效的 URL 去重

use std::collections::HashSet;
use std::hash::{Hash, Hasher};
use two_hasher::TwoHasher;

/// 布隆过滤器
/// 
/// 一个概率型数据结构，用于检查元素是否在集合中
/// 可能存在误判（false positive），但不会漏判（false negative）
pub struct BloomFilter {
    /// 位数组
    bits: Vec<bool>,
    /// 位数组大小
    size: usize,
    /// 哈希函数数量
    hash_count: usize,
    /// 已添加元素数量
    count: usize,
}

impl BloomFilter {
    /// 创建新布隆过滤器
    /// 
    /// # Arguments
    /// 
    /// * `expected_items` - 预期元素数量
    /// * `false_positive_rate` - 可接受的误判率（0.0-1.0）
    /// 
    /// # Examples
    /// 
    /// ```
    /// use rust_spider::scheduler::BloomFilter;
    /// 
    /// // 预期存储 10000 个元素，误判率 0.01
    /// let filter = BloomFilter::new(10000, 0.01);
    /// ```
    pub fn new(expected_items: usize, false_positive_rate: f64) -> Self {
        // 计算最优的位数组大小和哈希函数数量
        let size = Self::optimal_size(expected_items, false_positive_rate);
        let hash_count = Self::optimal_hash_count(size, expected_items);
        
        Self {
            bits: vec![false; size],
            size,
            hash_count,
            count: 0,
        }
    }
    
    /// 创建默认布隆过滤器
    pub fn default() -> Self {
        Self::new(10000, 0.01)
    }
    
    /// 计算最优位数组大小
    fn optimal_size(n: usize, p: f64) -> usize {
        let m = -(n as f64) * p.ln() / 2.0_f64.ln().powi(2);
        m.ceil() as usize
    }
    
    /// 计算最优哈希函数数量
    fn optimal_hash_count(m: usize, n: usize) -> usize {
        let k = (m as f64 / n as f64) * 2.0_f64.ln();
        k.ceil() as usize
    }
    
    /// 添加元素
    pub fn insert(&mut self, item: &str) {
        for hash in self.hashes(item) {
            let index = hash % self.size;
            self.bits[index] = true;
        }
        self.count += 1;
    }
    
    /// 检查元素是否存在
    /// 
    /// 返回 true 表示可能存在，false 表示一定不存在
    pub fn contains(&self, item: &str) -> bool {
        for hash in self.hashes(item) {
            let index = hash % self.size;
            if !self.bits[index] {
                return false;
            }
        }
        true
    }
    
    /// 检查并添加
    /// 
    /// 返回 true 表示元素已存在，false 表示新添加
    pub fn check_and_insert(&mut self, item: &str) -> bool {
        if self.contains(item) {
            true
        } else {
            self.insert(item);
            false
        }
    }
    
    /// 生成多个哈希值
    fn hashes(&self, item: &str) -> Vec<usize> {
        let mut hashes = Vec::with_capacity(self.hash_count);
        
        // 使用两个哈希函数生成多个哈希值
        let hash1 = self.hash1(item);
        let hash2 = self.hash2(item);
        
        for i in 0..self.hash_count {
            let combined = hash1.wrapping_add(i.wrapping_mul(hash2));
            hashes.push(combined.abs() as usize);
        }
        
        hashes
    }
    
    /// 第一个哈希函数
    fn hash1(&self, item: &str) -> i64 {
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        item.hash(&mut hasher);
        hasher.finish() as i64
    }
    
    /// 第二个哈希函数
    fn hash2(&self, item: &str) -> i64 {
        let mut hasher = TwoHasher::default();
        item.hash(&mut hasher);
        hasher.finish() as i64
    }
    
    /// 获取元素数量
    pub fn len(&self) -> usize {
        self.count
    }
    
    /// 检查是否为空
    pub fn is_empty(&self) -> bool {
        self.count == 0
    }
    
    /// 清空过滤器
    pub fn clear(&mut self) {
        self.bits.fill(false);
        self.count = 0;
    }
    
    /// 获取误判率估计
    pub fn false_positive_rate(&self) -> f64 {
        let ones = self.bits.iter().filter(|&&b| b).count() as f64;
        let ratio = ones / self.size as f64;
        ratio.powi(self.hash_count as i32)
    }
}

impl Default for BloomFilter {
    fn default() -> Self {
        Self::new(10000, 0.01)
    }
}

/// 简单的双哈希器
mod two_hasher {
    use std::hash::{Hasher, Hash};
    
    #[derive(Default)]
    pub struct TwoHasher {
        hash: u64,
    }
    
    impl TwoHasher {
        pub fn finish(&self) -> u64 {
            self.hash
        }
    }
    
    impl Hasher for TwoHasher {
        fn write(&mut self, bytes: &[u8]) {
            for byte in bytes {
                self.hash = self.hash.wrapping_add(*byte as u64);
                self.hash = self.hash.wrapping_mul(31);
            }
        }
        
        fn write_u64(&mut self, i: u64) {
            self.hash = self.hash.wrapping_add(i);
            self.hash = self.hash.wrapping_mul(31);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_bloom_filter() {
        let mut filter = BloomFilter::new(1000, 0.01);
        
        // 添加元素
        filter.insert("hello");
        filter.insert("world");
        
        // 检查存在
        assert!(filter.contains("hello"));
        assert!(filter.contains("world"));
        
        // 检查不存在
        assert!(!filter.contains("rust"));
    }
    
    #[test]
    fn test_check_and_insert() {
        let mut filter = BloomFilter::default();
        
        // 第一次插入返回 false
        assert!(!filter.check_and_insert("test"));
        
        // 第二次检查返回 true
        assert!(filter.check_and_insert("test"));
    }
}
