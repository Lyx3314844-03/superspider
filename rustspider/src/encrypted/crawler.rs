#![allow(dead_code)]

//! 加密网站爬取模块
//! 为 Rust Spider 提供强大的加密网站爬取能力

use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Duration;

/// 加密网站爬虫
pub struct EncryptedSiteCrawler {
    reverse_client: crate::node_reverse::client::NodeReverseClient,
    http_client: Client,
    user_agent: String,
}

struct PageFetchResult {
    html: String,
    status_code: u16,
    headers: HashMap<String, serde_json::Value>,
    cookies: String,
}

/// 加密信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EncryptionInfo {
    pub patterns: Vec<String>,
    pub encrypted_scripts: HashMap<String, String>,
    pub script_count: usize,
}

/// 爬取结果
#[derive(Debug, Serialize, Deserialize)]
pub struct CrawlResult {
    pub url: String,
    pub html: String,
    pub encryption_info: EncryptionInfo,
    pub anti_bot_profile: Option<crate::node_reverse::client::AntiBotProfileResponse>,
    pub decrypted_data: Vec<String>,
    pub webpack_modules: usize,
    pub success: bool,
    pub error: Option<String>,
}

impl EncryptedSiteCrawler {
    /// 创建新的加密网站爬虫
    pub fn new(reverse_service_url: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let url = if reverse_service_url.is_empty() {
            "http://localhost:3000"
        } else {
            reverse_service_url
        };

        let http_client = Client::builder()
            .timeout(Duration::from_secs(30))
            .default_headers({
                let mut headers = reqwest::header::HeaderMap::new();
                headers.insert(
                    reqwest::header::USER_AGENT,
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        .parse()
                        .map_err(|e| format!("Failed to parse User-Agent: {}", e))?,
                );
                headers.insert(
                    reqwest::header::ACCEPT,
                    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                        .parse()
                        .map_err(|e| format!("Failed to parse Accept header: {}", e))?,
                );
                headers.insert(
                    reqwest::header::ACCEPT_LANGUAGE,
                    "en-US,en;q=0.9,zh-CN;q=0.8"
                        .parse()
                        .map_err(|e| format!("Failed to parse Accept-Language header: {}", e))?,
                );
                headers
            })
            .build()
            .map_err(|e| format!("Failed to build HTTP client: {}", e))?;

        Ok(Self {
            reverse_client: crate::node_reverse::client::NodeReverseClient::new(url),
            http_client,
            user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36".to_string(),
        })
    }

    /// 创建默认爬虫
    pub fn default_crawler() -> Result<Self, Box<dyn std::error::Error>> {
        Self::new("http://localhost:3000")
    }

    /// 爬取加密网站
    pub async fn crawl(&self, url: &str) -> Result<CrawlResult, Box<dyn std::error::Error>> {
        let mut result = CrawlResult {
            url: url.to_string(),
            html: String::new(),
            encryption_info: EncryptionInfo {
                patterns: Vec::new(),
                encrypted_scripts: HashMap::new(),
                script_count: 0,
            },
            anti_bot_profile: None,
            decrypted_data: Vec::new(),
            webpack_modules: 0,
            success: false,
            error: None,
        };

        println!("\n{}", "=".repeat(80));
        println!("🔐 加密网站爬取处理器 (Rust Spider)");
        println!("{}", "=".repeat(80));

        // 步骤 1: 检查逆向服务
        println!("\n[1/6] 检查 Node.js 逆向服务...");
        if !self.check_reverse_service().await? {
            result.error = Some("Node.js 逆向服务不可用".to_string());
            result.success = false;
            return Ok(result);
        }
        println!("✅ 逆向服务正常运行");

        // 步骤 2: 获取页面
        println!("\n[2/6] 获取加密页面...");
        let page = self.fetch_page(url).await?;
        result.html = page.html.clone();
        println!("✅ 页面获取成功，大小: {} 字节", page.html.len());

        println!("\n[3/7] 生成反爬画像...");
        result.anti_bot_profile = self.profile_anti_bot(url, &page).await?;
        println!("✅ 反爬画像完成");

        // 步骤 3: 检测加密
        println!("\n[4/7] 检测页面加密...");
        let encryption_info = self.detect_encryption(&page.html);
        result.encryption_info = encryption_info.clone();
        if !encryption_info.is_empty() {
            encryption_info.print();
        } else {
            println!("ℹ️  未检测到明显加密");
        }
        println!("✅ 加密检测完成");

        // 步骤 4: 模拟浏览器环境
        println!("\n[5/7] 模拟浏览器环境...");
        self.simulate_browser(&page.html).await?;
        println!("✅ 浏览器模拟完成");

        // 步骤 5: 分析加密算法
        println!("\n[6/7] 分析加密算法...");
        if !encryption_info.encrypted_scripts.is_empty() {
            self.analyze_encryption(&encryption_info.encrypted_scripts)
                .await?;
        }
        println!("✅ 加密分析完成");

        // 步骤 6: 执行混淆代码
        println!("\n[7/7] 执行混淆代码...");
        self.execute_obfuscated_code(&page.html).await?;
        println!("✅ 混淆代码执行完成");

        result.success = true;
        println!("\n{}", "=".repeat(80));
        println!("✅ 加密网站爬取完成！");
        println!("{}", "=".repeat(80));

        Ok(result)
    }

