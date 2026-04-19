package antibot

import "time"

// NightModePolicy lowers crawl aggressiveness during configured quiet hours.
type NightModePolicy struct {
	Enabled         bool
	StartHour       int
	EndHour         int
	DelayMultiplier float64
	RateLimitFactor float64
}

// DefaultNightModePolicy mirrors the shared framework defaults used by pyspider.
func DefaultNightModePolicy() NightModePolicy {
	return NightModePolicy{
		Enabled:         true,
		StartHour:       23,
		EndHour:         6,
		DelayMultiplier: 1.5,
		RateLimitFactor: 0.5,
	}
}

// IsActive reports whether the provided time falls into the configured quiet-hour window.
func (p NightModePolicy) IsActive(at time.Time) bool {
	if !p.Enabled {
		return false
	}
	hour := at.Hour()
	if p.StartHour == p.EndHour {
		return true
	}
	if p.StartHour < p.EndHour {
		return hour >= p.StartHour && hour < p.EndHour
	}
	return hour >= p.StartHour || hour < p.EndHour
}

// ApplyDelay scales a delay when the policy is active.
func (p NightModePolicy) ApplyDelay(base time.Duration, at time.Time) time.Duration {
	if base <= 0 || !p.IsActive(at) {
		return base
	}
	adjusted := time.Duration(float64(base) * p.DelayMultiplier)
	if adjusted < base {
		return base
	}
	return adjusted
}

// ApplyRateLimit scales a rate limit when the policy is active.
func (p NightModePolicy) ApplyRateLimit(base float64, at time.Time) float64 {
	if base <= 0 || !p.IsActive(at) {
		return base
	}
	adjusted := base * p.RateLimitFactor
	if adjusted <= 0 {
		return base
	}
	return adjusted
}
