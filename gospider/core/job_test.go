package core

import "testing"

func TestJobSpecSupportsHTTPAndBrowserModes(t *testing.T) {
	job := JobSpec{
		Name:    "example",
		Runtime: RuntimeBrowser,
		Target:  TargetSpec{URL: "https://example.com"},
	}

	if err := job.Validate(); err != nil {
		t.Fatalf("expected valid job, got %v", err)
	}
}

func TestStateTransitionRejectsInvalidMove(t *testing.T) {
	state := StateQueued
	if err := state.CanTransitionTo(StateSucceeded); err == nil {
		t.Fatal("expected invalid direct transition")
	}
}

func TestJobSpecNormalizesV2BrowserActions(t *testing.T) {
	job := JobSpec{
		Name:    "v2-browser",
		Runtime: RuntimeBrowser,
		Target:  TargetSpec{URL: "https://example.com"},
		Browser: BrowserSpec{
			Profile: "chrome-stealth",
			Actions: []ActionSpec{{Type: "goto", URL: "https://example.com"}},
		},
		Output: OutputSpec{Format: "json"},
	}

	if err := job.Validate(); err != nil {
		t.Fatalf("expected valid job, got %v", err)
	}
	if len(job.Actions) != 1 {
		t.Fatalf("expected v1-compatible actions mirror, got %d", len(job.Actions))
	}
}

func TestJobSpecSupportsMediaAndAIRuntimes(t *testing.T) {
	for _, runtime := range []Runtime{RuntimeMedia, RuntimeAI} {
		job := JobSpec{
			Name:    string(runtime) + "-job",
			Runtime: runtime,
			Target:  TargetSpec{URL: "https://example.com"},
			Output:  OutputSpec{Format: "json"},
		}
		if err := job.Validate(); err != nil {
			t.Fatalf("expected runtime %s to validate, got %v", runtime, err)
		}
	}
}

func TestJobServiceStoresNormalizedResultRecord(t *testing.T) {
	service := NewJobService()
	if _, err := service.Submit(JobSpec{
		Name:    "job-1",
		Runtime: RuntimeHTTP,
		Target:  TargetSpec{URL: "https://example.com"},
		Output:  OutputSpec{Format: "json"},
	}); err != nil {
		t.Fatalf("unexpected submit error: %v", err)
	}

	result := NewJobResult(JobSpec{
		Name:    "job-1",
		Runtime: RuntimeHTTP,
		Target:  TargetSpec{URL: "https://example.com"},
	}, StateSucceeded)
	result.SetExtractField("title", "hello")
	result.SetArtifact("html", ArtifactRef{Kind: "html", Path: "artifacts/job-1.html"})
	result.Finalize()

	if err := service.AttachResult("job-1", result); err != nil {
		t.Fatalf("unexpected attach error: %v", err)
	}

	stored, ok := service.GetStoredResult("job-1")
	if !ok {
		t.Fatal("expected stored result")
	}
	if stored.State != string(StateSucceeded) {
		t.Fatalf("expected stored state %s, got %s", StateSucceeded, stored.State)
	}
	if stored.Extract["title"] != "hello" {
		t.Fatalf("expected stored extract field")
	}
	if _, ok := stored.Artifacts["html"]; !ok {
		t.Fatal("expected stored artifact")
	}
}
