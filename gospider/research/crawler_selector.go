package research

import (
	"fmt"
	"math"
)

type CrawlerSelectionRequest struct {
	URL          string `json:"url"`
	Content      string `json:"content,omitempty"`
	ScenarioHint string `json:"scenario_hint,omitempty"`
}

type CrawlerSelection struct {
	Scenario          string      `json:"scenario"`
	CrawlerType       string      `json:"crawler_type"`
	RecommendedRunner string      `json:"recommended_runner"`
	RunnerOrder       []string    `json:"runner_order"`
	SiteFamily        string      `json:"site_family"`
	RiskLevel         string      `json:"risk_level"`
	Capabilities      []string    `json:"capabilities"`
	StrategyHints     []string    `json:"strategy_hints"`
	JobTemplates      []string    `json:"job_templates"`
	FallbackPlan      []string    `json:"fallback_plan"`
	StopConditions    []string    `json:"stop_conditions"`
	Confidence        float64     `json:"confidence"`
	ReasonCodes       []string    `json:"reason_codes"`
	Profile           SiteProfile `json:"profile"`
}

func (s CrawlerSelection) ToMap() map[string]interface{} {
	return map[string]interface{}{
		"scenario":           s.Scenario,
		"crawler_type":       s.CrawlerType,
		"recommended_runner": s.RecommendedRunner,
		"runner_order":       append([]string(nil), s.RunnerOrder...),
		"site_family":        s.SiteFamily,
		"risk_level":         s.RiskLevel,
		"capabilities":       append([]string(nil), s.Capabilities...),
		"strategy_hints":     append([]string(nil), s.StrategyHints...),
		"job_templates":      append([]string(nil), s.JobTemplates...),
		"fallback_plan":      append([]string(nil), s.FallbackPlan...),
		"stop_conditions":    append([]string(nil), s.StopConditions...),
		"confidence":         s.Confidence,
		"reason_codes":       append([]string(nil), s.ReasonCodes...),
		"profile":            s.Profile,
	}
}

type CrawlerSelector struct{}

func NewCrawlerSelector() *CrawlerSelector {
	return &CrawlerSelector{}
}

func (s *CrawlerSelector) Select(request CrawlerSelectionRequest) CrawlerSelection {
	content := request.Content
	if content == "" {
		content = fmt.Sprintf("<title>%s</title>", request.URL)
	}
	profile := profileSite(request.URL, content)
	scenario := request.ScenarioHint
	if scenario == "" {
		scenario = selectionScenario(profile)
	}
	runnerOrder := profile.RunnerOrder
	if len(runnerOrder) == 0 {
		runnerOrder = []string{"http", "browser"}
	}
	return CrawlerSelection{
		Scenario:          scenario,
		CrawlerType:       profile.CrawlerType,
		RecommendedRunner: runnerOrder[0],
		RunnerOrder:       append([]string(nil), runnerOrder...),
		SiteFamily:        profile.SiteFamily,
		RiskLevel:         profile.RiskLevel,
		Capabilities:      selectionCapabilities(profile, runnerOrder),
		StrategyHints:     append([]string(nil), profile.StrategyHints...),
		JobTemplates:      append([]string(nil), profile.JobTemplates...),
		FallbackPlan:      selectionFallbackPlan(profile, runnerOrder),
		StopConditions:    selectionStopConditions(profile),
		Confidence:        selectionConfidence(profile),
		ReasonCodes:       selectionReasonCodes(profile),
		Profile:           profile,
	}
}

func selectionScenario(profile SiteProfile) string {
	switch profile.CrawlerType {
	case "login_session":
		return "authenticated_session"
	case "infinite_scroll_listing":
		return "infinite_scroll_listing"
	case "ecommerce_search":
		return "ecommerce_listing"
	case "ecommerce_detail":
		return "ecommerce_detail"
	case "hydrated_spa":
		return "javascript_hydrated_page"
	case "api_bootstrap":
		return "embedded_api_or_bootstrap_json"
	case "search_results":
		return "search_results"
	case "static_listing":
		return "static_listing"
	case "static_detail":
		return "static_detail"
	default:
		return "generic_page"
	}
}

