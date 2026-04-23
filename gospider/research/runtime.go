package research

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"reflect"
	"sort"
	"strings"

	"github.com/PuerkitoBio/goquery"
	"gospider/storage"
)

type SiteProfile struct {
	URL             string          `json:"url"`
	PageType        string          `json:"page_type"`
	SiteFamily      string          `json:"site_family"`
	Signals         map[string]bool `json:"signals"`
	CandidateFields []string        `json:"candidate_fields"`
	RiskLevel       string          `json:"risk_level"`
	CrawlerType     string          `json:"crawler_type"`
	RunnerOrder     []string        `json:"runner_order"`
	StrategyHints   []string        `json:"strategy_hints"`
	JobTemplates    []string        `json:"job_templates"`
}

type ResearchRuntime struct{}

func NewResearchRuntime() *ResearchRuntime {
	return &ResearchRuntime{}
}

func (r *ResearchRuntime) Run(job ResearchJob, content string) (map[string]interface{}, error) {
	if len(job.SeedURLs) == 0 || strings.TrimSpace(job.SeedURLs[0]) == "" {
		return nil, fmt.Errorf("seed_urls[0] is required")
	}
	seed := job.SeedURLs[0]
	if strings.TrimSpace(content) == "" {
		content = fmt.Sprintf("<title>%s</title>", seed)
	}
	profile := profileSite(seed, content)
	extracted, err := extractContent(content, job.ExtractSchema, job.ExtractSpecs)
	if err != nil {
		return nil, err
	}

	result := map[string]interface{}{
		"seed":    seed,
		"profile": profile,
		"extract": extracted,
	}

	if outputPath := stringMapValue(job.Output, "path"); outputPath != "" {
		datasetResult, err := writeDataset(outputPath, stringMapValue(job.Output, "format"), extracted)
		if err != nil {
			return nil, err
		}
		result["dataset"] = datasetResult
	}
	return result, nil
}

