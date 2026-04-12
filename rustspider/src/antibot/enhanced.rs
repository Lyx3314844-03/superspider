//! 增强的反爬模块
//! 提供 Cloudflare/Akamai 绕过、验证码破解、浏览器指纹等功能

use md5::{Digest, Md5};
use rand::Rng;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use tokio::time::sleep;

/// User-Agent 轮换器（本地定义）
pub struct UserAgentRotator {
    user_agents: Vec<String>,
}

impl UserAgentRotator {
    pub fn new() -> Self {
        Self {
            user_agents: vec![
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36".to_string(),
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36".to_string(),
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
                    .to_string(),
            ],
        }
    }

    pub fn get_random_user_agent(&self) -> String {
        let mut rng = rand::thread_rng();
        self.user_agents[rng.gen_range(0..self.user_agents.len())].clone()
    }
}

impl Default for UserAgentRotator {
    fn default() -> Self {
        Self::new()
    }
}

/// Cloudflare 绕过器
pub struct CloudflareBypass {
    ua_rotator: UserAgentRotator,
}

impl CloudflareBypass {
    pub fn new() -> Self {
        Self {
            ua_rotator: UserAgentRotator::new(),
        }
    }

    /// 获取绕过 Cloudflare 的请求头
    pub fn get_cloudflare_headers(&self) -> HashMap<String, String> {
        let mut headers = HashMap::new();
        headers.insert(
            "User-Agent".to_string(),
            self.ua_rotator.get_random_user_agent(),
        );
        headers.insert(
            "Accept".to_string(),
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
                .to_string(),
        );
        headers.insert(
            "Accept-Language".to_string(),
            "en-US,en;q=0.9,zh-CN;q=0.8".to_string(),
        );
        headers.insert(
            "Accept-Encoding".to_string(),
            "gzip, deflate, br".to_string(),
        );
        headers.insert("Connection".to_string(), "keep-alive".to_string());
        headers.insert("Upgrade-Insecure-Requests".to_string(), "1".to_string());
        headers.insert("Sec-Fetch-Dest".to_string(), "document".to_string());
        headers.insert("Sec-Fetch-Mode".to_string(), "navigate".to_string());
        headers.insert("Sec-Fetch-Site".to_string(), "none".to_string());
        headers.insert("Sec-Fetch-User".to_string(), "?1".to_string());
        headers.insert(
            "Sec-Ch-Ua".to_string(),
            r#""Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120""#.to_string(),
        );
        headers.insert("Sec-Ch-Ua-Mobile".to_string(), "?0".to_string());
        headers.insert("Sec-Ch-Ua-Platform".to_string(), r#""Windows""#.to_string());
        headers.insert("Cache-Control".to_string(), "max-age=0".to_string());
        headers
    }

    /// 检测 Cloudflare 挑战
    pub fn detect_cloudflare(&self, html: &str, status_code: u16) -> bool {
        let indicators = vec![
            "cf-chl-bypass",
            "jschl_vc",
            "cf-wrapper",
            "cloudflare",
            "checking your browser",
        ];

        let html_lower = html.to_lowercase();
        for indicator in indicators {
            if html_lower.contains(indicator) {
                return true;
            }
        }

        status_code == 403 || status_code == 503
    }
}

impl Default for CloudflareBypass {
    fn default() -> Self {
        Self::new()
    }
}

/// Akamai 绕过器
pub struct AkamaiBypass {
    ua_rotator: UserAgentRotator,
}

impl AkamaiBypass {
    pub fn new() -> Self {
        Self {
            ua_rotator: UserAgentRotator::new(),
        }
    }

    /// 获取绕过 Akamai 的请求头
    pub fn get_akamai_headers(&self) -> HashMap<String, String> {
        let mut headers = HashMap::new();
        headers.insert(
            "User-Agent".to_string(),
            self.ua_rotator.get_random_user_agent(),
        );
        headers.insert(
            "Accept".to_string(),
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
                .to_string(),
        );
        headers.insert(
            "Accept-Language".to_string(),
            "en-US,en;q=0.9,zh-CN;q=0.8".to_string(),
        );
        headers.insert("X-Requested-With".to_string(), "XMLHttpRequest".to_string());
        headers.insert("Sec-Fetch-Dest".to_string(), "empty".to_string());
        headers.insert("Sec-Fetch-Mode".to_string(), "cors".to_string());
        headers.insert("Sec-Fetch-Site".to_string(), "same-origin".to_string());
        headers
    }

    /// 检测 Akamai 拦截
    pub fn detect_akamai(&self, html: &str, status_code: u16) -> bool {
        let indicators = vec![
            "ak_bmsc",
            "bm_sz",
            "abck",
            "akamai",
            "bot manager",
            "access denied",
        ];

        let html_lower = html.to_lowercase();
        for indicator in indicators {
            if html_lower.contains(indicator) {
                return true;
            }
        }

        status_code == 403
    }
}

impl Default for AkamaiBypass {
    fn default() -> Self {
        Self::new()
    }
}

/// 验证码解决器
pub struct CaptchaSolver {
    client: reqwest::Client,
    api_key: String,
    service: String,
    fallback_api_key: Option<String>,
    fallback_service: Option<String>,
    two_captcha_base_url: String,
    anti_captcha_base_url: String,
    poll_interval: Duration,
    max_polls: usize,
}

#[derive(Clone)]
struct SiteChallengeRequest {
    kind: String,
    site_key: String,
    page_url: String,
    action: Option<String>,
    c_data: Option<String>,
    page_data: Option<String>,
}

impl CaptchaSolver {
    pub fn new(api_key: String, service: String) -> Self {
        Self {
            client: reqwest::Client::new(),
            api_key,
            service,
            fallback_api_key: None,
            fallback_service: None,
            two_captcha_base_url: "https://2captcha.com".to_string(),
            anti_captcha_base_url: "https://api.anti-captcha.com".to_string(),
            poll_interval: Duration::from_secs(2),
            max_polls: 15,
        }
    }

