//! Node.js 逆向服务客户端
//! 为 Rust Spider 提供统一的逆向能力

use regex::Regex;
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
        let local = local_crypto_analysis(code);

        match self
            .http_client
            .post(format!("{}/api/crypto/analyze", self.base_url))
            .json(&request)
            .send()
            .await
        {
            Ok(response) if response.status().is_success() => {
                match response.json::<CryptoAnalyzeResponse>().await {
                    Ok(mut payload) => {
                        merge_crypto_analysis(&mut payload, &local);
                        Ok(payload)
                    }
                    Err(error) => {
                        if local.success {
                            Ok(local)
                        } else {
                            Err(Box::new(error))
                        }
                    }
                }
            }
            Ok(_) | Err(_) if local.success => Ok(local),
            Ok(error_response) => {
                Err(format!("crypto analyze failed: {}", error_response.status()).into())
            }
            Err(error) => Err(Box::new(error)),
        }
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

    pub async fn analyze_webpack(
        &self,
        code: &str,
    ) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        let payload = serde_json::json!({
            "code": code
        });

        let response = self
            .http_client
            .post(format!("{}/api/webpack/analyze", self.base_url))
            .json(&payload)
            .send()
            .await?
            .json::<serde_json::Value>()
            .await?;

        Ok(response)
    }

    pub async fn canvas_fingerprint(
        &self,
    ) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        let response = self
            .http_client
            .post(format!("{}/api/canvas/fingerprint", self.base_url))
            .json(&serde_json::json!({}))
            .send()
            .await?
            .json::<serde_json::Value>()
            .await?;

        Ok(response)
    }

    pub async fn reverse_signature(
        &self,
        code: &str,
        input: &str,
        expected_output: &str,
    ) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        let response = self
            .http_client
            .post(format!("{}/api/signature/reverse", self.base_url))
            .json(&serde_json::json!({
                "code": code,
                "input": input,
                "expectedOutput": expected_output
            }))
            .send()
            .await?
            .json::<serde_json::Value>()
            .await?;

        Ok(response)
    }
}

impl Default for NodeReverseClient {
    fn default() -> Self {
        Self::new(DEFAULT_BASE_URL)
    }
}

