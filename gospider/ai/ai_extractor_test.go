package ai

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

func TestDefaultAIConfigSupportsAnthropicEnvironment(t *testing.T) {
	t.Setenv("AI_PROVIDER", "anthropic")
	t.Setenv("ANTHROPIC_API_KEY", "anthropic-key")
	t.Setenv("ANTHROPIC_BASE_URL", "https://api.anthropic.test/v1")
	t.Setenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

	cfg := DefaultAIConfig()

	if cfg.Provider != "anthropic" {
		t.Fatalf("expected anthropic provider, got %s", cfg.Provider)
	}
	if cfg.APIKey != "anthropic-key" {
		t.Fatalf("unexpected api key: %s", cfg.APIKey)
	}
	if cfg.BaseURL != "https://api.anthropic.test/v1" {
		t.Fatalf("unexpected base url: %s", cfg.BaseURL)
	}
	if cfg.Model != "claude-sonnet-4-20250514" {
		t.Fatalf("unexpected model: %s", cfg.Model)
	}
}

func TestCallLLMSupportsAnthropicMessagesAPI(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/messages" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		if got := r.Header.Get("x-api-key"); got != "anthropic-key" {
			t.Fatalf("unexpected anthropic key header: %s", got)
		}
		if got := r.Header.Get("anthropic-version"); got != "2023-06-01" {
			t.Fatalf("unexpected anthropic version header: %s", got)
		}
		var payload map[string]any
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatalf("failed to decode payload: %v", err)
		}
		if payload["model"] != "claude-sonnet-4-20250514" {
			t.Fatalf("unexpected model payload: %#v", payload["model"])
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"content": []map[string]any{
				{"type": "text", "text": "anthropic-response"},
			},
		})
	}))
	defer server.Close()

	extractor := NewAIExtractor(&AIConfig{
		APIKey:      "anthropic-key",
		BaseURL:     server.URL,
		Model:       "claude-sonnet-4-20250514",
		MaxTokens:   256,
		Temperature: 0.1,
		Provider:    "anthropic",
	})

	response, err := extractor.callLLM("hello")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if response != "anthropic-response" {
		t.Fatalf("unexpected response: %s", response)
	}
}

func TestMain(m *testing.M) {
	code := m.Run()
	os.Exit(code)
}
