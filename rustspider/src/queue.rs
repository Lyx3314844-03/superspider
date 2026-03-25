//! 持久化队列模块
//! 支持 SQLite 存储，重启后恢复

use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

/// 队列项
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueueItem {
    pub url: String,
    pub priority: i32,
    pub depth: i32,
    pub retry_count: i32,
    pub request_data: Option<Vec<u8>>,
    pub created_at: f64,
}

impl QueueItem {
    pub fn new(url: String) -> Self {
        Self {
            url,
            priority: 0,
            depth: 0,
            retry_count: 0,
            request_data: None,
            created_at: current_timestamp(),
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

    pub fn with_data(mut self, data: Vec<u8>) -> Self {
        self.request_data = Some(data);
        self
    }
}

/// 持久化优先队列
pub struct PersistentPriorityQueue {
    conn: Arc<Mutex<Connection>>,
    max_size: usize,
    table_name: String,
}

impl PersistentPriorityQueue {
    /// 创建队列
    pub fn new(db_path: &str, max_size: usize) -> Result<Self, rusqlite::Error> {
        let conn = Connection::open(db_path)?;

        // 启用 WAL 模式提高并发性能
        conn.pragma_update(None, "journal_mode", "WAL")?;

        let queue = Self {
            conn: Arc::new(Mutex::new(conn)),
            max_size,
            table_name: "requests".to_string(),
        };

        queue.init_db()?;
        Ok(queue)
    }

    /// 创建内存队列
    pub fn in_memory(max_size: usize) -> Result<Self, rusqlite::Error> {
        let conn = Connection::open_in_memory()?;

        let queue = Self {
            conn: Arc::new(Mutex::new(conn)),
            max_size,
            table_name: "requests".to_string(),
        };

        queue.init_db()?;
        Ok(queue)
    }

    fn init_db(&self) -> Result<(), rusqlite::Error> {
        let conn = self.conn.lock().unwrap();

        conn.execute(
            &format!(
                "CREATE TABLE IF NOT EXISTS {} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    priority INTEGER DEFAULT 0,
                    depth INTEGER DEFAULT 0,
                    retry_count INTEGER DEFAULT 0,
                    request_data BLOB,
                    created_at REAL,
                    updated_at REAL
                )",
                self.table_name
            ),
            [],
        )?;

        conn.execute(
            &format!(
                "CREATE INDEX IF NOT EXISTS idx_priority ON {}(priority DESC, created_at ASC)",
                self.table_name
            ),
            [],
        )?;

        conn.execute(
            &format!(
                "CREATE INDEX IF NOT EXISTS idx_url ON {}(url)",
                self.table_name
            ),
            [],
        )?;

        Ok(())
    }

    /// 添加请求到队列
    pub fn put(&self, item: QueueItem) -> Result<bool, rusqlite::Error> {
        let conn = self.conn.lock().unwrap();

        // 检查队列大小
        if self.size()? >= self.max_size {
            return Ok(false);
        }

        let now = current_timestamp();

        let rows_affected = conn.execute(
            &format!(
                "INSERT OR IGNORE INTO {} 
                (url, priority, depth, retry_count, request_data, created_at, updated_at)
                VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
                self.table_name
            ),
            params![
                item.url,
                item.priority,
                item.depth,
                item.retry_count,
                item.request_data,
                item.created_at,
                now
            ],
        )?;

        Ok(rows_affected > 0)
    }

    /// 获取最高优先级的请求
    pub fn get(&self) -> Result<Option<QueueItem>, rusqlite::Error> {
        let conn = self.conn.lock().unwrap();

        let mut stmt = conn.prepare(&format!(
            "SELECT url, priority, depth, request_data, retry_count, created_at
             FROM {}
             ORDER BY priority DESC, created_at ASC
             LIMIT 1",
            self.table_name
        ))?;

        let item = stmt.query_row([], |row| {
            Ok(QueueItem {
                url: row.get(0)?,
                priority: row.get(1)?,
                depth: row.get(2)?,
                retry_count: row.get(3)?,
                request_data: row.get(4)?,
                created_at: row.get(5)?,
            })
        });

        match item {
            Ok(item) => {
                // 删除已获取的记录
                conn.execute(
                    &format!("DELETE FROM {} WHERE url = ?", self.table_name),
                    params![item.url],
                )?;
                Ok(Some(item))
            }
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(e),
        }
    }

    /// 批量获取请求
    pub fn get_batch(&self, batch_size: usize) -> Result<Vec<QueueItem>, rusqlite::Error> {
        let conn = self.conn.lock().unwrap();

        let mut stmt = conn.prepare(&format!(
            "SELECT url, priority, depth, request_data, retry_count, created_at
             FROM {}
             ORDER BY priority DESC, created_at ASC
             LIMIT ?1",
            self.table_name
        ))?;

        let items = stmt.query_map(params![batch_size], |row| {
            Ok(QueueItem {
                url: row.get(0)?,
                priority: row.get(1)?,
                depth: row.get(2)?,
                retry_count: row.get(3)?,
                request_data: row.get(4)?,
                created_at: row.get(5)?,
            })
        })?;

        let mut result = Vec::new();
        let mut urls_to_delete = Vec::new();

        for item in items.flatten() {
            urls_to_delete.push(item.url.clone());
            result.push(item);
        }

        // 批量删除
        if !urls_to_delete.is_empty() {
            let placeholders = vec!["?"; urls_to_delete.len()].join(",");
            let sql = format!(
                "DELETE FROM {} WHERE url IN ({})",
                self.table_name, placeholders
            );

            let mut params_vec: Vec<&dyn rusqlite::ToSql> = Vec::new();
            for url in &urls_to_delete {
                params_vec.push(url);
            }

            conn.execute(&sql, params_vec.as_slice())?;
        }

        Ok(result)
    }

    /// 移除指定 URL
    pub fn remove(&self, url: &str) -> Result<bool, rusqlite::Error> {
        let conn = self.conn.lock().unwrap();

        let rows = conn.execute(
            &format!("DELETE FROM {} WHERE url = ?", self.table_name),
            params![url],
        )?;

        Ok(rows > 0)
    }

    /// 检查 URL 是否存在
    pub fn exists(&self, url: &str) -> Result<bool, rusqlite::Error> {
        let conn = self.conn.lock().unwrap();

        let mut stmt = conn.prepare(&format!(
            "SELECT 1 FROM {} WHERE url = ? LIMIT 1",
            self.table_name
        ))?;

        let exists = stmt.exists(params![url])?;
        Ok(exists)
    }

    /// 获取队列大小
    pub fn size(&self) -> Result<usize, rusqlite::Error> {
        let conn = self.conn.lock().unwrap();

        let mut stmt = conn.prepare(&format!("SELECT COUNT(*) FROM {}", self.table_name))?;
        let count: i32 = stmt.query_row([], |row| row.get(0))?;

        Ok(count as usize)
    }

    /// 清空队列
    pub fn clear(&self) -> Result<(), rusqlite::Error> {
        let conn = self.conn.lock().unwrap();
        conn.execute(&format!("DELETE FROM {}", self.table_name), [])?;
        Ok(())
    }

    /// 更新优先级
    pub fn update_priority(&self, url: &str, new_priority: i32) -> Result<bool, rusqlite::Error> {
        let conn = self.conn.lock().unwrap();
        let now = current_timestamp();

        let rows = conn.execute(
            &format!(
                "UPDATE {} SET priority = ?, updated_at = ? WHERE url = ?",
                self.table_name
            ),
            params![new_priority, now, url],
        )?;

        Ok(rows > 0)
    }

    /// 增加重试次数
    pub fn increment_retry(&self, url: &str) -> Result<i32, rusqlite::Error> {
        let conn = self.conn.lock().unwrap();
        let now = current_timestamp();

        conn.execute(
            &format!(
                "UPDATE {} SET retry_count = retry_count + 1, updated_at = ? WHERE url = ?",
                self.table_name
            ),
            params![now, url],
        )?;

        // 获取新的重试次数
        let mut stmt = conn.prepare(&format!(
            "SELECT retry_count FROM {} WHERE url = ?",
            self.table_name
        ))?;

        let retry_count: i32 = stmt.query_row(params![url], |row| row.get(0))?;
        Ok(retry_count)
    }

    /// 获取统计信息
    pub fn get_stats(&self) -> Result<QueueStats, rusqlite::Error> {
        let conn = self.conn.lock().unwrap();

        // 总数
        let mut stmt = conn.prepare(&format!("SELECT COUNT(*) FROM {}", self.table_name))?;
        let total: i32 = stmt.query_row([], |row| row.get(0))?;

        // 按优先级分组
        let mut stmt = conn.prepare(&format!(
            "SELECT priority, COUNT(*) FROM {} GROUP BY priority",
            self.table_name
        ))?;
        let mut by_priority = std::collections::HashMap::new();
        let mut rows =
            stmt.query_map([], |row| Ok((row.get::<_, i32>(0)?, row.get::<_, i32>(1)?)))?;

        while let Some(Ok((priority, count))) = rows.next() {
            by_priority.insert(priority, count as usize);
        }

        // 平均深度
        let mut stmt = conn.prepare(&format!("SELECT AVG(depth) FROM {}", self.table_name))?;
        let avg_depth: Option<f64> = stmt.query_row([], |row| row.get(0)).ok();

        // 重试中的请求
        let mut stmt = conn.prepare(&format!(
            "SELECT COUNT(*) FROM {} WHERE retry_count > 0",
            self.table_name
        ))?;
        let retrying: i32 = stmt.query_row([], |row| row.get(0))?;

        Ok(QueueStats {
            total: total as usize,
            by_priority,
            avg_depth: avg_depth.unwrap_or(0.0),
            retrying: retrying as usize,
            max_size: self.max_size,
            utilization: total as f64 / self.max_size as f64,
        })
    }
}

/// 队列统计信息
#[derive(Debug, Clone)]
pub struct QueueStats {
    pub total: usize,
    pub by_priority: std::collections::HashMap<i32, usize>,
    pub avg_depth: f64,
    pub retrying: usize,
    pub max_size: usize,
    pub utilization: f64,
}

impl std::fmt::Display for QueueStats {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "QueueStats {{ total: {}, by_priority: {:?}, avg_depth: {:.2}, retrying: {}, utilization: {:.2}% }}",
            self.total,
            self.by_priority,
            self.avg_depth,
            self.retrying,
            self.utilization * 100.0
        )
    }
}

