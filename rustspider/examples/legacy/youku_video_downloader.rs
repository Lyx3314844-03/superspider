// Rust 优酷视频下载器
// 使用 rustspider 框架下载优酷视频
//
// 目标视频：https://v.youku.com/v_show/id_XNTk4Mjg1MjEzMg==.html
//
// 运行方法:
// ```bash
// cd C:\Users\Administrator\spider\rustspider
// cargo run --example youku_video_downloader
// ```

use std::error::Error;
use std::fs;
use std::io::Write;
use std::time::Duration;

/// 视频信息
#[derive(Debug, Clone, Default)]
pub struct VideoInfo {
    pub title: String,
    pub video_id: String,
    pub download_url: String,
    pub m3u8_url: String,
}

/// 优酷视频下载器
pub struct YoukuVideoDownloader {
    video_url: String,
    video_info: VideoInfo,
    output_dir: String,
}

impl YoukuVideoDownloader {
    pub fn new(video_url: impl Into<String>, output_dir: impl Into<String>) -> Self {
        Self {
            video_url: video_url.into(),
            video_info: VideoInfo::default(),
            output_dir: output_dir.into(),
        }
    }

    /// 启动下载
    pub fn start(&mut self) -> Result<(), Box<dyn Error>> {
        self.print_header();

        // 1. 创建输出目录
        self.create_output_dir()?;

        // 2. 获取视频信息
        if let Err(e) = self.get_video_info() {
            self.on_error(&e.to_string());
            return Ok(());
        }

        // 3. 解析下载链接
        if let Err(e) = self.parse_download_url() {
            self.on_error(&e.to_string());
            return Ok(());
        }

        // 4. 下载视频
        if let Err(e) = self.download_video() {
            self.on_error(&e.to_string());
            return Ok(());
        }

        Ok(())
    }

    fn print_header(&self) {
        println!("\n{}", "╔".repeat(40));
        println!(
            "{} Rust/rustspider - 优酷视频下载器 {}",
            "║".repeat(12),
            "║".repeat(12)
        );
        println!("{}", "╚".repeat(40));
        println!("\n📺 视频链接：{}\n", self.video_url);
        println!("📁 保存目录：{}\n", self.output_dir);
    }

    fn create_output_dir(&self) -> Result<(), Box<dyn Error>> {
        println!("📁 创建输出目录...");
        fs::create_dir_all(&self.output_dir)?;
        println!("   ✓ 目录已创建：{}", self.output_dir);
        Ok(())
    }

    fn get_video_info(&mut self) -> Result<(), Box<dyn Error>> {
        println!("🌐 正在获取视频信息...");

        // 创建 HTTP 客户端
        let client = reqwest::blocking::Client::builder()
            .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            .timeout(Duration::from_secs(30))
            .build()?;

        let response = client.get(&self.video_url).send()?;

        if response.status().is_success() {
            let html = response.text()?;

            // 保存 HTML
            let html_path = format!("{}/video_source.html", self.output_dir);
            fs::write(&html_path, &html)?;
            println!("   ✓ HTML 已保存到：{}", html_path);

            // 解析视频 ID
            if let Some(id) = self.extract_video_id_from_url() {
                self.video_info.video_id = id;
            }

            // 解析标题
            self.parse_title(&html);

            // 解析 m3u8 URL
            self.parse_m3u8_url(&html);

            println!("   ✓ 视频信息已获取");
            println!("      标题：{}", self.video_info.title);
        } else {
            return Err(format!("请求失败：{}", response.status()).into());
        }

        Ok(())
    }

