package dispatch

import (
	"context"
	"strings"
	"testing"
	"time"

	"gospider/core"
)

type stubExecutor struct {
	result *core.JobResult
	err    error
}

func (s stubExecutor) Execute(_ context.Context, _ core.JobSpec) (*core.JobResult, error) {
	return s.result, s.err
}

func TestPolicyExecutorRejectsBlockedDomains(t *testing.T) {
	executor := &policyExecutor{inner: stubExecutor{}}
	job := core.JobSpec{
		Name:    "blocked-domain",
		Runtime: core.RuntimeHTTP,
		Target: core.TargetSpec{
			URL:            "https://example.com",
			AllowedDomains: []string{"blocked.com"},
		},
		Output: core.OutputSpec{Format: "json"},
	}

	result, err := executor.Execute(context.Background(), job)
	if err == nil {
		t.Fatal("expected allowed domain validation to fail")
	}
	if !strings.Contains(err.Error(), "allowed_domains") {
		t.Fatalf("unexpected error: %v", err)
	}
	if result == nil || result.State != core.StateFailed {
		t.Fatalf("expected failed result, got %#v", result)
	}
}

func TestPolicyExecutorDerivesSameDomainAllowList(t *testing.T) {
	result := core.NewJobResult(core.JobSpec{
		Name:    "same-domain",
		Runtime: core.RuntimeAI,
		Target:  core.TargetSpec{URL: "https://example.com"},
	}, core.StateSucceeded)
	result.Text = "ok"
	result.FinishedAt = result.StartedAt
	result.Finalize()

	executor := &policyExecutor{inner: stubExecutor{result: result}}
	job := core.JobSpec{
		Name:    "same-domain",
		Runtime: core.RuntimeAI,
		Target:  core.TargetSpec{URL: "https://example.com"},
		Policy:  core.PolicySpec{SameDomainOnly: true},
		Output:  core.OutputSpec{Format: "json"},
	}

	if _, err := executor.Execute(context.Background(), job); err != nil {
		t.Fatalf("expected same-domain job to pass, got %v", err)
	}
}

func TestPolicyExecutorEnforcesByteBudget(t *testing.T) {
	job := core.JobSpec{
		Name:    "budget",
		Runtime: core.RuntimeAI,
		Target:  core.TargetSpec{URL: "https://example.com"},
		Policy: core.PolicySpec{
			Budget: core.BudgetSpec{BytesIn: 8},
		},
		Output: core.OutputSpec{Format: "json"},
	}
	result := core.NewJobResult(job, core.StateSucceeded)
	result.Text = "this payload is too large"
	result.FinishedAt = result.StartedAt
	result.Finalize()

	executor := &policyExecutor{inner: stubExecutor{result: result}}
	policyResult, err := executor.Execute(context.Background(), job)
	if err == nil {
		t.Fatal("expected byte budget failure")
	}
	if !strings.Contains(err.Error(), "budget.bytes_in") {
		t.Fatalf("unexpected error: %v", err)
	}
	if policyResult == nil || policyResult.State != core.StateFailed {
		t.Fatalf("expected failed result, got %#v", policyResult)
	}
}

func TestPolicyExecutorEnforcesWallTimeBudget(t *testing.T) {
	job := core.JobSpec{
		Name:    "wall-time",
		Runtime: core.RuntimeAI,
		Target:  core.TargetSpec{URL: "https://example.com"},
		Policy: core.PolicySpec{
			Budget: core.BudgetSpec{WallTimeMS: 1},
		},
		Output: core.OutputSpec{Format: "json"},
	}
	result := core.NewJobResult(job, core.StateSucceeded)
	result.Text = "ok"
	result.StartedAt = time.Now().Add(-5 * time.Millisecond)
	result.FinishedAt = time.Now()
	result.Finalize()

	executor := &policyExecutor{inner: stubExecutor{result: result}}
	policyResult, err := executor.Execute(context.Background(), job)
	if err == nil {
		t.Fatal("expected wall time budget failure")
	}
	if !strings.Contains(err.Error(), "budget.wall_time_ms") {
		t.Fatalf("unexpected error: %v", err)
	}
	if policyResult == nil || policyResult.State != core.StateFailed {
		t.Fatalf("expected failed result, got %#v", policyResult)
	}
}
