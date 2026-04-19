use chrono::{TimeZone, Utc};
use rustspider::NightModePolicy;
use std::time::Duration;

#[test]
fn night_mode_detects_cross_midnight_window() {
    let policy = NightModePolicy::default();

    assert!(policy.is_active(Utc.with_ymd_and_hms(2026, 4, 13, 1, 0, 0).unwrap()));
    assert!(!policy.is_active(Utc.with_ymd_and_hms(2026, 4, 13, 14, 0, 0).unwrap()));
}

#[test]
fn night_mode_scales_delay_and_rate_limit() {
    let policy = NightModePolicy::default();
    let at = Utc.with_ymd_and_hms(2026, 4, 13, 23, 30, 0).unwrap();

    assert_eq!(
        policy.apply_delay(Duration::from_secs(2), at),
        Duration::from_secs(3)
    );
    assert_eq!(policy.apply_rate_limit(10.0, at), 5.0);
}
