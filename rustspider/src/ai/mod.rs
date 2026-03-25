//! RustSpider AI 集成模块
//! 
//! 提供 LLM（Large Language Model）集成，支持：
//! - 智能内容提取
//! - 页面理解
//! - 自然语言配置爬虫

use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

/// AI 配置
#[derive(Debug, Clone)]
pub struct AIConfig {
    pub api_key: String,
    pub base_url: String,
    pub model: String,
    pub max_tokens: u32,
    pub temperature: f32,
}

impl Default for AIConfig {
    fn default() -> Self {
        Self {
            api_key: std::env::var("OPENAI_API_KEY").unwrap_or_default(),
            base_url: "https://api.openai.com/v1".to_string(),
            model: "gpt-4".to_string(),
            max_tokens: 2000,
            temperature: 0.7,
        }
    }
}

/// AI 提取器
pub struct AIExtractor {
    config: AIConfig,
    client: Client,
}

impl AIExtractor {
    pub fn new(config: AIConfig) -> Self {
        Self {
            client: Client::new(),
            config,
        }
    }

    pub fn with_openai_api_key(api_key: &str) -> Self {
        Self::new(AIConfig {
            api_key: api_key.to_string(),
            ..Default::default()
        })
    }

    /// 提取结构化数据
    /// 
    /// # Arguments
    /// * `content` - 页面内容
    /// * `schema` - JSON Schema 定义期望的输出格式
    /// * `instructions` - 提取指令
    /// 
    /// # Example
    /// ```
    /// let extractor = AIExtractor::with_openai_api_key("your-api-key");
    /// let schema = json!({
    ///     "type": "object",
    ///     "properties": {
    ///         "title": {"type": "string"},
    ///         "price": {"type": "number"},
    ///         "description": {"type": "string"}
    ///     }
    /// });
    /// let result = extractor.extract_structured(html_content, schema, "提取商品信息").await?;
    /// ```
    pub async fn extract_structured(
        &self,
        content: &str,
        schema: Value,
        instructions: &str,
    ) -> Result<Value, AIError> {
        let prompt = format!(
            r#"请从以下内容中提取结构化数据。

提取要求：{}

期望的输出格式（JSON Schema）：
{}

页面内容：
{}

请直接返回符合 JSON Schema 的 JSON 对象，不要包含其他解释。"#,
            instructions,
            schema,
            content
        );

        self.call_llm(&prompt).await
    }

    /// 页面理解
    /// 
    /// # Arguments
    /// * `content` - 页面内容
    /// * `question` - 关于页面的问题
    /// 
    /// # Example
    /// ```
    /// let extractor = AIExtractor::with_openai_api_key("your-api-key");
    /// let answer = extractor.understand_page(html_content, "这个页面的主要功能是什么？").await?;
    /// ```
    pub async fn understand_page(
        &self,
        content: &str,
        question: &str,
    ) -> Result<String, AIError> {
        let prompt = format!(
            r#"请分析以下网页内容并回答问题。

问题：{}

页面内容：
{}

请详细回答。"#,
            question,
            content
        );

        let response = self.call_llm(&prompt).await?;
        Ok(response["text"].as_str().unwrap_or("").to_string())
    }

    /// 生成爬虫配置
    /// 
    /// # Arguments
    /// * `description` - 自然语言描述
    /// 
    /// # Example
    /// ```
    /// let extractor = AIExtractor::with_openai_api_key("your-api-key");
    /// let config = extractor.generate_spider_config("爬取知乎热门问题").await?;
    /// ```
    pub async fn generate_spider_config(
        &self,
        description: &str,
    ) -> Result<Value, AIError> {
        let prompt = format!(
            r#"根据以下自然语言描述，生成爬虫配置（JSON 格式）。

描述：{}

请返回以下格式的 JSON：
{{
    "start_urls": ["起始 URL"],
    "rules": [
        {{
            "name": "规则名称",
            "pattern": "URL 匹配模式",
            "extract": ["要提取的字段"],
            "follow_links": true/false
        }}
    ],
    "settings": {{
        "concurrency": 并发数，
        "max_depth": 最大深度，
        "delay": 请求延迟（毫秒）
    }}
}}

只返回 JSON，不要其他解释。"#,
            description
        );

        self.call_llm(&prompt).await
    }

