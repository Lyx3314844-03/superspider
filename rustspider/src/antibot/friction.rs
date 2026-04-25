use chrono::Utc;
use std::collections::{BTreeMap, HashMap, HashSet};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AccessFrictionReport {
    pub level: String,
    pub signals: Vec<String>,
    pub recommended_actions: Vec<String>,
    pub retry_after_seconds: Option<u64>,
    pub should_upgrade_to_browser: bool,
    pub requires_human_access: bool,
    pub challenge_handoff: BTreeMap<String, serde_json::Value>,
    pub capability_plan: BTreeMap<String, serde_json::Value>,
    pub blocked: bool,
}

pub fn analyze_access_friction(
    status_code: u16,
    headers: &HashMap<String, String>,
    html: &str,
    url: &str,
) -> AccessFrictionReport {
    let normalized_headers = normalize_headers(headers);
    let header_text = normalized_headers
        .iter()
        .map(|(key, value)| format!("{key}: {value}"))
        .collect::<Vec<_>>()
        .join("\n");
    let haystack = format!("{url}\n{html}\n{header_text}").to_lowercase();
    let mut signals: Vec<String> = Vec::new();

    match status_code {
        401 | 403 => signals.push("auth-or-forbidden".to_string()),
        429 => signals.push("rate-limited".to_string()),
        503 | 520 | 521 | 522 => signals.push("temporary-gateway-or-challenge".to_string()),
        _ => {}
    }

    let groups: [(&str, &[&str]); 9] = [
        (
            "captcha",
            &[
                "captcha",
                "recaptcha",
                "hcaptcha",
                "turnstile",
                "验证码",
                "滑块",
            ],
        ),
        (
            "slider-captcha",
            &[
                "geetest",
                "gt_captcha",
                "nc_token",
                "aliyuncaptcha",
                "tencentcaptcha",
                "滑块验证",
                "拖动滑块",
            ],
        ),
        (
            "managed-browser-challenge",
            &[
                "cf-chl",
                "checking your browser",
                "browser verification",
                "challenge-platform",
                "please enable javascript",
            ],
        ),
        (
            "request-blocked",
            &[
                "access denied",
                "request blocked",
                "request rejected",
                "被拒绝",
                "封禁",
                "访问过于频繁",
            ],
        ),
        (
            "auth-required",
            &["login", "sign in", "扫码", "登录", "安全验证"],
        ),
        (
            "waf-vendor",
            &[
                "cloudflare",
                "akamai",
                "imperva",
                "datadome",
                "perimeterx",
                "aliyun",
                "tencent",
                "bytedance",
                "dun.163",
            ],
        ),
        (
            "risk-control",
            &[
                "risk control",
                "风险",
                "异常访问",
                "suspicious activity",
                "环境异常",
                "账号存在风险",
            ],
        ),
        (
            "js-signature",
            &[
                "x-bogus",
                "a_bogus",
                "mstoken",
                "m_h5_tk",
                "h5st",
                "_signature",
                "cryptojs",
                "__webpack_require__",
                "webpackchunk",
            ],
        ),
        (
            "fingerprint-required",
            &[
                "navigator.webdriver",
                "canvas fingerprint",
                "webgl",
                "deviceid",
                "fpcollect",
                "sec-ch-ua",
            ],
        ),
    ];
    for (signal, patterns) in groups {
        if patterns
            .iter()
            .any(|pattern| haystack.contains(&pattern.to_lowercase()))
        {
            signals.push(signal.to_string());
        }
    }

    if normalized_headers.contains_key("retry-after") {
        signals.push("retry-after".to_string());
    }
    if ["cf-ray", "x-datadome", "x-akamai-transformed"]
        .iter()
        .any(|header| normalized_headers.contains_key(*header))
    {
        signals.push("waf-vendor".to_string());
    }
    let html_lower = html.to_lowercase();
    if status_code == 200
        && !html.trim().is_empty()
        && html.trim().len() < 300
        && (html_lower.contains("<script")
            || html_lower.contains("enable javascript")
            || html_lower.contains("window.location"))
    {
        signals.push("empty-or-script-shell".to_string());
    }

    signals = dedupe(signals);
    let retry_after_seconds = normalized_headers
        .get("retry-after")
        .and_then(|value| parse_retry_after_seconds(value));
    let level = friction_level(status_code, &signals);
    let recommended_actions = friction_actions(&signals, retry_after_seconds);
    let should_upgrade_to_browser = contains_any(
        &signals,
        &[
            "managed-browser-challenge",
            "captcha",
            "slider-captcha",
            "auth-required",
            "waf-vendor",
            "js-signature",
            "fingerprint-required",
            "empty-or-script-shell",
        ],
    );
    let requires_human_access =
        contains_any(&signals, &["captcha", "slider-captcha", "auth-required"]);
    let blocked = level == "medium" || level == "high";
    let challenge_handoff = challenge_handoff(&signals);
    let capability_plan = capability_plan(&level, &signals, retry_after_seconds);

    AccessFrictionReport {
        level,
        signals,
        recommended_actions,
        retry_after_seconds,
        should_upgrade_to_browser,
        requires_human_access,
        challenge_handoff,
        capability_plan,
        blocked,
    }
}

