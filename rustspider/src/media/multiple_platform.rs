use reqwest::blocking::Client;
use std::fs;
use std::io::{self, Write};
use std::path::Path;
use std::process::Command;

pub struct MultiPlatformDownloader {
    output_dir: String,
    client: Client,
}

impl MultiPlatformDownloader {
    pub fn new(output_dir: &str) -> Self {
        let dir = if output_dir.is_empty() { "downloads" } else { output_dir };
        fs::create_dir_all(dir).ok();
        
        Self {
            output_dir: dir.to_string(),
            client: Client::builder()
                .timeout(std::time::Duration::from_secs(60))
                .build()
                .unwrap_or_default(),
        }
    }
    
    pub fn detect_platform(&self, url: &str) -> &'static str {
        let lower = url.to_lowercase();
        if lower.contains("youtube.com") || lower.contains("youtu.be") { "youtube" }
        else if lower.contains("tiktok.com") { "tiktok" }
        else if lower.contains("instagram.com") { "instagram" }
        else if lower.contains("twitter.com") || lower.contains("x.com") { "twitter" }
        else if lower.contains("bilibili.com") || lower.contains("b23.tv") { "bilibili" }
        else { "generic" }
    }
    
    pub fn download(&self, url: &str, quality: &str) -> Result<String, String> {
        let platform = self.detect_platform(url);
        match platform {
            "youtube" => self.download_youtube(url, quality),
            "tiktok" => self.download_tiktok(url, quality),
            "bilibili" => self.download_bilibili(url, quality),
            _ => self.download_generic(url),
        }
    }
    
    fn download_youtube(&self, url: &str, _quality: &str) -> Result<String, String> {
        // Try yt-dlp first
        let output = Command::new("yt-dlp")
            .args(&["-f", "best", "-o", &format!("{}/%(title)s_%(id)s.%(ext)s", self.output_dir), url])
            .output();
        
        if let Ok(result) = output {
            if result.status.success() {
                return Ok("Downloaded via yt-dlp".to_string());
            }
        }
        
        // Fallback: extract video info
        let video_id = self.extract_youtube_id(url);
        match video_id {
            Some(id) => Ok(format!("Video ID: {}", id)),
            None => Err("Invalid YouTube URL".to_string()),
        }
    }
    
    fn extract_youtube_id(&self, url: &str) -> Option<String> {
        let patterns = [
            r"(?:youtube.com/watch\?v=|youtu.be/|youtube.com/embed/)([a-zA-Z0-9_-]{11})",
            r"youtube.com/shorts/([a-zA-Z0-9_-]{11})",
        ];
        for pattern in &patterns {
            if let Ok(re) = regex::Regex::new(pattern) {
                if let Some(caps) = re.captures(url) {
                    return Some(caps.get(1).unwrap().as_str().to_string());
                }
            }
        }
        None
    }
    
    fn download_tiktok(&self, url: &str, _quality: &str) -> Result<String, String> {
        // Get page HTML
        let resp = self.client.get(url)
            .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            .send()
            .map_err(|e| e.to_string())?;
        
        let body = resp.text().map_err(|e| e.to_string())?;
        
        // Extract video ID
        let video_id = regex::Regex::new(r"/video/(\d+)")
            .ok()
            .and_then(|re| re.captures(url))
            .and_then(|c| c.get(1))
            .map(|m| m.as_str())
            .unwrap_or("unknown");
        
        // Extract video URL
        let video_url = regex::Regex::new(r"\"playAddr\"\s*:\s*\"([^\"]+)\"")
            .ok()
            .and_then(|re| re.captures(&body))
            .and_then(|c| c.get(1))
            .map(|m| m.as_str().replace("\/", "/"));
        
        match video_url {
            Some(url) => {
                let filepath = format!("{}/tiktok_{}.mp4", self.output_dir, video_id);
                self.download_file(&url, &filepath)?;
                Ok(filepath)
            }
            None => Err("Could not extract video URL".to_string()),
        }
    }
    
    fn download_bilibili(&self, url: &str, _quality: &str) -> Result<String, String> {
        let bvid = regex::Regex::new(r"(?:bilibili\.com/video/|b23\.tv/)([a-zA-Z0-9]+)")
            .ok()
            .and_then(|re| re.captures(url))
            .and_then(|c| c.get(1))
            .map(|m| m.as_str());
        
        match bvid {
            Some(id) => {
                let api_url = format!("https://api.bilibili.com/x/player/pagelist?bvid={}", id);
                let resp = self.client.get(&api_url).send().map_err(|e| e.to_string())?;
                let _body = resp.text().map_err(|e| e.to_string())?;
                Ok(format!("Bilibili video: {}", id))
            }
            None => Err("Invalid Bilibili URL".to_string()),
        }
    }
    
    fn download_generic(&self, url: &str) -> Result<String, String> {
        let filename = format!("download_{}.mp4", chrono::Utc::now().timestamp());
        let filepath = format!("{}/{}", self.output_dir, filename);
        self.download_file(url, &filepath)
    }
    
    fn download_file(&self, url: &str, filepath: &str) -> Result<String, String> {
        let mut resp = self.client.get(url)
            .send()
            .map_err(|e| e.to_string())?;
        
        let mut file = fs::File::create(filepath).map_err(|e| e.to_string())?;
        io::copy(&mut resp, &mut file).map_err(|e| e.to_string())?;
        
        Ok(filepath.to_string())
    }
}

// Music downloader for Rust
pub struct MusicDownloader {
    output_dir: String,
    client: Client,
}

impl MusicDownloader {
    pub fn new(output_dir: &str) -> Self {
        let dir = if output_dir.is_empty() { "downloads/music" } else { output_dir };
        fs::create_dir_all(dir).ok();
        
        Self {
            output_dir: dir.to_string(),
            client: Client::builder()
                .timeout(std::time::Duration::from_secs(30))
                .build()
                .unwrap_or_default(),
        }
    }
    
    pub fn search_netease(&self, query: &str, limit: usize) -> Result<Vec<String>, String> {
        let api_url = format!(
            "https://music.163.com/api/search/get?s={}&type=1&limit={}",
            query, limit
        );
        
        let resp = self.client.get(&api_url)
            .header("User-Agent", "Mozilla/5.0")
            .send()
            .map_err(|e| e.to_string())?;
        
        let body = resp.text().map_err(|e| e.to_string())?;
        Ok(vec![body])
    }
}