fn local_crypto_analysis(code: &str) -> CryptoAnalyzeResponse {
    let lowered = code.to_lowercase();
    let contains_any = |markers: &[&str]| -> usize {
        markers
            .iter()
            .filter(|marker| lowered.contains(**marker))
            .count()
    };
    let libraries = [
        ("CryptoJS", &["cryptojs."][..]),
        (
            "NodeCrypto",
            &[
                "require('crypto')",
                "require(\"crypto\")",
                "createcipheriv",
                "createhmac",
                "createhash",
            ][..],
        ),
        (
            "WebCrypto",
            &[
                "crypto.subtle",
                "subtle.encrypt",
                "subtle.decrypt",
                "subtle.digest",
                "subtle.sign",
            ][..],
        ),
        ("Forge", &["forge.", "node-forge"][..]),
        ("SJCL", &["sjcl."][..]),
        ("sm-crypto", &["sm2", "sm3", "sm4", "sm-crypto"][..]),
        ("JSEncrypt", &["jsencrypt", "node-rsa"][..]),
        ("jsrsasign", &["jsrsasign", "rsasign"][..]),
        ("tweetnacl", &["tweetnacl", "nacl.sign", "nacl.box"][..]),
        (
            "elliptic",
            &["secp256k1", "elliptic.ec", "ecdh", "ecdsa"][..],
        ),
        (
            "sodium",
            &["libsodium", "sodium.", "xchacha20", "ed25519", "x25519"][..],
        ),
    ];
    let operations = [
        (
            "encrypt",
            &["encrypt(", "subtle.encrypt", "createcipheriv", ".encrypt("][..],
        ),
        (
            "decrypt",
            &[
                "decrypt(",
                "subtle.decrypt",
                "createdecipheriv",
                ".decrypt(",
            ][..],
        ),
        (
            "sign",
            &["sign(", "subtle.sign", "jsonwebtoken.sign", "jws.sign"][..],
        ),
        (
            "verify",
            &[
                "verify(",
                "subtle.verify",
                "jsonwebtoken.verify",
                "jws.verify",
            ][..],
        ),
        (
            "hash",
            &[
                "createhash",
                "subtle.digest",
                "md5(",
                "sha1(",
                "sha256(",
                "sha512(",
                "sha3",
                "ripemd160",
            ][..],
        ),
        ("kdf", &["pbkdf2", "scrypt", "bcrypt", "hkdf"][..]),
        (
            "encode",
            &["btoa(", "atob(", "base64", "base64url", "jwt"][..],
        ),
    ];
    let mode_markers = [
        ("CBC", &["cbc"][..]),
        ("GCM", &["gcm"][..]),
        ("CTR", &["ctr"][..]),
        ("ECB", &["ecb"][..]),
        ("CFB", &["cfb"][..]),
        ("OFB", &["ofb"][..]),
        ("CCM", &["ccm"][..]),
        ("XTS", &["xts"][..]),
    ];
    let dynamic_source_markers = [
        (
            "storage",
            &["localstorage", "sessionstorage", "indexeddb"][..],
        ),
        ("cookie", &["document.cookie"][..]),
        ("navigator", &["navigator."][..]),
        ("time", &["date.now", "new date(", "performance.now"][..]),
        (
            "random",
            &["math.random", "getrandomvalues", "randombytes"][..],
        ),
        ("env", &["process.env", "import.meta.env"][..]),
        ("window_state", &["window.__", "globalthis.", "window["][..]),
        (
            "network",
            &[
                "fetch(",
                "axios.",
                "xmlhttprequest",
                ".response",
                "await fetch",
            ][..],
        ),
    ];
    let runtime_selector_markers = [
        (
            "algorithm_variable",
            &["algorithm", "algo", "ciphername"][..],
        ),
        ("mode_variable", &["mode =", "mode:", "ciphermode"][..]),
        (
            "switch_dispatch",
            &["switch(", "case 'aes", "case \"aes"][..],
        ),
        (
            "computed_lookup",
            &["[algo]", "[algorithm]", "algorithms[", "ciphers["][..],
        ),
    ];
    let obfuscation_loader_markers = [
        ("eval_packer", &["eval(function(p,a,c,k,e,d)"][..]),
        ("hex_array", &["_0x", "\\x"][..]),
        ("base64_loader", &["atob(", "buffer.from(", "base64"][..]),
        (
            "function_constructor",
            &[
                "function(",
                "constructor(\"return this\")",
                "constructor('return this')",
            ][..],
        ),
        (
            "webpack_loader",
            &["__webpack_require__", "webpackjsonp", "webpackchunk"][..],
        ),
        (
            "anti_debug",
            &["debugger", "devtools", "setinterval(function(){debugger"][..],
        ),
    ];
    let sink_catalog = [
        ("CryptoJS.AES.encrypt", &["cryptojs.aes.encrypt"][..]),
        ("CryptoJS.AES.decrypt", &["cryptojs.aes.decrypt"][..]),
        ("CryptoJS.DES.encrypt", &["cryptojs.des.encrypt"][..]),
        (
            "CryptoJS.TripleDES.encrypt",
            &["cryptojs.tripledes.encrypt"][..],
        ),
        (
            "CryptoJS.HmacSHA256",
            &["cryptojs.hmacsha256", "hmacsha256("][..],
        ),
        ("CryptoJS.PBKDF2", &["cryptojs.pbkdf2", "pbkdf2("][..]),
        ("crypto.createCipheriv", &["createcipheriv"][..]),
        ("crypto.createDecipheriv", &["createdecipheriv"][..]),
        ("crypto.createHmac", &["createhmac"][..]),
        ("crypto.createHash", &["createhash"][..]),
        ("crypto.subtle.encrypt", &["subtle.encrypt"][..]),
        ("crypto.subtle.decrypt", &["subtle.decrypt"][..]),
        ("crypto.subtle.sign", &["subtle.sign"][..]),
        ("crypto.subtle.digest", &["subtle.digest"][..]),
        ("sm4.encrypt", &["sm4.encrypt"][..]),
        ("sm2.doSignature", &["sm2.dosignature"][..]),
        ("jwt.sign", &["jsonwebtoken.sign", "jwt.sign"][..]),
        ("jwt.verify", &["jsonwebtoken.verify", "jwt.verify"][..]),
    ];
    let algorithms = [
        (
            "AES",
            &[
                "cryptojs.aes",
                "aes-gcm",
                "aes-cbc",
                "aes-ctr",
                "aes-ecb",
                "createcipheriv",
                "createdecipheriv",
                "subtle.encrypt",
                "subtle.decrypt",
            ][..],
        ),
        ("DES", &["cryptojs.des", "des-cbc", "des-ecb"][..]),
        (
            "TripleDES",
            &["cryptojs.tripledes", "des-ede3", "3des", "tripledes"][..],
        ),
        (
            "RSA",
            &[
                "jsencrypt",
                "node-rsa",
                "publicencrypt",
                "privatedecrypt",
                "rsa-oaep",
                "rsa-pss",
                "rsasign",
            ][..],
        ),
        ("ECDSA", &["ecdsa", "secp256k1", "elliptic.ec"][..]),
        ("Ed25519", &["ed25519"][..]),
        ("X25519", &["x25519"][..]),
        ("SM2", &["sm2"][..]),
        ("SM3", &["sm3"][..]),
        ("SM4", &["sm4"][..]),
        ("RC4", &["cryptojs.rc4", "rc4"][..]),
        ("Rabbit", &["cryptojs.rabbit", "rabbit"][..]),
        ("ChaCha20", &["chacha20", "xchacha20"][..]),
        ("Salsa20", &["salsa20"][..]),
        ("Blowfish", &["blowfish"][..]),
        ("Twofish", &["twofish"][..]),
        ("TEA", &["tea.encrypt", "tea.decrypt"][..]),
        ("XTEA", &["xtea"][..]),
        ("XXTEA", &["xxtea"][..]),
        (
            "HMAC-SHA1",
            &["hmacsha1", "createhmac('sha1", "createhmac(\"sha1"][..],
        ),
        (
            "HMAC-SHA256",
            &["hmacsha256", "createhmac('sha256", "createhmac(\"sha256"][..],
        ),
        (
            "HMAC-SHA512",
            &["hmacsha512", "createhmac('sha512", "createhmac(\"sha512"][..],
        ),
        ("MD5", &["cryptojs.md5", "md5("][..]),
        ("SHA1", &["cryptojs.sha1", "sha1("][..]),
        ("SHA256", &["cryptojs.sha256", "sha256("][..]),
        ("SHA512", &["cryptojs.sha512", "sha512("][..]),
        ("SHA3", &["cryptojs.sha3", "sha3"][..]),
        ("RIPEMD160", &["ripemd160"][..]),
        ("PBKDF2", &["cryptojs.pbkdf2", "pbkdf2"][..]),
        ("scrypt", &["scrypt"][..]),
        ("bcrypt", &["bcrypt"][..]),
        ("HKDF", &["hkdf"][..]),
        ("Base64", &["btoa(", "atob(", "base64"][..]),
        (
            "JWT",
            &[
                "jsonwebtoken.sign",
                "jsonwebtoken.verify",
                "jwt.sign",
                "jwt.verify",
                "jws.sign",
            ][..],
        ),
    ];

    let mut crypto_types = Vec::new();
    for (name, markers) in algorithms {
        let hits = contains_any(markers);
        if hits == 0 {
            continue;
        }
        let mut modes = mode_markers
            .iter()
            .filter(|(_, markers)| contains_any(markers) > 0)
            .map(|(name, _)| (*name).to_string())
            .collect::<Vec<_>>();
        modes.sort();
        modes.dedup();
        let confidence =
            (0.55_f64 + 0.12_f64 * (hits.min(3) as f64) + 0.03_f64 * (modes.len().min(3) as f64))
                .min(0.99);
        crypto_types.push(CryptoType {
            name: name.to_string(),
            confidence,
            modes,
        });
    }

    let detected_libraries = libraries
        .iter()
        .filter(|(_, markers)| contains_any(markers) > 0)
        .map(|(name, _)| (*name).to_string())
        .collect::<Vec<_>>();
    let detected_operations = operations
        .iter()
        .filter(|(_, markers)| contains_any(markers) > 0)
        .map(|(name, _)| (*name).to_string())
        .collect::<Vec<_>>();
    let detected_modes = mode_markers
        .iter()
        .filter(|(_, markers)| contains_any(markers) > 0)
        .map(|(name, _)| (*name).to_string())
        .collect::<Vec<_>>();
    let normalized_algorithms = crypto_types
        .iter()
        .map(|item| item.name.clone())
        .collect::<Vec<_>>();
    let dynamic_key_sources = dynamic_source_markers
        .iter()
        .filter(|(_, markers)| contains_any(markers) > 0)
        .map(|(name, _)| (*name).to_string())
        .collect::<Vec<_>>();
    let runtime_algorithm_selection = runtime_selector_markers
        .iter()
        .filter(|(_, markers)| contains_any(markers) > 0)
        .map(|(name, _)| (*name).to_string())
        .collect::<Vec<_>>();
    let obfuscation_loaders = obfuscation_loader_markers
        .iter()
        .filter(|(_, markers)| contains_any(markers) > 0)
        .map(|(name, _)| (*name).to_string())
        .collect::<Vec<_>>();
    let algorithm_aliases = algorithms
        .iter()
        .filter_map(|(name, markers)| {
            let aliases = markers
                .iter()
                .filter(|marker| lowered.contains(**marker))
                .map(|marker| (*marker).to_string())
                .collect::<Vec<_>>();
            if aliases.is_empty() {
                None
            } else {
                Some(((*name).to_string(), aliases))
            }
        })
        .collect::<std::collections::BTreeMap<_, _>>();
    let crypto_sinks = sink_catalog
        .iter()
        .filter(|(_, markers)| contains_any(markers) > 0)
        .map(|(name, _)| (*name).to_string())
        .collect::<Vec<_>>();
    let assignment_regex = Regex::new(
        r"(?i)(?:const|let|var)?\s*([A-Za-z_$][\w$]*(?:key|iv|nonce|salt|secret|token)[A-Za-z0-9_$]*)\s*[:=]\s*([^;\n]+)",
    )
    .ok();
    let source_detail_tokens = [
        ("storage.localStorage", &["localstorage"][..]),
        ("storage.sessionStorage", &["sessionstorage"][..]),
        ("storage.indexedDB", &["indexeddb"][..]),
        ("cookie.document", &["document.cookie"][..]),
        ("navigator", &["navigator."][..]),
        ("time.date", &["date.now", "new date("][..]),
        ("time.performance", &["performance.now"][..]),
        ("random.math", &["math.random"][..]),
        ("random.crypto", &["getrandomvalues", "randombytes"][..]),
        ("env.process", &["process.env"][..]),
        ("env.import_meta", &["import.meta.env"][..]),
        (
            "window.bootstrap",
            &["window.__", "globalthis.", "window["][..],
        ),
        ("network.fetch", &["fetch(", "await fetch"][..]),
        ("network.xhr", &["xmlhttprequest", ".response"][..]),
        ("network.axios", &["axios."][..]),
        (
            "dom.querySelector",
            &["queryselector(", "queryselectorall("][..],
        ),
        ("dom.getElementById", &["getelementbyid("][..]),
        (
            "url.searchParams",
            &["urlsearchparams", "searchparams.get("][..],
        ),
    ];
    let key_flow_candidates = assignment_regex
        .as_ref()
        .map(|regex| {
            regex
                .captures_iter(code)
                .filter_map(|captures| {
                    let variable = captures.get(1)?.as_str().trim().to_string();
                    let expression = captures.get(2)?.as_str().trim().to_string();
                    let expression_lower = expression.to_lowercase();
                    let sources = source_detail_tokens
                        .iter()
                        .filter(|(_, tokens)| {
                            tokens.iter().any(|token| expression_lower.contains(*token))
                        })
                        .map(|(name, _)| (*name).to_string())
                        .collect::<Vec<_>>();
                    if sources.is_empty() {
                        return None;
                    }
                    Some(serde_json::json!({
                        "variable": variable,
                        "expression": expression.chars().take(160).collect::<String>(),
                        "sources": sources,
                        "dynamic": true
                    }))
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();
    let derivation_tokens = [
        ("hash", &["sha", "md5(", "ripemd", "digest("][..]),
        ("hmac", &["hmac"][..]),
        ("kdf", &["pbkdf2", "scrypt", "bcrypt", "hkdf"][..]),
        (
            "encode",
            &["btoa(", "atob(", "base64", "buffer.from", "tostring("][..],
        ),
        ("concat", &["concat(", "+", "join("][..]),
        ("json", &["json.stringify", "json.parse"][..]),
        (
            "url",
            &[
                "encodeuricomponent",
                "decodeuricomponent",
                "urlsearchparams",
            ][..],
        ),
    ];
    let code_lines = code.lines().collect::<Vec<_>>();
    let key_flow_chains = key_flow_candidates
        .iter()
        .filter_map(|candidate| {
            let variable = candidate.get("variable")?.as_str()?.to_string();
            let source_kind = candidate
                .get("sources")
                .and_then(|value| value.as_array())
                .and_then(|values| values.first())
                .and_then(|value| value.as_str())
                .unwrap_or("unknown")
                .to_string();
            let source_expression = candidate
                .get("expression")
                .and_then(|value| value.as_str())
                .unwrap_or("")
                .to_string();
            let mut tracked = vec![variable.clone()];
            let mut derivations = Vec::new();
            if let Some(regex) = &assignment_regex {
                for captures in regex.captures_iter(code) {
                    let target_var = captures.get(1)?.as_str().trim().to_string();
                    let expression = captures.get(2)?.as_str().trim().to_string();
                    if tracked.iter().any(|item| item == &target_var) {
                        continue;
                    }
                    if !tracked.iter().any(|item| {
                        Regex::new(&format!(r"\b{}\b", regex::escape(item)))
                            .map(|re| re.is_match(&expression))
                            .unwrap_or(false)
                    }) {
                        continue;
                    }
                    let expression_lower = expression.to_lowercase();
                    let kind = derivation_tokens
                        .iter()
                        .find(|(_, tokens)| {
                            tokens.iter().any(|token| expression_lower.contains(*token))
                        })
                        .map(|(name, _)| (*name).to_string())
                        .unwrap_or_else(|| "propagate".to_string());
                    derivations.push(serde_json::json!({
                        "variable": target_var,
                        "kind": kind,
                        "expression": expression.chars().take(160).collect::<String>(),
                    }));
                    tracked.push(target_var);
                }
            }
            let sinks = sink_catalog
                .iter()
                .filter_map(|(sink, markers)| {
                    let matched = code_lines.iter().any(|line| {
                        let lower_line = line.to_lowercase();
                        if !markers.iter().any(|marker| lower_line.contains(*marker)) {
                            return false;
                        }
                        tracked.iter().any(|item| {
                            Regex::new(&format!(r"\b{}\b", regex::escape(item)))
                                .map(|re| re.is_match(line))
                                .unwrap_or(false)
                        })
                    });
                    matched.then(|| (*sink).to_string())
                })
                .collect::<Vec<_>>();
            if derivations.is_empty() && sinks.is_empty() {
                return None;
            }
            let mut confidence = 0.55_f64;
            if !sinks.is_empty() {
                confidence += 0.10;
            }
            confidence += (derivations.len() as f64 * 0.06).min(0.18);
            if source_kind != "unknown" {
                confidence += 0.06;
            }
            Some(serde_json::json!({
                "variable": variable,
                "source": {
                    "kind": source_kind,
                    "expression": source_expression,
                },
                "derivations": derivations,
                "sinks": sinks,
                "confidence": (confidence.min(0.99) * 100.0).round() / 100.0,
            }))
        })
        .collect::<Vec<_>>();
    let has_key_derivation = contains_any(
        operations
            .iter()
            .find(|(name, _)| *name == "kdf")
            .map(|(_, markers)| *markers)
            .unwrap_or(&[]),
    ) > 0;
    let has_random_iv = lowered.contains("wordarray.random")
        || lowered.contains("randombytes")
        || lowered.contains("getrandomvalues")
        || lowered.contains("nonce")
        || lowered.contains("iv");
    let has_public_key = crypto_types.iter().any(|item| {
        matches!(
            item.name.as_str(),
            "RSA" | "ECDSA" | "Ed25519" | "X25519" | "SM2"
        )
    });
    let has_runtime_lib = detected_libraries
        .iter()
        .any(|name| matches!(name.as_str(), "WebCrypto" | "NodeCrypto" | "sodium"));
    let has_kdf = crypto_types
        .iter()
        .any(|item| matches!(item.name.as_str(), "PBKDF2" | "scrypt" | "bcrypt" | "HKDF"));
    let risk_score = (if crypto_types.is_empty() { 0 } else { 18 }
        + (dynamic_key_sources.len() * 8).min(20)
        + (runtime_algorithm_selection.len() * 6).min(18)
        + (obfuscation_loaders.len() * 8).min(24)
        + (key_flow_candidates.len() * 4).min(16)
        + (crypto_sinks.len() * 2).min(12)
        + if has_public_key { 8 } else { 0 }
        + if has_runtime_lib { 6 } else { 0 }
        + if has_kdf { 6 } else { 0 })
    .min(100);
    let mut recommended_approach = Vec::new();
    if !obfuscation_loaders.is_empty() {
        recommended_approach.push("unpack-loader-first".to_string());
    }
    if !dynamic_key_sources.is_empty() {
        recommended_approach.push("trace-key-materialization".to_string());
    }
    if !runtime_algorithm_selection.is_empty() {
        recommended_approach.push("trace-algorithm-branch".to_string());
    }
    if detected_libraries.iter().any(|name| name == "WebCrypto") {
        recommended_approach.push("hook-webcrypto".to_string());
    }
    if crypto_types.iter().any(|item| {
        matches!(
            item.name.as_str(),
            "JWT" | "HMAC-SHA1" | "HMAC-SHA256" | "HMAC-SHA512"
        )
    }) {
        recommended_approach.push("rebuild-signing-canonicalization".to_string());
    }
    if has_public_key {
        recommended_approach.push("capture-key-import-and-padding".to_string());
    }
    if recommended_approach.is_empty() {
        recommended_approach.push("static-analysis-sufficient".to_string());
    }
    let analysis = serde_json::json!({
        "hasKeyDerivation": has_key_derivation,
        "hasRandomIV": has_random_iv,
        "detectedLibraries": detected_libraries,
        "detectedOperations": detected_operations,
        "detectedModes": detected_modes,
        "normalizedAlgorithms": normalized_algorithms,
        "algorithmAliases": algorithm_aliases,
        "dynamicKeySources": dynamic_key_sources,
        "keyFlowCandidates": key_flow_candidates,
        "keyFlowChains": key_flow_chains,
        "runtimeAlgorithmSelection": runtime_algorithm_selection,
        "obfuscationLoaders": obfuscation_loaders,
        "cryptoSinks": crypto_sinks,
        "riskScore": risk_score,
        "reverseComplexity": complexity_label(risk_score as i64),
        "recommendedApproach": recommended_approach,
        "requiresASTDataflow": !dynamic_key_sources.is_empty() || !runtime_algorithm_selection.is_empty() || !obfuscation_loaders.is_empty() || !key_flow_candidates.is_empty(),
        "requiresRuntimeExecution": !dynamic_key_sources.is_empty() || !obfuscation_loaders.is_empty() || detected_libraries.iter().any(|name| name == "WebCrypto") || !crypto_sinks.is_empty(),
        "requiresLoaderUnpack": !obfuscation_loaders.is_empty(),
    });

    CryptoAnalyzeResponse {
        success: !crypto_types.is_empty(),
        crypto_types,
        keys: extract_literals(
            code,
            r#"(?i)(?:const|let|var)?\s*(?:appSecret|secret|privateKey|publicKey|aesKey|desKey|rsaKey|signKey|hmacKey|key)\w*\s*[:=]\s*['"`]([^'"`\r\n]{4,128})['"`]"#,
        ),
        ivs: extract_literals(
            code,
            r#"(?i)(?:const|let|var)?\s*(?:iv|nonce|salt)\w*\s*[:=]\s*['"`]([^'"`\r\n]{4,128})['"`]"#,
        ),
        analysis: Some(analysis),
    }
}

fn merge_crypto_analysis(remote: &mut CryptoAnalyzeResponse, local: &CryptoAnalyzeResponse) {
    let mut by_name = std::collections::BTreeMap::new();
    for item in remote.crypto_types.iter().chain(local.crypto_types.iter()) {
        let entry = by_name.entry(item.name.clone()).or_insert(CryptoType {
            name: item.name.clone(),
            confidence: 0.0,
            modes: Vec::new(),
        });
        if item.confidence > entry.confidence {
            entry.confidence = item.confidence;
        }
        entry.modes.extend(item.modes.clone());
        entry.modes.sort();
        entry.modes.dedup();
    }
    remote.crypto_types = by_name.into_values().collect();
    remote.crypto_types.sort_by(|left, right| {
        right
            .confidence
            .partial_cmp(&left.confidence)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(left.name.cmp(&right.name))
    });
    remote.keys.extend(local.keys.clone());
    remote.keys.sort();
    remote.keys.dedup();
    remote.ivs.extend(local.ivs.clone());
    remote.ivs.sort();
    remote.ivs.dedup();

    let risk_score = remote
        .analysis
        .as_ref()
        .and_then(|value| value.get("riskScore"))
        .and_then(|value| value.as_i64())
        .unwrap_or(0)
        .max(
            local
                .analysis
                .as_ref()
                .and_then(|value| value.get("riskScore"))
                .and_then(|value| value.as_i64())
                .unwrap_or(0),
        );
    let merged_analysis = serde_json::json!({
        "hasKeyDerivation": remote.analysis.as_ref().and_then(|value| value.get("hasKeyDerivation")).and_then(|value| value.as_bool()).unwrap_or(false)
            || local.analysis.as_ref().and_then(|value| value.get("hasKeyDerivation")).and_then(|value| value.as_bool()).unwrap_or(false),
        "hasRandomIV": remote.analysis.as_ref().and_then(|value| value.get("hasRandomIV")).and_then(|value| value.as_bool()).unwrap_or(false)
            || local.analysis.as_ref().and_then(|value| value.get("hasRandomIV")).and_then(|value| value.as_bool()).unwrap_or(false),
        "detectedLibraries": merge_string_arrays(remote.analysis.as_ref().and_then(|value| value.get("detectedLibraries")), local.analysis.as_ref().and_then(|value| value.get("detectedLibraries"))),
        "detectedOperations": merge_string_arrays(remote.analysis.as_ref().and_then(|value| value.get("detectedOperations")), local.analysis.as_ref().and_then(|value| value.get("detectedOperations"))),
        "detectedModes": merge_string_arrays(remote.analysis.as_ref().and_then(|value| value.get("detectedModes")), local.analysis.as_ref().and_then(|value| value.get("detectedModes"))),
        "normalizedAlgorithms": merge_string_arrays(remote.analysis.as_ref().and_then(|value| value.get("normalizedAlgorithms")), local.analysis.as_ref().and_then(|value| value.get("normalizedAlgorithms"))),
        "algorithmAliases": merge_alias_maps(remote.analysis.as_ref().and_then(|value| value.get("algorithmAliases")), local.analysis.as_ref().and_then(|value| value.get("algorithmAliases"))),
        "dynamicKeySources": merge_string_arrays(remote.analysis.as_ref().and_then(|value| value.get("dynamicKeySources")), local.analysis.as_ref().and_then(|value| value.get("dynamicKeySources"))),
        "keyFlowCandidates": merge_flow_candidates(remote.analysis.as_ref().and_then(|value| value.get("keyFlowCandidates")), local.analysis.as_ref().and_then(|value| value.get("keyFlowCandidates"))),
        "keyFlowChains": merge_flow_candidates(remote.analysis.as_ref().and_then(|value| value.get("keyFlowChains")), local.analysis.as_ref().and_then(|value| value.get("keyFlowChains"))),
        "runtimeAlgorithmSelection": merge_string_arrays(remote.analysis.as_ref().and_then(|value| value.get("runtimeAlgorithmSelection")), local.analysis.as_ref().and_then(|value| value.get("runtimeAlgorithmSelection"))),
        "obfuscationLoaders": merge_string_arrays(remote.analysis.as_ref().and_then(|value| value.get("obfuscationLoaders")), local.analysis.as_ref().and_then(|value| value.get("obfuscationLoaders"))),
        "recommendedApproach": merge_string_arrays(remote.analysis.as_ref().and_then(|value| value.get("recommendedApproach")), local.analysis.as_ref().and_then(|value| value.get("recommendedApproach"))),
        "cryptoSinks": merge_string_arrays(remote.analysis.as_ref().and_then(|value| value.get("cryptoSinks")), local.analysis.as_ref().and_then(|value| value.get("cryptoSinks"))),
        "requiresASTDataflow": remote.analysis.as_ref().and_then(|value| value.get("requiresASTDataflow")).and_then(|value| value.as_bool()).unwrap_or(false)
            || local.analysis.as_ref().and_then(|value| value.get("requiresASTDataflow")).and_then(|value| value.as_bool()).unwrap_or(false),
        "requiresRuntimeExecution": remote.analysis.as_ref().and_then(|value| value.get("requiresRuntimeExecution")).and_then(|value| value.as_bool()).unwrap_or(false)
            || local.analysis.as_ref().and_then(|value| value.get("requiresRuntimeExecution")).and_then(|value| value.as_bool()).unwrap_or(false),
        "requiresLoaderUnpack": remote.analysis.as_ref().and_then(|value| value.get("requiresLoaderUnpack")).and_then(|value| value.as_bool()).unwrap_or(false)
            || local.analysis.as_ref().and_then(|value| value.get("requiresLoaderUnpack")).and_then(|value| value.as_bool()).unwrap_or(false),
        "riskScore": risk_score,
        "reverseComplexity": complexity_label(risk_score),
    });
    remote.analysis = Some(merged_analysis);
    if !remote.success && !remote.crypto_types.is_empty() {
        remote.success = true;
    }
}

fn merge_string_arrays(
    first: Option<&serde_json::Value>,
    second: Option<&serde_json::Value>,
) -> Vec<String> {
    let mut values = first
        .and_then(|value| value.as_array())
        .into_iter()
        .flatten()
        .chain(
            second
                .and_then(|value| value.as_array())
                .into_iter()
                .flatten(),
        )
        .filter_map(|value| value.as_str().map(str::to_string))
        .collect::<Vec<_>>();
    values.sort();
    values.dedup();
    values
}

fn merge_alias_maps(
    first: Option<&serde_json::Value>,
    second: Option<&serde_json::Value>,
) -> serde_json::Value {
    let mut merged = serde_json::Map::new();
    for source in [first, second] {
        let Some(source) = source else {
            continue;
        };
        let Some(object) = source.as_object() else {
            continue;
        };
        for (name, aliases) in object {
            let entry = merged
                .entry(name.clone())
                .or_insert_with(|| serde_json::Value::Array(Vec::new()));
            let mut values = entry
                .as_array()
                .cloned()
                .unwrap_or_default()
                .into_iter()
                .filter_map(|value| value.as_str().map(str::to_string))
                .collect::<Vec<_>>();
            values.extend(
                aliases
                    .as_array()
                    .into_iter()
                    .flatten()
                    .filter_map(|value| value.as_str().map(str::to_string)),
            );
            values.sort();
            values.dedup();
            *entry = serde_json::json!(values);
        }
    }
    serde_json::Value::Object(merged)
}

fn merge_flow_candidates(
    first: Option<&serde_json::Value>,
    second: Option<&serde_json::Value>,
) -> serde_json::Value {
    let mut merged = Vec::new();
    let mut seen = std::collections::BTreeSet::new();
    for source in [first, second] {
        let Some(source) = source else {
            continue;
        };
        let Some(array) = source.as_array() else {
            continue;
        };
        for item in array {
            let key = format!(
                "{}|{}",
                item.get("variable")
                    .and_then(|value| value.as_str())
                    .unwrap_or(""),
                item.get("expression")
                    .and_then(|value| value.as_str())
                    .unwrap_or("")
            );
            if seen.insert(key) {
                merged.push(item.clone());
            }
        }
    }
    serde_json::Value::Array(merged)
}

fn extract_literals(code: &str, pattern: &str) -> Vec<String> {
    let Ok(regex) = Regex::new(pattern) else {
        return Vec::new();
    };
    let mut values = Vec::new();
    for captures in regex.captures_iter(code) {
        let Some(value) = captures.get(1) else {
            continue;
        };
        let value = value.as_str().trim().to_string();
        if value.len() < 4 || value.len() > 128 || values.contains(&value) {
            continue;
        }
        values.push(value);
        if values.len() >= 8 {
            break;
        }
    }
    values
}

fn complexity_label(score: i64) -> &'static str {
    if score >= 80 {
        "extreme"
    } else if score >= 55 {
        "high"
    } else if score >= 30 {
        "medium"
    } else {
        "low"
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

#[cfg(test)]
mod tests {
    use super::local_crypto_analysis;

    #[test]
    fn local_crypto_analysis_detects_multiple_algorithms() {
        let response = local_crypto_analysis(
            r#"
            const key = "secret-key-1234";
            const iv = "nonce-001";
            const token = CryptoJS.HmacSHA256(data, key).toString();
            const cipher = sm4.encrypt(data, key, { mode: "cbc" });
            const digest = CryptoJS.SHA256(data).toString();
            const derived = CryptoJS.PBKDF2(password, salt, { keySize: 8 });
            const sessionKey = localStorage.getItem("session-key");
            const derivedKey = sha256(sessionKey || key);
            window.crypto.subtle.encrypt({ name: "AES-GCM", iv }, derivedKey, data);
            "#,
        );

        let names = response
            .crypto_types
            .iter()
            .map(|item| item.name.as_str())
            .collect::<std::collections::BTreeSet<_>>();
        assert!(names.contains("AES"));
        assert!(names.contains("SM4"));
        assert!(names.contains("HMAC-SHA256"));
        assert!(names.contains("SHA256"));
        assert!(names.contains("PBKDF2"));
        assert!(response.keys.contains(&"secret-key-1234".to_string()));
        assert!(response.ivs.contains(&"nonce-001".to_string()));
        let analysis = response.analysis.expect("analysis should exist");
        assert!(analysis["riskScore"].as_i64().unwrap_or_default() >= 30);
        assert_eq!(analysis["requiresASTDataflow"].as_bool(), Some(true));
        assert!(analysis["cryptoSinks"]
            .as_array()
            .unwrap_or(&Vec::new())
            .iter()
            .any(|item| item.as_str() == Some("crypto.subtle.encrypt")));
        assert!(analysis["algorithmAliases"]["AES"]
            .as_array()
            .unwrap_or(&Vec::new())
            .iter()
            .any(|item| item.as_str() == Some("aes-gcm")));
        assert!(analysis["keyFlowCandidates"]
            .as_array()
            .unwrap_or(&Vec::new())
            .iter()
            .any(|item| item["variable"].as_str() == Some("sessionKey")));
        assert!(analysis["keyFlowChains"]
            .as_array()
            .unwrap_or(&Vec::new())
            .iter()
            .any(|item| item["variable"].as_str() == Some("sessionKey")
                && item["sinks"].to_string().contains("crypto.subtle.encrypt")
                && item["derivations"].to_string().contains("derivedKey")));
        assert!(analysis["recommendedApproach"]
            .as_array()
            .unwrap_or(&Vec::new())
            .iter()
            .any(|item| item.as_str() == Some("trace-key-materialization")));
    }
}
