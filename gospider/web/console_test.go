package web

import (
	"testing"

	"gospider/core"
)

func TestWebConsoleReadsNormalizedJobStats(t *testing.T) {
	service := core.NewJobService()
	if _, err := service.Submit(core.JobSpec{
		Name:    "job-1",
		Runtime: core.RuntimeHTTP,
		Target:  core.TargetSpec{URL: "https://example.com"},
	}); err != nil {
		t.Fatalf("unexpected submit error: %v", err)
	}

	console := NewWebConsole(8080)
	console.SetJobService(service)

	state := console.RenderState()
	if len(state["jobs"].([]core.JobSummary)) != 1 {
		t.Fatalf("expected one job in rendered state")
	}
}
