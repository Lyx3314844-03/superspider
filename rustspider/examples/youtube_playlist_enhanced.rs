//! Rust YouTube 播放列表爬虫 - 增强版
//! 使用统一的爬虫基类，支持多种输出格式
//!
//! 目标播放列表：https://www.youtube.com/watch?v=tr5yZ2TzXaY&list=PLRuPQZBVD6vV89UKIzUwZFUhDx9DjXLxc

use rustspider::enhanced::*;
use std::error::Error;
use std::fs;
use std::time::Duration;

fn main() -> Result<(), Box<dyn Error>> {
    let playlist_url =
        "https://www.youtube.com/watch?v=tr5yZ2TzXaY&list=PLRuPQZBVD6vV89UKIzUwZFUhDx9DjXLxc";

    println!("\n{}", "╔".repeat(30));
    println!(
        "{} Rust/rustspider - YouTube 爬虫 {}",
        "║".repeat(10),
        "║".repeat(10)
    );
    println!("{}", "╚".repeat(30));
    println!("\n📺 播放列表：{}\n", playlist_url);

    // 创建爬虫
    let mut spider = YouTubePlaylistSpider::new(playlist_url);

    // 启动爬虫
    match spider.start() {
        Ok(videos) => {
            if !videos.is_empty() {
                println!("\n✅ 爬取完成!");

                // 保存结果
                spider.save_results()?;
            } else {
                println!("\n⚠️  未找到视频");
            }
        }
        Err(e) => {
            println!("\n❌ 爬取失败：{}", e);
        }
    }

    Ok(())
}

/// YouTube 播放列表爬虫
pub struct YouTubePlaylistSpider {
    base: YouTubeSpiderBase,
    html: String,
}

impl YouTubePlaylistSpider {
    pub fn new(playlist_url: impl Into<String>) -> Self {
        let mut base = YouTubeSpiderBase::new(playlist_url);
        base.platform = "Rust/rustspider".to_string();

        Self {
            base,
            html: String::new(),
        }
    }

    /// 启动爬虫
    pub fn start(&mut self) -> Result<&Vec<VideoItem>, Box<dyn Error>> {
        self.before_start();

        if let Err(e) = self.initialize() {
            self.on_error(e.as_ref());
            return Ok(&self.base.videos);
        }

        if let Err(e) = self.navigate() {
            self.on_error(e.as_ref());
            return Ok(&self.base.videos);
        }

        if let Err(e) = self.wait_and_scroll() {
            self.on_error(e.as_ref());
            return Ok(&self.base.videos);
        }

        if let Err(e) = self.extract_content() {
            self.on_error(e.as_ref());
            return Ok(&self.base.videos);
        }

        if let Err(e) = self.parse_videos() {
            self.on_error(e.as_ref());
            return Ok(&self.base.videos);
        }

        self.after_extract();
        self.calculate_stats();
        self.print_results();

        Ok(&self.base.videos)
    }

    fn before_start(&mut self) {
        self.base.stats.start_time = chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
        self.print_header();
    }

    fn print_header(&self) {
        println!("\n{}", "╔".repeat(30));
        println!(
            "{} {} - YouTube 爬虫 {}",
            "║".repeat(10),
            self.base.platform,
            "║".repeat(10)
        );
        println!("{}", "╚".repeat(30));
        println!("\n📺 播放列表：{}\n", self.base.playlist_url);
    }

    fn initialize(&mut self) -> Result<(), Box<dyn Error>> {
        println!("🚀 启动浏览器 (Playwright/Fantoccini)...");
        // 这里可以添加浏览器初始化代码
        println!("   ✓ 浏览器已启动（模拟）");
        Ok(())
    }

    fn navigate(&mut self) -> Result<(), Box<dyn Error>> {
        println!("🌐 正在加载播放列表页面...");
        // 这里可以添加导航代码
        println!("   ✓ 页面已加载（模拟）");
        Ok(())
    }

    fn wait_and_scroll(&mut self) -> Result<(), Box<dyn Error>> {
        println!("📜 滚动加载所有视频...");
        // 这里可以添加滚动代码
        std::thread::sleep(Duration::from_secs(2));
        println!("   ✓ 滚动完成");
        Ok(())
    }

    fn extract_content(&mut self) -> Result<(), Box<dyn Error>> {
        println!("📄 获取页面内容...");

        // 模拟 HTML 内容（实际应该从浏览器获取）
        self.html = self.fetch_html()?;

        // 保存 HTML 用于调试
        fs::write("youtube_playlist_source.html", &self.html)?;
        println!("   ✓ HTML 已保存到：youtube_playlist_source.html");

        Ok(())
    }