    pub fn set_two_captcha_base_url(&mut self, base_url: impl Into<String>) {
        self.two_captcha_base_url = base_url.into();
    }

    pub fn set_anti_captcha_base_url(&mut self, base_url: impl Into<String>) {
        self.anti_captcha_base_url = base_url.into();
    }

    pub fn set_poll_config(&mut self, poll_interval: Duration, max_polls: usize) {
        self.poll_interval = poll_interval;
        self.max_polls = max_polls.max(1);
    }

    pub fn set_fallback_service(&mut self, service: impl Into<String>, api_key: impl Into<String>) {
        self.fallback_service = Some(service.into());
        self.fallback_api_key = Some(api_key.into());
    }

    /// 解决图片验证码（调用第三方 API）
    pub async fn solve_image(&self, image_data: &[u8]) -> Result<String, String> {
        let primary = match self.service.as_str() {
            "2captcha" => self.solve_with_2captcha(image_data).await,
            "anticaptcha" => self.solve_with_anticaptcha(image_data).await,
            _ => Err(format!("不支持的验证码服务: {}", self.service)),
        };
        self.recover_with_fallback(primary, image_data, None).await
    }

    async fn recover_with_fallback(
        &self,
        primary: Result<String, String>,
        image_data: &[u8],
        challenge: Option<SiteChallengeRequest>,
    ) -> Result<String, String> {
        match primary {
            Ok(value) => Ok(value),
            Err(error) => {
                if !self.should_try_fallback(&error) {
                    return Err(error);
                }
                let Some(fallback_solver) = self.fallback_solver() else {
                    return Err(error);
                };
                let fallback_result = match challenge {
                    Some(challenge) => match fallback_solver.service.as_str() {
                        "2captcha" => {
                            fallback_solver
                                .solve_site_challenge_with_2captcha(&challenge)
                                .await
                        }
                        "anticaptcha" => {
                            fallback_solver
                                .solve_site_challenge_with_anticaptcha(&challenge)
                                .await
                        }
                        _ => Err(format!("不支持的验证码服务: {}", fallback_solver.service)),
                    },
                    None => match fallback_solver.service.as_str() {
                        "2captcha" => fallback_solver.solve_with_2captcha(image_data).await,
                        "anticaptcha" => fallback_solver.solve_with_anticaptcha(image_data).await,
                        _ => Err(format!("不支持的验证码服务: {}", fallback_solver.service)),
                    },
                };
                fallback_result
                    .map_err(|fallback_error| format!("{error}; fallback failed: {fallback_error}"))
            }
        }
    }

    /// 解决 reCAPTCHA
    pub async fn solve_recaptcha(&self, site_key: &str, page_url: &str) -> Result<String, String> {
        if self.api_key.trim().is_empty() {
            return Err("验证码服务 API key 不能为空".to_string());
        }
        if site_key.trim().is_empty() || page_url.trim().is_empty() {
            return Err("site_key 和 page_url 不能为空".to_string());
        }

        self.solve_site_challenge_request(SiteChallengeRequest {
            kind: "recaptcha".to_string(),
            site_key: site_key.to_string(),
            page_url: page_url.to_string(),
            action: None,
            c_data: None,
            page_data: None,
        })
        .await
    }

    pub async fn solve_hcaptcha(&self, site_key: &str, page_url: &str) -> Result<String, String> {
        if self.api_key.trim().is_empty() {
            return Err("验证码服务 API key 不能为空".to_string());
        }
        if site_key.trim().is_empty() || page_url.trim().is_empty() {
            return Err("site_key 和 page_url 不能为空".to_string());
        }

        self.solve_site_challenge_request(SiteChallengeRequest {
            kind: "hcaptcha".to_string(),
            site_key: site_key.to_string(),
            page_url: page_url.to_string(),
            action: None,
            c_data: None,
            page_data: None,
        })
        .await
    }

    pub async fn solve_turnstile(
        &self,
        site_key: &str,
        page_url: &str,
        action: Option<&str>,
        c_data: Option<&str>,
        page_data: Option<&str>,
    ) -> Result<String, String> {
        if self.api_key.trim().is_empty() {
            return Err("验证码服务 API key 不能为空".to_string());
        }
        if site_key.trim().is_empty() || page_url.trim().is_empty() {
            return Err("site_key 和 page_url 不能为空".to_string());
        }

        self.solve_site_challenge_request(SiteChallengeRequest {
            kind: "turnstile".to_string(),
            site_key: site_key.to_string(),
            page_url: page_url.to_string(),
            action: action.map(ToOwned::to_owned),
            c_data: c_data.map(ToOwned::to_owned),
            page_data: page_data.map(ToOwned::to_owned),
        })
        .await
    }

    async fn solve_site_challenge_request(
        &self,
        challenge: SiteChallengeRequest,
    ) -> Result<String, String> {
        let primary = match self.service.as_str() {
            "2captcha" => self.solve_site_challenge_with_2captcha(&challenge).await,
            "anticaptcha" => self.solve_site_challenge_with_anticaptcha(&challenge).await,
            _ => Err(format!("不支持的验证码服务: {}", self.service)),
        };
        self.recover_with_fallback(primary, &[], Some(challenge))
            .await
    }

