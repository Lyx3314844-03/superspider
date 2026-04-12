package distributed

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"sort"
	"sync"
	"time"

	"gospider/core"
)

const (
	defaultLeaseTTL   = 30 * time.Second
	defaultMaxRetries = 3
)

// ServiceOptions configures distributed lease behavior.
type ServiceOptions struct {
	DefaultLeaseTTL time.Duration
	MaxRetries      int
}

// Lease represents a leased normalized job.
type Lease struct {
	LeaseID     string
	WorkerID    string
	Job         core.JobSpec
	Attempt     int
	ExpiresAt   time.Time
	HeartbeatAt time.Time
}

// JobRecord tracks normalized distributed job state.
type JobRecord struct {
	Job            core.JobSpec
	State          core.TaskState
	LeaseID        string
	Attempts       int
	LastError      string
	LastWorkerID   string
	LastHeartbeat  time.Time
	LeaseExpiresAt time.Time
	UpdatedAt      time.Time
}

// DeadLetterRecord captures a job that exceeded its retry budget.
type DeadLetterRecord struct {
	Job        core.JobSpec   `json:"job"`
	WorkerID   string         `json:"worker_id"`
	LeaseID    string         `json:"lease_id"`
	Attempts   int            `json:"attempts"`
	Reason     string         `json:"reason"`
	DeadAt     time.Time      `json:"dead_at"`
	FinalState core.TaskState `json:"final_state"`
}

// ServiceStats exposes resilience-oriented counters for the in-memory service.
type ServiceStats struct {
	Queued            int           `json:"queued"`
	ActiveLeases      int           `json:"active_leases"`
	DeadLetters       int           `json:"dead_letters"`
	MaxRetries        int           `json:"max_retries"`
	MaxAttempts       int           `json:"max_attempts"`
	DefaultLeaseTTL   time.Duration `json:"default_lease_ttl"`
	PeakQueueDepth    int           `json:"peak_queue_depth"`
	PeakActiveLeases  int           `json:"peak_active_leases"`
	TotalSubmitted    int           `json:"total_submitted"`
	TotalLeased       int           `json:"total_leased"`
	TotalHeartbeats   int           `json:"total_heartbeats"`
	TotalAcknowledged int           `json:"total_acknowledged"`
	TotalRetried      int           `json:"total_retried"`
	TotalExpired      int           `json:"total_expired"`
	TotalDeadLetters  int           `json:"total_dead_letters"`
}

// DistributedService is the minimal normalized distributed contract for jobs.
type DistributedService struct {
	mu          sync.RWMutex
	queue       []core.JobSpec
	jobs        map[string]*JobRecord
	leases      map[string]*Lease
	deadLetters map[string]*DeadLetterRecord
	visited     map[string]bool
	defaultTTL  time.Duration
	maxRetries  int
	stats       ServiceStats
}

// NewDistributedService creates an in-memory distributed service with defaults.
func NewDistributedService() *DistributedService {
	return NewDistributedServiceWithOptions(ServiceOptions{})
}

// NewDistributedServiceWithOptions creates an in-memory distributed service with custom resilience settings.
func NewDistributedServiceWithOptions(opts ServiceOptions) *DistributedService {
	ttl := opts.DefaultLeaseTTL
	if ttl <= 0 {
		ttl = defaultLeaseTTL
	}
	maxRetries := opts.MaxRetries
	if maxRetries < 0 {
		maxRetries = 0
	}
	if opts.MaxRetries == 0 {
		maxRetries = defaultMaxRetries
	}

	service := &DistributedService{
		queue:       make([]core.JobSpec, 0),
		jobs:        make(map[string]*JobRecord),
		leases:      make(map[string]*Lease),
		deadLetters: make(map[string]*DeadLetterRecord),
		visited:     make(map[string]bool),
		defaultTTL:  ttl,
		maxRetries:  maxRetries,
	}
	service.stats.MaxRetries = maxRetries
	service.stats.MaxAttempts = maxRetries + 1
	service.stats.DefaultLeaseTTL = ttl
	return service
}

