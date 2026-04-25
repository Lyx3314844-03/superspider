package research

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestCrawlerSelectorRecommendsBrowserForEcommerceListing(t *testing.T) {
	selection := NewCrawlerSelector().Select(CrawlerSelectionRequest{
		URL: "https://shop.example.com/search?q=phone",
		Content: `<html><script>window.__NEXT_DATA__ = {"items":[]}</script><body>
			<input type="search"><div class="product-list"><div class="sku-item">SKU-1</div>
			<span class="price">￥10</span><button>加入购物车</button></div></body></html>`,
	})

	if selection.Scenario != "ecommerce_listing" || selection.CrawlerType != "ecommerce_search" {
		t.Fatalf("unexpected selection: %#v", selection)
	}
	if selection.RecommendedRunner != "browser" {
		t.Fatalf("expected browser first, got %s", selection.RecommendedRunner)
	}
	if !containsString(selection.Capabilities, "commerce_fields") || !containsString(selection.ReasonCodes, "signal:has_price") {
		t.Fatalf("expected commerce capabilities and price reason: %#v", selection)
	}
	if selection.Confidence < 0.7 {
		t.Fatalf("expected useful confidence, got %f", selection.Confidence)
	}
	payload := selection.ToMap()
	if payload["recommended_runner"] != "browser" {
		t.Fatalf("unexpected contract payload: %#v", payload)
	}
	encoded, err := json.Marshal(selection)
	if err != nil || !strings.Contains(string(encoded), `"recommended_runner":"browser"`) {
		t.Fatalf("expected snake_case JSON contract, payload=%s err=%v", string(encoded), err)
	}
}

func TestCrawlerSelectorCapturesLoginRisk(t *testing.T) {
	selection := NewCrawlerSelector().Select(CrawlerSelectionRequest{
		URL:     "https://secure.example.com/login",
		Content: `<form><input type="password"><div>验证码</div></form>`,
	})

	if selection.Scenario != "authenticated_session" || selection.RiskLevel != "high" {
		t.Fatalf("unexpected login selection: %#v", selection)
	}
	if !containsString(selection.Capabilities, "session_cookies") || !containsString(selection.Capabilities, "anti_bot_evidence") {
		t.Fatalf("expected login/captcha capabilities: %#v", selection.Capabilities)
	}
	joined := strings.Join(selection.FallbackPlan, "\n")
	if !strings.Contains(strings.ToLower(joined), "captcha") {
		t.Fatalf("expected captcha fallback plan: %#v", selection.FallbackPlan)
	}
}

func TestCrawlerSelectorMatchesSharedEcommerceGoldenContract(t *testing.T) {
	root := filepath.Clean(filepath.Join("..", ".."))
	html, err := os.ReadFile(filepath.Join(root, "examples", "crawler-selection", "ecommerce-search-input.html"))
	if err != nil {
		t.Fatalf("read shared fixture: %v", err)
	}
	goldenBytes, err := os.ReadFile(filepath.Join(root, "examples", "crawler-selection", "ecommerce-search-selection.json"))
	if err != nil {
		t.Fatalf("read shared golden: %v", err)
	}
	var golden map[string]interface{}
	if err := json.Unmarshal(goldenBytes, &golden); err != nil {
		t.Fatalf("parse shared golden: %v", err)
	}

	selection := NewCrawlerSelector().Select(CrawlerSelectionRequest{
		URL:     "https://shop.example.com/search?q=phone",
		Content: string(html),
	})
	payload := selection.ToMap()

	for _, field := range []string{"scenario", "crawler_type", "recommended_runner", "site_family", "risk_level"} {
		if payload[field] != golden[field] {
			t.Fatalf("field %s mismatch: got %#v want %#v", field, payload[field], golden[field])
		}
	}
	if selection.Confidence != golden["confidence"].(float64) {
		t.Fatalf("confidence mismatch: got %v want %v", selection.Confidence, golden["confidence"])
	}
	for _, capability := range golden["capabilities"].([]interface{}) {
		if !containsString(selection.Capabilities, capability.(string)) {
			t.Fatalf("missing golden capability %s in %#v", capability, selection.Capabilities)
		}
	}
}
