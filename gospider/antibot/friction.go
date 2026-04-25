package antibot

import (
	"net/http"
	"strconv"
	"strings"
	"time"
)

type AccessFrictionReport struct {
	Level                  string         `json:"level"`
	Signals                []string       `json:"signals"`
	RecommendedActions     []string       `json:"recommended_actions"`
	RetryAfterSeconds      int            `json:"retry_after_seconds,omitempty"`
	ShouldUpgradeToBrowser bool           `json:"should_upgrade_to_browser"`
	RequiresHumanAccess    bool           `json:"requires_human_access"`
	ChallengeHandoff       map[string]any `json:"challenge_handoff"`
	CapabilityPlan         map[string]any `json:"capability_plan"`
	Blocked                bool           `json:"blocked"`
}

func AnalyzeAccessFriction(statusCode int, headers http.Header, html string, targetURL string) AccessFrictionReport {
	haystack := strings.ToLower(targetURL + "\n" + html + "\n" + headerHaystack(headers))
	signals := []string{}

	switch statusCode {
	case http.StatusUnauthorized, http.StatusForbidden:
		signals = append(signals, "auth-or-forbidden")
	case http.StatusTooManyRequests:
		signals = append(signals, "rate-limited")
	case http.StatusServiceUnavailable, 520, 521, 522:
		signals = append(signals, "temporary-gateway-or-challenge")
	}

	keywordGroups := map[string][]string{
		"captcha":                   {"captcha", "recaptcha", "hcaptcha", "turnstile", "验证码", "滑块"},
		"slider-captcha":            {"geetest", "gt_captcha", "nc_token", "aliyuncaptcha", "tencentcaptcha", "滑块验证", "拖动滑块"},
		"managed-browser-challenge": {"cf-chl", "checking your browser", "browser verification", "challenge-platform", "please enable javascript"},
		"request-blocked":           {"access denied", "request blocked", "request rejected", "被拒绝", "封禁", "访问过于频繁"},
		"auth-required":             {"login", "sign in", "扫码", "登录", "安全验证"},
		"waf-vendor":                {"cloudflare", "akamai", "imperva", "datadome", "perimeterx", "aliyun", "tencent", "bytedance", "dun.163"},
		"risk-control":              {"risk control", "风险", "异常访问", "suspicious activity", "环境异常", "账号存在风险"},
		"js-signature":              {"x-bogus", "a_bogus", "mstoken", "m_h5_tk", "h5st", "_signature", "cryptojs", "__webpack_require__", "webpackchunk"},
		"fingerprint-required":      {"navigator.webdriver", "canvas fingerprint", "webgl", "deviceid", "fpcollect", "sec-ch-ua"},
	}
	for signal, patterns := range keywordGroups {
		for _, pattern := range patterns {
			if strings.Contains(haystack, strings.ToLower(pattern)) {
				signals = append(signals, signal)
				break
			}
		}
	}

	if headers.Get("Retry-After") != "" {
		signals = append(signals, "retry-after")
	}
	if headers.Get("CF-Ray") != "" || headers.Get("X-DataDome") != "" || headers.Get("X-Akamai-Transformed") != "" {
		signals = append(signals, "waf-vendor")
	}
	htmlLower := strings.ToLower(html)
	if statusCode == http.StatusOK && len(strings.TrimSpace(html)) > 0 && len(strings.TrimSpace(html)) < 300 && (strings.Contains(htmlLower, "<script") || strings.Contains(htmlLower, "enable javascript") || strings.Contains(htmlLower, "window.location")) {
		signals = append(signals, "empty-or-script-shell")
	}

	signals = dedupeStrings(signals)
	retryAfter := parseRetryAfterSeconds(headers.Get("Retry-After"))
	level := accessFrictionLevel(statusCode, signals)
	actions := accessFrictionActions(signals, retryAfter)

	return AccessFrictionReport{
		Level:                  level,
		Signals:                signals,
		RecommendedActions:     actions,
		RetryAfterSeconds:      retryAfter,
		ShouldUpgradeToBrowser: containsAny(signals, "managed-browser-challenge", "captcha", "slider-captcha", "auth-required", "waf-vendor", "js-signature", "fingerprint-required", "empty-or-script-shell"),
		RequiresHumanAccess:    containsAny(signals, "captcha", "slider-captcha", "auth-required"),
		ChallengeHandoff:       challengeHandoff(signals),
		CapabilityPlan:         capabilityPlan(level, signals, retryAfter),
		Blocked:                level == "medium" || level == "high",
	}
}

func headerHaystack(headers http.Header) string {
	var parts []string
	for key, values := range headers {
		parts = append(parts, strings.ToLower(key)+": "+strings.Join(values, " "))
	}
	return strings.Join(parts, "\n")
}

