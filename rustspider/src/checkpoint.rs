//! RustSpider 断点续爬模块
//!
//! 特性:
//! 1. ✅ 自动保存爬虫状态
//! 2. ✅ 支持手动/自动 checkpoint
//! 3. ✅ 状态持久化 (JSON)
//! 4. ✅ 恢复爬虫状态
//! 5. ✅ 增量爬取支持
//!
//! 使用示例:
//! ```rust
//! use rustspider::checkpoint::CheckpointManager;
//!
//! let checkpoint = CheckpointManager::new("checkpoints", Some(300));
//!
//! // 保存状态
//! checkpoint.save("my_spider", visited_urls, pending_urls, stats);
//!
//! // 恢复状态
//! if let Some(state) = checkpoint.load("my_spider") {
//!     spider.load_state(state);
//! }
//! ```

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{self, File};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::{Arc, RwLock};
use std::time::Duration;
use md5::{Md5, Digest};

/// 爬虫状态
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckpointState {
    pub spider_id: String,
    pub timestamp: String,
    pub visited_urls: Vec<String>,
    pub pending_urls: Vec<String>,
    pub stats: HashMap<String, serde_json::Value>,
    pub config: HashMap<String, serde_json::Value>,
    pub checksum: String,
}

impl CheckpointState {
    /// 创建新状态
    pub fn new(
        spider_id: String,
        visited_urls: Vec<String>,
        pending_urls: Vec<String>,
        stats: HashMap<String, serde_json::Value>,
        config: HashMap<String, serde_json::Value>,
    ) -> Self {
        let mut state = Self {
            spider_id,
            timestamp: chrono::Local::now().format("%Y-%m-%dT%H:%M:%S").to_string(),
            visited_urls,
            pending_urls,
            stats,
            config,
            checksum: String::new(),
        };
        state.checksum = state.compute_checksum();
        state
    }
    
    /// 计算校验和
    pub fn compute_checksum(&self) -> String {
        let mut content = HashMap::new();
        content.insert("spider_id", &self.spider_id);
        content.insert("visited_count", &self.visited_urls.len());
        content.insert("pending_count", &self.pending_urls.len());
        content.insert("stats", &self.stats);
        
        let json = serde_json::to_string(&content).unwrap_or_default();
        let mut hasher = Md5::new();
        hasher.update(json.as_bytes());
        hex::encode(hasher.finalize())
    }
    
    /// 验证校验和
    pub fn verify_checksum(&self) -> bool {
        self.checksum == self.compute_checksum()
    }
}

/// 断点管理器
pub struct CheckpointManager {
    checkpoint_dir: PathBuf,
    auto_save_interval: Option<Duration>,
    state_cache: Arc<RwLock<HashMap<String, CheckpointState>>>,
    stop_auto_save: Arc<RwLock<bool>>,
}

impl CheckpointManager {
    /// 创建断点管理器
    ///
    /// # Arguments
    /// * `checkpoint_dir` - checkpoint 存储目录
    /// * `auto_save_interval` - 自动保存间隔 (秒), None 表示禁用
    pub fn new(checkpoint_dir: &str, auto_save_interval: Option<u64>) -> Self {
        // 创建 checkpoint 目录
        let path = PathBuf::from(checkpoint_dir);
        if let Err(e) = fs::create_dir_all(&path) {
            panic!("创建 checkpoint 目录失败：{}", e);
        }
        
        let manager = Self {
            checkpoint_dir: path,
            auto_save_interval: auto_save_interval.map(Duration::from_secs),
            state_cache: Arc::new(RwLock::new(HashMap::new())),
            stop_auto_save: Arc::new(RwLock::new(false)),
        };
        
        // 启动自动保存
        if manager.auto_save_interval.is_some() {
            manager.start_auto_save();
        }
        
        manager
    }
    
    /// 启动自动保存
    fn start_auto_save(&self) {
        let interval = self.auto_save_interval.unwrap();
        let cache = Arc::clone(&self.state_cache);
        let stop_flag = Arc::clone(&self.stop_auto_save);
        let checkpoint_dir = self.checkpoint_dir.clone();
        
        std::thread::spawn(move || {
            loop {
                std::thread::sleep(interval);
                
                // 检查是否停止
                if *stop_flag.read().unwrap() {
                    break;
                }
                
                // 保存所有缓存状态
                let cache_read = cache.read().unwrap();
                for (spider_id, state) in cache_read.iter() {
                    let file_path = checkpoint_dir.join(format!("{}.checkpoint.json", spider_id));
                    let temp_path = checkpoint_dir.join(format!("{}.checkpoint.json.tmp", spider_id));
                    
                    if let Err(e) = Self::save_state_internal(&temp_path, &file_path, state) {
                        eprintln!("自动保存失败 {}: {}", spider_id, e);
                    }
                }
            }
        });
    }
    
    /// 保存爬虫状态
    pub fn save(
        &self,
        spider_id: &str,
        visited_urls: Vec<String>,
        pending_urls: Vec<String>,
        stats: HashMap<String, serde_json::Value>,
        config: HashMap<String, serde_json::Value>,
        immediate: bool,
    ) -> Result<(), String> {
        let state = CheckpointState::new(
            spider_id.to_string(),
            visited_urls,
            pending_urls,
            stats,
            config,
        );
        
        // 保存到缓存
        {
            let mut cache = self.state_cache.write().unwrap();
            cache.insert(spider_id.to_string(), state.clone());
        }
        
        // 立即保存
        if immediate {
            self.save_state(spider_id, &state)?;
        }
        
        Ok(())
    }
    
