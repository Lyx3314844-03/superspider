//! 分布式模块（完整版）
//! 支持 Redis 分布式队列、布隆过滤器、任务分发

use md5::{Digest, Md5};
use redis::{Client, Commands};
use serde::{Deserialize, Serialize};
use std::collections::hash_map::DefaultHasher;
use std::error::Error;
use std::hash::{Hash, Hasher};
use std::time::{SystemTime, UNIX_EPOCH};

/// 爬取任务
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CrawlTask {
    pub url: String,
    pub priority: i32,
    pub depth: i32,
    pub task_type: String,
    pub spider_name: String,
    pub created_at: f64,
    pub retry_count: i32,
    pub metadata: Option<serde_json::Value>,
}

impl CrawlTask {
    pub fn new(url: String) -> Self {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs_f64();

        Self {
            url,
            priority: 0,
            depth: 0,
            task_type: "crawl".to_string(),
            spider_name: "default".to_string(),
            created_at: now,
            retry_count: 0,
            metadata: None,
        }
    }

    pub fn with_priority(mut self, priority: i32) -> Self {
        self.priority = priority;
        self
    }

    pub fn with_depth(mut self, depth: i32) -> Self {
        self.depth = depth;
        self
    }

    pub fn with_spider_name(mut self, name: String) -> Self {
        self.spider_name = name;
        self
    }

    pub fn to_json(&self) -> Result<String, Box<dyn Error>> {
        Ok(serde_json::to_string(self)?)
    }

    pub fn from_json(json_str: &str) -> Result<Self, Box<dyn Error>> {
        Ok(serde_json::from_str(json_str)?)
    }
}

/// Redis 分布式队列
pub struct RedisDistributedQueue {
    client: Client,
    name: String,
    max_size: usize,
}

impl RedisDistributedQueue {
    /// 创建队列
    pub fn new(redis_url: &str, name: &str, max_size: usize) -> Result<Self, Box<dyn Error>> {
        let client = Client::open(redis_url)?;
        Ok(Self {
            client,
            name: name.to_string(),
            max_size,
        })
    }

    /// 添加任务
    pub fn push(&self, task: &CrawlTask) -> Result<bool, Box<dyn Error>> {
        let mut conn = self.client.get_connection()?;

        // 检查队列大小
        let size: usize = conn.zcard(self.priority_queue_key())?;
        if size >= self.max_size {
            return Ok(false);
        }

        // 检查是否已存在
        if self.exists(&task.url)?
            || conn.sismember::<_, _, bool>(self.pending_key(), &task.url)?
            || conn.hexists::<_, _, bool>(self.processing_key(), &task.url)?
        {
            return Ok(false);
        }

        // 添加到优先级队列
        let task_json = task.to_json()?;
        let _: () = conn.zadd(self.priority_queue_key(), &task_json, task.priority)?;
        let _: () = conn.sadd(self.pending_key(), &task.url)?;

        Ok(true)
    }

    /// 获取任务
    pub fn pop(&self) -> Result<Option<CrawlTask>, Box<dyn Error>> {
        self.lease("scheduler", 30)
    }

    pub fn lease(
        &self,
        worker_id: &str,
        lease_ttl_secs: u64,
    ) -> Result<Option<CrawlTask>, Box<dyn Error>> {
        let mut conn = self.client.get_connection()?;

        let results: Vec<(String, f64)> = conn.zpopmax(self.priority_queue_key(), 1)?;

        if let Some((task_json, _score)) = results.into_iter().next() {
            let task = CrawlTask::from_json(&task_json)?;
            let _: () = conn.srem(self.pending_key(), &task.url)?;

            let processing_data = serde_json::json!({
                "url": task.url,
                "started_at": current_timestamp(),
                "worker_id": worker_id,
                "expires_at": current_timestamp() + lease_ttl_secs as f64,
                "retry_count": task.retry_count,
                "task": task,
            });
            let _: () = conn.hset(
                self.processing_key(),
                self.url_key(&task.url),
                processing_data.to_string(),
            )?;

            return Ok(Some(task));
        }

        Ok(None)
    }

    /// 确认任务完成
    pub fn ack(&self, task: &CrawlTask, success: bool) -> Result<(), Box<dyn Error>> {
        self.ack_url(&task.url, success, 3)
    }

