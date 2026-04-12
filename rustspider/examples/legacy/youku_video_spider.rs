// Rust 优酷视频爬虫
// 使用 rustspider 框架爬取优酷视频信息
//
// 目标视频：https://v.youku.com/v_show/id_XNTk4Mjg1MjEzMg==.html
//
// 运行方法:
// ```bash
// cd C:\Users\Administrator\spider\rustspider
// cargo run --example youku_video_spider
// ```

use std::error::Error;
use std::fs;
use std::time::Duration;

/// 视频信息
#[derive(Debug, Clone, Default, serde::Serialize)]
pub struct VideoInfo {
    pub title: String,
    pub description: String,
    pub duration: String,
    pub channel: String,
    pub url: String,
    pub thumbnail: String,
    pub views: String,
    pub published: String,
    pub video_id: String,
    pub download_url: String,
}

/// 优酷视频爬虫
pub struct YoukuVideoSpider {
    video_url: String,
    video_info: VideoInfo,
    html: String,
}

impl YoukuVideoSpider {
    pub fn new(video_url: impl Into<String>) -> Self {
        Self {
            video_url: video_url.into(),
            video_info: VideoInfo::default(),
            html: String::new(),
        }
    }

    /// 启动爬虫
    pub fn start(&mut self) -> Result<VideoInfo, Box<dyn Error>> {
        self.print_header();

        // 1. 初始化
        if let Err(e) = self.initialize() {
            self.on_error_msg(&e.to_string());
            return Ok(self.video_info.clone());
        }

        // 2. 获取 HTML
        if let Err(e) = self.fetch_html() {
            self.on_error_msg(&e.to_string());
            return Ok(self.video_info.clone());
        }

        // 3. 解析视频
        if let Err(e) = self.parse_video() {
            self.on_error_msg(&e.to_string());
            return Ok(self.video_info.clone());
        }

        // 4. 打印结果
        self.print_results();

        // 5. 保存结果
        if let Err(e) = self.save_results() {
            self.on_error_msg(&e.to_string());
        }

        Ok(self.video_info.clone())
    }

    fn print_header(&self) {
        println!("\n{}", "╔".repeat(30));
        println!(
            "{} Rust/rustspider - 优酷视频爬虫 {}",
            "║".repeat(10),
            "║".repeat(10)
        );
        println!("{}", "╚".repeat(30));
        println!("\n📺 视频链接：{}\n", self.video_url);
    }

    fn initialize(&mut self) -> Result<(), Box<dyn Error>> {
        println!("🚀 初始化爬虫...");

        // 提取视频 ID
        if let Some(id) = self.extract_video_id_from_url() {
            self.video_info.video_id = id;
        }

        self.video_info.url = self.video_url.clone();

        println!("   ✓ 初始化完成");
        Ok(())
    }

    fn fetch_html(&mut self) -> Result<(), Box<dyn Error>> {
        println!("🌐 正在获取页面内容...");

        // 创建 HTTP 客户端
        let client = reqwest::blocking::Client::builder()
            .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            .timeout(Duration::from_secs(30))
            .build()?;

        // 尝试不同的 URL
        let urls_to_try = vec![
            self.video_url.clone(),
            self.video_url.replace("youku.tv", "youku.com"),
        ];

        for url in urls_to_try {
            println!("   尝试：{}", url);

            match client.get(&url).send() {
                Ok(response) => {
                    if response.status().is_success() {
                        self.html = response.text()?;
                        println!("   ✓ 获取成功");

                        // 保存 HTML
                        fs::write("youku_video_source.html", &self.html)?;
                        println!("   ✓ HTML 已保存到：youku_video_source.html");
                        return Ok(());
                    } else {
                        println!("   ⚠️  状态码：{}", response.status());
                    }
                }
                Err(e) => {
                    println!("   ⚠️  请求失败：{}", e);
                }
            }
        }

        // 如果 HTTP 请求失败，尝试使用 Playwright
        println!("   尝试使用浏览器获取...");
        self.fetch_with_browser()?;

        Ok(())
    }

