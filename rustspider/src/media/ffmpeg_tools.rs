//! FFmpeg 工具集
//! 支持视频转换、合并、压缩、截图、音频提取等

use std::error::Error;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::io::{BufRead, BufReader};

/// 视频信息
#[derive(Debug)]
pub struct VideoInfo {
    pub filename: String,
    pub duration: f64,
    pub size: u64,
    pub format: String,
    pub video_codec: String,
    pub audio_codec: String,
    pub width: i32,
    pub height: i32,
    pub bitrate: i64,
    pub frame_rate: f64,
    pub has_video: bool,
    pub has_audio: bool,
}

/// FFmpeg 执行器
pub struct FFmpegExecutor {
    ffmpeg_path: PathBuf,
    ffprobe_path: PathBuf,
}

impl FFmpegExecutor {
    /// 创建 FFmpeg 执行器
    pub fn new() -> Result<Self, Box<dyn Error>> {
        let ffmpeg_path = Self::find_ffmpeg().ok_or("未找到 ffmpeg")?;
        let ffprobe_path = Self::find_ffprobe().unwrap_or_else(|| ffmpeg_path.clone());

        Ok(Self {
            ffmpeg_path,
            ffprobe_path,
        })
    }

    /// 创建 FFmpeg 执行器（自定义路径）
    pub fn with_paths(ffmpeg_path: &str, ffprobe_path: &str) -> Self {
        Self {
            ffmpeg_path: PathBuf::from(ffmpeg_path),
            ffprobe_path: PathBuf::from(ffprobe_path),
        }
    }

    fn find_ffmpeg() -> Option<PathBuf> {
        // 尝试 PATH
        if let Ok(path) = which::which("ffmpeg") {
            return Some(path);
        }

        // 尝试常见路径
        let common_paths = [
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Users\Administrator\ffmpeg\bin\ffmpeg.exe",
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
        ];

        for path in &common_paths {
            let p = PathBuf::from(path);
            if p.exists() {
                return Some(p);
            }
        }

        None
    }

    fn find_ffprobe() -> Option<PathBuf> {
        if let Ok(path) = which::which("ffprobe") {
            return Some(path);
        }

        if let Some(ffmpeg) = Self::find_ffmpeg() {
            let ffprobe = ffmpeg.parent()?.join("ffprobe");
            if ffprobe.exists() {
                return Some(ffprobe);
            }
        }

        None
    }

    /// 运行 FFmpeg
    pub fn run(&self, args: &[&str], input_file: Option<&str>, output_file: Option<&str>) -> Result<bool, Box<dyn Error>> {
        let mut cmd = Command::new(&self.ffmpeg_path);
        cmd.arg("-y"); // 覆盖输出

        if let Some(input) = input_file {
            cmd.arg("-i").arg(input);
        }

        cmd.args(args);

        if let Some(output) = output_file {
            cmd.arg(output);
        }

        let output = cmd
            .stderr(Stdio::piped())
            .stdout(Stdio::piped())
            .output()?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            eprintln!("FFmpeg 错误：{}", stderr);
            return Ok(false);
        }

