//! 反反爬模块

use md5::{Digest, Md5};
use rand::Rng;
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

/// 反反爬处理器
pub struct AntiBotHandler {
    user_agents: Vec<String>,
    referers: Vec<String>,
    languages: Vec<String>,
}

impl AntiBotHandler {
    /// 创建反反爬处理器
    pub fn new() -> Self {
        AntiBotHandler {
            user_agents: vec![
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36".to_string(),
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36".to_string(),
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0".to_string(),
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15".to_string(),
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36".to_string(),
            ],
            referers: vec![
                "https://www.google.com/".to_string(),
                "https://www.bing.com/".to_string(),
                "https://www.baidu.com/".to_string(),
            ],
            languages: vec![
                "zh-CN,zh;q=0.9,en;q=0.8".to_string(),
                "en-US,en;q=0.9".to_string(),
                "zh-TW,zh;q=0.9".to_string(),
            ],
        }
    }

    /// 获取随机请求头
    pub fn get_random_headers(&self) -> HashMap<String, String> {
        let mut rng = rand::thread_rng();
        let mut headers = HashMap::new();

        headers.insert(
            "User-Agent".to_string(),
            self.user_agents[rng.gen_range(0..self.user_agents.len())].clone(),
        );
        headers.insert(
            "Referer".to_string(),
            self.referers[rng.gen_range(0..self.referers.len())].clone(),
        );
        headers.insert(
            "Accept-Language".to_string(),
            self.languages[rng.gen_range(0..self.languages.len())].clone(),
        );
        headers.insert(
            "Accept".to_string(),
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
                .to_string(),
        );
        headers.insert(
            "Accept-Encoding".to_string(),
            "gzip, deflate, br".to_string(),
        );
        headers.insert("Connection".to_string(), "keep-alive".to_string());
        headers.insert("Upgrade-Insecure-Requests".to_string(), "1".to_string());

        headers
    }

    /// 获取智能延迟
    pub fn get_intelligent_delay(&self, base_delay: f64) -> f64 {
        let mut rng = rand::thread_rng();

        // 基础延迟
        let mut delay = base_delay + rng.gen_range(0.0..2.0);

        // 随机添加额外延迟（30% 概率）
        if rng.gen::<f32>() < 0.3 {
            delay += rng.gen_range(1.0..3.0);
        }

        // 时间段调整（夜间增加延迟）
        let hour = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs()
            / 3600
            % 24;

        if !(6..=23).contains(&hour) {
            delay *= 1.5;
        }

        delay
    }

    /// 检查是否被封禁
    pub fn is_blocked(&self, html: &str, status_code: u16) -> bool {
        let blocked_keywords = [
            "access denied",
            "blocked",
            "captcha",
            "验证码",
            "封禁",
            "403 forbidden",
            "429 too many requests",
            "request rejected",
            "ip banned",
        ];

        let html_lower = html.to_lowercase();
        for keyword in &blocked_keywords {
            if html_lower.contains(keyword) {
                return true;
            }
        }

        if status_code == 403 || status_code == 429 {
            return true;
        }

        false
    }

    /// 绕过 Cloudflare
    pub fn bypass_cloudflare(&self) -> HashMap<String, String> {
        let mut headers = self.get_random_headers();
        headers.insert(
            "sec-ch-ua".to_string(),
            "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\"".to_string(),
        );
        headers.insert("sec-ch-ua-mobile".to_string(), "?0".to_string());
        headers.insert("sec-ch-ua-platform".to_string(), "\"Windows\"".to_string());
        headers
    }

    /// 绕过 Akamai
    pub fn bypass_akamai(&self) -> HashMap<String, String> {
        let mut headers = self.get_random_headers();
        headers.insert("X-Requested-With".to_string(), "XMLHttpRequest".to_string());
        headers
    }

    /// 生成浏览器指纹
    pub fn generate_fingerprint(&self) -> String {
        let mut hasher = Md5::new();
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        hasher.update(timestamp.to_string().as_bytes());
        format!("{:x}", hasher.finalize())
    }

    /// 轮换代理
    pub fn rotate_proxy(&self, proxy_pool: &[String]) -> Option<String> {
        if proxy_pool.is_empty() {
            return None;
        }

        let mut rng = rand::thread_rng();
        Some(proxy_pool[rng.gen_range(0..proxy_pool.len())].clone())
    }

    /// 解决验证码（需要第三方服务）
    pub fn solve_captcha(&self, captcha_image: &[u8], api_key: Option<&str>) -> Option<String> {
        // 实际实现需要调用 2Captcha 等第三方服务
        api_key.map(|_| "solved".to_string())
    }
}

impl Default for AntiBotHandler {
    fn default() -> Self {
        Self::new()
    }
}

/// Cloudflare 绕过器
pub struct CloudflareBypass {
    antibot: AntiBotHandler,
}

impl CloudflareBypass {
    pub fn new() -> Self {
        CloudflareBypass {
            antibot: AntiBotHandler::new(),
        }
    }

    pub fn get_headers(&self) -> HashMap<String, String> {
        self.antibot.bypass_cloudflare()
    }
}

impl Default for CloudflareBypass {
    fn default() -> Self {
        Self::new()
    }
}

/// Akamai 绕过器
pub struct AkamaiBypass {
    antibot: AntiBotHandler,
}

impl AkamaiBypass {
    pub fn new() -> Self {
        AkamaiBypass {
            antibot: AntiBotHandler::new(),
        }
    }

    pub fn get_headers(&self) -> HashMap<String, String> {
        self.antibot.bypass_akamai()
    }
}

impl Default for AkamaiBypass {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_random_headers() {
        let handler = AntiBotHandler::new();
        let headers = handler.get_random_headers();

        assert!(headers.contains_key("User-Agent"));
        assert!(headers.contains_key("Accept"));
    }

    #[test]
    fn test_is_blocked() {
        let handler = AntiBotHandler::new();

        assert!(handler.is_blocked("access denied", 200));
        assert!(handler.is_blocked("normal page", 403));
        assert!(!handler.is_blocked("normal page", 200));
    }

    #[test]
    fn test_intelligent_delay() {
        let handler = AntiBotHandler::new();
        let delay = handler.get_intelligent_delay(1.0);

        assert!(delay >= 1.0);
    }
}
