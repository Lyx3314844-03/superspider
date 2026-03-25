//! Rust 爬虫增强模块
//! 提供统一的爬虫接口和工具函数

use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::fs::File;
use std::io::{BufWriter, Write};
use std::time::Instant;

/// 视频数据项
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VideoItem {
    pub index: u32,
    pub title: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub duration: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub channel: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub url: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub thumbnail: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub views: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub published: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub description: String,
}

impl VideoItem {
    pub fn new() -> Self {
        Self {
            index: 0,
            title: String::new(),
            duration: String::new(),
            channel: String::new(),
            url: String::new(),
            thumbnail: String::new(),
            views: String::new(),
            published: String::new(),
            description: String::new(),
        }
    }

    pub fn with_title(title: impl Into<String>) -> Self {
        Self {
            title: title.into(),
            ..Self::new()
        }
    }

    pub fn to_map(&self) -> serde_json::Value {
        serde_json::json!({
            "index": self.index,
            "title": self.title,
            "duration": self.duration,
            "channel": self.channel,
            "url": self.url,
            "thumbnail": self.thumbnail,
            "views": self.views,
            "published": self.published,
            "description": self.description,
        })
    }
}

impl Default for VideoItem {
    fn default() -> Self {
        Self::new()
    }
}

/// 爬取统计信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CrawlStats {
    pub total_videos: usize,
    pub unique_channels: usize,
    pub crawl_time_secs: f64,
    pub start_time: String,
    pub end_time: String,
    pub total_duration: String,
}

impl CrawlStats {
    pub fn new() -> Self {
        Self {
            total_videos: 0,
            unique_channels: 0,
            crawl_time_secs: 0.0,
            start_time: String::new(),
            end_time: String::new(),
            total_duration: String::new(),
        }
    }
}

impl Default for CrawlStats {
    fn default() -> Self {
        Self::new()
    }
}

/// 增强型 YouTube 爬虫基类
pub struct YouTubeSpiderBase {
    pub name: String,
    pub platform: String,
    pub playlist_url: String,
    pub videos: Vec<VideoItem>,
    pub stats: CrawlStats,
    pub settings: serde_json::Value,
    start_time: Option<Instant>,
    start_datetime: Option<String>,
    end_datetime: Option<String>,
}

impl YouTubeSpiderBase {
    pub fn new(playlist_url: impl Into<String>) -> Self {
        Self {
            name: "youtube_spider".to_string(),
            platform: "Rust".to_string(),
            playlist_url: playlist_url.into(),
            videos: Vec::new(),
            stats: CrawlStats::new(),
            settings: serde_json::json!({}),
            start_time: None,
            start_datetime: None,
            end_datetime: None,
        }
    }

    pub fn with_settings(playlist_url: impl Into<String>, settings: serde_json::Value) -> Self {
        Self {
            settings,
            ..Self::new(playlist_url)
        }
    }

    /// 启动爬虫（模板方法）
    pub fn start(&mut self) -> Result<&Vec<VideoItem>, Box<dyn std::error::Error>> {
        self.before_start();

        if let Err(e) = self.initialize() {
            self.on_error(e.as_ref());
            return Ok(&self.videos);
        }

        if let Err(e) = self.navigate() {
            self.on_error(e.as_ref());
            return Ok(&self.videos);
        }

        if let Err(e) = self.wait_and_scroll() {
            self.on_error(e.as_ref());
            return Ok(&self.videos);
        }

        if let Err(e) = self.extract_content() {
            self.on_error(e.as_ref());
            return Ok(&self.videos);
        }

        if let Err(e) = self.parse_videos() {
            self.on_error(e.as_ref());
            return Ok(&self.videos);
        }

        self.after_extract();
        self.calculate_stats();
        self.print_results();

        Ok(&self.videos)
    }

    fn before_start(&mut self) {
        self.start_time = Some(Instant::now());
        self.start_datetime = Some(chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string());
        self.stats.start_time = self.start_datetime.clone().unwrap();
        self.print_header();
    }

    fn print_header(&self) {
        println!("\n{}", "╔".repeat(30));
        println!(
            "{} {} - YouTube 爬虫 {}",
            "║".repeat(10),
            self.platform,
            "║".repeat(10)
        );
        println!("{}", "╚".repeat(30));
        println!("\n📺 播放列表：{}\n", self.playlist_url);
    }

