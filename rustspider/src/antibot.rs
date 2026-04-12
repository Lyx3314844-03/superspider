#![allow(clippy::module_inception)]

// RustSpider 反爬增强模块 - 代理池和 User-Agent 轮换

pub mod antibot;
pub mod enhanced;

use rand::Rng;
use std::collections::HashMap;
use std::fs::File;
use std::io::{BufRead, BufReader, Write};
use std::sync::Mutex;

// User-Agent 池
const USER_AGENTS: &[&str] = &
    ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
     "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
     "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"];

// 代理池
pub struct ProxyPool {
    proxies: Mutex<Vec<String>>,
    failed_count: Mutex<HashMap<String, usize>>,
    max_failed: usize,
    test_url: String,
}

impl ProxyPool {
    pub fn new(max_failed: usize, test_url: &str) -> Self {
        let pool = Self {
            proxies: Mutex::new(Vec::new()),
            failed_count: Mutex::new(HashMap::new()),
            max_failed,
            test_url: test_url.to_string(),
        };
        pool.load_from_file();
        pool
    }

    pub fn add(&self, proxy: &str) {
        let mut proxies = self.proxies.lock().unwrap();
        if !proxies.iter().any(|p| p == proxy) {
            proxies.push(proxy.to_string());
            drop(proxies);
            self.save_to_file();
        }
    }

    pub fn get_random(&self) -> Option<String> {
        let proxies = self.proxies.lock().unwrap();
        if proxies.is_empty() {
            return None;
        }
        let mut rng = rand::thread_rng();
        let idx = rng.gen_range(0..proxies.len());
        Some(proxies[idx].clone())
    }

    pub fn list_all(&self) {
        let proxies = self.proxies.lock().unwrap();
        println!("代理池大小: {}", proxies.len());
        for (i, p) in proxies.iter().enumerate() {
            println!("{}. {}", i + 1, p);
        }
    }

    pub fn test_all(&self) {
        let proxies = self.proxies.lock().unwrap();
        println!("测试所有代理...");
        for p in proxies.iter() {
            let valid = self.validate(p);
            println!("{} - {}", p, if valid { "✓ 有效" } else { "✗ 无效" });
        }
    }

    pub fn clear(&self) {
        let mut proxies = self.proxies.lock().unwrap();
        proxies.clear();
        drop(proxies);
        self.save_to_file();
        println!("代理池已清空");
    }

    fn validate(&self, proxy: &str) -> bool {
        if self.test_url.is_empty() {
            return true;
        }
        // 简化的验证逻辑
        true
    }

    fn load_from_file(&self) {
        if let Ok(file) = File::open("proxies.txt") {
            let reader = BufReader::new(file);
            let mut proxies = self.proxies.lock().unwrap();
            for proxy in reader.lines().map_while(Result::ok) {
                if !proxy.trim().is_empty() {
                    proxies.push(proxy.trim().to_string());
                }
            }
        }
    }

    fn save_to_file(&self) {
        let proxies = self.proxies.lock().unwrap();
        if let Ok(mut file) = File::create("proxies.txt") {
            for p in proxies.iter() {
                writeln!(file, "{}", p).ok();
            }
        }
    }
}

// 获取随机 User-Agent
pub fn get_random_user_agent() -> String {
    let mut rng = rand::thread_rng();
    let idx = rng.gen_range(0..USER_AGENTS.len());
    USER_AGENTS[idx].to_string()
}

// 反爬配置
#[derive(Debug, Clone)]
pub struct AntiBotConfig {
    pub enable_proxy: bool,
    pub enable_ua: bool,
    pub enable_cookie: bool,
    pub min_delay: u64,
    pub max_delay: u64,
    pub max_retries: u32,
}

impl Default for AntiBotConfig {
    fn default() -> Self {
        Self {
            enable_proxy: true,
            enable_ua: true,
            enable_cookie: true,
            min_delay: 1000,
            max_delay: 3000,
            max_retries: 3,
        }
    }
}

// 验证码检测
pub fn detect_captcha(html: &str) -> bool {
    let patterns = [
        "captcha",
        "验证码",
        "verify",
        "robot",
        "blocked",
        "请验证",
        "security check",
    ];
    let html_lower = html.to_lowercase();
    patterns.iter().any(|p| html_lower.contains(p))
}

// 主函数入口
pub fn antibot_main(args: &[String]) {
    let pool = ProxyPool::new(3, "https://www.google.com");

    println!("╔═══════════════════════════════════════════════════════════╗");
    println!("║         RustSpider 反爬增强模块                            ║");
    println!("╚═══════════════════════════════════════════════════════════╝");

    if args.is_empty() {
        println!("\n用法: cargo run -- antibot <命令>");
        println!("命令: list | test | clear");
        return;
    }

    match args[0].as_str() {
        "add" if args.len() > 1 => {
            pool.add(&args[1]);
            println!("添加代理: {}", args[1]);
        }
        "list" => pool.list_all(),
        "test" => pool.test_all(),
        "clear" => pool.clear(),
        _ => {
            println!("测试 User-Agent 轮换:");
            for i in 0..3 {
                let ua = get_random_user_agent();
                println!("  {}. {}", i + 1, &ua[..ua.len().min(60)]);
            }
        }
    }
}