/// 重试队列
pub struct RetryQueue {
    queue: PersistentPriorityQueue,
    max_retries: i32,
}

impl RetryQueue {
    pub fn new(db_path: &str, max_retries: i32) -> Result<Self, rusqlite::Error> {
        let queue = PersistentPriorityQueue::new(db_path, 10000)?;
        Ok(Self { queue, max_retries })
    }

    pub fn in_memory(max_retries: i32) -> Result<Self, rusqlite::Error> {
        let queue = PersistentPriorityQueue::in_memory(10000)?;
        Ok(Self { queue, max_retries })
    }

    /// 添加重试
    pub fn add_retry(&self, mut item: QueueItem) -> Result<bool, rusqlite::Error> {
        if item.retry_count >= self.max_retries {
            return Ok(false);
        }

        // 延迟重试（指数退避）
        item.priority -= 10; // 降低优先级
        item.retry_count += 1;

        self.queue.put(item)
    }

    pub fn get(&self) -> Result<Option<QueueItem>, rusqlite::Error> {
        self.queue.get()
    }

    pub fn size(&self) -> Result<usize, rusqlite::Error> {
        self.queue.size()
    }

    pub fn clear(&self) -> Result<(), rusqlite::Error> {
        self.queue.clear()
    }
}

/// 获取当前时间戳
fn current_timestamp() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs_f64()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_queue_creation() -> Result<(), rusqlite::Error> {
        // 简单测试队列创建
        let queue = PersistentPriorityQueue::new("test_queue_basic.db", 1000)?;

        assert_eq!(queue.size()?, 0);

        // 清理
        queue.clear()?;
        let _ = std::fs::remove_file("test_queue_basic.db");

        Ok(())
    }

    #[test]
    fn test_retry_queue_creation() -> Result<(), rusqlite::Error> {
        // 简单测试重试队列创建
        let retry_queue = RetryQueue::new("test_retry_basic.db", 3)?;

        assert_eq!(retry_queue.size()?, 0);

        // 清理
        retry_queue.clear()?;
        let _ = std::fs::remove_file("test_retry_basic.db");

        Ok(())
    }
}
