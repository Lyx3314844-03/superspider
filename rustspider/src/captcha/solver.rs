//! 验证码识别模块

use std::collections::BTreeMap;
use std::time::Duration;

/// 验证码解决器
pub struct CaptchaSolver {
    api_key: String,
    service: String,
    timeout: Duration,
    client: reqwest::blocking::Client,
    poll_interval: Duration,
    max_polls: usize,
    base_url: Option<String>,
}

/// 解决结果
#[derive(Debug, Clone)]
pub struct SolveResult {
    pub success: bool,
    pub text: Option<String>,
    pub error: Option<String>,
}

impl CaptchaSolver {
    /// 创建验证码解决器
    pub fn new(api_key: &str, service: &str) -> Self {
        CaptchaSolver {
            api_key: api_key.to_string(),
            service: service.to_string(),
            timeout: Duration::from_secs(30),
            client: reqwest::blocking::Client::builder()
                .timeout(Duration::from_secs(30))
                .build()
                .unwrap_or_default(),
            poll_interval: Duration::from_secs(2),
            max_polls: 30,
            base_url: None,
        }
    }

    pub fn set_polling_config(&mut self, poll_interval: Duration, max_polls: usize) {
        if poll_interval > Duration::ZERO {
            self.poll_interval = poll_interval;
        }
        if max_polls > 0 {
            self.max_polls = max_polls;
        }
    }

    pub fn set_base_url(&mut self, base_url: &str) {
        self.base_url = Some(base_url.trim_end_matches('/').to_string());
    }

    /// 解决图片验证码
    pub fn solve_image(&self, image_data: &[u8]) -> SolveResult {
        match self.service.as_str() {
            "2captcha" => self.solve_2captcha(image_data),
            "anticaptcha" => self.solve_anticaptcha(image_data),
            _ => self.solve_2captcha(image_data),
        }
    }

    /// 使用 2Captcha 解决
    fn solve_2captcha(&self, image_data: &[u8]) -> SolveResult {
        // 上传图片
        let base64_image = encode_base64(image_data);

        let mut payload = BTreeMap::new();
        payload.insert("key".to_string(), self.api_key.clone());
        payload.insert("method".to_string(), "base64".to_string());
        payload.insert("body".to_string(), base64_image);

        let resp = match self
            .client
            .post(&self.build_url("http://2captcha.com/in.php"))
            .form(&payload)
            .send()
        {
            Ok(r) => r,
            Err(e) => {
                return SolveResult {
                    success: false,
                    text: None,
                    error: Some(e.to_string()),
                }
            }
        };

        let text = resp.text().unwrap_or_default();
        let parts: Vec<&str> = text.split('|').collect();

        if parts[0] != "OK" {
            return SolveResult {
                success: false,
                text: None,
                error: Some(parts[0].to_string()),
            };
        }

        let task_id = parts[1];

        // 轮询获取结果
        for _ in 0..30 {
            std::thread::sleep(Duration::from_secs(2));

            let resp = match self
                .client
                .get(&format!(
                    "{}?key={}&action=get&id={}",
                    self.build_url("http://2captcha.com/res.php"),
                    self.api_key,
                    task_id
                ))
                .send()
            {
                Ok(r) => r,
                Err(e) => continue,
            };

            let text = resp.text().unwrap_or_default();
            let parts: Vec<&str> = text.split('|').collect();

            if parts[0] == "OK" {
                return SolveResult {
                    success: true,
                    text: Some(parts[1].to_string()),
                    error: None,
                };
            }

            if parts[0] != "CAPCHA_NOT_READY" {
                return SolveResult {
                    success: false,
                    text: None,
                    error: Some(parts[0].to_string()),
                };
            }
        }

        SolveResult {
            success: false,
            text: None,
            error: Some("Timeout".to_string()),
        }
    }

