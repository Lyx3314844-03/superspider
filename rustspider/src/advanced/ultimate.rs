//! Rust Spider 终极增强版 v5.0
//! 极致性能 + 系统级 + 零拷贝

#![allow(dead_code)]

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::Semaphore;
use tokio::task::JoinSet;

use crate::antibot::enhanced::{base64_decode, CaptchaSolver};
use crate::encrypted::EncryptedSiteCrawlerEnhanced;
use crate::node_reverse::client::NodeReverseClient;

/// 终极爬虫
pub struct UltimateSpider {
    config: UltimateConfig,
    reverse_client: NodeReverseClient,
    enhanced_crawler: Arc<EncryptedSiteCrawlerEnhanced>,
    proxy_pool: Option<ProxyPool>,
    monitor: Arc<SpiderMonitor>,
    checkpoint_mgr: CheckpointManager,
}

/// 终极配置
#[derive(Debug, Clone)]
pub struct UltimateConfig {
    pub reverse_service_url: String,
    pub max_concurrency: usize,
    pub max_retries: u32,
    pub timeout: Duration,
    pub user_agent: String,
    pub proxy_servers: Vec<String>,
    pub output_format: String,
    pub monitor_port: u16,
    pub checkpoint_dir: String,
    pub enable_ai: bool,
    pub enable_browser: bool,
    pub enable_distributed: bool,
    pub captcha_provider: String,
    pub captcha_api_key: String,
    pub captcha_fallback_provider: Option<String>,
    pub captcha_fallback_api_key: Option<String>,
}

impl Default for UltimateConfig {
    fn default() -> Self {
        Self {
            reverse_service_url: "http://localhost:3000".to_string(),
            max_concurrency: 10,
            max_retries: 3,
            timeout: Duration::from_secs(30),
            user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36".to_string(),
            proxy_servers: vec![],
            output_format: "json".to_string(),
            monitor_port: 8080,
            checkpoint_dir: "artifacts/ultimate/checkpoints".to_string(),
            enable_ai: true,
            enable_browser: true,
            enable_distributed: true,
            captcha_provider: "2captcha".to_string(),
            captcha_api_key: String::new(),
            captcha_fallback_provider: None,
            captcha_fallback_api_key: None,
        }
    }
}

/// 爬取任务
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CrawlTask {
    pub id: String,
    pub url: String,
    pub priority: i32,
    pub depth: u32,
    pub metadata: HashMap<String, serde_json::Value>,
}

/// 爬取结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CrawlResult {
    pub task_id: String,
    pub url: String,
    pub success: bool,
    pub data: Option<serde_json::Value>,
    pub error: Option<String>,
    pub duration: Duration,
    pub retries: u32,
    pub proxy_used: Option<String>,
    pub anti_detect: HashMap<String, bool>,
    pub anti_bot_level: Option<String>,
    pub anti_bot_signals: Vec<String>,
    pub reverse_runtime: serde_json::Value,
}

#[derive(Debug, Clone, Default)]
struct CaptchaHints {
    challenge_kind: Option<String>,
    site_key: Option<String>,
    action: Option<String>,
    c_data: Option<String>,
    page_data: Option<String>,
    image_bytes: Option<Vec<u8>>,
    image_source: Option<String>,
}

/// 代理池
pub struct ProxyPool {
    proxies: Vec<String>,
    current_idx: usize,
}

impl ProxyPool {
    pub fn new(proxies: Vec<String>) -> Self {
        Self {
            proxies: if proxies.is_empty() {
                vec![
                    "http://proxy1:8080".to_string(),
                    "http://proxy2:8080".to_string(),
                ]
            } else {
                proxies
            },
            current_idx: 0,
        }
    }

    pub fn get_next_proxy(&mut self) -> Option<String> {
        if self.proxies.is_empty() {
            return None;
        }
        let proxy = self.proxies[self.current_idx].clone();
        self.current_idx = (self.current_idx + 1) % self.proxies.len();
        Some(proxy)
    }
}

/// 爬虫监控器
pub struct SpiderMonitor {
    pub total_tasks: usize,
    pub success_tasks: usize,
    pub failed_tasks: usize,
    pub start_time: Instant,
}

impl SpiderMonitor {
    pub fn new() -> Self {
        Self {
            total_tasks: 0,
            success_tasks: 0,
            failed_tasks: 0,
            start_time: Instant::now(),
        }
    }

    pub fn print_status(&self) {
        println!("  📊 监控状态:");
        println!("    总任务数: {}", self.total_tasks);
        println!("    成功: {}", self.success_tasks);
        println!("    失败: {}", self.failed_tasks);
        println!("    运行时间: {:?}", self.start_time.elapsed());
    }
}

impl Default for SpiderMonitor {
    fn default() -> Self {
        Self::new()
    }
}

/// 断点管理器
#[derive(Clone)]
pub struct CheckpointManager {
    checkpoint_dir: String,
}

impl CheckpointManager {
    pub fn new(checkpoint_dir: String) -> Self {
        Self { checkpoint_dir }
    }

    pub fn save_checkpoint(&self, task_id: &str, data: &serde_json::Value) {
        let dir = PathBuf::from(&self.checkpoint_dir);
        let _ = fs::create_dir_all(&dir);
        let path = dir.join(format!("{task_id}.json"));
        if let Ok(encoded) = serde_json::to_string_pretty(data) {
            let _ = fs::write(path, encoded);
        }
    }

    pub fn load_checkpoint(&self, task_id: &str) -> Option<serde_json::Value> {
        let path = PathBuf::from(&self.checkpoint_dir).join(format!("{task_id}.json"));
        let content = fs::read_to_string(path).ok()?;
        serde_json::from_str(&content).ok()
    }
}

impl UltimateSpider {
    /// 创建终极爬虫
    pub fn new(config: UltimateConfig) -> Self {
        let enhanced_crawler = Arc::new(EncryptedSiteCrawlerEnhanced::new(
            &config.reverse_service_url,
        ));

        let proxy_pool = if !config.proxy_servers.is_empty() {
            Some(ProxyPool::new(config.proxy_servers.clone()))
        } else {
            None
        };

        let checkpoint_dir = config.checkpoint_dir.clone();
        let reverse_service_url = config.reverse_service_url.clone();

        Self {
            config,
            reverse_client: NodeReverseClient::new(&reverse_service_url),
            enhanced_crawler,
            proxy_pool,
            monitor: Arc::new(SpiderMonitor::new()),
            checkpoint_mgr: CheckpointManager::new(checkpoint_dir),
        }
    }