        Ok(true)
    }

    /// 获取视频信息
    pub fn get_video_info(&self, input_file: &str) -> Result<VideoInfo, Box<dyn Error>> {
        let output = Command::new(&self.ffprobe_path)
            .args(&[
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                input_file,
            ])
            .output()?;

        let json_str = String::from_utf8_lossy(&output.stdout);
        let json: serde_json::Value = serde_json::from_str(&json_str)?;

        let format = json.get("format").unwrap_or(&serde_json::Value::Null);
        let streams = json.get("streams").and_then(|s| s.as_array()).unwrap_or(&Vec::new());

        let video_stream = streams.iter().find(|s| {
            s.get("codec_type").and_then(|v| v.as_str()) == Some("video")
        });

        let audio_stream = streams.iter().find(|s| {
            s.get("codec_type").and_then(|v| v.as_str()) == Some("audio")
        });

        Ok(VideoInfo {
            filename: Path::new(input_file).file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("unknown")
                .to_string(),
            duration: format.get("duration")
                .and_then(|v| v.as_str())
                .and_then(|s| s.parse().ok())
                .unwrap_or(0.0),
            size: format.get("size")
                .and_then(|v| v.as_u64())
                .unwrap_or(0),
            format: format.get("format_name")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown")
                .to_string(),
            video_codec: video_stream
                .and_then(|s| s.get("codec_name"))
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            audio_codec: audio_stream
                .and_then(|s| s.get("codec_name"))
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            width: video_stream
                .and_then(|s| s.get("width"))
                .and_then(|v| v.as_i64())
                .map(|v| v as i32)
                .unwrap_or(0),
            height: video_stream
                .and_then(|s| s.get("height"))
                .and_then(|v| v.as_i64())
                .map(|v| v as i32)
                .unwrap_or(0),
            bitrate: format.get("bit_rate")
                .and_then(|v| v.as_i64())
                .unwrap_or(0),
            frame_rate: video_stream
                .and_then(|s| s.get("r_frame_rate"))
                .and_then(|v| v.as_str())
                .and_then(|s| {
                    let parts: Vec<f64> = s.split('/').filter_map(|p| p.parse().ok()).collect();
                    if parts.len() == 2 && parts[1] != 0.0 {
                        Some(parts[0] / parts[1])
                    } else {
                        None
                    }
                })
                .unwrap_or(0.0),
            has_video: video_stream.is_some(),
            has_audio: audio_stream.is_some(),
        })
    }
}

/// FFmpeg 工具集
pub struct FFmpegTools {
    executor: FFmpegExecutor,
}

impl FFmpegTools {
    /// 创建工具集
    pub fn new() -> Result<Self, Box<dyn Error>> {
        Ok(Self {
            executor: FFmpegExecutor::new()?,
        })
    }

    /// 创建工具集（自定义执行器）
    pub fn with_executor(executor: FFmpegExecutor) -> Self {
        Self { executor }
    }

    /// 转换视频格式
    pub fn convert_format(
        &self,
        input_file: &str,
        output_file: &str,
        video_codec: &str,
        audio_codec: &str,
        crf: i32,
    ) -> Result<bool, Box<dyn Error>> {
        self.executor.run(
            &[
                "-c:v", video_codec,
                "-crf", &crf.to_string(),
                "-preset", "medium",
                "-c:a", audio_codec,
                "-b:a", "192k",
            ],
            Some(input_file),
            Some(output_file),
        )
    }

    /// 压缩视频
    pub fn compress(
        &self,
        input_file: &str,
        output_file: &str,
        quality: &str,
        max_width: i32,
        max_height: i32,
    ) -> Result<bool, Box<dyn Error>> {
        let crf = match quality {
            "low" => 28,
            "medium" => 23,
            "high" => 18,
            _ => 23,
        };

        let filter = format!(
            "scale='min({},iw)':'min({},ih)':force_original_aspect_ratio=decrease",
            max_width, max_height
        );

        self.executor.run(
            &[
                "-c:v", "libx264",
                "-crf", &crf.to_string(),
                "-preset", "slow",
                "-c:a", "aac",
                "-b:a", "128k",
                "-vf", &filter,
            ],
            Some(input_file),
            Some(output_file),
        )
    }

    /// 提取音频
    pub fn extract_audio(
        &self,
        input_file: &str,
        output_file: &str,
        audio_format: &str,
        bitrate: &str,
    ) -> Result<bool, Box<dyn Error>> {
        let audio_codec = if audio_format == "mp3" {
            "libmp3lame"
        } else {
            "copy"
        };

        self.executor.run(
            &[
                "-vn",
                "-acodec", audio_codec,
                "-ab", bitrate,
            ],
            Some(input_file),
            Some(output_file),
        )
    }

