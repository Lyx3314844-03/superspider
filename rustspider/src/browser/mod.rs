//! 浏览器自动化模块 - 完整功能
//!
//! 提供完整的浏览器自动化支持，包括：
//! - 页面导航和元素操作
//! - 表单填写和提交
//! - 截图和 PDF 生成
//! - 文件下载
//! - Cookie 管理
//! - 多标签页支持
//! - 自动化检测绕过

use std::time::{Duration, SystemTime, UNIX_EPOCH};

pub fn browser_compatibility_matrix() -> serde_json::Value {
    serde_json::json!({
        "base_engine": "fantoccini-webdriver",
        "bridge_style": "webdriver-and-helper",
        "surfaces": {
            "playwright": {
                "supported": true,
                "mode": "native-process",
                "adapter_engine": "node-playwright"
            },
            "selenium": {
                "supported": true,
                "mode": "native",
                "adapter_engine": "fantoccini-webdriver"
            },
            "webdriver": {
                "supported": true,
                "mode": "native",
                "adapter_engine": "fantoccini-webdriver"
            }
        },
        "artifacts": {
            "html": true,
            "screenshot": true,
            "har": true,
            "trace": true,
            "pdf": false
        },
        "interaction": {
            "file_upload": true,
            "iframe_switching": "webdriver-frame-switch",
            "shadow_dom": "open-shadow-root-helper",
            "realtime_stream_capture": "in-page-websocket-eventsource-hook"
        },
        "access_friction": {
            "classifier": true,
            "signals": ["captcha", "rate-limited", "managed-browser-challenge", "auth-required", "waf-vendor"],
            "actions": ["honor-retry-after", "render-with-browser", "persist-session-state", "pause-for-human-access"]
        },
        "constraints": [
            "playwright support is provided through a native node/playwright helper process; webdriver remains the embedded Rust browser engine"
        ]
    })
}

/// 浏览器配置
#[derive(Debug, Clone)]
#[cfg(feature = "browser")]
pub struct BrowserConfig {
    /// 是否无头模式
    pub headless: bool,
    /// WebDriver 地址
    pub webdriver_url: String,
    /// 默认超时
    pub timeout: Duration,
    /// 用户代理
    pub user_agent: Option<String>,
    /// 代理设置
    pub proxy: Option<String>,
    /// 扩展程序
    pub extensions: Vec<String>,
    /// 额外参数
    pub args: Vec<String>,
}

#[cfg(feature = "browser")]
impl Default for BrowserConfig {
    fn default() -> Self {
        BrowserConfig {
            headless: true,
            webdriver_url: "http://localhost:4444".to_string(),
            timeout: Duration::from_secs(30),
            user_agent: None,
            proxy: None,
            extensions: vec![],
            args: vec![],
        }
    }
}

/// 浏览器管理器
#[cfg(feature = "browser")]
pub struct BrowserManager {
    webdriver: fantoccini::Client,
    config: BrowserConfig,
    behavior_profile: crate::behavior::BehaviorProfile,
}

#[cfg(feature = "browser")]
pub type SeleniumConfig = BrowserConfig;

#[cfg(feature = "browser")]
#[derive(Debug, Clone)]
pub struct PlaywrightConfig {
    pub headless: bool,
    pub timeout: Duration,
    pub user_agent: Option<String>,
    pub node_command: String,
    pub helper_script: std::path::PathBuf,
}

#[cfg(feature = "browser")]
impl Default for PlaywrightConfig {
    fn default() -> Self {
        Self {
            headless: true,
            timeout: Duration::from_secs(30),
            user_agent: None,
            node_command: std::env::var("RUSTSPIDER_NODE")
                .or_else(|_| std::env::var("SPIDER_NODE"))
                .unwrap_or_else(|_| "node".to_string()),
            helper_script: resolve_playwright_helper_script(),
        }
    }
}

#[cfg(feature = "browser")]
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PlaywrightFetchResult {
    pub title: String,
    pub url: String,
    pub html_path: String,
    pub screenshot_path: String,
}

#[cfg(feature = "browser")]
pub struct PlaywrightBrowser {
    config: PlaywrightConfig,
}

#[cfg(feature = "browser")]
pub struct SeleniumBrowser {
    inner: BrowserManager,
}

#[cfg(feature = "browser")]
impl PlaywrightBrowser {
    pub fn new(config: PlaywrightConfig) -> Self {
        Self { config }
    }

    pub fn default_headless() -> Self {
        Self::new(PlaywrightConfig::default())
    }

    pub fn fetch(
        &self,
        url: &str,
        screenshot_path: &str,
        html_path: &str,
    ) -> Result<PlaywrightFetchResult, BrowserError> {
        if url.trim().is_empty() {
            return Err(BrowserError::NavigationFailed(
                "playwright fetch url cannot be empty".to_string(),
            ));
        }
        let args = self.fetch_args(url, screenshot_path, html_path);
        let output = std::process::Command::new(&self.config.node_command)
            .args(&args)
            .output()
            .map_err(|e| BrowserError::ConnectionFailed(e.to_string()))?;
        if !output.status.success() {
            return Err(BrowserError::NavigationFailed(
                String::from_utf8_lossy(&output.stderr).trim().to_string(),
            ));
        }
        let payload: serde_json::Value = serde_json::from_slice(&output.stdout)
            .map_err(|e| BrowserError::ContentFetchFailed(e.to_string()))?;
        Ok(PlaywrightFetchResult {
            title: payload
                .get("title")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string(),
            url: payload
                .get("url")
                .and_then(|v| v.as_str())
                .unwrap_or(url)
                .to_string(),
            html_path: payload
                .get("html_path")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string(),
            screenshot_path: payload
                .get("screenshot_path")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string(),
        })
    }

    pub fn fetch_args(&self, url: &str, screenshot_path: &str, html_path: &str) -> Vec<String> {
        let mut args = vec![
            self.config.helper_script.to_string_lossy().to_string(),
            "--url".to_string(),
            url.to_string(),
            "--timeout-seconds".to_string(),
            self.config.timeout.as_secs().max(1).to_string(),
        ];
        if self.config.headless {
            args.push("--headless".to_string());
        }
        if let Some(user_agent) = self
            .config
            .user_agent
            .as_ref()
            .filter(|value| !value.is_empty())
        {
            args.push("--user-agent".to_string());
            args.push(user_agent.clone());
        }
        if !screenshot_path.is_empty() {
            args.push("--screenshot".to_string());
            args.push(screenshot_path.to_string());
        }
        if !html_path.is_empty() {
            args.push("--html".to_string());
            args.push(html_path.to_string());
        }
        args
    }
}

