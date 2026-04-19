package browser

import (
	"testing"
	"time"
)

func TestNightModeWindowAndDelayMultiplier(t *testing.T) {
	if !IsNightModeActiveAt(1, 0, 6) {
		t.Fatal("expected night mode active at 1am")
	}
	if IsNightModeActiveAt(14, 0, 6) {
		t.Fatal("did not expect night mode active at 2pm")
	}
	profile := DefaultBehaviorProfile()
	if NightModeDelayMultiplierAt(2, profile) <= 1.0 {
		t.Fatal("expected elevated delay multiplier at night")
	}
}

func TestRandomizedActionDelayRespectsFlags(t *testing.T) {
	profile := DefaultBehaviorProfile()
	delay := RandomizedActionDelay("click", profile, time.Date(2026, 1, 1, 2, 0, 0, 0, time.UTC))
	if delay <= 0 {
		t.Fatalf("expected randomized delay, got %s", delay)
	}
	profile.BehaviorRandomization = false
	if RandomizedActionDelay("click", profile, time.Now()) != 0 {
		t.Fatal("expected zero delay when randomization disabled")
	}
}
