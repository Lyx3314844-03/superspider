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

type BrowserAdapterSupport struct {
	Supported     bool     `json:"supported"`
	Mode          string   `json:"mode"`
	AdapterEngine string   `json:"adapter_engine"`
	Notes         []string `json:"notes,omitempty"`
}

type BrowserCompatibilityMatrix struct {
	BaseEngine  string                           `json:"base_engine"`
	BridgeStyle string                           `json:"bridge_style"`
	Surfaces    map[string]BrowserAdapterSupport `json:"surfaces"`
	Artifacts   map[string]bool                  `json:"artifacts"`
	Interaction map[string]string                `json:"interaction,omitempty"`
	Constraints []string                         `json:"constraints,omitempty"`
}

func DefaultCompatibilityBridge() BrowserAdapterSupport {
	return BrowserAdapterSupport{
		Supported:     true,
		Mode:          "compatibility-bridge",
		AdapterEngine: "chromedp",
		Notes: []string{
			"reuses the existing chromedp browser runtime",
			"does not embed a separate native Playwright or Selenium engine",
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
		BaseEngine:  "chromedp+selenium-webdriver",
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
		Constraints: []string{
			"playwright remains bridged to the chromedp runtime; selenium/webdriver is now available as a native remote protocol surface",
		},
	}
}