#[cfg(feature = "browser")]
impl BrowserManager {
    /// 创建浏览器管理器
    pub async fn new(config: BrowserConfig) -> Result<Self, BrowserError> {
        use fantoccini::ClientBuilder;
        use serde_json::Value;

        let mut caps = serde_json::map::Map::new();

        // Chrome 选项
        let mut chrome_opts = serde_json::map::Map::new();

        // 无头模式
        let mut args = Vec::new();
        if config.headless {
            args.push("--headless=new".to_string());
        }
        if let Some(ua) = &config.user_agent {
            args.push(format!("--user-agent={}", ua));
        }
        if let Some(proxy) = &config.proxy {
            args.push(format!("--proxy-server={}", proxy));
        }
        args.extend(config.args.iter().cloned());
        if !args.is_empty() {
            chrome_opts.insert(
                "args".to_string(),
                Value::Array(args.into_iter().map(Value::String).collect()),
            );
        }

        // 添加扩展
        if !config.extensions.is_empty() {
            chrome_opts.insert(
                "extensions".to_string(),
                Value::Array(
                    config
                        .extensions
                        .iter()
                        .map(|s| Value::String(s.clone()))
                        .collect(),
                ),
            );
        }

        caps.insert("goog:chromeOptions".to_string(), Value::Object(chrome_opts));

        // 连接 WebDriver
        let webdriver = ClientBuilder::native()
            .capabilities(caps)
            .connect(&config.webdriver_url)
            .await
            .map_err(|e| BrowserError::ConnectionFailed(e.to_string()))?;

        // 绕过自动化检测
        let bypass_script = r#"
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 4
            });
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
        "#;
        webdriver.execute(bypass_script, vec![]).await.ok();

        Ok(BrowserManager {
            webdriver,
            config,
            behavior_profile: crate::behavior::BehaviorProfile::default(),
        })
    }

    /// 创建默认浏览器（无头模式）
    pub async fn default_headless() -> Result<Self, BrowserError> {
        Self::new(BrowserConfig::default()).await
    }

    /// 创建有头浏览器（用于调试）
    pub async fn with_head() -> Result<Self, BrowserError> {
        let config = BrowserConfig {
            headless: false,
            ..BrowserConfig::default()
        };
        Self::new(config).await
    }

    /// 导航到 URL
    pub async fn navigate(&self, url: &str) -> Result<(), BrowserError> {
        self.webdriver
            .goto(url)
            .await
            .map_err(|e| BrowserError::NavigationFailed(e.to_string()))
    }

    /// 获取 HTML 源码
    pub async fn get_html(&self) -> Result<String, BrowserError> {
        self.webdriver
            .source()
            .await
            .map_err(|e| BrowserError::ContentFetchFailed(e.to_string()))
    }

    /// 获取页面标题
    pub async fn get_title(&self) -> Result<String, BrowserError> {
        self.webdriver
            .title()
            .await
            .map_err(|e| BrowserError::ContentFetchFailed(e.to_string()))
    }

    /// 获取当前 URL
    pub async fn get_url(&self) -> Result<String, BrowserError> {
        self.webdriver
            .current_url()
            .await
            .map(|u| u.to_string())
            .map_err(|e| BrowserError::ContentFetchFailed(e.to_string()))
    }

    /// 点击元素
    pub async fn click(&self, selector: &str) -> Result<(), BrowserError> {
        use fantoccini::Locator;
        self.behavior_pause("click").await;

        let element = self
            .webdriver
            .wait()
            .for_element(Locator::Css(selector))
            .await
            .map_err(|e| BrowserError::ElementNotFound(selector.to_string(), e.to_string()))?;

        element
            .click()
            .await
            .map_err(|e| BrowserError::InteractionFailed(e.to_string()))
    }

    pub async fn analyze_locators(
        &self,
        target: crate::parser::LocatorTarget,
    ) -> Result<crate::parser::LocatorPlan, BrowserError> {
        let html = self.get_html().await?;
        Ok(crate::parser::LocatorAnalyzer.analyze(&html, &target))
    }

    pub async fn analyze_devtools(&self) -> Result<crate::parser::DevToolsReport, BrowserError> {
        let html = self.get_html().await?;
        let network = self
            .get_network_requests()
            .await
            .unwrap_or_default()
            .into_iter()
            .map(|entry| crate::parser::DevToolsNetworkArtifact {
                url: entry
                    .get("name")
                    .and_then(|value| value.as_str())
                    .unwrap_or_default()
                    .to_string(),
                method: "GET".to_string(),
                status: 0,
                resource_type: entry
                    .get("type")
                    .and_then(|value| value.as_str())
                    .unwrap_or_default()
                    .to_string(),
            })
            .collect::<Vec<_>>();
        Ok(crate::parser::DevToolsAnalyzer.analyze(&html, &network, &[]))
    }

    pub async fn devtools_analyze(&self) -> Result<crate::parser::DevToolsReport, BrowserError> {
        self.analyze_devtools().await
    }

    pub async fn auto_click(
        &self,
        target: crate::parser::LocatorTarget,
    ) -> Result<crate::parser::LocatorCandidate, BrowserError> {
        self.behavior_pause("click").await;
        let plan = self.analyze_locators(target).await?;
        let mut last_error = None;
        for candidate in plan.candidates {
            match self.find_candidate(&candidate).await {
                Ok(element) => {
                    element
                        .click()
                        .await
                        .map_err(|e| BrowserError::InteractionFailed(e.to_string()))?;
                    return Ok(candidate);
                }
                Err(error) => last_error = Some(error),
            }
        }
        Err(last_error.unwrap_or_else(|| {
            BrowserError::ElementNotFound("auto locator".to_string(), "no candidates".to_string())
        }))
    }

    /// 输入文本
    pub async fn fill(&self, selector: &str, text: &str) -> Result<(), BrowserError> {
        use fantoccini::Locator;
        self.behavior_pause("type").await;

        let element = self
            .webdriver
            .wait()
            .for_element(Locator::Css(selector))
            .await
            .map_err(|e| BrowserError::ElementNotFound(selector.to_string(), e.to_string()))?;

        element
            .send_keys(text)
            .await
            .map_err(|e| BrowserError::InteractionFailed(e.to_string()))
    }

    pub async fn auto_fill(
        &self,
        target: crate::parser::LocatorTarget,
        text: &str,
    ) -> Result<crate::parser::LocatorCandidate, BrowserError> {
        self.behavior_pause("type").await;
        let plan = self.analyze_locators(target).await?;
        let mut last_error = None;
        for candidate in plan.candidates {
            match self.find_candidate(&candidate).await {
                Ok(element) => {
                    element
                        .send_keys(text)
                        .await
                        .map_err(|e| BrowserError::InteractionFailed(e.to_string()))?;
                    return Ok(candidate);
                }
                Err(error) => last_error = Some(error),
            }
        }
        Err(last_error.unwrap_or_else(|| {
            BrowserError::ElementNotFound("auto locator".to_string(), "no candidates".to_string())
        }))
    }

    async fn find_candidate(
        &self,
        candidate: &crate::parser::LocatorCandidate,
    ) -> Result<fantoccini::elements::Element, BrowserError> {
        use fantoccini::Locator;
        let locator = if candidate.kind == "xpath" {
            Locator::XPath(&candidate.expr)
        } else {
            Locator::Css(&candidate.expr)
        };
        self.webdriver
            .wait()
            .for_element(locator)
            .await
            .map_err(|e| BrowserError::ElementNotFound(candidate.expr.clone(), e.to_string()))
    }

    /// 上传文件到 <input type="file">
    pub async fn upload_file(&self, selector: &str, file_path: &str) -> Result<(), BrowserError> {
        use fantoccini::Locator;

        let absolute = std::fs::canonicalize(file_path)
            .map_err(|e| BrowserError::FileOperationFailed(e.to_string()))?;
        let element = self
            .webdriver
            .wait()
            .for_element(Locator::Css(selector))
            .await
            .map_err(|e| BrowserError::ElementNotFound(selector.to_string(), e.to_string()))?;

        element
            .send_keys(&absolute.to_string_lossy())
            .await
            .map_err(|e| BrowserError::InteractionFailed(e.to_string()))
    }

    /// 切换到 iframe
    pub async fn enter_frame(&self, selector: &str) -> Result<(), BrowserError> {
        use fantoccini::Locator;

        let frame = self
            .webdriver
            .wait()
            .for_element(Locator::Css(selector))
            .await
            .map_err(|e| BrowserError::ElementNotFound(selector.to_string(), e.to_string()))?;

        frame
            .enter_frame()
            .await
            .map_err(|e| BrowserError::WindowOperationFailed(e.to_string()))
    }

    /// 返回父 frame
    pub async fn enter_parent_frame(&self) -> Result<(), BrowserError> {
        self.webdriver
            .enter_parent_frame()
            .await
            .map_err(|e| BrowserError::WindowOperationFailed(e.to_string()))
    }

    /// 清空输入框并输入
    pub async fn fill_clear(&self, selector: &str, text: &str) -> Result<(), BrowserError> {
        use fantoccini::Locator;

        let element = self
            .webdriver
            .wait()
            .for_element(Locator::Css(selector))
            .await
            .map_err(|e| BrowserError::ElementNotFound(selector.to_string(), e.to_string()))?;

        // 全选
        element.send_keys("\u{E009}a").await.ok();
        // 删除
        element.send_keys("\u{E017}").await.ok();
        // 输入新文本
        element
            .send_keys(text)
            .await
            .map_err(|e| BrowserError::InteractionFailed(e.to_string()))
    }

    /// 选择下拉选项（按文本）
    pub async fn select_option(&self, selector: &str, value: &str) -> Result<(), BrowserError> {
        use fantoccini::Locator;

        let _element = self
            .webdriver
            .wait()
            .for_element(Locator::Css(selector))
            .await
            .map_err(|e| BrowserError::ElementNotFound(selector.to_string(), e.to_string()))?;

        // 使用 JavaScript 选择选项
        let selector_json = serde_json::to_string(selector)
            .map_err(|e| BrowserError::ScriptExecutionFailed(e.to_string()))?;
        let value_json = serde_json::to_string(value)
            .map_err(|e| BrowserError::ScriptExecutionFailed(e.to_string()))?;
        let script = format!(
            "var select = document.querySelector({selector_json}); if(select) {{ select.value = {value_json}; select.dispatchEvent(new Event('change', {{bubbles: true}})); }}"
        );
        self.webdriver
            .execute(&script, vec![])
            .await
            .map(|_| ())
            .map_err(|e| BrowserError::InteractionFailed(e.to_string()))
    }

    /// 选择下拉选项（按值）
    pub async fn select_option_by_value(
        &self,
        selector: &str,
        value: &str,
    ) -> Result<(), BrowserError> {
        use fantoccini::Locator;

        let _element = self
            .webdriver
            .wait()
            .for_element(Locator::Css(selector))
            .await
            .map_err(|e| BrowserError::ElementNotFound(selector.to_string(), e.to_string()))?;

        // 使用 JavaScript 选择选项
        let selector_json = serde_json::to_string(selector)
            .map_err(|e| BrowserError::ScriptExecutionFailed(e.to_string()))?;
        let value_json = serde_json::to_string(value)
            .map_err(|e| BrowserError::ScriptExecutionFailed(e.to_string()))?;
        let script = format!(
            "var select = document.querySelector({selector_json}); if(select) {{ select.value = {value_json}; select.dispatchEvent(new Event('change', {{bubbles: true}})); }}"
        );
        self.webdriver
            .execute(&script, vec![])
            .await
            .map(|_| ())
            .map_err(|e| BrowserError::InteractionFailed(e.to_string()))
    }

    /// 悬停元素
    pub async fn hover(&self, selector: &str) -> Result<(), BrowserError> {
        self.behavior_pause("hover").await;
        // fantoccini 0.21 不支持 hover，使用 JavaScript 替代
        let selector_json = serde_json::to_string(selector)
            .map_err(|e| BrowserError::ScriptExecutionFailed(e.to_string()))?;
        let script = format!(
            r#"
            var element = document.querySelector({selector_json});
            if (element) {{
                element.scrollIntoView({{block: 'center', inline: 'center'}});
                var event = new MouseEvent('mouseover', {{
                    'view': window,
                    'bubbles': true,
                    'cancelable': true
                }});
                element.dispatchEvent(event);
            }}
        "#
        );

        self.webdriver
            .execute(&script, vec![])
            .await
            .map(|_| ())
            .map_err(|e| BrowserError::InteractionFailed(e.to_string()))
    }

    /// 截图
    pub async fn screenshot(&self) -> Result<Vec<u8>, BrowserError> {
        self.webdriver
            .screenshot()
            .await
            .map_err(|e| BrowserError::ScreenshotFailed(e.to_string()))
    }

    /// 截图保存为文件
    pub async fn screenshot_to_file(&self, path: &str) -> Result<(), BrowserError> {
        use std::fs::File;
        use std::io::Write;

        let data = self.screenshot().await?;
        if let Some(parent) = std::path::Path::new(path).parent() {
            if !parent.as_os_str().is_empty() {
                std::fs::create_dir_all(parent)
                    .map_err(|e| BrowserError::FileOperationFailed(e.to_string()))?;
            }
        }
        let mut file =
            File::create(path).map_err(|e| BrowserError::FileOperationFailed(e.to_string()))?;
        file.write_all(&data)
            .map_err(|e| BrowserError::FileOperationFailed(e.to_string()))?;
        Ok(())
    }

    /// 元素截图
    pub async fn screenshot_element(&self, selector: &str) -> Result<Vec<u8>, BrowserError> {
        use fantoccini::Locator;

        let element = self
            .webdriver
            .wait()
            .for_element(Locator::Css(selector))
            .await
            .map_err(|e| BrowserError::ElementNotFound(selector.to_string(), e.to_string()))?;

        element
            .screenshot()
            .await
            .map_err(|e| BrowserError::ScreenshotFailed(e.to_string()))
    }

    /// 执行 JavaScript
    pub async fn execute_script(&self, script: &str) -> Result<(), BrowserError> {
        self.webdriver
            .execute(script, vec![])
            .await
            .map(|_| ())
            .map_err(|e| BrowserError::ScriptExecutionFailed(e.to_string()))
    }

    /// 执行 JavaScript 并返回结果
    pub async fn execute_script_value(
        &self,
        script: &str,
    ) -> Result<serde_json::Value, BrowserError> {
        self.webdriver
            .execute(script, vec![])
            .await
            .map_err(|e| BrowserError::ScriptExecutionFailed(e.to_string()))
    }

    /// 在 open Shadow DOM selector path 上执行表达式。
    pub async fn execute_shadow_dom(
        &self,
        selector_path: &[&str],
        expression: &str,
    ) -> Result<serde_json::Value, BrowserError> {
        let script = build_shadow_traversal_script(selector_path, expression)?;
        self.execute_script_value(&script).await
    }

    /// 获取 open Shadow DOM path 目标元素文本。
    pub async fn get_shadow_text(&self, selector_path: &[&str]) -> Result<String, BrowserError> {
        let value = self
            .execute_shadow_dom(selector_path, "target.textContent || ''")
            .await?;
        Ok(value.as_str().unwrap_or_default().to_string())
    }

    /// 获取 open Shadow DOM path 目标元素 HTML。
    pub async fn get_shadow_html(&self, selector_path: &[&str]) -> Result<String, BrowserError> {
        let value = self
            .execute_shadow_dom(
                selector_path,
                "target.outerHTML || target.textContent || ''",
            )
            .await?;
        Ok(value.as_str().unwrap_or_default().to_string())
    }

    /// 安装页面内 WebSocket/EventSource collector，适合捕获安装后的实时流消息。
    pub async fn install_realtime_capture(&self) -> Result<(), BrowserError> {
        self.execute_script(REALTIME_CAPTURE_SCRIPT).await
    }

    /// 读取页面内 WebSocket/EventSource collector 的消息。
    pub async fn get_realtime_messages(&self) -> Result<Vec<serde_json::Value>, BrowserError> {
        let value = self
            .execute_script_value(
                "return window.__rustspiderRealtime ? window.__rustspiderRealtime.slice() : [];",
            )
            .await?;
        Ok(value.as_array().cloned().unwrap_or_default())
    }

    /// 滚动到页面底部
    pub async fn scroll_to_bottom(&self) -> Result<(), BrowserError> {
        self.behavior_pause("scroll").await;
        self.webdriver
            .execute("window.scrollTo(0, document.body.scrollHeight);", vec![])
            .await
            .map(|_| ())
            .map_err(|e| BrowserError::ScriptExecutionFailed(e.to_string()))
    }

    /// 滚动到顶部
    pub async fn scroll_to_top(&self) -> Result<(), BrowserError> {
        self.webdriver
            .execute("window.scrollTo(0, 0);", vec![])
            .await
            .map(|_| ())
            .map_err(|e| BrowserError::ScriptExecutionFailed(e.to_string()))
    }

    /// 滚动到元素
    pub async fn scroll_to_element(&self, selector: &str) -> Result<(), BrowserError> {
        self.behavior_pause("scroll").await;
        let selector_json = serde_json::to_string(selector)
            .map_err(|e| BrowserError::ScriptExecutionFailed(e.to_string()))?;
        let script = format!(
            "var el = document.querySelector({selector_json}); if(el) el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});"
        );
        self.webdriver
            .execute(&script, vec![])
            .await
            .map(|_| ())
            .map_err(|e| BrowserError::ScriptExecutionFailed(e.to_string()))
    }

    /// 等待元素出现
    pub async fn wait_for_element(
        &self,
        selector: &str,
        timeout: Option<Duration>,
    ) -> Result<(), BrowserError> {
        let t = timeout.unwrap_or(self.config.timeout);

        // 使用轮询方式等待
        let start = std::time::Instant::now();
        while start.elapsed() < t {
            if self.element_exists(selector).await? {
                return Ok(());
            }
            tokio::time::sleep(Duration::from_millis(500)).await;
        }

        Err(BrowserError::Timeout(format!("等待元素超时：{}", selector)))
    }

    /// 等待元素消失
    pub async fn wait_for_element_gone(
        &self,
        selector: &str,
        timeout: Option<Duration>,
    ) -> Result<(), BrowserError> {
        let t = timeout.unwrap_or(self.config.timeout);

        let start = std::time::Instant::now();
        while start.elapsed() < t {
            if !self.element_exists(selector).await? {
                return Ok(());
            }
            tokio::time::sleep(Duration::from_millis(500)).await;
        }

        Err(BrowserError::Timeout(format!(
            "等待元素消失超时：{}",
            selector
        )))
    }

    /// 等待文本出现
    pub async fn wait_for_text(
        &self,
        text: &str,
        timeout: Option<Duration>,
    ) -> Result<(), BrowserError> {
        let t = timeout.unwrap_or(self.config.timeout);
        let text_to_find = text.to_string();

        let start = std::time::Instant::now();
        while start.elapsed() < t {
            if let Ok(html) = self.get_html().await {
                if html.contains(&text_to_find) {
                    return Ok(());
                }
            }
            tokio::time::sleep(Duration::from_millis(500)).await;
        }

        Err(BrowserError::Timeout(format!("等待文本超时：{}", text)))
    }

    /// 等待页面加载完成
    pub async fn wait_for_page_load(&self, timeout: Option<Duration>) -> Result<(), BrowserError> {
        let t = timeout.unwrap_or(self.config.timeout);

        let start = std::time::Instant::now();
        while start.elapsed() < t {
            let result = self
                .webdriver
                .execute("return document.readyState", vec![])
                .await;

            if let Ok(v) = result {
                if let Ok(state) = serde_json::from_value::<String>(v) {
                    if state == "complete" {
                        return Ok(());
                    }
                }
            }
            tokio::time::sleep(Duration::from_millis(500)).await;
        }

        Err(BrowserError::Timeout("等待页面加载超时".to_string()))
    }

    /// 等待网络空闲
    pub async fn wait_for_network_idle(
        &self,
        timeout: Option<Duration>,
    ) -> Result<(), BrowserError> {
        let t = timeout.unwrap_or(self.config.timeout);

        let start = std::time::Instant::now();
        while start.elapsed() < t {
            let result = self.webdriver
                .execute("return window.performance.getEntriesByType('resource').filter(r => !r.responseEnd).length", vec![])
                .await;

            if let Ok(v) = result {
                if let Ok(count) = serde_json::from_value::<u64>(v) {
                    if count == 0 {
                        return Ok(());
                    }
                }
            }
            tokio::time::sleep(Duration::from_millis(500)).await;
        }

        Err(BrowserError::Timeout("等待网络空闲超时".to_string()))
    }

    /// 获取资源请求摘要
    pub async fn get_network_requests(&self) -> Result<Vec<serde_json::Value>, BrowserError> {
        let value = self
            .execute_script_value(concat!(
                "return window.performance.getEntriesByType('resource').map(function(r) {",
                "return {",
                "name: r.name,",
                "type: r.initiatorType,",
                "duration: r.duration,",
                "startTime: r.startTime,",
                "transferSize: r.transferSize || 0",
                "};",
                "});"
            ))
            .await?;
        Ok(value.as_array().cloned().unwrap_or_default())
    }

    /// 获取元素文本
    pub async fn get_element_text(&self, selector: &str) -> Result<String, BrowserError> {
        use fantoccini::Locator;

        let element = self
            .webdriver
            .wait()
            .for_element(Locator::Css(selector))
            .await
            .map_err(|e| BrowserError::ElementNotFound(selector.to_string(), e.to_string()))?;

        element
            .text()
            .await
            .map_err(|e| BrowserError::ContentFetchFailed(e.to_string()))
    }

    /// 获取元素属性
    pub async fn get_element_attribute(
        &self,
        selector: &str,
        attr: &str,
    ) -> Result<String, BrowserError> {
        use fantoccini::Locator;

        let element = self
            .webdriver
            .wait()
            .for_element(Locator::Css(selector))
            .await
            .map_err(|e| BrowserError::ElementNotFound(selector.to_string(), e.to_string()))?;

        element
            .attr(attr)
            .await
            .map_err(|e| BrowserError::ContentFetchFailed(e.to_string()))?
            .ok_or_else(|| BrowserError::AttributeNotFound(attr.to_string()))
    }

    /// 获取元素数量
    pub async fn count_elements(&self, selector: &str) -> Result<usize, BrowserError> {
        use fantoccini::Locator;

        let elements = self
            .webdriver
            .find_all(Locator::Css(selector))
            .await
            .map_err(|e| BrowserError::ElementNotFound(selector.to_string(), e.to_string()))?;

        Ok(elements.len())
    }

    /// 检查元素是否存在
    pub async fn element_exists(&self, selector: &str) -> Result<bool, BrowserError> {
        use fantoccini::Locator;

        match self.webdriver.find(Locator::Css(selector)).await {
            Ok(_) => Ok(true),
            Err(fantoccini::error::CmdError::Standard(e)) => {
                // 检查错误类型
                let is_not_found = format!("{:?}", e.error).contains("NoSuchElement")
                    || e.message.contains("no such element");
                Ok(!is_not_found)
            }
            Err(e) => Err(BrowserError::ElementNotFound(
                selector.to_string(),
                e.to_string(),
            )),
        }
    }

    /// 获取所有匹配元素的文本
    pub async fn get_all_texts(&self, selector: &str) -> Result<Vec<String>, BrowserError> {
        use fantoccini::Locator;

        let elements = self
            .webdriver
            .find_all(Locator::Css(selector))
            .await
            .map_err(|e| BrowserError::ElementNotFound(selector.to_string(), e.to_string()))?;

        let mut texts = Vec::new();
        for element in elements {
            let text = element
                .text()
                .await
                .map_err(|e| BrowserError::ContentFetchFailed(e.to_string()))?;
            texts.push(text);
        }

        Ok(texts)
    }

    /// 设置 Cookie
    pub async fn set_cookie(
        &self,
        name: &str,
        value: &str,
        _domain: Option<&str>,
    ) -> Result<(), BrowserError> {
        use fantoccini::cookies::Cookie;

        let cookie = Cookie::new(name.to_string(), value.to_string());

        self.webdriver
            .add_cookie(cookie)
            .await
            .map_err(|e| BrowserError::CookieOperationFailed(e.to_string()))
    }

    /// 获取 Cookie
    pub async fn get_cookie(&self, name: &str) -> Result<Option<String>, BrowserError> {
        let cookies = self
            .webdriver
            .get_all_cookies()
            .await
            .map_err(|e| BrowserError::CookieOperationFailed(e.to_string()))?;

        Ok(cookies
            .iter()
            .find(|c| c.name() == name)
            .map(|c| c.value().to_string()))
    }

    /// 获取所有 Cookie
    pub async fn get_all_cookies(
        &self,
    ) -> Result<Vec<fantoccini::cookies::Cookie<'_>>, BrowserError> {
        self.webdriver
            .get_all_cookies()
            .await
            .map_err(|e| BrowserError::CookieOperationFailed(e.to_string()))
    }

    /// 删除 Cookie
    pub async fn delete_cookie(&self, name: &str) -> Result<(), BrowserError> {
        self.webdriver
            .delete_cookie(name)
            .await
            .map_err(|e| BrowserError::CookieOperationFailed(e.to_string()))
    }

    /// 删除所有 Cookie
    pub async fn delete_all_cookies(&self) -> Result<(), BrowserError> {
        self.webdriver
            .delete_all_cookies()
            .await
            .map_err(|e| BrowserError::CookieOperationFailed(e.to_string()))
    }

    /// 获取窗口大小
    pub async fn get_window_size(&self) -> Result<(u64, u64), BrowserError> {
        let rect: (u64, u64, u64, u64) = self
            .webdriver
            .get_window_rect()
            .await
            .map_err(|e| BrowserError::WindowOperationFailed(e.to_string()))?;

        Ok((rect.2, rect.3)) // width, height
    }

    /// 设置窗口大小
    pub async fn set_window_size(&self, width: u32, height: u32) -> Result<(), BrowserError> {
        self.webdriver
            .set_window_rect(0, 0, width, height)
            .await
            .map_err(|e| BrowserError::WindowOperationFailed(e.to_string()))
    }

    /// 最大化窗口
    pub async fn maximize_window(&self) -> Result<(), BrowserError> {
        self.webdriver
            .maximize_window()
            .await
            .map_err(|e| BrowserError::WindowOperationFailed(e.to_string()))
    }

    /// 刷新页面
    pub async fn refresh(&self) -> Result<(), BrowserError> {
        self.webdriver
            .refresh()
            .await
            .map_err(|e| BrowserError::NavigationFailed(e.to_string()))
    }

    /// 后退
    pub async fn back(&self) -> Result<(), BrowserError> {
        self.webdriver
            .back()
            .await
            .map_err(|e| BrowserError::NavigationFailed(e.to_string()))
    }

    /// 前进
    pub async fn forward(&self) -> Result<(), BrowserError> {
        self.webdriver
            .forward()
            .await
            .map_err(|e| BrowserError::NavigationFailed(e.to_string()))
    }

    /// 关闭浏览器
    pub async fn close(self) -> Result<(), BrowserError> {
        self.webdriver
            .close()
            .await
            .map_err(|e| BrowserError::CloseFailed(e.to_string()))
    }

    /// 关闭当前标签页
    pub async fn close_tab(&self) -> Result<(), BrowserError> {
        self.webdriver
            .close_window()
            .await
            .map_err(|e| BrowserError::WindowOperationFailed(e.to_string()))
    }

    /// 获取标签页列表
    pub async fn get_window_handles(&self) -> Result<Vec<String>, BrowserError> {
        self.webdriver
            .windows()
            .await
            .map(|handles| handles.into_iter().map(|h| format!("{:?}", h)).collect())
            .map_err(|e| BrowserError::WindowOperationFailed(e.to_string()))
    }

    /// 切换到标签页
    pub async fn switch_to_window(&self, handle: &str) -> Result<(), BrowserError> {
        // 使用字符串匹配来切换窗口
        let handles = self
            .webdriver
            .windows()
            .await
            .map_err(|e| BrowserError::WindowOperationFailed(e.to_string()))?;

        for h in handles {
            if format!("{:?}", h) == handle {
                self.webdriver
                    .switch_to_window(h)
                    .await
                    .map_err(|e| BrowserError::WindowOperationFailed(e.to_string()))?;
                return Ok(());
            }
        }

        Err(BrowserError::WindowOperationFailed(format!(
            "窗口句柄不存在：{}",
            handle
        )))
    }

    /// 创建新标签页
    pub async fn new_tab(&self) -> Result<(), BrowserError> {
        let response = self
            .webdriver
            .new_window(true)
            .await
            .map_err(|e| BrowserError::WindowOperationFailed(e.to_string()))?;
        self.webdriver
            .switch_to_window(response.handle)
            .await
            .map_err(|e| BrowserError::WindowOperationFailed(e.to_string()))?;

        Ok(())
    }

    /// 下载文件
    pub async fn download_file(&self, url: &str, save_path: &str) -> Result<(), BrowserError> {
        use reqwest::Client;
        use tokio::io::AsyncWriteExt;

        let client = Client::new();
        let response = client
            .get(url)
            .send()
            .await
            .map_err(|e| BrowserError::DownloadFailed(e.to_string()))?;

        let bytes = response
            .bytes()
            .await
            .map_err(|e| BrowserError::DownloadFailed(e.to_string()))?;

        let mut file = tokio::fs::File::create(save_path)
            .await
            .map_err(|e| BrowserError::FileOperationFailed(e.to_string()))?;

        file.write_all(&bytes)
            .await
            .map_err(|e| BrowserError::FileOperationFailed(e.to_string()))?;

        Ok(())
    }

    /// 绕过自动化检测
    pub async fn bypass_detection(&self) -> Result<(), BrowserError> {
        let scripts = vec![
            // 隐藏 webdriver 属性
            r#"Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"#,
            // 伪装 plugins
            r#"Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });"#,
            // 伪装 languages
            r#"Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });"#,
            // 伪装 hardwareConcurrency
            r#"Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 4 });"#,
            // 伪装 deviceMemory
            r#"Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });"#,
            // 添加 chrome 属性
            r#"Object.defineProperty(navigator, 'chrome', { get: () => ({}) });"#,
        ];

        for script in scripts {
            self.webdriver.execute(script, vec![]).await.ok();
        }

        Ok(())
    }

    async fn behavior_pause(&self, action: &str) {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|value| value.as_secs())
            .unwrap_or_default();
        let hour = ((now / 3600) % 24) as u8;
        let delay =
            crate::behavior::randomized_action_delay_ms(action, hour, &self.behavior_profile);
        if delay > 0 {
            tokio::time::sleep(Duration::from_millis(delay)).await;
        }
    }
}

