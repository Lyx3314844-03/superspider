//! Stable benchmark-smoke coverage for rustspider.
//!
//! This target intentionally avoids nightly `test` benches so the repository
//! can keep `cargo clippy --all-targets -D warnings` green on stable toolchains.

use std::hint::black_box;

use rustspider::cookie::{Cookie, CookieJar};
use rustspider::parser::HTMLParser;
use rustspider::performance::{CircuitBreaker, ContentFingerprinter, RateLimiter};
use rustspider::queue::{PersistentPriorityQueue, QueueItem};
use rustspider::spider::{SpiderConfig, SpiderEngine};

#[test]
fn benchmark_smoke_spider_engine_creation() {
    let config = SpiderConfig::default();
    let engine = SpiderEngine::new(config).expect("engine should build");
    black_box(engine);
}

#[test]
fn benchmark_smoke_spider_add_url() {
    let config = SpiderConfig::default();
    let engine = SpiderEngine::new(config).expect("engine should build");

    engine
        .add_url("https://example.com")
        .expect("url should enqueue");
}

#[test]
fn benchmark_smoke_rate_limiter_wait() {
    let limiter = RateLimiter::new(10_000, 1);
    limiter.wait();
}

#[test]
fn benchmark_smoke_circuit_breaker() {
    let cb = CircuitBreaker::new(1000, 100, 60);
    assert!(cb.allow());
    cb.record_success();
}

#[test]
fn benchmark_smoke_content_fingerprint() {
    let fingerprinter = ContentFingerprinter::new();
    let content = "This is a test content for fingerprinting. ".repeat(100);
    black_box(fingerprinter.is_duplicate(&content));
}

#[test]
fn benchmark_smoke_html_parser() {
    let html = r#"
        <!DOCTYPE html>
        <html>
        <head><title>Test Page Title</title></head>
        <body>
            <div class="content">
                <a href="/link1">Link 1</a>
            </div>
        </body>
        </html>
    "#;

    let parser = HTMLParser::new(html);
    black_box(parser.title());
    black_box(parser.css(".content"));
    black_box(parser.links());
}

#[test]
fn benchmark_smoke_queue_push_pop() {
    let queue = PersistentPriorityQueue::in_memory(16).expect("queue should build");
    let item = QueueItem::new("https://example.com/bench".to_string()).with_priority(1);

    assert!(queue.put(item).expect("push should succeed"));
    black_box(queue.get().expect("pop should succeed"));
}

#[test]
fn benchmark_smoke_cookie_jar() {
    let mut jar = CookieJar::new();
    for i in 0..10 {
        jar.set(Cookie::new(
            &format!("cookie_{i}"),
            &format!("value_{i}"),
            "example.com",
        ));
    }

    for i in 0..10 {
        black_box(jar.get(&format!("cookie_{i}"), "example.com"));
    }
}

#[test]
fn benchmark_smoke_memory_and_hash() {
    let data = vec![0u8; 1024];
    let text = "test data for hashing".repeat(100);
    black_box(data);
    black_box(text);
}

fn main() {}
