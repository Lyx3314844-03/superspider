package core

import (
	"fmt"
	"sync"
)

// JobSummary is the lightweight job view used by control surfaces.
type JobSummary struct {
	Name     string    `json:"name"`
	Runtime  Runtime   `json:"runtime"`
	URL      string    `json:"url"`
	Priority int       `json:"priority"`
	State    TaskState `json:"state"`
}

// JobService is the minimal shared task service for product entrypoints.
type JobService struct {
	mu    sync.RWMutex
	order []string
	jobs  map[string]JobSummary
}

// NewJobService creates an in-memory shared job service.
func NewJobService() *JobService {
	return &JobService{
		order: make([]string, 0),
		jobs:  make(map[string]JobSummary),
	}
}

// Submit validates and stores a normalized job for control-surface use.
func (s *JobService) Submit(job JobSpec) (JobSummary, error) {
	if err := job.Validate(); err != nil {
		return JobSummary{}, err
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	key := job.Name
	if key == "" {
		key = job.Target.URL
	}
	if _, exists := s.jobs[key]; exists {
		return JobSummary{}, fmt.Errorf("job %q already exists", key)
	}

	summary := JobSummary{
		Name:     key,
		Runtime:  job.Runtime,
		URL:      job.Target.URL,
		Priority: job.Priority,
		State:    StateQueued,
	}
	s.jobs[key] = summary
	s.order = append(s.order, key)
	return summary, nil
}

// List returns all known jobs in submission order.
func (s *JobService) List() []JobSummary {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make([]JobSummary, 0, len(s.order))
	for _, key := range s.order {
		result = append(result, s.jobs[key])
	}
	return result
}