    pub fn ack_url(
        &self,
        url: &str,
        success: bool,
        max_retries: i32,
    ) -> Result<(), Box<dyn Error>> {
        let mut conn = self.client.get_connection()?;

        let payload: Option<String> = conn.hget(self.processing_key(), self.url_key(url))?;
        let _: () = conn.hdel(self.processing_key(), self.url_key(url))?;
        let Some(payload) = payload else {
            return Ok(());
        };
        let lease: serde_json::Value = serde_json::from_str(&payload)?;
        let mut task: CrawlTask = serde_json::from_value(lease["task"].clone())?;

        if success {
            let _: () = conn.sadd(self.url_set_key(), self.url_key(url))?;
            return Ok(());
        }

        task.retry_count += 1;
        if task.retry_count > max_retries {
            let _: () = conn.lpush(self.failed_queue_key(), task.to_json()?)?;
            let _: () = conn.sadd(self.url_set_key(), self.url_key(url))?;
        } else {
            let _: () = conn.zadd(self.priority_queue_key(), task.to_json()?, task.priority)?;
            let _: () = conn.sadd(self.pending_key(), url)?;
        }
        Ok(())
    }

    pub fn heartbeat(&self, url: &str, lease_ttl_secs: u64) -> Result<bool, Box<dyn Error>> {
        let mut conn = self.client.get_connection()?;
        let key = self.url_key(url);
        let payload: Option<String> = conn.hget(self.processing_key(), &key)?;
        let Some(payload) = payload else {
            return Ok(false);
        };
        let mut lease: serde_json::Value = serde_json::from_str(&payload)?;
        lease["expires_at"] = serde_json::Value::from(current_timestamp() + lease_ttl_secs as f64);
        let _: () = conn.hset(self.processing_key(), key, lease.to_string())?;
        Ok(true)
    }

    pub fn reap_expired_leases(
        &self,
        now_secs: f64,
        max_retries: i32,
    ) -> Result<usize, Box<dyn Error>> {
        let mut conn = self.client.get_connection()?;
        let processing: std::collections::HashMap<String, String> =
            conn.hgetall(self.processing_key())?;
        let mut reaped = 0usize;
        for (url_key, payload) in processing {
            let lease: serde_json::Value = serde_json::from_str(&payload)?;
            let expires_at = lease["expires_at"].as_f64().unwrap_or(0.0);
            if expires_at > now_secs {
                continue;
            }
            let task_url = lease["url"].as_str().unwrap_or_default().to_string();
            self.ack_url(&task_url, false, max_retries)?;
            reaped += 1;
        }

        Ok(reaped)
    }

    /// 检查 URL 是否存在
    pub fn exists(&self, url: &str) -> Result<bool, Box<dyn Error>> {
        let mut conn = self.client.get_connection()?;
        let exists: bool = conn.sismember(self.url_set_key(), self.url_key(url))?;
        Ok(exists)
    }

    /// 队列大小
    pub fn size(&self) -> Result<usize, Box<dyn Error>> {
        let mut conn = self.client.get_connection()?;
        let size: usize = conn.zcard(self.priority_queue_key())?;
        Ok(size)
    }

    /// 处理中任务数
    pub fn processing_count(&self) -> Result<usize, Box<dyn Error>> {
        let mut conn = self.client.get_connection()?;
        let count: usize = conn.hlen(self.processing_key())?;
        Ok(count)
    }

    /// 失败队列大小
    pub fn failed_count(&self) -> Result<usize, Box<dyn Error>> {
        let mut conn = self.client.get_connection()?;
        let count: usize = conn.llen(self.failed_queue_key())?;
        Ok(count)
    }

    /// 清空队列
    pub fn clear(&self) -> Result<(), Box<dyn Error>> {
        let mut conn = self.client.get_connection()?;
        let _: () = conn.del(&[
            self.priority_queue_key(),
            self.url_set_key(),
            self.processing_key(),
            self.failed_queue_key(),
        ])?;
        Ok(())
    }

    /// 获取统计信息
    pub fn get_stats(&self) -> Result<serde_json::Value, Box<dyn Error>> {
        Ok(serde_json::json!({
            "queue_size": self.size()?,
            "processing": self.processing_count()?,
            "failed": self.failed_count()?,
            "max_size": self.max_size,
        }))
    }

    fn priority_queue_key(&self) -> String {
        "spider:shared:queue".to_string()
    }

    fn url_set_key(&self) -> String {
        "spider:shared:visited".to_string()
    }

    fn processing_key(&self) -> String {
        format!("queue:{}:processing", self.name)
    }

    fn pending_key(&self) -> String {
        format!("queue:{}:pending", self.name)
    }

    fn failed_queue_key(&self) -> String {
        format!("queue:{}:failed", self.name)
    }

    fn url_key(&self, url: &str) -> String {
        let mut hasher = Md5::new();
        hasher.update(url.as_bytes());
        format!("url:{:x}", hasher.finalize())
    }
}

