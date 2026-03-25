//! 数据管道接口
//! 
//! 定义数据管道的基本行为

use crate::model::Page;

/// 数据管道接口
/// 
/// 用于处理和输出爬取结果
pub trait Pipeline: Send + Sync {
    /// 处理页面
    /// 
    /// # Arguments
    /// 
    /// * `page` - 页面对象
    /// 
    /// # Returns
    /// 
    /// 成功或错误信息
    fn process(&self, page: &mut Page) -> Result<(), Box<dyn std::error::Error + Send + Sync>>;
    
    /// 管道名称
    fn name(&self) -> &str;
    
    /// 关闭管道（清理资源）
    fn close(&mut self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        Ok(())
    }
}