    fn parse_videos(&mut self) -> Result<(), Box<dyn Error>> {
        println!("🔍 解析视频信息...");

        // 方法 1: 正则解析
        self.base.videos = self.parse_with_regex()?;

        // 方法 2: 如果正则失败，尝试从 JSON 解析
        if self.base.videos.is_empty() {
            println!("   尝试从 JSON 数据解析...");
            self.base.videos = self.parse_from_json()?;
        }

        println!("   ✓ 共解析 {} 个视频", self.base.videos.len());
        Ok(())
    }

    fn parse_with_regex(&self) -> Result<Vec<VideoItem>, Box<dyn Error>> {
        let mut videos = Vec::new();
        let mut seen_titles = std::collections::HashSet::new();

        // 使用正则表达式解析
        let re = regex::Regex::new(
            r#"<ytd-playlist-panel-video-renderer[^>]*>.*?</ytd-playlist-panel-video-renderer>"#,
        )?;
        let title_re = regex::Regex::new(r#"id="video-title"[^>]*>([^<]+)</span>"#)?;
        let url_re = regex::Regex::new(r#"href="([^"]*watch\?v=[^"]*)""#)?;
        let channel_re = regex::Regex::new(r#"id="byline"[^>]*>([^<]+)</span>"#)?;

        for cap in re.captures_iter(&self.html) {
            let video_elem = cap.get(0).unwrap().as_str();

            let mut video = VideoItem::new();

            // 提取标题
            if let Some(title_match) = title_re.captures(video_elem) {
                video.title = title_match.get(1).unwrap().as_str().trim().to_string();
            }

            // 提取 URL
            if let Some(url_match) = url_re.captures(video_elem) {
                video.url = url_match.get(1).unwrap().as_str().replace("&amp;", "&");
            }

            // 提取频道
            if let Some(channel_match) = channel_re.captures(video_elem) {
                video.channel = channel_match.get(1).unwrap().as_str().trim().to_string();
            }

            // 跳过重复或空标题
            if video.title.is_empty() || seen_titles.contains(&video.title) {
                continue;
            }
            seen_titles.insert(video.title.clone());

            video.index = (videos.len() + 1) as u32;
            videos.push(video);
        }

        println!("   找到 {} 个视频元素", videos.len());
        Ok(videos)
    }

    fn parse_from_json(&self) -> Result<Vec<VideoItem>, Box<dyn Error>> {
        let mut videos = Vec::new();

        // 查找 ytInitialData
        if let Some(json_match) =
            regex::Regex::new(r#"var ytInitialData\s*=\s*(\{.+?\});"#)?.captures(&self.html)
        {
            let json_str = json_match.get(1).unwrap().as_str();

            if let Ok(data) = serde_json::from_str::<serde_json::Value>(json_str) {
                self.extract_from_json_contents(&data, &mut videos);
            }
        }

        Ok(videos)
    }

    fn extract_from_json_contents(&self, _data: &serde_json::Value, _videos: &mut Vec<VideoItem>) {
        // 简化的 JSON 解析
        // 实际实现需要递归遍历 JSON 结构
    }

    fn after_extract(&mut self) {
        // 实际实现应该记录结束时间
    }

    fn calculate_stats(&mut self) {
        self.base.stats.total_videos = self.base.videos.len();

        let mut channels = std::collections::HashSet::new();
        for video in &self.base.videos {
            if !video.channel.is_empty() {
                channels.insert(&video.channel);
            }
        }
        self.base.stats.unique_channels = channels.len();
    }

    fn print_results(&self) {
        println!("\n{}", "═".repeat(60));
        println!("{:>20}爬取结果", "");
        println!("{}", "═".repeat(60));
        println!("共找到 {} 个视频", self.base.stats.total_videos);
        println!("唯一频道数：{}", self.base.stats.unique_channels);
        println!("\n前 20 个视频:");

        for (i, video) in self.base.videos.iter().take(20).enumerate() {
            println!("\n{:2}. {}", i + 1, video.title);
            if !video.duration.is_empty() {
                println!("    ⏱️  时长：{}", video.duration);
            }
            if !video.channel.is_empty() {
                println!("    👤  频道：{}", video.channel);
            }
        }

        if self.base.videos.len() > 20 {
            println!("\n... 还有 {} 个视频", self.base.videos.len() - 20);
        }
    }

    fn on_error(&self, error: &dyn Error) {
        println!("\n❌ 爬取失败：{}", error);
    }

    /// 保存结果
    pub fn save_results(&self) -> Result<(), Box<dyn Error>> {
        println!("\n💾 导出结果...");

        // 保存为 JSON
        self.base.save_to_file(None, "json")?;

        // 保存为 TXT
        self.base.save_to_file(None, "txt")?;

        // 保存为 CSV
        self.base.save_to_file(None, "csv")?;

        Ok(())
    }

    /// 获取 HTML（模拟）
    fn fetch_html(&self) -> Result<String, Box<dyn Error>> {
        // 实际实现应该从浏览器获取 HTML
        // 这里返回空字符串用于演示
        Ok(String::new())
    }
}
