//! 数据库管道模块
//! 
//! 提供多种数据库存储支持

#[cfg(feature = "database")]
mod sql_pipeline;
#[cfg(feature = "database")]
mod mongo_pipeline;

#[cfg(feature = "database")]
pub use sql_pipeline::{SqlPipeline, SqlType};
#[cfg(feature = "database")]
pub use mongo_pipeline::MongoPipeline;
