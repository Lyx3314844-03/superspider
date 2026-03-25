//! RustSpider 断点续爬模块测试

use crate::checkpoint::{CheckpointManager, CheckpointState};
use std::collections::HashMap;
use std::time::Duration;

#[test]
fn test_checkpoint_state_new() {
    let visited = vec!["url1".to_string(), "url2".to_string()];
    let pending = vec!["url3".to_string()];
    let mut stats = HashMap::new();
    stats.insert("total".to_string(), serde_json::json!(100));
    
    let state = CheckpointState::new(
        "test_spider".to_string(),
        visited,
        pending,
        stats,
        HashMap::new(),
    );
    
    assert_eq!(state.spider_id, "test_spider");
    assert_eq!(state.visited_urls.len(), 2);
    assert_eq!(state.pending_urls.len(), 1);
    assert!(!state.checksum.is_empty());
}

#[test]
fn test_checkpoint_state_checksum() {
    let mut stats1 = HashMap::new();
    stats1.insert("total".to_string(), serde_json::json!(100));
    
    let state1 = CheckpointState::new(
        "test".to_string(),
        vec!["url1".to_string()],
        vec![],
        stats1,
        HashMap::new(),
    );
    
    let mut stats2 = HashMap::new();
    stats2.insert("total".to_string(), serde_json::json!(100));
    
    let state2 = CheckpointState::new(
        "test".to_string(),
        vec!["url1".to_string()],
        vec![],
        stats2,
        HashMap::new(),
    );
    
    // 相同状态应该有相同校验和
    assert_eq!(state1.checksum, state2.checksum);
    
    // 不同状态应该有不同校验和
    let mut stats3 = HashMap::new();
    stats3.insert("total".to_string(), serde_json::json!(200));
    
    let state3 = CheckpointState::new(
        "test".to_string(),
        vec!["url1".to_string()],
        vec![],
        stats3,
        HashMap::new(),
    );
    
    assert_ne!(state1.checksum, state3.checksum);
}

#[test]
fn test_checkpoint_state_verify() {
    let mut stats = HashMap::new();
    stats.insert("total".to_string(), serde_json::json!(100));
    
    let state = CheckpointState::new(
        "test".to_string(),
        vec!["url1".to_string()],
        vec![],
        stats,
        HashMap::new(),
    );
    
    assert!(state.verify_checksum());
    
    // 篡改校验和
    let mut bad_state = state.clone();
    bad_state.checksum = "bad_checksum".to_string();
    
    assert!(!bad_state.verify_checksum());
}

#[test]
fn test_checkpoint_manager_new() {
    let temp_dir = tempfile::tempdir().unwrap();
    let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), Some(300));
    
    assert!(temp_dir.path().exists());
}

#[test]
fn test_checkpoint_manager_save_and_load() {
    let temp_dir = tempfile::tempdir().unwrap();
    let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), None);
    
    let mut stats = HashMap::new();
    stats.insert("total".to_string(), serde_json::json!(100));
    
    // 保存
    checkpoint.save(
        "test_spider",
        vec!["url1".to_string(), "url2".to_string()],
        vec!["url3".to_string()],
        stats.clone(),
        HashMap::new(),
        true,
    ).unwrap();
    
    // 加载
    let state = checkpoint.load("test_spider").unwrap();
    
    assert_eq!(state.spider_id, "test_spider");
    assert_eq!(state.visited_urls.len(), 2);
    assert_eq!(state.pending_urls.len(), 1);
}

#[test]
fn test_checkpoint_manager_save_cached() {
    let temp_dir = tempfile::tempdir().unwrap();
    let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), None);
    
    // 保存到缓存（不立即保存）
    checkpoint.save(
        "test_cached",
        vec![],
        vec![],
        HashMap::new(),
        HashMap::new(),
        false,
    ).unwrap();
    
    // 从缓存加载
    let state = checkpoint.load("test_cached").unwrap();
    assert!(state.is_some());
}