#[cfg(feature = "browser")]
impl SeleniumBrowser {
    pub async fn new(config: SeleniumConfig) -> Result<Self, BrowserError> {
        Ok(Self {
            inner: BrowserManager::new(config).await?,
        })
    }

    pub async fn navigate(&self, url: &str) -> Result<(), BrowserError> {
        self.inner.navigate(url).await
    }

    pub async fn get_html(&self) -> Result<String, BrowserError> {
        self.inner.get_html().await
    }

    pub async fn screenshot(&self) -> Result<Vec<u8>, BrowserError> {
        self.inner.screenshot().await
    }

    pub async fn close(self) -> Result<(), BrowserError> {
        self.inner.close().await
    }

    pub async fn upload_file(&self, selector: &str, file_path: &str) -> Result<(), BrowserError> {
        self.inner.upload_file(selector, file_path).await
    }

    pub async fn enter_frame(&self, selector: &str) -> Result<(), BrowserError> {
        self.inner.enter_frame(selector).await
    }

    pub async fn enter_parent_frame(&self) -> Result<(), BrowserError> {
        self.inner.enter_parent_frame().await
    }
}

#[cfg(feature = "browser")]
const REALTIME_CAPTURE_SCRIPT: &str = r#"
if (!window.__rustspiderRealtimeInstalled) {
    window.__rustspiderRealtimeInstalled = true;
    window.__rustspiderRealtime = window.__rustspiderRealtime || [];
    const push = (entry) => {
        try {
            window.__rustspiderRealtime.push(Object.assign({ts: Date.now()}, entry));
        } catch (_) {}
    };
    const NativeWebSocket = window.WebSocket;
    if (NativeWebSocket) {
        window.WebSocket = function(url, protocols) {
            const socket = protocols === undefined ? new NativeWebSocket(url) : new NativeWebSocket(url, protocols);
            push({protocol: "websocket", direction: "open", url: String(url)});
            const nativeSend = socket.send;
            socket.send = function(data) {
                push({protocol: "websocket", direction: "sent", url: String(url), data: String(data)});
                return nativeSend.call(this, data);
            };
            socket.addEventListener("message", (event) => {
                push({protocol: "websocket", direction: "received", url: String(url), data: String(event.data)});
            });
            socket.addEventListener("error", () => {
                push({protocol: "websocket", direction: "error", url: String(url)});
            });
            return socket;
        };
        window.WebSocket.prototype = NativeWebSocket.prototype;
        Object.assign(window.WebSocket, NativeWebSocket);
    }
    const NativeEventSource = window.EventSource;
    if (NativeEventSource) {
        window.EventSource = function(url, config) {
            const source = new NativeEventSource(url, config);
            push({protocol: "sse", direction: "open", url: String(url)});
            source.addEventListener("message", (event) => {
                push({protocol: "sse", direction: "received", url: String(url), event_id: event.lastEventId || "", data: String(event.data)});
            });
            source.addEventListener("error", () => {
                push({protocol: "sse", direction: "error", url: String(url)});
            });
            return source;
        };
        window.EventSource.prototype = NativeEventSource.prototype;
    }
}
"#;