    /// 检查逆向服务
    async fn check_reverse_service(&self) -> Result<bool, Box<dyn std::error::Error>> {
        self.reverse_client.health_check().await
    }

    /// 获取页面
    async fn fetch_page(&self, url: &str) -> Result<PageFetchResult, Box<dyn std::error::Error>> {
        let response = self.http_client.get(url).send().await?;
        let status_code = response.status().as_u16();
        let headers = response
            .headers()
            .iter()
            .map(|(name, value)| {
                let key = name.as_str().to_string();
                let value =
                    serde_json::Value::String(value.to_str().unwrap_or_default().to_string());
                (key, value)
            })
            .collect::<HashMap<_, _>>();
        let cookies = response
            .headers()
            .get_all(reqwest::header::SET_COOKIE)
            .iter()
            .filter_map(|value| value.to_str().ok())
            .collect::<Vec<_>>()
            .join("; ");
        let html = response.text().await?;
        Ok(PageFetchResult {
            html,
            status_code,
            headers,
            cookies,
        })
    }

    async fn profile_anti_bot(
        &self,
        url: &str,
        page: &PageFetchResult,
    ) -> Result<
        Option<crate::node_reverse::client::AntiBotProfileResponse>,
        Box<dyn std::error::Error>,
    > {
        let request = crate::node_reverse::client::AntiBotProfileRequest {
            html: page.html.clone(),
            js: String::new(),
            headers: page.headers.clone(),
            cookies: page.cookies.clone(),
            status_code: Some(page.status_code),
            url: url.to_string(),
        };
        let profile = self.reverse_client.profile_anti_bot(&request).await?;
        if !profile.success {
            return Ok(None);
        }

        println!(
            "  🛡️  Anti-bot profile: level={} score={}",
            profile.level, profile.score
        );
        if !profile.signals.is_empty() {
            println!("  signals: {}", profile.signals.join(", "));
        }
        if let Some(next) = profile.recommendations.first() {
            println!("  next: {}", next);
        }

        Ok(Some(profile))
    }

    /// 检测加密
    fn detect_encryption(&self, html: &str) -> EncryptionInfo {
        let mut info = EncryptionInfo {
            patterns: Vec::new(),
            encrypted_scripts: HashMap::new(),
            script_count: 0,
        };

        // 加密检测模式
        let encryption_patterns = vec![
            r"CryptoJS\.(AES|DES|RSA|MD5|SHA|HMAC|RC4|Base64)",
            r"encrypt\(|decrypt\(",
            r"createCipheriv|createDecipheriv",
            r"publicEncrypt|privateDecrypt",
            r"btoa\(|atob\(",
            r"eval\(function\(p,a,c,k,e,d\)",
            r"\\x[0-9a-fA-F]{2}",
        ];

        for pattern in encryption_patterns {
            if regex::Regex::new(pattern).unwrap().is_match(html) {
                info.patterns.push(pattern.to_string());
            }
        }

        // 提取 script 标签
        let script_pattern = regex::Regex::new(r"<script[^>]*>(.*?)</script>").unwrap();
        let scripts: Vec<&str> = script_pattern
            .captures_iter(html)
            .filter_map(|cap| cap.get(1))
            .map(|m| m.as_str())
            .collect();

        info.script_count = scripts.len();

        // 分析每个脚本
        for (i, script) in scripts.iter().enumerate() {
            let script = script.trim();
            if !script.is_empty() && !script.starts_with("<!--") && self.is_encrypted(script) {
                let key = format!("script_{}", i);
                info.encrypted_scripts.insert(key, script.to_string());
            }
        }

        info
    }

