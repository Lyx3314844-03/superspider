package nodereverse

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
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

func TestAnalyzeWebpackUsesWebpackEndpoint(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/webpack/analyze" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"success":     true,
			"entrypoints": []string{"main"},
		})
	}))
	defer server.Close()

	client := NewNodeReverseClient(server.URL)
	response, err := client.AnalyzeWebpack("__webpack_require__(1)")
	if err != nil {
		t.Fatalf("AnalyzeWebpack returned error: %v", err)
	}
	if response["success"] != true {
		t.Fatalf("expected success response: %#v", response)
	}
}

func TestCanvasFingerprintUsesCanvasEndpoint(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/canvas/fingerprint" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		_ = json.NewEncoder(w).Encode(CanvasFingerprintResponse{
			Success: true,
			Hash:    "mock-canvas",
		})
	}))
	defer server.Close()

	client := NewNodeReverseClient(server.URL)
	response, err := client.CanvasFingerprint()
	if err != nil {
		t.Fatalf("CanvasFingerprint returned error: %v", err)
	}
	if response.Hash != "mock-canvas" {
		t.Fatalf("unexpected canvas response: %#v", response)
	}
}

func TestReverseSignatureUsesSignatureEndpoint(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/signature/reverse" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		_ = json.NewEncoder(w).Encode(SignatureReverseResponse{
			Success:      true,
			FunctionName: "sign",
		})
	}))
	defer server.Close()

	client := NewNodeReverseClient(server.URL)
	response, err := client.ReverseSignature("function sign(v){return v}", "left", "left")
	if err != nil {
		t.Fatalf("ReverseSignature returned error: %v", err)
	}
	if response.FunctionName != "sign" {
		t.Fatalf("unexpected signature response: %#v", response)
	}
}

func TestAnalyzeCryptoFallsBackToLocalMultiAlgorithmHeuristics(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "offline", http.StatusInternalServerError)
	}))
	defer server.Close()

	client := NewNodeReverseClient(server.URL)
	response, err := client.AnalyzeCrypto(`
        const key = "secret-key-1234";
        const iv = "nonce-001";
        const token = CryptoJS.HmacSHA256(data, key).toString();
        const cipher = sm4.encrypt(data, key, { mode: "cbc" });
        const digest = CryptoJS.SHA256(data).toString();
        const derived = CryptoJS.PBKDF2(password, salt, { keySize: 8 });
        const sessionKey = localStorage.getItem("session-key");
        const derivedKey = sha256(sessionKey || key);
        window.crypto.subtle.encrypt({ name: "AES-GCM", iv }, derivedKey, data);
    `)
	if err != nil {
		t.Fatalf("AnalyzeCrypto returned error: %v", err)
	}
	names := map[string]bool{}
	for _, item := range response.CryptoTypes {
		names[item.Name] = true
	}
	for _, required := range []string{"AES", "SM4", "HMAC-SHA256", "SHA256", "PBKDF2"} {
		if !names[required] {
			t.Fatalf("missing %s in %#v", required, response.CryptoTypes)
		}
	}
	if len(response.Keys) == 0 || response.Keys[0] != "secret-key-1234" {
		t.Fatalf("expected detected keys, got %#v", response.Keys)
	}
	if len(response.Ivs) == 0 || response.Ivs[0] != "nonce-001" {
		t.Fatalf("expected detected ivs, got %#v", response.Ivs)
	}
	if response.Analysis.ReverseComplexity == "" {
		t.Fatalf("expected reverse complexity, got %#v", response.Analysis)
	}
	if !containsString(response.Analysis.CryptoSinks, "crypto.subtle.encrypt") {
		t.Fatalf("expected crypto sink, got %#v", response.Analysis.CryptoSinks)
	}
	if !containsString(response.Analysis.AlgorithmAliases["AES"], "aes-gcm") {
		t.Fatalf("expected aes alias, got %#v", response.Analysis.AlgorithmAliases)
	}
	foundFlow := false
	for _, item := range response.Analysis.KeyFlowCandidates {
		if fmt.Sprint(item["variable"]) == "sessionKey" {
			if sources, ok := item["sources"].([]string); ok && containsString(sources, "storage.localStorage") {
				foundFlow = true
			}
		}
	}
	if !foundFlow {
		t.Fatalf("expected key flow candidate, got %#v", response.Analysis.KeyFlowCandidates)
	}
	foundChain := false
	for _, item := range response.Analysis.KeyFlowChains {
		if fmt.Sprint(item["variable"]) != "sessionKey" {
			continue
		}
		if !strings.Contains(fmt.Sprint(item["source"]), "storage.localStorage") {
			continue
		}
		if !strings.Contains(fmt.Sprint(item["derivations"]), "derivedKey") {
			continue
		}
		if !strings.Contains(fmt.Sprint(item["sinks"]), "crypto.subtle.encrypt") {
			continue
		}
		foundChain = true
		break
	}
	if !foundChain {
		t.Fatalf("expected key flow chain, got %#v", response.Analysis.KeyFlowChains)
	}
	if !containsString(response.Analysis.RecommendedApproach, "trace-key-materialization") {
		t.Fatalf("expected reverse approach hint, got %#v", response.Analysis.RecommendedApproach)
	}
	if !response.Analysis.RequiresASTDataflow {
		t.Fatalf("expected ast/dataflow hint in %#v", response.Analysis)
	}
}

func containsString(values []string, expected string) bool {
	for _, value := range values {
		if value == expected {
			return true
		}
	}
	return false
}