#[test]
fn test_checkpoint_manager_load_nonexistent() {
    let temp_dir = tempfile::tempdir().unwrap();
    let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), None);
    
    let state = checkpoint.load("nonexistent");
    assert!(state.is_none());
}

#[test]
fn test_checkpoint_manager_delete() {
    let temp_dir = tempfile::tempdir().unwrap();
    let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), None);
    
    // 保存
    checkpoint.save(
        "test_delete",
        vec![],
        vec![],
        HashMap::new(),
        HashMap::new(),
        true,
    ).unwrap();
    
    // 删除
    checkpoint.delete("test_delete").unwrap();
    
    // 加载应该返回 None
    let state = checkpoint.load("test_delete");
    assert!(state.is_none());
}

#[test]
fn test_checkpoint_manager_list() {
    let temp_dir = tempfile::tempdir().unwrap();
    let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), None);
    
    // 保存多个
    for i in 0..3 {
        checkpoint.save(
            &format!("spider_{}", i),
            vec![],
            vec![],
            HashMap::new(),
            HashMap::new(),
            true,
        ).unwrap();
    }
    
    let checkpoints = checkpoint.list_checkpoints();
    
    assert_eq!(checkpoints.len(), 3);
    assert!(checkpoints.contains(&"spider_0".to_string()));
}

#[test]
fn test_checkpoint_manager_get_stats() {
    let temp_dir = tempfile::tempdir().unwrap();
    let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), None);
    
    let mut stats = HashMap::new();
    stats.insert("total".to_string(), serde_json::json!(100));
    
    checkpoint.save(
        "test_stats",
        vec!["url1".to_string(), "url2".to_string()],
        vec!["url3".to_string()],
        stats,
        HashMap::new(),
        true,
    ).unwrap();
    
    let result_stats = checkpoint.get_stats("test_stats").unwrap();
    
    assert_eq!(result_stats["visited_count"], serde_json::json!(2));
    assert_eq!(result_stats["pending_count"], serde_json::json!(1));
}

#[test]
fn test_checkpoint_manager_get_stats_nonexistent() {
    let temp_dir = tempfile::tempdir().unwrap();
    let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), None);
    
    let stats = checkpoint.get_stats("nonexistent");
    assert!(stats.is_none());
}

#[test]
fn test_checkpoint_manager_auto_save() {
    let temp_dir = tempfile::tempdir().unwrap();
    let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), Some(1));
    
    // 保存到缓存（不立即保存）
    checkpoint.save(
        "test_auto",
        vec!["url1".to_string()],
        vec![],
        HashMap::new(),
        HashMap::new(),
        false,
    ).unwrap();
    
    // 等待自动保存
    std::thread::sleep(Duration::from_millis(1500));
    
    // 检查文件是否存在
    let file_path = temp_dir.path().join("test_auto.checkpoint.json");
    assert!(file_path.exists(), "自动保存应该创建文件");
}

#[test]
fn test_checkpoint_manager_close() {
    let temp_dir = tempfile::tempdir().unwrap();
    
    {
        let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), None);
        
        // 保存到缓存（不立即保存）
        checkpoint.save(
            "test_close",
            vec!["url1".to_string()],
            vec![],
            HashMap::new(),
            HashMap::new(),
            false,
        ).unwrap();
        
        // checkpoint 在这里被 drop，应该保存所有缓存
    }
    
    // 检查文件是否存在
    let file_path = temp_dir.path().join("test_close.checkpoint.json");
    assert!(file_path.exists(), "关闭时应该保存所有缓存状态");
}