    /// 初始化（子类实现）
    fn initialize(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        Ok(())
    }

    /// 导航到页面（子类实现）
    fn navigate(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        Ok(())
    }

    /// 等待和滚动（子类实现）
    fn wait_and_scroll(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        Ok(())
    }

    /// 提取内容（子类实现）
    fn extract_content(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        Ok(())
    }

    /// 解析视频（子类实现）
    fn parse_videos(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        Ok(())
    }

    fn after_extract(&mut self) {
        if let Some(instant) = self.start_time {
            let elapsed = instant.elapsed();
            self.stats.crawl_time_secs = elapsed.as_secs_f64();
        }
        self.end_datetime = Some(chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string());
        self.stats.end_time = self.end_datetime.clone().unwrap();
    }

    fn calculate_stats(&mut self) {
        self.stats.total_videos = self.videos.len();
        let channels: HashSet<&String> = self
            .videos
            .iter()
            .filter_map(|v| {
                if v.channel.is_empty() {
                    None
                } else {
                    Some(&v.channel)
                }
            })
            .collect();
        self.stats.unique_channels = channels.len();
    }

    fn print_results(&self) {
        println!("\n{}", "═".repeat(60));
        println!("{:>20}爬取结果", "");
        println!("{}", "═".repeat(60));
        println!("共找到 {} 个视频", self.stats.total_videos);
        println!("唯一频道数：{}", self.stats.unique_channels);
        println!("爬取耗时：{:.2}秒", self.stats.crawl_time_secs);
        println!("\n前 20 个视频:");

        for (i, video) in self.videos.iter().take(20).enumerate() {
            println!("\n{:2}. {}", i + 1, video.title);
            if !video.duration.is_empty() {
                println!("    ⏱️  时长：{}", video.duration);
            }
            if !video.channel.is_empty() {
                println!("    👤  频道：{}", video.channel);
            }
        }

        if self.videos.len() > 20 {
            println!("\n... 还有 {} 个视频", self.videos.len() - 20);
        }
    }

    fn on_error(&self, error: &dyn std::error::Error) {
        println!("\n❌ 爬取失败：{}", error);
    }

    /// 保存到文件
    pub fn save_to_file(
        &self,
        filename: Option<&str>,
        format: &str,
    ) -> Result<String, Box<dyn std::error::Error>> {
        let default_filename = format!(
            "youtube_playlist_{}.{}",
            chrono::Local::now().format("%Y%m%d_%H%M%S"),
            format
        );
        let filename = filename.unwrap_or(&default_filename);

        match format.to_lowercase().as_str() {
            "json" => self.save_json(filename)?,
            "txt" => self.save_txt(filename)?,
            "csv" => self.save_csv(filename)?,
            _ => return Err(format!("不支持的格式：{}", format).into()),
        }

        println!("💾 结果已保存到：{}", filename);
        Ok(filename.to_string())
    }

    fn save_json(&self, filename: &str) -> Result<(), Box<dyn std::error::Error>> {
        let file = File::create(filename)?;
        let mut writer = BufWriter::new(file);

        let data = serde_json::json!({
            "playlist_url": self.playlist_url,
            "crawl_stats": self.stats,
            "videos": self.videos,
        });

        serde_json::to_writer_pretty(&mut writer, &data)?;
        Ok(())
    }

    fn save_txt(&self, filename: &str) -> Result<(), Box<dyn std::error::Error>> {
        let file = File::create(filename)?;
        let mut writer = BufWriter::new(file);

        writeln!(writer, "YouTube 播放列表视频列表")?;
        writeln!(writer, "{}", "═".repeat(60))?;
        writeln!(writer)?;
        writeln!(writer, "播放列表 URL: {}", self.playlist_url)?;
        writeln!(writer, "爬取时间：{}", self.stats.start_time)?;
        writeln!(writer, "视频总数：{}", self.stats.total_videos)?;
        writeln!(writer, "唯一频道数：{}", self.stats.unique_channels)?;
        writeln!(writer, "爬取耗时：{:.2}秒\n", self.stats.crawl_time_secs)?;
        writeln!(writer, "{}", "═".repeat(60))?;
        writeln!(writer)?;

        for (i, video) in self.videos.iter().enumerate() {
            writeln!(writer, "{}. {}", i + 1, video.title)?;
            if !video.duration.is_empty() {
                writeln!(writer, "   时长：{}", video.duration)?;
            }
            if !video.channel.is_empty() {
                writeln!(writer, "   频道：{}", video.channel)?;
            }
            if !video.url.is_empty() {
                writeln!(writer, "   链接：{}", video.url)?;
            }
            writeln!(writer)?;
        }

        Ok(())
    }

