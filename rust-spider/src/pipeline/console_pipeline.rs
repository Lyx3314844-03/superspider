//! 控制台数据管道
//! 
//! 将爬取结果输出到控制台

use log::info;
use crate::model::Page;
use crate::pipeline::Pipeline;

/// 控制台数据管道
/// 
/// 将页面数据输出到标准输出
pub struct ConsolePipeline {
    /// 是否显示详细信息
    verbose: bool,
}

impl ConsolePipeline {
    /// 创建新管道
    pub fn new() -> Self {
        Self { verbose: false }
    }
    
    /// 创建带详细模式的管道
    pub fn verbose() -> Self {
        Self { verbose: true }
    }
}

impl Default for ConsolePipeline {
    fn default() -> Self {
        Self::new()
    }
}

impl Pipeline for ConsolePipeline {
    fn process(&self, page: &mut Page) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        info!("=== Page: {} ===", page.url);
        info!("Status: {}", page.response.status_code);
        
        if let Some(title) = &page.title {
            info!("Title: {}", title);
        }
        
        if self.verbose {
            info!("Links found: {}", page.get_links().len());
            info!("Images found: {}", page.get_images().len());
            
            if !page.fields.is_empty() {
                info!("Fields:");
                for (key, value) in &page.fields {
                    info!("  {}: {}", key, value);
                }
            }
        }
        
        Ok(())
    }
    
    fn name(&self) -> &str {
        "ConsolePipeline"
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Response;
    
    #[test]
    fn test_console_pipeline() {
        let pipeline = ConsolePipeline::new();
        
        let response = Response::success(
            "https://example.com",
            200,
            "<html><head><title>Test</title></head><body>Hello</body></html>",
            100,
        );
        
        let mut page = Page::from_response(response);
        let result = pipeline.process(&mut page);
        
        assert!(result.is_ok());
    }
}