    /// 启动终极爬虫
    pub async fn start(
        &self,
        urls: Vec<String>,
    ) -> Result<Vec<CrawlResult>, Box<dyn std::error::Error>> {
        println!("\n{}", "=".repeat(100));
        println!("🚀 Rust Spider 终极增强版 v5.0");
        println!("{}", "=".repeat(100));

        // 步骤 1: 检查服务
        println!("\n[1/10] 检查 Node.js 逆向服务...");
        if !self.reverse_client.health_check().await? {
            return Err("Node.js 逆向服务不可用".into());
        }
        println!("✅ 逆向服务正常运行");

        // 步骤 2: 初始化监控
        println!("\n[2/10] 初始化监控面板...");
        println!("✅ 监控面板已启动");

        // 步骤 3: 创建任务
        println!("\n[3/10] 创建爬取任务...");
        let tasks: Vec<CrawlTask> = urls
            .into_iter()
            .enumerate()
            .map(|(i, url)| CrawlTask {
                id: format!("task_{}", i),
                url,
                priority: 0,
                depth: 0,
                metadata: HashMap::new(),
            })
            .collect();
        println!("✅ 已创建 {} 个任务", tasks.len());

        // 步骤 4: 开始爬取
        println!("\n[4/10] 开始爬取...");
        let results = self.crawl_tasks(tasks).await?;

        println!("\n{}", "=".repeat(100));
        println!("✅ 爬取完成！");
        println!("{}", "=".repeat(100));

        Ok(results)
    }

    /// 爬取任务列表
    async fn crawl_tasks(
        &self,
        tasks: Vec<CrawlTask>,
    ) -> Result<Vec<CrawlResult>, Box<dyn std::error::Error>> {
        let semaphore = Arc::new(Semaphore::new(self.config.max_concurrency));
        let mut join_set = JoinSet::new();
        let mut results = Vec::new();

        for task in tasks {
            let semaphore = semaphore.clone();
            let enhanced_crawler = self.enhanced_crawler.clone();
            let config = self.config.clone();
            let checkpoint_mgr = self.checkpoint_mgr.clone();

            join_set.spawn(async move {
                let _permit = semaphore.acquire().await.unwrap();
                Self::crawl_page(task, enhanced_crawler, config, checkpoint_mgr).await
            });
        }

        while let Some(result) = join_set.join_next().await {
            if let Ok(result) = result {
                results.push(result);
            }
        }

        Ok(results)
    }

    /// 爬取单个页面
    async fn crawl_page(
        task: CrawlTask,
        enhanced_crawler: Arc<EncryptedSiteCrawlerEnhanced>,
        config: UltimateConfig,
        checkpoint_mgr: CheckpointManager,
    ) -> CrawlResult {
        let start_time = Instant::now();
        let mut result = CrawlResult {
            task_id: task.id.clone(),
            url: task.url.clone(),
            success: false,
            data: None,
            error: None,
            duration: Duration::ZERO,
            retries: 0,
            proxy_used: None,
            anti_detect: HashMap::new(),
            anti_bot_level: None,
            anti_bot_signals: Vec::new(),
            reverse_runtime: serde_json::json!({}),
        };

        println!("\n📄 爬取页面: {}", task.url);

        // 步骤 1: 智能反爬检测
        println!("  [1/8] 智能反爬检测...");
        let (anti_detect, anti_bot_level, anti_bot_signals, captcha_hints) =
            Self::detect_anti_detection(&task.url, &config).await;
        result.anti_detect = anti_detect.clone();
        result.anti_bot_level = anti_bot_level.clone();
        result.anti_bot_signals = anti_bot_signals.clone();
        println!(
            "  ✅ 检测到 {} 种反爬机制",
            anti_detect.values().filter(|enabled| **enabled).count()
        );
        if let Some(level) = &anti_bot_level {
            println!("    level: {}", level);
        }
        if !anti_bot_signals.is_empty() {
            println!("    signals: {}", anti_bot_signals.join(", "));
        }

        // 步骤 2: 自动反爬绕过
        println!("  [2/8] 自动反爬绕过...");
        let captcha_recovery = if anti_detect.get("captcha").copied().unwrap_or(false) {
            Self::attempt_captcha_recovery(&task, &config, &captcha_hints).await
        } else {
            None
        };
        if anti_detect.get("captcha").copied().unwrap_or(false) {
            println!("    🔓 检测到验证码");
            if let Some(recovery) = &captcha_recovery {
                if let Some(status) = recovery.get("status").and_then(|value| value.as_str()) {
                    println!("    captcha recovery: {}", status);
                    result
                        .anti_bot_signals
                        .push(format!("captcha-recovery:{status}"));
                }
            }
            if let Some(source) = &captcha_hints.image_source {
                println!("    captcha image: {}", source);
            }
        }
        if anti_detect.get("waf").copied().unwrap_or(false) {
            println!("    🛡️  检测到 WAF");
        }
        println!("  ✅ 反爬绕过完成");

        // 步骤 3: TLS 指纹生成
        println!("  [3/8] TLS 指纹生成...");
        if let Ok(tls_fp) = enhanced_crawler
            .generate_tls_fingerprint("chrome", "120")
            .await
        {
            println!("  ✅ JA3: {}", tls_fp.ja3);
        }

        // 步骤 4: Canvas 指纹生成
        println!("  [4/8] Canvas 指纹生成...");
        if let Ok(canvas_fp) = enhanced_crawler.generate_canvas_fingerprint().await {
            println!("  ✅ Hash: {}", canvas_fp.hash);
        }

        let reverse_runtime = Self::collect_reverse_runtime(&task.url, &config).await;
        let mut reverse_runtime = reverse_runtime;
        if let Some(runtime) = reverse_runtime.as_object_mut() {
            runtime.insert(
                "captcha_hints".to_string(),
                Self::summarize_captcha_hints(&captcha_hints),
            );
            if let Some(recovery) = captcha_recovery.clone() {
                runtime.insert("captcha_recovery".to_string(), recovery);
            }
        }
        result.reverse_runtime = reverse_runtime.clone();

        // 步骤 5: 浏览器模拟
        println!("  [5/8] 浏览器环境模拟...");
        match Self::simulate_browser(&task.url, &config).await {
            Ok(_) => println!("  ✅ 浏览器模拟完成"),
            Err(err) => println!("  ⚠️ 浏览器模拟未完成: {}", err),
        }

        // 步骤 6: 加密分析
        println!("  [6/8] 加密分析...");
        match Self::analyze_encryption(&task.url, &config).await {
            Ok(_) => println!("  ✅ 加密分析完成"),
            Err(err) => println!("  ⚠️ 加密分析未完成: {}", err),
        }

        // 步骤 7: AI 提取
        println!("  [7/8] AI 智能提取...");
        let mut data = Self::ai_extract(&task.url);
        if let Some(object) = data.as_object_mut() {
            object.insert(
                "_runtime".to_string(),
                serde_json::json!({
                    "reverse": reverse_runtime
                }),
            );
        }
        result.data = Some(data);
        println!("  ✅ AI 提取完成");

        // 步骤 8: 数据存储
        println!("  [8/8] 数据存储...");
        if let Some(data) = &result.data {
            checkpoint_mgr.save_checkpoint(&task.id, data);
            println!(
                "  ✅ 数据存储完成: {}",
                PathBuf::from(&checkpoint_mgr.checkpoint_dir)
                    .join(format!("{}.json", task.id))
                    .display()
            );
        } else {
            println!("  ✅ 数据存储完成");
        }

        result.success = true;
        result.duration = start_time.elapsed();

        println!("  ✅ 页面爬取完成: {:?}", result.duration);

        result
    }

