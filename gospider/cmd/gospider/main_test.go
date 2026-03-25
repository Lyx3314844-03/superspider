//go:build legacy_cli

package main

import (
	"testing"

	"gospider/core"
)

func TestSubmitCommandUsesJobService(t *testing.T) {
	service := core.NewJobService()
	if err := submitCommand(service, "https://example.com", "http", 7); err != nil {
		t.Fatalf("unexpected submit error: %v", err)
	}

	jobs := service.List()
	if len(jobs) != 1 {
		t.Fatalf("expected one job, got %d", len(jobs))
	}
	if jobs[0].URL != "https://example.com" {
		t.Fatalf("expected submitted url, got %s", jobs[0].URL)
	}
}
