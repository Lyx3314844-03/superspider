package main

import (
	"encoding/json"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	browserpkg "gospider/browser"
)

type ecommerceBrowserCapture struct {
	Kind              string                   `json:"kind"`
	SiteFamily        string                   `json:"site_family"`
	Mode              string                   `json:"mode"`
	URL               string                   `json:"url"`
	Title             string                   `json:"title"`
	Detector          EcommerceDetectionResult `json:"detector"`
	ProductLinks      []string                 `json:"product_link_candidates"`
	SKUCandidates     []string                 `json:"sku_candidates"`
	ImageCandidates   []string                 `json:"image_candidates"`
	JSONLDProducts    []map[string]any         `json:"json_ld_products"`
	BootstrapProducts []map[string]any         `json:"bootstrap_products"`
	APICandidates     []string                 `json:"api_candidates"`
	APIJobTemplates   []map[string]any         `json:"api_job_templates"`
	AccessChallenge   map[string]any           `json:"access_challenge"`
	Runtime           map[string]any           `json:"runtime"`
	ParameterTable    []ParamEntry             `json:"parameter_table"`
	CouponsPromotions []PromotionSignal        `json:"coupons_promotions"`
	StockStatus       StockStatus              `json:"stock_status"`
	Artifacts         map[string]string        `json:"artifacts"`
}

type SeleniumEcommerceCrawler struct {
	SiteFamily string
	OutputDir  string
	Attempts   int
}

func NewSeleniumEcommerceCrawler(siteFamily string) *SeleniumEcommerceCrawler {
	return &SeleniumEcommerceCrawler{
		SiteFamily: siteFamily,
		OutputDir:  filepath.Join("artifacts", "browser"),
		Attempts:   envInt("ECOM_BROWSER_ATTEMPTS", map[bool]int{true: 2, false: 1}[isHighFrictionSite(siteFamily)]),
	}
}

