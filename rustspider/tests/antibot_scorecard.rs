use rustspider::antibot::antibot::{AkamaiBypass, AntiBotHandler, CloudflareBypass};
use rustspider::antibot::enhanced::{
    AkamaiBypass as EnhancedAkamaiBypass, BrowserFingerprint,
    CloudflareBypass as EnhancedCloudflareBypass,
};

#[test]
fn core_antibot_handler_detects_blocks_and_rotates_proxy() {
    let handler = AntiBotHandler::new();

    assert!(handler.is_blocked("captcha required", 200));
    assert!(handler.is_blocked("normal page", 429));
    assert!(!handler.is_blocked("normal page", 200));

    let proxy = handler.rotate_proxy(&[
        "http://proxy-1:8080".to_string(),
        "http://proxy-2:8080".to_string(),
    ]);
    assert!(proxy.is_some());
}

#[test]
fn core_bypass_helpers_emit_expected_headers() {
    let cloudflare = CloudflareBypass::new().get_headers();
    let akamai = AkamaiBypass::new().get_headers();

    assert!(cloudflare.contains_key("sec-ch-ua"));
    assert!(akamai.contains_key("X-Requested-With"));
}

#[test]
fn enhanced_bypass_helpers_detect_vendor_challenges() {
    let cloudflare = EnhancedCloudflareBypass::new();
    let akamai = EnhancedAkamaiBypass::new();

    assert!(
        cloudflare.detect_cloudflare("Checking your browser before accessing target.example", 503)
    );
    assert!(akamai.detect_akamai("Akamai bot manager access denied", 403));
}

#[test]
fn browser_fingerprint_and_stealth_headers_are_populated() {
    let fingerprint = BrowserFingerprint::new();
    let data = fingerprint.generate_fingerprint();
    let headers = fingerprint.generate_stealth_headers();

    assert!(!data.user_agent.is_empty());
    assert!(!data.screen.is_empty());
    assert!(!data.canvas_hash.is_empty());
    assert!(headers.contains_key("Sec-Ch-Ua"));
    assert!(headers.contains_key("DNT"));
}
