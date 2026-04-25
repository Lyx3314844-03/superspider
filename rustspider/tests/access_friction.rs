use std::collections::HashMap;

use chrono::{Duration, Utc};
use rustspider::antibot::friction::analyze_access_friction;

#[test]
fn access_friction_honors_retry_after() {
    let headers = HashMap::from([("Retry-After".to_string(), "20".to_string())]);
    let report =
        analyze_access_friction(429, &headers, "too many requests", "https://shop.example");

    assert_eq!(report.level, "high");
    assert_eq!(report.retry_after_seconds, Some(20));
    assert_eq!(
        report.capability_plan["throttle"]["crawl_delay_seconds"],
        serde_json::json!(30)
    );
    assert_eq!(report.capability_plan["retry_budget"], serde_json::json!(1));
    assert!(report.signals.contains(&"rate-limited".to_string()));
    assert!(report
        .recommended_actions
        .contains(&"honor-retry-after".to_string()));
    assert!(report.blocked);
}

#[test]
fn access_friction_recommends_browser_human_checkpoint() {
    let report = analyze_access_friction(
        200,
        &HashMap::new(),
        "<html><div>hcaptcha 安全验证</div></html>",
        "https://shop.example/challenge",
    );

    assert_eq!(report.level, "high");
    assert!(report.should_upgrade_to_browser);
    assert!(report.requires_human_access);
    assert_eq!(
        report.challenge_handoff["required"],
        serde_json::json!(true)
    );
    assert_eq!(
        report.challenge_handoff["method"],
        serde_json::json!("human-authorized-browser-session")
    );
    assert_eq!(
        report.capability_plan["session"]["reuse_only_after_authorized_access"],
        serde_json::json!(true)
    );
    assert!(report
        .recommended_actions
        .contains(&"pause-for-human-access".to_string()));
}

#[test]
fn access_friction_parses_retry_after_http_date() {
    let retry_at = (Utc::now() + Duration::minutes(2)).to_rfc2822();
    let headers = HashMap::from([("Retry-After".to_string(), retry_at)]);

    let report =
        analyze_access_friction(429, &headers, "too many requests", "https://shop.example");

    assert!(report.retry_after_seconds.unwrap_or_default() > 0);
}

#[test]
fn access_friction_routes_signature_fingerprint_pages_to_devtools_node_reverse() {
    let report = analyze_access_friction(
        200,
        &HashMap::new(),
        "<script>window._signature='x'; const token = CryptoJS.MD5(navigator.webdriver + 'x-bogus').toString();</script>",
        "https://example.com/api/list?X-Bogus=abc",
    );

    assert_eq!(report.level, "medium");
    assert!(report.should_upgrade_to_browser);
    assert!(report.signals.contains(&"js-signature".to_string()));
    assert!(report.signals.contains(&"fingerprint-required".to_string()));
    assert!(report
        .recommended_actions
        .contains(&"capture-devtools-network".to_string()));
    assert!(report
        .recommended_actions
        .contains(&"run-nodejs-reverse-analysis".to_string()));
    assert!(report.capability_plan["transport_order"]
        .as_array()
        .unwrap()
        .contains(&serde_json::json!("devtools-analysis")));
    assert!(report.capability_plan["transport_order"]
        .as_array()
        .unwrap()
        .contains(&serde_json::json!("node-reverse-analysis")));
}