func profileSite(url string, content string) SiteProfile {
	lower := strings.ToLower(content)
	parsedURL, _ := urlpkgParse(url)
	query := map[string][]string{}
	pathLower := ""
	if parsedURL != nil {
		query = parsedURL.Query()
		pathLower = strings.ToLower(parsedURL.Path)
	}
	hasSearchQuery := len(query["q"]) > 0 ||
		len(query["query"]) > 0 ||
		len(query["keyword"]) > 0 ||
		len(query["search"]) > 0 ||
		len(query["wd"]) > 0 ||
		strings.Contains(strings.ToLower(url), "/search") ||
		strings.Contains(strings.ToLower(url), "search?") ||
		strings.Contains(strings.ToLower(url), "keyword=")
	siteFamily := resolveSiteFamily(strings.ToLower(parsedHost(parsedURL)))
	signals := map[string]bool{
		"has_form":       strings.Contains(lower, "<form"),
		"has_pagination": strings.Contains(lower, "next") || strings.Contains(lower, "page=") || strings.Contains(lower, "pagination") || strings.Contains(content, "下一页"),
		"has_list":       strings.Contains(lower, "<li") || strings.Contains(lower, "<ul") || strings.Contains(lower, "<ol") || strings.Contains(lower, "product-list") || strings.Contains(lower, "goods-list") || strings.Contains(lower, "sku-item"),
		"has_detail":     strings.Contains(lower, "<article") || strings.Contains(lower, "<h1"),
		"has_captcha":    strings.Contains(lower, "captcha") || strings.Contains(lower, "verify") || strings.Contains(lower, "human verification") || strings.Contains(content, "滑块") || strings.Contains(content, "验证码"),
		"has_price":      strings.Contains(lower, "price") || strings.Contains(lower, `"price"`) || strings.Contains(content, "￥") || strings.Contains(content, "¥") || strings.Contains(content, "价格"),
		"has_search":     hasSearchQuery || strings.Contains(lower, `type="search"`) || strings.Contains(content, "搜索") || strings.Contains(lower, "search-input"),
		"has_login":      strings.Contains(lower, `type="password"`) || strings.Contains(lower, "sign in") || strings.Contains(lower, "signin") || strings.Contains(content, "登录"),
		"has_hydration":  strings.Contains(lower, "__next_data__") || strings.Contains(lower, "__next_f") || strings.Contains(lower, "__nuxt__") || strings.Contains(lower, "__apollo_state__") || strings.Contains(lower, "__initial_state__") || strings.Contains(lower, "__preloaded_state__") || strings.Contains(lower, "window.__initial_data__"),
		"has_api_bootstrap": strings.Contains(lower, "__initial_state__") ||
			strings.Contains(lower, "__preloaded_state__") ||
			strings.Contains(lower, "__next_data__") ||
			strings.Contains(lower, "__apollo_state__") ||
			strings.Contains(lower, "application/json") ||
			strings.Contains(lower, "window.__initial_data__"),
		"has_infinite_scroll": strings.Contains(lower, "load more") ||
			strings.Contains(lower, "infinite") ||
			strings.Contains(lower, "intersectionobserver") ||
			strings.Contains(lower, "onscroll") ||
			strings.Contains(lower, "virtual-list") ||
			strings.Contains(content, "加载更多"),
		"has_graphql":        strings.Contains(lower, "graphql"),
		"has_reviews":        strings.Contains(lower, "review") || strings.Contains(content, "评价") || strings.Contains(lower, "comments"),
		"has_product_schema": strings.Contains(strings.ReplaceAll(lower, " ", ""), `"@type":"product"`) || strings.Contains(strings.ReplaceAll(lower, " ", ""), `"@type":"offer"`),
		"has_cart":           strings.Contains(lower, "add to cart") || strings.Contains(content, "购物车") || strings.Contains(lower, "buy-now") || strings.Contains(content, "立即购买"),
		"has_sku":            strings.Contains(lower, "sku") || strings.Contains(content, "商品编号") || strings.Contains(strings.ToLower(url), "item.jd.com") || strings.Contains(strings.ToLower(url), "/item.htm"),
		"has_image":          strings.Contains(lower, "<img") || strings.Contains(lower, "og:image"),
	}

	crawlerType := resolveCrawlerType(signals, pathLower)
	pageType := "generic"
	switch crawlerType {
	case "static_listing", "search_results", "ecommerce_search", "infinite_scroll_listing":
		pageType = "list"
	case "static_detail", "ecommerce_detail":
		pageType = "detail"
	default:
		if signals["has_list"] && !signals["has_detail"] {
			pageType = "list"
		} else if signals["has_detail"] {
			pageType = "detail"
		}
	}

	candidateFields := []string{}
	if strings.Contains(lower, "<title") {
		candidateFields = append(candidateFields, "title")
	}
	if signals["has_price"] {
		candidateFields = append(candidateFields, "price")
	}
	if strings.Contains(lower, "author") || strings.Contains(content, "作者") {
		candidateFields = append(candidateFields, "author")
	}
	if signals["has_sku"] {
		candidateFields = append(candidateFields, "sku")
	}
	if signals["has_reviews"] {
		candidateFields = append(candidateFields, "rating")
	}
	if signals["has_search"] {
		candidateFields = append(candidateFields, "keyword")
	}
	if signals["has_image"] {
		candidateFields = append(candidateFields, "image")
	}
	if strings.Contains(lower, "shop") || strings.Contains(lower, "seller") || strings.Contains(content, "店铺") {
		candidateFields = append(candidateFields, "shop")
	}
	if strings.Contains(lower, "description") || strings.Contains(content, "详情") {
		candidateFields = append(candidateFields, "description")
	}

	riskLevel := "low"
	if signals["has_captcha"] {
		riskLevel = "high"
	} else if strings.HasPrefix(strings.ToLower(url), "https://") && (signals["has_form"] || signals["has_login"] || signals["has_hydration"] || signals["has_graphql"]) {
		riskLevel = "medium"
	}
	runnerOrder := resolveRunnerOrder(crawlerType, signals)

	return SiteProfile{
		URL:             url,
		PageType:        pageType,
		SiteFamily:      siteFamily,
		Signals:         signals,
		CandidateFields: uniqueStrings(candidateFields),
		RiskLevel:       riskLevel,
		CrawlerType:     crawlerType,
		RunnerOrder:     runnerOrder,
		StrategyHints:   resolveStrategyHints(crawlerType, signals),
		JobTemplates:    resolveJobTemplates(crawlerType, siteFamily),
	}
}