// Submit queues a normalized job for distributed processing.
func (s *DistributedService) Submit(job core.JobSpec) error {
	if err := job.Validate(); err != nil {
		return err
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	key := job.Target.URL
	if s.visited[key] {
		return nil
	}
	now := time.Now()
	s.visited[key] = true
	s.queueJobLocked(job)
	s.jobs[key] = &JobRecord{
		Job:       job,
		State:     core.StateQueued,
		UpdatedAt: now,
	}
	s.stats.TotalSubmitted++
	return nil
}

// Lease returns the next available job lease for a worker.
func (s *DistributedService) Lease(workerID string, ttl time.Duration) (*Lease, error) {
	if workerID == "" {
		return nil, fmt.Errorf("worker id is required")
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if len(s.queue) == 0 {
		return nil, nil
	}

	if ttl <= 0 {
		ttl = s.defaultTTL
	}

	job := s.queue[0]
	s.queue = s.queue[1:]
	leaseID, err := newLeaseID()
	if err != nil {
		return nil, err
	}
	now := time.Now()
	lease := &Lease{
		LeaseID:     leaseID,
		WorkerID:    workerID,
		Job:         job,
		Attempt:     s.jobs[job.Target.URL].Attempts + 1,
		ExpiresAt:   now.Add(ttl),
		HeartbeatAt: now,
	}
	s.leases[lease.LeaseID] = lease

	record := s.jobs[job.Target.URL]
	record.State = core.StateLeased
	record.LeaseID = lease.LeaseID
	record.Attempts = lease.Attempt
	record.LastWorkerID = workerID
	record.LastHeartbeat = now
	record.LeaseExpiresAt = lease.ExpiresAt
	record.UpdatedAt = now

	s.stats.TotalLeased++
	if len(s.leases) > s.stats.PeakActiveLeases {
		s.stats.PeakActiveLeases = len(s.leases)
	}

	return lease, nil
}

// Heartbeat renews a lease and records the most recent heartbeat timestamp.
func (s *DistributedService) Heartbeat(leaseID string, ttl time.Duration) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	lease, ok := s.leases[leaseID]
	if !ok {
		return fmt.Errorf("unknown lease %s", leaseID)
	}
	if ttl <= 0 {
		ttl = s.defaultTTL
	}

	now := time.Now()
	lease.HeartbeatAt = now
	lease.ExpiresAt = now.Add(ttl)

	record := s.jobs[lease.Job.Target.URL]
	record.LastHeartbeat = now
	record.LeaseExpiresAt = lease.ExpiresAt
	record.UpdatedAt = now

	s.stats.TotalHeartbeats++
	return nil
}

// Ack marks a leased job as succeeded.
func (s *DistributedService) Ack(leaseID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	lease, ok := s.leases[leaseID]
	if !ok {
		return fmt.Errorf("unknown lease %s", leaseID)
	}

	record := s.jobs[lease.Job.Target.URL]
	record.State = core.StateSucceeded
	record.LeaseID = leaseID
	record.UpdatedAt = time.Now()
	delete(s.leases, leaseID)
	s.stats.TotalAcknowledged++
	return nil
}

// Retry marks a leased job for retry and requeues it.
func (s *DistributedService) Retry(leaseID string) error {
	return s.RetryWithError(leaseID, "")
}

// RetryWithError marks a leased job for retry with an explanatory reason.
func (s *DistributedService) RetryWithError(leaseID, reason string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	lease, ok := s.leases[leaseID]
	if !ok {
		return fmt.Errorf("unknown lease %s", leaseID)
	}
	return s.retryOrDeadLetterLocked(lease, core.StateRetryScheduled, defaultReason(reason, "retry requested"))
}

// Fail records a failed lease attempt; jobs are retried until the retry budget is exhausted.
func (s *DistributedService) Fail(leaseID, reason string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	lease, ok := s.leases[leaseID]
	if !ok {
		return fmt.Errorf("unknown lease %s", leaseID)
	}
	return s.retryOrDeadLetterLocked(lease, core.StateFailed, defaultReason(reason, "worker execution failed"))
}

// ReapExpiredLeases requeues or dead-letters expired leases and returns the number reaped.
func (s *DistributedService) ReapExpiredLeases(now time.Time) int {
	s.mu.Lock()
	defer s.mu.Unlock()

	if now.IsZero() {
		now = time.Now()
	}

	expired := 0
	for leaseID, lease := range s.leases {
		if lease.ExpiresAt.After(now) {
			continue
		}
		expired++
		record := s.jobs[lease.Job.Target.URL]
		record.State = core.StateExpired
		record.UpdatedAt = now
		record.LastError = "lease expired"
		_ = s.retryOrDeadLetterLocked(lease, core.StateExpired, "lease expired")
		delete(s.leases, leaseID)
	}

	return expired
}

// DeadLetters returns the current dead-letter queue entries sorted by time.
func (s *DistributedService) DeadLetters() []DeadLetterRecord {
	s.mu.RLock()
	defer s.mu.RUnlock()

	records := make([]DeadLetterRecord, 0, len(s.deadLetters))
	for _, record := range s.deadLetters {
		records = append(records, *record)
	}
	sort.Slice(records, func(i, j int) bool {
		if records[i].DeadAt.Equal(records[j].DeadAt) {
			return records[i].Job.Target.URL < records[j].Job.Target.URL
		}
		return records[i].DeadAt.Before(records[j].DeadAt)
	})
	return records
}

// ActiveLeases returns the number of active leases.
func (s *DistributedService) ActiveLeases() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return len(s.leases)
}

