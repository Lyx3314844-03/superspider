package main

import (
	"encoding/json"
	"fmt"
	"math"
	"regexp"
	"strings"
)

// ═══════════════════════════════════════════════════════════════════════
// Universal E-commerce Site Detector (Go version)
// Auto-detects any e-commerce site from URL patterns, HTML structure,
// JSON-LD metadata, and known platform signatures.
// ═══════════════════════════════════════════════════════════════════════

// EcommerceDetectionResult holds the outcome of e-commerce site detection.
type EcommerceDetectionResult struct {
	IsEcommerce      bool     `json:"is_ecommerce"`
	Confidence       float64  `json:"confidence"`
	SiteFamily       string   `json:"site_family"`
	Platform         string   `json:"platform"`
	DetectedFeatures []string `json:"detected_features"`
	Currency         string   `json:"currency"`
	HasJSONLD        bool     `json:"has_jsonld"`
	HasNextData      bool     `json:"has_next_data"`
	PriceAPIDetected bool     `json:"price_api_detected"`
	CartURL          string   `json:"cart_url"`
	CategoryURLs     []string `json:"category_urls"`
}

// URL_SIGNATURES maps platform names to their URL regex patterns and confidence.
var URL_SIGNATURES = map[string]map[string]interface{}{
	// China
	"jd":            {"patterns": []string{`jd\.com`, `jd\.hk`}, "confidence": 0.95},
	"taobao":        {"patterns": []string{`taobao\.com`}, "confidence": 0.95},
	"tmall":         {"patterns": []string{`tmall\.com`}, "confidence": 0.95},
	"pinduoduo":     {"patterns": []string{`pinduoduo\.com`, `yangkeduo\.com`, `pdd\.com`}, "confidence": 0.95},
	"1688":          {"patterns": []string{`1688\.com`}, "confidence": 0.95},
	"suning":        {"patterns": []string{`suning\.com`}, "confidence": 0.90},
	"vip":           {"patterns": []string{`vip\.com`, `vipshop\.com`}, "confidence": 0.95},
	"dangdang":      {"patterns": []string{`dangdang\.com`}, "confidence": 0.95},
	"xiaohongshu":   {"patterns": []string{`xiaohongshu\.com`, `xhscdn\.com`}, "confidence": 0.95},
	"douyin-shop":   {"patterns": []string{`douyin\.com`, `jinritemai\.com`}, "confidence": 0.90},
	"kuaishou-shop": {"patterns": []string{`kuaishou\.com`, `kwai\.com`}, "confidence": 0.90},
	"kaola":         {"patterns": []string{`kaola\.com`}, "confidence": 0.95},
	"gome":          {"patterns": []string{`gome\.com\.cn`}, "confidence": 0.95},
	// International
	"amazon":       {"patterns": []string{`amazon\.(com|co\.uk|de|fr|it|es|co\.jp|com\.au|ca|in)`}, "confidence": 0.95},
	"ebay":         {"patterns": []string{`ebay\.(com|co\.uk|de|fr)`}, "confidence": 0.95},
	"aliexpress":   {"patterns": []string{`aliexpress\.(com|us|es|ru)`}, "confidence": 0.95},
	"lazada":       {"patterns": []string{`lazada\.(com|co|com\.my|com\.ph|co\.id|co\.th|vn)`}, "confidence": 0.95},
	"shopee":       {"patterns": []string{`shopee\.(com|co\.th|co\.id|com\.my|com\.ph|vn|tw|br)`}, "confidence": 0.95},
	"rakuten":      {"patterns": []string{`rakuten\.(co\.jp|com)`}, "confidence": 0.95},
	"walmart":      {"patterns": []string{`walmart\.(com|ca)`}, "confidence": 0.95},
	"bestbuy":      {"patterns": []string{`bestbuy\.(com|ca)`}, "confidence": 0.95},
	"target":       {"patterns": []string{`target\.com`}, "confidence": 0.95},
	"costco":       {"patterns": []string{`costco\.(com|ca)`}, "confidence": 0.95},
	"newegg":       {"patterns": []string{`newegg\.(com|ca)`}, "confidence": 0.95},
	"temu":         {"patterns": []string{`temu\.(com|co\.uk|co\.jp|de|fr)`}, "confidence": 0.95},
	"shein":        {"patterns": []string{`shein\.(com|co\.uk|co\.jp|de|fr)`}, "confidence": 0.95},
	"wish":         {"patterns": []string{`wish\.com`}, "confidence": 0.95},
	"mercadolibre": {"patterns": []string{`mercadolibre\.(com\.ar|com\.mx|com\.br)`}, "confidence": 0.95},
	"ozon":         {"patterns": []string{`ozon\.ru`}, "confidence": 0.95},
	"wildberries":  {"patterns": []string{`wildberries\.ru`}, "confidence": 0.95},
	"allegro":      {"patterns": []string{`allegro\.(pl|cz|sk)`}, "confidence": 0.95},
	"cdiscount":    {"patterns": []string{`cdiscount\.com`}, "confidence": 0.95},
}