    fn parse_title(&mut self, html: &str) {
        // 尝试多种模式
        let patterns = vec![
            r#"<title>([^<]+)</title>"#,
            r#""title"\s*:\s*"([^"]+)""#,
            r#"<h1[^>]*>([^<]+)</h1>"#,
        ];

        for pattern in &patterns {
            if let Ok(re) = regex::Regex::new(pattern) {
                if let Some(caps) = re.captures(html) {
                    if let Some(title) = caps.get(1) {
                        self.video_info.title = title.as_str().trim().to_string();
                        // 清理标题
                        self.video_info.title = self
                            .video_info
                            .title
                            .replace(" - 优酷", "")
                            .replace("- 优酷", "")
                            .replace("高清完整正版视频在线观看 - 优酷", "");
                        return;
                    }
                }
            }
        }

        // 如果无法解析，使用视频 ID
        if self.video_info.title.is_empty() {
            self.video_info.title = format!("youku_video_{}", self.video_info.video_id);
        }
    }

    fn parse_m3u8_url(&mut self, html: &str) {
        // 查找 m3u8 URL
        let patterns = vec![
            r#"(https?://[^"\s]+\.m3u8[^"\s]*)"#,
            r#"videoUrl"\s*:\s*"([^"]+)"#,
            r#"data"\s*:\s*\{[^}]*"url"\s*:\s*"([^"]+)"#,
        ];

        for pattern in &patterns {
            if let Ok(re) = regex::Regex::new(pattern) {
                if let Some(caps) = re.captures(html) {
                    if let Some(url) = caps.get(1) {
                        let url_str = url.as_str();
                        if url_str.contains("m3u8") || url_str.contains("mp4") {
                            self.video_info.m3u8_url = url_str.to_string();
                            println!("   ✓ 找到视频 URL: {}", &url_str[..url_str.len().min(80)]);
                            return;
                        }
                    }
                }
            }
        }

        println!("   ⚠️  未找到 m3u8 视频链接");
    }

    fn parse_download_url(&mut self) -> Result<(), Box<dyn Error>> {
        // 如果没有找到 m3u8，尝试使用 yt-dlp 获取
        if self.video_info.m3u8_url.is_empty() {
            println!("   尝试使用 yt-dlp 获取下载链接...");
            self.get_download_url_with_ytdlp()?;
        }

        Ok(())
    }

    fn get_download_url_with_ytdlp(&mut self) -> Result<(), Box<dyn Error>> {
        // 使用 yt-dlp 获取视频信息
        let output = std::process::Command::new("yt-dlp")
            .args(["--no-download", "-j", &self.video_url])
            .output();

        match output {
            Ok(result) => {
                if result.status.success() {
                    let json_str = String::from_utf8_lossy(&result.stdout);
                    if let Ok(data) = serde_json::from_str::<serde_json::Value>(&json_str) {
                        // 提取标题
                        if let Some(title) = data.get("title").and_then(|v| v.as_str()) {
                            self.video_info.title = title.to_string();
                        }

                        // 提取 URL
                        if let Some(url) = data.get("url").and_then(|v| v.as_str()) {
                            self.video_info.download_url = url.to_string();
                            println!("   ✓ 找到下载链接：{}", url);
                        }

                        // 提取 m3u8
                        if let Some(formats) = data.get("formats").and_then(|v| v.as_array()) {
                            for format in formats {
                                if let Some(ext) = format.get("ext").and_then(|v| v.as_str()) {
                                    if ext == "mp4" {
                                        if let Some(url) =
                                            format.get("url").and_then(|v| v.as_str())
                                        {
                                            self.video_info.download_url = url.to_string();
                                            println!("   ✓ 找到 MP4 链接：{}", url);
                                            break;
                                        }
                                    }
                                }
                            }
                        }
                    }
                } else {
                    println!("   ⚠️  yt-dlp 执行失败");
                }
            }
            Err(e) => {
                println!("   ⚠️  yt-dlp 未安装或不可用：{}", e);
                println!("   提示：请安装 yt-dlp: pip install yt-dlp");
            }
        }

        Ok(())
    }

    fn download_video(&mut self) -> Result<(), Box<dyn Error>> {
        println!("\n📥 开始下载视频...");

        // 优先使用 yt-dlp 下载
        if self.try_download_with_ytdlp()? {
            return Ok(());
        }

        // 否则使用 HTTP 下载
        self.download_with_http()
    }

