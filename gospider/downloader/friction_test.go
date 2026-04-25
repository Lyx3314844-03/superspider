package downloader

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHTTPDownloaderAttachesAccessFrictionReport(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Retry-After", "45")
		w.Header().Set("CF-Ray", "demo")
		w.WriteHeader(http.StatusTooManyRequests)
		_, _ = w.Write([]byte("checking your browser"))
	}))
	defer server.Close()

	response := NewDownloader().Download(&Request{
		URL:    server.URL,
		Method: http.MethodGet,
	})

	if response.AccessFriction == nil {
		t.Fatal("expected access friction report")
	}
	if response.AccessFriction.Level != "high" {
		t.Fatalf("expected high level, got %q", response.AccessFriction.Level)
	}
	if !response.AccessFriction.Blocked {
		t.Fatal("expected blocked report")
	}
	if response.AccessFriction.RetryAfterSeconds != 45 {
		t.Fatalf("expected retry-after 45, got %d", response.AccessFriction.RetryAfterSeconds)
	}
	if !response.AccessFriction.ShouldUpgradeToBrowser {
		t.Fatal("expected browser upgrade recommendation")
	}
}