fn parse_retry_after_seconds(value: &str) -> Option<u64> {
    let value = value.trim();
    if value.is_empty() {
        return None;
    }
    if let Ok(seconds) = value.parse::<u64>() {
        return Some(seconds);
    }
    chrono::DateTime::parse_from_rfc2822(value)
        .ok()
        .map(|retry_at| {
            retry_at
                .with_timezone(&Utc)
                .signed_duration_since(Utc::now())
                .num_seconds()
                .max(0) as u64
        })
}

fn normalize_headers(headers: &HashMap<String, String>) -> HashMap<String, String> {
    headers
        .iter()
        .map(|(key, value)| (key.to_lowercase(), value.to_string()))
        .collect()
}

fn friction_level(status_code: u16, signals: &[String]) -> String {
    if contains_any(
        signals,
        &[
            "captcha",
            "slider-captcha",
            "auth-required",
            "request-blocked",
        ],
    ) {
        return "high".to_string();
    }
    if matches!(status_code, 401 | 403 | 429) {
        return "high".to_string();
    }
    if contains_any(
        signals,
        &[
            "managed-browser-challenge",
            "waf-vendor",
            "risk-control",
            "js-signature",
            "fingerprint-required",
            "empty-or-script-shell",
        ],
    ) {
        return "medium".to_string();
    }
    if !signals.is_empty() {
        return "low".to_string();
    }
    "none".to_string()
}

fn friction_actions(signals: &[String], retry_after_seconds: Option<u64>) -> Vec<String> {
    let mut actions: Vec<String> = Vec::new();
    if retry_after_seconds.is_some() || contains_any(signals, &["rate-limited"]) {
        actions.extend([
            "honor-retry-after".to_string(),
            "reduce-concurrency".to_string(),
            "increase-crawl-delay".to_string(),
        ]);
    }
    if contains_any(
        signals,
        &[
            "managed-browser-challenge",
            "waf-vendor",
            "empty-or-script-shell",
        ],
    ) {
        actions.extend([
            "render-with-browser".to_string(),
            "persist-session-state".to_string(),
            "capture-html-screenshot-har".to_string(),
        ]);
    }
    if contains_any(signals, &["js-signature", "fingerprint-required"]) {
        actions.extend([
            "capture-devtools-network".to_string(),
            "run-nodejs-reverse-analysis".to_string(),
            "replay-authorized-session-only".to_string(),
        ]);
    }
    if contains_any(signals, &["captcha", "slider-captcha", "auth-required"]) {
        actions.extend([
            "pause-for-human-access".to_string(),
            "document-authorization-requirement".to_string(),
        ]);
    }
    if contains_any(signals, &["request-blocked"]) {
        actions.push("stop-or-seek-site-permission".to_string());
    }
    actions.push("respect-robots-and-terms".to_string());
    dedupe(actions)
}

fn contains_any(items: &[String], candidates: &[&str]) -> bool {
    items
        .iter()
        .any(|item| candidates.iter().any(|candidate| item == candidate))
}

