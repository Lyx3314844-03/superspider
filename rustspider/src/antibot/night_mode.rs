use chrono::{DateTime, Timelike};
use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct NightModePolicy {
    pub enabled: bool,
    pub start_hour: u8,
    pub end_hour: u8,
    pub delay_multiplier: f64,
    pub rate_limit_factor: f64,
}

impl Default for NightModePolicy {
    fn default() -> Self {
        Self {
            enabled: true,
            start_hour: 23,
            end_hour: 6,
            delay_multiplier: 1.5,
            rate_limit_factor: 0.5,
        }
    }
}

impl NightModePolicy {
    pub fn is_active<Tz>(&self, at: DateTime<Tz>) -> bool
    where
        Tz: chrono::TimeZone,
    {
        if !self.enabled {
            return false;
        }
        let hour = at.hour() as u8;
        if self.start_hour == self.end_hour {
            return true;
        }
        if self.start_hour < self.end_hour {
            hour >= self.start_hour && hour < self.end_hour
        } else {
            hour >= self.start_hour || hour < self.end_hour
        }
    }

    pub fn apply_delay<Tz>(&self, base: Duration, at: DateTime<Tz>) -> Duration
    where
        Tz: chrono::TimeZone,
    {
        if base.is_zero() || !self.is_active(at) {
            return base;
        }
        let adjusted = Duration::from_secs_f64(base.as_secs_f64() * self.delay_multiplier);
        if adjusted < base {
            base
        } else {
            adjusted
        }
    }

    pub fn apply_rate_limit<Tz>(&self, base: f64, at: DateTime<Tz>) -> f64
    where
        Tz: chrono::TimeZone,
    {
        if base <= 0.0 || !self.is_active(at) {
            return base;
        }
        let adjusted = base * self.rate_limit_factor;
        if adjusted <= 0.0 {
            base
        } else {
            adjusted
        }
    }
}