func parsedHost(parsed *url.URL) string {
	if parsed == nil {
		return ""
	}
	return parsed.Hostname()
}

func resolveSiteFamily(host string) string {
	mapping := map[string]string{
		"jd.com":           "jd",
		"3.cn":             "jd",
		"taobao.com":       "taobao",
		"tmall.com":        "tmall",
		"pinduoduo.com":    "pinduoduo",
		"yangkeduo.com":    "pinduoduo",
		"xiaohongshu.com":  "xiaohongshu",
		"xhslink.com":      "xiaohongshu",
		"douyin.com":       "douyin-shop",
		"jinritemai.com":   "douyin-shop",
	}
	for suffix, family := range mapping {
		if host == suffix || strings.HasSuffix(host, "."+suffix) {
			return family
		}
	}
	return "generic"
}

func urlpkgParse(raw string) (*url.URL, error) {
	if strings.TrimSpace(raw) == "" {
		return nil, nil
	}
	return url.Parse(raw)
}

func resolveCrawlerType(signals map[string]bool, path string) string {
	switch {
	case signals["has_login"] && !signals["has_detail"]:
		return "login_session"
	case signals["has_infinite_scroll"] && (signals["has_list"] || signals["has_search"]):
		return "infinite_scroll_listing"
	case signals["has_price"] && (signals["has_cart"] || signals["has_sku"] || signals["has_product_schema"]) && (signals["has_search"] || (signals["has_list"] && strings.Contains(path, "search"))):
		return "ecommerce_search"
	case signals["has_price"] && (signals["has_cart"] || signals["has_sku"] || signals["has_product_schema"]) && signals["has_list"] && !signals["has_detail"]:
		return "ecommerce_search"
	case signals["has_price"] && (signals["has_cart"] || signals["has_sku"] || signals["has_product_schema"]):
		return "ecommerce_detail"
	case signals["has_hydration"] && (signals["has_list"] || signals["has_detail"] || signals["has_search"]):
		return "hydrated_spa"
	case signals["has_api_bootstrap"] || signals["has_graphql"]:
		return "api_bootstrap"
	case signals["has_search"] && (signals["has_list"] || signals["has_pagination"]):
		return "search_results"
	case signals["has_list"] && !signals["has_detail"]:
		return "static_listing"
	case signals["has_detail"]:
		return "static_detail"
	default:
		return "generic_http"
	}
}

func resolveRunnerOrder(crawlerType string, signals map[string]bool) []string {
	switch crawlerType {
	case "hydrated_spa", "infinite_scroll_listing", "login_session", "ecommerce_search":
		return []string{"browser", "http"}
	case "ecommerce_detail":
		if signals["has_hydration"] {
			return []string{"browser", "http"}
		}
		return []string{"http", "browser"}
	default:
		return []string{"http", "browser"}
	}
}

func resolveStrategyHints(crawlerType string, signals map[string]bool) []string {
	hints := map[string][]string{
		"generic_http": {
			"start with plain HTTP fetch and fall back to browser only if selectors are empty",
			"prefer stable title/meta/schema extraction before custom DOM selectors",
		},
		"static_listing": {
			"use HTTP mode first and follow pagination links conservatively",
			"dedupe URLs before entering detail pages to avoid list-page churn",
		},
		"static_detail": {
			"extract title, meta, and structured data before custom selectors",
			"persist raw HTML for selector iteration and regression tests",
		},
		"search_results": {
			"seed from the search URL and normalize keyword/query parameters",
			"treat listing and detail extraction as separate stages with separate schemas",
		},
		"ecommerce_search": {
			"start with browser rendering, capture HTML and network payloads, then promote stable fields into HTTP follow-up jobs",
			"split listing fields from detail fields so sku/price/image can be validated independently",
		},
		"ecommerce_detail": {
			"extract embedded product JSON and schema blocks before relying on brittle selectors",
			"keep screenshot and HTML artifacts together for price/title regression checks",
		},
		"hydrated_spa": {
			"render the page in browser mode and inspect embedded hydration data before DOM scraping",
			"capture network responses and promote repeatable JSON endpoints into secondary HTTP jobs",
		},
		"api_bootstrap": {
			"inspect script tags and bootstrap JSON before adding browser interactions",
			"extract stable JSON blobs into dedicated parsing rules so DOM churn matters less",
		},
		"infinite_scroll_listing": {
			"drive a bounded scroll loop and stop when repeated snapshots stop changing",
			"persist network and DOM artifacts so load-more behavior can be replayed without guessing",
		},
		"login_session": {
			"bootstrap an authenticated session once, then reuse cookies or storage state for follow-up jobs",
			"validate the post-login page shape before starting extraction",
		},
	}
	resolved := append([]string(nil), hints[crawlerType]...)
	if len(resolved) == 0 {
		resolved = append([]string(nil), hints["generic_http"]...)
	}
	if signals["has_captcha"] {
		resolved = append(resolved, "treat challenge pages as blockers and capture evidence instead of scraping through them")
	}
	return resolved
}

