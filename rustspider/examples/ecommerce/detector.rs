//! Universal e-commerce site detector for the Rust example crawler.

#![allow(dead_code)]

use regex::Regex;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EcommerceDetectionResult {
    pub is_ecommerce: bool,
    pub confidence: f64,
    pub site_family: String,
    pub platform: String,
    pub detected_features: Vec<String>,
    pub currency: String,
    pub has_jsonld: bool,
    pub has_next_data: bool,
    pub price_api_detected: bool,
    pub cart_url: String,
    pub category_urls: Vec<String>,
}

impl Default for EcommerceDetectionResult {
    fn default() -> Self {
        Self {
            is_ecommerce: false,
            confidence: 0.0,
            site_family: "generic".to_string(),
            platform: String::new(),
            detected_features: Vec::new(),
            currency: String::new(),
            has_jsonld: false,
            has_next_data: false,
            price_api_detected: false,
            cart_url: String::new(),
            category_urls: Vec::new(),
        }
    }
}

pub fn detect_ecommerce_site(raw_url: &str, html: &str) -> EcommerceDetectionResult {
    let mut result = EcommerceDetectionResult::default();
    if raw_url.trim().is_empty() {
        return result;
    }

    merge_result(&mut result, detect_by_url(raw_url));
    merge_result(&mut result, detect_by_platform(html));
    merge_result(&mut result, detect_by_html_signals(html));
    merge_result(&mut result, detect_by_structured_data(html));
    merge_result(&mut result, detect_by_price_api(html));

    if html.contains("application/ld+json") {
        result.has_jsonld = true;
        push_feature(&mut result, "json_ld");
    }
    if html.contains("__NEXT_DATA__")
        || html.contains("__INITIAL_STATE__")
        || html.contains("__NUXT__")
    {
        result.has_next_data = true;
        push_feature(&mut result, "hydration_data");
    }
    if result.site_family != "generic" {
        if let Some((cart, categories)) = site_family_urls().get(result.site_family.as_str()) {
            result.cart_url = (*cart).to_string();
            result.category_urls = categories.iter().map(|url| (*url).to_string()).collect();
        }
    }
    result
}

fn merge_result(
    result: &mut EcommerceDetectionResult,
    candidate: Option<EcommerceDetectionResult>,
) {
    let Some(candidate) = candidate else {
        return;
    };
    result.is_ecommerce = result.is_ecommerce || candidate.is_ecommerce;
    if candidate.confidence > result.confidence {
        result.confidence = candidate.confidence;
    }
    if result.site_family == "generic" && candidate.site_family != "generic" {
        result.site_family = candidate.site_family;
    }
    if result.platform.is_empty() && !candidate.platform.is_empty() {
        result.platform = candidate.platform;
    }
    if result.currency.is_empty() && !candidate.currency.is_empty() {
        result.currency = candidate.currency;
    }
    result.has_jsonld |= candidate.has_jsonld;
    result.has_next_data |= candidate.has_next_data;
    result.price_api_detected |= candidate.price_api_detected;
    for feature in candidate.detected_features {
        push_feature(result, &feature);
    }
}

fn push_feature(result: &mut EcommerceDetectionResult, feature: &str) {
    if !result
        .detected_features
        .iter()
        .any(|value| value == feature)
    {
        result.detected_features.push(feature.to_string());
    }
}

fn detect_by_url(raw_url: &str) -> Option<EcommerceDetectionResult> {
    for (family, patterns, confidence, currency) in url_signatures() {
        if patterns.iter().any(|pattern| regex_match(pattern, raw_url)) {
            return Some(EcommerceDetectionResult {
                is_ecommerce: true,
                confidence,
                site_family: family.to_string(),
                platform: family.to_string(),
                currency: currency.to_string(),
                detected_features: vec!["url_pattern".to_string()],
                ..Default::default()
            });
        }
    }
    None
}

fn detect_by_platform(html: &str) -> Option<EcommerceDetectionResult> {
    if html.is_empty() {
        return None;
    }
    let lowered = html.to_ascii_lowercase();
    for (platform, needles, confidence) in platform_signatures() {
        if needles.iter().any(|needle| lowered.contains(needle)) {
            return Some(EcommerceDetectionResult {
                is_ecommerce: true,
                confidence,
                platform: platform.to_string(),
                detected_features: vec!["platform_signature".to_string()],
                ..Default::default()
            });
        }
    }
    None
}