/// Redis 布隆过滤器
pub struct RedisBloomFilter {
    client: Client,
    name: String,
    size: usize,
    hash_count: usize,
}

impl RedisBloomFilter {
    /// 创建布隆过滤器
    pub fn new(
        redis_url: &str,
        name: &str,
        expected_items: usize,
        error_rate: f64,
    ) -> Result<Self, Box<dyn Error>> {
        let client = Client::open(redis_url)?;

        // 计算最优参数
        let size = (((-(expected_items as f64)) * error_rate.ln()) / (2.0_f64.ln().powi(2))).ceil()
            as usize;
        let size = size.div_ceil(8) * 8; // 对齐到字节
        let hash_count = ((size as f64 / expected_items as f64) * 2.0_f64.ln()).ceil() as usize;

        Ok(Self {
            client,
            name: name.to_string(),
            size,
            hash_count,
        })
    }

    /// 添加元素
    pub fn add(&self, item: &str) -> Result<bool, Box<dyn Error>> {
        let mut conn = self.client.get_connection()?;
        let item_bytes = item.as_bytes();
        let mut is_new = true;

        for seed in 0..self.hash_count {
            let pos = self.hash(item_bytes, seed) % self.size;
            let existed: bool = conn.setbit(self.key(), pos, true)?;
            if !existed {
                is_new = false;
            }
        }

        Ok(is_new)
    }

    /// 检查元素是否存在
    pub fn contains(&self, item: &str) -> Result<bool, Box<dyn Error>> {
        let mut conn = self.client.get_connection()?;
        let item_bytes = item.as_bytes();

        for seed in 0..self.hash_count {
            let pos = self.hash(item_bytes, seed) % self.size;
            let exists: bool = conn.getbit(self.key(), pos)?;
            if !exists {
                return Ok(false);
            }
        }

        Ok(true)
    }

    /// 清空过滤器
    pub fn clear(&self) -> Result<(), Box<dyn Error>> {
        let mut conn = self.client.get_connection()?;
        let _: () = conn.del(self.key())?;
        Ok(())
    }

    /// 估算元素数量
    pub fn count(&self) -> Result<usize, Box<dyn Error>> {
        let mut conn = self.client.get_connection()?;
        let bits_set: usize = conn.bitcount(self.key())?;

        if bits_set == 0 {
            return Ok(0);
        }

        let count = -(self.size as f64 / self.hash_count as f64)
            * (1.0 - bits_set as f64 / self.size as f64).ln();

        Ok(count as usize)
    }

    fn key(&self) -> String {
        format!("bloom:{}", self.name)
    }

    fn hash(&self, item: &[u8], seed: usize) -> usize {
        let mut hasher = DefaultHasher::new();
        item.hash(&mut hasher);
        seed.hash(&mut hasher);
        hasher.finish() as usize
    }
}

/// Redis 分布式调度器
pub struct RedisDistributedScheduler {
    queue: RedisDistributedQueue,
    filter: RedisBloomFilter,
    spider_name: String,
    client: Client,
}

impl RedisDistributedScheduler {
    /// 创建调度器
    pub fn new(redis_url: &str, spider_name: &str) -> Result<Self, Box<dyn Error>> {
        let client = Client::open(redis_url)?;
        let queue = RedisDistributedQueue::new(redis_url, spider_name, 1_000_000)?;
        let filter = RedisBloomFilter::new(redis_url, spider_name, 1_000_000, 0.01)?;

        Ok(Self {
            queue,
            filter,
            spider_name: spider_name.to_string(),
            client,
        })
    }

    /// 调度 URL
    pub fn schedule(&self, url: &str, priority: i32, depth: i32) -> Result<bool, Box<dyn Error>> {
        // 检查是否已爬取
        if self.filter.contains(url)? {
            return Ok(false);
        }

        // 添加到过滤器
        self.filter.add(url)?;

        // 创建任务
        let task = CrawlTask::new(url.to_string())
            .with_priority(priority)
            .with_depth(depth)
            .with_spider_name(self.spider_name.clone());

        // 入队
        self.queue.push(&task)
    }

    /// 获取下一个任务
    pub fn next_task(&self) -> Result<Option<CrawlTask>, Box<dyn Error>> {
        self.queue.pop()
    }

    /// 确认任务完成
    pub fn ack(&self, task: &CrawlTask, success: bool) -> Result<(), Box<dyn Error>> {
        self.queue.ack(task, success)?;
        self.update_stats(success)?;
        Ok(())
    }