    /// 调用 LLM
    async fn call_llm(&self, prompt: &str) -> Result<Value, AIError> {
        let url = format!("{}/chat/completions", self.config.base_url);
        
        let response = self.client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.config.api_key))
            .header("Content-Type", "application/json")
            .json(&json!({
                "model": self.config.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature
            }))
            .send()
            .await
            .map_err(|e| AIError::RequestFailed(e.to_string()))?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            return Err(AIError::APIError(format!("HTTP {}: {}", status, error_text)));
        }

        let result: Value = response
            .json()
            .await
            .map_err(|e| AIError::ParseFailed(e.to_string()))?;

        // 解析 OpenAI 格式响应
        if let Some(choices) = result["choices"].as_array() {
            if let Some(first) = choices.first() {
                if let Some(content) = first["message"]["content"].as_str() {
                    // 尝试解析为 JSON
                    if let Ok(json) = serde_json::from_str::<Value>(content) {
                        return Ok(json);
                    }
                    // 返回文本
                    return Ok(json!({ "text": content }));
                }
            }
        }

        Err(AIError::UnexpectedResponse(result))
    }
}

/// AI 错误类型
#[derive(Debug, thiserror::Error)]
pub enum AIError {
    #[error("请求失败：{0}")]
    RequestFailed(String),
    
    #[error("API 错误：{0}")]
    APIError(String),
    
    #[error("解析失败：{0}")]
    ParseFailed(String),
    
    #[error("意外的响应：{0:?}")]
    UnexpectedResponse(Value),
    
    #[error("配置错误：{0}")]
    ConfigError(String),
}

/// AI 提取结果
#[derive(Debug, Serialize, Deserialize)]
pub struct AIExtractionResult {
    pub success: bool,
    pub data: Value,
    pub confidence: f32,
    pub message: Option<String>,
}

/// 页面分析结果
#[derive(Debug, Serialize, Deserialize)]
pub struct PageAnalysis {
    pub page_type: String,
    pub main_content: String,
    pub links: Vec<LinkInfo>,
    pub entities: Vec<Entity>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LinkInfo {
    pub url: String,
    pub text: String,
    pub link_type: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Entity {
    pub name: String,
    pub entity_type: String,
    pub value: String,
}

/// 智能爬虫助手
pub struct SpiderAssistant {
    extractor: AIExtractor,
}

impl SpiderAssistant {
    pub fn new(api_key: &str) -> Self {
        Self {
            extractor: AIExtractor::with_openai_api_key(api_key),
        }
    }

    /// 分析页面并返回结构化信息
    pub async fn analyze_page(&self, content: &str) -> Result<PageAnalysis, AIError> {
        let prompt = format!(
            r#"请分析以下网页内容，返回结构化信息。

页面内容：
{}

请返回以下格式的 JSON：
{{
    "page_type": "页面类型（如：文章页、列表页、商品页等）",
    "main_content": "主要内容摘要",
    "links": [
        {{"url": "链接", "text": "链接文本", "link_type": "链接类型"}}
    ],
    "entities": [
        {{"name": "实体名", "entity_type": "实体类型", "value": "值"}}
    ]
}}"#,
            content
        );

        let result = self.extractor.call_llm(&prompt).await?;
        
        serde_json::from_value(result)
            .map_err(|e| AIError::ParseFailed(e.to_string()))
    }

    /// 判断是否需要爬取该页面
    pub async fn should_crawl(
        &self,
        content: &str,
        criteria: &str,
    ) -> Result<bool, AIError> {
        let prompt = format!(
            r#"请判断是否应该爬取以下页面。

爬取标准：{}

页面内容：
{}

请只返回 true 或 false。"#,
            criteria,
            content
        );

        let result = self.extractor.call_llm(&prompt).await?;
        
        if let Some(text) = result["text"].as_str() {
            Ok(text.trim().to_lowercase() == "true")
        } else {
            Ok(false)
        }
    }

    /// 提取指定字段
    pub async fn extract_fields(
        &self,
        content: &str,
        fields: &[&str],
    ) -> Result<Value, AIError> {
        let fields_json = serde_json::to_value(fields).unwrap();
        
        let prompt = format!(
            r#"请从以下内容中提取指定字段。

需要提取的字段：{}

页面内容：
{}

请返回包含这些字段的 JSON 对象。"#,
            fields_json,
            content
        );

        self.extractor.call_llm(&prompt).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    #[ignore] // 需要 API Key
    async fn test_extract_structured() {
        let extractor = AIExtractor::with_openai_api_key("test-key");
        let schema = json!({
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "price": {"type": "number"}
            }
        });
        
        let result = extractor.extract_structured(
            "<html><h1>Test Product</h1><span>$99.99</span></html>",
            schema,
            "提取商品信息"
        ).await;
        
        assert!(result.is_ok());
    }
}
