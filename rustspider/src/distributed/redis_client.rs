use redis::{Client, Commands, Connection, RedisResult};

/// Redis 分布式协调器
pub struct DistributedCoordinator {
    client: Client,
}

impl DistributedCoordinator {
    /// 创建新的分布式协调器
    pub fn new(redis_url: &str) -> RedisResult<Self> {
        let client = redis::Client::open(redis_url)?;
        Ok(Self { client })
    }

    /// 获取 Redis 连接
    fn get_conn(&self) -> RedisResult<Connection> {
        self.client.get_connection()
    }

    /// 向分布式队列推送任务
    pub fn push_task(&self, queue_name: &str, task: &str) -> RedisResult<()> {
        let mut conn = self.get_conn()?;
        let _: usize = conn.lpush(queue_name, task)?;
        Ok(())
    }

    /// 从分布式队列拉取任务 (阻塞)
    pub fn pop_task(&self, queue_name: &str, timeout_secs: usize) -> Option<String> {
        let mut conn = self.get_conn().ok()?;
        // BRPOP 阻塞等待 - 修复：直接传入 &mut conn
        let result: Option<(String, String)> = redis::cmd("BRPOP")
            .arg(queue_name)
            .arg(timeout_secs)
            .query(&mut conn)
            .ok()?;
        result.map(|(_, task)| task)
    }

    /// 标记任务完成
    pub fn mark_task_done(&self, task_id: &str) -> RedisResult<()> {
        let mut conn = self.get_conn()?;
        let _: i64 = conn.sadd("completed_tasks", task_id)?;
        Ok(())
    }

    /// 检查任务是否已完成
    pub fn is_task_done(&self, task_id: &str) -> bool {
        let mut conn = match self.get_conn() {
            Ok(c) => c,
            Err(_) => return false,
        };
        let exists: bool = conn.sismember("completed_tasks", task_id).unwrap_or(false);
        exists
    }

    /// 更新 URL 去重集合 (Bloom Filter 简化版)
    pub fn add_seen_url(&self, url: &str) -> RedisResult<bool> {
        let mut conn = self.get_conn()?;
        conn.sadd("seen_urls", url)
    }

    /// 检查 URL 是否已访问
    pub fn has_seen_url(&self, url: &str) -> bool {
        let mut conn = match self.get_conn() {
            Ok(c) => c,
            Err(_) => return false,
        };
        let exists: bool = conn.sismember("seen_urls", url).unwrap_or(false);
        exists
    }

    /// 获取当前在线 Worker 数量
    pub fn get_active_worker_count(&self) -> RedisResult<usize> {
        let mut conn = self.get_conn()?;
        let count: usize = conn.scard("active_workers")?;
        Ok(count)
    }

    /// 注册 Worker - 修复：每个 worker 使用独立的 key
    pub fn register_worker(&self, worker_id: &str) -> RedisResult<()> {
        let mut conn = self.get_conn()?;
        let _: () = conn.sadd("active_workers", worker_id)?;
        // 为每个 worker 设置独立的过期 key
        let worker_key = format!("worker:{}", worker_id);
        let _: () = conn.set(&worker_key, "active")?;
        let _: () = conn.expire(&worker_key, 300)?; // 5 分钟过期
        Ok(())
    }

    /// 注销 Worker
    pub fn deregister_worker(&self, worker_id: &str) -> RedisResult<()> {
        let mut conn = self.get_conn()?;
        let _: i64 = conn.srem("active_workers", worker_id)?;
        Ok(())
    }
}