func parseRetryAfterSeconds(value string) int {
	value = strings.TrimSpace(value)
	if value == "" {
		return 0
	}
	seconds, err := strconv.Atoi(value)
	if err != nil || seconds < 0 {
		if retryAt, parseErr := http.ParseTime(value); parseErr == nil {
			return max(0, int(time.Until(retryAt).Seconds()))
		}
		return 0
	}
	return seconds
}

func accessFrictionLevel(statusCode int, signals []string) string {
	if containsAny(signals, "captcha", "slider-captcha", "auth-required", "request-blocked") {
		return "high"
	}
	if statusCode == http.StatusUnauthorized || statusCode == http.StatusForbidden || statusCode == http.StatusTooManyRequests {
		return "high"
	}
	if containsAny(signals, "managed-browser-challenge", "waf-vendor", "risk-control", "js-signature", "fingerprint-required", "empty-or-script-shell") {
		return "medium"
	}
	if len(signals) > 0 {
		return "low"
	}
	return "none"
}

func accessFrictionActions(signals []string, retryAfter int) []string {
	actions := []string{}
	if retryAfter > 0 || containsAny(signals, "rate-limited") {
		actions = append(actions, "honor-retry-after", "reduce-concurrency", "increase-crawl-delay")
	}
	if containsAny(signals, "managed-browser-challenge", "waf-vendor", "empty-or-script-shell") {
		actions = append(actions, "render-with-browser", "persist-session-state", "capture-html-screenshot-har")
	}
	if containsAny(signals, "js-signature", "fingerprint-required") {
		actions = append(actions, "capture-devtools-network", "run-nodejs-reverse-analysis", "replay-authorized-session-only")
	}
	if containsAny(signals, "captcha", "slider-captcha", "auth-required") {
		actions = append(actions, "pause-for-human-access", "document-authorization-requirement")
	}
	if containsAny(signals, "request-blocked") {
		actions = append(actions, "stop-or-seek-site-permission")
	}
	actions = append(actions, "respect-robots-and-terms")
	return dedupeStrings(actions)
}

func dedupeStrings(items []string) []string {
	seen := map[string]bool{}
	out := []string{}
	for _, item := range items {
		if !seen[item] {
			seen[item] = true
			out = append(out, item)
		}
	}
	return out
}

func containsAny(items []string, candidates ...string) bool {
	for _, item := range items {
		for _, candidate := range candidates {
			if item == candidate {
				return true
			}
		}
	}
	return false
}

func challengeHandoff(signals []string) map[string]any {
	if !containsAny(signals, "captcha", "slider-captcha", "auth-required", "risk-control") {
		return map[string]any{
			"required": false,
			"method":   "none",
			"resume":   "automatic",
		}
	}
	return map[string]any{
		"required":        true,
		"method":          "human-authorized-browser-session",
		"resume":          "after-challenge-cleared-and-session-persisted",
		"artifacts":       []string{"screenshot", "html", "cookies-or-storage-state", "network-summary"},
		"stop_conditions": []string{"explicit-access-denied", "robots-disallow", "missing-site-permission"},
	}
}

func capabilityPlan(level string, signals []string, retryAfter int) map[string]any {
	transportOrder := []string{"http"}
	if containsAny(signals, "managed-browser-challenge", "waf-vendor", "captcha", "slider-captcha", "auth-required", "empty-or-script-shell") {
		transportOrder = append(transportOrder, "browser-render", "authorized-session-replay")
	}
	if containsAny(signals, "js-signature", "fingerprint-required") {
		transportOrder = append(transportOrder, "devtools-analysis", "node-reverse-analysis")
	}
	if containsAny(signals, "request-blocked") {
		transportOrder = append(transportOrder, "stop-until-permission")
	}

	crawlDelay := retryAfter
	if crawlDelay <= 0 {
		crawlDelay = 1
	}
	if level == "medium" && crawlDelay < 5 {
		crawlDelay = 5
	}
	if level == "high" && crawlDelay < 30 {
		crawlDelay = 30
	}

	concurrency := 2
	if level == "medium" || level == "high" {
		concurrency = 1
	}
	retryBudget := 2
	if level == "high" {
		retryBudget = 1
	}
	if containsAny(signals, "request-blocked") {
		retryBudget = 0
	}

	return map[string]any{
		"mode":            "maximum-compliant",
		"transport_order": dedupeStrings(transportOrder),
		"throttle": map[string]any{
			"concurrency":         concurrency,
			"crawl_delay_seconds": crawlDelay,
			"jitter_ratio":        0.35,
			"honor_retry_after":   true,
		},
		"session": map[string]any{
			"persist_storage_state":              true,
			"reuse_only_after_authorized_access": containsAny(signals, "captcha", "slider-captcha", "auth-required", "risk-control"),
			"isolate_by_site":                    true,
		},
		"artifacts":       []string{"html", "screenshot", "cookies-or-storage-state", "network-summary", "friction-report"},
		"retry_budget":    retryBudget,
		"stop_conditions": []string{"robots-disallow", "explicit-access-denied", "missing-site-permission"},
	}
}
