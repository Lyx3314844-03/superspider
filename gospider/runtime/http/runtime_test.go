package httpruntime

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"gospider/core"
)

func TestHTTPRuntimeReturnsNormalizedResult(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	}))
	defer server.Close()

	runtime := NewRuntime()
	job := core.JobSpec{
		Name:    "fetch",
		Runtime: core.RuntimeHTTP,
		Target: core.TargetSpec{
			URL:    server.URL,
			Method: http.MethodGet,
		},
	}

	result, err := runtime.Execute(context.Background(), job)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.State != core.StateSucceeded {
		t.Fatalf("expected succeeded, got %s", result.State)
	}
	if result.StatusCode != http.StatusOK {
		t.Fatalf("expected status %d, got %d", http.StatusOK, result.StatusCode)
	}
	if string(result.Body) != "ok" {
		t.Fatalf("expected body %q, got %q", "ok", string(result.Body))
	}
}