    fn update_stats(&self, success: bool) -> Result<(), Box<dyn Error>> {
        let mut conn = self.client.get_connection()?;

        if success {
            let _: () = conn.hincr("spider:shared:stats", "success", 1)?;
            let _: () = conn.hincr("spider:shared:stats", "rust:success", 1)?;
        } else {
            let _: () = conn.hincr("spider:shared:stats", "failed", 1)?;
            let _: () = conn.hincr("spider:shared:stats", "rust:failed", 1)?;
        }
        let _: () = conn.hincr("spider:shared:stats", "processed", 1)?;
        let _: () = conn.hincr("spider:shared:stats", "rust:processed", 1)?;

        Ok(())
    }

    /// 获取统计信息
    pub fn get_stats(&self) -> Result<serde_json::Value, Box<dyn Error>> {
        let queue_stats = self.queue.get_stats()?;
        let mut conn = self.client.get_connection()?;

        let today = chrono::Local::now().format("%Y-%m-%d").to_string();
        let success: i64 = conn
            .hget(format!("stats:{}:success", self.spider_name), &today)
            .unwrap_or(0);
        let failed: i64 = conn
            .hget(format!("stats:{}:failed", self.spider_name), &today)
            .unwrap_or(0);

        Ok(serde_json::json!({
            "queue": queue_stats,
            "spider_name": self.spider_name,
            "success_today": success,
            "failed_today": failed,
            "total_processed": success + failed,
        }))
    }
}

/// Redis 工作节点
pub struct RedisWorker {
    scheduler: RedisDistributedScheduler,
    spider_name: String,
    running: bool,
    processed: usize,
    failed: usize,
    start_time: f64,
}

impl RedisWorker {
    /// 创建工作节点
    pub fn new(redis_url: &str, spider_name: &str) -> Result<Self, Box<dyn Error>> {
        let scheduler = RedisDistributedScheduler::new(redis_url, spider_name)?;

        Ok(Self {
            scheduler,
            spider_name: spider_name.to_string(),
            running: false,
            processed: 0,
            failed: 0,
            start_time: 0.0,
        })
    }

    /// 启动工作节点
    pub fn start<F>(
        &mut self,
        mut callback: F,
        max_tasks: usize,
        timeout_secs: u64,
    ) -> Result<(), Box<dyn Error>>
    where
        F: FnMut(&CrawlTask) -> Result<(), Box<dyn Error>>,
    {
        self.running = true;
        self.start_time = current_timestamp();

        println!("工作节点启动：{}", self.spider_name);

        let mut tasks_processed = 0;
        let mut last_task_time = current_timestamp();

        while self.running {
            // 检查是否达到最大任务数
            if max_tasks > 0 && tasks_processed >= max_tasks {
                println!("达到最大任务数：{}", max_tasks);
                break;
            }

            // 获取任务
            match self.scheduler.next_task()? {
                Some(task) => {
                    last_task_time = current_timestamp();
                    println!("处理任务：{}", task.url);

                    match callback(&task) {
                        Ok(()) => {
                            self.scheduler.ack(&task, true)?;
                            self.processed += 1;
                            tasks_processed += 1;
                        }
                        Err(e) => {
                            eprintln!("任务失败：{} - {}", task.url, e);
                            self.scheduler.ack(&task, false)?;
                            self.failed += 1;
                        }
                    }
                }
                None => {
                    // 队列为空，等待
                    std::thread::sleep(std::time::Duration::from_secs(1));

                    // 检查超时
                    if timeout_secs > 0
                        && (current_timestamp() - last_task_time) > timeout_secs as f64
                    {
                        println!("队列超时，退出");
                        break;
                    }
                }
            }
        }

        self.stop();
        Ok(())
    }

    /// 停止工作节点
    pub fn stop(&mut self) {
        self.running = false;
        println!("工作节点停止：{}", self.spider_name);
    }

    /// 获取统计信息
    pub fn get_stats(&self) -> serde_json::Value {
        let runtime = current_timestamp() - self.start_time;
        let rate = if runtime > 0.0 {
            self.processed as f64 / runtime
        } else {
            0.0
        };

        serde_json::json!({
            "spider_name": self.spider_name,
            "processed": self.processed,
            "failed": self.failed,
            "runtime": runtime,
            "rate": rate,
        })
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
    #[test]
    fn test_bloom_filter() {
        // 注意：需要 Redis 服务
        // let filter = RedisBloomFilter::new("redis://localhost:6379", "test", 1000, 0.01).unwrap();
        // assert!(filter.add("item1").unwrap());
        // assert!(filter.contains("item1").unwrap());
    }
}
