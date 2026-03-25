//! 命令行工具

use clap::{Parser, Subcommand};
use std::error::Error;
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "rustspider-video")]
#[command(about = "视频下载命令行工具", long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,

    /// 详细输出
    #[arg(short, long, global = true)]
    pub verbose: bool,
}

#[derive(Subcommand)]
pub enum Commands {
    /// 下载视频
    Download {
        /// 视频 URL
        url: String,

        /// 输出目录
        #[arg(short, long, default_value = "downloads")]
        output_dir: String,

        /// 输出文件名
        #[arg(short, long)]
        output_name: Option<String>,

        /// 并发数
        #[arg(short, long, default_value = "10")]
        workers: usize,
    },

    /// 解析视频 URL
    Parse {
        /// 视频 URL
        url: String,
    },

    /// 转换视频格式
    Convert {
        /// 输入文件
        input: String,

        /// 输出文件
        output: String,

        /// 目标格式
        #[arg(short, long)]
        format: String,
    },

    /// 获取视频信息
    Info {
        /// 输入文件
        input: String,
    },

    /// 截取截图
    Screenshot {
        /// 输入文件
        input: String,

        /// 输出文件
        #[arg(short, long)]
        output: Option<String>,

        /// 时间戳
        #[arg(short, long, default_value = "00:00:01")]
        timestamp: String,
    },
}

/// 运行 CLI
pub async fn run() -> Result<(), Box<dyn Error>> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Download {
            url,
            output_dir,
            output_name,
            workers,
        } => {
            cmd_download(&url, &output_dir, output_name.as_deref(), workers).await?;
        }

        Commands::Parse { url } => {
            cmd_parse(&url)?;
        }

        Commands::Convert {
            input,
            output,
            format,
        } => {
            cmd_convert(&input, &output, &format)?;
        }

        Commands::Info { input } => {
            cmd_info(&input)?;
        }

        Commands::Screenshot {
            input,
            output,
            timestamp,
        } => {
            cmd_screenshot(&input, output.as_deref(), &timestamp)?;
        }
    }

    Ok(())
}

async fn cmd_download(
    url: &str,
    output_dir: &str,
    output_name: Option<&str>,
    workers: usize,
) -> Result<(), Box<dyn Error>> {
    use crate::video::{hls_downloader::*, video_parser::*};

    println!("解析视频：{}", url);

    // 解析视频
    let parser = UniversalParser::new()?;
    let video = parser.parse(url).ok_or("无法解析视频")?;

    println!("✓ 解析成功：{}", video.title);
    println!("  平台：{}", video.platform);

    // 确定下载 URL
    let download_url = video
        .m3u8_url
        .or(video.mp4_url)
        .or(video.dash_url)
        .ok_or("未找到可下载的 URL")?;

    let name = output_name.unwrap_or(&video.video_id);

    if download_url.contains(".m3u8") {
        // HLS 下载
        let downloader = HlsDownloader::new(output_dir, workers)?;
        let success = downloader.download(&download_url, name).await?;

        if success {
            println!("✓ 下载完成");
        } else {
            println!("✗ 下载失败");
        }
    } else if download_url.contains(".mpd") {
        // DASH 下载
        let downloader = DashDownloader::new(output_dir)?;
        let success = downloader.download(&download_url, name).await?;

        if success {
            println!("✓ 下载完成");
        } else {
            println!("✗ 下载失败");
        }
    } else {
        // 直接下载
        println!("直接下载：{}", download_url);
        let client = reqwest::Client::new();
        let resp = client.get(download_url).send().await?;
        let bytes = resp.bytes().await?;

        std::fs::create_dir_all(output_dir)?;
        let output_path = PathBuf::from(output_dir).join(format!("{}.mp4", name));
        std::fs::write(&output_path, &bytes)?;

        println!("✓ 下载完成：{}", output_path.display());
    }

    Ok(())
}

fn cmd_parse(url: &str) -> Result<(), Box<dyn Error>> {
    use crate::video::video_parser::*;

    let parser = UniversalParser::new()?;
    let video = parser.parse(url).ok_or("无法解析视频")?;

    println!("\n视频信息:");
    println!("  平台：{}", video.platform);
    println!("  标题：{}", video.title);
    println!("  视频 ID: {}", video.video_id);

    if let Some(url) = &video.m3u8_url {
        println!("  M3U8: {}", url);
    }
    if let Some(url) = &video.mp4_url {
        println!("  MP4: {}", url);
    }

    Ok(())
}

fn cmd_convert(input: &str, output: &str, format: &str) -> Result<(), Box<dyn Error>> {
    use crate::video::ffmpeg_tools::*;

    let tools = FFmpegTools::new()?;

    println!("转换视频：{} -> {}", input, output);

    match format {
        "mp4" => {
            tools.convert_format(input, output, "libx264", "aac", 23)?;
        }
        "mp3" => {
            tools.extract_audio(input, output, "mp3", "192k")?;
        }
        _ => {
            return Err(format!("不支持的格式：{}", format).into());
        }
    }

    println!("✓ 转换完成");

    Ok(())
}

fn cmd_info(input: &str) -> Result<(), Box<dyn Error>> {
    use crate::video::ffmpeg_tools::*;

    let tools = FFmpegTools::new()?;
    let info = tools.get_video_info(input)?;

    println!("\n视频信息:");
    println!("  文件名：{}", info.filename);
    println!("  时长：{:.2}秒", info.duration);
    println!("  大小：{:.2}MB", info.size as f64 / 1024.0 / 1024.0);
    println!("  格式：{}", info.format);
    println!("  分辨率：{}x{}", info.width, info.height);
    println!("  视频编码：{}", info.video_codec);
    println!("  音频编码：{}", info.audio_codec);

    Ok(())
}

fn cmd_screenshot(
    input: &str,
    output: Option<&str>,
    timestamp: &str,
) -> Result<(), Box<dyn Error>> {
    use crate::video::ffmpeg_tools::*;

    let tools = FFmpegTools::new()?;
    let output_file = output.unwrap_or("screenshot.jpg");

    println!("截取截图：{} @ {}", input, timestamp);

    if tools.take_screenshot(input, output_file, timestamp, None)? {
        println!("✓ 截图完成：{}", output_file);
    } else {
        println!("✗ 截图失败");
    }

    Ok(())
}
