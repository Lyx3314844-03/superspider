package nodereverse

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestProfileAntiBotUsesProfileEndpoint(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/anti-bot/profile" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		if r.Method != http.MethodPost {
			t.Fatalf("unexpected method: %s", r.Method)
		}

		var payload AntiBotProfileRequest
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatalf("failed to decode request: %v", err)
		}
		if payload.StatusCode != 429 {
			t.Fatalf("expected status code 429, got %d", payload.StatusCode)
		}

		_ = json.NewEncoder(w).Encode(AntiBotProfileResponse{
			Success: true,
			Level:   "high",
			Signals: []string{"managed-browser-challenge"},
		})
	}))
	defer server.Close()

	client := NewNodeReverseClient(server.URL)
	response, err := client.ProfileAntiBot(AntiBotProfileRequest{
		HTML:       "<title>Just a moment...</title>",
		StatusCode: 429,
	})
	if err != nil {
		t.Fatalf("ProfileAntiBot returned error: %v", err)
	}
	if !response.Success {
		t.Fatalf("expected success response")
	}
	if response.Level != "high" {
		t.Fatalf("unexpected level: %s", response.Level)
	}
}

func TestDetectAntiBotUsesDetectEndpoint(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/anti-bot/detect" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		_ = json.NewEncoder(w).Encode(AntiBotProfileResponse{
			Success: true,
			Detection: map[string]bool{
				"hasCloudflare": true,
			},
			Signals: []string{"vendor:cloudflare"},
		})
	}))
	defer server.Close()

	client := NewNodeReverseClient(server.URL)
	response, err := client.DetectAntiBot(AntiBotProfileRequest{
		Headers: map[string]interface{}{"cf-ray": "token"},
	})
	if err != nil {
		t.Fatalf("DetectAntiBot returned error: %v", err)
	}
	if !response.Detection["hasCloudflare"] {
		t.Fatalf("expected cloudflare detection")
	}
}

func TestSpoofFingerprintUsesSpoofEndpoint(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/fingerprint/spoof" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		_ = json.NewEncoder(w).Encode(FingerprintSpoofResponse{
			Success:  true,
			Browser:  "chrome",
			Platform: "windows",
			Fingerprint: map[string]interface{}{
				"userAgent": "mock",
			},
		})
	}))
	defer server.Close()

	client := NewNodeReverseClient(server.URL)
	response, err := client.SpoofFingerprint(FingerprintSpoofRequest{Browser: "chrome", Platform: "windows"})
	if err != nil {
		t.Fatalf("SpoofFingerprint returned error: %v", err)
	}
	if response.Browser != "chrome" || response.Platform != "windows" {
		t.Fatalf("unexpected spoof response: %#v", response)
	}
}

func TestGenerateTLSFingerprintUsesTLSEndpoint(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/tls/fingerprint" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		_ = json.NewEncoder(w).Encode(TLSFingerprintResponse{
			Success: true,
			Browser: "chrome",
			Version: "120",
			Fingerprint: map[string]interface{}{
				"ja3": "mock-ja3",
			},
		})
	}))
	defer server.Close()

	client := NewNodeReverseClient(server.URL)
	response, err := client.GenerateTLSFingerprint(TLSFingerprintRequest{Browser: "chrome", Version: "120"})
	if err != nil {
		t.Fatalf("GenerateTLSFingerprint returned error: %v", err)
	}
	if response.Fingerprint["ja3"] != "mock-ja3" {
		t.Fatalf("unexpected tls fingerprint response: %#v", response)
	}
}
