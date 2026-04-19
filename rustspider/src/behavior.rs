use rand::Rng;

#[derive(Debug, Clone)]
pub struct BehaviorProfile {
    pub behavior_randomization: bool,
    pub night_mode: bool,
    pub night_mode_start_hour: u8,
    pub night_mode_end_hour: u8,
}

impl Default for BehaviorProfile {
    fn default() -> Self {
        Self {
            behavior_randomization: true,
            night_mode: true,
            night_mode_start_hour: 0,
            night_mode_end_hour: 6,
        }
    }
}

pub fn is_night_mode_active_at(hour: u8, start_hour: u8, end_hour: u8) -> bool {
    if start_hour == end_hour {
        return false;
    }
    if start_hour < end_hour {
        hour >= start_hour && hour < end_hour
    } else {
        hour >= start_hour || hour < end_hour
    }
}

pub fn randomized_action_delay_ms(action: &str, hour: u8, profile: &BehaviorProfile) -> u64 {
    if !profile.behavior_randomization {
        return 0;
    }
    let base = match action {
        "click" => 45_u64,
        "type" => 35_u64,
        "hover" => 55_u64,
        "scroll" => 65_u64,
        _ => 30_u64,
    };
    let jitter = rand::thread_rng().gen_range(10_u64..50_u64);
    let multiplier = if profile.night_mode
        && is_night_mode_active_at(
            hour,
            profile.night_mode_start_hour,
            profile.night_mode_end_hour,
        ) {
        1.75
    } else {
        1.0
    };
    ((base + jitter) as f64 * multiplier).round() as u64
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn night_mode_window_and_delay_work() {
        assert!(is_night_mode_active_at(1, 0, 6));
        assert!(!is_night_mode_active_at(14, 0, 6));
        let delay = randomized_action_delay_ms("click", 2, &BehaviorProfile::default());
        assert!(delay > 0);
    }
}