    /// 使用 Anti-Captcha 解决
    fn solve_anticaptcha(&self, image_data: &[u8]) -> SolveResult {
        let base64_image = encode_base64(image_data);

        // 创建任务
        let resp = match self
            .client
            .post(&self.build_url("https://api.anti-captcha.com/createTask"))
            .json(&serde_json::json!({
                "clientKey": self.api_key,
                "task": {
                    "type": "ImageToTextTask",
                    "body": base64_image,
                },
            }))
            .send()
        {
            Ok(r) => r,
            Err(e) => {
                return SolveResult {
                    success: false,
                    text: None,
                    error: Some(e.to_string()),
                }
            }
        };

        let result: serde_json::Value = resp.json().unwrap_or_default();

        if result["errorId"].as_i64().unwrap_or(1) != 0 {
            return SolveResult {
                success: false,
                text: None,
                error: Some(
                    result["errorDescription"]
                        .as_str()
                        .unwrap_or("Unknown error")
                        .to_string(),
                ),
            };
        }

        let task_id = result["taskId"].as_i64().unwrap_or(0);

        // 轮询获取结果
        for _ in 0..30 {
            std::thread::sleep(Duration::from_secs(2));

            let resp = match self
                .client
                .post(&self.build_url("https://api.anti-captcha.com/getTaskResult"))
                .json(&serde_json::json!({
                    "clientKey": self.api_key,
                    "taskId": task_id,
                }))
                .send()
            {
                Ok(r) => r,
                Err(e) => continue,
            };

            let result: serde_json::Value = resp.json().unwrap_or_default();

            if result["status"].as_str() == Some("ready") {
                if let Some(text) = result["solution"]["text"].as_str() {
                    return SolveResult {
                        success: true,
                        text: Some(text.to_string()),
                        error: None,
                    };
                }
            }
        }

        SolveResult {
            success: false,
            text: None,
            error: Some("Timeout".to_string()),
        }
    }

    /// 解决 reCAPTCHA
    pub fn solve_recaptcha(&self, site_key: &str, page_url: &str) -> SolveResult {
        if self.api_key.is_empty() {
            return SolveResult {
                success: false,
                text: None,
                error: Some("API key is required".to_string()),
            };
        }

        match self.service.as_str() {
            "2captcha" => {
                match self.solve_2captcha_token("userrecaptcha", site_key, page_url, "googlekey") {
                    Ok(token) => SolveResult {
                        success: true,
                        text: Some(token),
                        error: None,
                    },
                    Err(err) => SolveResult {
                        success: false,
                        text: None,
                        error: Some(err.to_string()),
                    },
                }
            }
            "anticaptcha" => {
                match self.solve_anticaptcha_token("NoCaptchaTaskProxyless", site_key, page_url) {
                    Ok(token) => SolveResult {
                        success: true,
                        text: Some(token),
                        error: None,
                    },
                    Err(err) => SolveResult {
                        success: false,
                        text: None,
                        error: Some(err.to_string()),
                    },
                }
            }
            _ => SolveResult {
                success: false,
                text: None,
                error: Some("unsupported service".to_string()),
            },
        }
    }

    /// 解决 hCaptcha
    pub fn solve_hcaptcha(&self, site_key: &str, page_url: &str) -> SolveResult {
        if self.api_key.is_empty() {
            return SolveResult {
                success: false,
                text: None,
                error: Some("API key is required".to_string()),
            };
        }

        match self.service.as_str() {
            "2captcha" => {
                match self.solve_2captcha_token("hcaptcha", site_key, page_url, "sitekey") {
                    Ok(token) => SolveResult {
                        success: true,
                        text: Some(token),
                        error: None,
                    },
                    Err(err) => SolveResult {
                        success: false,
                        text: None,
                        error: Some(err.to_string()),
                    },
                }
            }
            "anticaptcha" => {
                match self.solve_anticaptcha_token("HCaptchaTaskProxyless", site_key, page_url) {
                    Ok(token) => SolveResult {
                        success: true,
                        text: Some(token),
                        error: None,
                    },
                    Err(err) => SolveResult {
                        success: false,
                        text: None,
                        error: Some(err.to_string()),
                    },
                }
            }
            _ => SolveResult {
                success: false,
                text: None,
                error: Some("unsupported service".to_string()),
            },
        }
    }

    /// 报告错误的识别结果
    pub fn report_bad(&self, task_id: &str) -> Result<(), Box<dyn std::error::Error>> {
        // 实现报告错误识别
        Ok(())
    }

    fn solve_2captcha_token(
        &self,
        method: &str,
        site_key: &str,
        page_url: &str,
        site_key_field: &str,
    ) -> Result<String, Box<dyn std::error::Error>> {
        let submit_url = self.build_url("https://2captcha.com/in.php");
        let task_id = self
            .client
            .post(&submit_url)
            .form(&[
                ("key", self.api_key.as_str()),
                ("method", method),
                (site_key_field, site_key),
                ("pageurl", page_url),
                ("json", "1"),
            ])
            .send()?
            .json::<serde_json::Value>()?;

        if task_id["status"].as_i64().unwrap_or_default() != 1 {
            return Err(format!(
                "2captcha submit failed: {}",
                task_id["request"].as_str().unwrap_or("unknown")
            )
            .into());
        }

        let task_id = task_id["request"]
            .as_str()
            .ok_or("2captcha returned invalid task id")?;
        self.poll_2captcha_token(task_id)
    }

