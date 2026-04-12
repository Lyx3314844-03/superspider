use reqwest::Client;
use std::error::Error;

pub mod video_parser;
pub use video_parser::{UniversalParser, VideoData};

/// 媒体下载器
pub struct MediaDownloader {
    client: Client,
}

impl MediaDownloader {
    pub fn new() -> Self {
        Self {
            client: Client::new(),
        }
    }

    /// 下载单个文件
    pub async fn download_file(&self, url: &str, output_path: &str) -> Result<(), Box<dyn Error>> {
        println!("⬇️  Downloading: {}", url);

        let response = self.client.get(url).send().await?;
        let bytes = response.bytes().await?;

        std::fs::write(output_path, bytes)?;
        println!("✅ Saved to: {}", output_path);

        Ok(())
    }

    /// 批量下载文件
    pub async fn batch_download(
        &self,
        urls: Vec<&str>,
        output_dir: &str,
    ) -> Result<Vec<(String, Result<(), Box<dyn Error>>)>, Box<dyn Error>> {
        let mut results = Vec::new();

        for url in urls {
            let filename = url.split('/').next_back().unwrap_or("unknown");
            let output_path = format!("{}/{}", output_dir, filename);

            let result = self.download_file(url, &output_path).await;
            results.push((url.to_string(), result));
        }

        Ok(results)
    }
}

impl Default for MediaDownloader {
    fn default() -> Self {
        Self::new()
    }
}
