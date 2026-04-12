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

func TestDistributedServiceHeartbeatRenewsLease(t *testing.T) {
	service := NewDistributedServiceWithOptions(ServiceOptions{
		DefaultLeaseTTL: 10 * time.Millisecond,
		MaxRetries:      1,
	})
	job := core.JobSpec{
		Name:    "job-heartbeat",
		Runtime: core.RuntimeHTTP,
		Target:  core.TargetSpec{URL: "https://example.com/heartbeat"},
	}

	if err := service.Submit(job); err != nil {
		t.Fatalf("unexpected submit error: %v", err)
	}

	lease, err := service.Lease("worker-heartbeat", 10*time.Millisecond)
	if err != nil {
		t.Fatalf("unexpected lease error: %v", err)
	}
	if lease == nil {
		t.Fatal("expected lease")
	}
	before := lease.ExpiresAt

	time.Sleep(2 * time.Millisecond)
	if err := service.Heartbeat(lease.LeaseID, 50*time.Millisecond); err != nil {
		t.Fatalf("unexpected heartbeat error: %v", err)
	}

	stored, ok := service.Get(job.Target.URL)
	if !ok {
		t.Fatal("expected stored job")
	}
	if !stored.LeaseExpiresAt.After(before) {
		t.Fatalf("expected renewed lease expiry after %s, got %s", before, stored.LeaseExpiresAt)
	}

	stats := service.Stats()
	if stats.TotalHeartbeats != 1 {
		t.Fatalf("expected one heartbeat, got %d", stats.TotalHeartbeats)
	}
}

func TestDistributedServiceExpiredLeaseRequeuesUntilDeadLetter(t *testing.T) {
	service := NewDistributedServiceWithOptions(ServiceOptions{
		DefaultLeaseTTL: 5 * time.Millisecond,
		MaxRetries:      1,
	})
	job := core.JobSpec{
		Name:    "job-expire",
		Runtime: core.RuntimeHTTP,
		Target:  core.TargetSpec{URL: "https://example.com/expire"},
	}

	if err := service.Submit(job); err != nil {
		t.Fatalf("unexpected submit error: %v", err)
	}

	firstLease, err := service.Lease("worker-expire-1", 5*time.Millisecond)
	if err != nil {
		t.Fatalf("unexpected first lease error: %v", err)
	}
	if firstLease == nil {
		t.Fatal("expected first lease")
	}

	if reaped := service.ReapExpiredLeases(firstLease.ExpiresAt.Add(time.Millisecond)); reaped != 1 {
		t.Fatalf("expected one expired lease to be reaped, got %d", reaped)
	}
	if len(service.DeadLetters()) != 0 {
		t.Fatal("expected no dead letters after first expiry")
	}
	if service.QueueLen() != 1 {
		t.Fatalf("expected expired job to be requeued, got %d", service.QueueLen())
	}

	secondLease, err := service.Lease("worker-expire-2", 5*time.Millisecond)
	if err != nil {
		t.Fatalf("unexpected second lease error: %v", err)
	}
	if secondLease == nil {
		t.Fatal("expected second lease")
	}

	if reaped := service.ReapExpiredLeases(secondLease.ExpiresAt.Add(time.Millisecond)); reaped != 1 {
		t.Fatalf("expected second expiry to be reaped, got %d", reaped)
	}

	deadLetters := service.DeadLetters()
	if len(deadLetters) != 1 {
		t.Fatalf("expected one dead-letter entry, got %d", len(deadLetters))
	}
	if deadLetters[0].Reason != "lease expired" {
		t.Fatalf("expected lease expired dead-letter reason, got %s", deadLetters[0].Reason)
	}

	stored, ok := service.Get(job.Target.URL)
	if !ok {
		t.Fatal("expected stored job")
	}
	if stored.State != core.StateFailed {
		t.Fatalf("expected failed state after dead-lettering, got %s", stored.State)
	}

	stats := service.Stats()
	if stats.TotalExpired != 1 {
		t.Fatalf("expected one requeued expiry, got %d", stats.TotalExpired)
	}
	if stats.TotalDeadLetters != 1 {
		t.Fatalf("expected one dead letter, got %d", stats.TotalDeadLetters)
	}
}
