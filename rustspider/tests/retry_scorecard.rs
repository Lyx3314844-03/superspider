use std::time::Duration;

use rustspider::{RetryConfig, RetryHandler, RetryStrategy};

#[test]
fn retry_profiles_keep_expected_bounds() {
    let aggressive = RetryConfig::aggressive();
    let conservative = RetryConfig::conservative();

    assert_eq!(aggressive.max_retries, 5);
    assert_eq!(aggressive.strategy as u8, RetryStrategy::Exponential as u8);
    assert!(aggressive.base_delay <= Duration::from_secs(1));

    assert_eq!(conservative.max_retries, 2);
    assert!(conservative.base_delay >= Duration::from_secs(2));
}

#[test]
fn retry_handler_only_retries_known_status_codes() {
    let handler = RetryHandler::new(RetryConfig::default());

    assert!(handler.should_retry(Some(429)));
    assert!(handler.should_retry(Some(503)));
    assert!(!handler.should_retry(Some(404)));
    assert!(!handler.should_retry(None));
}