func resolveJobTemplates(crawlerType string, siteFamily string) []string {
	mapping := map[string][]string{
		"generic_http":            {"examples/crawler-types/api-bootstrap-http.json"},
		"static_listing":          {"examples/crawler-types/api-bootstrap-http.json"},
		"static_detail":           {"examples/crawler-types/api-bootstrap-http.json"},
		"search_results":          {"examples/crawler-types/api-bootstrap-http.json"},
		"ecommerce_search":        {"examples/crawler-types/ecommerce-search-browser.json"},
		"ecommerce_detail":        {"examples/crawler-types/ecommerce-search-browser.json", "examples/crawler-types/api-bootstrap-http.json"},
		"hydrated_spa":            {"examples/crawler-types/hydrated-spa-browser.json"},
		"api_bootstrap":           {"examples/crawler-types/api-bootstrap-http.json"},
		"infinite_scroll_listing": {"examples/crawler-types/infinite-scroll-browser.json"},
		"login_session":           {"examples/crawler-types/login-session-browser.json"},
	}
	if templates, ok := mapping[crawlerType]; ok {
		return appendSiteFamilyTemplates(templates, siteFamily, crawlerType)
	}
	return appendSiteFamilyTemplates([]string{"examples/crawler-types/api-bootstrap-http.json"}, siteFamily, crawlerType)
}

func appendSiteFamilyTemplates(templates []string, siteFamily string, crawlerType string) []string {
	return uniqueStrings(append(append([]string{}, templates...), siteFamilyTemplates(siteFamily, crawlerType)...))
}

func siteFamilyTemplates(siteFamily string, crawlerType string) []string {
	if siteFamily == "jd" && crawlerType == "ecommerce_detail" {
		return []string{"examples/site-presets/jd-detail-browser.json"}
	}
	if siteFamily == "taobao" && crawlerType == "ecommerce_detail" {
		return []string{"examples/site-presets/taobao-detail-browser.json"}
	}
	mapping := map[string][]string{
		"jd":          {"examples/site-presets/jd-search-browser.json"},
		"taobao":      {"examples/site-presets/taobao-search-browser.json"},
		"tmall":       {"examples/site-presets/tmall-search-browser.json"},
		"pinduoduo":   {"examples/site-presets/pinduoduo-search-browser.json"},
		"xiaohongshu": {"examples/site-presets/xiaohongshu-feed-browser.json"},
		"douyin-shop": {"examples/site-presets/douyin-shop-browser.json"},
	}
	return mapping[siteFamily]
}

func uniqueStrings(values []string) []string {
	seen := map[string]struct{}{}
	result := make([]string, 0, len(values))
	for _, value := range values {
		if _, ok := seen[value]; ok {
			continue
		}
		seen[value] = struct{}{}
		result = append(result, value)
	}
	return result
}

