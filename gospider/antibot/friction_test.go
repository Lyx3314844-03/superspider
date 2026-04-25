package antibot

import (
	"net/http"
	"testing"
	"time"
)

func TestAnalyzeAccessFrictionHonorsRetryAfter(t *testing.T) {
	headers := http.Header{"Retry-After": []string{"15"}}
	report := AnalyzeAccessFriction(http.StatusTooManyRequests, headers, "too many requests", "https://shop.example")

	if report.Level != "high" {
		t.Fatalf("expected high level, got %q", report.Level)
	}
	if report.RetryAfterSeconds != 15 {
		t.Fatalf("expected retry-after seconds, got %d", report.RetryAfterSeconds)
	}
	throttle := report.CapabilityPlan["throttle"].(map[string]any)
	if throttle["crawl_delay_seconds"] != 30 {
		t.Fatalf("expected retry-after delay in capability plan: %#v", throttle)
	}
	if !containsAny(report.Signals, "rate-limited") || !containsAny(report.RecommendedActions, "honor-retry-after") {
		t.Fatalf("expected rate limit signal and action: %#v %#v", report.Signals, report.RecommendedActions)
	}
}

func TestAnalyzeAccessFrictionRecommendsBrowserHumanCheckpoint(t *testing.T) {
	report := AnalyzeAccessFriction(http.StatusOK, nil, "<html>hcaptcha 安全验证</html>", "https://shop.example/challenge")

	if report.Level != "high" || !report.Blocked {
		t.Fatalf("expected high blocked report: %#v", report)
	}
	if !report.ShouldUpgradeToBrowser || !report.RequiresHumanAccess {
		t.Fatalf("expected browser and human checkpoint recommendation: %#v", report)
	}
	if report.ChallengeHandoff["required"] != true || report.ChallengeHandoff["method"] != "human-authorized-browser-session" {
		t.Fatalf("expected human handoff metadata: %#v", report.ChallengeHandoff)
	}
	session := report.CapabilityPlan["session"].(map[string]any)
	if session["reuse_only_after_authorized_access"] != true {
		t.Fatalf("expected authorized session reuse gate: %#v", session)
	}
	if !containsAny(report.RecommendedActions, "pause-for-human-access") {
		t.Fatalf("expected human action: %#v", report.RecommendedActions)
	}
}

func TestAnalyzeAccessFrictionParsesRetryAfterHTTPDate(t *testing.T) {
	retryAt := time.Now().Add(2 * time.Minute).UTC().Format(http.TimeFormat)
	headers := http.Header{"Retry-After": []string{retryAt}}

	report := AnalyzeAccessFriction(http.StatusTooManyRequests, headers, "too many requests", "https://shop.example")

	if report.RetryAfterSeconds <= 0 {
		t.Fatalf("expected positive retry-after seconds, got %d", report.RetryAfterSeconds)
	}
}

func TestAnalyzeAccessFrictionRoutesSignatureFingerprintToDevToolsNodeReverse(t *testing.T) {
	report := AnalyzeAccessFriction(
		http.StatusOK,
		nil,
		`<script>window._signature='x'; const token = CryptoJS.MD5(navigator.webdriver + 'x-bogus').toString();</script>`,
		"https://example.com/api/list?X-Bogus=abc",
	)

	if report.Level != "medium" || !report.ShouldUpgradeToBrowser {
		t.Fatalf("expected medium browser-upgrade report: %#v", report)
	}
	if !containsAny(report.Signals, "js-signature") || !containsAny(report.Signals, "fingerprint-required") {
		t.Fatalf("expected js signature and fingerprint signals: %#v", report.Signals)
	}
	if !containsAny(report.RecommendedActions, "capture-devtools-network") || !containsAny(report.RecommendedActions, "run-nodejs-reverse-analysis") {
		t.Fatalf("expected devtools/node reverse actions: %#v", report.RecommendedActions)
	}
	transport := report.CapabilityPlan["transport_order"].([]string)
	if !containsAny(transport, "devtools-analysis") || !containsAny(transport, "node-reverse-analysis") {
		t.Fatalf("expected devtools/node reverse transport order: %#v", transport)
	}
}
