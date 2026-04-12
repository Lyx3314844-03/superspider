use rustspider::cookie::{Cookie, CookieJar};
use rustspider::error::{ErrorHandler, ErrorType, SpiderError};
use rustspider::parser::{HTMLParser, JSONParser};
use rustspider::preflight::{run_preflight, PreflightOptions};
use rustspider::queue::{PersistentPriorityQueue, QueueItem};
use rustspider::retry::{RetryConfig, RetryHandler, RetryStrategy};
use rustspider::spider::SpiderBuilder;
use std::time::Duration;

#[test]
fn spider_builder_creates_engine_with_named_stats() {
    let engine = SpiderBuilder::new()
        .name("integration")
        .concurrency(2)
        .max_requests(5)
        .build()
        .expect("engine should build");

    let stats = engine.get_stats();
    assert_eq!(stats.name, "integration");
    assert_eq!(stats.requested, 0);
    assert_eq!(stats.handled, 0);
}

#[test]
fn html_parser_extracts_expected_fields() {
    let parser = HTMLParser::new(
        r#"<html><head><title>RustSpider</title></head><body><a href="https://example.com">example</a></body></html>"#,
    );

    assert_eq!(parser.title(), Some("RustSpider".to_string()));
    assert_eq!(parser.links(), vec!["https://example.com".to_string()]);
}

#[test]
fn json_parser_reads_nested_values() {
    let parser = JSONParser::new(r#"{"user":{"name":"rust","scores":[1,2,3]}}"#)
        .expect("json parser should be created");

    assert_eq!(parser.get_string("user.name"), Some("rust".to_string()));
    assert_eq!(parser.get_i64("user.scores.1"), Some(2));
}

#[test]
fn preflight_reports_success_for_temp_directory() {
    let temp_dir = std::env::temp_dir().join("rustspider-integration-preflight");
    let report = run_preflight(&PreflightOptions::new().with_writable_path(&temp_dir));

    assert!(report.is_success(), "report: {:?}", report.checks);
    let _ = std::fs::remove_dir_all(temp_dir);
}

#[test]
fn error_handler_tracks_recorded_errors() {
    let handler = ErrorHandler::new(5);

    assert!(handler.handle(&SpiderError::with_type(
        "parse failed",
        ErrorType::ParseError,
    )));
    assert!(handler.handle(&SpiderError::with_type(
        "network timeout",
        ErrorType::TimeoutError,
    )));

    let summary = handler.get_error_summary();
    assert_eq!(summary.total_errors, 2);
    assert_eq!(summary.fatal_errors, 0);
}

#[test]
fn cookie_jar_can_store_and_read_cookie() {
    let mut jar = CookieJar::new();
    jar.set(Cookie::new("session", "abc123", "example.com"));

    let cookie = jar
        .get("session", "example.com")
        .expect("cookie should exist");
    assert_eq!(cookie.value, "abc123");
    assert_eq!(jar.count(), 1);
}

#[test]
fn persistent_queue_round_trip_works_in_memory() {
    let queue = PersistentPriorityQueue::in_memory(10).expect("queue should initialize");
    assert!(queue
        .put(QueueItem::new("https://example.com".to_string()))
        .unwrap());

    let item = queue.get().expect("queue read should succeed");
    assert_eq!(
        item.expect("queue item should exist").url,
        "https://example.com"
    );
}

#[test]
fn retry_handler_retries_failed_operation_once() {
    let handler = RetryHandler::new(RetryConfig {
        max_retries: 1,
        strategy: RetryStrategy::Fixed,
        base_delay: Duration::from_millis(1),
        max_delay: Duration::from_millis(1),
        jitter_factor: 0.0,
        retry_on_status_codes: vec![],
    });

    let mut attempts = 0usize;
    let result = handler.execute_with_retry(|| {
        attempts += 1;
        if attempts == 1 {
            Err("transient")
        } else {
            Ok("ok")
        }
    });

    assert!(result.success);
    assert_eq!(result.attempts, 2);
    assert_eq!(result.result, Some("ok"));
}