    async fn solve_with_2captcha(&self, image_data: &[u8]) -> Result<String, String> {
        if self.api_key.trim().is_empty() {
            return Err("2Captcha API key 不能为空".to_string());
        }
        if image_data.is_empty() {
            return Err("图片数据不能为空".to_string());
        }

        let body = base64_encode(image_data);
        let response_text = self
            .client
            .post(format!(
                "{}/in.php",
                self.two_captcha_base_url.trim_end_matches('/')
            ))
            .form(&[
                ("key", self.api_key.as_str()),
                ("method", "base64"),
                ("body", body.as_str()),
                ("json", "0"),
            ])
            .send()
            .await
            .map_err(|err| err.to_string())?
            .text()
            .await
            .map_err(|err| err.to_string())?;

        let task_id = parse_2captcha_ok_response(&response_text)?;
        self.poll_2captcha_result(&task_id).await
    }

    async fn solve_with_anticaptcha(&self, image_data: &[u8]) -> Result<String, String> {
        if self.api_key.trim().is_empty() {
            return Err("Anti-Captcha API key 不能为空".to_string());
        }
        if image_data.is_empty() {
            return Err("图片数据不能为空".to_string());
        }

        let payload = json!({
            "clientKey": self.api_key,
            "task": {
                "type": "ImageToTextTask",
                "body": base64_encode(image_data),
            }
        });

        let response: Value = self
            .client
            .post(format!(
                "{}/createTask",
                self.anti_captcha_base_url.trim_end_matches('/')
            ))
            .json(&payload)
            .send()
            .await
            .map_err(|err| err.to_string())?
            .json()
            .await
            .map_err(|err| err.to_string())?;

        let task_id = parse_anticaptcha_task_id(&response)?;
        self.poll_anticaptcha_image_result(task_id).await
    }

    async fn solve_recaptcha_with_2captcha(
        &self,
        site_key: &str,
        page_url: &str,
    ) -> Result<String, String> {
        let response_text = self
            .client
            .post(format!(
                "{}/in.php",
                self.two_captcha_base_url.trim_end_matches('/')
            ))
            .form(&[
                ("key", self.api_key.as_str()),
                ("method", "userrecaptcha"),
                ("googlekey", site_key),
                ("pageurl", page_url),
                ("json", "0"),
            ])
            .send()
            .await
            .map_err(|err| err.to_string())?
            .text()
            .await
            .map_err(|err| err.to_string())?;

        let task_id = parse_2captcha_ok_response(&response_text)?;
        self.poll_2captcha_result(&task_id).await
    }

    async fn solve_recaptcha_with_anticaptcha(
        &self,
        site_key: &str,
        page_url: &str,
    ) -> Result<String, String> {
        let payload = json!({
            "clientKey": self.api_key,
            "task": {
                "type": "NoCaptchaTaskProxyless",
                "websiteURL": page_url,
                "websiteKey": site_key,
            }
        });

        let response: Value = self
            .client
            .post(format!(
                "{}/createTask",
                self.anti_captcha_base_url.trim_end_matches('/')
            ))
            .json(&payload)
            .send()
            .await
            .map_err(|err| err.to_string())?
            .json()
            .await
            .map_err(|err| err.to_string())?;

        let task_id = parse_anticaptcha_task_id(&response)?;
        self.poll_anticaptcha_recaptcha_result(task_id).await
    }

    async fn solve_site_challenge_with_2captcha(
        &self,
        challenge: &SiteChallengeRequest,
    ) -> Result<String, String> {
        let method = match challenge.kind.as_str() {
            "recaptcha" => "userrecaptcha",
            "hcaptcha" => "hcaptcha",
            "turnstile" => "turnstile",
            other => return Err(format!("不支持的站点验证码类型: {}", other)),
        };

        let mut form = vec![
            ("key", self.api_key.as_str()),
            ("method", method),
            ("sitekey", challenge.site_key.as_str()),
            ("pageurl", challenge.page_url.as_str()),
            ("json", "0"),
        ];
        if let Some(action) = challenge.action.as_deref() {
            form.push(("action", action));
        }
        if let Some(c_data) = challenge.c_data.as_deref() {
            form.push(("data", c_data));
        }
        if let Some(page_data) = challenge.page_data.as_deref() {
            form.push(("pagedata", page_data));
        }

        let response_text = self
            .client
            .post(format!(
                "{}/in.php",
                self.two_captcha_base_url.trim_end_matches('/')
            ))
            .form(&form)
            .send()
            .await
            .map_err(|err| err.to_string())?
            .text()
            .await
            .map_err(|err| err.to_string())?;

        let task_id = parse_2captcha_ok_response(&response_text)?;
        self.poll_2captcha_result(&task_id).await
    }

    async fn solve_site_challenge_with_anticaptcha(
        &self,
        challenge: &SiteChallengeRequest,
    ) -> Result<String, String> {
        let task_type = match challenge.kind.as_str() {
            "recaptcha" => "NoCaptchaTaskProxyless",
            "hcaptcha" => "HCaptchaTaskProxyless",
            "turnstile" => "TurnstileTaskProxyless",
            other => return Err(format!("不支持的站点验证码类型: {}", other)),
        };

        let mut task = json!({
            "type": task_type,
            "websiteURL": challenge.page_url,
            "websiteKey": challenge.site_key,
        });
        if let Some(action) = challenge.action.as_deref() {
            task["action"] = json!(action);
        }
        if let Some(c_data) = challenge.c_data.as_deref() {
            task["cData"] = json!(c_data);
        }
        if let Some(page_data) = challenge.page_data.as_deref() {
            task["chlPageData"] = json!(page_data);
        }

        let response: Value = self
            .client
            .post(format!(
                "{}/createTask",
                self.anti_captcha_base_url.trim_end_matches('/')
            ))
            .json(&json!({
                "clientKey": self.api_key,
                "task": task,
            }))
            .send()
            .await
            .map_err(|err| err.to_string())?
            .json()
            .await
            .map_err(|err| err.to_string())?;

        let task_id = parse_anticaptcha_task_id(&response)?;
        self.poll_anticaptcha_site_challenge_result(task_id).await
    }