    /// 检查代码是否被加密
    fn is_encrypted(&self, code: &str) -> bool {
        if code.contains("eval(function(")
            || code.contains("\\x")
            || (code.len() > 1000 && !code.contains(" "))
        {
            return true;
        }

        code.contains("CryptoJS.")
            || code.contains("encrypt(")
            || code.contains("decrypt(")
            || code.contains("atob(")
            || code.contains("btoa(")
    }

    /// 模拟浏览器环境
    async fn simulate_browser(&self, html: &str) -> Result<(), Box<dyn std::error::Error>> {
        // 检测浏览器指纹
        let fingerprint_pattern =
            regex::Regex::new(r"navigator\.(userAgent|platform|language|vendor)").unwrap();
        if fingerprint_pattern.is_match(html) {
            println!("  🌐 检测到浏览器指纹检测");

            let result = self.reverse_client.simulate_browser(
                "return JSON.stringify({userAgent: navigator.userAgent, platform: navigator.platform});",
                Some(serde_json::json!({
                    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "language": "zh-CN",
                    "platform": "Win32",
                })),
            ).await?;

            if result.success {
                println!("  ✅ 浏览器环境模拟成功");
            }
        }

        Ok(())
    }

    /// 分析加密算法
    async fn analyze_encryption(
        &self,
        scripts: &HashMap<String, String>,
    ) -> Result<(), Box<dyn std::error::Error>> {
        for (key, script) in scripts {
            println!("  🔍 分析 {}...", key);

            let result = self.reverse_client.analyze_crypto(script).await?;

            if result.success && !result.crypto_types.is_empty() {
                println!("    ✅ 检测到加密算法:");
                for crypto in &result.crypto_types {
                    println!("      - {} (置信度: {:.2})", crypto.name, crypto.confidence);
                }
            }

            if !result.keys.is_empty() {
                println!("    🔑 密钥:");
                for key in &result.keys {
                    println!("      - {}", key);
                }
            }
        }

        Ok(())
    }

    /// 执行混淆代码
    async fn execute_obfuscated_code(&self, html: &str) -> Result<(), Box<dyn std::error::Error>> {
        // 查找 eval 混淆的代码
        let eval_pattern = regex::Regex::new(r"eval\(function\(p,a,c,k,e,d\)\{(.*?)\}").unwrap();
        let matches: Vec<&str> = eval_pattern.find_iter(html).map(|m| m.as_str()).collect();

        let count = matches.len().min(5);
        for (i, obfuscated_code) in matches.iter().take(count).enumerate() {
            println!("  📦 执行混淆代码块 #{}...", i + 1);

            let result = self
                .reverse_client
                .execute_js(
                    obfuscated_code,
                    Some(serde_json::json!({
                        "window": {},
                        "document": {},
                        "navigator": {"userAgent": "Mozilla/5.0"},
                    })),
                    Some(10000),
                )
                .await?;

            if result.success {
                println!("    ✅ 执行成功");
                if let Some(result_str) = result.result.as_str() {
                    let end = result_str.len().min(100);
                    println!("    📝 结果: {}", &result_str[..end]);
                }
            }
        }

        if count == 0 {
            println!("  ℹ️  未找到 eval 混淆代码");
        }

        Ok(())
    }
}

impl EncryptionInfo {
    /// 检查是否为空
    pub fn is_empty(&self) -> bool {
        self.patterns.is_empty() && self.encrypted_scripts.is_empty()
    }

    /// 打印加密信息
    pub fn print(&self) {
        if !self.patterns.is_empty() {
            println!("  🔐 检测到加密模式:");
            for pattern in &self.patterns {
                println!("    - {}", pattern);
            }
        }
        if !self.encrypted_scripts.is_empty() {
            println!("  📜 加密脚本数: {}", self.encrypted_scripts.len());
        }
        println!("  📄 总脚本数: {}", self.script_count);
    }
}