func extractContent(content string, schema map[string]interface{}, specs []map[string]interface{}) (map[string]interface{}, error) {
	properties := map[string]interface{}{}
	if schema != nil {
		if raw, ok := schema["properties"].(map[string]interface{}); ok {
			properties = raw
		}
	}

	extracted := map[string]interface{}{}
	if len(specs) > 0 {
		for _, spec := range specs {
			field := strings.TrimSpace(stringMapValue(spec, "field"))
			if field == "" {
				continue
			}
			value := extractWithSpec(content, field, spec)
			if isEmptyValue(value) {
				if boolMapValue(spec, "required") {
					return nil, fmt.Errorf("required extract field %q could not be resolved", field)
				}
				continue
			}
			if err := validateSchema(field, value, schemaForField(spec, properties, field)); err != nil {
				return nil, err
			}
			extracted[field] = value
		}
		return extracted, nil
	}

	fieldNames := make([]string, 0, len(properties))
	for field := range properties {
		fieldNames = append(fieldNames, field)
	}
	sort.Strings(fieldNames)
	for _, field := range fieldNames {
		if value, ok := heuristicExtract(field, content); ok {
			extracted[field] = value
		}
	}
	return extracted, nil
}

func extractWithSpec(content string, field string, spec map[string]interface{}) interface{} {
	extractType := strings.ToLower(strings.TrimSpace(stringMapValue(spec, "type")))
	expr := stringMapValue(spec, "expr")
	path := stringMapValue(spec, "path")
	attr := stringMapValue(spec, "attr")

	switch extractType {
	case "css":
		selector := expr
		if selector == "" && field == "title" {
			selector = "title"
		}
		if selector != "" {
			if value := cssSelectText(content, selector); value != "" {
				return value
			}
		}
	case "css_attr":
		if expr != "" && attr != "" {
			if value := cssSelectAttr(content, expr, attr); value != "" {
				return value
			}
		}
	case "xpath":
		return xpathExtract(content, expr)
	case "regex":
		if expr == "" {
			return nil
		}
		re, err := regexp.Compile("(?is)" + expr)
		if err != nil {
			return nil
		}
		match := re.FindStringSubmatch(content)
		if len(match) > 1 {
			return strings.TrimSpace(match[1])
		}
		if len(match) == 1 {
			return strings.TrimSpace(match[0])
		}
	case "json_path":
		if path == "" {
			path = expr
		}
		return jsonPathExtract(content, path)
	case "ai":
		if field == "title" {
			if value, ok := heuristicExtract("title", content); ok {
				return value
			}
		}
		if field == "html" || field == "dom" {
			return content
		}
	}

	if value, ok := heuristicExtract(field, content); ok {
		return value
	}
	return nil
}

func xpathExtract(content string, expr string) interface{} {
	normalized := strings.TrimSpace(strings.ToLower(expr))
	switch normalized {
	case "//title/text()":
		if value, ok := heuristicExtract("title", content); ok {
			return value
		}
	case "//h1/text()":
		re := regexp.MustCompile(`(?is)<h1[^>]*>(.*?)</h1>`)
		if match := re.FindStringSubmatch(content); len(match) > 1 {
			return strings.TrimSpace(stripHTML(match[1]))
		}
	default:
		metaRe := regexp.MustCompile(`(?is)^//meta\[@name=['"]([^'"]+)['"]\]/@content$`)
		if match := metaRe.FindStringSubmatch(normalized); len(match) > 1 {
			pattern := regexp.MustCompile(fmt.Sprintf(`(?is)<meta[^>]*name=["']%s["'][^>]*content=["']([^"']+)["']`, regexp.QuoteMeta(match[1])))
			if found := pattern.FindStringSubmatch(content); len(found) > 1 {
				return strings.TrimSpace(found[1])
			}
		}
	}
	return nil
}

func heuristicExtract(field string, content string) (interface{}, bool) {
	switch strings.ToLower(strings.TrimSpace(field)) {
	case "title":
		re := regexp.MustCompile(`(?is)<title>(.*?)</title>`)
		match := re.FindStringSubmatch(content)
		if len(match) > 1 {
			return strings.TrimSpace(match[1]), true
		}
	default:
		re := regexp.MustCompile(`(?im)` + regexp.QuoteMeta(field) + `\s*[:=]\s*([^\n<]+)`)
		match := re.FindStringSubmatch(content)
		if len(match) > 1 {
			return strings.TrimSpace(match[1]), true
		}
	}
	return nil, false
}

func jsonPathExtract(content string, path string) interface{} {
	if strings.TrimSpace(path) == "" {
		return nil
	}
	var payload interface{}
	if err := json.Unmarshal([]byte(content), &payload); err != nil {
		return nil
	}
	normalized := strings.TrimPrefix(strings.TrimSpace(path), "$.")
	if normalized == "" {
		return nil
	}
	current := payload
	for _, segment := range strings.Split(normalized, ".") {
		object, ok := current.(map[string]interface{})
		if !ok {
			return nil
		}
		value, exists := object[segment]
		if !exists {
			return nil
		}
		current = value
	}
	return current
}