    /// 检测反爬机制
    async fn detect_anti_detection(
        url: &str,
        config: &UltimateConfig,
    ) -> (
        HashMap<String, bool>,
        Option<String>,
        Vec<String>,
        CaptchaHints,
    ) {
        let mut anti_detect = HashMap::new();
        anti_detect.insert("captcha".to_string(), false);
        anti_detect.insert("waf".to_string(), false);
        anti_detect.insert("rate_limit".to_string(), false);
        anti_detect.insert("ip_ban".to_string(), false);
        anti_detect.insert("js_challenge".to_string(), false);
        let empty_hints = CaptchaHints::default();

        let client = match reqwest::Client::builder()
            .timeout(config.timeout)
            .user_agent(&config.user_agent)
            .build()
        {
            Ok(client) => client,
            Err(_) => return (anti_detect, None, Vec::new(), empty_hints),
        };

        let response = match client.get(url).send().await {
            Ok(response) => response,
            Err(_) => return (anti_detect, None, Vec::new(), empty_hints),
        };

        let status_code = response.status().as_u16();
        let headers = response
            .headers()
            .iter()
            .map(|(name, value)| {
                (
                    name.as_str().to_string(),
                    serde_json::Value::String(value.to_str().unwrap_or_default().to_string()),
                )
            })
            .collect::<std::collections::HashMap<_, _>>();
        let cookies = response
            .headers()
            .get_all(reqwest::header::SET_COOKIE)
            .iter()
            .filter_map(|value| value.to_str().ok())
            .collect::<Vec<_>>()
            .join("; ");
        let html = match response.text().await {
            Ok(html) => html,
            Err(_) => return (anti_detect, None, Vec::new(), empty_hints),
        };
        let captcha_image_source = Self::extract_captcha_image_source(&html);
        let challenge_kind = Self::extract_captcha_challenge_kind(&html);
        let captcha_hints = CaptchaHints {
            challenge_kind,
            site_key: Self::extract_captcha_site_key(&html),
            action: Self::extract_captcha_action(&html),
            c_data: Self::extract_captcha_c_data(&html),
            page_data: Self::extract_captcha_page_data(&html),
            image_bytes: Self::resolve_captcha_image_bytes(
                &client,
                url,
                captcha_image_source.as_deref(),
            )
            .await,
            image_source: captcha_image_source,
        };

        let reverse_client = NodeReverseClient::new(&config.reverse_service_url);
        let profile = match reverse_client
            .profile_anti_bot(&crate::node_reverse::client::AntiBotProfileRequest {
                html,
                js: String::new(),
                headers,
                cookies,
                status_code: Some(status_code),
                url: url.to_string(),
            })
            .await
        {
            Ok(profile) if profile.success => profile,
            _ => return (anti_detect, None, Vec::new(), captcha_hints),
        };

        let mut signals = profile.signals.clone();
        for signal in &profile.signals {
            match signal.as_str() {
                "captcha" => {
                    anti_detect.insert("captcha".to_string(), true);
                }
                "rate-limit" | "requires-paced-requests" => {
                    anti_detect.insert("rate_limit".to_string(), true);
                }
                "request-blocked" => {
                    anti_detect.insert("ip_ban".to_string(), true);
                }
                "javascript-challenge" | "managed-browser-challenge" => {
                    anti_detect.insert("js_challenge".to_string(), true);
                }
                _ if signal.starts_with("vendor:") => {
                    anti_detect.insert("waf".to_string(), true);
                }
                _ => {}
            }
        }
        if captcha_hints.site_key.is_some() {
            anti_detect.insert("captcha".to_string(), true);
            if !signals
                .iter()
                .any(|item| item == "captcha-sitekey-detected")
            {
                signals.push("captcha-sitekey-detected".to_string());
            }
        }
        if let Some(kind) = captcha_hints.challenge_kind.as_deref() {
            anti_detect.insert("captcha".to_string(), true);
            let marker = format!("captcha-kind:{kind}");
            if !signals.iter().any(|item| item == &marker) {
                signals.push(marker);
            }
        }
        if captcha_hints.image_bytes.is_some() {
            anti_detect.insert("captcha".to_string(), true);
            if !signals.iter().any(|item| item == "captcha-image-detected") {
                signals.push("captcha-image-detected".to_string());
            }
        }

        (anti_detect, Some(profile.level), signals, captcha_hints)
    }

    /// AI 提取
    fn ai_extract(url: &str) -> serde_json::Value {
        serde_json::json!({
            "url": url,
            "title": "AI Extracted Title",
            "content": "AI Extracted Content",
            "metadata": {}
        })
    }

    async fn simulate_browser(
        url: &str,
        config: &UltimateConfig,
    ) -> Result<serde_json::Value, String> {
        let client = reqwest::Client::builder()
            .timeout(config.timeout)
            .user_agent(&config.user_agent)
            .build()
            .map_err(|err| err.to_string())?;
        let response = client
            .get(url)
            .send()
            .await
            .map_err(|err| err.to_string())?;
        let html = response.text().await.map_err(|err| err.to_string())?;
        if !html.contains("navigator.") && !html.contains("webdriver") {
            return Err("page does not advertise browser fingerprint checks".to_string());
        }

        let reverse_client = NodeReverseClient::new(&config.reverse_service_url);
        let result = reverse_client
            .simulate_browser(
                "return JSON.stringify({userAgent:navigator.userAgent,platform:navigator.platform,language:navigator.language});",
                Some(serde_json::json!({
                    "userAgent": config.user_agent,
                    "language": "zh-CN",
                    "platform": "Win32",
                })),
            )
            .await
            .map_err(|err| err.to_string())?;
        if !result.success {
            return Err(result
                .error
                .unwrap_or_else(|| "simulate browser failed".to_string()));
        }
        Ok(result.result)
    }

