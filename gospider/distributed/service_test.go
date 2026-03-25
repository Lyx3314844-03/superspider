package distributed

import (
	"testing"
	"time"

	"gospider/core"
)

func TestDistributedServiceLeasesAndCompletesJob(t *testing.T) {
	service := NewDistributedService()
	job := core.JobSpec{
		Name:    "job-1",
		Runtime: core.RuntimeHTTP,
		Target:  core.TargetSpec{URL: "https://example.com"},
	}

	if err := service.Submit(job); err != nil {
		t.Fatalf("unexpected submit error: %v", err)
	}

	lease, err := service.Lease("worker-1", time.Minute)
	if err != nil {
		t.Fatalf("unexpected lease error: %v", err)
	}
	if lease == nil {
		t.Fatal("expected lease")
	}
	if lease.WorkerID != "worker-1" {
		t.Fatalf("expected worker-1, got %s", lease.WorkerID)
	}

	if err := service.Ack(lease.LeaseID); err != nil {
		t.Fatalf("unexpected ack error: %v", err)
	}

	stored, ok := service.Get(job.Target.URL)
	if !ok {
		t.Fatal("expected stored job")
	}
	if stored.State != core.StateSucceeded {
		t.Fatalf("expected succeeded state, got %s", stored.State)
	}
}

func TestDistributedServiceCanRetryLeasedJob(t *testing.T) {
	service := NewDistributedService()
	job := core.JobSpec{
		Name:    "job-2",
		Runtime: core.RuntimeHTTP,
		Target:  core.TargetSpec{URL: "https://example.com/retry"},
	}

	if err := service.Submit(job); err != nil {
		t.Fatalf("unexpected submit error: %v", err)
	}

	lease, err := service.Lease("worker-2", time.Minute)
	if err != nil {
		t.Fatalf("unexpected lease error: %v", err)
	}
	if lease == nil {
		t.Fatal("expected lease")
	}

	if err := service.Retry(lease.LeaseID); err != nil {
		t.Fatalf("unexpected retry error: %v", err)
	}

	stored, ok := service.Get(job.Target.URL)
	if !ok {
		t.Fatal("expected stored job")
	}
	if stored.State != core.StateRetryScheduled {
		t.Fatalf("expected retry_scheduled state, got %s", stored.State)
	}
	if service.QueueLen() != 1 {
		t.Fatalf("expected queued retry job, got %d", service.QueueLen())
	}
}
