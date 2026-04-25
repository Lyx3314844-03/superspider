package httpruntime

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"sync/atomic"
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

func TestHTTPRuntimeRespectsRobotsPolicy(t *testing.T) {
	var blockedHits atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/robots.txt":
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte("User-agent: *\nDisallow: /blocked\n"))
		case "/blocked":
			blockedHits.Add(1)
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte("should-not-fetch"))
		default:
			w.WriteHeader(http.StatusNotFound)
		}
	}))
	defer server.Close()

	runtime := NewRuntime()
	job := core.JobSpec{
		Name:    "robots-policy",
		Runtime: core.RuntimeHTTP,
		Target: core.TargetSpec{
			URL:    server.URL + "/blocked",
			Method: http.MethodGet,
		},
		Policy: core.PolicySpec{
			RespectRobotsTxt: true,
		},
	}

	result, err := runtime.Execute(context.Background(), job)
	if err == nil {
		t.Fatalf("expected robots policy error")
	}
	if result == nil {
		t.Fatalf("expected normalized result payload")
	}
	if result.StatusCode != http.StatusForbidden {
		t.Fatalf("expected status 403, got %d", result.StatusCode)
	}
	if blockedHits.Load() != 0 {
		t.Fatalf("expected target endpoint not to be requested, got %d hits", blockedHits.Load())
	}
}

func TestHTTPRuntimeRetriesRetryableStatuses(t *testing.T) {
	var hits atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/robots.txt":
			w.WriteHeader(http.StatusNotFound)
		case "/retry":
			current := hits.Add(1)
			if current == 1 {
				w.Header().Set("Retry-After", "0")
				w.WriteHeader(http.StatusTooManyRequests)
				_, _ = w.Write([]byte("retry"))
				return
			}
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte("ok-after-retry"))
		default:
			w.WriteHeader(http.StatusNotFound)
		}
	}))
	defer server.Close()

	runtime := NewRuntime()
	job := core.JobSpec{
		Name:    "retry-job",
		Runtime: core.RuntimeHTTP,
		Target: core.TargetSpec{
			URL:    server.URL + "/retry",
			Method: http.MethodGet,
		},
		Resources: core.ResourceSpec{
			Retries: 1,
		},
	}

	result, err := runtime.Execute(context.Background(), job)
	if err != nil {
		t.Fatalf("unexpected error after retry: %v", err)
	}
	if result.State != core.StateSucceeded {
		t.Fatalf("expected succeeded state, got %s", result.State)
	}
	if result.StatusCode != http.StatusOK {
		t.Fatalf("expected final status 200, got %d", result.StatusCode)
	}
	if string(result.Body) != "ok-after-retry" {
		t.Fatalf("unexpected response body: %q", string(result.Body))
	}
	if hits.Load() != 2 {
		t.Fatalf("expected exactly 2 attempts, got %d", hits.Load())
	}
}

func TestHTTPRuntimeDoesNotRetryHumanAccessChallenge(t *testing.T) {
	var hits atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		hits.Add(1)
		w.Header().Set("Retry-After", "0")
		w.WriteHeader(http.StatusTooManyRequests)
		_, _ = w.Write([]byte("hcaptcha security check"))
	}))
	defer server.Close()

	runtime := NewRuntime()
	job := core.JobSpec{
		Name:    "human-challenge",
		Runtime: core.RuntimeHTTP,
		Target:  core.TargetSpec{URL: server.URL, Method: http.MethodGet},
		Resources: core.ResourceSpec{
			Retries: 3,
		},
	}

	result, err := runtime.Execute(context.Background(), job)
	if err == nil {
		t.Fatalf("expected access friction error")
	}
	if result == nil || result.State != core.StateFailed {
		t.Fatalf("expected failed result, got %#v", result)
	}
	if hits.Load() != 1 {
		t.Fatalf("expected one attempt for human challenge, got %d", hits.Load())
	}
}