    async fn poll_2captcha_result(&self, task_id: &str) -> Result<String, String> {
        for _ in 0..self.max_polls {
            sleep(self.poll_interval).await;

            let response_text = self
                .client
                .get(format!(
                    "{}/res.php",
                    self.two_captcha_base_url.trim_end_matches('/')
                ))
                .query(&[
                    ("key", self.api_key.as_str()),
                    ("action", "get"),
                    ("id", task_id),
                    ("json", "0"),
                ])
                .send()
                .await
                .map_err(|err| err.to_string())?
                .text()
                .await
                .map_err(|err| err.to_string())?;

            match parse_2captcha_poll_response(&response_text) {
                Ok(Some(text)) => return Ok(text),
                Ok(None) => continue,
                Err(err) => return Err(err),
            }
        }

        Err("2Captcha 轮询超时".to_string())
    }

    async fn poll_anticaptcha_image_result(&self, task_id: i64) -> Result<String, String> {
        for _ in 0..self.max_polls {
            sleep(self.poll_interval).await;

            let response: Value = self
                .client
                .post(format!(
                    "{}/getTaskResult",
                    self.anti_captcha_base_url.trim_end_matches('/')
                ))
                .json(&json!({
                    "clientKey": self.api_key,
                    "taskId": task_id,
                }))
                .send()
                .await
                .map_err(|err| err.to_string())?
                .json()
                .await
                .map_err(|err| err.to_string())?;

            match parse_anticaptcha_text_result(&response)? {
                Some(text) => return Ok(text),
                None => continue,
            }
        }

        Err("Anti-Captcha 轮询超时".to_string())
    }

    async fn poll_anticaptcha_recaptcha_result(&self, task_id: i64) -> Result<String, String> {
        for _ in 0..self.max_polls {
            sleep(self.poll_interval).await;

            let response: Value = self
                .client
                .post(format!(
                    "{}/getTaskResult",
                    self.anti_captcha_base_url.trim_end_matches('/')
                ))
                .json(&json!({
                    "clientKey": self.api_key,
                    "taskId": task_id,
                }))
                .send()
                .await
                .map_err(|err| err.to_string())?
                .json()
                .await
                .map_err(|err| err.to_string())?;

            match parse_anticaptcha_recaptcha_result(&response)? {
                Some(token) => return Ok(token),
                None => continue,
            }
        }

        Err("Anti-Captcha reCAPTCHA 轮询超时".to_string())
    }

    async fn poll_anticaptcha_site_challenge_result(&self, task_id: i64) -> Result<String, String> {
        for _ in 0..self.max_polls {
            sleep(self.poll_interval).await;

            let response: Value = self
                .client
                .post(format!(
                    "{}/getTaskResult",
                    self.anti_captcha_base_url.trim_end_matches('/')
                ))
                .json(&json!({
                    "clientKey": self.api_key,
                    "taskId": task_id,
                }))
                .send()
                .await
                .map_err(|err| err.to_string())?
                .json()
                .await
                .map_err(|err| err.to_string())?;

            match parse_anticaptcha_site_challenge_result(&response)? {
                Some(token) => return Ok(token),
                None => continue,
            }
        }

        Err("Anti-Captcha 站点验证码轮询超时".to_string())
    }

    fn fallback_solver(&self) -> Option<Self> {
        let service = self.fallback_service.as_ref()?.trim();
        let api_key = self.fallback_api_key.as_ref()?.trim();
        if service.is_empty() || api_key.is_empty() {
            return None;
        }

        Some(Self {
            client: self.client.clone(),
            api_key: api_key.to_string(),
            service: service.to_string(),
            fallback_api_key: None,
            fallback_service: None,
            two_captcha_base_url: self.two_captcha_base_url.clone(),
            anti_captcha_base_url: self.anti_captcha_base_url.clone(),
            poll_interval: self.poll_interval,
            max_polls: self.max_polls,
        })
    }

