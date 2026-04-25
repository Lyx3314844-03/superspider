package browser

import (
	"strings"
	"testing"
	"time"
)

func TestBrowserConfigFromPlaywrightOptionsMapsCoreFields(t *testing.T) {
	options := &PlaywrightBrowserOptions{
		Headless:  false,
		Width:     1366,
		Height:    768,
		UserAgent: "FixtureBrowser/1.0",
		Proxy:     "http://127.0.0.1:8080",
		Timeout:   45 * time.Second,
	}

	cfg := BrowserConfigFromPlaywrightOptions(options)

	if cfg.Headless {
		t.Fatal("expected headless to be mapped")
	}
	if cfg.ViewportWidth != 1366 || cfg.ViewportHeight != 768 {
		t.Fatalf("unexpected viewport mapping: %dx%d", cfg.ViewportWidth, cfg.ViewportHeight)
	}
	if cfg.UserAgent != "FixtureBrowser/1.0" {
		t.Fatalf("unexpected user agent mapping: %s", cfg.UserAgent)
	}
	if cfg.Proxy != "http://127.0.0.1:8080" {
		t.Fatalf("unexpected proxy mapping: %s", cfg.Proxy)
	}
	if cfg.Timeout != 45*time.Second {
		t.Fatalf("unexpected timeout mapping: %s", cfg.Timeout)
	}
}

func TestCompatibilityBridgeReportsAdapterEngine(t *testing.T) {
	bridge := DefaultCompatibilityBridge()

	if !bridge.Supported {
		t.Fatal("expected compatibility bridge to be supported")
	}
	if bridge.Mode != "native-process" {
		t.Fatalf("unexpected bridge mode: %s", bridge.Mode)
	}
	if bridge.AdapterEngine != "node-playwright" {
		t.Fatalf("unexpected adapter engine: %s", bridge.AdapterEngine)
	}
}

func TestBrowserCompatibilitySupportReportsUploadAndIframeSupport(t *testing.T) {
	matrix := BrowserCompatibilitySupport()

	if matrix.Interaction["file_upload"] != "native-upload-input" {
		t.Fatalf("unexpected file upload support: %s", matrix.Interaction["file_upload"])
	}
	if matrix.Interaction["iframe_support"] != "same-origin-helpers" {
		t.Fatalf("unexpected iframe support: %s", matrix.Interaction["iframe_support"])
	}
	if matrix.Interaction["shadow_dom"] != "open-shadow-root-helpers" {
		t.Fatalf("unexpected shadow dom support: %s", matrix.Interaction["shadow_dom"])
	}
	if matrix.Interaction["realtime_stream_capture"] != "cdp-websocket-sse-events" {
		t.Fatalf("unexpected realtime support: %s", matrix.Interaction["realtime_stream_capture"])
	}
}

func TestBrowserPoolShouldRecycleWhenAgeIdleOrRequestLimitExceeded(t *testing.T) {
	now := time.Now()

	if !BrowserPoolShouldRecycle(now.Add(-2*time.Hour), now, 1, time.Hour, 0, 0, now) {
		t.Fatal("expected age limit to trigger recycle")
	}
	if !BrowserPoolShouldRecycle(now, now.Add(-10*time.Minute), 1, 0, 5*time.Minute, 0, now) {
		t.Fatal("expected idle limit to trigger recycle")
	}
	if !BrowserPoolShouldRecycle(now, now, 100, 0, 0, 100, now) {
		t.Fatal("expected request limit to trigger recycle")
	}
	if BrowserPoolShouldRecycle(now, now, 3, time.Hour, time.Hour, 10, now) {
		t.Fatal("did not expect recycle when limits are not exceeded")
	}
}

func TestPlaywrightBrowserBuildsNativeHelperCommand(t *testing.T) {
	options := DefaultPlaywrightOptions()
	options.UserAgent = "FixtureBrowser/1.0"
	browser := &PlaywrightBrowser{
		options: options,
		node:    "node",
		helper:  "tools/playwright_fetch.mjs",
	}

	args := browser.fetchArgs("https://example.com", "page.png", "page.html")
	joined := strings.Join(args, " ")
	for _, expected := range []string{
		"tools/playwright_fetch.mjs",
		"--url https://example.com",
		"--headless",
		"--user-agent FixtureBrowser/1.0",
		"--screenshot page.png",
		"--html page.html",
	} {
		if !strings.Contains(joined, expected) {
			t.Fatalf("expected %q in helper args: %v", expected, args)
		}
	}
}