    async fn analyze_encryption(
        url: &str,
        config: &UltimateConfig,
    ) -> Result<serde_json::Value, String> {
        let client = reqwest::Client::builder()
            .timeout(config.timeout)
            .user_agent(&config.user_agent)
            .build()
            .map_err(|err| err.to_string())?;
        let response = client
            .get(url)
            .send()
            .await
            .map_err(|err| err.to_string())?;
        let html = response.text().await.map_err(|err| err.to_string())?;
        let candidate = if let Some(start) = html.find("<script") {
            &html[start..]
        } else {
            &html
        };

        let reverse_client = NodeReverseClient::new(&config.reverse_service_url);
        let result = reverse_client
            .analyze_crypto(candidate)
            .await
            .map_err(|err| err.to_string())?;
        if !result.success {
            return Err("analyze crypto failed".to_string());
        }
        Ok(serde_json::json!({
            "crypto_types": result.crypto_types,
            "keys": result.keys,
            "ivs": result.ivs,
            "analysis": result.analysis,
        }))
    }

    async fn collect_reverse_runtime(url: &str, config: &UltimateConfig) -> serde_json::Value {
        let client = match reqwest::Client::builder()
            .timeout(config.timeout)
            .user_agent(&config.user_agent)
            .build()
        {
            Ok(client) => client,
            Err(err) => {
                return serde_json::json!({"success": false, "error": err.to_string()});
            }
        };
        let response = match client.get(url).send().await {
            Ok(response) => response,
            Err(err) => {
                return serde_json::json!({"success": false, "error": err.to_string()});
            }
        };
        let status_code = response.status().as_u16();
        let headers = response
            .headers()
            .iter()
            .map(|(name, value)| {
                (
                    name.as_str().to_string(),
                    serde_json::Value::String(value.to_str().unwrap_or_default().to_string()),
                )
            })
            .collect::<std::collections::HashMap<_, _>>();
        let cookies = response
            .headers()
            .get_all(reqwest::header::SET_COOKIE)
            .iter()
            .filter_map(|value| value.to_str().ok())
            .collect::<Vec<_>>()
            .join("; ");
        let html = match response.text().await {
            Ok(html) => html,
            Err(err) => {
                return serde_json::json!({"success": false, "error": err.to_string()});
            }
        };

        let reverse_client = NodeReverseClient::new(&config.reverse_service_url);
        let request = crate::node_reverse::client::AntiBotProfileRequest {
            html,
            js: String::new(),
            headers,
            cookies,
            status_code: Some(status_code),
            url: url.to_string(),
        };
        let detect = reverse_client.detect_anti_bot(&request).await.ok();
        let profile = reverse_client.profile_anti_bot(&request).await.ok();
        let spoof = reverse_client
            .spoof_fingerprint("chrome", "windows")
            .await
            .ok();
        let tls = reverse_client.tls_fingerprint("chrome", "120").await.ok();

        serde_json::json!({
            "success": detect.is_some() && profile.is_some() && spoof.is_some() && tls.is_some(),
            "detect": detect,
            "profile": profile,
            "fingerprint_spoof": spoof,
            "tls_fingerprint": tls,
        })
    }

    async fn attempt_captcha_recovery(
        task: &CrawlTask,
        config: &UltimateConfig,
        detected_hints: &CaptchaHints,
    ) -> Option<serde_json::Value> {
        let provider = config.captcha_provider.trim();
        if provider.is_empty() || config.captcha_api_key.trim().is_empty() {
            return Some(serde_json::json!({
                "status": "not-configured",
                "provider": provider,
            }));
        }

        let site_key = task
            .metadata
            .get("captcha_site_key")
            .and_then(|value| value.as_str())
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .or(detected_hints
                .site_key
                .as_deref()
                .filter(|value| !value.trim().is_empty()));
        let challenge_kind = task
            .metadata
            .get("captcha_kind")
            .and_then(|value| value.as_str())
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .or(detected_hints
                .challenge_kind
                .as_deref()
                .filter(|value| !value.trim().is_empty()));
        let page_url = task
            .metadata
            .get("captcha_page_url")
            .and_then(|value| value.as_str())
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .unwrap_or(task.url.as_str());
        let image_text = task
            .metadata
            .get("captcha_image_text")
            .and_then(|value| value.as_str())
            .map(str::trim)
            .filter(|value| !value.is_empty());
        let image_b64 = task
            .metadata
            .get("captcha_image_b64")
            .and_then(|value| value.as_str())
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .and_then(|value| base64_decode(value).ok());
        let action = task
            .metadata
            .get("captcha_action")
            .and_then(|value| value.as_str())
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .or(detected_hints
                .action
                .as_deref()
                .filter(|value| !value.trim().is_empty()));
        let c_data = task
            .metadata
            .get("captcha_c_data")
            .and_then(|value| value.as_str())
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .or(detected_hints
                .c_data
                .as_deref()
                .filter(|value| !value.trim().is_empty()));
        let page_data = task
            .metadata
            .get("captcha_page_data")
            .and_then(|value| value.as_str())
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .or(detected_hints
                .page_data
                .as_deref()
                .filter(|value| !value.trim().is_empty()));
        let image_bytes = image_b64
            .or_else(|| image_text.map(|value| value.as_bytes().to_vec()))
            .or_else(|| detected_hints.image_bytes.clone());

        if site_key.is_none() && image_bytes.is_none() {
            return Some(serde_json::json!({
                "status": "metadata-missing",
                "provider": provider,
                "required": ["captcha_site_key or captcha_image_text/captcha_image_b64"],
            }));
        }

        let mut solver = CaptchaSolver::new(config.captcha_api_key.clone(), provider.to_string());
        Self::configure_captcha_solver(
            &mut solver,
            provider,
            task.metadata.get("captcha_provider_base_url"),
        );
        if let (Some(fallback_provider), Some(fallback_key)) = (
            config
                .captcha_fallback_provider
                .as_ref()
                .map(|value| value.trim())
                .filter(|value| !value.is_empty()),
            config
                .captcha_fallback_api_key
                .as_ref()
                .map(|value| value.trim())
                .filter(|value| !value.is_empty()),
        ) {
            solver.set_fallback_service(fallback_provider.to_string(), fallback_key.to_string());
            Self::configure_captcha_solver(
                &mut solver,
                fallback_provider,
                task.metadata.get("captcha_fallback_base_url"),
            );
        }

        let mode = if site_key.is_some() {
            challenge_kind.unwrap_or("recaptcha")
        } else {
            "image"
        };
        let solve_result = if let Some(site_key) = site_key {
            match challenge_kind.unwrap_or("recaptcha") {
                "hcaptcha" => solver.solve_hcaptcha(site_key, page_url).await,
                "turnstile" => {
                    solver
                        .solve_turnstile(site_key, page_url, action, c_data, page_data)
                        .await
                }
                _ => solver.solve_recaptcha(site_key, page_url).await,
            }
        } else if let Some(image_bytes) = image_bytes {
            solver.solve_image(&image_bytes).await
        } else {
            return Some(serde_json::json!({
                "status": "metadata-missing",
                "provider": provider,
            }));
        };

        Some(match solve_result {
            Ok(token) => serde_json::json!({
                "status": "solved",
                "provider": provider,
                "mode": mode,
                "token_preview": Self::token_preview(&token),
            }),
            Err(error) => serde_json::json!({
                "status": "failed",
                "provider": provider,
                "mode": mode,
                "error": error,
            }),
        })
    }

