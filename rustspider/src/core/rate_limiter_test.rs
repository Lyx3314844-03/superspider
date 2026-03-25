//! RustSpider 速率限制器和布隆过滤器测试

use crate::core::{RateLimiterV3, BloomFilterV3};
use std::time::Duration;

#[test]
fn test_rate_limiter_new() {
    let limiter = RateLimiterV3::new(100.0);
    
    let tokens = limiter.tokens.blocking_lock();
    assert_eq!(*tokens, 100.0);
}

#[test]
fn test_rate_limiter_wait() {
    let limiter = RateLimiterV3::new(10.0);
    
    // 第一次应该很快
    let start = std::time::Instant::now();
    futures::executor::block_on(limiter.wait());
    let elapsed = start.elapsed();
    
    assert!(elapsed < Duration::from_millis(100));
}

#[test]
fn test_rate_limiter_rate_limit() {
    let limiter = RateLimiterV3::new(100.0);
    
    // 快速消耗令牌
    for _ in 0..10 {
        futures::executor::block_on(limiter.wait());
    }
    
    // 第 11 次应该需要等待
    let start = std::time::Instant::now();
    futures::executor::block_on(limiter.wait());
    let elapsed = start.elapsed();
    
    // 应该等待一段时间
    assert!(elapsed >= Duration::from_millis(5));
}

#[test]
fn test_bloom_filter_new() {
    let bf = BloomFilterV3::new(1000, 0.01);
    
    assert!(!bf.bits.is_empty());
    assert!(bf.num_hashes > 0);
}

#[test]
fn test_bloom_filter_add_and_contains() {
    let bf = BloomFilterV3::new(1000, 0.01);
    
    let data = b"test data";
    
    // 添加前应该不存在
    assert!(!bf.contains(data));
    
    // 添加
    bf.add(data);
    
    // 添加后应该存在
    assert!(bf.contains(data));
}

#[test]
fn test_bloom_filter_false_positive() {
    let bf = BloomFilterV3::new(1000, 0.01);
    
    // 添加一些数据
    for i in 0..100 {
        bf.add(format!("data{}", i).as_bytes());
    }
    
    // 检查不存在的数据（可能有误判，但应该很低）
    let mut false_positives = 0;
    let total_tests = 1000;
    
    for i in 100..100 + total_tests {
        if bf.contains(format!("data{}", i).as_bytes()) {
            false_positives += 1;
        }
    }
    
    // 误判率应该低于 5%
    let false_positive_rate = false_positives as f64 / total_tests as f64;
    assert!(false_positive_rate < 0.05, "误判率过高：{}%", false_positive_rate * 100.0);
}

#[test]
fn test_bloom_filter_multiple_adds() {
    let bf = BloomFilterV3::new(1000, 0.01);
    
    let datas = vec![
        b"data1".to_vec(),
        b"data2".to_vec(),
        b"data3".to_vec(),
    ];
    
    // 添加所有数据
    for data in &datas {
        bf.add(data);
    }
    
    // 验证所有数据都存在
    for data in &datas {
        assert!(bf.contains(data), "添加的数据应该存在");
    }
}

#[test]
fn test_hash_bytes() {
    let data = b"test data";
    
    let (h1, h2) = BloomFilterV3::hash_bytes(data);
    
    // 两次哈希应该相同
    let (h1_again, h2_again) = BloomFilterV3::hash_bytes(data);
    
    assert_eq!(h1, h1_again, "h1 应该相同");
    assert_eq!(h2, h2_again, "h2 应该相同");
    
    // 不同数据应该有不同的哈希
    let (h3, h4) = BloomFilterV3::hash_bytes(b"different data");
    
    // 注意：哈希可能碰撞，但概率很低
    assert!(h1 != h3 || h2 != h4, "不同数据应该有不同的哈希");
}

#[test]
fn test_bloom_filter_empty_data() {
    let bf = BloomFilterV3::new(1000, 0.01);
    
    // 空数据
    let data = b"";
    bf.add(data);
    
    assert!(bf.contains(data));
}

#[test]
fn test_bloom_filter_large_data() {
    let bf = BloomFilterV3::new(10000, 0.01);
    
    // 添加大量数据
    for i in 0..1000 {
        bf.add(format!("data{}", i).as_bytes());
    }
    
    // 验证所有数据都存在
    for i in 0..1000 {
        assert!(bf.contains(format!("data{}", i).as_bytes()));
    }
}

#[test]
fn test_bloom_filter_special_characters() {
    let bf = BloomFilterV3::new(1000, 0.01);
    
    let special_data = vec![
        b"hello world".to_vec(),
        b"中文测试".to_vec(),
        b"!@#$%^&*()".to_vec(),
        b"\x00\x01\x02".to_vec(),
    ];
    
    for data in &special_data {
        bf.add(data);
    }
    
    for data in &special_data {
        assert!(bf.contains(data), "特殊字符数据应该存在");
    }
}

#[tokio::test]
async fn test_rate_limiter_concurrent() {
    let limiter = std::sync::Arc::new(RateLimiterV3::new(1000.0));
    
    let mut handles = vec![];
    
    // 并发等待令牌
    for _ in 0..10 {
        let limiter = std::sync::Arc::clone(&limiter);
        let handle = tokio::spawn(async move {
            limiter.wait().await;
        });
        handles.push(handle);
    }
    
    // 等待所有任务完成
    for handle in handles {
        handle.await.unwrap();
    }
}

#[bench]
fn bench_bloom_filter_add(b: &mut test::Bencher) {
    let bf = BloomFilterV3::new(10000, 0.01);
    let data = b"test data";
    
    b.iter(|| {
        bf.add(data);
    });
}

#[bench]
fn bench_bloom_filter_contains(b: &mut test::Bencher) {
    let bf = BloomFilterV3::new(10000, 0.01);
    let data = b"test data";
    bf.add(data);
    
    b.iter(|| {
        bf.contains(data);
    });
}
