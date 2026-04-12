//! YouTube 视频下载器
//! 支持 YouTube 视频信息提取和下载

use std::error::Error;
use std::fs::{self, File};
use std::io::{Read, Write};
use std::path::Path;
use regex::Regex;
use serde::{Deserialize, Serialize};
use serde_json::Value;

/// YouTube 视频数据
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct YouTubeVideoData {
    pub title: String,
    pub video_id: String,
    pub author: String,
    pub duration: i64,
    pub description: String,
    pub thumbnail: String,
    pub formats: Vec<FormatInfo>,
    pub video_url: Option<String>,
}

/// 格式信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FormatInfo {
    pub itag: i32,
    pub mime_type: String,
    pub quality: String,
    pub width: i32,
    pub height: i32,
    pub bitrate: i32,
    pub url: String,
    pub has_audio: bool,
    pub has_video: bool,
    pub codecs: String,
}

/// YouTube 解析器
pub struct YouTubeParser {
    client: reqwest::blocking::Client,
}

impl YouTubeParser {
    pub fn new() -> Result<Self, Box<dyn Error>> {
        let client = reqwest::blocking::Client::builder()
            .timeout(std::time::Duration::from_secs(30))
            .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            .build()?;

        Ok(Self { client })
    }

    /// 解析 YouTube 视频
    pub fn parse(&self, url: &str) -> Option<YouTubeVideoData> {
        println!("Parsing YouTube video: {}", url);

        // 提取视频 ID
        let video_id = self.extract_video_id(url)?;

        // 获取页面
        let resp = self.client.get(url).send().ok()?;
        let html = resp.text().ok()?;

        // 提取视频信息
        self.extract_video_info(&html, url, &video_id)
    }

    /// 从 HTML 提取视频信息
    fn extract_video_info(&self, html: &str, url: &str, video_id: &str) -> Option<YouTubeVideoData> {
        // 查找 ytInitialPlayerResponse
        let player_response = self.find_player_response(html)?;

        let mut video_data = YouTubeVideoData {
            title: String::new(),
            video_id: video_id.to_string(),
            author: String::new(),
            duration: 0,
            description: String::new(),
            thumbnail: String::new(),
            formats: Vec::new(),
            video_url: None,
        };

        // 提取视频详情
        if let Some(video_details) = player_response.get("videoDetails").and_then(|v| v.as_object()) {
            video_data.title = video_details.get("title").and_then(|v| v.as_str()).unwrap_or("Unknown").to_string();
            video_data.author = video_details.get("author").and_then(|v| v.as_str()).unwrap_or("Unknown").to_string();
            video_data.duration = video_details.get("lengthSeconds").and_then(|v| v.as_i64()).unwrap_or(0);
            video_data.description = video_details.get("shortDescription").and_then(|v| v.as_str()).unwrap_or("").to_string();

            // 提取缩略图
            if let Some(thumbnail) = video_details.get("thumbnail").and_then(|v| v.as_object()) {
                if let Some(thumbnails) = thumbnail.get("thumbnails").and_then(|v| v.as_array()) {
                    if let Some(last) = thumbnails.last().and_then(|v| v.as_object()) {
                        video_data.thumbnail = last.get("url").and_then(|v| v.as_str()).unwrap_or("").to_string();
                    }
                }
            }
        }

        // 提取流媒体数据
        if let Some(streaming_data) = player_response.get("streamingData").and_then(|v| v.as_object()) {
            let formats = self.extract_formats(streaming_data);
            video_data.formats = formats.clone();

            // 选择最佳格式（带音频的视频）
            for fmt in formats {
                if fmt.has_audio && fmt.has_video {
                    video_data.video_url = Some(fmt.url);
                    break;
                }
            }
        }

        if video_data.video_url.is_none() {
            println!("未找到可下载的视频流");
            return None;
        }

        Some(video_data)
    }

