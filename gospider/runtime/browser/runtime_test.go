package browserruntime

import (
	"context"
	"testing"

	"gospider/core"
)

func TestBrowserRuntimeEmitsNormalizedResult(t *testing.T) {
	runtime := NewRuntime(func(ctx context.Context, job core.JobSpec) (string, error) {
		return "<html><title>browser</title><img src=\"https://cdn.example.com/a.jpg\"></html>", nil
	})

	job := core.JobSpec{
		Name:    "browser-fetch",
		Runtime: core.RuntimeBrowser,
		Target:  core.TargetSpec{URL: "https://example.com"},
	}

	result, err := runtime.Execute(context.Background(), job)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.State != core.StateSucceeded {
		t.Fatalf("expected succeeded, got %s", result.State)
	}
	if result.Runtime != core.RuntimeBrowser {
		t.Fatalf("expected browser runtime, got %s", result.Runtime)
	}
	if result.Text == "" {
		t.Fatal("expected browser result text")
	}
}
