package core

import (
	"context"
	"errors"
	"testing"
	"time"
)

type blockingExecutor struct {
	started chan struct{}
}

func (b *blockingExecutor) Execute(ctx context.Context, job JobSpec) (*JobResult, error) {
	close(b.started)
	<-ctx.Done()
	return nil, ctx.Err()
}

func TestJobRunnerCancelCancelsRunningJob(t *testing.T) {
	runner := NewJobRunner(DefaultConfig())
	executor := &blockingExecutor{started: make(chan struct{})}
	runner.SetExecutor(executor)

	job := &JobSpec{
		Name:    "cancel-me",
		Runtime: RuntimeHTTP,
		Target:  TargetSpec{URL: "https://example.com"},
		Output:  OutputSpec{Format: "json"},
		Resources: ResourceSpec{
			Timeout: 5 * time.Second,
		},
	}

	done := make(chan error, 1)
	go func() {
		_, err := runner.Run(context.Background(), job)
		done <- err
	}()

	select {
	case <-executor.started:
	case <-time.After(2 * time.Second):
		t.Fatal("executor did not start")
	}

	if !runner.IsRunning(job.Name) {
		t.Fatal("expected job to be marked running")
	}

	if err := runner.Cancel(job.Name); err != nil {
		t.Fatalf("cancel failed: %v", err)
	}

	select {
	case err := <-done:
		if err == nil {
			t.Fatal("expected cancelled job to return an error")
		}
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("expected wrapped context cancellation, got %v", err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("cancelled job did not exit")
	}

	if runner.IsRunning(job.Name) {
		t.Fatal("expected job to be removed from running set after cancellation")
	}
}

func TestJobRunnerCancelRejectsUnknownJob(t *testing.T) {
	runner := NewJobRunner(DefaultConfig())
	if err := runner.Cancel("missing-job"); err == nil {
		t.Fatal("expected cancelling unknown job to fail")
	}
}