#[test]
fn test_checkpoint_manager_concurrent_save() {
    let temp_dir = tempfile::tempdir().unwrap();
    let checkpoint = std::sync::Arc::new(CheckpointManager::new(temp_dir.path().to_str().unwrap(), None));
    
    let mut handles = vec![];
    
    // 并发保存
    for i in 0..5 {
        let checkpoint = std::sync::Arc::clone(&checkpoint);
        let handle = std::thread::spawn(move || {
            checkpoint.save(
                &format!("spider_{}", i),
                vec![format!("url_{}", i)],
                vec![],
                HashMap::new(),
                HashMap::new(),
                true,
            ).unwrap();
        });
        handles.push(handle);
    }
    
    // 等待所有线程完成
    for handle in handles {
        handle.join().unwrap();
    }
    
    // 验证所有 checkpoint 都被保存
    let checkpoints = checkpoint.list_checkpoints();
    assert_eq!(checkpoints.len(), 5);
}

#[test]
fn test_checkpoint_manager_large_data() {
    let temp_dir = tempfile::tempdir().unwrap();
    let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), None);
    
    // 创建 1000 个 URL
    let visited_urls: Vec<String> = (0..1000)
        .map(|i| format!("http://example.com/page{}", i))
        .collect();
    
    checkpoint.save(
        "test_large",
        visited_urls,
        vec![],
        HashMap::new(),
        HashMap::new(),
        true,
    ).unwrap();
    
    let state = checkpoint.load("test_large").unwrap();
    assert_eq!(state.visited_urls.len(), 1000);
}

#[test]
fn test_checkpoint_manager_special_characters() {
    let temp_dir = tempfile::tempdir().unwrap();
    let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), None);
    
    let visited_urls = vec![
        "http://example.com/page?param=value&other=123".to_string(),
        "http://example.com/page with spaces".to_string(),
        "http://example.com/page/中文/unicode".to_string(),
    ];
    
    checkpoint.save(
        "test_special",
        visited_urls,
        vec![],
        HashMap::new(),
        HashMap::new(),
        true,
    ).unwrap();
    
    let state = checkpoint.load("test_special").unwrap();
    assert_eq!(state.visited_urls.len(), 3);
}

#[test]
fn test_checkpoint_manager_empty_state() {
    let temp_dir = tempfile::tempdir().unwrap();
    let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), None);
    
    checkpoint.save(
        "test_empty",
        vec![],
        vec![],
        HashMap::new(),
        HashMap::new(),
        true,
    ).unwrap();
    
    let state = checkpoint.load("test_empty").unwrap();
    assert_eq!(state.visited_urls.len(), 0);
    assert_eq!(state.pending_urls.len(), 0);
}

#[tokio::test]
async fn test_checkpoint_manager_drop() {
    let temp_dir = tempfile::tempdir().unwrap();
    
    {
        let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), None);
        
        checkpoint.save(
            "test_drop",
            vec!["url1".to_string()],
            vec![],
            HashMap::new(),
            HashMap::new(),
            false,
        ).unwrap();
        
        // checkpoint 在这里被 drop
    }
    
    // 检查文件是否存在
    let file_path = temp_dir.path().join("test_drop.checkpoint.json");
    assert!(file_path.exists());
}

#[bench]
fn bench_checkpoint_save(b: &mut test::Bencher) {
    let temp_dir = tempfile::tempdir().unwrap();
    let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), None);
    
    let mut stats = HashMap::new();
    stats.insert("total".to_string(), serde_json::json!(100));
    
    b.iter(|| {
        checkpoint.save(
            "benchmark",
            vec!["url1".to_string()],
            vec![],
            stats.clone(),
            HashMap::new(),
            true,
        ).unwrap();
    });
}

#[bench]
fn bench_checkpoint_load(b: &mut test::Bencher) {
    let temp_dir = tempfile::tempdir().unwrap();
    let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), None);
    
    checkpoint.save(
        "benchmark",
        vec!["url1".to_string()],
        vec![],
        HashMap::new(),
        HashMap::new(),
        true,
    ).unwrap();
    
    b.iter(|| {
        checkpoint.load("benchmark");
    });
}
