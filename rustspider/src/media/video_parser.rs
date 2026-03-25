//! 视频平台解析器
//! 支持优酷、爱奇艺、腾讯等平台

use std::error::Error;
use regex::Regex;
use serde::{Deserialize, Serialize};

/// 视频数据
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VideoData {
    pub title: String,
    pub video_id: String,
    pub platform: String,
    pub m3u8_url: Option<String>,
    pub mp4_url: Option<String>,
    pub dash_url: Option<String>,
    pub download_url: Option<String>,
    pub cover_url: Option<String>,
    pub duration: i64,
    pub description: String,
}

/// 通用解析器
pub struct UniversalParser {
    client: reqwest::blocking::Client,
}

impl UniversalParser {
    pub fn new() -> Result<Self, Box<dyn Error>> {
        let client = reqwest::blocking::Client::builder()
            .timeout(std::time::Duration::from_secs(30))
            .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            .build()?;

        Ok(Self { client })
    }

    /// 解析视频
    pub fn parse(&self, url: &str) -> Option<VideoData> {
        // 检测平台
        if let Some(platform) = self.detect_platform(url) {
            match platform {
                "youku" => return self.parse_youku(url),
                "iqiyi" => return self.parse_iqiyi(url),
                "tencent" => return self.parse_tencent(url),
                _ => {}
            }
        }

        // 通用解析
        self.universal_parse(url)
    }

    fn detect_platform(&self, url: &str) -> Option<&str> {
        if url.contains("youku.com") || url.contains("youku.tv") {
            Some("youku")
        } else if url.contains("iqiyi.com") {
            Some("iqiyi")
        } else if url.contains("qq.com") || url.contains("v.qq.com") {
            Some("tencent")
        } else {
            None
        }
    }

    fn parse_youku(&self, url: &str) -> Option<VideoData> {
        let video_id = self.extract_video_id(url, r"id_(?:X)?([a-zA-Z0-9=]+)")?;

        // 获取页面
        let resp = self.client.get(url).send().ok()?;
        let html = resp.text().ok()?;

        let title = self.extract_title(&html, &video_id);
        let video_data = self.extract_video_data(&html);

        Some(VideoData {
            title,
            video_id,
            platform: "youku".to_string(),
            m3u8_url: video_data.get("m3u8_url").cloned(),
            mp4_url: video_data.get("mp4_url").cloned(),
            download_url: video_data.get("download_url").cloned(),
            cover_url: video_data.get("cover_url").cloned(),
            duration: 0,
            description: String::new(),
        })
    }

    fn parse_iqiyi(&self, url: &str) -> Option<VideoData> {
        let video_id = self.extract_video_id(url, r"/v_(\w+)\.html")?;

        let resp = self.client.get(url).send().ok()?;
        let html = resp.text().ok()?;

        let title = self.extract_title(&html, &video_id);

        // 查找 M3U8
        let m3u8_url = Regex::new(r"(https?://[^"\s]+\.m3u8[^"\s]*)")
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().to_string());

        Some(VideoData {
            title,
            video_id,
            platform: "iqiyi".to_string(),
            m3u8_url,
            mp4_url: None,
            dash_url: None,
            download_url: None,
            cover_url: None,
            duration: 0,
            description: String::new(),
        })
    }

    fn parse_tencent(&self, url: &str) -> Option<VideoData> {
        let video_id = self.extract_video_id(url, r"/x/(\w+)\.html")?;

        let resp = self.client.get(url).send().ok()?;
        let html = resp.text().ok()?;

        let title = self.extract_title(&html, &video_id);

        // 查找 MP4
        let mp4_url = Regex::new(r#""url"\s*:\s*"([^"]+\.mp4[^"]*)""#)
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().to_string());

        Some(VideoData {
            title,
            video_id,
            platform: "tencent".to_string(),
            m3u8_url: None,
            mp4_url,
            dash_url: None,
            download_url: None,
            cover_url: None,
            duration: 0,
            description: String::new(),
        })
    }

    fn universal_parse(&self, url: &str) -> Option<VideoData> {
        let resp = self.client.get(url).send().ok()?;
        let html = resp.text().ok()?;

        // 提取标题
        let title = Regex::new(r"<title>([^<]+)</title>")
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().trim().to_string())?;

        // 提取 M3U8
        let m3u8_url = Regex::new(r"(https?://[^"\s]+\.m3u8[^"\s]*)")
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().to_string());

        // 提取 MP4
        let mp4_url = Regex::new(r"(https?://[^"\s]+\.mp4[^"\s]*)")
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().to_string());

        Some(VideoData {
            title,
            video_id: format!("{:x}", md5::compute(url.as_bytes())),
            platform: "unknown".to_string(),
            m3u8_url,
            mp4_url,
            dash_url: None,
            download_url: None,
            cover_url: None,
            duration: 0,
            description: String::new(),
        })
    }

    fn extract_video_id(&self, url: &str, pattern: &str) -> Option<String> {
        Regex::new(pattern)
            .ok()
            .and_then(|re| re.captures(url))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().to_string())
    }

    fn extract_title(&self, html: &str, video_id: &str) -> String {
        Regex::new(r"<title>([^<]+)</title>")
            .ok()
            .and_then(|re| re.captures(html))
            .and_then(|caps| caps.get(1))
            .map(|m| {
                let title = m.as_str().trim();
                // 清理标题
                let title = regex::Regex::new(r"\s*-?\s*优酷\s*$")
                    .ok()
                    .and_then(|re| Some(re.replace_all(title, "")))
                    .map(|s| s.to_string())
                    .unwrap_or_else(|| title.to_string());
                title
            })
            .unwrap_or_else(|| format!("Video {}", video_id))
    }

    fn extract_video_data(&self, html: &str) -> std::collections::HashMap<String, String> {
        let mut data = std::collections::HashMap::new();

        // 查找 M3U8
        if let Some(m3u8) = Regex::new(r"(https?://[^"\s]+\.m3u8[^"\s]*)")
            .ok()
            .and_then(|re| re.captures(html))
            .and_then(|caps| caps.get(1))
        {
            data.insert("m3u8_url".to_string(), m3u8.as_str().to_string());
        }

        // 查找封面
        if let Some(cover) = Regex::new(r#""poster"\s*:\s*"([^"]+)""#)
            .ok()
            .and_then(|re| re.captures(html))
            .and_then(|caps| caps.get(1))
        {
            data.insert("cover_url".to_string(), cover.as_str().to_string());
        }

        data
    }
}

impl Default for UniversalParser {
    fn default() -> Self {
        Self::new().unwrap()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parser() {
        let parser = UniversalParser::new().unwrap();
        
        // 注意：这是示例测试，需要有效的 URL
        // let video = parser.parse("https://v.youku.com/...");
        // assert!(video.is_some());
    }
}
