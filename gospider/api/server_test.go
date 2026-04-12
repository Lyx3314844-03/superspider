package api

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"gospider/core"
	"gospider/events"
)

func TestAPICreatesJobViaPublicService(t *testing.T) {
	service := core.NewJobService()
	server := NewServerWithJobService(&Config{Host: "127.0.0.1", Port: 8080}, service)

	body, err := json.Marshal(map[string]any{
		"url":      "https://example.com",
		"runtime":  "http",
		"priority": 3,
	})
	if err != nil {
		t.Fatalf("unexpected marshal error: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/api/v1/tasks", bytes.NewReader(body))
	rec := httptest.NewRecorder()

	server.router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}
	if len(service.List()) != 1 {
		t.Fatalf("expected one job in service, got %d", len(service.List()))
	}
}

func TestAPICreatesJobFromNormalizedJobSpecPayload(t *testing.T) {
	service := core.NewJobService()
	server := NewServerWithJobService(&Config{Host: "127.0.0.1", Port: 8080}, service)

	body, err := json.Marshal(map[string]any{
		"name":    "browser-job",
		"runtime": "browser",
		"target": map[string]any{
			"url":        "https://example.com/app",
			"method":     "GET",
			"timeout_ms": 1500,
		},
		"browser": map[string]any{
			"profile": "chrome-stealth",
			"actions": []map[string]any{
				{
					"type":       "goto",
					"url":        "https://example.com/app",
					"timeout_ms": 5000,
				},
			},
		},
		"output": map[string]any{
			"format": "json",
		},
		"anti_bot": map[string]any{
			"identity_profile": "residential-browser",
			"challenge_policy": "browser_upgrade",
		},
		"policy": map[string]any{
			"same_domain_only": true,
		},
	})
	if err != nil {
		t.Fatalf("unexpected marshal error: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/api/v1/tasks", bytes.NewReader(body))
	rec := httptest.NewRecorder()

	server.router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}

	record, ok := service.Get("browser-job")
	if !ok {
		t.Fatal("expected stored normalized job")
	}
	if record.Spec.Runtime != core.RuntimeBrowser {
		t.Fatalf("expected runtime %s, got %s", core.RuntimeBrowser, record.Spec.Runtime)
	}
	if record.Spec.Target.Timeout != 1500*time.Millisecond {
		t.Fatalf("expected target timeout 1500ms, got %s", record.Spec.Target.Timeout)
	}
	if len(record.Spec.Browser.Actions) != 1 {
		t.Fatalf("expected one browser action, got %d", len(record.Spec.Browser.Actions))
	}
	if record.Spec.AntiBot.IdentityProfile != "residential-browser" {
		t.Fatalf("expected anti bot profile to be normalized")
	}
}

func TestAPICanReadAndCancelStoredJobInMemoryMode(t *testing.T) {
	service := core.NewJobService()
	server := NewServerWithJobService(&Config{Host: "127.0.0.1", Port: 8080}, service)

	if _, err := service.Submit(core.JobSpec{
		Name:    "job-1",
		Runtime: core.RuntimeHTTP,
		Target:  core.TargetSpec{URL: "https://example.com"},
	}); err != nil {
		t.Fatalf("unexpected submit error: %v", err)
	}

	getReq := httptest.NewRequest(http.MethodGet, "/api/v1/tasks/job-1", nil)
	getRec := httptest.NewRecorder()
	server.router.ServeHTTP(getRec, getReq)
	if getRec.Code != http.StatusOK {
		t.Fatalf("expected get status 200, got %d", getRec.Code)
	}

	cancelReq := httptest.NewRequest(http.MethodPost, "/api/v1/tasks/job-1/cancel", nil)
	cancelRec := httptest.NewRecorder()
	server.router.ServeHTTP(cancelRec, cancelReq)
	if cancelRec.Code != http.StatusOK {
		t.Fatalf("expected cancel status 200, got %d", cancelRec.Code)
	}

	record, ok := service.Get("job-1")
	if !ok {
		t.Fatal("expected cancelled job to remain stored")
	}
	if record.Summary.State != core.StateCancelled {
		t.Fatalf("expected cancelled state, got %s", record.Summary.State)
	}
}

