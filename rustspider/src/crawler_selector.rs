use crate::research::{profile_site, SiteProfile};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CrawlerSelectionRequest {
    pub url: String,
    #[serde(default)]
    pub content: String,
    #[serde(default)]
    pub scenario_hint: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CrawlerSelection {
    pub scenario: String,
    pub crawler_type: String,
    pub recommended_runner: String,
    pub runner_order: Vec<String>,
    pub site_family: String,
    pub risk_level: String,
    pub capabilities: Vec<String>,
    pub strategy_hints: Vec<String>,
    pub job_templates: Vec<String>,
    pub fallback_plan: Vec<String>,
    pub stop_conditions: Vec<String>,
    pub confidence: f64,
    pub reason_codes: Vec<String>,
    pub profile: SiteProfile,
}

pub struct CrawlerSelector;

impl CrawlerSelector {
    pub fn new() -> Self {
        Self
    }

    pub fn select(&self, request: CrawlerSelectionRequest) -> CrawlerSelection {
        let content = if request.content.trim().is_empty() {
            format!("<title>{}</title>", request.url)
        } else {
            request.content
        };
        let profile = profile_site(&request.url, &content);
        let scenario = request
            .scenario_hint
            .unwrap_or_else(|| selection_scenario(&profile).to_string());
        let runner_order = if profile.runner_order.is_empty() {
            vec!["http".to_string(), "browser".to_string()]
        } else {
            profile.runner_order.clone()
        };

        CrawlerSelection {
            scenario,
            crawler_type: profile.crawler_type.clone(),
            recommended_runner: runner_order
                .first()
                .cloned()
                .unwrap_or_else(|| "http".to_string()),
            runner_order: runner_order.clone(),
            site_family: profile.site_family.clone(),
            risk_level: profile.risk_level.clone(),
            capabilities: selection_capabilities(&profile, &runner_order),
            strategy_hints: profile.strategy_hints.clone(),
            job_templates: profile.job_templates.clone(),
            fallback_plan: selection_fallback_plan(&profile, &runner_order),
            stop_conditions: selection_stop_conditions(&profile),
            confidence: selection_confidence(&profile),
            reason_codes: selection_reason_codes(&profile),
            profile,
        }
    }
}

impl Default for CrawlerSelector {
    fn default() -> Self {
        Self::new()
    }
}

impl CrawlerSelection {
    pub fn to_value(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or_else(|_| serde_json::Value::Null)
    }
}

fn selection_scenario(profile: &SiteProfile) -> &'static str {
    match profile.crawler_type.as_str() {
        "login_session" => "authenticated_session",
        "infinite_scroll_listing" => "infinite_scroll_listing",
        "ecommerce_search" => "ecommerce_listing",
        "ecommerce_detail" => "ecommerce_detail",
        "hydrated_spa" => "javascript_hydrated_page",
        "api_bootstrap" => "embedded_api_or_bootstrap_json",
        "search_results" => "search_results",
        "static_listing" => "static_listing",
        "static_detail" => "static_detail",
        _ => "generic_page",
    }
}

fn selection_capabilities(profile: &SiteProfile, runner_order: &[String]) -> Vec<String> {
    let mut capabilities = Vec::new();
    if contains(runner_order, "http") {
        capabilities.push("http_fetch".to_string());
    }
    if contains(runner_order, "browser") {
        capabilities.push("browser_rendering".to_string());
    }
    if signal(profile, "has_pagination") {
        capabilities.push("pagination".to_string());
    }
    if signal(profile, "has_infinite_scroll") {
        capabilities.push("scroll_automation".to_string());
    }
    if signal(profile, "has_login") {
        capabilities.push("session_cookies".to_string());
    }
    if signal(profile, "has_api_bootstrap") || signal(profile, "has_graphql") {
        capabilities.push("network_or_bootstrap_json".to_string());
    }
    if signal(profile, "has_price") || signal(profile, "has_product_schema") {
        capabilities.push("commerce_fields".to_string());
    }
    if signal(profile, "has_captcha") {
        capabilities.push("anti_bot_evidence".to_string());
    }
    if profile.page_type == "detail" {
        capabilities.push("detail_extraction".to_string());
    }
    if profile.page_type == "list" {
        capabilities.push("listing_extraction".to_string());
    }
    dedupe(capabilities)
}

fn selection_fallback_plan(profile: &SiteProfile, runner_order: &[String]) -> Vec<String> {
    let mut plan = if runner_order.first().map(String::as_str) == Some("browser") {
        vec![
            "render with browser and save DOM, screenshot, and network artifacts".to_string(),
            "promote stable JSON/API responses into HTTP replay jobs".to_string(),
            "fall back to DOM selectors only after bootstrap/network data is empty".to_string(),
        ]
    } else {
        vec![
            "start with HTTP fetch and schema/meta/bootstrap extraction".to_string(),
            "fall back to browser rendering when required fields are missing".to_string(),
            "persist raw HTML and normalized fields for selector regression tests".to_string(),
        ]
    };
    if signal(profile, "has_captcha") {
        plan.push(
            "stop on captcha/challenge pages and return evidence instead of bypassing blindly"
                .to_string(),
        );
    }
    if profile.crawler_type == "login_session" {
        plan.push(
            "establish authenticated storage state before queueing follow-up URLs".to_string(),
        );
    }
    plan
}