fn detect_by_html_signals(html: &str) -> Option<EcommerceDetectionResult> {
    if html.is_empty() {
        return None;
    }
    let mut signals = 0;
    for pattern in html_signals() {
        if regex_match(pattern, html) {
            signals += 1;
        }
    }
    let has_jsonld = html.contains("application/ld+json");
    let has_next_data = html.contains("__NEXT_DATA__") || html.contains("__INITIAL_STATE__");
    if has_jsonld {
        signals += 2;
    }
    if has_next_data {
        signals += 1;
    }
    if signals < 2 {
        return None;
    }
    Some(EcommerceDetectionResult {
        is_ecommerce: true,
        confidence: (signals as f64 * 0.15).min(0.85),
        has_jsonld,
        has_next_data,
        detected_features: vec!["html_structure".to_string()],
        ..Default::default()
    })
}

fn detect_by_structured_data(html: &str) -> Option<EcommerceDetectionResult> {
    for payload in json_payloads(html) {
        if let Ok(value) = serde_json::from_str::<Value>(&payload) {
            if contains_product_shape(&value) {
                return Some(EcommerceDetectionResult {
                    is_ecommerce: true,
                    confidence: 0.75,
                    has_jsonld: true,
                    detected_features: vec!["structured_product_data".to_string()],
                    ..Default::default()
                });
            }
        }
    }
    None
}

fn detect_by_price_api(html: &str) -> Option<EcommerceDetectionResult> {
    let lowered = html.to_ascii_lowercase();
    let hits = [
        "price",
        "amount",
        "currency",
        "discount",
        "saleprice",
        "stock",
    ]
    .iter()
    .filter(|needle| lowered.contains(**needle))
    .count();
    if hits >= 3 {
        Some(EcommerceDetectionResult {
            is_ecommerce: true,
            confidence: 0.50,
            price_api_detected: true,
            detected_features: vec!["price_api".to_string()],
            ..Default::default()
        })
    } else {
        None
    }
}

fn contains_product_shape(value: &Value) -> bool {
    match value {
        Value::Object(map) => {
            let node_type = map
                .get("@type")
                .and_then(Value::as_str)
                .unwrap_or_default()
                .to_ascii_lowercase();
            if ["product", "offer", "aggregateoffer", "itemlist"].contains(&node_type.as_str()) {
                return true;
            }
            let product_fields = ["sku", "price", "offers", "priceCurrency", "aggregateRating"];
            if product_fields
                .iter()
                .filter(|key| map.contains_key(**key))
                .count()
                >= 2
            {
                return true;
            }
            map.values().any(contains_product_shape)
        }
        Value::Array(values) => values.iter().any(contains_product_shape),
        _ => false,
    }
}

fn json_payloads(html: &str) -> Vec<String> {
    let mut values = Vec::new();
    for pattern in [
        r#"(?is)<script[^>]+type=["']application/ld\+json["'][^>]*>(.*?)</script>"#,
        r#"(?is)<script[^>]+type=["']application/json["'][^>]*>(.*?)</script>"#,
        r#"(?is)__NEXT_DATA__\s*=\s*(\{.*?\})\s*;"#,
        r#"(?is)__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;"#,
    ] {
        if let Ok(regex) = Regex::new(pattern) {
            for capture in regex.captures_iter(html) {
                if let Some(payload) = capture.get(1) {
                    values.push(payload.as_str().trim().to_string());
                }
            }
        }
    }
    values
}

fn regex_match(pattern: &str, text: &str) -> bool {
    Regex::new(&format!("(?i){pattern}"))
        .map(|regex| regex.is_match(text))
        .unwrap_or(false)
}

