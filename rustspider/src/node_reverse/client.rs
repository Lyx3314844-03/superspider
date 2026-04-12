//! Node.js 逆向服务客户端
//! 为 Rust Spider 提供统一的逆向能力

use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;

const DEFAULT_BASE_URL: &str = "http://localhost:3000";

/// Node.js 逆向客户端
pub struct NodeReverseClient {
    base_url: String,
    http_client: Client,
}

impl NodeReverseClient {
    /// 创建新的客户端
    pub fn new(base_url: impl Into<String>) -> Self {
        let base_url = base_url.into();
        let base_url = if base_url.is_empty() {
            DEFAULT_BASE_URL.to_string()
        } else {
            base_url
        };

        let http_client = Client::builder()
            .timeout(Duration::from_secs(30))
            .build()
            .unwrap_or_default();

        Self {
            base_url,
            http_client,
        }
    }

    /// 健康检查
    pub async fn health_check(&self) -> Result<bool, Box<dyn std::error::Error>> {
        let resp = self
            .http_client
            .get(format!("{}/health", self.base_url))
            .send()
            .await?;

        Ok(resp.status().is_success())
    }

    /// 分析加密算法
    pub async fn analyze_crypto(
        &self,
        code: &str,
    ) -> Result<CryptoAnalyzeResponse, Box<dyn std::error::Error>> {
        let request = CryptoAnalyzeRequest {
            code: code.to_string(),
        };

        let response = self
            .http_client
            .post(format!("{}/api/crypto/analyze", self.base_url))
            .json(&request)
            .send()
            .await?
            .json::<CryptoAnalyzeResponse>()
            .await?;

        Ok(response)
    }

    /// 执行加密
    pub async fn encrypt(
        &self,
        algorithm: &str,
        data: &str,
        key: &str,
        iv: Option<&str>,
        mode: Option<&str>,
    ) -> Result<CryptoResponse, Box<dyn std::error::Error>> {
        let request = CryptoEncryptRequest {
            algorithm: algorithm.to_string(),
            data: data.to_string(),
            key: key.to_string(),
            iv: iv.map(String::from),
            mode: mode.map(String::from),
        };

        let response = self
            .http_client
            .post(format!("{}/api/crypto/encrypt", self.base_url))
            .json(&request)
            .send()
            .await?
            .json::<CryptoResponse>()
            .await?;

        Ok(response)
    }

    /// 执行解密
    pub async fn decrypt(
        &self,
        algorithm: &str,
        data: &str,
        key: &str,
        iv: Option<&str>,
        mode: Option<&str>,
    ) -> Result<CryptoResponse, Box<dyn std::error::Error>> {
        let request = CryptoEncryptRequest {
            algorithm: algorithm.to_string(),
            data: data.to_string(),
            key: key.to_string(),
            iv: iv.map(String::from),
            mode: mode.map(String::from),
        };

        let response = self
            .http_client
            .post(format!("{}/api/crypto/decrypt", self.base_url))
            .json(&request)
            .send()
            .await?
            .json::<CryptoResponse>()
            .await?;

        Ok(response)
    }

    /// 执行 JavaScript 代码
    pub async fn execute_js(
        &self,
        code: &str,
        context: Option<serde_json::Value>,
        timeout: Option<u64>,
    ) -> Result<ExecuteJSResponse, Box<dyn std::error::Error>> {
        let mut payload = serde_json::json!({
            "code": code
        });

        if let Some(ctx) = context {
            payload["context"] = ctx;
        }
        if let Some(t) = timeout {
            payload["timeout"] = serde_json::json!(t);
        }

        let response = self
            .http_client
            .post(format!("{}/api/js/execute", self.base_url))
            .json(&payload)
            .send()
            .await?
            .json::<ExecuteJSResponse>()
            .await?;

        Ok(response)
    }