#[cfg(feature = "browser")]
fn normalize_shadow_path<'a>(selector_path: &'a [&'a str]) -> Result<Vec<&'a str>, BrowserError> {
    let path: Vec<&str> = selector_path
        .iter()
        .map(|selector| selector.trim())
        .filter(|selector| !selector.is_empty())
        .collect();
    if path.is_empty() {
        return Err(BrowserError::ScriptExecutionFailed(
            "shadow selector path cannot be empty".to_string(),
        ));
    }
    Ok(path)
}

#[cfg(feature = "browser")]
fn resolve_playwright_helper_script() -> std::path::PathBuf {
    for env_name in [
        "RUSTSPIDER_PLAYWRIGHT_NODE_HELPER",
        "SPIDER_PLAYWRIGHT_NODE_HELPER",
    ] {
        if let Ok(path) = std::env::var(env_name) {
            if !path.trim().is_empty() {
                return std::path::PathBuf::from(path);
            }
        }
    }
    let manifest_dir = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let candidates = [
        manifest_dir
            .parent()
            .map(|root| root.join("tools").join("playwright_fetch.mjs")),
        Some(manifest_dir.join("tools").join("playwright_fetch.mjs")),
    ];
    for candidate in candidates.into_iter().flatten() {
        if candidate.exists() {
            return candidate;
        }
    }
    std::path::PathBuf::from("..")
        .join("tools")
        .join("playwright_fetch.mjs")
}

#[cfg(feature = "browser")]
fn build_shadow_traversal_script(
    selector_path: &[&str],
    expression: &str,
) -> Result<String, BrowserError> {
    let expression = expression.trim();
    if expression.is_empty() {
        return Err(BrowserError::ScriptExecutionFailed(
            "shadow expression cannot be empty".to_string(),
        ));
    }
    let path = normalize_shadow_path(selector_path)?;
    let path_json = serde_json::to_string(&path)
        .map_err(|err| BrowserError::ScriptExecutionFailed(err.to_string()))?;
    Ok(format!(
        r#"const selectors = {path_json};
let root = document;
let target = null;
for (let index = 0; index < selectors.length; index++) {{
    const selector = selectors[index];
    target = root.querySelector(selector);
    if (!target) {{
        throw new Error("shadow selector not found: " + selector);
    }}
    if (index < selectors.length - 1) {{
        if (!target.shadowRoot) {{
            throw new Error("open shadowRoot not found: " + selector);
        }}
        root = target.shadowRoot;
    }}
}}
return ({expression});"#
    ))
}

/// 浏览器错误
#[derive(Debug, thiserror::Error)]
pub enum BrowserError {
    #[error("连接 WebDriver 失败：{0}")]
    ConnectionFailed(String),

    #[error("导航失败：{0}")]
    NavigationFailed(String),

    #[error("内容获取失败：{0}")]
    ContentFetchFailed(String),

    #[error("元素未找到：{0} ({1})")]
    ElementNotFound(String, String),

    #[error("交互失败：{0}")]
    InteractionFailed(String),

    #[error("截图失败：{0}")]
    ScreenshotFailed(String),

    #[error("脚本执行失败：{0}")]
    ScriptExecutionFailed(String),

    #[error("超时：{0}")]
    Timeout(String),

    #[error("属性未找到：{0}")]
    AttributeNotFound(String),

    #[error("Cookie 操作失败：{0}")]
    CookieOperationFailed(String),

    #[error("窗口操作失败：{0}")]
    WindowOperationFailed(String),

    #[error("文件操作失败：{0}")]
    FileOperationFailed(String),

    #[error("下载失败：{0}")]
    DownloadFailed(String),

    #[error("关闭失败：{0}")]
    CloseFailed(String),

    #[error("浏览器未初始化")]
    NotInitialized,
}

/// 浏览器构建器
#[cfg(feature = "browser")]
pub struct BrowserBuilder {
    config: BrowserConfig,
}

#[cfg(feature = "browser")]
impl BrowserBuilder {
    /// 创建新构建器
    pub fn new() -> Self {
        BrowserBuilder {
            config: BrowserConfig::default(),
        }
    }

    /// 设置无头模式
    pub fn headless(mut self, headless: bool) -> Self {
        self.config.headless = headless;
        self
    }

    /// 设置 WebDriver 地址
    pub fn webdriver_url(mut self, url: &str) -> Self {
        self.config.webdriver_url = url.to_string();
        self
    }

    /// 设置超时
    pub fn timeout(mut self, timeout: Duration) -> Self {
        self.config.timeout = timeout;
        self
    }

    /// 设置用户代理
    pub fn user_agent(mut self, ua: &str) -> Self {
        self.config.user_agent = Some(ua.to_string());
        self
    }

    /// 设置代理
    pub fn proxy(mut self, proxy: &str) -> Self {
        self.config.proxy = Some(proxy.to_string());
        self
    }

    /// 添加扩展
    pub fn extension(mut self, ext: &str) -> Self {
        self.config.extensions.push(ext.to_string());
        self
    }

    /// 添加启动参数
    pub fn arg(mut self, arg: &str) -> Self {
        self.config.args.push(arg.to_string());
        self
    }

    /// 构建浏览器
    pub async fn build(self) -> Result<BrowserManager, BrowserError> {
        BrowserManager::new(self.config).await
    }
}

#[cfg(feature = "browser")]
impl Default for BrowserBuilder {
    fn default() -> Self {
        Self::new()
    }
}

/// 表单处理器
#[cfg(feature = "browser")]
pub struct FormHandler<'a> {
    browser: &'a BrowserManager,
    form_selector: &'a str,
}