    /// 查找 ytInitialPlayerResponse JSON
    fn find_player_response(&self, html: &str) -> Option<Value> {
        let patterns = vec![
            r"ytInitialPlayerResponse\s*=\s*(\{.+?\});",
            r"var\s+ytInitialPlayerResponse\s*=\s*(\{.+?\});",
        ];

        for pattern_str in patterns {
            if let Ok(re) = Regex::new(pattern_str) {
                if let Some(caps) = re.captures(html) {
                    if let Some(json_str) = caps.get(1).map(|m| m.as_str()) {
                        // 提取 JSON
                        let start = json_str.find('{')?;
                        let end = json_str.rfind('}')? + 1;
                        let json_str = &json_str[start..end];

                        if let Ok(json) = serde_json::from_str::<Value>(json_str) {
                            return Some(json);
                        }
                    }
                }
            }
        }

        None
    }

    /// 提取格式信息
    fn extract_formats(&self, streaming_data: &serde_json::Map<String, Value>) -> Vec<FormatInfo> {
        let mut formats = Vec::new();

        // 提取普通格式
        if let Some(formats_array) = streaming_data.get("formats").and_then(|v| v.as_array()) {
            for fmt in formats_array {
                if let Some(fmt_obj) = fmt.as_object() {
                    formats.push(self.parse_format(fmt_obj));
                }
            }
        }

        // 提取自适应格式
        if let Some(adaptive_formats) = streaming_data.get("adaptiveFormats").and_then(|v| v.as_array()) {
            for fmt in adaptive_formats {
                if let Some(fmt_obj) = fmt.as_object() {
                    formats.push(self.parse_format(fmt_obj));
                }
            }
        }

        formats
    }

    /// 解析单个格式
    fn parse_format(&self, fmt: &serde_json::Map<String, Value>) -> FormatInfo {
        let mime_type = fmt.get("mimeType").and_then(|v| v.as_str()).unwrap_or("").to_string();

        FormatInfo {
            itag: fmt.get("itag").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
            mime_type: mime_type.clone(),
            quality: fmt.get("quality").and_then(|v| v.as_str()).unwrap_or("").to_string(),
            width: fmt.get("width").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
            height: fmt.get("height").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
            bitrate: fmt.get("bitrate").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
            url: fmt.get("url").and_then(|v| v.as_str()).unwrap_or("").to_string(),
            has_audio: self.has_audio(&mime_type),
            has_video: self.has_video(&mime_type),
            codecs: fmt.get("codecs").and_then(|v| v.as_str()).unwrap_or("").to_string(),
        }
    }

    fn has_audio(&self, mime_type: &str) -> bool {
        mime_type.contains("mp4a") || mime_type.contains("opus") || mime_type.contains("ac-3")
    }

    fn has_video(&self, mime_type: &str) -> bool {
        mime_type.contains("video/") || mime_type.contains("avc") || mime_type.contains("vp9")
    }

    /// 从 URL 提取视频 ID
    fn extract_video_id(&self, url: &str) -> Option<String> {
        // youtu.be 短链接
        if url.contains("youtu.be") {
            let parts: Vec<&str> = url.split('/').collect();
            return Some(parts.last()?.to_string());
        }

        // 标准链接
        if let Ok(re) = Regex::new(r"[?&]v=([a-zA-Z0-9_-]+)") {
            if let Some(caps) = re.captures(url) {
                return Some(caps.get(1)?.as_str().to_string());
            }
        }

        // /embed/ 格式
        if let Ok(re) = Regex::new(r"/embed/([a-zA-Z0-9_-]+)") {
            if let Some(caps) = re.captures(url) {
                return Some(caps.get(1)?.as_str().to_string());
            }
        }

        None
    }

    /// 获取最佳格式
    pub fn get_best_format(&self, video_data: &YouTubeVideoData) -> Option<&FormatInfo> {
        video_data.formats
            .iter()
            .filter(|f| f.has_audio && f.has_video)
            .max_by_key(|f| f.height)
    }

    /// 按质量选择格式
    pub fn select_format_by_quality(&self, video_data: &YouTubeVideoData, quality: &str) -> Option<&FormatInfo> {
        let target_height = match quality.to_lowercase().as_str() {
            "1080p" => 1080,
            "720p" => 720,
            "480p" => 480,
            _ => 0, // best
        };

        let formats: Vec<&FormatInfo> = video_data.formats
            .iter()
            .filter(|f| f.has_audio && f.has_video)
            .collect();

        if target_height == 0 {
            // 最佳质量
            formats.into_iter().max_by_key(|f| f.height)
        } else {
            // 指定质量
            formats.into_iter()
                .filter(|f| f.height >= target_height)
                .min_by_key(|f| f.height)
        }
    }
}