    fn fetch_with_browser(&mut self) -> Result<(), Box<dyn Error>> {
        println!("   🚀 启动 Playwright 浏览器...");

        // 使用 playwright 命令行工具
        let output = std::process::Command::new("pwsh")
            .args([
                "-Command",
                &format!(
                    r#"
                    $url = "{}"
                    Start-Process "msedge" --headless --window-size=1920,1080 --user-agent="Mozilla/5.0" $url
                    Start-Sleep -Seconds 5
                    "#,
                    self.video_url
                ),
            ])
            .output();

        match output {
            Ok(_) => {
                println!("   ✓ 浏览器已启动（后台）");
                // 这里可以添加更复杂的浏览器自动化逻辑
            }
            Err(e) => {
                println!("   ⚠️  浏览器启动失败：{}", e);
            }
        }

        Ok(())
    }

    fn parse_video(&mut self) -> Result<(), Box<dyn Error>> {
        println!("🔍 解析视频信息...");

        // 方法 1: 从 JSON 解析
        self.parse_from_json()?;

        // 方法 2: 使用正则解析
        if self.video_info.title.is_empty() {
            println!("   尝试使用正则解析...");
            self.parse_with_regex()?;
        }

        if !self.video_info.title.is_empty() {
            println!("   ✓ 解析成功：{}", self.video_info.title);
        } else {
            println!("   ⚠️  未能解析到视频信息");
        }

        Ok(())
    }

    fn parse_from_json(&mut self) -> Result<(), Box<dyn Error>> {
        // 查找 JSON 数据
        let patterns = vec![
            r#"window\.__INITIAL_DATA__\s*=\s*({.+?});"#,
            r#"var\s+__INITIAL_DATA__\s*=\s*({.+?});"#,
            r#""initData"\s*:\s*({.+?})[,}]"#,
        ];

        for pattern in &patterns {
            if let Ok(re) = regex::Regex::new(pattern) {
                if let Some(caps) = re.captures(&self.html) {
                    if let Some(json_str) = caps.get(1) {
                        let json_str = json_str.as_str().replace("undefined", "null");

                        if let Ok(data) = serde_json::from_str::<serde_json::Value>(&json_str) {
                            self.extract_from_json(&data);
                            if !self.video_info.title.is_empty() {
                                return Ok(());
                            }
                        }
                    }
                }
            }
        }

        Ok(())
    }

    fn extract_from_json(&mut self, data: &serde_json::Value) {
        if let Some(obj) = data.as_object() {
            // 递归查找 data 字段
            if let Some(data_val) = obj.get("data") {
                self.extract_from_json(data_val);
            }

            // 提取标题
            if let Some(title) = obj.get("title").and_then(|v| v.as_str()) {
                self.video_info.title = title.to_string();
            }

            // 提取描述
            if let Some(desc) = obj.get("description").and_then(|v| v.as_str()) {
                self.video_info.description = desc.to_string();
            }

            // 提取频道
            if let Some(channel) = obj.get("channel").and_then(|v| v.as_str()) {
                self.video_info.channel = channel.to_string();
            }

            // 提取观看次数
            if let Some(views) = obj.get("views").or_else(|| obj.get("viewCount")) {
                self.video_info.views = match views {
                    serde_json::Value::String(s) => s.clone(),
                    serde_json::Value::Number(n) => n.to_string(),
                    _ => String::new(),
                };
            }

            // 提取缩略图
            if let Some(thumb) = obj.get("thumbnail").or_else(|| obj.get("poster")) {
                if let Some(thumb_str) = thumb.as_str() {
                    self.video_info.thumbnail = thumb_str.to_string();
                }
            }

            // 提取视频 URL
            if let Some(url) = obj.get("videoUrl").or_else(|| obj.get("download_url")) {
                if let Some(url_str) = url.as_str() {
                    self.video_info.download_url = url_str.to_string();
                }
            }
        }
    }