    /// 合并视频
    pub fn merge_videos(
        &self,
        input_files: &[&str],
        output_file: &str,
    ) -> Result<bool, Box<dyn Error>> {
        if input_files.len() < 2 {
            return Err("至少需要 2 个视频文件".into());
        }

        // 创建文件列表
        let list_file = tempfile::NamedTempFile::new()?;
        for file in input_files {
            use std::io::Write;
            writeln!(list_file.as_file(), "file '{}'", file)?;
        }

        self.executor.run(
            &[
                "-f", "concat",
                "-safe", "0",
                "-i", list_file.path().to_str().unwrap(),
                "-c", "copy",
            ],
            None,
            Some(output_file),
        )
    }

    /// 截取截图
    pub fn take_screenshot(
        &self,
        input_file: &str,
        output_file: &str,
        timestamp: &str,
        width: Option<i32>,
    ) -> Result<bool, Box<dyn Error>> {
        let mut args = vec!["-ss", timestamp, "-vframes", "1"];

        if let Some(w) = width {
            args.push("-vf");
            args.push(&format!("scale={}:auto", w));
        }

        self.executor.run(&args, Some(input_file), Some(output_file))
    }

    /// 批量截图
    pub fn take_screenshots_batch(
        &self,
        input_file: &str,
        output_dir: &str,
        interval: i32,
        width: i32,
    ) -> Result<Vec<String>, Box<dyn Error>> {
        let info = self.executor.get_video_info(input_file)?;
        let duration = info.duration as i32;

        std::fs::create_dir_all(output_dir)?;

        let mut screenshots = Vec::new();

        for i in 0..(duration / interval) {
            let timestamp = format!("{:02}:{:02}:{:02}", 0, 0, i * interval);
            let output_file = format!("{}/screenshot_{:04}.jpg", output_dir, i);

            if self.take_screenshot(input_file, &output_file, &timestamp, Some(width))? {
                screenshots.push(output_file);
            }
        }

        Ok(screenshots)
    }

    /// 裁剪视频
    pub fn trim_video(
        &self,
        input_file: &str,
        output_file: &str,
        start_time: &str,
        duration: Option<&str>,
    ) -> Result<bool, Box<dyn Error>> {
        let mut args = vec!["-ss", start_time, "-c", "copy"];

        if let Some(dur) = duration {
            args.push("-t");
            args.push(dur);
        }

        self.executor.run(&args, Some(input_file), Some(output_file))
    }

    /// 改变分辨率
    pub fn change_resolution(
        &self,
        input_file: &str,
        output_file: &str,
        resolution: &str,
    ) -> Result<bool, Box<dyn Error>> {
        self.executor.run(
            &[
                "-c:v", "libx264",
                "-vf", &format!("scale={}", resolution),
                "-c:a", "copy",
            ],
            Some(input_file),
            Some(output_file),
        )
    }

    /// 提取帧
    pub fn extract_frames(
        &self,
        input_file: &str,
        output_dir: &str,
        frame_rate: f64,
    ) -> Result<Vec<String>, Box<dyn Error>> {
        std::fs::create_dir_all(output_dir)?;

        let args = &[
            "-vf", &format!("fps={}", frame_rate),
            &format!("{}/frame_%06d.jpg", output_dir),
        ];

        self.executor.run(args, Some(input_file), None)?;

        // 收集生成的文件
        let mut frames = Vec::new();
        for entry in std::fs::read_dir(output_dir)? {
            let entry = entry?;
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) == Some("jpg") {
                frames.push(path.display().to_string());
            }
        }

        frames.sort();
        Ok(frames)
    }

    /// 获取视频信息
    pub fn get_video_info(&self, input_file: &str) -> Result<VideoInfo, Box<dyn Error>> {
        self.executor.get_video_info(input_file)
    }
}

impl Default for FFmpegTools {
    fn default() -> Self {
        Self::new().unwrap()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ffmpeg_executor() {
        // 注意：需要安装 ffmpeg
        let executor = FFmpegExecutor::new();
        assert!(executor.is_ok());
    }
}