/// YouTube 下载器
pub struct YouTubeDownloader {
    output_dir: String,
    parser: YouTubeParser,
    client: reqwest::blocking::Client,
}

impl YouTubeDownloader {
    pub fn new(output_dir: &str) -> Result<Self, Box<dyn Error>> {
        let parser = YouTubeParser::new()?;
        let client = reqwest::blocking::Client::builder()
            .timeout(std::time::Duration::from_secs(120))
            .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            .build()?;

        Ok(Self {
            output_dir: output_dir.to_string(),
            parser,
            client,
        })
    }

    /// 下载视频
    pub fn download(&self, url: &str) -> Result<String, Box<dyn Error>> {
        self.download_with_quality(url, "best")
    }

    /// 下载视频（指定清晰度）
    pub fn download_with_quality(&self, url: &str, quality: &str) -> Result<String, Box<dyn Error>> {
        println!("\n📺 YouTube 视频下载");
        println!("═══════════════════════════════════════════════════");
        println!("URL: {}", url);

        // 解析视频
        println!("\n正在解析视频...");
        let video_data = self.parser.parse(url)
            .ok_or("解析视频失败")?;

        // 显示信息
        println!("\n视频信息:");
        println!("  标题：{}", video_data.title);
        println!("  作者：{}", video_data.author);
        println!("  时长：{}s", video_data.duration);
        println!("  可用格式：{}", video_data.formats.len());

        // 选择格式
        let format = if quality == "best" {
            self.parser.get_best_format(&video_data)
        } else {
            self.parser.select_format_by_quality(&video_data, quality)
        }.ok_or("未找到合适的视频格式")?;

        println!("\n选择格式:");
        println!("  质量：{}", format.quality);
        println!("  分辨率：{}x{}", format.width, format.height);

        // 创建输出目录
        fs::create_dir_all(&self.output_dir)?;

        // 生成文件名
        let safe_title = Self::sanitize_filename(&video_data.title);
        let file_name = format!("{}_{}.mp4", safe_title, video_data.video_id);
        let output_path = Path::new(&self.output_dir).join(&file_name);

        // 下载
        println!("\n⬇️  正在下载...");
        self.download_file(&format.url, &output_path)?;

        println!("\n═══════════════════════════════════════════════════");
        println!("✅ 下载完成：{}", output_path.display());

        Ok(output_path.to_string_lossy().to_string())
    }

    /// 下载文件
    fn download_file(&self, url: &str, path: &Path) -> Result<(), Box<dyn Error>> {
        let mut resp = self.client.get(url).send()?;
        
        if !resp.status().is_success() {
            return Err(format!("HTTP 错误：{}", resp.status()).into());
        }

        let total = resp.content_length().unwrap_or(0);
        let mut downloaded: u64 = 0;

        let mut file = File::create(path)?;
        let mut buffer = [0u8; 8192];

        loop {
            match resp.read(&mut buffer)? {
                0 => break,
                n => {
                    file.write_all(&buffer[..n])?;
                    downloaded += n as u64;

                    if total > 0 {
                        let percent = (downloaded * 100 / total) as u32;
                        print!("\r进度：{}%", percent);
                    }
                }
            }
        }

        println!("\r进度：100%");
        Ok(())
    }

    /// 清理文件名
    fn sanitize_filename(name: &str) -> String {
        let invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*'];
        let mut sanitized: String = name.chars()
            .map(|c| if invalid_chars.contains(&c) { '_' } else { c })
            .collect();

        sanitized = sanitized.trim().to_string();
        if sanitized.len() > 100 {
            sanitized = sanitized[..100].to_string();
        }

        sanitized
    }

    /// 获取解析器
    pub fn get_parser(&self) -> &YouTubeParser {
        &self.parser
    }
}
