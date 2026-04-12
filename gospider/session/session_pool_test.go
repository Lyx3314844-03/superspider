package session

import (
	"net/http"
	"testing"
)

func TestSessionGetClientUsesProxyURL(t *testing.T) {
	session, err := NewSession("test-agent")
	if err != nil {
		t.Fatalf("new session failed: %v", err)
	}

	session.ProxyURL = "http://proxy.example:8080"
	client := session.GetClient()
	if client.Transport == nil {
		t.Fatal("expected proxy transport to be configured")
	}

	transport, ok := client.Transport.(*http.Transport)
	if !ok {
		t.Fatalf("expected *http.Transport, got %T", client.Transport)
	}

	request, err := http.NewRequest(http.MethodGet, "https://example.com", nil)
	if err != nil {
		t.Fatalf("new request failed: %v", err)
	}

	proxyURL, err := transport.Proxy(request)
	if err != nil {
		t.Fatalf("proxy resolution failed: %v", err)
	}
	if proxyURL == nil || proxyURL.String() != "http://proxy.example:8080" {
		t.Fatalf("unexpected proxy URL: %v", proxyURL)
	}
}

func TestSessionGetClientIgnoresInvalidProxyURL(t *testing.T) {
	session, err := NewSession("test-agent")
	if err != nil {
		t.Fatalf("new session failed: %v", err)
	}

	session.ProxyURL = "://bad-proxy"
	client := session.GetClient()
	if client.Transport != nil {
		t.Fatalf("expected invalid proxy URL to be ignored, got transport %T", client.Transport)
	}
}
