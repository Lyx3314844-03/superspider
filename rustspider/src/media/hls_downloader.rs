//! HLS/DASH 视频流下载器
//! 支持 M3U8 播放列表解析、TS 分片下载、视频合并

use futures::stream::{self, StreamExt};
use regex::Regex;
use std::error::Error;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::Duration;
use url::Url;

/// 媒体分片
#[derive(Debug, Clone)]
pub struct MediaSegment {
    pub url: String,
    pub duration: f64,
    pub title: Option<String>,
    pub sequence: u64,
}

/// 媒体播放列表
#[derive(Debug)]
pub struct MediaPlaylist {
    pub target_duration: f64,
    pub media_sequence: u64,
    pub segments: Vec<MediaSegment>,
    pub endlist: bool,
    pub total_duration: f64,
}

/// HLS 下载器
pub struct HlsDownloader {
    client: reqwest::Client,
    output_dir: PathBuf,
    max_workers: usize,
    timeout: Duration,
}

impl HlsDownloader {
    /// 创建 HLS 下载器
    pub fn new(output_dir: &str, max_workers: usize) -> Result<Self, Box<dyn Error>> {
        let output_path = PathBuf::from(output_dir);
        fs::create_dir_all(&output_path)?;

        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(30))
            .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            .build()?;