func TestHTTPRuntimeFailsBlockedAccessFriction(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("CF-Ray", "demo")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`<html><body>hcaptcha security check</body></html>`))
	}))
	defer server.Close()

	runtime := NewRuntime()
	job := core.JobSpec{
		Name:    "blocked-job",
		Runtime: core.RuntimeHTTP,
		Target:  core.TargetSpec{URL: server.URL, Method: http.MethodGet},
	}

	result, err := runtime.Execute(context.Background(), job)
	if err == nil {
		t.Fatalf("expected access friction error")
	}
	if result == nil || result.State != core.StateFailed {
		t.Fatalf("expected failed result, got %#v", result)
	}
	if _, ok := result.Metadata["access_friction"]; !ok {
		t.Fatalf("expected access friction metadata")
	}
}

func TestHTTPRuntimeExtractsStructuredFields(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/robots.txt":
			w.WriteHeader(http.StatusNotFound)
		default:
			w.Header().Set("Content-Type", "text/html")
			_, _ = w.Write([]byte(`<html><title>Example Domain</title><a href="/docs">Docs</a></html>`))
		}
	}))
	defer server.Close()

	runtime := NewRuntime()
	job := core.JobSpec{
		Name:    "extract-job",
		Runtime: core.RuntimeHTTP,
		Target:  core.TargetSpec{URL: server.URL, Method: http.MethodGet},
		Extract: []core.ExtractSpec{
			{Field: "title", Type: "css", Expr: "title", Required: true},
			{Field: "first_link", Type: "css_attr", Expr: "a", Attr: "href", Required: true, Schema: map[string]interface{}{"type": "string"}},
		},
	}

	result, err := runtime.Execute(context.Background(), job)
	if err != nil {
		t.Fatalf("unexpected extract error: %v", err)
	}
	if got := result.Extract["title"]; got != "Example Domain" {
		t.Fatalf("unexpected title extract: %#v", got)
	}
	if got := result.Extract["first_link"]; got != "/docs" {
		t.Fatalf("unexpected attr extract: %#v", got)
	}
	graphArtifact, ok := result.ArtifactRefs["graph"]
	if !ok {
		t.Fatalf("expected graph artifact ref")
	}
	if graphArtifact.Kind != "graph" {
		t.Fatalf("expected graph artifact kind, got %#v", graphArtifact.Kind)
	}
	if _, err := os.Stat(graphArtifact.Path); err != nil {
		t.Fatalf("expected persisted graph artifact, got error %v", err)
	}
}

func TestHTTPRuntimeAIExtractsStructuredFields(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/robots.txt":
			w.WriteHeader(http.StatusNotFound)
		default:
			w.Header().Set("Content-Type", "text/html")
			_, _ = w.Write([]byte(`<html><head><title>AI Domain</title><meta name="description" content="AI Description"></head><body><a href="/docs">Docs</a><img src="/cover.png"></body></html>`))
		}
	}))
	defer server.Close()

	runtime := NewRuntime()
	job := core.JobSpec{
		Name:    "ai-structured-job",
		Runtime: core.RuntimeHTTP,
		Target:  core.TargetSpec{URL: server.URL, Method: http.MethodGet},
		Extract: []core.ExtractSpec{
			{Field: "title", Type: "ai", Required: true, Schema: map[string]interface{}{"type": "string"}},
			{Field: "description", Type: "ai", Required: true, Schema: map[string]interface{}{"type": "string"}},
			{Field: "links", Type: "ai", Required: true, Schema: map[string]interface{}{"type": "array"}},
			{Field: "images", Type: "ai", Required: true, Schema: map[string]interface{}{"type": "array"}},
		},
	}

	result, err := runtime.Execute(context.Background(), job)
	if err != nil {
		t.Fatalf("unexpected ai extract error: %v", err)
	}
	if got := result.Extract["title"]; got != "AI Domain" {
		t.Fatalf("unexpected ai title extract: %#v", got)
	}
	if got := result.Extract["description"]; got != "AI Description" {
		t.Fatalf("unexpected ai description extract: %#v", got)
	}
	links, ok := result.Extract["links"].([]interface{})
	if !ok || len(links) != 1 || links[0] != server.URL+"/docs" {
		t.Fatalf("unexpected ai links extract: %#v", result.Extract["links"])
	}
	images, ok := result.Extract["images"].([]interface{})
	if !ok || len(images) != 1 || images[0] != server.URL+"/cover.png" {
		t.Fatalf("unexpected ai images extract: %#v", result.Extract["images"])
	}
}