    fn poll_2captcha_token(&self, task_id: &str) -> Result<String, Box<dyn std::error::Error>> {
        for _ in 0..self.max_polls {
            std::thread::sleep(self.poll_interval);
            let poll_url = format!(
                "{}?key={}&action=get&id={}&json=1",
                self.build_url("https://2captcha.com/res.php"),
                self.api_key,
                task_id
            );
            let result = self
                .client
                .get(&poll_url)
                .send()?
                .json::<serde_json::Value>()?;
            if result["status"].as_i64().unwrap_or_default() == 1 {
                return Ok(result["request"].as_str().unwrap_or_default().to_string());
            }
            let request = result["request"].as_str().unwrap_or_default();
            if request != "CAPCHA_NOT_READY" {
                return Err(format!("2captcha poll failed: {request}").into());
            }
        }
        Err("2captcha solve timeout".into())
    }

    fn solve_anticaptcha_token(
        &self,
        task_type: &str,
        site_key: &str,
        page_url: &str,
    ) -> Result<String, Box<dyn std::error::Error>> {
        let create_url = self.build_url("https://api.anti-captcha.com/createTask");
        let result = self
            .client
            .post(&create_url)
            .json(&serde_json::json!({
                "clientKey": self.api_key,
                "task": {
                    "type": task_type,
                    "websiteURL": page_url,
                    "websiteKey": site_key
                }
            }))
            .send()?
            .json::<serde_json::Value>()?;

        if result["errorId"].as_i64().unwrap_or(1) != 0 {
            return Err(result["errorDescription"]
                .as_str()
                .unwrap_or("anti-captcha create task failed")
                .to_string()
                .into());
        }
        let task_id = result["taskId"]
            .as_i64()
            .ok_or("anti-captcha returned invalid task id")?;
        self.poll_anticaptcha_token(task_id)
    }

    fn poll_anticaptcha_token(&self, task_id: i64) -> Result<String, Box<dyn std::error::Error>> {
        let get_url = self.build_url("https://api.anti-captcha.com/getTaskResult");
        for _ in 0..self.max_polls {
            std::thread::sleep(self.poll_interval);
            let result = self
                .client
                .post(&get_url)
                .json(&serde_json::json!({
                    "clientKey": self.api_key,
                    "taskId": task_id
                }))
                .send()?
                .json::<serde_json::Value>()?;

            if result["errorId"].as_i64().unwrap_or(1) != 0 {
                return Err(result["errorDescription"]
                    .as_str()
                    .unwrap_or("anti-captcha poll failed")
                    .to_string()
                    .into());
            }
            if result["status"].as_str() == Some("ready") {
                let solution = &result["solution"];
                let token = solution["gRecaptchaResponse"]
                    .as_str()
                    .or_else(|| solution["token"].as_str())
                    .unwrap_or_default();
                if !token.is_empty() {
                    return Ok(token.to_string());
                }
            }
        }
        Err("anti-captcha solve timeout".into())
    }

    fn build_url(&self, default_url: &str) -> String {
        if let Some(base) = &self.base_url {
            if default_url.contains("/in.php") {
                return format!("{base}/in.php");
            }
            if default_url.contains("/res.php") {
                return format!("{base}/res.php");
            }
            if default_url.contains("/createTask") {
                return format!("{base}/createTask");
            }
            if default_url.contains("/getTaskResult") {
                return format!("{base}/getTaskResult");
            }
        }
        default_url.to_string()
    }
}

fn encode_base64(input: &[u8]) -> String {
    const TABLE: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut output = String::with_capacity(input.len().div_ceil(3) * 4);
    let mut chunks = input.chunks_exact(3);
    for chunk in &mut chunks {
        let value = ((chunk[0] as u32) << 16) | ((chunk[1] as u32) << 8) | chunk[2] as u32;
        output.push(TABLE[((value >> 18) & 0x3f) as usize] as char);
        output.push(TABLE[((value >> 12) & 0x3f) as usize] as char);
        output.push(TABLE[((value >> 6) & 0x3f) as usize] as char);
        output.push(TABLE[(value & 0x3f) as usize] as char);
    }

    let remainder = chunks.remainder();
    if !remainder.is_empty() {
        let first = remainder[0] as u32;
        output.push(TABLE[((first >> 2) & 0x3f) as usize] as char);
        if remainder.len() == 1 {
            output.push(TABLE[((first & 0x03) << 4) as usize] as char);
            output.push('=');
            output.push('=');
        } else {
            let second = remainder[1] as u32;
            output.push(TABLE[(((first & 0x03) << 4) | ((second >> 4) & 0x0f)) as usize] as char);
            output.push(TABLE[((second & 0x0f) << 2) as usize] as char);
            output.push('=');
        }
    }

    output
}