fn dedupe(items: Vec<String>) -> Vec<String> {
    let mut seen = HashSet::new();
    let mut out = Vec::new();
    for item in items {
        if seen.insert(item.clone()) {
            out.push(item);
        }
    }
    out
}

fn challenge_handoff(signals: &[String]) -> BTreeMap<String, serde_json::Value> {
    let mut handoff = BTreeMap::new();
    if !contains_any(
        signals,
        &["captcha", "slider-captcha", "auth-required", "risk-control"],
    ) {
        handoff.insert("required".to_string(), serde_json::json!(false));
        handoff.insert("method".to_string(), serde_json::json!("none"));
        handoff.insert("resume".to_string(), serde_json::json!("automatic"));
        return handoff;
    }
    handoff.insert("required".to_string(), serde_json::json!(true));
    handoff.insert(
        "method".to_string(),
        serde_json::json!("human-authorized-browser-session"),
    );
    handoff.insert(
        "resume".to_string(),
        serde_json::json!("after-challenge-cleared-and-session-persisted"),
    );
    handoff.insert(
        "artifacts".to_string(),
        serde_json::json!([
            "screenshot",
            "html",
            "cookies-or-storage-state",
            "network-summary"
        ]),
    );
    handoff.insert(
        "stop_conditions".to_string(),
        serde_json::json!([
            "explicit-access-denied",
            "robots-disallow",
            "missing-site-permission"
        ]),
    );
    handoff
}

fn capability_plan(
    level: &str,
    signals: &[String],
    retry_after_seconds: Option<u64>,
) -> BTreeMap<String, serde_json::Value> {
    let mut transport_order = vec!["http".to_string()];
    if contains_any(
        signals,
        &[
            "managed-browser-challenge",
            "waf-vendor",
            "captcha",
            "slider-captcha",
            "auth-required",
            "empty-or-script-shell",
        ],
    ) {
        transport_order.extend([
            "browser-render".to_string(),
            "authorized-session-replay".to_string(),
        ]);
    }
    if contains_any(signals, &["js-signature", "fingerprint-required"]) {
        transport_order.extend([
            "devtools-analysis".to_string(),
            "node-reverse-analysis".to_string(),
        ]);
    }
    if contains_any(signals, &["request-blocked"]) {
        transport_order.push("stop-until-permission".to_string());
    }

    let mut crawl_delay_seconds = retry_after_seconds.unwrap_or(1);
    if level == "medium" {
        crawl_delay_seconds = crawl_delay_seconds.max(5);
    }
    if level == "high" {
        crawl_delay_seconds = crawl_delay_seconds.max(30);
    }
    let concurrency = if level == "medium" || level == "high" {
        1
    } else {
        2
    };
    let retry_budget = if contains_any(signals, &["request-blocked"]) {
        0
    } else if level == "high" {
        1
    } else {
        2
    };

    let mut plan = BTreeMap::new();
    plan.insert("mode".to_string(), serde_json::json!("maximum-compliant"));
    plan.insert(
        "transport_order".to_string(),
        serde_json::json!(dedupe(transport_order)),
    );
    plan.insert(
        "throttle".to_string(),
        serde_json::json!({
            "concurrency": concurrency,
            "crawl_delay_seconds": crawl_delay_seconds,
            "jitter_ratio": 0.35,
            "honor_retry_after": true
        }),
    );
    plan.insert(
        "session".to_string(),
        serde_json::json!({
            "persist_storage_state": true,
            "reuse_only_after_authorized_access": contains_any(signals, &["captcha", "slider-captcha", "auth-required", "risk-control"]),
            "isolate_by_site": true
        }),
    );
    plan.insert(
        "artifacts".to_string(),
        serde_json::json!([
            "html",
            "screenshot",
            "cookies-or-storage-state",
            "network-summary",
            "friction-report"
        ]),
    );
    plan.insert("retry_budget".to_string(), serde_json::json!(retry_budget));
    plan.insert(
        "stop_conditions".to_string(),
        serde_json::json!([
            "robots-disallow",
            "explicit-access-denied",
            "missing-site-permission"
        ]),
    );
    plan
}
