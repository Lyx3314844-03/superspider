use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::error::Error;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum AIProvider {
    OpenAI,
    Anthropic,
}

#[derive(Debug, Serialize)]
struct ChatMessage {
    role: String,
    content: String,
}

#[derive(Debug, Clone)]
pub struct FewShotExample {
    pub user: String,
    pub assistant: String,
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
    model: String,
    provider: AIProvider,
}

impl AIClient {
    /// 创建新的 AI 客户端
    pub fn new(api_key: &str, endpoint: Option<&str>) -> Self {
        // 修复：创建带超时的 Client
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(30)) // 30 秒超时
            .build()
            .expect("Failed to create HTTP client");

        let endpoint = endpoint.unwrap_or("https://api.openai.com/v1/chat/completions");
        let provider = detect_provider(endpoint, None);
        Self {
            client,
            api_key: api_key.to_string(),
            endpoint: endpoint.to_string(),
            model: default_model(provider).to_string(),
            provider,
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

    pub async fn chat_with_examples(
        &self,
        prompt: &str,
        examples: &[FewShotExample],
    ) -> Result<String, Box<dyn Error>> {
        match self.provider {
            AIProvider::Anthropic => self.chat_anthropic(prompt, examples).await,
            AIProvider::OpenAI => self.chat_openai(prompt, examples).await,
        }
    }

    /// 通用聊天方法
    async fn chat(&self, prompt: &str) -> Result<String, Box<dyn Error>> {
        self.chat_with_examples(prompt, &[]).await
    }

    async fn chat_openai(
        &self,
        prompt: &str,
        examples: &[FewShotExample],
    ) -> Result<String, Box<dyn Error>> {
        let mut messages = vec![ChatMessage {
            role: "system".to_string(),
            content: "You are an expert web scraping assistant.".to_string(),
        }];
        messages.extend(build_messages(prompt, examples));

        let response = self
            .client
            .post(&self.endpoint)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .json(&serde_json::json!({
                "model": self.model,
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

    async fn chat_anthropic(
        &self,
        prompt: &str,
        examples: &[FewShotExample],
    ) -> Result<String, Box<dyn Error>> {
        let response = self
            .client
            .post(build_anthropic_endpoint(&self.endpoint))
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", "2023-06-01")
            .header("Content-Type", "application/json")
            .json(&serde_json::json!({
                "model": self.model,
                "max_tokens": 1024,
                "temperature": 0.7,
                "messages": build_messages(prompt, examples)
            }))
            .send()
            .await?
            .json::<serde_json::Value>()
            .await?;

        let content = response["content"]
            .as_array()
            .ok_or("Anthropic API returned invalid content array")?;
        let text = content
            .iter()
            .find_map(|item| item.get("text").and_then(|value| value.as_str()))
            .ok_or("Anthropic API returned empty content array")?;
        Ok(text.to_string())
    }
}

fn detect_provider(endpoint: &str, model: Option<&str>) -> AIProvider {
    let endpoint_lower = endpoint.to_ascii_lowercase();
    let model_lower = model.unwrap_or_default().to_ascii_lowercase();
    if endpoint_lower.contains("anthropic") || model_lower.contains("claude") {
        AIProvider::Anthropic
    } else {
        AIProvider::OpenAI
    }
}

fn default_model(provider: AIProvider) -> &'static str {
    match provider {
        AIProvider::OpenAI => "gpt-5.2",
        AIProvider::Anthropic => "claude-sonnet-4-20250514",
    }
}

fn build_anthropic_endpoint(endpoint: &str) -> String {
    let trimmed = endpoint.trim_end_matches('/');
    if trimmed.ends_with("/messages") {
        trimmed.to_string()
    } else {
        format!("{trimmed}/messages")
    }
}

fn build_messages(prompt: &str, examples: &[FewShotExample]) -> Vec<ChatMessage> {
    let mut messages = Vec::new();
    for example in examples {
        if !example.user.trim().is_empty() {
            messages.push(ChatMessage {
                role: "user".to_string(),
                content: example.user.clone(),
            });
        }
        if !example.assistant.trim().is_empty() {
            messages.push(ChatMessage {
                role: "assistant".to_string(),
                content: example.assistant.clone(),
            });
        }
    }
    messages.push(ChatMessage {
        role: "user".to_string(),
        content: prompt.to_string(),
    });
    messages
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Read, Write};
    use std::net::TcpListener;
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::sync::Arc;
    use std::thread;
    use std::time::Duration;

    struct MockServer {
        addr: String,
        shutdown: Arc<AtomicBool>,
        handle: Option<thread::JoinHandle<()>>,
    }

    impl Drop for MockServer {
        fn drop(&mut self) {
            self.shutdown.store(true, Ordering::SeqCst);
            let _ = std::net::TcpStream::connect(&self.addr);
            if let Some(handle) = self.handle.take() {
                let _ = handle.join();
            }
        }
    }

    fn start_mock_server() -> MockServer {
        let listener = TcpListener::bind("127.0.0.1:0").expect("listener");
        listener.set_nonblocking(true).expect("nonblocking");
        let addr = listener.local_addr().expect("addr");
        let shutdown = Arc::new(AtomicBool::new(false));
        let flag = shutdown.clone();
        let handle = thread::spawn(move || {
            while !flag.load(Ordering::SeqCst) {
                match listener.accept() {
                    Ok((mut stream, _)) => {
                        let mut buffer = [0_u8; 8192];
                        let size = stream.read(&mut buffer).unwrap_or(0);
                        let request = String::from_utf8_lossy(&buffer[..size]).to_string();
                        let body = if request.starts_with("POST /messages") {
                            r#"{"content":[{"type":"text","text":"anthropic-response"}]}"#
                        } else {
                            r#"{"choices":[{"message":{"content":"openai-response"}}]}"#
                        };
                        let response = format!(
                            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                            body.len(),
                            body
                        );
                        let _ = stream.write_all(response.as_bytes());
                        let _ = stream.flush();
                    }
                    Err(err) if err.kind() == std::io::ErrorKind::WouldBlock => {
                        thread::sleep(Duration::from_millis(20));
                    }
                    Err(_) => break,
                }
            }
        });

        MockServer {
            addr: addr.to_string(),
            shutdown,
            handle: Some(handle),
        }
    }

    #[tokio::test]
    async fn ai_client_supports_anthropic_messages_api() {
        let server = start_mock_server();
        let client = AIClient::new("anthropic-key", Some(&format!("http://{}", server.addr)));

        let response = client.chat("hello").await.expect("chat should succeed");
        assert_eq!(response, "openai-response");

        let anthropic = AIClient {
            client: Client::builder()
                .timeout(Duration::from_secs(30))
                .build()
                .unwrap(),
            api_key: "anthropic-key".to_string(),
            endpoint: format!("http://{}", server.addr),
            model: "claude-sonnet-4-20250514".to_string(),
            provider: AIProvider::Anthropic,
        };
        let response = anthropic
            .chat("hello")
            .await
            .expect("anthropic chat should succeed");
        assert_eq!(response, "anthropic-response");
    }

    #[tokio::test]
    async fn ai_client_supports_few_shot_messages() {
        let server = start_mock_server();
        let client = AIClient::new("openai-key", Some(&format!("http://{}", server.addr)));

        let response = client
            .chat_with_examples(
                "final-question",
                &[FewShotExample {
                    user: "example-question".to_string(),
                    assistant: "example-answer".to_string(),
                }],
            )
            .await
            .expect("few-shot chat should succeed");

        assert_eq!(response, "openai-response");
    }
}
