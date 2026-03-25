//! 媒体下载模块

use std::fs::File;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::collections::HashMap;
use regex::Regex;

/// 媒体下载器
pub struct MediaDownloader {
    output_dir: PathBuf,
    client: reqwest::blocking::Client,
}

impl MediaDownloader {
    /// 创建媒体下载器
    pub fn new(output_dir: &str) -> Self {
        let output_path = PathBuf::from(output_dir);
        
        // 创建目录
        let _ = std::fs::create_dir_all(output_path.join("images"));
        let _ = std::fs::create_dir_all(output_path.join("videos"));
        let _ = std::fs::create_dir_all(output_path.join("audio"));
        
        MediaDownloader {
            output_dir: output_path,
            client: reqwest::blocking::Client::builder()
                .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                .timeout(std::time::Duration::from_secs(30))
                .build()
                .unwrap_or_default(),
        }
    }
    
    /// 下载图片
    pub fn download_image(&self, url: &str, filename: Option<&str>) -> DownloadResult {
        match self._download(url, "images", filename) {
            Ok((path, size)) => DownloadResult {
                url: url.to_string(),
                path,
                size,
                success: true,
                error: None,
            },
            Err(e) => DownloadResult {
                url: url.to_string(),
                path: String::new(),
                size: 0,
                success: false,
                error: Some(e.to_string()),
            },
        }
    }
    
    /// 下载视频
    pub fn download_video(&self, url: &str, filename: Option<&str>) -> DownloadResult {
        match self._download(url, "videos", filename) {
            Ok((path, size)) => DownloadResult {
                url: url.to_string(),
                path,
                size,
                success: true,
                error: None,
            },
            Err(e) => DownloadResult {
                url: url.to_string(),
                path: String::new(),
                size: 0,
                success: false,
                error: Some(e.to_string()),
            },
        }
    }
    
    /// 下载音频
    pub fn download_audio(&self, url: &str, filename: Option<&str>) -> DownloadResult {
        match self._download(url, "audio", filename) {
            Ok((path, size)) => DownloadResult {
                url: url.to_string(),
                path,
                size,
                success: true,
                error: None,
            },
            Err(e) => DownloadResult {
                url: url.to_string(),
                path: String::new(),
                size: 0,
                success: false,
                error: Some(e.to_string()),
            },
        }
    }
    
    /// 通用下载方法
    fn _download(&self, url: &str, dir: &str, filename: Option<&str>) -> std::io::Result<(String, u64)> {
        let resp = self.client.get(url).send()
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
        
        let bytes = resp.bytes()
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
        
        // 生成文件名
        let fname = filename.unwrap_or_else(|| {
            Path::new(url).file_name()
                .and_then(|s| s.to_str())
                .unwrap_or("file")
        }).to_string();
        
        let filepath = self.output_dir.join(dir).join(fname);
        
        // 保存文件
        let mut file = File::create(&filepath)?;
        file.write_all(&bytes)?;
        
        Ok((filepath.to_string_lossy().to_string(), bytes.len() as u64))
    }
    
    /// 从 HTML 中提取图片链接
    pub fn extract_images_from_html(&self, html: &str) -> Vec<String> {
        let mut urls = Vec::new();
        
        // 匹配 img 标签
        let img_pattern = r#"<img[^>]+src=["']([^"']+)["']"#;
        if let Ok(re) = Regex::new(img_pattern) {
            for cap in re.captures_iter(html) {
                if let Some(url) = cap.get(1) {
                    urls.push(url.as_str().to_string());
                }
            }
        }
        
        // 匹配背景图片
        let bg_pattern = r#"url\(["']?([^"')\s]+)["']?\)"#;
        if let Ok(re) = Regex::new(bg_pattern) {
            for cap in re.captures_iter(html) {
                if let Some(url) = cap.get(1) {
                    let url_str = url.as_str();
                    if url_str.ends_with(".jpg") || url_str.ends_with(".jpeg") || 
                       url_str.ends_with(".png") || url_str.ends_with(".gif") || 
                       url_str.ends_with(".webp") {
                        urls.push(url_str.to_string());
                    }
                }
            }
        }
        
        // 去重
        urls.sort();
        urls.dedup();
        urls
    }
    
