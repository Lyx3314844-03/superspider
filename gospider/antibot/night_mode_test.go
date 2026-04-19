package antibot

import (
	"testing"
	"time"
)

func TestNightModePolicyDetectsCrossMidnightWindow(t *testing.T) {
	policy := DefaultNightModePolicy()

	if !policy.IsActive(time.Date(2026, 4, 13, 1, 0, 0, 0, time.UTC)) {
		t.Fatal("expected night mode to be active during early morning quiet hours")
	}
	if policy.IsActive(time.Date(2026, 4, 13, 14, 0, 0, 0, time.UTC)) {
		t.Fatal("expected night mode to be inactive during daytime")
	}
}

func TestNightModePolicyScalesDelayAndRateLimit(t *testing.T) {
	policy := DefaultNightModePolicy()
	night := time.Date(2026, 4, 13, 23, 30, 0, 0, time.UTC)

	if got := policy.ApplyDelay(2*time.Second, night); got != 3*time.Second {
		t.Fatalf("unexpected adjusted delay: %s", got)
	}
	if got := policy.ApplyRateLimit(10, night); got != 5 {
		t.Fatalf("unexpected adjusted rate: %v", got)
	}
}
