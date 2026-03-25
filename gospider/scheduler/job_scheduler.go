package scheduler

import (
	"sort"
	"sync"

	"gospider/core"
)

// JobScheduler stores normalized jobs while preserving request-like priority ordering.
type JobScheduler struct {
	queue   []core.JobSpec
	visited map[string]bool
	mu      sync.RWMutex
}

// NewJobScheduler creates an empty normalized job scheduler.
func NewJobScheduler() *JobScheduler {
	return &JobScheduler{
		queue:   make([]core.JobSpec, 0),
		visited: make(map[string]bool),
	}
}

// Enqueue adds a validated job to the scheduler if its target has not been seen.
func (s *JobScheduler) Enqueue(job core.JobSpec) error {
	if err := job.Validate(); err != nil {
		return err
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if s.visited[job.Target.URL] {
		return nil
	}
	s.visited[job.Target.URL] = true
	s.queue = append(s.queue, job)
	sort.Slice(s.queue, func(i, j int) bool {
		return s.queue[i].Priority > s.queue[j].Priority
	})
	return nil
}

// Next returns the next highest-priority normalized job.
func (s *JobScheduler) Next() *core.JobSpec {
	s.mu.Lock()
	defer s.mu.Unlock()

	if len(s.queue) == 0 {
		return nil
	}

	job := s.queue[0]
	s.queue = s.queue[1:]
	return &job
}

// QueueLen returns the number of pending normalized jobs.
func (s *JobScheduler) QueueLen() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return len(s.queue)
}

// VisitedCount returns the number of unique target URLs seen by the scheduler.
func (s *JobScheduler) VisitedCount() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return len(s.visited)
}