// Stats returns a snapshot of current resilience-oriented service counters.
func (s *DistributedService) Stats() ServiceStats {
	s.mu.RLock()
	defer s.mu.RUnlock()

	stats := s.stats
	stats.Queued = len(s.queue)
	stats.ActiveLeases = len(s.leases)
	stats.DeadLetters = len(s.deadLetters)
	return stats
}

// Get returns the current stored record for a normalized job key.
func (s *DistributedService) Get(key string) (*JobRecord, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	record, ok := s.jobs[key]
	return record, ok
}

// QueueLen returns the number of queued normalized jobs.
func (s *DistributedService) QueueLen() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return len(s.queue)
}

func (s *DistributedService) queueJobLocked(job core.JobSpec) {
	s.queue = append(s.queue, job)
	sort.Slice(s.queue, func(i, j int) bool {
		return s.queue[i].Priority > s.queue[j].Priority
	})
	if len(s.queue) > s.stats.PeakQueueDepth {
		s.stats.PeakQueueDepth = len(s.queue)
	}
}

func (s *DistributedService) retryOrDeadLetterLocked(lease *Lease, nextState core.TaskState, reason string) error {
	record := s.jobs[lease.Job.Target.URL]
	delete(s.leases, lease.LeaseID)
	result := EvaluateLeaseTransition(LeaseTransitionInput{
		Job:         record.Job,
		WorkerID:    lease.WorkerID,
		LeaseID:     lease.LeaseID,
		Attempt:     record.Attempts,
		HeartbeatAt: lease.HeartbeatAt,
		ExpiresAt:   lease.ExpiresAt,
		Reason:      reason,
		MaxRetries:  s.maxRetries,
		Expired:     nextState == core.StateExpired,
	})
	*record = result.Record
	if result.DeadLetter != nil {
		s.deadLetters[record.Job.Target.URL] = result.DeadLetter
		s.stats.TotalDeadLetters++
		return nil
	}
	if result.Requeue {
		s.queueJobLocked(lease.Job)
	}
	if nextState == core.StateExpired {
		s.stats.TotalExpired++
	} else {
		s.stats.TotalRetried++
	}
	return nil
}

func defaultReason(reason, fallback string) string {
	if reason != "" {
		return reason
	}
	return fallback
}

func newLeaseID() (string, error) {
	buf := make([]byte, 8)
	if _, err := rand.Read(buf); err != nil {
		return "", err
	}
	return hex.EncodeToString(buf), nil
}
