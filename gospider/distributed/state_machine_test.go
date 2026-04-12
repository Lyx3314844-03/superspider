package distributed

import (
	"testing"
	"time"

	"gospider/core"
)

func TestEvaluateLeaseTransitionRequeuesBeforeRetryBudgetExhausted(t *testing.T) {
	job := core.JobSpec{
		Name:    "job-retry",
		Runtime: core.RuntimeHTTP,
		Target:  core.TargetSpec{URL: "https://example.com/retry"},
	}
	result := EvaluateLeaseTransition(LeaseTransitionInput{
		Job:         job,
		WorkerID:    "worker-1",
		LeaseID:     "lease-1",
		Attempt:     1,
		HeartbeatAt: time.Now(),
		ExpiresAt:   time.Now().Add(time.Second),
		Reason:      "lease expired",
		MaxRetries:  2,
		Expired:     true,
	})

	if !result.Requeue {
		t.Fatal("expected requeue before retry budget is exhausted")
	}
	if result.DeadLetter != nil {
		t.Fatal("did not expect dead letter before retry budget is exhausted")
	}
	if result.Record.State != core.StateExpired {
		t.Fatalf("expected expired state, got %s", result.Record.State)
	}
}

func TestEvaluateLeaseTransitionDeadLettersAfterRetryBudgetExhausted(t *testing.T) {
	job := core.JobSpec{
		Name:    "job-dead",
		Runtime: core.RuntimeHTTP,
		Target:  core.TargetSpec{URL: "https://example.com/dead"},
	}
	result := EvaluateLeaseTransition(LeaseTransitionInput{
		Job:         job,
		WorkerID:    "worker-2",
		LeaseID:     "lease-2",
		Attempt:     3,
		HeartbeatAt: time.Now(),
		ExpiresAt:   time.Now().Add(time.Second),
		Reason:      "lease expired",
		MaxRetries:  2,
		Expired:     true,
	})

	if result.Requeue {
		t.Fatal("did not expect requeue after retry budget is exhausted")
	}
	if result.DeadLetter == nil {
		t.Fatal("expected dead letter after retry budget is exhausted")
	}
	if result.Record.State != core.StateFailed {
		t.Fatalf("expected failed state, got %s", result.Record.State)
	}
}