// PLATFORM_SIGNATURES detects CMS/SaaS e-commerce platforms.
var PLATFORM_SIGNATURES = map[string]map[string]interface{}{
	"shopify":     {"html": []string{"shopify.com", "cdn.shopify", "Shopify.theme"}, "confidence": 0.90},
	"magento":     {"html": []string{"Magento_", "mage-cache", "mage/cookies"}, "confidence": 0.90},
	"woocommerce": {"html": []string{"woocommerce", "wp-content/plugins/woocommerce"}, "confidence": 0.85},
	"bigcommerce": {"html": []string{"bigcommerce", "bc.js"}, "confidence": 0.90},
	"prestashop":  {"html": []string{"prestashop", "ps-shoppingcart"}, "confidence": 0.90},
	"wix":         {"html": []string{"wix.com", "wixstores"}, "confidence": 0.80},
	"squarespace": {"html": []string{"squarespace.com", "sqs-shop"}, "confidence": 0.80},
	"salesforce":  {"html": []string{"demandware", "sfcc", "commercecloud"}, "confidence": 0.85},
}

// ECOMMERCE_HTML_SIGNALS identifies e-commerce structural indicators.
var ECOMMERCE_HTML_SIGNALS = []string{
	`application/ld\+json[^"]*Product`,
	`"@type"\s*:\s*"Product"`,
	`"@type"\s*:\s*"Offer"`,
	`"@type"\s*:\s*"AggregateOffer"`,
	`class="[^"]*price[^"]*"`,
	`class="[^"]*add-to-cart[^"]*"`,
	`class="[^"]*buy-now[^"]*"`,
	`class="[^"]*add_to_cart[^"]*"`,
	`shopping[\-]?cart`,
	`data-product-id`,
	`data-sku`,
	`data-variant-id`,
	`itemtype="https?://schema\.org/Product"`,
	`[\$\€\£\¥\₹][\d,]+\.?\d*`,
	`\uffe5[\d,]+`,
}

// DetectEcommerceSite detects if a URL/HTML represents an e-commerce site.
func DetectEcommerceSite(rawURL string, html string) EcommerceDetectionResult {
	result := EcommerceDetectionResult{
		SiteFamily: "generic",
	}

	if rawURL == "" {
		return result
	}

	// Layer 1: URL pattern matching (fast, high confidence)
	urlMatch := detectByURL(rawURL)
	if urlMatch.IsEcommerce {
		result = urlMatch
	}

	// Layer 2: Platform/CMS signature detection
	if !result.IsEcommerce && html != "" {
		platformMatch := detectByPlatform(html)
		if platformMatch.IsEcommerce {
			result = platformMatch
		}
	}

	// Layer 3: HTML structure analysis
	if !result.IsEcommerce && html != "" {
		htmlMatch := detectByHTMLSignals(html)
		if htmlMatch.IsEcommerce {
			result = htmlMatch
		}
		// Merge detected features
		result.DetectedFeatures = append(result.DetectedFeatures, htmlMatch.DetectedFeatures...)
	}

	// Layer 4: Embedded structured data parsing
	if html != "" {
		if strings.Contains(html, "application/ld+json") {
			result.HasJSONLD = true
			result.DetectedFeatures = append(result.DetectedFeatures, "json_ld")
		}
		if strings.Contains(html, "__NEXT_DATA__") {
			result.HasNextData = true
			result.DetectedFeatures = append(result.DetectedFeatures, "next_data")
		}
		if !result.IsEcommerce && (result.HasJSONLD || result.HasNextData) {
			products := extractDetectorJSONLDProducts(html)
			if len(products) > 0 {
				result.IsEcommerce = true
				result.Confidence = 0.70
				result.DetectedFeatures = append(result.DetectedFeatures, "embedded_product_data")
			}
		}
	}

	return result
}

func detectByURL(rawURL string) EcommerceDetectionResult {
	for family, sig := range URL_SIGNATURES {
		patterns, ok := sig["patterns"].([]string)
		if !ok {
			continue
		}
		for _, pat := range patterns {
			re := regexp.MustCompile(pat)
			if re.MatchString(rawURL) {
				confidence := 0.95
				if c, ok := sig["confidence"].(float64); ok {
					confidence = c
				}
				return EcommerceDetectionResult{
					IsEcommerce:      true,
					Confidence:       confidence,
					SiteFamily:       family,
					DetectedFeatures: []string{"url_pattern"},
				}
			}
		}
	}
	return EcommerceDetectionResult{}
}

