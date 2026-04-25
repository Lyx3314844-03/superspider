package browser

import "time"

type PlaywrightBrowserOptions struct {
	Headless  bool
	Width     int
	Height    int
	UserAgent string
	Proxy     string
	Timeout   time.Duration
}

func DefaultPlaywrightOptions() *PlaywrightBrowserOptions {
	return &PlaywrightBrowserOptions{
		Headless:  true,
		Width:     1920,
		Height:    1080,
		UserAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
		Timeout:   30 * time.Second,
	}
}

type BrowserAdapterSupport struct {
	Supported     bool     `json:"supported"`
	Mode          string   `json:"mode"`
	AdapterEngine string   `json:"adapter_engine"`
	Notes         []string `json:"notes,omitempty"`
}

type BrowserCompatibilityMatrix struct {
	BaseEngine     string                           `json:"base_engine"`
	BridgeStyle    string                           `json:"bridge_style"`
	Surfaces       map[string]BrowserAdapterSupport `json:"surfaces"`
	Artifacts      map[string]bool                  `json:"artifacts"`
	Interaction    map[string]string                `json:"interaction,omitempty"`
	AccessFriction map[string]any                   `json:"access_friction,omitempty"`
	Constraints    []string                         `json:"constraints,omitempty"`
}

func DefaultCompatibilityBridge() BrowserAdapterSupport {
	return BrowserAdapterSupport{
		Supported:     true,
		Mode:          "native-process",
		AdapterEngine: "node-playwright",
		Notes: []string{
			"executes the shared Node Playwright helper",
			"requires npm package playwright and browser binaries to be installed",
		},
	}
}

func BrowserConfigFromPlaywrightOptions(options *PlaywrightBrowserOptions) *BrowserConfig {
	cfg := DefaultConfig()
	if options == nil {
		return cfg
	}
	cfg.Headless = options.Headless
	if options.Width > 0 {
		cfg.ViewportWidth = options.Width
	}
	if options.Height > 0 {
		cfg.ViewportHeight = options.Height
	}
	if options.UserAgent != "" {
		cfg.UserAgent = options.UserAgent
	}
	if options.Proxy != "" {
		cfg.Proxy = options.Proxy
	}
	if options.Timeout > 0 {
		cfg.Timeout = options.Timeout
	}
	return cfg
}

func BrowserPoolShouldRecycle(
	createdAt time.Time,
	lastUsedAt time.Time,
	requestCount int,
	maxAge time.Duration,
	maxIdle time.Duration,
	maxRequests int,
	now time.Time,
) bool {
	if maxAge > 0 && now.Sub(createdAt) >= maxAge {
		return true
	}
	if maxIdle > 0 && now.Sub(lastUsedAt) >= maxIdle {
		return true
	}
	if maxRequests > 0 && requestCount >= maxRequests {
		return true
	}
	return false
}

func BrowserCompatibilitySupport() BrowserCompatibilityMatrix {
	bridge := DefaultCompatibilityBridge()
	return BrowserCompatibilityMatrix{
		BaseEngine:  "chromedp+selenium-webdriver+node-playwright",
		BridgeStyle: "native-and-bridge",
		Surfaces: map[string]BrowserAdapterSupport{
			"playwright": bridge,
			"selenium": {
				Supported:     true,
				Mode:          "native",
				AdapterEngine: "selenium-webdriver",
				Notes:         []string{"uses the native WebDriver HTTP protocol surface"},
			},
			"webdriver": {
				Supported:     true,
				Mode:          "native",
				AdapterEngine: "selenium-webdriver",
			},
		},
		Artifacts: map[string]bool{
			"html":       true,
			"screenshot": true,
			"har":        true,
			"trace":      true,
			"pdf":        false,
		},
		Interaction: map[string]string{
			"file_upload":             "native-upload-input",
			"iframe_support":          "same-origin-helpers",
			"shadow_dom":              "open-shadow-root-helpers",
			"realtime_stream_capture": "cdp-websocket-sse-events",
		},
		AccessFriction: map[string]any{
			"classifier": true,
			"signals":    []string{"captcha", "rate-limited", "managed-browser-challenge", "auth-required", "waf-vendor"},
			"actions":    []string{"honor-retry-after", "render-with-browser", "persist-session-state", "pause-for-human-access"},
		},
		Constraints: []string{
			"playwright support is a native helper-process adapter; install browsers with `npx playwright install` before live use",
		},
	}
}