        Ok(Self {
            client,
            output_dir: output_path,
            max_workers,
            timeout: Duration::from_secs(30),
        })
    }

    /// 下载 HLS 视频
    pub async fn download(
        &self,
        m3u8_url: &str,
        output_name: &str,
    ) -> Result<bool, Box<dyn Error>> {
        println!("开始下载 HLS: {}", m3u8_url);

        // 1. 下载播放列表
        let playlist_content = self.fetch_m3u8(m3u8_url).await?;

        // 2. 解析播放列表
        let base_url = Self::get_base_url(m3u8_url);
        let playlist = self.parse_media_playlist(&playlist_content, &base_url)?;

        println!(
            "解析到 {} 个分片，总时长 {:.1}秒",
            playlist.segments.len(),
            playlist.total_duration
        );

        // 3. 下载分片
        let temp_dir = self.output_dir.join(format!("{}_temp", output_name));
        fs::create_dir_all(&temp_dir)?;

        let success = self
            .download_segments(&playlist.segments, &temp_dir)
            .await?;

        if success {
            // 4. 合并分片
            let output_file = self.output_dir.join(format!("{}.ts", output_name));
            self.merge_segments(&playlist.segments, &temp_dir, &output_file)?;

            // 5. 清理临时文件
            let _ = fs::remove_dir_all(&temp_dir);

            println!("下载完成：{}", output_file.display());
            return Ok(true);
        }

        Ok(false)
    }

    /// 获取 M3U8 内容
    async fn fetch_m3u8(&self, url: &str) -> Result<String, Box<dyn Error>> {
        let resp = self.client.get(url).send().await?;
        let text = resp.text().await?;
        Ok(text)
    }

    /// 解析媒体播放列表
    fn parse_media_playlist(
        &self,
        content: &str,
        base_url: &str,
    ) -> Result<MediaPlaylist, Box<dyn Error>> {
        let mut playlist = MediaPlaylist {
            target_duration: 0.0,
            media_sequence: 0,
            segments: Vec::new(),
            endlist: false,
            total_duration: 0.0,
        };

        let mut current_segment: Option<MediaSegment> = None;
        let mut sequence = 0u64;

        for line in content.lines() {
            let line = line.trim();

            if line.starts_with("#EXT-X-TARGETDURATION:") {
                if let Ok(val) = line
                    .strip_prefix("#EXT-X-TARGETDURATION:")
                    .unwrap_or("")
                    .parse()
                {
                    playlist.target_duration = val;
                }
            } else if line.starts_with("#EXT-X-MEDIA-SEQUENCE:") {
                if let Ok(val) = line
                    .strip_prefix("#EXT-X-MEDIA-SEQUENCE:")
                    .unwrap_or("")
                    .parse()
                {
                    playlist.media_sequence = val;
                }
            } else if line.starts_with("#EXT-X-ENDLIST") {
                playlist.endlist = true;
            } else if line.starts_with("#EXTINF:") {
                // 解析分片信息
                if let Some(caps) = Regex::new(r"#EXTINF:([\d.]+),\s*(.*)")?.captures(line) {
                    let duration = caps
                        .get(1)
                        .and_then(|m| m.as_str().parse().ok())
                        .unwrap_or(0.0);
                    let title = caps.get(2).map(|m| m.as_str().to_string());

                    current_segment = Some(MediaSegment {
                        url: String::new(),
                        duration,
                        title,
                        sequence,
                    });
                    sequence += 1;
                }
            } else if !line.is_empty() && !line.starts_with('#') {
                // 分片 URL
                if let Some(mut seg) = current_segment.take() {
                    seg.url = Self::resolve_url(line, base_url);
                    playlist.total_duration += seg.duration;
                    playlist.segments.push(seg);
                }
            }
        }

        Ok(playlist)
    }

    /// 下载所有分片
    async fn download_segments(
        &self,
        segments: &[MediaSegment],
        output_dir: &Path,
    ) -> Result<bool, Box<dyn Error>> {
        let success_count = stream::iter(segments.iter().cloned())
            .map(|segment| {
                let client = self.client.clone();
                let output_dir = output_dir.to_path_buf();
                async move {
                    Self::download_segment(client, &segment, &output_dir)
                        .await
                        .unwrap_or(false)
                }
            })
            .buffer_unordered(self.max_workers)
            .filter(|success| futures::future::ready(*success))
            .count()
            .await;

        println!(
            "分片下载完成：成功 {}/{}, 成功率 {:.1}%",
            success_count,
            segments.len(),
            success_count as f64 / segments.len() as f64 * 100.0
        );

        Ok(success_count > segments.len() * 9 / 10)
    }

    /// 下载单个分片
    async fn download_segment(
        client: reqwest::Client,
        segment: &MediaSegment,
        output_dir: &Path,
    ) -> Result<bool, Box<dyn Error>> {
        let filename = output_dir.join(format!("{:06}.ts", segment.sequence));

        for attempt in 0..3 {
            match client.get(&segment.url).send().await {
                Ok(resp) => {
                    if let Ok(bytes) = resp.bytes().await {
                        let mut file = fs::File::create(&filename)?;
                        file.write_all(&bytes)?;
                        return Ok(true);
                    }
                }
                Err(e) => {
                    eprintln!("分片下载失败 (尝试 {}/3): {}", attempt + 1, e);
                    tokio::time::sleep(Duration::from_secs(2u64.pow(attempt))).await;
                }
            }
        }

        Err("分片下载失败".into())
    }

    /// 合并分片
    fn merge_segments(
        &self,
        segments: &[MediaSegment],
        temp_dir: &Path,
        output_file: &Path,
    ) -> Result<(), Box<dyn Error>> {
        println!("合并 {} 个分片...", segments.len());

        let mut output = fs::File::create(output_file)?;

        for segment in segments {
            let filename = temp_dir.join(format!("{:06}.ts", segment.sequence));
            if filename.exists() {
                let content = fs::read(&filename)?;
                output.write_all(&content)?;
            }
        }

        println!("合并完成：{}", output_file.display());
        Ok(())
    }

    fn get_base_url(url: &str) -> String {
        if let Ok(parsed) = Url::parse(url) {
            if let Some(base) = parsed.path().rsplit_once('/') {
                return format!(
                    "{}://{}{}",
                    parsed.scheme(),
                    parsed.host_str().unwrap_or(""),
                    base.0
                );
            }
        }
        String::new()
    }

    fn resolve_url(url: &str, base_url: &str) -> String {
        if url.starts_with("http://") || url.starts_with("https://") {
            return url.to_string();
        } else if let Ok(base) = Url::parse(base_url) {
            if let Ok(resolved) = base.join(url) {
                return resolved.to_string();
            }
        }
        url.to_string()
    }
}