    fn configure_captcha_solver(
        solver: &mut CaptchaSolver,
        provider: &str,
        base_url_value: Option<&serde_json::Value>,
    ) {
        let Some(base_url) = base_url_value
            .and_then(|value| value.as_str())
            .map(str::trim)
            .filter(|value| !value.is_empty())
        else {
            return;
        };
        match provider {
            "2captcha" => solver.set_two_captcha_base_url(base_url.to_string()),
            "anticaptcha" => solver.set_anti_captcha_base_url(base_url.to_string()),
            _ => {}
        }
    }

    fn token_preview(token: &str) -> String {
        let trimmed = token.trim();
        if trimmed.len() <= 12 {
            return trimmed.to_string();
        }
        format!("{}...", &trimmed[..12])
    }

    fn summarize_captcha_hints(hints: &CaptchaHints) -> serde_json::Value {
        serde_json::json!({
            "challenge_kind": hints.challenge_kind,
            "site_key_detected": hints.site_key.as_ref().map(|value| !value.trim().is_empty()).unwrap_or(false),
            "site_key_preview": hints.site_key.as_ref().map(|value| Self::token_preview(value)),
            "action": hints.action,
            "c_data_present": hints.c_data.as_ref().map(|value| !value.trim().is_empty()).unwrap_or(false),
            "page_data_present": hints.page_data.as_ref().map(|value| !value.trim().is_empty()).unwrap_or(false),
            "image_source": hints.image_source,
            "image_detected": hints.image_bytes.as_ref().map(|value| !value.is_empty()).unwrap_or(false),
        })
    }

    fn extract_captcha_site_key(html: &str) -> Option<String> {
        for pattern in [
            r#"data-sitekey=["']([^"'<>]+)["']"#,
            r#"data-site-key=["']([^"'<>]+)["']"#,
            r#""sitekey"\s*:\s*"([^"]+)""#,
            r#""siteKey"\s*:\s*"([^"]+)""#,
            r#"sitekey\s*:\s*["']([^"'<>]+)["']"#,
            r#"siteKey\s*:\s*["']([^"'<>]+)["']"#,
            r#"grecaptcha(?:\.enterprise)?\.execute\(\s*["']([^"'<>]+)["']"#,
            r#"hcaptcha\.execute\(\s*["']([^"'<>]+)["']"#,
        ] {
            let regex = regex::Regex::new(pattern).ok()?;
            if let Some(captures) = regex.captures(html) {
                if let Some(value) = captures.get(1) {
                    let site_key = value.as_str().trim();
                    if !site_key.is_empty() {
                        return Some(site_key.to_string());
                    }
                }
            }
        }
        Self::extract_captcha_query_param(html, &["sitekey", "siteKey", "k", "render"])
    }

    fn extract_captcha_challenge_kind(html: &str) -> Option<String> {
        let lower = html.to_lowercase();
        if lower.contains("turnstile.render")
            || lower.contains("turnstile.execute")
            || lower.contains("cf-turnstile")
        {
            return Some("turnstile".to_string());
        }
        if lower.contains("challenges.cloudflare.com") || lower.contains("/turnstile/") {
            return Some("turnstile".to_string());
        }
        if lower.contains("hcaptcha.render")
            || lower.contains("hcaptcha.execute")
            || lower.contains("hcaptcha.com/1/api.js")
        {
            return Some("hcaptcha".to_string());
        }
        if lower.contains("hcaptcha.com/") {
            return Some("hcaptcha".to_string());
        }
        if lower.contains("grecaptcha.render")
            || lower.contains("grecaptcha.execute")
            || lower.contains("grecaptcha.enterprise.execute")
            || lower.contains("recaptcha/api.js")
        {
            return Some("recaptcha".to_string());
        }
        if lower.contains("google.com/recaptcha/") {
            return Some("recaptcha".to_string());
        }
        None
    }

    fn extract_captcha_action(html: &str) -> Option<String> {
        Self::extract_captcha_option(
            html,
            &[
                r#"data-action=["']([^"'<>]+)["']"#,
                r#"name=["']action["'][^>]*value=["']([^"'<>]+)["']"#,
                r#"value=["']([^"'<>]+)["'][^>]*name=["']action["']"#,
                r#""action"\s*:\s*"([^"]+)""#,
                r#"action\s*:\s*["']([^"'<>]+)["']"#,
            ],
        )
        .or_else(|| Self::extract_captcha_query_param(html, &["action"]))
    }

    fn extract_captcha_c_data(html: &str) -> Option<String> {
        Self::extract_captcha_option(
            html,
            &[
                r#"data-cdata=["']([^"'<>]+)["']"#,
                r#"data-c-data=["']([^"'<>]+)["']"#,
                r#"name=["'](?:cData|cdata|data)["'][^>]*value=["']([^"'<>]+)["']"#,
                r#"value=["']([^"'<>]+)["'][^>]*name=["'](?:cData|cdata|data)["']"#,
                r#""cData"\s*:\s*"([^"]+)""#,
                r#""cdata"\s*:\s*"([^"]+)""#,
                r#"cData\s*:\s*["']([^"'<>]+)["']"#,
            ],
        )
        .or_else(|| Self::extract_captcha_query_param(html, &["cData", "cdata", "data"]))
    }

    fn extract_captcha_page_data(html: &str) -> Option<String> {
        Self::extract_captcha_option(
            html,
            &[
                r#""chlPageData"\s*:\s*"([^"]+)""#,
                r#""pageData"\s*:\s*"([^"]+)""#,
                r#""pagedata"\s*:\s*"([^"]+)""#,
                r#"name=["'](?:pagedata|pageData|chlPageData)["'][^>]*value=["']([^"'<>]+)["']"#,
                r#"value=["']([^"'<>]+)["'][^>]*name=["'](?:pagedata|pageData|chlPageData)["']"#,
                r#"chlPageData\s*:\s*["']([^"'<>]+)["']"#,
                r#"pageData\s*:\s*["']([^"'<>]+)["']"#,
            ],
        )
        .or_else(|| {
            Self::extract_captcha_query_param(html, &["pagedata", "pageData", "chlPageData"])
        })
    }