func selectionCapabilities(profile SiteProfile, runnerOrder []string) []string {
	capabilities := []string{}
	if containsString(runnerOrder, "http") {
		capabilities = append(capabilities, "http_fetch")
	}
	if containsString(runnerOrder, "browser") {
		capabilities = append(capabilities, "browser_rendering")
	}
	if profile.Signals["has_pagination"] {
		capabilities = append(capabilities, "pagination")
	}
	if profile.Signals["has_infinite_scroll"] {
		capabilities = append(capabilities, "scroll_automation")
	}
	if profile.Signals["has_login"] {
		capabilities = append(capabilities, "session_cookies")
	}
	if profile.Signals["has_api_bootstrap"] || profile.Signals["has_graphql"] {
		capabilities = append(capabilities, "network_or_bootstrap_json")
	}
	if profile.Signals["has_price"] || profile.Signals["has_product_schema"] {
		capabilities = append(capabilities, "commerce_fields")
	}
	if profile.Signals["has_captcha"] {
		capabilities = append(capabilities, "anti_bot_evidence")
	}
	if profile.PageType == "detail" {
		capabilities = append(capabilities, "detail_extraction")
	}
	if profile.PageType == "list" {
		capabilities = append(capabilities, "listing_extraction")
	}
	return uniqueStrings(capabilities)
}

func selectionFallbackPlan(profile SiteProfile, runnerOrder []string) []string {
	var plan []string
	if len(runnerOrder) > 0 && runnerOrder[0] == "browser" {
		plan = []string{
			"render with browser and save DOM, screenshot, and network artifacts",
			"promote stable JSON/API responses into HTTP replay jobs",
			"fall back to DOM selectors only after bootstrap/network data is empty",
		}
	} else {
		plan = []string{
			"start with HTTP fetch and schema/meta/bootstrap extraction",
			"fall back to browser rendering when required fields are missing",
			"persist raw HTML and normalized fields for selector regression tests",
		}
	}
	if profile.Signals["has_captcha"] {
		plan = append(plan, "stop on captcha/challenge pages and return evidence instead of bypassing blindly")
	}
	if profile.CrawlerType == "login_session" {
		plan = append(plan, "establish authenticated storage state before queueing follow-up URLs")
	}
	return plan
}

func selectionStopConditions(profile SiteProfile) []string {
	if profile.CrawlerType == "infinite_scroll_listing" {
		return []string{
			"stop after two unchanged DOM or item-count snapshots",
			"stop when network responses repeat without new item IDs",
			"respect configured max pages/items/time budget",
		}
	}
	if profile.PageType == "list" {
		return []string{
			"stop when next-page URL repeats or disappears",
			"stop when item URLs no longer add new fingerprints",
			"respect configured max pages/items/time budget",
		}
	}
	if profile.CrawlerType == "login_session" {
		return []string{
			"stop if post-login page still contains password or captcha signals",
			"stop when authenticated session storage cannot be established",
		}
	}
	return []string{
		"stop after required fields are present and normalized",
		"stop when HTTP and browser surfaces both produce empty required fields",
	}
}

func selectionConfidence(profile SiteProfile) float64 {
	score := 0.55
	if profile.CrawlerType != "generic_http" {
		score += 0.15
	}
	if profile.SiteFamily != "generic" {
		score += 0.1
	}
	if len(profile.CandidateFields) > 0 {
		score += 0.05
	}
	if len(profile.RunnerOrder) > 1 {
		score += 0.05
	}
	if profile.RiskLevel == "medium" {
		score -= 0.05
	}
	if profile.RiskLevel == "high" {
		score -= 0.15
	}
	if score < 0.2 {
		return 0.2
	}
	if score > 0.95 {
		return 0.95
	}
	return math.Round(score*100) / 100
}

func selectionReasonCodes(profile SiteProfile) []string {
	reasons := []string{
		"crawler_type:" + profile.CrawlerType,
		"page_type:" + profile.PageType,
		"site_family:" + profile.SiteFamily,
		"risk:" + profile.RiskLevel,
	}
	for name, enabled := range profile.Signals {
		if enabled {
			reasons = append(reasons, "signal:"+name)
		}
	}
	return uniqueStrings(reasons)
}

func containsString(values []string, needle string) bool {
	for _, value := range values {
		if value == needle {
			return true
		}
	}
	return false
}
