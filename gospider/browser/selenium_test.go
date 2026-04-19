package browser

import (
	"encoding/base64"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestSeleniumClientCreatesSessionAndMapsCoreCommands(t *testing.T) {
	sessionCreated := false
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.Method == http.MethodPost && r.URL.Path == "/session":
			sessionCreated = true
			var payload map[string]any
			_ = json.NewDecoder(r.Body).Decode(&payload)
			alwaysMatch := payload["capabilities"].(map[string]any)["alwaysMatch"].(map[string]any)
			if alwaysMatch["browserName"] != "chrome" {
				t.Fatalf("unexpected browserName payload: %#v", alwaysMatch["browserName"])
			}
			_ = json.NewEncoder(w).Encode(map[string]any{"value": map[string]any{"sessionId": "session-1"}})
		case r.Method == http.MethodPost && r.URL.Path == "/session/session-1/url":
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte(`{"value":null}`))
		case r.Method == http.MethodGet && r.URL.Path == "/session/session-1/source":
			_ = json.NewEncoder(w).Encode(map[string]any{"value": "<html>fixture</html>"})
		case r.Method == http.MethodGet && r.URL.Path == "/session/session-1/title":
			_ = json.NewEncoder(w).Encode(map[string]any{"value": "Fixture Title"})
		case r.Method == http.MethodGet && r.URL.Path == "/session/session-1/screenshot":
			_ = json.NewEncoder(w).Encode(map[string]any{"value": base64.StdEncoding.EncodeToString([]byte("png"))})
		case r.Method == http.MethodDelete && r.URL.Path == "/session/session-1":
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte(`{"value":null}`))
		default:
			t.Fatalf("unexpected selenium request: %s %s", r.Method, r.URL.Path)
		}
	}))
	defer server.Close()

	client, err := NewSeleniumClient(&SeleniumConfig{
		WebDriverURL: server.URL,
		BrowserName:  "chrome",
		Headless:     true,
		UserAgent:    "GoSpider Selenium",
	})
	if err != nil {
		t.Fatalf("unexpected create error: %v", err)
	}
	if !sessionCreated {
		t.Fatal("expected selenium session to be created")
	}
	if err := client.Navigate("https://example.com"); err != nil {
		t.Fatalf("unexpected navigate error: %v", err)
	}
	if html, err := client.HTML(); err != nil || html != "<html>fixture</html>" {
		t.Fatalf("unexpected html response: %q %v", html, err)
	}
	if title, err := client.Title(); err != nil || title != "Fixture Title" {
		t.Fatalf("unexpected title response: %q %v", title, err)
	}
	if screenshot, err := client.Screenshot(); err != nil || string(screenshot) != "png" {
		t.Fatalf("unexpected screenshot response: %q %v", string(screenshot), err)
	}
	if err := client.Close(); err != nil {
		t.Fatalf("unexpected close error: %v", err)
	}
}
