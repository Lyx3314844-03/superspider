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

// Lease represents a leased normalized job.
type Lease struct {
	LeaseID   string
	WorkerID  string
	Job       core.JobSpec
	ExpiresAt time.Time
}

// JobRecord tracks normalized distributed job state.
type JobRecord struct {
	Job     core.JobSpec
	State   core.TaskState
	LeaseID string
}

// DistributedService is the minimal normalized distributed contract for jobs.
type DistributedService struct {
	mu       sync.RWMutex
	queue    []core.JobSpec
	jobs     map[string]*JobRecord
	leases   map[string]*Lease
	visited  map[string]bool
}

// NewDistributedService creates an in-memory distributed service.
func NewDistributedService() *DistributedService {
	return &DistributedService{
		queue:   make([]core.JobSpec, 0),
		jobs:    make(map[string]*JobRecord),
		leases:  make(map[string]*Lease),
		visited: make(map[string]bool),
	}
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
	s.visited[key] = true
	s.queue = append(s.queue, job)
	sort.Slice(s.queue, func(i, j int) bool {
		return s.queue[i].Priority > s.queue[j].Priority
	})
	s.jobs[key] = &JobRecord{Job: job, State: core.StateQueued}
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

	job := s.queue[0]
	s.queue = s.queue[1:]
	leaseID, err := newLeaseID()
	if err != nil {
		return nil, err
	}
	lease := &Lease{
		LeaseID:   leaseID,
		WorkerID:  workerID,
		Job:       job,
		ExpiresAt: time.Now().Add(ttl),
	}
	s.leases[lease.LeaseID] = lease
	s.jobs[job.Target.URL] = &JobRecord{
		Job:     job,
		State:   core.StateLeased,
		LeaseID: lease.LeaseID,
	}
	return lease, nil
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
	delete(s.leases, leaseID)
	return nil
}

// Retry marks a leased job for retry and requeues it.
func (s *DistributedService) Retry(leaseID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	lease, ok := s.leases[leaseID]
	if !ok {
		return fmt.Errorf("unknown lease %s", leaseID)
	}

	record := s.jobs[lease.Job.Target.URL]
	record.State = core.StateRetryScheduled
	record.LeaseID = leaseID
	s.queue = append(s.queue, lease.Job)
	sort.Slice(s.queue, func(i, j int) bool {
		return s.queue[i].Priority > s.queue[j].Priority
	})
	delete(s.leases, leaseID)
	return nil
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

func newLeaseID() (string, error) {
	buf := make([]byte, 8)
	if _, err := rand.Read(buf); err != nil {
		return "", err
	}
	return hex.EncodeToString(buf), nil
}
