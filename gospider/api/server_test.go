package api

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"gospider/core"
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