    fn save_csv(&self, filename: &str) -> Result<(), Box<dyn std::error::Error>> {
        let file = File::create(filename)?;
        let mut writer = BufWriter::new(file);

        // 写入表头
        writeln!(
            writer,
            "index,title,duration,channel,url,thumbnail,views,published"
        )?;

        // 写入数据
        for (i, video) in self.videos.iter().enumerate() {
            writeln!(
                writer,
                "{},{},{},{},{},{},{},{}",
                i + 1,
                escape_csv(&video.title),
                escape_csv(&video.duration),
                escape_csv(&video.channel),
                escape_csv(&video.url),
                escape_csv(&video.thumbnail),
                escape_csv(&video.views),
                escape_csv(&video.published)
            )?;
        }

        Ok(())
    }
}

/// CSV 转义
fn escape_csv(value: &str) -> String {
    if value.is_empty() {
        return String::new();
    }
    if value.contains(',') || value.contains('"') || value.contains('\n') {
        return format!("\"{}\"", value.replace('"', "\"\""));
    }
    value.to_string()
}

// 工具函数

/// 将时长字符串转换为秒
pub fn parse_duration_to_seconds(duration: &str) -> u32 {
    if duration.is_empty() {
        return 0;
    }

    let parts: Vec<&str> = duration.split(':').collect();
    let mut seconds = 0;

    match parts.len() {
        1 => {
            seconds = parts[0].parse().unwrap_or(0);
        }
        2 => {
            let minutes: u32 = parts[0].parse().unwrap_or(0);
            let secs: u32 = parts[1].parse().unwrap_or(0);
            seconds = minutes * 60 + secs;
        }
        3 => {
            let hours: u32 = parts[0].parse().unwrap_or(0);
            let minutes: u32 = parts[1].parse().unwrap_or(0);
            let secs: u32 = parts[2].parse().unwrap_or(0);
            seconds = hours * 3600 + minutes * 60 + secs;
        }
        _ => {}
    }

    seconds
}

/// 将秒转换为时长字符串
pub fn format_seconds_to_duration(seconds: u32) -> String {
    if seconds < 60 {
        format!("{}秒", seconds)
    } else if seconds < 3600 {
        let minutes = seconds / 60;
        let secs = seconds % 60;
        format!("{}分{}秒", minutes, secs)
    } else {
        let hours = seconds / 3600;
        let minutes = (seconds % 3600) / 60;
        let secs = seconds % 60;
        format!("{}小时{}分{}秒", hours, minutes, secs)
    }
}

/// 从 URL 提取视频 ID
pub fn extract_video_id(url: &str) -> Option<String> {
    let patterns = [
        r"v=([a-zA-Z0-9_-]+)",
        r"youtu\.be/([a-zA-Z0-9_-]+)",
        r"embed/([a-zA-Z0-9_-]+)",
    ];

    for pattern in patterns {
        if let Some(captures) = regex::Regex::new(pattern)
            .ok()
            .and_then(|re| re.captures(url))
        {
            if let Some(m) = captures.get(1) {
                return Some(m.as_str().to_string());
            }
        }
    }

    None
}

/// 构建 YouTube URL
pub fn build_youtube_url(video_id: &str, playlist_id: Option<&str>, index: Option<u32>) -> String {
    let mut base = format!("https://www.youtube.com/watch?v={}", video_id);

    if let Some(pid) = playlist_id {
        base.push_str(&format!("&list={}", pid));
    }
    if let Some(idx) = index {
        base.push_str(&format!("&index={}", idx));
    }

    base
}