#[cfg(feature = "browser")]
impl<'a> FormHandler<'a> {
    /// 创建表单处理器
    pub fn new(browser: &'a BrowserManager, form_selector: &'a str) -> Self {
        FormHandler {
            browser,
            form_selector,
        }
    }

    /// 填写字段
    pub async fn fill_field(&self, field_selector: &str, value: &str) -> Result<(), BrowserError> {
        let selector = format!("{} {}", self.form_selector, field_selector);
        self.browser.fill(&selector, value).await
    }

    /// 提交表单
    pub async fn submit(&self) -> Result<(), BrowserError> {
        let selector = format!(
            "{} button[type='submit'], {} input[type='submit']",
            self.form_selector, self.form_selector
        );
        self.browser.click(&selector).await
    }
}

#[cfg(test)]
mod tests {
    use std::time::Duration;

    #[test]
    #[cfg(feature = "browser")]
    fn test_browser_config_default() {
        use super::BrowserConfig;
        let config = BrowserConfig::default();
        assert!(config.headless);
        assert_eq!(config.webdriver_url, "http://localhost:4444");
        assert_eq!(config.timeout, Duration::from_secs(30));
    }

    #[test]
    #[cfg(feature = "browser")]
    fn test_browser_builder() {
        use super::BrowserBuilder;
        let builder = BrowserBuilder::new()
            .headless(true)
            .user_agent("Mozilla/5.0")
            .timeout(Duration::from_secs(60));

        assert_eq!(builder.config.timeout, Duration::from_secs(60));
        assert_eq!(builder.config.user_agent, Some("Mozilla/5.0".to_string()));
    }