    /// AST 语法分析
    pub async fn analyze_ast(
        &self,
        code: &str,
        analysis: Option<Vec<&str>>,
    ) -> Result<ASTAnalyzeResponse, Box<dyn std::error::Error>> {
        let analysis = analysis.unwrap_or(vec!["crypto", "obfuscation", "anti-debug"]);

        let payload = serde_json::json!({
            "code": code,
            "analysis": analysis
        });

        let response = self
            .http_client
            .post(format!("{}/api/ast/analyze", self.base_url))
            .json(&payload)
            .send()
            .await?
            .json::<ASTAnalyzeResponse>()
            .await?;

        Ok(response)
    }

    /// 模拟浏览器环境
    pub async fn simulate_browser(
        &self,
        code: &str,
        browser_config: Option<serde_json::Value>,
    ) -> Result<BrowserSimulateResponse, Box<dyn std::error::Error>> {
        let mut payload = serde_json::json!({
            "code": code
        });

        if let Some(config) = browser_config {
            payload["browserConfig"] = config;
        }

        let response = self
            .http_client
            .post(format!("{}/api/browser/simulate", self.base_url))
            .json(&payload)
            .send()
            .await?
            .json::<BrowserSimulateResponse>()
            .await?;

        Ok(response)
    }

    /// 调用 JavaScript 函数
    pub async fn call_function(
        &self,
        function_name: &str,
        args: Vec<serde_json::Value>,
        code: &str,
    ) -> Result<FunctionCallResponse, Box<dyn std::error::Error>> {
        let payload = serde_json::json!({
            "functionName": function_name,
            "args": args,
            "code": code
        });

        let response = self
            .http_client
            .post(format!("{}/api/function/call", self.base_url))
            .json(&payload)
            .send()
            .await?
            .json::<FunctionCallResponse>()
            .await?;

        Ok(response)
    }

    /// 检测页面中的反爬特征
    pub async fn detect_anti_bot(
        &self,
        request: &AntiBotProfileRequest,
    ) -> Result<AntiBotProfileResponse, Box<dyn std::error::Error>> {
        let response = self
            .http_client
            .post(format!("{}/api/anti-bot/detect", self.base_url))
            .json(request)
            .send()
            .await?
            .json::<AntiBotProfileResponse>()
            .await?;

        Ok(response)
    }

    /// 生成完整的反爬画像、请求蓝图和规避计划
    pub async fn profile_anti_bot(
        &self,
        request: &AntiBotProfileRequest,
    ) -> Result<AntiBotProfileResponse, Box<dyn std::error::Error>> {
        let response = self
            .http_client
            .post(format!("{}/api/anti-bot/profile", self.base_url))
            .json(request)
            .send()
            .await?
            .json::<AntiBotProfileResponse>()
            .await?;

        Ok(response)
    }

    pub async fn spoof_fingerprint(
        &self,
        browser: &str,
        platform: &str,
    ) -> Result<FingerprintSpoofResponse, Box<dyn std::error::Error>> {
        let payload = serde_json::json!({
            "browser": browser,
            "platform": platform
        });

        let response = self
            .http_client
            .post(format!("{}/api/fingerprint/spoof", self.base_url))
            .json(&payload)
            .send()
            .await?
            .json::<FingerprintSpoofResponse>()
            .await?;

        Ok(response)
    }

    pub async fn tls_fingerprint(
        &self,
        browser: &str,
        version: &str,
    ) -> Result<TLSFingerprintResponse, Box<dyn std::error::Error>> {
        let payload = serde_json::json!({
            "browser": browser,
            "version": version
        });

        let response = self
            .http_client
            .post(format!("{}/api/tls/fingerprint", self.base_url))
            .json(&payload)
            .send()
            .await?
            .json::<TLSFingerprintResponse>()
            .await?;

        Ok(response)
    }
}

impl Default for NodeReverseClient {
    fn default() -> Self {
        Self::new(DEFAULT_BASE_URL)
    }
}

// ==================== 请求/响应类型定义 ====================

#[derive(Serialize)]
pub struct CryptoAnalyzeRequest {
    pub code: String,
}

