//! 调度器接口
//! 
//! 定义调度器的基本行为

use crate::model::Request;

/// 调度器接口
/// 
/// 负责管理请求队列和去重
pub trait Scheduler: Send + Sync {
    /// 添加请求
    fn add_request(
        &mut self,
        request: Request,
        parent: Option<Request>,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>>;
    
    /// 获取下一个请求
    fn poll(
        &mut self,
    ) -> Result<Option<Request>, Box<dyn std::error::Error + Send + Sync>>;
    
    /// 检查是否还有请求
    fn is_empty(&self) -> bool;
    
    /// 获取队列大小
    fn len(&self) -> usize;
    
    /// 清空队列
    fn clear(&mut self) -> Result<(), Box<dyn std::error::Error + Send + Sync>>;
    
    /// 重置去重器
    fn reset_dedup(&mut self);
}
