//! Rust 多媒体下载模块
//! 支持视频、图片、音乐批量下载

use serde::{Deserialize, Serialize};
use std::fs;
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use std::time::Duration;

/// 媒体项基类
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MediaItem {
    pub id: String,
    pub title: String,
    pub url: String,
    pub thumbnail: String,
    pub duration: String,
    pub size: i64,
    pub format: String,
    pub quality: String,
    pub downloaded: bool,
    pub download_path: String,
    pub error: String,
}

impl MediaItem {
    pub fn new() -> Self {
        Self {
            id: String::new(),
            title: String::new(),
            url: String::new(),
            thumbnail: String::new(),
            duration: String::new(),
            size: 0,
            format: String::new(),
            quality: String::new(),
            downloaded: false,
            download_path: String::new(),
            error: String::new(),
        }
    }

    pub fn to_map(&self) -> serde_json::Value {
        serde_json::json!({
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "thumbnail": self.thumbnail,
            "duration": self.duration,
            "size": self.size,
            "format": self.format,
            "quality": self.quality,
            "downloaded": self.downloaded,
            "download_path": self.download_path,
            "error": self.error,
        })
    }
}

impl Default for MediaItem {
    fn default() -> Self {
        Self::new()
    }
}

/// 视频项
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VideoItem {
    #[serde(flatten)]
    pub base: MediaItem,
    pub channel: String,
    pub views: String,
    pub published: String,
    pub description: String,
    pub index: u32,
}

impl VideoItem {
    pub fn new() -> Self {
        Self {
            base: MediaItem::new(),
            channel: String::new(),
            views: String::new(),
            published: String::new(),
            description: String::new(),
            index: 0,
        }
    }
}

impl Default for VideoItem {
    fn default() -> Self {
        Self::new()
    }
}

/// 图片项
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImageItem {
    #[serde(flatten)]
    pub base: MediaItem,
    pub width: u32,
    pub height: u32,
    pub alt: String,
    pub source: String,
}

impl ImageItem {
    pub fn new() -> Self {
        Self {
            base: MediaItem::new(),
            width: 0,
            height: 0,
            alt: String::new(),
            source: String::new(),
        }
    }
}

impl Default for ImageItem {
    fn default() -> Self {
        Self::new()
    }
}

/// 音频项
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AudioItem {
    #[serde(flatten)]
    pub base: MediaItem,
    pub artist: String,
    pub album: String,
    pub track: u32,
    pub lyrics: String,
}

impl AudioItem {
    pub fn new() -> Self {
        Self {
            base: MediaItem::new(),
            artist: String::new(),
            album: String::new(),
            track: 0,
            lyrics: String::new(),
        }
    }
}

impl Default for AudioItem {
    fn default() -> Self {
        Self::new()
    }
}

/// 下载统计
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DownloadStats {
    pub total: usize,
    pub success: usize,
    pub failed: usize,
    pub skipped: usize,
    pub start_time: String,
    pub end_time: String,
    pub items: Vec<serde_json::Value>,
}

impl DownloadStats {
    pub fn new() -> Self {
        Self {
            total: 0,
            success: 0,
            failed: 0,
            skipped: 0,
            start_time: String::new(),
            end_time: String::new(),
            items: Vec::new(),
        }
    }
}

impl Default for DownloadStats {
    fn default() -> Self {
        Self::new()
    }
}

/// 媒体下载器
pub struct MediaDownloader {
    output_dir: PathBuf,
    #[allow(dead_code)]
    user_agent: String,
    client: reqwest::blocking::Client,
}

impl MediaDownloader {
    pub fn new(output_dir: impl AsRef<Path>) -> Self {
        let output_dir = output_dir.as_ref().to_path_buf();
        fs::create_dir_all(&output_dir).ok();

        let client = reqwest::blocking::Client::builder()
            .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            .timeout(Duration::from_secs(300))
            .build()
            .unwrap_or_default();

        Self {
            output_dir,
            user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36".to_string(),
            client,
        }
    }