/// DASH 下载器
pub struct DashDownloader {
    client: reqwest::Client,
    output_dir: PathBuf,
}

impl DashDownloader {
    /// 创建 DASH 下载器
    pub fn new(output_dir: &str) -> Result<Self, Box<dyn Error>> {
        let output_path = PathBuf::from(output_dir);
        fs::create_dir_all(&output_path)?;

        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(30))
            .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            .build()?;

        Ok(Self {
            client,
            output_dir: output_path,
        })
    }

    /// 下载 DASH 视频
    pub async fn download(&self, mpd_url: &str, output_name: &str) -> Result<bool, Box<dyn Error>> {
        println!("开始下载 DASH: {}", mpd_url);

        // 1. 下载 MPD
        let mpd_content = self.fetch_mpd(mpd_url).await?;

        // 2. 解析 MPD（简化实现）
        let base_url = HlsDownloader::get_base_url(mpd_url);

        // 3. 提取视频分片 URLs
        let video_urls = self.extract_video_urls(&mpd_content, &base_url)?;

        if video_urls.is_empty() {
            println!("未找到视频分片");
            return Ok(false);
        }

        println!("找到 {} 个视频分片", video_urls.len());

        // 4. 下载分片
        let temp_dir = self.output_dir.join(format!("{}_temp", output_name));
        fs::create_dir_all(&temp_dir)?;

        let success = self.download_dash_segments(&video_urls, &temp_dir).await?;

        if success {
            println!("DASH 下载完成，需要使用 ffmpeg 合并");
            return Ok(true);
        }

        Ok(false)
    }

    async fn fetch_mpd(&self, url: &str) -> Result<String, Box<dyn Error>> {
        let resp = self.client.get(url).send().await?;
        Ok(resp.text().await?)
    }

    fn extract_video_urls(
        &self,
        mpd_content: &str,
        base_url: &str,
    ) -> Result<Vec<String>, Box<dyn Error>> {
        let mut urls = Vec::new();

        // 简化实现：提取 BaseURL 和 SegmentURL
        let baseurl_re = Regex::new(r"<BaseURL>([^<]+)</BaseURL>")?;
        let segmenturl_re = Regex::new(r#"<SegmentURL media="([^"]+)""#)?;

        let base_url_from_mpd = baseurl_re
            .captures(mpd_content)
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str());

        let final_base = base_url_from_mpd.unwrap_or(base_url);

        for caps in segmenturl_re.captures_iter(mpd_content) {
            if let Some(media) = caps.get(1) {
                urls.push(HlsDownloader::resolve_url(media.as_str(), final_base));
            }
        }

        Ok(urls)
    }

    async fn download_dash_segments(
        &self,
        urls: &[String],
        output_dir: &Path,
    ) -> Result<bool, Box<dyn Error>> {
        let mut success_count = 0;

        for (i, url) in urls.iter().enumerate() {
            let filename = output_dir.join(format!("{:06}.m4s", i));

            match self.client.get(url).send().await {
                Ok(resp) => {
                    if let Ok(bytes) = resp.bytes().await {
                        let mut file = fs::File::create(&filename)?;
                        file.write_all(&bytes)?;
                        success_count += 1;
                    }
                }
                Err(e) => {
                    eprintln!("分片下载失败：{}", e);
                }
            }
        }

        println!("DASH 分片下载完成：{}/{}", success_count, urls.len());
        Ok(success_count > 0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_hls_downloader() {
        let downloader = HlsDownloader::new("test_downloads", 5).unwrap();

        // 注意：这是一个示例测试，需要有效的 M3U8 URL
        // let success = downloader.download("https://example.com/video.m3u8", "test").await;
        // assert!(success.is_ok());
    }
}