    fn try_download_with_ytdlp(&mut self) -> Result<bool, Box<dyn Error>> {
        println!("   尝试使用 yt-dlp 下载...");

        let output_filename = format!(
            "{}/{}",
            self.output_dir,
            self.video_info.title.replace("/", "_").replace("\\", "_")
        );

        let output = std::process::Command::new("yt-dlp")
            .args([
                "-o",
                &format!("{}.%(ext)s", output_filename),
                "--no-playlist",
                &self.video_url,
            ])
            .output();

        match output {
            Ok(result) => {
                if result.status.success() {
                    let stdout = String::from_utf8_lossy(&result.stdout);

                    println!("   ✓ 下载完成!");
                    println!("   {}", stdout);

                    // 查找下载的文件
                    if let Some(file) = self.find_downloaded_file() {
                        println!("   ✓ 视频已保存到：{}", file);
                        return Ok(true);
                    }
                } else {
                    println!(
                        "   ⚠️  yt-dlp 下载失败：{}",
                        String::from_utf8_lossy(&result.stderr)
                    );
                }
            }
            Err(e) => {
                println!("   ⚠️  yt-dlp 不可用：{}", e);
            }
        }

        Ok(false)
    }

    fn download_with_http(&mut self) -> Result<(), Box<dyn Error>> {
        println!("   使用 HTTP 下载...");

        if self.video_info.download_url.is_empty() {
            return Err("未找到可下载的 URL".into());
        }

        let client = reqwest::blocking::Client::builder()
            .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            .timeout(Duration::from_secs(3600))
            .build()?;

        let response = client.get(&self.video_info.download_url).send()?;

        if !response.status().is_success() {
            return Err(format!("下载失败：{}", response.status()).into());
        }

        // 获取文件大小
        let total_size = response.content_length().unwrap_or(0);
        println!("   文件大小：{} MB", total_size / 1024 / 1024);

        // 下载
        let video_path = format!(
            "{}/{}.mp4",
            self.output_dir,
            self.video_info.title.replace("/", "_").replace("\\", "_")
        );
        let mut file = fs::File::create(&video_path)?;

        let bytes = response.bytes()?;
        file.write_all(&bytes)?;

        println!("   ✓ 下载完成：{}", video_path);

        Ok(())
    }

    fn find_downloaded_file(&self) -> Option<String> {
        // 查找目录中最新的视频文件
        if let Ok(entries) = fs::read_dir(&self.output_dir) {
            let mut latest_file = None;
            let mut latest_time = None;

            for entry in entries.flatten() {
                if let Ok(metadata) = entry.metadata() {
                    if metadata.is_file() {
                        let path = entry.path();
                        if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
                            if ["mp4", "flv", "webm", "mkv"].contains(&ext.to_lowercase().as_str())
                            {
                                if let Ok(modified) = metadata.modified() {
                                    if latest_time.is_none() || Some(modified) > latest_time {
                                        latest_time = Some(modified);
                                        latest_file = Some(path.display().to_string());
                                    }
                                }
                            }
                        }
                    }
                }
            }

            return latest_file;
        }
        None
    }

    fn extract_video_id_from_url(&self) -> Option<String> {
        if let Ok(re) = regex::Regex::new(r"id_([a-zA-Z0-9=]+)") {
            if let Some(caps) = re.captures(&self.video_url) {
                if let Some(id) = caps.get(1) {
                    return Some(id.as_str().to_string());
                }
            }
        }
        None
    }

    fn on_error(&self, error: &str) {
        println!("\n❌ 下载失败：{}", error);
    }
}

fn main() -> Result<(), Box<dyn Error>> {
    // 优酷视频链接
    let video_url = "https://v.youku.com/v_show/id_XNTk4Mjg1MjEzMg==.html";

    // 输出目录
    let output_dir = "C:/Users/Administrator/spider/rustspider/downloads";

    // 创建下载器
    let mut downloader = YoukuVideoDownloader::new(video_url, output_dir);

    // 开始下载
    downloader.start()?;

    Ok(())
}