    #[test]
    #[cfg(feature = "browser")]
    fn test_shadow_traversal_script_uses_json_selectors() {
        let script = super::build_shadow_traversal_script(
            &["app-shell", "button[data-name=\"primary\"]"],
            "target.textContent || ''",
        )
        .expect("script");

        assert!(script.contains("button[data-name=\\\"primary\\\"]"));
        assert!(script.contains("open shadowRoot not found"));
        assert!(script.contains("target.textContent"));
    }

    #[test]
    fn test_browser_compatibility_matrix_reports_native_browser_surfaces() {
        let matrix = super::browser_compatibility_matrix();
        assert_eq!(
            matrix["surfaces"]["selenium"]["adapter_engine"],
            "fantoccini-webdriver"
        );
        assert_eq!(matrix["interaction"]["file_upload"], true);
        assert_eq!(
            matrix["interaction"]["realtime_stream_capture"],
            "in-page-websocket-eventsource-hook"
        );
    }

    #[test]
    #[cfg(feature = "browser")]
    fn test_playwright_browser_builds_node_helper_command() {
        let browser = super::PlaywrightBrowser::new(super::PlaywrightConfig {
            headless: true,
            timeout: Duration::from_secs(12),
            user_agent: Some("FixtureBrowser/1.0".to_string()),
            node_command: "node".to_string(),
            helper_script: "tools/playwright_fetch.mjs".into(),
        });
        let args = browser.fetch_args("https://example.com", "page.png", "page.html");
        let joined = args.join(" ");
        for expected in [
            "tools/playwright_fetch.mjs",
            "--url https://example.com",
            "--timeout-seconds 12",
            "--headless",
            "--user-agent FixtureBrowser/1.0",
            "--screenshot page.png",
            "--html page.html",
        ] {
            assert!(joined.contains(expected), "missing {expected}: {args:?}");
        }
    }
}
