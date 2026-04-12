use reqwest::Client;
use serde::{Deserialize, Serialize};

/// Rust 语言调用 Crawlee 桥接服务的客户端
pub struct CrawleeBridgeClient {
    bridge_url: String,
    http_client: Client,
}

#[derive(Serialize)]
struct CrawlRequest {
    urls: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    on_page_script: Option<String>,
    max_concurrency: usize,
}

#[derive(Deserialize, Debug)]
pub struct CrawlResponse {
    pub success: bool,
    pub data: Option<serde_json::Value>,
    pub error: Option<String>,
}

impl CrawleeBridgeClient {
    pub fn new(bridge_url: String) -> Self {
        Self {
            bridge_url,
            http_client: Client::new(),
        }
    }

    /// 执行 Crawlee 抓取任务
    pub async fn crawl(
        &self,
        urls: Vec<String>,
        script: Option<String>,
        max_concurrency: usize,
    ) -> Result<CrawlResponse, Box<dyn std::error::Error>> {
        let payload = CrawlRequest {
            urls,
            on_page_script: script,
            max_concurrency,
        };

        let response = self
            .http_client
            .post(format!("{}/api/crawl", self.bridge_url))
            .json(&payload)
            .send()
            .await?;

        let result: CrawlResponse = response.json().await?;

        if !result.success {
            return Err(format!("Bridge Error: {}", result.error.unwrap_or_default()).into());
        }

        Ok(result)
    }
}
