//! JSON 文件数据管道
//! 
//! 将爬取结果保存为 JSON 格式

use std::fs::{File, OpenOptions};
use std::io::{Write, BufWriter};
use std::path::Path;
use serde_json::{json, Value};
use crate::model::Page;
use crate::pipeline::Pipeline;

/// JSON 文件数据管道
/// 
/// 将页面数据保存为 JSON 格式
pub struct JsonFilePipeline {
    /// 输出文件路径
    file_path: String,
    /// 是否每行一个 JSON 对象
    line_delimited: bool,
}

impl JsonFilePipeline {
    /// 创建新管道
    /// 
    /// # Arguments
    /// 
    /// * `file_path` - 输出文件路径
    pub fn new(file_path: impl Into<String>) -> Result<Self, Box<dyn std::error::Error>> {
        let file_path = file_path.into();
        
        if let Some(parent) = Path::new(&file_path).parent() {
            std::fs::create_dir_all(parent)?;
        }
        
        Ok(Self {
            file_path,
            line_delimited: true,
        })
    }
    
    /// 创建格式化 JSON 管道
    pub fn pretty(file_path: impl Into<String>) -> Result<Self, Box<dyn std::error::Error>> {
        let file_path = file_path.into();
        
        if let Some(parent) = Path::new(&file_path).parent() {
            std::fs::create_dir_all(parent)?;
        }
        
        Ok(Self {
            file_path,
            line_delimited: false,
        })
    }
    
    /// 将页面转换为 JSON 值
    fn page_to_json(page: &Page) -> Value {
        json!({
            "url": page.url,
            "status_code": page.response.status_code,
            "title": page.title,
            "html": page.html,
            "fields": page.fields,
            "links": page.get_links(),
            "images": page.get_images(),
            "elapsed_ms": page.response.elapsed_ms,
        })
    }
}

impl Pipeline for JsonFilePipeline {
    fn process(&self, page: &mut Page) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.file_path)?;
        
        let mut writer = BufWriter::new(file);
        
        let json_value = Self::page_to_json(page);
        
        if self.line_delimited {
            // 每行一个 JSON 对象（JSONL 格式）
            writeln!(writer, "{}", json_value)?;
        } else {
            // 格式化 JSON
            let pretty = serde_json::to_string_pretty(&json_value)?;
            writeln!(writer, "{}", pretty)?;
        }
        
        writer.flush()?;
        
        Ok(())
    }
    
    fn name(&self) -> &str {
        "JsonFilePipeline"
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Response;
    use std::fs;
    
    #[test]
    fn test_json_pipeline() {
        let temp_path = "/tmp/test_spider_output.json";
        
        let pipeline = JsonFilePipeline::new(temp_path).unwrap();
        
        let response = Response::success(
            "https://example.com",
            200,
            "<html><head><title>Test</title></head><body>Hello</body></html>",
            100,
        );
        
        let mut page = Page::from_response(response);
        page.put_field("custom_field", "custom_value");
        
        let result = pipeline.process(&mut page);
        
        assert!(result.is_ok());
        
        // 验证文件内容
        let content = fs::read_to_string(temp_path).unwrap();
        assert!(content.contains("https://example.com"));
        assert!(content.contains("Test"));
        
        // 清理
        let _ = fs::remove_file(temp_path);
    }
}
