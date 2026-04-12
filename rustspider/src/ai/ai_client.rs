use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::error::Error;

#[derive(Debug, Serialize)]
struct ChatMessage {
    role: String,
    content: String,
}

#[derive(Debug, Deserialize)]
struct AIResponse {
    choices: Vec<Choice>,
}

#[derive(Debug, Deserialize)]
struct Choice {
    message: Message,
}

#[derive(Debug, Deserialize)]
struct Message {
    content: String,
}

/// AI 智能助手客户端
pub struct AIClient {
    client: Client,
    api_key: String,
    endpoint: String,
}

impl AIClient {
    /// 创建新的 AI 客户端
    pub fn new(api_key: &str, endpoint: Option<&str>) -> Self {
        // 修复：创建带超时的 Client
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(30)) // 30 秒超时
            .build()
            .expect("Failed to create HTTP client");

        Self {
            client,
            api_key: api_key.to_string(),
            endpoint: endpoint
                .unwrap_or("https://api.openai.com/v1/chat/completions")
                .to_string(),
        }
    }

    /// 提取页面结构化数据
    pub async fn extract_data(
        &self,
        html_content: &str,
        description: &str,
    ) -> Result<String, Box<dyn Error>> {
        let prompt = format!(
            "You are a web scraping expert. Extract data from the following HTML based on this description: {}\n\nHTML:\n{}",
            description,
            &html_content[..html_content.len().min(8000)]
        );

        self.chat(&prompt).await
    }

    /// 智能分析页面内容
    pub async fn analyze_page(&self, html_content: &str) -> Result<String, Box<dyn Error>> {
        let prompt = format!(
            "Analyze this HTML and tell me:\n1. What type of page is this?\n2. What data can be extracted?\n3. What are the main CSS selectors/XPaths to target?\n\nHTML:\n{}",
            &html_content[..html_content.len().min(5000)]
        );

        self.chat(&prompt).await
    }

    /// 生成爬虫代码
    pub async fn generate_scraper(
        &self,
        url: &str,
        target_data: &str,
        language: &str,
    ) -> Result<String, Box<dyn Error>> {
        let prompt = format!(
            "Generate a complete scraper in {} for this URL: {}\nTarget data: {}\nInclude error handling and data extraction.",
            language,
            url,
            target_data
        );

        self.chat(&prompt).await
    }

    /// 通用聊天方法
    async fn chat(&self, prompt: &str) -> Result<String, Box<dyn Error>> {
        let messages = vec![
            ChatMessage {
                role: "system".to_string(),
                content: "You are an expert web scraping assistant.".to_string(),
            },
            ChatMessage {
                role: "user".to_string(),
                content: prompt.to_string(),
            },
        ];

        let response = self
            .client
            .post(&self.endpoint)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .json(&serde_json::json!({
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "temperature": 0.7
            }))
            .send()
            .await?
            .json::<AIResponse>()
            .await?;

        // 修复：安全检查空数组，防止 panic
        let choice = response
            .choices
            .first()
            .ok_or("AI API returned empty choices array")?;
        Ok(choice.message.content.clone())
    }
}