func detectByPlatform(html string) EcommerceDetectionResult {
	for platform, sig := range PLATFORM_SIGNATURES {
		htmlSigs, ok := sig["html"].([]string)
		if !ok {
			continue
		}
		for _, needle := range htmlSigs {
			if strings.Contains(html, needle) {
				confidence := 0.85
				if c, ok := sig["confidence"].(float64); ok {
					confidence = c
				}
				return EcommerceDetectionResult{
					IsEcommerce:      true,
					Confidence:       confidence,
					SiteFamily:       platform,
					Platform:         platform,
					DetectedFeatures: []string{"platform_signature"},
				}
			}
		}
	}
	return EcommerceDetectionResult{}
}

// detectByHTMLSignals analyzes HTML structure for e-commerce signals.
func detectByHTMLSignals(html string) EcommerceDetectionResult {
	signals := 0
	hasJsonld := false
	hasNextData := false

	for _, signal := range ECOMMERCE_HTML_SIGNALS {
		re := regexp.MustCompile(signal)
		if re.MatchString(html) {
			signals++
		}
	}

	if strings.Contains(html, "application/ld+json") {
		hasJsonld = true
		signals += 2
	}
	if strings.Contains(html, "__NEXT_DATA__") || strings.Contains(html, "__INITIAL_STATE__") {
		hasNextData = true
		signals++
	}

	confidence := math.Min(0.8, float64(signals)*0.15)
	if signals >= 2 {
		return EcommerceDetectionResult{
			IsEcommerce:      true,
			Confidence:       confidence,
			HasJSONLD:        hasJsonld,
			HasNextData:      hasNextData,
			DetectedFeatures: []string{"html_structure"},
		}
	}
	return EcommerceDetectionResult{}
}

// EXPECTED_JSONLD_FIELDS lists product-related schema.org fields.
var EXPECTED_JSONLD_FIELDS = []string{
	"@type", "name", "image", "offers",
	"price", "priceCurrency", "availability",
	"sku", "brand", "review", "aggregateRating",
}

// detectByStructuredData looks for structured product data in script tags.
func detectByStructuredData(html string) EcommerceDetectionResult {
	for _, field := range EXPECTED_JSONLD_FIELDS {
		if strings.Contains(html, fmt.Sprintf("\"%s\"", field)) {
			return EcommerceDetectionResult{
				IsEcommerce:      true,
				Confidence:       0.6,
				HasJSONLD:        true,
				DetectedFeatures: []string{"structured_data"},
			}
		}
	}
	return EcommerceDetectionResult{}
}

// detectByPriceHeuristic detects price-related patterns in the page.
func detectByPriceHeuristic(html string) EcommerceDetectionResult {
	priceIndicators := []string{
		"price", "amount", "currency",
		"discount", "originalPrice", "salePrice",
	}
	hits := 0
	for _, ind := range priceIndicators {
		if strings.Contains(html, ind) {
			hits++
		}
	}
	if hits >= 3 {
		return EcommerceDetectionResult{
			IsEcommerce:      true,
			Confidence:       0.5,
			PriceAPIDetected: true,
			DetectedFeatures: []string{"price_api"},
		}
	}
	return EcommerceDetectionResult{}
}

// extractJSONLDProducts extracts Product-type JSON-LD blocks from HTML.
func extractDetectorJSONLDProducts(html string) []map[string]interface{} {
	re := regexp.MustCompile(`(?s)<script[^>]*type=\"application/ld\+json\"[^>]*>(.*?)</script>`)
	matches := re.FindAllStringSubmatch(html, -1)
	var products []map[string]interface{}
	for _, m := range matches {
		var data interface{}
		if err := json.Unmarshal([]byte(m[1]), &data); err != nil {
			continue
		}
		// Flatten @graph arrays
		var items []interface{}
		switch v := data.(type) {
		case map[string]interface{}:
			if graph, ok := v["@graph"].([]interface{}); ok {
				items = graph
			} else {
				items = []interface{}{v}
			}
		case []interface{}:
			items = v
		}
		for _, item := range items {
			obj, ok := item.(map[string]interface{})
			if !ok {
				continue
			}
			if t, ok := obj["@type"].(string); ok && (t == "Product" || t == "Offer" || t == "AggregateOffer") {
				products = append(products, obj)
			}
		}
	}
	return products
}
