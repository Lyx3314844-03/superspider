package dispatch

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"gospider/core"
)

func TestDispatchExecutorRoutesHTTPJobs(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	}))
	defer server.Close()

	executor := NewExecutor(Options{})
	result, err := executor.Execute(context.Background(), core.JobSpec{
		Name:    "http-job",
		Runtime: core.RuntimeHTTP,
		Target: core.TargetSpec{
			URL:    server.URL,
			Method: http.MethodGet,
		},
		Output: core.OutputSpec{Format: "json"},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.State != core.StateSucceeded {
		t.Fatalf("expected succeeded, got %s", result.State)
	}
	if result.Metrics == nil || result.Metrics.BytesIn == 0 {
		t.Fatal("expected metrics to be populated")
	}
}

func TestDispatchExecutorRoutesMediaJobsWithoutNetworkWhenDownloadDisabled(t *testing.T) {
	executor := NewExecutor(Options{})
	result, err := executor.Execute(context.Background(), core.JobSpec{
		Name:    "media-job",
		Runtime: core.RuntimeMedia,
		Target: core.TargetSpec{
			URL: "https://cdn.example.com/video.mp4",
		},
		Output: core.OutputSpec{Format: "artifact"},
		Media: core.MediaSpec{
			Enabled:   true,
			Download:  false,
			OutputDir: "downloads",
		},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.State != core.StateSucceeded {
		t.Fatalf("expected succeeded, got %s", result.State)
	}
	if len(result.MediaRecord) != 1 {
		t.Fatalf("expected one media artifact, got %d", len(result.MediaRecord))
	}
	if _, ok := result.ArtifactRefs["video"]; !ok {
		t.Fatal("expected named media artifact ref")
	}
}

func TestDispatchExecutorRoutesAIJobsUsingMockExtract(t *testing.T) {
	executor := NewExecutor(Options{})
	result, err := executor.Execute(context.Background(), core.JobSpec{
		Name:    "ai-job",
		Runtime: core.RuntimeAI,
		Target: core.TargetSpec{
			URL:  "https://example.com/article",
			Body: "ignored because mock extract is provided",
		},
		Output: core.OutputSpec{Format: "json"},
		Metadata: map[string]interface{}{
			"mock_extract": map[string]interface{}{
				"title": "hello",
			},
		},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.State != core.StateSucceeded {
		t.Fatalf("expected succeeded, got %s", result.State)
	}
	if result.Extract["title"] != "hello" {
		t.Fatalf("expected extracted title to round-trip")
	}
}

func TestDispatchExecutorRoutesBrowserJobsWhenBrowserExecutorProvided(t *testing.T) {
	executor := NewExecutor(Options{
		BrowserExecutor: func(ctx context.Context, job core.JobSpec) (string, error) {
			return "<html>browser</html>", nil
		},
	})

	result, err := executor.Execute(context.Background(), core.JobSpec{
		Name:    "browser-job",
		Runtime: core.RuntimeBrowser,
		Target:  core.TargetSpec{URL: "https://example.com"},
		Output:  core.OutputSpec{Format: "json"},
		Browser: core.BrowserSpec{
			Profile: "chrome-stealth",
		},
		AntiBot: core.AntiBotSpec{
			SessionMode: "sticky",
			Stealth:     true,
		},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Runtime != core.RuntimeBrowser {
		t.Fatalf("expected browser runtime, got %s", result.Runtime)
	}
	if result.AntiBot == nil || result.AntiBot.FingerprintProfile != "chrome-stealth" {
		t.Fatal("expected browser anti-bot trace")
	}
}