func (crawler *SeleniumEcommerceCrawler) Crawl(mode string) (*ecommerceBrowserCapture, error) {
	profile := profileForFamily(crawler.SiteFamily)
	targetURL := profile.CatalogURL
	switch mode {
	case "detail":
		targetURL = profile.DetailURL
	case "review":
		targetURL = profile.ReviewURL
	default:
		mode = "catalog"
	}

	cfg := browserpkg.DefaultSeleniumConfig()
	cfg.Headless = envBool("ECOM_BROWSER_HEADLESS", !isHighFrictionSite(crawler.SiteFamily))
	cfg.Timeout = 60 * time.Second
	cfg.UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
	cfg.WindowSize = "1920,1080"
	cfg.UserDataDir = envString("ECOM_BROWSER_PROFILE", filepath.Join("artifacts", "browser", "profiles", "gospider-"+crawler.SiteFamily))
	cfg.ExtraArgs = []string{
		"--disable-blink-features=AutomationControlled",
		"--disable-dev-shm-usage",
		"--no-first-run",
		"--no-default-browser-check",
	}
	client, err := browserpkg.NewSeleniumClient(cfg)
	if err != nil {
		return nil, err
	}
	defer client.Close()
	client.ApplyEcommerceRuntimeProfile(cfg.UserAgent)

	var challenge map[string]any
	var lastErr error
	for attempt := 1; attempt <= maxInt(1, crawler.Attempts); attempt++ {
		client.Warmup(originURL(targetURL))
		if err := client.Navigate(targetURL); err != nil {
			lastErr = err
			time.Sleep(time.Duration(attempt) * 4 * time.Second)
			continue
		}
		_ = client.WaitReady(30 * time.Second)
		_ = client.ScrollToBottom(map[bool]int{true: 8, false: 4}[mode == "catalog"], 900*time.Millisecond)
		challenge, _ = client.DetectAccessChallenge()
		if blocked, _ := challenge["blocked"].(bool); !blocked {
			break
		}
		manualSeconds := envInt("ECOM_BROWSER_MANUAL_SECONDS", map[bool]int{true: 180, false: 0}[isHighFrictionSite(crawler.SiteFamily)])
		if blocked, _ := challenge["blocked"].(bool); blocked && !cfg.Headless && manualSeconds > 0 {
			fmt.Printf("access challenge detected, keep the browser open for %ds to complete login/verification manually\n", manualSeconds)
			_ = client.WaitForManualAccess(time.Duration(manualSeconds) * time.Second)
			_ = client.ScrollToBottom(map[bool]int{true: 4, false: 2}[mode == "catalog"], 900*time.Millisecond)
			challenge, _ = client.DetectAccessChallenge()
			if blocked, _ := challenge["blocked"].(bool); !blocked {
				break
			}
		}
		if attempt < maxInt(1, crawler.Attempts) {
			time.Sleep(time.Duration(attempt) * 4 * time.Second)
		}
	}
	if lastErr != nil && challenge == nil {
		return nil, lastErr
	}

	html, err := client.HTML()
	if err != nil {
		return nil, err
	}
	title, _ := client.Title()
	currentURL, _ := client.CurrentURL()
	links := collectRegexMatches(html, []string{`<a[^>]+href=["']([^"']+)["']`}, 100)
	images := collectRegexMatches(html, []string{`<img[^>]+(?:src|data-src|data-lazy-img)=["']([^"']+)["']`}, 100)
	apiCandidates := extractAPICandidates(html, 30)
	skuCandidates := collectRegexMatches(html, profile.ItemIDPatterns, 20)

	artifactDir := crawler.OutputDir
	if err := os.MkdirAll(artifactDir, 0755); err != nil {
		return nil, err
	}
	prefix := fmt.Sprintf("gospider-%s-%s", crawler.SiteFamily, mode)
	htmlPath := filepath.Join(artifactDir, prefix+".html")
	jsonPath := filepath.Join(artifactDir, prefix+".json")
	screenshotPath := filepath.Join(artifactDir, prefix+".png")
	_ = os.WriteFile(htmlPath, []byte(html), 0644)
	if shot, err := client.Screenshot(); err == nil {
		_ = os.WriteFile(screenshotPath, shot, 0644)
	}

	payload := ecommerceBrowserCapture{
		Kind:              "ecommerce_browser_capture",
		SiteFamily:        crawler.SiteFamily,
		Mode:              mode,
		URL:               currentURL,
		Title:             title,
		Detector:          DetectEcommerceSite(currentURL, html),
		ProductLinks:      collectProductLinks(currentURL, links, profile, 30),
		SKUCandidates:     skuCandidates,
		ImageCandidates:   collectImageLinks(currentURL, images, 30),
		JSONLDProducts:    extractJSONLDProducts(html, 10),
		BootstrapProducts: extractBootstrapProducts(html, 10),
		APICandidates:     apiCandidates,
		APIJobTemplates:   buildAPIJobTemplates(currentURL, crawler.SiteFamily, apiCandidates, skuCandidates, 20),
		AccessChallenge:   challenge,
		Runtime: map[string]any{
			"headless":       cfg.Headless,
			"user_data_dir":  cfg.UserDataDir,
			"attempts":       maxInt(1, crawler.Attempts),
			"webdriver_url":  cfg.WebDriverURL,
			"network_source": "selenium_page_source",
		},
		ParameterTable:    ExtractParameterTable(html),
		CouponsPromotions: DetectCouponsPromotions(html),
		StockStatus:       ExtractStockStatus(html),
		Artifacts: map[string]string{
			"html":       htmlPath,
			"json":       jsonPath,
			"screenshot": screenshotPath,
		},
	}
	data, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return nil, err
	}
	if err := os.WriteFile(jsonPath, data, 0644); err != nil {
		return nil, err
	}
	return &payload, nil
}

func originURL(rawURL string) string {
	parsed, err := url.Parse(rawURL)
	if err != nil || parsed.Scheme == "" || parsed.Host == "" {
		return ""
	}
	return parsed.Scheme + "://" + parsed.Host + "/"
}

func maxInt(a int, b int) int {
	if a > b {
		return a
	}
	return b
}

func runSeleniumEcommerceCapture(siteFamily string, mode string) error {
	crawler := NewSeleniumEcommerceCrawler(siteFamily)
	payload, err := crawler.Crawl(mode)
	if err != nil {
		return err
	}
	jsonPath := payload.Artifacts["json"]
	fmt.Printf("browser capture exported to %s\n", jsonPath)
	return nil
}

func isHighFrictionSite(siteFamily string) bool {
	switch strings.ToLower(siteFamily) {
	case "jd", "taobao", "tmall", "pdd", "amazon":
		return true
	default:
		return false
	}
}

func envString(name string, fallback string) string {
	if value := os.Getenv(name); strings.TrimSpace(value) != "" {
		return value
	}
	return fallback
}

func envBool(name string, fallback bool) bool {
	value := strings.TrimSpace(strings.ToLower(os.Getenv(name)))
	if value == "" {
		return fallback
	}
	return value == "1" || value == "true" || value == "yes" || value == "on"
}

func envInt(name string, fallback int) int {
	value := strings.TrimSpace(os.Getenv(name))
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}