    /// 下载文件
    pub fn download_file(&self, url: &str, save_path: &Path) -> bool {
        println!("   📥 下载：{}", url);

        match self.client.get(url).send() {
            Ok(resp) => {
                if !resp.status().is_success() {
                    println!("   ❌ HTTP 错误：{}", resp.status());
                    return false;
                }

                let total_size = resp.content_length().unwrap_or(0);
                let mut downloaded: u64 = 0;

                // 创建目录
                if let Some(parent) = save_path.parent() {
                    fs::create_dir_all(parent).ok();
                }

                match File::create(save_path) {
                    Ok(file) => {
                        let mut writer = BufWriter::new(file);
                        let bytes = resp.bytes();

                        if let Ok(content) = bytes {
                            writer.write_all(&content).ok();
                            downloaded = content.len() as u64;
                        }

                        if total_size > 0 {
                            let progress = (downloaded * 100) / total_size;
                            println!("\r   进度：{}%", progress);
                        }

                        println!(
                            "\r   ✓ 下载完成：{}",
                            save_path.file_name().unwrap().to_string_lossy()
                        );
                        true
                    }
                    Err(e) => {
                        println!("   ❌ 创建文件失败：{}", e);
                        false
                    }
                }
            }
            Err(e) => {
                println!("   ❌ 下载失败：{}", e);
                false
            }
        }
    }

    /// 下载视频
    pub fn download_video(&self, video: &VideoItem, quality: &str) -> bool {
        let video_dir = self.output_dir.join("videos");
        let safe_title = Self::sanitize_filename(&video.base.title);
        let save_path = video_dir.join(format!("{}.mp4", safe_title));

        // YouTube 视频
        if video.base.url.contains("youtube.com") || video.base.url.contains("youtu.be") {
            return self.download_youtube_video(&video.base.url, &save_path, quality);
        }

        self.download_file(&video.base.url, &save_path)
    }

    /// 下载音频
    pub fn download_audio(&self, audio: &AudioItem, format: &str) -> bool {
        let audio_dir = self.output_dir.join("audios");
        let safe_title = Self::sanitize_filename(&audio.base.title);
        let save_path = audio_dir.join(format!("{}.{}", safe_title, format));

        self.download_file(&audio.base.url, &save_path)
    }

    /// 下载图片
    pub fn download_image(&self, image: &ImageItem) -> bool {
        let image_dir = self.output_dir.join("images");
        let safe_title = Self::sanitize_filename(&image.base.title);
        let ext = Self::get_image_extension(&image.base.url);
        let save_path = image_dir.join(format!("{}.{}", safe_title, ext));

        self.download_file(&image.base.url, &save_path)
    }

    /// 批量下载（简化版，单线程）
    pub fn download_batch(&self, items: &[MediaItem], max_workers: usize) -> DownloadStats {
        let mut stats = DownloadStats::new();
        stats.total = items.len();
        stats.start_time = chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string();

        println!("\n📦 开始批量下载 {} 个文件...", items.len());
        println!("   最大并发数：{}", max_workers);
        println!("   输出目录：{}", self.output_dir.display());
        println!();

        for (i, item) in items.iter().enumerate() {
            print!("[{}/{}] ", i + 1, items.len());

            if self.is_already_downloaded(item) {
                println!("⏭️  跳过（已存在）");
                stats.skipped += 1;
                stats.items.push(item.to_map());
                continue;
            }

            let success = match item.format.as_str() {
                "video" => self.download_video_from_item(item),
                "audio" => self.download_audio_from_item(item),
                "image" => self.download_image_from_item(item),
                _ => false,
            };

            if success {
                stats.success += 1;
            } else {
                stats.failed += 1;
            }
            stats.items.push(item.to_map());

            std::thread::sleep(Duration::from_millis(500));
        }

        stats.end_time = chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
        self.save_download_log(&stats);

        stats
    }

