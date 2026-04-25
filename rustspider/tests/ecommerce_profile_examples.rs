#[path = "../examples/ecommerce/detector.rs"]
mod detector;
#[path = "../examples/ecommerce/profile.rs"]
mod profile;

use rustspider::scrapy::Response;
use serde_json::json;
use std::collections::BTreeMap;

#[test]
fn example_profile_falls_back_to_generic_for_unknown_family() {
    let profile = profile::profile_for_family("unknown-shop");
    assert_eq!(
        profile.catalog_url,
        "https://shop.example.com/search?q=demo"
    );
}

#[test]
fn example_profile_supports_social_commerce_families() {
    assert_eq!(
        profile::profile_for_family("xiaohongshu").catalog_url,
        "https://www.xiaohongshu.com/search_result?keyword=iphone"
    );
    assert_eq!(
        profile::profile_for_family("douyin-shop").detail_url,
        "https://haohuo.jinritemai.com/views/product/item2?id=100000000000"
    );
}

#[test]
fn example_site_family_detection_recognizes_social_commerce_hosts() {
    let response = Response {
        url: "https://www.xiaohongshu.com/explore/demo".to_string(),
        status_code: 200,
        headers: BTreeMap::new(),
        text: String::new(),
        request: None,
    };
    assert_eq!(profile::site_family_from_response(&response), "xiaohongshu");

    let response = Response {
        url: "https://haohuo.jinritemai.com/views/product/item2?id=1".to_string(),
        status_code: 200,
        headers: BTreeMap::new(),
        text: String::new(),
        request: None,
    };
    assert_eq!(profile::site_family_from_response(&response), "douyin-shop");
}

#[test]
fn example_profile_extracts_bootstrap_products() {
    let html = r#"<html><head><script>window.__NEXT_DATA__={"props":{"pageProps":{"product":{"sku":"SKU-1","name":"Demo Phone","price":"6999","image":"https://cdn.example.com/p1.jpg","shopName":"Demo Shop","aggregateRating":{"ratingValue":"4.9","reviewCount":"123"}}}}};</script></head></html>"#;
    let products = profile::extract_bootstrap_products(html, 5);
    assert!(!products.is_empty());
    assert_eq!(
        products[0].get("sku").and_then(|value| value.as_str()),
        Some("SKU-1")
    );
    assert_eq!(
        products[0].get("price").and_then(|value| value.as_str()),
        Some("6999")
    );
}

#[test]
fn example_profile_extracts_api_candidates_from_embedded_json() {
    let html = r#"<html><head><script type="application/json">{"detailApi":"api/item/detail?id=1","reviewApi":"/api/review/list?sku=1"}</script></head></html>"#;
    let candidates = profile::extract_api_candidates(html, 10);
    assert!(candidates
        .iter()
        .any(|candidate| candidate == "api/item/detail?id=1"));
}

#[test]
fn example_profile_builds_api_job_templates() {
    let templates = profile::build_api_job_templates(
        "https://shop.example.com/item/sku-1",
        "generic",
        &["api/item/detail?id=1".to_string()],
        &["SKU-1".to_string()],
        10,
    );
    assert!(!templates.is_empty());
    assert_eq!(
        templates[0].get("runtime").and_then(|value| value.as_str()),
        Some("http")
    );
}

#[test]
fn example_profile_builds_network_replay_templates() {
    let artifact = json!({
        "network_events": [
            {
                "url": "https://shop.example.com/_next/static/app.js",
                "method": "GET",
                "status": 200,
                "resource_type": "script"
            },
            {
                "url": "https://shop.example.com/api/item/detail?id=1",
                "method": "POST",
                "status": 200,
                "resource_type": "fetch",
                "request_headers": {
                    "Content-Type": "application/json",
                    "Cookie": "session=secret"
                },
                "post_data": "{\"sku\":\"SKU-1\"}",
                "response_headers": {
                    "content-type": "application/json"
                }
            }
        ]
    });

    let entries = profile::normalize_network_entries(&artifact, 10);
    assert_eq!(entries.len(), 2);
    let candidates = profile::extract_network_api_candidates(&artifact, 10);
    assert_eq!(
        candidates,
        vec!["https://shop.example.com/api/item/detail?id=1".to_string()]
    );
    let templates = profile::build_network_replay_job_templates(
        "https://shop.example.com/item/sku-1",
        "generic",
        &artifact,
        10,
    );
    assert_eq!(templates.len(), 1);
    let target = templates[0]
        .get("target")
        .and_then(|value| value.as_object())
        .unwrap();
    assert_eq!(
        target.get("method").and_then(|value| value.as_str()),
        Some("POST")
    );
    assert_eq!(
        target.get("body").and_then(|value| value.as_str()),
        Some("{\"sku\":\"SKU-1\"}")
    );
    let headers = target
        .get("headers")
        .and_then(|value| value.as_object())
        .unwrap();
    assert!(!headers.contains_key("Cookie"));
}

#[test]
fn example_detector_identifies_marketplace_and_jsonld() {
    let html = r#"<script type="application/ld+json">{"@type":"Product","name":"Demo","offers":{"price":"9.99","priceCurrency":"USD"}}</script><button>Add to cart</button>"#;
    let result = detector::detect_ecommerce_site("https://www.amazon.com/dp/B0TEST", html);

    assert!(result.is_ecommerce);
    assert_eq!(result.site_family, "amazon");
    assert!(result.has_jsonld);
}