    /// 保存状态到存储
    fn save_state(&self, spider_id: &str, state: &CheckpointState) -> Result<(), String> {
        let file_path = self.checkpoint_dir.join(format!("{}.checkpoint.json", spider_id));
        let temp_path = self.checkpoint_dir.join(format!("{}.checkpoint.json.tmp", spider_id));
        
        Self::save_state_internal(&temp_path, &file_path, state)
    }
    
    /// 内部保存方法
    fn save_state_internal(
        temp_path: &Path,
        file_path: &Path,
        state: &CheckpointState,
    ) -> Result<(), String> {
        // 序列化
        let json = serde_json::to_string_pretty(state)
            .map_err(|e| format!("序列化失败：{}", e))?;
        
        // 写入临时文件
        let mut file = File::create(temp_path)
            .map_err(|e| format!("创建临时文件失败：{}", e))?;
        file.write_all(json.as_bytes())
            .map_err(|e| format!("写入文件失败：{}", e))?;
        file.sync_all()
            .map_err(|e| format!("同步文件失败：{}", e))?;
        
        // 原子替换
        fs::rename(temp_path, file_path)
            .map_err(|e| format!("原子替换失败：{}", e))?;
        
        Ok(())
    }
    
    /// 加载爬虫状态
    pub fn load(&self, spider_id: &str) -> Option<CheckpointState> {
        // 先从缓存加载
        {
            let cache = self.state_cache.read().unwrap();
            if let Some(state) = cache.get(spider_id) {
                return Some(state.clone());
            }
        }
        
        // 从存储加载
        self.load_state(spider_id).ok().flatten()
    }
    
    /// 从存储加载状态
    fn load_state(&self, spider_id: &str) -> Result<Option<CheckpointState>, String> {
        let file_path = self.checkpoint_dir.join(format!("{}.checkpoint.json", spider_id));
        
        if !file_path.exists() {
            return Ok(None);
        }
        
        // 读取文件
        let mut file = File::open(&file_path)
            .map_err(|e| format!("打开文件失败：{}", e))?;
        
        let mut json = String::new();
        file.read_to_string(&mut json)
            .map_err(|e| format!("读取文件失败：{}", e))?;
        
        // 反序列化
        let mut state: CheckpointState = serde_json::from_str(&json)
            .map_err(|e| format!("反序列化失败：{}", e))?;
        
        // 验证校验和
        if !state.verify_checksum() {
            return Err(format!("checkpoint 校验和失败：{}", spider_id));
        }
        
        // 保存到缓存
        {
            let mut cache = self.state_cache.write().unwrap();
            cache.insert(spider_id.to_string(), state.clone());
        }
        
        Ok(Some(state))
    }
    
    /// 删除 checkpoint
    pub fn delete(&self, spider_id: &str) -> Result<(), String> {
        // 从缓存删除
        {
            let mut cache = self.state_cache.write().unwrap();
            cache.remove(spider_id);
        }
        
        // 从存储删除
        let file_path = self.checkpoint_dir.join(format!("{}.checkpoint.json", spider_id));
        if file_path.exists() {
            fs::remove_file(&file_path)
                .map_err(|e| format!("删除文件失败：{}", e))?;
        }
        
        Ok(())
    }
    
    /// 列出所有 checkpoint
    pub fn list_checkpoints(&self) -> Vec<String> {
        let mut checkpoints = Vec::new();
        
        if let Ok(entries) = fs::read_dir(&self.checkpoint_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.extension().and_then(|s| s.to_str()) == Some("json") {
                    if let Some(filename) = path.file_name().and_then(|s| s.to_str()) {
                        if filename.ends_with(".checkpoint.json") {
                            if let Some(spider_id) = filename.strip_suffix(".checkpoint.json") {
                                checkpoints.push(spider_id.to_string());
                            }
                        }
                    }
                }
            }
        }
        
        checkpoints.sort();
        checkpoints
    }
    
    /// 获取 checkpoint 统计
    pub fn get_stats(&self, spider_id: &str) -> Option<HashMap<String, serde_json::Value>> {
        let state = self.load(spider_id)?;
        
        let mut stats = HashMap::new();
        stats.insert("spider_id".to_string(), serde_json::Value::String(state.spider_id));
        stats.insert("timestamp".to_string(), serde_json::Value::String(state.timestamp));
        stats.insert(
            "visited_count".to_string(),
            serde_json::Value::Number(state.visited_urls.len().into()),
        );
        stats.insert(
            "pending_count".to_string(),
            serde_json::Value::Number(state.pending_urls.len().into()),
        );
        stats.insert("checksum".to_string(), serde_json::Value::String(state.checksum));
        
        Some(stats)
    }
}

impl Drop for CheckpointManager {
    fn drop(&mut self) {
        // 停止自动保存
        if self.auto_save_interval.is_some() {
            *self.stop_auto_save.write().unwrap() = true;
        }
        
        // 保存所有缓存状态
        let cache = self.state_cache.read().unwrap();
        for (spider_id, state) in cache.iter() {
            if let Err(e) = self.save_state(spider_id, state) {
                eprintln!("关闭时保存失败 {}: {}", spider_id, e);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_checkpoint_save_load() {
        let temp_dir = tempfile::tempdir().unwrap();
        let checkpoint = CheckpointManager::new(temp_dir.path().to_str().unwrap(), None);
        
        let mut stats = HashMap::new();
        stats.insert("total".to_string(), serde_json::json!(100));
        
        checkpoint.save(
            "test_spider",
            vec!["url1".to_string()],
            vec!["url2".to_string()],
            stats.clone(),
            HashMap::new(),
            true,
        ).unwrap();
        
        let state = checkpoint.load("test_spider").unwrap();
        assert_eq!(state.spider_id, "test_spider");
        assert_eq!(state.visited_urls.len(), 1);
        assert_eq!(state.pending_urls.len(), 1);
    }
}