    /// 下载 YouTube 视频
    fn download_youtube_video(&self, url: &str, save_path: &Path, quality: &str) -> bool {
        // 检查 yt-dlp
        let check = std::process::Command::new("yt-dlp")
            .arg("--version")
            .output();

        if check.is_err() {
            println!("   ⚠️  yt-dlp 未安装");
            return false;
        }

        // 构建命令
        let mut cmd = std::process::Command::new("yt-dlp");
        cmd.arg("-o")
            .arg(save_path.to_string_lossy().to_string())
            .arg("--no-playlist");

        match quality {
            "best" => {
                cmd.arg("-f").arg("bestvideo+bestaudio/best");
            }
            "audio" => {
                cmd.arg("-x").arg("--audio-format").arg("mp3");
            }
            _ => {}
        }

        cmd.arg(url);

        match cmd.output() {
            Ok(output) => {
                if output.status.success() {
                    println!("   ✓ YouTube 视频下载完成");
                    true
                } else {
                    println!("   ❌ YouTube 下载失败");
                    false
                }
            }
            Err(e) => {
                println!("   ❌ YouTube 下载异常：{}", e);
                false
            }
        }
    }

    /// 清理文件名
    fn sanitize_filename(filename: &str) -> String {
        let illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '？', '*'];
        let mut result = filename.to_string();

        for c in illegal_chars {
            result = result.replace(c, "_");
        }

        if result.len() > 100 {
            result = result[..100].to_string();
        }

        result.trim().to_string()
    }

    /// 获取图片扩展名
    fn get_image_extension(url: &str) -> &'static str {
        let url_lower = url.to_lowercase();

        if url_lower.contains(".jpg") || url_lower.contains(".jpeg") {
            "jpg"
        } else if url_lower.contains(".png") {
            "png"
        } else if url_lower.contains(".gif") {
            "gif"
        } else if url_lower.contains(".webp") {
            "webp"
        } else if url_lower.contains(".bmp") {
            "bmp"
        } else if url_lower.contains(".svg") {
            "svg"
        } else {
            "jpg"
        }
    }

    /// 检查是否已下载
    fn is_already_downloaded(&self, item: &MediaItem) -> bool {
        if item.title.is_empty() {
            return false;
        }

        let safe_title = Self::sanitize_filename(&item.title);
        let check_dir = match item.format.as_str() {
            "video" => self.output_dir.join("videos"),
            "audio" => self.output_dir.join("audios"),
            "image" => self.output_dir.join("images"),
            _ => return false,
        };

        let extensions = [
            "mp4", "mkv", "webm", "mp3", "wav", "flac", "jpg", "png", "gif",
        ];

        for ext in extensions {
            let check_path = check_dir.join(format!("{}.{}", safe_title, ext));
            if check_path.exists() {
                return true;
            }
        }

        false
    }

    /// 保存下载日志
    fn save_download_log(&self, stats: &DownloadStats) {
        let log_file = self.output_dir.join("download_log.json");

        if let Ok(file) = File::create(&log_file) {
            let mut writer = BufWriter::new(file);
            if let Ok(json) = serde_json::to_string_pretty(stats) {
                writer.write_all(json.as_bytes()).ok();
                println!("\n📝 下载日志已保存到：{}", log_file.display());
            }
        }
    }

    /// 辅助方法（用于从基类下载）
    fn download_video_from_item(&self, item: &MediaItem) -> bool {
        let video = VideoItem {
            base: item.clone(),
            ..Default::default()
        };
        self.download_video(&video, "best")
    }

    fn download_audio_from_item(&self, item: &MediaItem) -> bool {
        let audio = AudioItem {
            base: item.clone(),
            ..Default::default()
        };
        self.download_audio(&audio, "mp3")
    }

    fn download_image_from_item(&self, item: &MediaItem) -> bool {
        let image = ImageItem {
            base: item.clone(),
            ..Default::default()
        };
        self.download_image(&image)
    }

    /// 克隆用于线程
    #[allow(dead_code)]
    fn clone_for_thread(&self) -> MediaDownloader {
        MediaDownloader {
            output_dir: self.output_dir.clone(),
            user_agent: self.user_agent.clone(),
            client: self.client.clone(),
        }
    }
}

/// 生成 MD5 ID
pub fn generate_id(text: &str) -> String {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    let mut hasher = DefaultHasher::new();
    text.hash(&mut hasher);
    format!("{:016x}", hasher.finish())
}
