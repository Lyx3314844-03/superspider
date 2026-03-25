//! Redis 调度器
//! 
//! 基于 Redis 的分布式请求调度器

use redis::{Client, Commands, Connection};
use log::{debug, info, warn};

use crate::model::Request;
use crate::scheduler::Scheduler;

/// Redis 调度器
/// 
/// 使用 Redis 作为共享请求队列，支持分布式爬虫
pub struct RedisScheduler {
    /// Redis 客户端
    client: Client,
    /// 连接
    connection: Option<Connection>,
    /// 队列键名
    queue_key: String,
    /// 去重集合键名
    dedup_key: String,
}

impl RedisScheduler {
    /// 创建新调度器
    /// 
    /// # Arguments
    /// 
    /// * `redis_url` - Redis 连接 URL (redis://host:port)
    /// * `spider_name` - 爬虫名称（用于生成键名）
    /// 
    /// # Examples
    /// 
    /// ```rust,no_run
    /// use rust_spider::distributed::RedisScheduler;
    /// 
    /// let scheduler = RedisScheduler::new("redis://localhost:6379", "my_spider");
    /// ```
    pub fn new(redis_url: &str, spider_name: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let client = Client::open(redis_url)?;
        
        Ok(Self {
            client,
            connection: None,
            queue_key: format!("rustspider:{}:queue", spider_name),
            dedup_key: format!("rustspider:{}:dedup", spider_name),
        })
    }
    
    /// 获取连接
    fn get_connection(&mut self) -> Result<&mut Connection, Box<dyn std::error::Error>> {
        if self.connection.is_none() {
            self.connection = Some(self.client.get_connection()?);
        }
        Ok(self.connection.as_mut().unwrap())
    }
    
    /// 添加到请求队列（低优先级）
    pub fn push_request(&mut self, request: &Request) -> Result<(), Box<dyn std::error::Error>> {
        let conn = self.get_connection()?;
        
        // 检查是否已存在
        let fingerprint = request.fingerprint();
        let exists: bool = conn.sismember(&self.dedup_key, &fingerprint)?;
        
        if exists {
            debug!("Request already exists: {}", request.url);
            return Ok(());
        }
        
        // 添加到队列（低优先级）
        let request_json = serde_json::to_string(request)?;
        conn.lpush(&self.queue_key, &request_json)?;
        
        // 添加到去重集合
        conn.sadd(&self.dedup_key, &fingerprint)?;
        
        debug!("Pushed request: {}", request.url);
        Ok(())
    }
    
    /// 添加到高优先级队列
    pub fn push_high_priority(&mut self, request: &Request) -> Result<(), Box<dyn std::error::Error>> {
        let conn = self.get_connection()?;
        
        let fingerprint = request.fingerprint();
        let exists: bool = conn.sismember(&self.dedup_key, &fingerprint)?;
        
        if exists {
            return Ok(());
        }
        
        // 添加到高优先级队列（使用 RPUSH）
        let request_json = serde_json::to_string(request)?;
        conn.rpush(&self.queue_key, &request_json)?;
        
        conn.sadd(&self.dedup_key, &fingerprint)?;
        
        Ok(())
    }
    
    /// 获取队列大小
    pub fn len(&mut self) -> Result<usize, Box<dyn std::error::Error>> {
        let conn = self.get_connection()?;
        let len: usize = conn.llen(&self.queue_key)?;
        Ok(len)
    }
    
    /// 检查是否为空
    pub fn is_empty(&mut self) -> Result<bool, Box<dyn std::error::Error>> {
        Ok(self.len()? == 0)
    }
    
    /// 清空队列
    pub fn clear(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        let conn = self.get_connection()?;
        conn.del(&self.queue_key)?;
        Ok(())
    }
    
    /// 获取去重集合大小
    pub fn dedup_count(&mut self) -> Result<usize, Box<dyn std::error::Error>> {
        let conn = self.get_connection()?;
        let count: usize = conn.scard(&self.dedup_key)?;
        Ok(count)
    }
}

impl Scheduler for RedisScheduler {
    fn add_request(
        &mut self,
        request: Request,
        _parent: Option<Request>,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        self.push_request(&request).map_err(|e| e.into())
    }
    
    fn poll(&mut self) -> Result<Option<Request>, Box<dyn std::error::Error + Send + Sync>> {
        let conn = self.get_connection()?;
        
        // 从队列右侧弹出（LIFO）
        let result: Option<String> = conn.rpop(&self.queue_key)?;
        
        match result {
            Some(json) => {
                let request: Request = serde_json::from_str(&json)?;
                debug!("Polled request: {}", request.url);
                Ok(Some(request))
            }
            None => Ok(None),
        }
    }
    
    fn is_empty(&self) -> bool {
        // 只读操作，不需要连接
        false
    }
    
    fn len(&self) -> usize {
        // 只读操作，不需要连接
        0
    }
    
    fn clear(&mut self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        self.clear().map_err(|e| e.into())
    }
    
    fn reset_dedup(&mut self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let conn = self.get_connection()?;
        conn.del(&self.dedup_key)?;
        info!("Reset dedup filter");
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    #[ignore] // 需要 Redis 服务器
    fn test_redis_scheduler() {
        let mut scheduler = RedisScheduler::new("redis://localhost:6379", "test_spider").unwrap();
        
        let request = Request::new("https://example.com");
        scheduler.add_request(request, None).unwrap();
        
        let polled = scheduler.poll().unwrap();
        assert!(polled.is_some());
    }
}
