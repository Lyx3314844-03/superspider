//! 数据管道模块
//! 
//! 负责处理和输出爬取结果

mod pipeline;
mod console_pipeline;
mod file_pipeline;
mod json_pipeline;

pub use pipeline::Pipeline;
pub use console_pipeline::ConsolePipeline;
pub use file_pipeline::FilePipeline;
pub use json_pipeline::JsonFilePipeline;