fn selection_stop_conditions(profile: &SiteProfile) -> Vec<String> {
    if profile.crawler_type == "infinite_scroll_listing" {
        return vec![
            "stop after two unchanged DOM or item-count snapshots".to_string(),
            "stop when network responses repeat without new item IDs".to_string(),
            "respect configured max pages/items/time budget".to_string(),
        ];
    }
    if profile.page_type == "list" {
        return vec![
            "stop when next-page URL repeats or disappears".to_string(),
            "stop when item URLs no longer add new fingerprints".to_string(),
            "respect configured max pages/items/time budget".to_string(),
        ];
    }
    if profile.crawler_type == "login_session" {
        return vec![
            "stop if post-login page still contains password or captcha signals".to_string(),
            "stop when authenticated session storage cannot be established".to_string(),
        ];
    }
    vec![
        "stop after required fields are present and normalized".to_string(),
        "stop when HTTP and browser surfaces both produce empty required fields".to_string(),
    ]
}

fn selection_confidence(profile: &SiteProfile) -> f64 {
    let mut score: f64 = 0.55;
    if profile.crawler_type != "generic_http" {
        score += 0.15;
    }
    if profile.site_family != "generic" {
        score += 0.1;
    }
    if !profile.candidate_fields.is_empty() {
        score += 0.05;
    }
    if profile.runner_order.len() > 1 {
        score += 0.05;
    }
    if profile.risk_level == "medium" {
        score -= 0.05;
    } else if profile.risk_level == "high" {
        score -= 0.15;
    }
    (score.clamp(0.2, 0.95) * 100.0).round() / 100.0
}

fn selection_reason_codes(profile: &SiteProfile) -> Vec<String> {
    let mut reasons = vec![
        format!("crawler_type:{}", profile.crawler_type),
        format!("page_type:{}", profile.page_type),
        format!("site_family:{}", profile.site_family),
        format!("risk:{}", profile.risk_level),
    ];
    for (name, enabled) in &profile.signals {
        if *enabled {
            reasons.push(format!("signal:{name}"));
        }
    }
    dedupe(reasons)
}

fn signal(profile: &SiteProfile, name: &str) -> bool {
    *profile.signals.get(name).unwrap_or(&false)
}

fn contains(values: &[String], needle: &str) -> bool {
    values.iter().any(|value| value == needle)
}

fn dedupe(mut values: Vec<String>) -> Vec<String> {
    let mut result = Vec::new();
    for value in values.drain(..) {
        if !result.contains(&value) {
            result.push(value);
        }
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn selector_recommends_browser_for_ecommerce_listing() {
        let selection = CrawlerSelector::new().select(CrawlerSelectionRequest {
            url: "https://shop.example.com/search?q=phone".to_string(),
            content: r#"
                <html><script>window.__NEXT_DATA__ = {"items":[]}</script><body>
                <input type="search"><div class="product-list"><div class="sku-item">SKU-1</div>
                <span class="price">￥10</span><button>加入购物车</button></div></body></html>
            "#
            .to_string(),
            scenario_hint: None,
        });

        assert_eq!(selection.scenario, "ecommerce_listing");
        assert_eq!(selection.crawler_type, "ecommerce_search");
        assert_eq!(selection.recommended_runner, "browser");
        assert!(selection
            .capabilities
            .contains(&"commerce_fields".to_string()));
        assert!(selection
            .reason_codes
            .contains(&"signal:has_price".to_string()));
        assert!(selection.confidence >= 0.7);
        let payload = selection.to_value();
        assert_eq!(payload["recommended_runner"], "browser");
        assert_eq!(payload["profile"]["crawler_type"], "ecommerce_search");
    }

    #[test]
    fn selector_captures_login_risk() {
        let selection = CrawlerSelector::new().select(CrawlerSelectionRequest {
            url: "https://secure.example.com/login".to_string(),
            content: r#"<form><input type="password"><div>验证码</div></form>"#.to_string(),
            scenario_hint: None,
        });

        assert_eq!(selection.scenario, "authenticated_session");
        assert_eq!(selection.risk_level, "high");
        assert!(selection
            .capabilities
            .contains(&"session_cookies".to_string()));
        assert!(selection
            .capabilities
            .contains(&"anti_bot_evidence".to_string()));
        assert!(selection
            .fallback_plan
            .iter()
            .any(|item| item.to_ascii_lowercase().contains("captcha")));
    }

    #[test]
    fn selector_matches_shared_ecommerce_golden_contract() {
        let html =
            std::fs::read_to_string("../examples/crawler-selection/ecommerce-search-input.html")
                .expect("shared fixture should be readable");
        let golden: serde_json::Value = serde_json::from_str(
            &std::fs::read_to_string(
                "../examples/crawler-selection/ecommerce-search-selection.json",
            )
            .expect("shared golden should be readable"),
        )
        .expect("shared golden should be valid json");

        let selection = CrawlerSelector::new().select(CrawlerSelectionRequest {
            url: "https://shop.example.com/search?q=phone".to_string(),
            content: html,
            scenario_hint: None,
        });
        let payload = selection.to_value();

        for field in [
            "scenario",
            "crawler_type",
            "recommended_runner",
            "runner_order",
            "site_family",
            "risk_level",
            "confidence",
        ] {
            assert_eq!(payload[field], golden[field], "field {field} should match");
        }
        for capability in golden["capabilities"].as_array().unwrap() {
            assert!(payload["capabilities"]
                .as_array()
                .unwrap()
                .contains(capability));
        }
    }
}
