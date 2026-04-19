package browser

import (
	"math/rand"
	"time"
)

type BehaviorProfile struct {
	BehaviorRandomization bool
	NightMode             bool
	NightModeStartHour    int
	NightModeEndHour      int
}

func DefaultBehaviorProfile() BehaviorProfile {
	return BehaviorProfile{
		BehaviorRandomization: true,
		NightMode:             true,
		NightModeStartHour:    0,
		NightModeEndHour:      6,
	}
}

func IsNightModeActiveAt(hour int, startHour int, endHour int) bool {
	if startHour == endHour {
		return false
	}
	if startHour < endHour {
		return hour >= startHour && hour < endHour
	}
	return hour >= startHour || hour < endHour
}

func NightModeDelayMultiplierAt(hour int, profile BehaviorProfile) float64 {
	if profile.NightMode && IsNightModeActiveAt(hour, profile.NightModeStartHour, profile.NightModeEndHour) {
		return 1.75
	}
	return 1.0
}

func RandomizedActionDelay(action string, profile BehaviorProfile, now time.Time) time.Duration {
	if !profile.BehaviorRandomization {
		return 0
	}
	base := map[string]time.Duration{
		"click":  45 * time.Millisecond,
		"type":   35 * time.Millisecond,
		"hover":  55 * time.Millisecond,
		"scroll": 65 * time.Millisecond,
	}[action]
	if base == 0 {
		base = 30 * time.Millisecond
	}
	jitter := time.Duration(rand.Intn(40)) * time.Millisecond
	multiplier := NightModeDelayMultiplierAt(now.Hour(), profile)
	return time.Duration(float64(base+jitter) * multiplier)
}