#[derive(Deserialize, Serialize, Debug)]
pub struct CryptoAnalyzeResponse {
    pub success: bool,
    #[serde(default)]
    pub crypto_types: Vec<CryptoType>,
    #[serde(default)]
    pub keys: Vec<String>,
    #[serde(default)]
    pub ivs: Vec<String>,
    pub analysis: Option<serde_json::Value>,
}

#[derive(Deserialize, Serialize, Debug)]
pub struct CryptoType {
    pub name: String,
    pub confidence: f64,
    #[serde(default)]
    pub modes: Vec<String>,
}

#[derive(Serialize)]
pub struct CryptoEncryptRequest {
    pub algorithm: String,
    pub data: String,
    pub key: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub iv: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub mode: Option<String>,
}

#[derive(Deserialize, Serialize, Debug)]
pub struct CryptoResponse {
    pub success: bool,
    #[serde(default)]
    pub encrypted: Option<String>,
    #[serde(default)]
    pub decrypted: Option<String>,
    #[serde(default)]
    pub hash: Option<String>,
    #[serde(default)]
    pub error: Option<String>,
}

#[derive(Deserialize, Serialize, Debug)]
pub struct ExecuteJSResponse {
    pub success: bool,
    pub result: serde_json::Value,
    #[serde(default)]
    pub error: Option<String>,
}

#[derive(Deserialize, Serialize, Debug)]
pub struct ASTAnalyzeResponse {
    pub success: bool,
    pub results: serde_json::Value,
}

#[derive(Deserialize, Serialize, Debug)]
pub struct BrowserSimulateResponse {
    pub success: bool,
    pub result: serde_json::Value,
    #[serde(default)]
    pub cookies: String,
    #[serde(default)]
    pub error: Option<String>,
}

#[derive(Deserialize, Serialize, Debug)]
pub struct FunctionCallResponse {
    pub success: bool,
    pub result: serde_json::Value,
    #[serde(default)]
    pub error: Option<String>,
}

#[derive(Serialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct AntiBotProfileRequest {
    #[serde(skip_serializing_if = "String::is_empty", default)]
    pub html: String,
    #[serde(skip_serializing_if = "String::is_empty", default)]
    pub js: String,
    #[serde(skip_serializing_if = "std::collections::HashMap::is_empty", default)]
    pub headers: std::collections::HashMap<String, serde_json::Value>,
    #[serde(skip_serializing_if = "String::is_empty", default)]
    pub cookies: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub status_code: Option<u16>,
    #[serde(skip_serializing_if = "String::is_empty", default)]
    pub url: String,
}

#[derive(Deserialize, Serialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct AntiBotProfileResponse {
    pub success: bool,
    #[serde(default)]
    pub detection: serde_json::Map<String, serde_json::Value>,
    #[serde(default)]
    pub vendors: Vec<serde_json::Value>,
    #[serde(default)]
    pub challenges: Vec<serde_json::Value>,
    #[serde(default)]
    pub signals: Vec<String>,
    #[serde(default)]
    pub score: i64,
    #[serde(default)]
    pub level: String,
    #[serde(default)]
    pub recommendations: Vec<String>,
    #[serde(default)]
    pub request_blueprint: serde_json::Value,
    #[serde(default)]
    pub mitigation_plan: serde_json::Value,
    #[serde(default)]
    pub error: Option<String>,
}

#[derive(Deserialize, Serialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct FingerprintSpoofResponse {
    pub success: bool,
    #[serde(default)]
    pub fingerprint: serde_json::Value,
    #[serde(default)]
    pub browser: String,
    #[serde(default)]
    pub platform: String,
    #[serde(default)]
    pub error: Option<String>,
}

#[derive(Deserialize, Serialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct TLSFingerprintResponse {
    pub success: bool,
    #[serde(default)]
    pub fingerprint: serde_json::Value,
    #[serde(default)]
    pub browser: String,
    #[serde(default)]
    pub version: String,
    #[serde(default)]
    pub error: Option<String>,
}