func TestAPIExposesTaskResultAndArtifactsInMemoryMode(t *testing.T) {
	service := core.NewJobService()
	server := NewServerWithJobService(&Config{Host: "127.0.0.1", Port: 8080}, service)

	if _, err := service.Submit(core.JobSpec{
		Name:    "job-result",
		Runtime: core.RuntimeMedia,
		Target:  core.TargetSpec{URL: "https://cdn.example.com/video.mp4"},
		Output:  core.OutputSpec{Format: "artifact"},
	}); err != nil {
		t.Fatalf("unexpected submit error: %v", err)
	}

	result := core.NewJobResult(core.JobSpec{
		Name:    "job-result",
		Runtime: core.RuntimeMedia,
		Target:  core.TargetSpec{URL: "https://cdn.example.com/video.mp4"},
	}, core.StateSucceeded)
	result.AddMediaArtifact(core.MediaArtifact{
		Type: "video",
		URL:  "https://cdn.example.com/video.mp4",
		Path: "downloads/job-result.mp4",
	})
	result.Finalize()

	if err := service.AttachResult("job-result", result); err != nil {
		t.Fatalf("unexpected attach error: %v", err)
	}

	resultReq := httptest.NewRequest(http.MethodGet, "/api/v1/tasks/job-result/result", nil)
	resultRec := httptest.NewRecorder()
	server.router.ServeHTTP(resultRec, resultReq)
	if resultRec.Code != http.StatusOK {
		t.Fatalf("expected result status 200, got %d", resultRec.Code)
	}

	artifactsReq := httptest.NewRequest(http.MethodGet, "/api/v1/tasks/job-result/artifacts", nil)
	artifactsRec := httptest.NewRecorder()
	server.router.ServeHTTP(artifactsRec, artifactsReq)
	if artifactsRec.Code != http.StatusOK {
		t.Fatalf("expected artifacts status 200, got %d", artifactsRec.Code)
	}
}

func TestAPIListsMemoryEvents(t *testing.T) {
	service := core.NewJobService()
	server := NewServerWithJobService(&Config{Host: "127.0.0.1", Port: 8080}, service)

	if _, err := service.Submit(core.JobSpec{
		Name:    "job-events",
		Runtime: core.RuntimeHTTP,
		Target:  core.TargetSpec{URL: "https://example.com"},
		Output:  core.OutputSpec{Format: "json"},
	}); err != nil {
		t.Fatalf("unexpected submit error: %v", err)
	}

	result := core.NewJobResult(core.JobSpec{
		Name:    "job-events",
		Runtime: core.RuntimeHTTP,
		Target:  core.TargetSpec{URL: "https://example.com"},
	}, core.StateSucceeded)
	result.Finalize()
	if err := service.AttachResult("job-events", result); err != nil {
		t.Fatalf("unexpected attach error: %v", err)
	}

	req := httptest.NewRequest(http.MethodGet, "/api/v1/events?limit=10", nil)
	rec := httptest.NewRecorder()
	server.router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected events status 200, got %d", rec.Code)
	}

	var payload []events.Event
	if err := json.Unmarshal(rec.Body.Bytes(), &payload); err != nil {
		t.Fatalf("unexpected unmarshal error: %v", err)
	}
	if len(payload) == 0 {
		t.Fatal("expected at least one event")
	}
}

func TestAPIHealthRemainsPublicWhenAuthEnabled(t *testing.T) {
	server := NewServerWithJobService(&Config{
		Host:       "127.0.0.1",
		Port:       8080,
		EnableAuth: true,
		AuthToken:  "secret-token",
	}, core.NewJobService())

	req := httptest.NewRequest(http.MethodGet, "/api/v1/health", nil)
	rec := httptest.NewRecorder()
	server.router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected public health endpoint, got %d", rec.Code)
	}
}