    fn should_try_fallback(&self, error: &str) -> bool {
        let normalized = error.trim().to_lowercase();
        !normalized.is_empty()
            && !normalized.contains("不能为空")
            && !normalized.contains("不支持")
            && !normalized.contains("site_key")
            && !normalized.contains("page_url")
    }
}

fn parse_2captcha_ok_response(response_text: &str) -> Result<String, String> {
    let trimmed = response_text.trim();
    if let Some(task_id) = trimmed.strip_prefix("OK|") {
        if task_id.trim().is_empty() {
            return Err("2Captcha 返回了空任务 ID".to_string());
        }
        return Ok(task_id.trim().to_string());
    }
    Err(trimmed.to_string())
}

fn parse_2captcha_poll_response(response_text: &str) -> Result<Option<String>, String> {
    let trimmed = response_text.trim();
    if trimmed == "CAPCHA_NOT_READY" || trimmed == "CAPTCHA_NOT_READY" {
        return Ok(None);
    }
    if let Some(solution) = trimmed.strip_prefix("OK|") {
        return Ok(Some(solution.trim().to_string()));
    }
    Err(trimmed.to_string())
}

fn parse_anticaptcha_task_id(response: &Value) -> Result<i64, String> {
    if response["errorId"].as_i64().unwrap_or(1) != 0 {
        return Err(response["errorDescription"]
            .as_str()
            .unwrap_or("Anti-Captcha 请求失败")
            .to_string());
    }
    response["taskId"]
        .as_i64()
        .filter(|task_id| *task_id > 0)
        .ok_or_else(|| "Anti-Captcha 未返回有效 taskId".to_string())
}

fn parse_anticaptcha_text_result(response: &Value) -> Result<Option<String>, String> {
    if response["errorId"].as_i64().unwrap_or(0) != 0 {
        return Err(response["errorDescription"]
            .as_str()
            .unwrap_or("Anti-Captcha 结果查询失败")
            .to_string());
    }

    match response["status"].as_str() {
        Some("processing") => Ok(None),
        Some("ready") => response["solution"]["text"]
            .as_str()
            .map(|text| Some(text.to_string()))
            .ok_or_else(|| "Anti-Captcha 未返回文本结果".to_string()),
        Some(status) => Err(format!("未知的 Anti-Captcha 状态: {}", status)),
        None => Err("Anti-Captcha 响应缺少 status".to_string()),
    }
}

fn parse_anticaptcha_recaptcha_result(response: &Value) -> Result<Option<String>, String> {
    if response["errorId"].as_i64().unwrap_or(0) != 0 {
        return Err(response["errorDescription"]
            .as_str()
            .unwrap_or("Anti-Captcha reCAPTCHA 查询失败")
            .to_string());
    }

    match response["status"].as_str() {
        Some("processing") => Ok(None),
        Some("ready") => response["solution"]["gRecaptchaResponse"]
            .as_str()
            .map(|text| Some(text.to_string()))
            .ok_or_else(|| "Anti-Captcha 未返回 gRecaptchaResponse".to_string()),
        Some(status) => Err(format!("未知的 Anti-Captcha 状态: {}", status)),
        None => Err("Anti-Captcha 响应缺少 status".to_string()),
    }
}

fn parse_anticaptcha_site_challenge_result(response: &Value) -> Result<Option<String>, String> {
    if response["errorId"].as_i64().unwrap_or(0) != 0 {
        return Err(response["errorDescription"]
            .as_str()
            .unwrap_or("Anti-Captcha 站点验证码查询失败")
            .to_string());
    }

    match response["status"].as_str() {
        Some("processing") => Ok(None),
        Some("ready") => response["solution"]["gRecaptchaResponse"]
            .as_str()
            .or_else(|| response["solution"]["token"].as_str())
            .map(|text| Some(text.to_string()))
            .ok_or_else(|| "Anti-Captcha 未返回站点验证码 token".to_string()),
        Some(status) => Err(format!("未知的 Anti-Captcha 状态: {}", status)),
        None => Err("Anti-Captcha 响应缺少 status".to_string()),
    }
}

fn base64_encode(data: &[u8]) -> String {
    const TABLE: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    if data.is_empty() {
        return String::new();
    }

    let mut output = String::with_capacity(data.len().div_ceil(3) * 4);
    let mut index = 0;
    while index < data.len() {
        let b0 = data[index];
        let b1 = if index + 1 < data.len() {
            data[index + 1]
        } else {
            0
        };
        let b2 = if index + 2 < data.len() {
            data[index + 2]
        } else {
            0
        };

        output.push(TABLE[(b0 >> 2) as usize] as char);
        output.push(TABLE[((b0 & 0b0000_0011) << 4 | (b1 >> 4)) as usize] as char);

        if index + 1 < data.len() {
            output.push(TABLE[((b1 & 0b0000_1111) << 2 | (b2 >> 6)) as usize] as char);
        } else {
            output.push('=');
        }

        if index + 2 < data.len() {
            output.push(TABLE[(b2 & 0b0011_1111) as usize] as char);
        } else {
            output.push('=');
        }

        index += 3;
    }
    output
}

pub(crate) fn base64_decode(input: &str) -> Result<Vec<u8>, String> {
    let trimmed = input.trim();
    if trimmed.is_empty() {
        return Ok(Vec::new());
    }

    let mut bytes = Vec::with_capacity(trimmed.len() / 4 * 3);
    let mut chunk = [0u8; 4];
    let mut chunk_len = 0usize;

    for ch in trimmed.bytes() {
        if matches!(ch, b' ' | b'\n' | b'\r' | b'\t') {
            continue;
        }

        chunk[chunk_len] = ch;
        chunk_len += 1;
        if chunk_len != 4 {
            continue;
        }

        let a = decode_base64_char(chunk[0])?;
        let b = decode_base64_char(chunk[1])?;
        let c = if chunk[2] == b'=' {
            None
        } else {
            Some(decode_base64_char(chunk[2])?)
        };
        let d = if chunk[3] == b'=' {
            None
        } else {
            Some(decode_base64_char(chunk[3])?)
        };

        bytes.push((a << 2) | (b >> 4));
        if let Some(c) = c {
            bytes.push(((b & 0b0000_1111) << 4) | (c >> 2));
            if let Some(d) = d {
                bytes.push(((c & 0b0000_0011) << 6) | d);
            }
        }

        chunk_len = 0;
    }

    if chunk_len != 0 {
        return Err("base64 输入长度非法".to_string());
    }

    Ok(bytes)
}

fn decode_base64_char(ch: u8) -> Result<u8, String> {
    match ch {
        b'A'..=b'Z' => Ok(ch - b'A'),
        b'a'..=b'z' => Ok(ch - b'a' + 26),
        b'0'..=b'9' => Ok(ch - b'0' + 52),
        b'+' => Ok(62),
        b'/' => Ok(63),
        _ => Err(format!("非法 base64 字符: {}", ch as char)),
    }
}

/// 浏览器指纹生成器
pub struct BrowserFingerprint {
    resolutions: Vec<String>,
    timezones: Vec<String>,
    locales: Vec<String>,
    platforms: Vec<String>,
}

impl BrowserFingerprint {
    pub fn new() -> Self {
        Self {
            resolutions: vec![
                "1920x1080".to_string(),
                "1366x768".to_string(),
                "1536x864".to_string(),
                "1440x900".to_string(),
                "2560x1440".to_string(),
            ],
            timezones: vec![
                "Asia/Shanghai".to_string(),
                "America/New_York".to_string(),
                "Europe/London".to_string(),
                "Asia/Tokyo".to_string(),
            ],
            locales: vec![
                "zh-CN".to_string(),
                "en-US".to_string(),
                "en-GB".to_string(),
            ],
            platforms: vec![
                "Win32".to_string(),
                "MacIntel".to_string(),
                "Linux x86_64".to_string(),
            ],
        }
    }