    /// 从 HTML 中提取所有媒体 URL
    pub fn extract_media_urls(&self, html: &str) -> MediaURLs {
        let mut urls = MediaURLs::default();
        
        // 提取图片
        let img_pattern = r"(https?://[^\s\"'><]+\.(?:jpg|jpeg|png|gif|webp|bmp))";
        if let Ok(re) = Regex::new(img_pattern) {
            for cap in re.captures_iter(html) {
                urls.images.push(cap[1].to_string());
            }
        }
        
        // 提取视频
        let video_pattern = r"(https?://[^\s\"'><]+\.(?:mp4|webm|avi|mov|flv|mkv))";
        if let Ok(re) = Regex::new(video_pattern) {
            for cap in re.captures_iter(html) {
                urls.videos.push(cap[1].to_string());
            }
        }
        
        // 提取音频
        let audio_pattern = r"(https?://[^\s\"'><]+\.(?:mp3|wav|ogg|flac|aac|m4a))";
        if let Ok(re) = Regex::new(audio_pattern) {
            for cap in re.captures_iter(html) {
                urls.audios.push(cap[1].to_string());
            }
        }
        
        // 去重
        urls.images.sort();
        urls.images.dedup();
        urls.videos.sort();
        urls.videos.dedup();
        urls.audios.sort();
        urls.audios.dedup();
        
        urls
    }
    
    /// 下载所有媒体
    pub fn download_all(&self, urls: &MediaURLs) -> DownloadStats {
        let mut stats = DownloadStats::default();
        
        // 下载图片
        for url in &urls.images {
            let result = self.download_image(url, None);
            if result.success {
                stats.images_downloaded += 1;
                stats.total_bytes += result.size;
            } else {
                stats.images_failed += 1;
            }
        }
        
        // 下载视频
        for url in &urls.videos {
            let result = self.download_video(url, None);
            if result.success {
                stats.videos_downloaded += 1;
                stats.total_bytes += result.size;
            } else {
                stats.videos_failed += 1;
            }
        }
        
        // 下载音频
        for url in &urls.audios {
            let result = self.download_audio(url, None);
            if result.success {
                stats.audios_downloaded += 1;
                stats.total_bytes += result.size;
            } else {
                stats.audios_failed += 1;
            }
        }
        
        stats
    }
}

/// 下载结果
#[derive(Debug, Clone)]
pub struct DownloadResult {
    pub url: String,
    pub path: String,
    pub size: u64,
    pub success: bool,
    pub error: Option<String>,
}

/// 媒体 URL 集合
#[derive(Debug, Clone, Default)]
pub struct MediaURLs {
    pub images: Vec<String>,
    pub videos: Vec<String>,
    pub audios: Vec<String>,
}

/// 下载统计
#[derive(Debug, Clone, Default)]
pub struct DownloadStats {
    pub images_downloaded: u32,
    pub images_failed: u32,
    pub videos_downloaded: u32,
    pub videos_failed: u32,
    pub audios_downloaded: u32,
    pub audios_failed: u32,
    pub total_bytes: u64,
}

impl DownloadStats {
    /// 转换为 JSON 字符串
    pub fn to_json(&self) -> String {
        format!(
            r#"{{"images_downloaded":{},"images_failed":{},"videos_downloaded":{},"videos_failed":{},"audios_downloaded":{},"audios_failed":{},"total_bytes":{}}}"#,
            self.images_downloaded,
            self.images_failed,
            self.videos_downloaded,
            self.videos_failed,
            self.audios_downloaded,
            self.audios_failed,
            self.total_bytes,
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_extract_images() {
        let downloader = MediaDownloader::new("/tmp");
        let html = r#"<img src="https://example.com/image.jpg"><img src="https://example.com/image2.png">"#;
        
        let images = downloader.extract_images_from_html(html);
        assert_eq!(images.len(), 2);
    }
    
    #[test]
    fn test_extract_media_urls() {
        let downloader = MediaDownloader::new("/tmp");
        let html = r#"
            <img src="https://example.com/image.jpg">
            <video src="https://example.com/video.mp4"></video>
            <audio src="https://example.com/audio.mp3"></audio>
        "#;
        
        let urls = downloader.extract_media_urls(html);
        assert_eq!(urls.images.len(), 1);
        assert_eq!(urls.videos.len(), 1);
        assert_eq!(urls.audios.len(), 1);
    }
}