func TestAPIRequiresAuthForProtectedRoutes(t *testing.T) {
	server := NewServerWithJobService(&Config{
		Host:       "127.0.0.1",
		Port:       8080,
		EnableAuth: true,
		AuthToken:  "secret-token",
	}, core.NewJobService())

	req := httptest.NewRequest(http.MethodGet, "/api/v1/stats", nil)
	rec := httptest.NewRecorder()
	server.router.ServeHTTP(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("expected status 401 without auth, got %d", rec.Code)
	}
}

func TestAPIAcceptsBearerTokenForProtectedRoutes(t *testing.T) {
	server := NewServerWithJobService(&Config{
		Host:       "127.0.0.1",
		Port:       8080,
		EnableAuth: true,
		AuthToken:  "secret-token",
	}, core.NewJobService())

	req := httptest.NewRequest(http.MethodGet, "/api/v1/stats", nil)
	req.Header.Set("Authorization", "Bearer secret-token")
	rec := httptest.NewRecorder()
	server.router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200 with bearer token, got %d", rec.Code)
	}
}

func TestAPIExtractsGraphFromHTMLPayload(t *testing.T) {
	server := NewServerWithJobService(&Config{Host: "127.0.0.1", Port: 8080}, core.NewJobService())

	body, err := json.Marshal(map[string]any{
		"html": `<html><head><title>Go Graph API</title></head><body><a href="https://example.com/page">Read</a><img src="https://example.com/image.png"/></body></html>`,
	})
	if err != nil {
		t.Fatalf("unexpected marshal error: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/api/v1/graph/extract", bytes.NewReader(body))
	rec := httptest.NewRecorder()
	server.router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}

	var payload map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &payload); err != nil {
		t.Fatalf("unexpected unmarshal error: %v", err)
	}
	if payload["success"] != true {
		t.Fatalf("expected success envelope, got %#v", payload)
	}
	data, ok := payload["data"].(map[string]any)
	if !ok {
		t.Fatalf("expected data object in payload")
	}
	stats, ok := data["stats"].(map[string]any)
	if !ok {
		t.Fatalf("expected stats object in payload")
	}
	if stats["total_nodes"].(float64) < 3 {
		t.Fatalf("expected at least 3 nodes, got %#v", stats["total_nodes"])
	}
}

func TestAPIGraphExtractAliasSupportsApiPrefixWithoutVersion(t *testing.T) {
	server := NewServerWithJobService(&Config{Host: "127.0.0.1", Port: 8080}, core.NewJobService())

	body := bytes.NewReader([]byte(`{"html":"<html><head><title>Alias</title></head><body><a href='https://example.com'>A</a></body></html>"}`))
	req := httptest.NewRequest(http.MethodPost, "/api/graph/extract", body)
	rec := httptest.NewRecorder()
	server.router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}
}

func TestQueueTypeToStateSupportsLegacyAndNormalizedTerms(t *testing.T) {
	cases := map[string]core.TaskState{
		"pending":   core.StateQueued,
		"queued":    core.StateQueued,
		"completed": core.StateSucceeded,
		"succeeded": core.StateSucceeded,
		"failed":    core.StateFailed,
		"cancelled": core.StateCancelled,
	}

	for input, expected := range cases {
		if got := queueTypeToState(input); got != expected {
			t.Fatalf("expected %q -> %q, got %q", input, expected, got)
		}
	}
}

func TestParseTaskStateFiltersDeduplicatesAndNormalizes(t *testing.T) {
	filters := parseTaskStateFilters("pending,queued,completed")
	if len(filters) != 2 {
		t.Fatalf("expected 2 unique filters, got %d", len(filters))
	}
	if filters[0] != core.StateQueued {
		t.Fatalf("expected first filter queued, got %s", filters[0])
	}
	if filters[1] != core.StateSucceeded {
		t.Fatalf("expected second filter succeeded, got %s", filters[1])
	}
}
