package captcha

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"
)

func TestSolveReCaptchaWith2Captcha(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/in.php", func(w http.ResponseWriter, r *http.Request) {
		_ = r.ParseForm()
		if got := r.FormValue("method"); got != "userrecaptcha" {
			t.Fatalf("expected userrecaptcha method, got %s", got)
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"status":  1,
			"request": "task-1",
		})
	})
	polls := 0
	mux.HandleFunc("/res.php", func(w http.ResponseWriter, r *http.Request) {
		polls++
		payload := map[string]any{"status": 0, "request": "CAPCHA_NOT_READY"}
		if polls >= 2 {
			payload = map[string]any{"status": 1, "request": "recaptcha-token"}
		}
		_ = json.NewEncoder(w).Encode(payload)
	})
	server := httptest.NewServer(mux)
	defer server.Close()

	solver := NewCaptchaSolver("demo-key", "2captcha")
	solver.httpClient = server.Client()
	solver.SetPollingConfig(time.Millisecond, 3)

	originalTransport := solver.httpClient.Transport
	solver.httpClient.Transport = rewriteTransport(server, originalTransport)

	result, err := solver.SolveReCaptcha("site-key", "https://example.com/challenge")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !result.Success || result.Text != "recaptcha-token" {
		t.Fatalf("unexpected result: %#v", result)
	}
}

func TestSolveHCaptchaWithAntiCaptcha(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/createTask", func(w http.ResponseWriter, r *http.Request) {
		var payload map[string]any
		_ = json.NewDecoder(r.Body).Decode(&payload)
		task := payload["task"].(map[string]any)
		if got := task["type"]; got != "HCaptchaTaskProxyless" {
			t.Fatalf("expected HCaptchaTaskProxyless, got %#v", got)
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"errorId": 0,
			"taskId":  42,
		})
	})
	polls := 0
	mux.HandleFunc("/getTaskResult", func(w http.ResponseWriter, r *http.Request) {
		polls++
		payload := map[string]any{"errorId": 0, "status": "processing"}
		if polls >= 2 {
			payload = map[string]any{
				"errorId": 0,
				"status":  "ready",
				"solution": map[string]any{
					"gRecaptchaResponse": "hcaptcha-token",
				},
			}
		}
		_ = json.NewEncoder(w).Encode(payload)
	})
	server := httptest.NewServer(mux)
	defer server.Close()

	solver := NewCaptchaSolver("demo-key", "anticaptcha")
	solver.httpClient = server.Client()
	solver.SetPollingConfig(time.Millisecond, 3)

	originalTransport := solver.httpClient.Transport
	solver.httpClient.Transport = rewriteTransport(server, originalTransport)

	result, err := solver.SolveHCaptcha("site-key", "https://example.com/hcaptcha")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !result.Success || result.Text != "hcaptcha-token" {
		t.Fatalf("unexpected result: %#v", result)
	}
}

func TestLiveSolveReCaptchaWith2CaptchaIfConfigured(t *testing.T) {
	if !liveCaptchaEnabled() {
		t.Skip("GOSPIDER_LIVE_CAPTCHA_SMOKE not enabled")
	}
	apiKey := firstNonBlankEnv("TWO_CAPTCHA_API_KEY", "CAPTCHA_API_KEY")
	siteKey := firstNonBlankEnv("GOSPIDER_LIVE_RECAPTCHA_SITE_KEY")
	pageURL := firstNonBlankEnv("GOSPIDER_LIVE_RECAPTCHA_PAGE_URL")
	if apiKey == "" || siteKey == "" || pageURL == "" {
		t.Skip("2captcha recaptcha live target not configured")
	}

	solver := NewCaptchaSolver(apiKey, "2captcha")
	result, err := solver.SolveReCaptcha(siteKey, pageURL)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !result.Success || result.Text == "" {
		t.Fatalf("unexpected result: %#v", result)
	}
}

func TestLiveSolveHCaptchaWithAntiCaptchaIfConfigured(t *testing.T) {
	if !liveCaptchaEnabled() {
		t.Skip("GOSPIDER_LIVE_CAPTCHA_SMOKE not enabled")
	}
	apiKey := firstNonBlankEnv("ANTI_CAPTCHA_API_KEY")
	siteKey := firstNonBlankEnv("GOSPIDER_LIVE_HCAPTCHA_SITE_KEY")
	pageURL := firstNonBlankEnv("GOSPIDER_LIVE_HCAPTCHA_PAGE_URL")
	if apiKey == "" || siteKey == "" || pageURL == "" {
		t.Skip("anti-captcha hcaptcha live target not configured")
	}

	solver := NewCaptchaSolver(apiKey, "anticaptcha")
	result, err := solver.SolveHCaptcha(siteKey, pageURL)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !result.Success || result.Text == "" {
		t.Fatalf("unexpected result: %#v", result)
	}
}

func rewriteTransport(server *httptest.Server, fallback http.RoundTripper) http.RoundTripper {
	base := http.DefaultTransport
	if fallback != nil {
		base = fallback
	}
	return roundTripFunc(func(req *http.Request) (*http.Response, error) {
		req.URL.Scheme = "http"
		req.URL.Host = server.Listener.Addr().String()
		return base.RoundTrip(req)
	})
}

type roundTripFunc func(*http.Request) (*http.Response, error)

func (fn roundTripFunc) RoundTrip(req *http.Request) (*http.Response, error) {
	return fn(req)
}

func liveCaptchaEnabled() bool {
	switch firstNonBlankEnv("GOSPIDER_LIVE_CAPTCHA_SMOKE") {
	case "1", "true", "TRUE", "True":
		return true
	default:
		return false
	}
}

func firstNonBlankEnv(names ...string) string {
	for _, name := range names {
		if value := envValue(name); value != "" {
			return value
		}
	}
	return ""
}

func envValue(name string) string {
	value := ""
	if name != "" {
		value = strings.TrimSpace(os.Getenv(name))
	}
	return value
}
