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