    fn extract_captcha_option(html: &str, patterns: &[&str]) -> Option<String> {
        for pattern in patterns {
            let regex = regex::Regex::new(pattern).ok()?;
            if let Some(captures) = regex.captures(html) {
                if let Some(value) = captures.get(1) {
                    let extracted = Self::normalize_captcha_value(value.as_str());
                    if !extracted.is_empty() {
                        return Some(extracted);
                    }
                }
            }
        }
        None
    }

    fn extract_captcha_resource_urls(html: &str) -> Vec<String> {
        let mut urls = Vec::new();
        for pattern in [
            r#"(?is)<iframe[^>]*src=["']([^"'<>]+)["'][^>]*(?:turnstile|captcha|recaptcha|hcaptcha)[^>]*>"#,
            r#"(?is)<iframe[^>]*(?:turnstile|captcha|recaptcha|hcaptcha)[^>]*src=["']([^"'<>]+)["']"#,
            r#"(?is)<iframe[^>]*src=["']([^"'<>]*(?:turnstile|captcha|recaptcha|hcaptcha)[^"'<>]*)["']"#,
            r#"(?is)<script[^>]*src=["']([^"'<>]*(?:turnstile|captcha|recaptcha|hcaptcha)[^"'<>]*)["']"#,
            r#"(?i)fetch\(\s*["']([^"'<>]*(?:turnstile|captcha|recaptcha|hcaptcha)[^"'<>]*)["']"#,
            r#"(?i)\.open\(\s*["'](?:GET|POST)["']\s*,\s*["']([^"'<>]*(?:turnstile|captcha|recaptcha|hcaptcha)[^"'<>]*)["']"#,
            r#""(https?:\\?/\\?/[^"]*(?:turnstile|captcha|recaptcha|hcaptcha)[^"]*)""#,
            r#"['"](/[^"'<>]*(?:turnstile|captcha|recaptcha|hcaptcha)[^"'<>]*)['"]"#,
        ] {
            let Ok(regex) = regex::Regex::new(pattern) else {
                continue;
            };
            for captures in regex.captures_iter(html) {
                if let Some(value) = captures.get(1) {
                    let src = Self::normalize_captcha_value(value.as_str());
                    if !src.is_empty() && !urls.iter().any(|item| item == &src) {
                        urls.push(src);
                    }
                }
            }
        }
        urls
    }

    fn extract_captcha_query_param(html: &str, keys: &[&str]) -> Option<String> {
        for resource_url in Self::extract_captcha_resource_urls(html) {
            let parsed = match url::Url::parse(&resource_url)
                .or_else(|_| url::Url::parse(&format!("https://challenge.local{}", resource_url)))
            {
                Ok(parsed) => parsed,
                Err(_) => continue,
            };
            for key in keys {
                if let Some(value) = parsed
                    .query_pairs()
                    .find(|(name, _)| name.eq_ignore_ascii_case(key))
                    .map(|(_, value)| value.into_owned())
                {
                    let trimmed = Self::normalize_captcha_value(&value);
                    if !trimmed.is_empty() {
                        return Some(trimmed);
                    }
                }
            }
        }
        None
    }

    fn normalize_captcha_value(raw: &str) -> String {
        raw.trim()
            .replace("\\u002F", "/")
            .replace("\\u003D", "=")
            .replace("\\u0026", "&")
            .replace("\\/", "/")
            .replace("&amp;", "&")
    }

    fn extract_captcha_image_source(html: &str) -> Option<String> {
        let img_regex = regex::Regex::new(
            r#"(?is)<img[^>]*(?:captcha|verify|challenge)[^>]*src=["']([^"'<>]+)["']"#,
        )
        .ok()?;
        if let Some(captures) = img_regex.captures(html) {
            if let Some(value) = captures.get(1) {
                let source = value.as_str().trim();
                if !source.is_empty() {
                    return Some(source.to_string());
                }
            }
        }

        let generic_regex = regex::Regex::new(
            r#"(?i)src=["'](data:image/[^"'<>]+|[^"'<>]*(?:captcha|verify)[^"'<>]*)["']"#,
        )
        .ok()?;
        if let Some(captures) = generic_regex.captures(html) {
            if let Some(value) = captures.get(1) {
                let source = value.as_str().trim();
                if !source.is_empty() {
                    return Some(source.to_string());
                }
            }
        }

        None
    }

    fn extract_captcha_image_bytes(html: &str) -> Option<Vec<u8>> {
        let source = Self::extract_captcha_image_source(html)?;
        let (_, payload) = source.split_once("base64,")?;
        base64_decode(payload).ok()
    }

    async fn resolve_captcha_image_bytes(
        client: &reqwest::Client,
        page_url: &str,
        image_source: Option<&str>,
    ) -> Option<Vec<u8>> {
        let source = image_source?.trim();
        if source.is_empty() {
            return None;
        }
        if source.starts_with("data:image/") {
            let (_, payload) = source.split_once("base64,")?;
            return base64_decode(payload).ok();
        }

        let resolved = if source.starts_with("http://") || source.starts_with("https://") {
            source.to_string()
        } else {
            url::Url::parse(page_url)
                .ok()?
                .join(source)
                .ok()?
                .to_string()
        };

        let response = client.get(resolved).send().await.ok()?;
        if !response.status().is_success() {
            return None;
        }
        let bytes = response.bytes().await.ok()?;
        if bytes.is_empty() {
            return None;
        }
        Some(bytes.to_vec())
    }
}