func validateSchema(field string, value interface{}, schema map[string]interface{}) error {
	expectedType := strings.TrimSpace(stringMapValue(schema, "type"))
	if expectedType == "" {
		return nil
	}
	valid := false
	switch expectedType {
	case "string":
		_, valid = value.(string)
	case "number":
		switch value.(type) {
		case int, int32, int64, float32, float64:
			valid = true
		}
	case "integer":
		switch value.(type) {
		case int, int32, int64:
			valid = true
		}
	case "boolean":
		_, valid = value.(bool)
	case "object":
		valid = reflect.TypeOf(value) != nil && reflect.TypeOf(value).Kind() == reflect.Map
	case "array":
		valid = reflect.TypeOf(value) != nil && (reflect.TypeOf(value).Kind() == reflect.Slice || reflect.TypeOf(value).Kind() == reflect.Array)
	}
	if !valid {
		return fmt.Errorf("extract field %q violates schema.type=%s", field, expectedType)
	}
	return nil
}

func schemaForField(spec map[string]interface{}, properties map[string]interface{}, field string) map[string]interface{} {
	if raw, ok := spec["schema"].(map[string]interface{}); ok {
		return raw
	}
	if raw, ok := properties[field].(map[string]interface{}); ok {
		return raw
	}
	return map[string]interface{}{}
}

func stripHTML(value string) string {
	re := regexp.MustCompile(`(?is)<[^>]+>`)
	return re.ReplaceAllString(value, "")
}

func cssSelectText(content string, selector string) string {
	document, err := goquery.NewDocumentFromReader(bytes.NewReader([]byte(content)))
	if err != nil {
		return ""
	}
	selection := document.Find(selector).First()
	if selection.Length() == 0 {
		return ""
	}
	return strings.TrimSpace(selection.Text())
}

func cssSelectAttr(content string, selector string, attr string) string {
	document, err := goquery.NewDocumentFromReader(bytes.NewReader([]byte(content)))
	if err != nil {
		return ""
	}
	selection := document.Find(selector).First()
	if selection.Length() == 0 {
		return ""
	}
	value, ok := selection.Attr(attr)
	if !ok {
		return ""
	}
	return strings.TrimSpace(value)
}

func writeDataset(path string, format string, extracted map[string]interface{}) (map[string]interface{}, error) {
	if format == "" {
		format = detectOutputFormat(path)
	}
	if format == "" {
		format = "json"
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return nil, err
	}

	switch format {
	case "jsonl":
		encoded, err := json.Marshal(extracted)
		if err != nil {
			return nil, err
		}
		if err := os.WriteFile(path, append(encoded, '\n'), 0o644); err != nil {
			return nil, err
		}
	case "json", "csv":
		dataset := storage.NewDataset("research")
		dataset.Push(extracted)
		if err := dataset.Save(path, format); err != nil {
			return nil, err
		}
	default:
		return nil, fmt.Errorf("unsupported dataset format %q", format)
	}
	_ = storage.MirrorDatasetRow(extracted)

	return map[string]interface{}{
		"path":   path,
		"format": format,
	}, nil
}

func detectOutputFormat(path string) string {
	extension := strings.ToLower(filepath.Ext(path))
	switch extension {
	case ".json":
		return "json"
	case ".jsonl":
		return "jsonl"
	case ".csv":
		return "csv"
	default:
		return ""
	}
}

func stringMapValue(values map[string]interface{}, key string) string {
	if values == nil {
		return ""
	}
	if value, ok := values[key].(string); ok {
		return value
	}
	return ""
}

func boolMapValue(values map[string]interface{}, key string) bool {
	if values == nil {
		return false
	}
	if value, ok := values[key].(bool); ok {
		return value
	}
	return false
}

func isEmptyValue(value interface{}) bool {
	if value == nil {
		return true
	}
	if text, ok := value.(string); ok {
		return strings.TrimSpace(text) == ""
	}
	return false
}