    /// 生成完整的浏览器指纹
    pub fn generate_fingerprint(&self) -> BrowserFingerprintData {
        let mut rng = rand::thread_rng();

        BrowserFingerprintData {
            user_agent: self.get_random_user_agent(),
            screen: self.resolutions[rng.gen_range(0..self.resolutions.len())].clone(),
            timezone: self.timezones[rng.gen_range(0..self.timezones.len())].clone(),
            locale: self.locales[rng.gen_range(0..self.locales.len())].clone(),
            platform: self.platforms[rng.gen_range(0..self.platforms.len())].clone(),
            webdriver: false,
            canvas_hash: self.generate_canvas_hash(),
        }
    }

    /// 生成隐身请求头
    pub fn generate_stealth_headers(&self) -> HashMap<String, String> {
        let mut headers = HashMap::new();
        headers.insert("User-Agent".to_string(), self.get_random_user_agent());
        headers.insert(
            "Accept".to_string(),
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
                .to_string(),
        );
        headers.insert(
            "Accept-Language".to_string(),
            "zh-CN,zh;q=0.9,en;q=0.8".to_string(),
        );
        headers.insert(
            "Accept-Encoding".to_string(),
            "gzip, deflate, br".to_string(),
        );
        headers.insert("Connection".to_string(), "keep-alive".to_string());
        headers.insert("Upgrade-Insecure-Requests".to_string(), "1".to_string());
        headers.insert("Sec-Fetch-Dest".to_string(), "document".to_string());
        headers.insert("Sec-Fetch-Mode".to_string(), "navigate".to_string());
        headers.insert("Sec-Fetch-Site".to_string(), "none".to_string());
        headers.insert("Sec-Fetch-User".to_string(), "?1".to_string());
        headers.insert(
            "Sec-Ch-Ua".to_string(),
            r#""Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120""#.to_string(),
        );
        headers.insert("Sec-Ch-Ua-Mobile".to_string(), "?0".to_string());
        headers.insert("Sec-Ch-Ua-Platform".to_string(), r#""Windows""#.to_string());
        headers.insert("DNT".to_string(), "1".to_string());
        headers
    }

    fn get_random_user_agent(&self) -> String {
        let rotator = UserAgentRotator::new();
        rotator.get_random_user_agent()
    }

    fn generate_canvas_hash(&self) -> String {
        let mut rng = rand::thread_rng();
        let data = format!(
            "canvas_{}_{}",
            rng.gen_range(0..10000),
            self.get_timestamp()
        );
        let mut hasher = Md5::new();
        hasher.update(data.as_bytes());
        format!("{:x}", hasher.finalize())
    }

    fn get_timestamp(&self) -> u64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs()
    }
}

impl Default for BrowserFingerprint {
    fn default() -> Self {
        Self::new()
    }
}

/// 浏览器指纹数据
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BrowserFingerprintData {
    pub user_agent: String,
    pub screen: String,
    pub timezone: String,
    pub locale: String,
    pub platform: String,
    pub webdriver: bool,
    pub canvas_hash: String,
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::VecDeque;
    use std::env;
    use std::io::{Read, Write};
    use std::net::TcpListener;
    use std::sync::{Arc, Mutex};
    use std::thread;

    #[test]
    fn test_base64_encode_matches_expected_output() {
        assert_eq!(base64_encode(b"hello"), "aGVsbG8=");
        assert_eq!(base64_encode(b""), "");
    }

    #[test]
    fn test_parse_2captcha_submission_response() {
        let task_id = parse_2captcha_ok_response("OK|123456").expect("task id");
        assert_eq!(task_id, "123456");
        assert_eq!(
            parse_2captcha_ok_response("ERROR_ZERO_BALANCE").unwrap_err(),
            "ERROR_ZERO_BALANCE"
        );
    }

    #[test]
    fn test_parse_2captcha_poll_response() {
        assert_eq!(
            parse_2captcha_poll_response("CAPCHA_NOT_READY").expect("pending"),
            None
        );
        assert_eq!(
            parse_2captcha_poll_response("OK|solved").expect("solved"),
            Some("solved".to_string())
        );
    }

    #[test]
    fn test_parse_anticaptcha_task_and_results() {
        let create_response = json!({
            "errorId": 0,
            "taskId": 789,
        });
        assert_eq!(parse_anticaptcha_task_id(&create_response).unwrap(), 789);

        let text_ready = json!({
            "errorId": 0,
            "status": "ready",
            "solution": {
                "text": "captcha-text"
            }
        });
        assert_eq!(
            parse_anticaptcha_text_result(&text_ready).unwrap(),
            Some("captcha-text".to_string())
        );

        let recaptcha_ready = json!({
            "errorId": 0,
            "status": "ready",
            "solution": {
                "gRecaptchaResponse": "token-123"
            }
        });
        assert_eq!(
            parse_anticaptcha_recaptcha_result(&recaptcha_ready).unwrap(),
            Some("token-123".to_string())
        );

        let turnstile_ready = json!({
            "errorId": 0,
            "status": "ready",
            "solution": {
                "token": "turnstile-token"
            }
        });
        assert_eq!(
            parse_anticaptcha_site_challenge_result(&turnstile_ready).unwrap(),
            Some("turnstile-token".to_string())
        );
    }

    #[tokio::test]
    async fn test_solve_image_with_2captcha_local_server() {
        let server = spawn_sequence_server(vec![
            ("POST /in.php", "OK|task-1"),
            ("GET /res.php", "CAPCHA_NOT_READY"),
            ("GET /res.php", "OK|solved-image"),
        ]);

        let mut solver = CaptchaSolver::new("test-key".to_string(), "2captcha".to_string());
        solver.set_two_captcha_base_url(server.base_url.clone());
        solver.set_poll_config(Duration::from_millis(5), 3);

        let solved = solver
            .solve_image(b"image-bytes")
            .await
            .expect("should solve");
        assert_eq!(solved, "solved-image");
    }

    #[tokio::test]
    async fn test_solve_recaptcha_with_anticaptcha_local_server() {
        let server = spawn_sequence_server(vec![
            ("POST /createTask", r#"{"errorId":0,"taskId":42}"#),
            (
                "POST /getTaskResult",
                r#"{"errorId":0,"status":"processing"}"#,
            ),
            (
                "POST /getTaskResult",
                r#"{"errorId":0,"status":"ready","solution":{"gRecaptchaResponse":"token-xyz"}}"#,
            ),
        ]);

        let mut solver = CaptchaSolver::new("test-key".to_string(), "anticaptcha".to_string());
        solver.set_anti_captcha_base_url(server.base_url.clone());
        solver.set_poll_config(Duration::from_millis(5), 3);

        let solved = solver
            .solve_recaptcha("site-key", "https://example.com/challenge")
            .await
            .expect("should solve");
        assert_eq!(solved, "token-xyz");
    }

    #[tokio::test]
    async fn test_solve_image_falls_back_to_secondary_provider() {
        let primary_server = spawn_sequence_server(vec![("POST /in.php", "ERROR_ZERO_BALANCE")]);
        let fallback_server = spawn_sequence_server(vec![
            ("POST /createTask", r#"{"errorId":0,"taskId":11}"#),
            (
                "POST /getTaskResult",
                r#"{"errorId":0,"status":"ready","solution":{"text":"fallback-text"}}"#,
            ),
        ]);

        let mut solver = CaptchaSolver::new("primary-key".to_string(), "2captcha".to_string());
        solver.set_two_captcha_base_url(primary_server.base_url.clone());
        solver.set_anti_captcha_base_url(fallback_server.base_url.clone());
        solver.set_fallback_service("anticaptcha", "fallback-key");
        solver.set_poll_config(Duration::from_millis(5), 2);

        let solved = solver
            .solve_image(b"image-bytes")
            .await
            .expect("should solve via fallback");
        assert_eq!(solved, "fallback-text");
    }

    #[tokio::test]
    async fn test_solve_hcaptcha_with_2captcha_local_server() {
        let server = spawn_sequence_server(vec![
            ("POST /in.php", "OK|task-h"),
            ("GET /res.php", "OK|hcaptcha-token"),
        ]);

        let mut solver = CaptchaSolver::new("test-key".to_string(), "2captcha".to_string());
        solver.set_two_captcha_base_url(server.base_url.clone());
        solver.set_poll_config(Duration::from_millis(5), 2);

        let solved = solver
            .solve_hcaptcha("site-key", "https://example.com/hcaptcha")
            .await
            .expect("should solve hcaptcha");
        assert_eq!(solved, "hcaptcha-token");
    }

    #[tokio::test]
    async fn test_solve_turnstile_with_anticaptcha_local_server() {
        let server = spawn_sequence_server(vec![
            ("POST /createTask", r#"{"errorId":0,"taskId":77}"#),
            (
                "POST /getTaskResult",
                r#"{"errorId":0,"status":"ready","solution":{"token":"turnstile-token"}}"#,
            ),
        ]);

        let mut solver = CaptchaSolver::new("test-key".to_string(), "anticaptcha".to_string());
        solver.set_anti_captcha_base_url(server.base_url.clone());
        solver.set_poll_config(Duration::from_millis(5), 2);

        let solved = solver
            .solve_turnstile(
                "site-key",
                "https://example.com/turnstile",
                Some("managed"),
                Some("cdata"),
                Some("page-data"),
            )
            .await
            .expect("should solve turnstile");
        assert_eq!(solved, "turnstile-token");
    }

    #[tokio::test]
    async fn live_solve_recaptcha_with_2captcha_if_configured() {
        if !live_captcha_enabled() {
            eprintln!("skipping live recaptcha smoke: RUSTSPIDER_LIVE_CAPTCHA_SMOKE not enabled");
            return;
        }
        let Some(api_key) = first_non_blank_env(&["TWO_CAPTCHA_API_KEY", "CAPTCHA_API_KEY"]) else {
            eprintln!("skipping live recaptcha smoke: no 2captcha api key configured");
            return;
        };
        let Some(site_key) = env_non_blank("RUSTSPIDER_LIVE_RECAPTCHA_SITE_KEY") else {
            eprintln!("skipping live recaptcha smoke: site key missing");
            return;
        };
        let Some(page_url) = env_non_blank("RUSTSPIDER_LIVE_RECAPTCHA_PAGE_URL") else {
            eprintln!("skipping live recaptcha smoke: page url missing");
            return;
        };

        let solver = CaptchaSolver::new(api_key, "2captcha".to_string());
        let solved = solver
            .solve_recaptcha(&site_key, &page_url)
            .await
            .expect("live recaptcha should return a token");
        assert!(
            !solved.trim().is_empty(),
            "live recaptcha returned an empty token"
        );
    }

    #[tokio::test]
    async fn live_solve_hcaptcha_with_2captcha_if_configured() {
        if !live_captcha_enabled() {
            eprintln!("skipping live hcaptcha smoke: RUSTSPIDER_LIVE_CAPTCHA_SMOKE not enabled");
            return;
        }
        let Some(api_key) = first_non_blank_env(&["TWO_CAPTCHA_API_KEY", "CAPTCHA_API_KEY"]) else {
            eprintln!("skipping live hcaptcha smoke: no 2captcha api key configured");
            return;
        };
        let Some(site_key) = env_non_blank("RUSTSPIDER_LIVE_HCAPTCHA_SITE_KEY") else {
            eprintln!("skipping live hcaptcha smoke: site key missing");
            return;
        };
        let Some(page_url) = env_non_blank("RUSTSPIDER_LIVE_HCAPTCHA_PAGE_URL") else {
            eprintln!("skipping live hcaptcha smoke: page url missing");
            return;
        };

        let solver = CaptchaSolver::new(api_key, "2captcha".to_string());
        let solved = solver
            .solve_hcaptcha(&site_key, &page_url)
            .await
            .expect("live hcaptcha should return a token");
        assert!(
            !solved.trim().is_empty(),
            "live hcaptcha returned an empty token"
        );
    }

    #[tokio::test]
    async fn live_solve_turnstile_with_anticaptcha_if_configured() {
        if !live_captcha_enabled() {
            eprintln!("skipping live turnstile smoke: RUSTSPIDER_LIVE_CAPTCHA_SMOKE not enabled");
            return;
        }
        let Some(api_key) = env_non_blank("ANTI_CAPTCHA_API_KEY") else {
            eprintln!("skipping live turnstile smoke: anti-captcha api key missing");
            return;
        };
        let Some(site_key) = env_non_blank("RUSTSPIDER_LIVE_TURNSTILE_SITE_KEY") else {
            eprintln!("skipping live turnstile smoke: site key missing");
            return;
        };
        let Some(page_url) = env_non_blank("RUSTSPIDER_LIVE_TURNSTILE_PAGE_URL") else {
            eprintln!("skipping live turnstile smoke: page url missing");
            return;
        };

        let solver = CaptchaSolver::new(api_key, "anticaptcha".to_string());
        let action = env_non_blank("RUSTSPIDER_LIVE_TURNSTILE_ACTION");
        let c_data = env_non_blank("RUSTSPIDER_LIVE_TURNSTILE_CDATA");
        let page_data = env_non_blank("RUSTSPIDER_LIVE_TURNSTILE_PAGEDATA");
        let solved = solver
            .solve_turnstile(
                &site_key,
                &page_url,
                action.as_deref(),
                c_data.as_deref(),
                page_data.as_deref(),
            )
            .await
            .expect("live turnstile should return a token");
        assert!(
            !solved.trim().is_empty(),
            "live turnstile returned an empty token"
        );
    }

    struct SequenceServer {
        base_url: String,
        handle: Option<thread::JoinHandle<()>>,
    }

    fn live_captcha_enabled() -> bool {
        matches!(
            env::var("RUSTSPIDER_LIVE_CAPTCHA_SMOKE").ok().as_deref(),
            Some("1") | Some("true") | Some("TRUE") | Some("True")
        )
    }

    fn env_non_blank(name: &str) -> Option<String> {
        env::var(name).ok().and_then(|value| {
            let trimmed = value.trim();
            if trimmed.is_empty() {
                None
            } else {
                Some(trimmed.to_string())
            }
        })
    }

    fn first_non_blank_env(names: &[&str]) -> Option<String> {
        names.iter().find_map(|name| env_non_blank(name))
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
            while let Some((expected_request_line, body)) =
                queue_for_thread.lock().expect("lock").pop_front()
            {
                let (mut stream, _) = listener.accept().expect("accept");

                let mut buffer = [0_u8; 4096];
                let bytes_read = stream.read(&mut buffer).expect("read");
                let request = String::from_utf8_lossy(&buffer[..bytes_read]);
                let first_line = request.lines().next().unwrap_or_default().to_string();
                assert!(
                    first_line.starts_with(&expected_request_line),
                    "expected request line starting with {expected_request_line:?}, got {first_line:?}"
                );

                let response = format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                    body.len(),
                    body
                );
                stream.write_all(response.as_bytes()).expect("write");
                stream.flush().expect("flush");
            }
        });

        SequenceServer {
            base_url: format!("http://{}", address),
            handle: Some(handle),
        }
    }
}