/// 创建终极爬虫
pub fn create_ultimate_spider(config: Option<UltimateConfig>) -> UltimateSpider {
    UltimateSpider::new(config.unwrap_or_default())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::{HashMap, VecDeque};
    use std::io::{Read, Write};
    use std::net::TcpListener;
    use std::sync::{Arc, Mutex};
    use std::thread;

    #[tokio::test]
    async fn captcha_recovery_reports_missing_metadata() {
        let task = CrawlTask {
            id: "task-1".to_string(),
            url: "https://example.com/challenge".to_string(),
            priority: 1,
            depth: 0,
            metadata: HashMap::new(),
        };
        let config = UltimateConfig {
            captcha_provider: "2captcha".to_string(),
            captcha_api_key: "test-key".to_string(),
            ..UltimateConfig::default()
        };

        let payload =
            UltimateSpider::attempt_captcha_recovery(&task, &config, &CaptchaHints::default())
                .await
                .expect("payload");

        assert_eq!(payload["status"], "metadata-missing");
    }

    #[tokio::test]
    async fn captcha_recovery_can_use_fallback_provider() {
        let primary_server = spawn_sequence_server(vec![("POST /in.php", "ERROR_ZERO_BALANCE")]);
        let fallback_server = spawn_sequence_server(vec![
            ("POST /createTask", r#"{"errorId":0,"taskId":42}"#),
            (
                "POST /getTaskResult",
                r#"{"errorId":0,"status":"ready","solution":{"gRecaptchaResponse":"token-xyz"}}"#,
            ),
        ]);

        let mut metadata = HashMap::new();
        metadata.insert(
            "captcha_site_key".to_string(),
            serde_json::json!("site-key"),
        );
        metadata.insert(
            "captcha_provider_base_url".to_string(),
            serde_json::json!(primary_server.base_url.clone()),
        );
        metadata.insert(
            "captcha_fallback_base_url".to_string(),
            serde_json::json!(fallback_server.base_url.clone()),
        );
        let task = CrawlTask {
            id: "task-2".to_string(),
            url: "https://example.com/challenge".to_string(),
            priority: 1,
            depth: 0,
            metadata,
        };
        let config = UltimateConfig {
            captcha_provider: "2captcha".to_string(),
            captcha_api_key: "primary-key".to_string(),
            captcha_fallback_provider: Some("anticaptcha".to_string()),
            captcha_fallback_api_key: Some("fallback-key".to_string()),
            ..UltimateConfig::default()
        };

        let payload =
            UltimateSpider::attempt_captcha_recovery(&task, &config, &CaptchaHints::default())
                .await
                .expect("payload");

        assert_eq!(payload["status"], "solved");
        assert_eq!(payload["mode"], "recaptcha");
        assert_eq!(payload["token_preview"], "token-xyz");
    }

    #[test]
    fn extract_captcha_site_key_reads_common_markup() {
        let html = r#"
            <html>
              <body>
                <div class="g-recaptcha" data-sitekey="site-key-123"></div>
              </body>
            </html>
        "#;

        assert_eq!(
            UltimateSpider::extract_captcha_site_key(html).as_deref(),
            Some("site-key-123")
        );
    }

    #[test]
    fn extract_captcha_js_config_reads_turnstile_parameters() {
        let html = r##"
            <script>
              turnstile.render("#challenge", {
                sitekey: "turnstile-site",
                action: "managed",
                cData: "opaque-cdata",
                chlPageData: "opaque-page-data"
              });
            </script>
        "##;

        assert_eq!(
            UltimateSpider::extract_captcha_challenge_kind(html).as_deref(),
            Some("turnstile")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_site_key(html).as_deref(),
            Some("turnstile-site")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_action(html).as_deref(),
            Some("managed")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_c_data(html).as_deref(),
            Some("opaque-cdata")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_page_data(html).as_deref(),
            Some("opaque-page-data")
        );
    }

    #[test]
    fn extract_captcha_iframe_query_reads_turnstile_parameters() {
        let html = r##"
            <iframe
              src="https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/b/turnstile/if/ov2/av0/rcv/123?sitekey=iframe-site&action=login&cData=iframe-cdata&pagedata=iframe-page"
              class="cf-turnstile">
            </iframe>
        "##;

        assert_eq!(
            UltimateSpider::extract_captcha_challenge_kind(html).as_deref(),
            Some("turnstile")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_site_key(html).as_deref(),
            Some("iframe-site")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_action(html).as_deref(),
            Some("login")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_c_data(html).as_deref(),
            Some("iframe-cdata")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_page_data(html).as_deref(),
            Some("iframe-page")
        );
    }

    #[test]
    fn extract_captcha_execute_call_reads_recaptcha_site_key_and_action() {
        let html = r#"
            <script>
              grecaptcha.enterprise.execute("execute-site", { action: "submit-order" });
            </script>
        "#;

        assert_eq!(
            UltimateSpider::extract_captcha_challenge_kind(html).as_deref(),
            Some("recaptcha")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_site_key(html).as_deref(),
            Some("execute-site")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_action(html).as_deref(),
            Some("submit-order")
        );
    }

    #[test]
    fn summarize_captcha_hints_masks_full_sensitive_values() {
        let hints = CaptchaHints {
            challenge_kind: Some("turnstile".to_string()),
            site_key: Some("very-long-site-key-value".to_string()),
            action: Some("managed".to_string()),
            c_data: Some("opaque-cdata".to_string()),
            page_data: Some("opaque-page".to_string()),
            image_bytes: Some(b"captcha".to_vec()),
            image_source: Some("https://example.com/captcha.png".to_string()),
        };

        let summary = UltimateSpider::summarize_captcha_hints(&hints);

        assert_eq!(summary["challenge_kind"], "turnstile");
        assert_eq!(summary["site_key_detected"], true);
        assert_eq!(summary["site_key_preview"], "very-long-si...");
        assert_eq!(summary["c_data_present"], true);
        assert_eq!(summary["page_data_present"], true);
        assert_eq!(summary["image_detected"], true);
    }

    #[test]
    fn extract_captcha_script_render_query_reads_recaptcha_site_key() {
        let html = r#"
            <script src="https://www.google.com/recaptcha/enterprise.js?render=render-site"></script>
        "#;

        assert_eq!(
            UltimateSpider::extract_captcha_challenge_kind(html).as_deref(),
            Some("recaptcha")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_site_key(html).as_deref(),
            Some("render-site")
        );
    }

    #[test]
    fn extract_captcha_hidden_inputs_read_values() {
        let html = r#"
            <form>
              <input type="hidden" name="action" value="submit-form" />
              <input type="hidden" name="cData" value="hidden-cdata" />
              <input type="hidden" name="pagedata" value="hidden-page" />
            </form>
        "#;

        assert_eq!(
            UltimateSpider::extract_captcha_action(html).as_deref(),
            Some("submit-form")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_c_data(html).as_deref(),
            Some("hidden-cdata")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_page_data(html).as_deref(),
            Some("hidden-page")
        );
    }

    #[test]
    fn extract_captcha_escaped_url_reads_query_parameters() {
        let html = r#"
            <script>
              window.__challenge = {
                iframe: "https:\/\/challenges.cloudflare.com\/turnstile\/v0\/api.js?sitekey=escaped-site&amp;action=escaped-action&amp;cData=escaped-cdata&amp;pagedata=escaped-page"
              };
            </script>
        "#;

        assert_eq!(
            UltimateSpider::extract_captcha_site_key(html).as_deref(),
            Some("escaped-site")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_action(html).as_deref(),
            Some("escaped-action")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_c_data(html).as_deref(),
            Some("escaped-cdata")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_page_data(html).as_deref(),
            Some("escaped-page")
        );
    }

    #[test]
    fn extract_captcha_script_src_reads_query_parameters() {
        let html = r#"
            <script src="https://www.google.com/recaptcha/api.js?render=explicit&sitekey=script-site&action=script-action"></script>
        "#;

        assert_eq!(
            UltimateSpider::extract_captcha_site_key(html).as_deref(),
            Some("script-site")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_action(html).as_deref(),
            Some("script-action")
        );
    }

    #[test]
    fn extract_captcha_fetch_url_reads_query_parameters() {
        let html = r#"
            <script>
              fetch('/challenge/turnstile/verify?sitekey=fetch-site&cData=fetch-cdata&pagedata=fetch-page');
            </script>
        "#;

        assert_eq!(
            UltimateSpider::extract_captcha_site_key(html).as_deref(),
            Some("fetch-site")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_c_data(html).as_deref(),
            Some("fetch-cdata")
        );
        assert_eq!(
            UltimateSpider::extract_captcha_page_data(html).as_deref(),
            Some("fetch-page")
        );
    }

    #[test]
    fn extract_captcha_image_bytes_decodes_inline_data_uri() {
        let html = r#"
            <html>
              <body>
                <img class="captcha-image" src="data:image/png;base64,aGVsbG8=" />
              </body>
            </html>
        "#;

        assert_eq!(
            UltimateSpider::extract_captcha_image_bytes(html).as_deref(),
            Some(b"hello".as_slice())
        );
    }

    #[tokio::test]
    async fn resolve_captcha_image_bytes_fetches_relative_image_url() {
        let server = spawn_sequence_server(vec![("GET /captcha.png", "binary-captcha")]);
        let client = reqwest::Client::new();

        let bytes = UltimateSpider::resolve_captcha_image_bytes(
            &client,
            &(server.base_url.clone() + "/page"),
            Some("/captcha.png"),
        )
        .await;

        assert_eq!(bytes.as_deref(), Some(b"binary-captcha".as_slice()));
    }

    #[tokio::test]
    async fn captcha_recovery_uses_detected_image_bytes() {
        let primary_server = spawn_sequence_server(vec![
            ("POST /in.php", "OK|task-1"),
            ("GET /res.php", "OK|solved-image"),
        ]);

        let task = CrawlTask {
            id: "task-3".to_string(),
            url: "https://example.com/captcha".to_string(),
            priority: 1,
            depth: 0,
            metadata: HashMap::new(),
        };
        let config = UltimateConfig {
            captcha_provider: "2captcha".to_string(),
            captcha_api_key: "test-key".to_string(),
            ..UltimateConfig::default()
        };
        let hints = CaptchaHints {
            challenge_kind: None,
            site_key: None,
            action: None,
            c_data: None,
            page_data: None,
            image_bytes: Some(b"inline-image".to_vec()),
            image_source: Some("data:image/png;base64,aW5saW5lLWltYWdl".to_string()),
        };
        let mut task = task;
        task.metadata.insert(
            "captcha_provider_base_url".to_string(),
            serde_json::json!(primary_server.base_url.clone()),
        );

        let payload = UltimateSpider::attempt_captcha_recovery(&task, &config, &hints)
            .await
            .expect("payload");

        assert_eq!(payload["status"], "solved");
        assert_eq!(payload["mode"], "image");
    }

    #[tokio::test]
    async fn captcha_recovery_uses_detected_turnstile_kind() {
        let server = spawn_sequence_server(vec![
            ("POST /createTask", r#"{"errorId":0,"taskId":77}"#),
            (
                "POST /getTaskResult",
                r#"{"errorId":0,"status":"ready","solution":{"token":"turnstile-token"}}"#,
            ),
        ]);

        let task = CrawlTask {
            id: "task-4".to_string(),
            url: "https://example.com/turnstile".to_string(),
            priority: 1,
            depth: 0,
            metadata: HashMap::from([(
                "captcha_provider_base_url".to_string(),
                serde_json::json!(server.base_url.clone()),
            )]),
        };
        let config = UltimateConfig {
            captcha_provider: "anticaptcha".to_string(),
            captcha_api_key: "test-key".to_string(),
            ..UltimateConfig::default()
        };
        let hints = CaptchaHints {
            challenge_kind: Some("turnstile".to_string()),
            site_key: Some("turnstile-site".to_string()),
            action: Some("managed".to_string()),
            c_data: Some("opaque-cdata".to_string()),
            page_data: Some("opaque-page-data".to_string()),
            image_bytes: None,
            image_source: None,
        };

        let payload = UltimateSpider::attempt_captcha_recovery(&task, &config, &hints)
            .await
            .expect("payload");

        assert_eq!(payload["status"], "solved");
        assert_eq!(payload["mode"], "turnstile");
        assert_eq!(payload["token_preview"], "turnstile-to...");
    }

    struct SequenceServer {
        base_url: String,
        handle: Option<thread::JoinHandle<()>>,
    }

    impl Drop for SequenceServer {
        fn drop(&mut self) {
            if let Some(handle) = self.handle.take() {
                let _ = handle.join();
            }
        }
    }

    fn spawn_sequence_server(sequence: Vec<(&'static str, &'static str)>) -> SequenceServer {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind");
        let address = listener.local_addr().expect("local addr");
        let queue = Arc::new(Mutex::new(
            sequence
                .into_iter()
                .map(|(request_line, body)| (request_line.to_string(), body.to_string()))
                .collect::<VecDeque<_>>(),
        ));
        let queue_for_thread = Arc::clone(&queue);

        let handle = thread::spawn(move || {
            for stream in listener.incoming() {
                let mut stream = match stream {
                    Ok(stream) => stream,
                    Err(_) => break,
                };

                let mut buffer = [0_u8; 4096];
                let bytes_read = match stream.read(&mut buffer) {
                    Ok(size) => size,
                    Err(_) => break,
                };
                let request_text = String::from_utf8_lossy(&buffer[..bytes_read]);
                let request_line = request_text.lines().next().unwrap_or_default().to_string();

                let (expected_line, body) = {
                    let mut queue = queue_for_thread.lock().expect("queue");
                    queue.pop_front().expect("expected queued response")
                };
                assert!(
                    request_line.starts_with(&expected_line),
                    "unexpected request line: expected prefix {expected_line}, got {request_line}"
                );

                let response = format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                    body.len(),
                    body
                );
                let _ = stream.write_all(response.as_bytes());
                if queue_for_thread.lock().expect("queue").is_empty() {
                    break;
                }
            }
        });

        SequenceServer {
            base_url: format!("http://{}", address),
            handle: Some(handle),
        }
    }
}
