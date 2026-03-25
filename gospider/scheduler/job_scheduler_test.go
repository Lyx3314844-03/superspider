package scheduler

import (
	"testing"

	"gospider/core"
)

func TestSchedulerQueuesJobSpecByPriority(t *testing.T) {
	s := NewJobScheduler()

	if err := s.Enqueue(core.JobSpec{
		Name:     "low",
		Runtime:  core.RuntimeHTTP,
		Target:   core.TargetSpec{URL: "https://example.com/low"},
		Priority: 1,
	}); err != nil {
		t.Fatalf("unexpected enqueue error: %v", err)
	}

	if err := s.Enqueue(core.JobSpec{
		Name:     "high",
		Runtime:  core.RuntimeHTTP,
		Target:   core.TargetSpec{URL: "https://example.com/high"},
		Priority: 10,
	}); err != nil {
		t.Fatalf("unexpected enqueue error: %v", err)
	}

	job := s.Next()
	if job == nil {
		t.Fatal("expected queued job")
	}
	if job.Name != "high" {
		t.Fatalf("expected high priority job, got %s", job.Name)
	}
}