    fn parse_with_regex(&mut self) -> Result<(), Box<dyn Error>> {
        // 标题
        let title_patterns = vec![r#"<title>([^<]+)</title>"#, r#""title"\s*:\s*"([^"]+)""#];

        for pattern in &title_patterns {
            if let Ok(re) = regex::Regex::new(pattern) {
                if let Some(caps) = re.captures(&self.html) {
                    if let Some(title) = caps.get(1) {
                        self.video_info.title = title.as_str().trim().to_string();
                        // 清理标题
                        self.video_info.title = self
                            .video_info
                            .title
                            .replace(" - 优酷", "")
                            .replace("- 优酷", "");
                        break;
                    }
                }
            }
        }

        // 视频 ID
        if let Ok(re) = regex::Regex::new(r#"id_X([a-zA-Z0-9=]+)"#) {
            if let Some(caps) = re.captures(&self.html) {
                if let Some(id) = caps.get(1) {
                    self.video_info.video_id = format!("X{}", id.as_str());
                }
            }
        }

        Ok(())
    }

    fn extract_video_id_from_url(&self) -> Option<String> {
        if let Ok(re) = regex::Regex::new(r#"id_([a-zA-Z0-9=]+)"#) {
            if let Some(caps) = re.captures(&self.video_url) {
                if let Some(id) = caps.get(1) {
                    return Some(id.as_str().to_string());
                }
            }
        }
        None
    }

    fn print_results(&self) {
        println!("\n{}", "═".repeat(60));
        println!("{:>20}爬取结果", "");
        println!("{}", "═".repeat(60));

        if !self.video_info.title.is_empty() {
            println!("\n📺 标题：{}", self.video_info.title);
        } else {
            println!("\n⚠️  未找到视频标题");
        }

        if !self.video_info.video_id.is_empty() {
            println!("🆔 ID: {}", self.video_info.video_id);
        }
        if !self.video_info.description.is_empty() {
            let desc = &self.video_info.description;
            if desc.len() > 100 {
                println!("📝 描述：{}...", &desc[..100]);
            } else {
                println!("📝 描述：{}", desc);
            }
        }
        if !self.video_info.channel.is_empty() {
            println!("👤 频道：{}", self.video_info.channel);
        }
        if !self.video_info.views.is_empty() {
            println!("👁️ 观看：{}", self.video_info.views);
        }
        if !self.video_info.thumbnail.is_empty() {
            println!("🖼️ 缩略图：{}", self.video_info.thumbnail);
        }
        if !self.video_info.download_url.is_empty() {
            println!("🔗 下载链接：{}", self.video_info.download_url);
        }
        if !self.video_info.url.is_empty() {
            println!("🔗 视频链接：{}", self.video_info.url);
        }
    }

    fn on_error_msg(&self, error: &str) {
        println!("\n❌ 爬取失败：{}", error);
    }

    /// 保存结果
    pub fn save_results(&self) -> Result<(), Box<dyn Error>> {
        println!("\n💾 导出结果...");

        let timestamp = chrono::Local::now().format("%Y%m%d_%H%M%S").to_string();

        // JSON
        let json_path = format!("youku_video_{}.json", timestamp);
        let json_content = serde_json::to_string_pretty(&vec![&self.video_info])?;
        fs::write(&json_path, json_content)?;
        println!("   ✓ JSON: {}", json_path);

        // TXT
        let txt_path = format!("youku_video_{}.txt", timestamp);
        let mut txt_content = String::new();
        txt_content.push_str(&format!("标题：{}\n", self.video_info.title));
        txt_content.push_str(&format!("ID: {}\n", self.video_info.video_id));
        txt_content.push_str(&format!("描述：{}\n", self.video_info.description));
        txt_content.push_str(&format!("频道：{}\n", self.video_info.channel));
        txt_content.push_str(&format!("观看：{}\n", self.video_info.views));
        txt_content.push_str(&format!("缩略图：{}\n", self.video_info.thumbnail));
        txt_content.push_str(&format!("下载链接：{}\n", self.video_info.download_url));
        txt_content.push_str(&format!("视频链接：{}\n", self.video_info.url));
        fs::write(&txt_path, txt_content)?;
        println!("   ✓ TXT: {}", txt_path);

        Ok(())
    }
}

fn main() -> Result<(), Box<dyn Error>> {
    // 优酷视频链接
    let video_url = "https://v.youku.com/v_show/id_XNTk4Mjg1MjEzMg==.html";

    // 创建爬虫
    let mut spider = YoukuVideoSpider::new(video_url);

    // 启动爬虫
    spider.start()?;

    Ok(())
}
