//! 分布式模块
//! 
//! 提供基于 Redis 的分布式爬虫支持

#[cfg(feature = "distributed")]
mod redis_scheduler;

#[cfg(feature = "distributed")]
pub use redis_scheduler::RedisScheduler;