fn url_signatures() -> Vec<(&'static str, Vec<&'static str>, f64, &'static str)> {
    vec![
        ("jd", vec![r"jd\.com", r"jd\.hk"], 0.95, "CNY"),
        ("taobao", vec![r"taobao\.com"], 0.95, "CNY"),
        ("tmall", vec![r"tmall\.com"], 0.95, "CNY"),
        (
            "pinduoduo",
            vec![r"pinduoduo\.com", r"yangkeduo\.com", r"pdd\.com"],
            0.95,
            "CNY",
        ),
        ("1688", vec![r"1688\.com"], 0.95, "CNY"),
        ("suning", vec![r"suning\.com"], 0.90, "CNY"),
        ("vip", vec![r"vip\.com", r"vipshop\.com"], 0.95, "CNY"),
        (
            "xiaohongshu",
            vec![r"xiaohongshu\.com", r"xhscdn\.com"],
            0.95,
            "CNY",
        ),
        (
            "douyin-shop",
            vec![r"douyin\.com", r"jinritemai\.com"],
            0.90,
            "CNY",
        ),
        (
            "amazon",
            vec![r"amazon\.(com|co\.uk|de|fr|it|es|co\.jp|com\.au|ca|in)"],
            0.95,
            "USD",
        ),
        (
            "ebay",
            vec![r"ebay\.(com|co\.uk|de|fr|it|es|com\.au|ca)"],
            0.95,
            "USD",
        ),
        (
            "aliexpress",
            vec![r"aliexpress\.(com|us|es|ru|pt|fr|de|it)"],
            0.95,
            "USD",
        ),
        (
            "shopee",
            vec![r"shopee\.(com|co\.th|co\.id|com\.my|com\.ph|vn|tw|br)"],
            0.95,
            "USD",
        ),
        (
            "lazada",
            vec![r"lazada\.(com|com\.my|com\.ph|co\.id|co\.th|vn)"],
            0.95,
            "USD",
        ),
        ("walmart", vec![r"walmart\.(com|ca)"], 0.95, "USD"),
        ("target", vec![r"target\.com"], 0.95, "USD"),
        (
            "temu",
            vec![r"temu\.(com|co\.uk|co\.jp|de|fr|es|it|nl)"],
            0.95,
            "USD",
        ),
        (
            "shein",
            vec![r"shein\.(com|co\.uk|co\.jp|de|fr|es|it|nl)"],
            0.95,
            "USD",
        ),
        (
            "mercadolibre",
            vec![r"mercadolibre\.(com\.ar|com\.mx|com\.br|com\.co|cl)"],
            0.95,
            "USD",
        ),
        ("ozon", vec![r"ozon\.ru"], 0.95, "RUB"),
        ("wildberries", vec![r"wildberries\.ru"], 0.95, "RUB"),
        ("allegro", vec![r"allegro\.(pl|cz|sk)"], 0.95, "PLN"),
    ]
}

fn platform_signatures() -> Vec<(&'static str, Vec<&'static str>, f64)> {
    vec![
        (
            "shopify",
            vec!["shopify.com", "cdn.shopify", "shopify.theme"],
            0.90,
        ),
        (
            "magento",
            vec!["magento_", "mage-cache", "mage/cookies"],
            0.90,
        ),
        (
            "woocommerce",
            vec!["woocommerce", "wp-content/plugins/woocommerce"],
            0.85,
        ),
        ("bigcommerce", vec!["bigcommerce", "bc.js"], 0.90),
        ("prestashop", vec!["prestashop", "ps-shoppingcart"], 0.90),
        (
            "salesforce",
            vec!["demandware", "sfcc", "commercecloud"],
            0.85,
        ),
        ("wix", vec!["wix.com", "wixstores"], 0.80),
    ]
}

fn html_signals() -> Vec<&'static str> {
    vec![
        r#""@type"\s*:\s*"Product""#,
        r#""@type"\s*:\s*"Offer""#,
        r#"class=["'][^"']*price[^"']*["']"#,
        r#"class=["'][^"']*product[^"']*["']"#,
        r#"class=["'][^"']*add-to-cart[^"']*["']"#,
        r#"shopping[\-]?cart"#,
        r#"data-product-id"#,
        r#"data-sku"#,
        r#"data-variant-id"#,
        r#"itemtype=["']https?://schema\.org/Product["']"#,
        r#"[\$€£¥₹₩₽][\d,]+\.?\d*"#,
    ]
}

fn site_family_urls() -> HashMap<&'static str, (&'static str, Vec<&'static str>)> {
    HashMap::from([
        (
            "jd",
            ("https://cart.jd.com/", vec!["https://channel.jd.com/"]),
        ),
        (
            "taobao",
            (
                "https://cart.taobao.com/",
                vec!["https://www.taobao.com/tbhome/"],
            ),
        ),
        (
            "tmall",
            ("https://cart.tmall.com/", vec!["https://www.tmall.com/"]),
        ),
        (
            "amazon",
            (
                "https://www.amazon.com/gp/cart/",
                vec!["https://www.amazon.com/best-sellers/"],
            ),
        ),
    ])
}