/// Cloudflare 绕过器
pub struct CloudflareBypass {
    client: reqwest::blocking::Client,
}

impl CloudflareBypass {
    pub fn new() -> Self {
        CloudflareBypass {
            client: reqwest::blocking::Client::builder()
                .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                .build()
                .unwrap_or_default(),
        }
    }

    pub fn get_token(&self, url: &str) -> Option<String> {
        // 实现 Cloudflare 绕过逻辑
        None
    }

    pub fn solve_challenge(&self, html: &str) -> Option<String> {
        // 解析 JavaScript 挑战
        None
    }
}

impl Default for CloudflareBypass {
    fn default() -> Self {
        Self::new()
    }
}

/// Akamai 绕过器
pub struct AkamaiBypass {
    client: reqwest::blocking::Client,
}

impl AkamaiBypass {
    pub fn new() -> Self {
        AkamaiBypass {
            client: reqwest::blocking::Client::builder()
                .build()
                .unwrap_or_default(),
        }
    }

    pub fn get_sensor_data(&self, url: &str) -> Option<std::collections::HashMap<String, String>> {
        // 实现 Akamai 绕过逻辑
        None
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
    use std::io::{Read, Write};
    use std::net::TcpListener;
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::sync::Arc;
    use std::thread;

    struct MockServer {
        addr: String,
        shutdown: Arc<AtomicBool>,
        handle: Option<thread::JoinHandle<()>>,
    }

    impl Drop for MockServer {
        fn drop(&mut self) {
            self.shutdown.store(true, Ordering::SeqCst);
            let _ = std::net::TcpStream::connect(&self.addr);
            if let Some(handle) = self.handle.take() {
                let _ = handle.join();
            }
        }
    }

    fn start_mock_server(handler: fn(&str) -> String) -> MockServer {
        let listener = TcpListener::bind("127.0.0.1:0").expect("listener");
        listener.set_nonblocking(true).expect("nonblocking");
        let addr = listener.local_addr().expect("addr");
        let shutdown = Arc::new(AtomicBool::new(false));
        let flag = shutdown.clone();
        let handle = thread::spawn(move || {
            while !flag.load(Ordering::SeqCst) {
                match listener.accept() {
                    Ok((mut stream, _)) => {
                        let mut buffer = [0_u8; 8192];
                        let size = stream.read(&mut buffer).unwrap_or(0);
                        let request = String::from_utf8_lossy(&buffer[..size]).to_string();
                        let body = handler(&request);
                        let response = format!(
                            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                            body.len(),
                            body
                        );
                        let _ = stream.write_all(response.as_bytes());
                        let _ = stream.flush();
                    }
                    Err(err) if err.kind() == std::io::ErrorKind::WouldBlock => {
                        thread::sleep(Duration::from_millis(20));
                    }
                    Err(_) => break,
                }
            }
        });
        MockServer {
            addr: addr.to_string(),
            shutdown,
            handle: Some(handle),
        }
    }

    #[test]
    fn test_captcha_solver() {
        let solver = CaptchaSolver::new("test-key", "2captcha");
        // 实际测试需要有效的 API key 和图片数据
    }

    #[test]
    fn solve_recaptcha_with_2captcha() {
        let server = start_mock_server(|request| {
            if request.starts_with("POST /in.php") {
                r#"{"status":1,"request":"task-1"}"#.to_string()
            } else {
                r#"{"status":1,"request":"recaptcha-token"}"#.to_string()
            }
        });
        let mut solver = CaptchaSolver::new("demo-key", "2captcha");
        solver.set_base_url(&format!("http://{}", server.addr));
        solver.set_polling_config(Duration::from_millis(1), 2);

        let result = solver.solve_recaptcha("site-key", "https://example.com");
        assert!(result.success);
        assert_eq!(result.text.as_deref(), Some("recaptcha-token"));
    }

    #[test]
    fn solve_hcaptcha_with_anticaptcha() {
        let server = start_mock_server(|request| {
            if request.starts_with("POST /createTask") {
                r#"{"errorId":0,"taskId":42}"#.to_string()
            } else {
                r#"{"errorId":0,"status":"ready","solution":{"gRecaptchaResponse":"hcaptcha-token"}}"#.to_string()
            }
        });
        let mut solver = CaptchaSolver::new("demo-key", "anticaptcha");
        solver.set_base_url(&format!("http://{}", server.addr));
        solver.set_polling_config(Duration::from_millis(1), 2);

        let result = solver.solve_hcaptcha("site-key", "https://example.com");
        assert!(result.success);
        assert_eq!(result.text.as_deref(), Some("hcaptcha-token"));
    }
}
