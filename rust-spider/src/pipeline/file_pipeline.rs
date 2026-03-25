//! 文件数据管道
//! 
//! 将爬取结果保存到文件

use std::fs::{File, OpenOptions};
use std::io::{Write, BufWriter};
use std::path::Path;
use crate::model::Page;
use crate::pipeline::Pipeline;

/// 文件数据管道
/// 
/// 将页面数据保存到文本文件
pub struct FilePipeline {
    /// 输出文件路径
    file_path: String,
    /// 文件写入器
    writer: Option<BufWriter<File>>,
}

impl FilePipeline {
    /// 创建新管道
    /// 
    /// # Arguments
    /// 
    /// * `file_path` - 输出文件路径
    pub fn new(file_path: impl Into<String>) -> Result<Self, Box<dyn std::error::Error>> {
        let file_path = file_path.into();
        
        // 创建目录（如果不存在）
        if let Some(parent) = Path::new(&file_path).parent() {
            std::fs::create_dir_all(parent)?;
        }
        
        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&file_path)?;
        
        Ok(Self {
            file_path,
            writer: Some(BufWriter::new(file)),
        })
    }
    
    /// 创建覆盖模式的新管道
    pub fn with_overwrite(file_path: impl Into<String>) -> Result<Self, Box<dyn std::error::Error>> {
        let file_path = file_path.into();
        
        if let Some(parent) = Path::new(&file_path).parent() {
            std::fs::create_dir_all(parent)?;
        }
        
        let file = OpenOptions::new()
            .create(true)
            .write(true)
            .truncate(true)
            .open(&file_path)?;
        
        Ok(Self {
            file_path,
            writer: Some(BufWriter::new(file)),
        })
    }
}

impl Pipeline for FilePipeline {
    fn process(&self, page: &mut Page) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        // 由于需要可变引用，这里重新打开文件进行写入
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.file_path)?;
        
        let mut writer = BufWriter::new(file);
        
        writeln!(writer, "URL: {}", page.url)?;
        writeln!(writer, "Status: {}", page.response.status_code)?;
        
        if let Some(title) = &page.title {
            writeln!(writer, "Title: {}", title)?;
        }
        
        writeln!(writer, "---")?;
        
        writer.flush()?;
        
        Ok(())
    }
    
    fn name(&self) -> &str {
        "FilePipeline"
    }
    
    fn close(&mut self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        if let Some(writer) = &mut self.writer {
            writer.flush()?;
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Response;
    use std::fs;
    
    #[test]
    fn test_file_pipeline() {
        let temp_path = "/tmp/test_spider_output.txt";
        
        let mut pipeline = FilePipeline::new(temp_path).unwrap();
        
        let response = Response::success(
            "https://example.com",
            200,
            "<html><head><title>Test</title></head><body>Hello</body></html>",
            100,
        );
        
        let mut page = Page::from_response(response);
        let result = pipeline.process(&mut page);
        
        assert!(result.is_ok());
        
        // 清理
        let _ = fs::remove_file(temp_path);
        let _ = fs::remove_dir_all("/tmp");
    }
}
