package core

import (
	"fmt"
	"sync"
	"time"

	"gospider/events"
	"gospider/storage"
)

// JobSummary is the lightweight job view used by control surfaces.
type JobSummary struct {
	Name     string    `json:"name"`
	Runtime  Runtime   `json:"runtime"`
	URL      string    `json:"url"`
	Priority int       `json:"priority"`
	State    TaskState `json:"state"`
}

// JobRecord is the normalized control-plane representation for a stored job.
type JobRecord struct {
	Summary JobSummary `json:"summary"`
	Spec    JobSpec    `json:"spec"`
	Result  *JobResult `json:"result,omitempty"`
}

// JobStats captures basic in-memory control-plane counters.
type JobStats struct {
	Total     int `json:"total"`
	Queued    int `json:"queued"`
	Cancelled int `json:"cancelled"`
}

// JobService is the minimal shared task service for product entrypoints.
type JobService struct {
	mu      sync.RWMutex
	order   []string
	jobs    map[string]JobRecord
	results storage.ResultStore
	events  storage.EventStore
}

// NewJobService creates an in-memory shared job service.
func NewJobService() *JobService {
	return &JobService{
		order:   make([]string, 0),
		jobs:    make(map[string]JobRecord),
		results: storage.NewMemoryResultStore(),
		events:  storage.NewMemoryEventStore(1000),
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

	job.Name = key
	summary := JobSummary{
		Name:     key,
		Runtime:  job.Runtime,
		URL:      job.Target.URL,
		Priority: job.Priority,
		State:    StateQueued,
	}
	s.jobs[key] = JobRecord{
		Summary: summary,
		Spec:    job,
	}
	s.order = append(s.order, key)
	s.appendEvent(events.New(events.TopicTaskQueued, events.TaskLifecyclePayload{
		TaskID:    key,
		State:     string(StateQueued),
		Runtime:   string(job.Runtime),
		URL:       job.Target.URL,
		UpdatedAt: timeNow(),
		HasResult: false,
	}))
	return summary, nil
}

// List returns all known jobs in submission order.
func (s *JobService) List() []JobSummary {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make([]JobSummary, 0, len(s.order))
	for _, key := range s.order {
		record, ok := s.jobs[key]
		if ok {
			result = append(result, record.Summary)
		}
	}
	return result
}

// Get returns the stored normalized job record for a control-plane id.
func (s *JobService) Get(key string) (JobRecord, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	record, ok := s.jobs[key]
	return record, ok
}

// AttachResult stores a normalized result for a known job.
func (s *JobService) AttachResult(key string, result *JobResult) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	record, ok := s.jobs[key]
	if !ok {
		return fmt.Errorf("job %q not found", key)
	}
	record.Result = result
	s.jobs[key] = record
	if s.results != nil && result != nil {
		_ = s.results.Put(toStoredResultRecord(key, result))
	}
	if result != nil {
		s.appendEvent(events.New(events.TopicTaskResult, events.TaskResultPayload{
			TaskID:       key,
			State:        string(result.State),
			Runtime:      string(result.Runtime),
			URL:          result.URL,
			StatusCode:   result.StatusCode,
			Artifacts:    result.Artifacts,
			ArtifactRefs: toEventArtifactRefs(result.ArtifactRefs),
			UpdatedAt:    effectiveEventTime(result),
		}))
	}
	return nil
}

// GetStoredResult returns the normalized storage-layer result record.
func (s *JobService) GetStoredResult(key string) (storage.ResultRecord, bool) {
	if s.results == nil {
		return storage.ResultRecord{}, false
	}
	return s.results.Get(key)
}

// ListStoredResults returns stored result records ordered by most recent update.
func (s *JobService) ListStoredResults(limit int) []storage.ResultRecord {
	if s.results == nil {
		return nil
	}
	return s.results.List(limit)
}

// Delete removes a job from the in-memory control plane.
func (s *JobService) Delete(key string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, ok := s.jobs[key]; !ok {
		return false
	}
	delete(s.jobs, key)
	s.appendEvent(events.New(events.TopicTaskDeleted, events.TaskDeletedPayload{
		TaskID:    key,
		DeletedAt: timeNow(),
	}))
	return true
}

// Cancel transitions a queued job to cancelled.
func (s *JobService) Cancel(key string) (JobSummary, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	record, ok := s.jobs[key]
	if !ok {
		return JobSummary{}, fmt.Errorf("job %q not found", key)
	}
	if err := record.Summary.State.CanTransitionTo(StateCancelled); err != nil {
		return JobSummary{}, err
	}

	record.Summary.State = StateCancelled
	s.jobs[key] = record
	s.appendEvent(events.New(events.TopicTaskCancelled, events.TaskLifecyclePayload{
		TaskID:    key,
		State:     string(StateCancelled),
		Runtime:   string(record.Spec.Runtime),
		URL:       record.Spec.Target.URL,
		UpdatedAt: timeNow(),
		HasResult: record.Result != nil,
	}))
	return record.Summary, nil
}

// ListEvents returns recent normalized control-plane events.
func (s *JobService) ListEvents(limit int, topic string) []events.Event {
	if s.events == nil {
		return nil
	}
	return s.events.List(limit, topic)
}

// Stats returns a minimal state summary for lightweight control-plane deployments.
func (s *JobService) Stats() JobStats {
	s.mu.RLock()
	defer s.mu.RUnlock()

	stats := JobStats{Total: len(s.jobs)}
	for _, key := range s.order {
		record, ok := s.jobs[key]
		if !ok {
			continue
		}
		switch record.Summary.State {
		case StateQueued:
			stats.Queued++
		case StateCancelled:
			stats.Cancelled++
		}
	}
	return stats
}

func toStoredResultRecord(id string, result *JobResult) storage.ResultRecord {
	record := storage.ResultRecord{ID: id}
	if result == nil {
		return record
	}
	record.UpdatedAt = result.FinishedAt
	record.Warnings = append([]string(nil), result.Warnings...)
	record.StatusCode = result.StatusCode
	record.Runtime = string(result.Runtime)
	record.State = string(result.State)
	record.URL = result.URL
	if len(result.Extract) > 0 {
		record.Extract = make(map[string]interface{}, len(result.Extract))
		for key, value := range result.Extract {
			record.Extract[key] = value
		}
	}
	if len(result.ArtifactRefs) > 0 {
		record.Artifacts = make(map[string]storage.ArtifactRecord, len(result.ArtifactRefs))
		for name, artifact := range result.ArtifactRefs {
			record.Artifacts[name] = storage.ArtifactRecord{
				Name:     name,
				Kind:     artifact.Kind,
				URI:      artifact.URI,
				Path:     artifact.Path,
				Size:     artifact.Size,
				Metadata: artifact.Metadata,
			}
		}
	}
	if record.UpdatedAt.IsZero() {
		record.UpdatedAt = result.StartedAt
	}
	return record
}

func (s *JobService) appendEvent(event events.Event) {
	if s.events != nil {
		_ = s.events.Put(event)
	}
}

func effectiveEventTime(result *JobResult) time.Time {
	if result == nil {
		return timeNow()
	}
	if !result.FinishedAt.IsZero() {
		return result.FinishedAt
	}
	if !result.StartedAt.IsZero() {
		return result.StartedAt
	}
	return timeNow()
}

var timeNow = func() time.Time {
	return time.Now()
}

func toEventArtifactRefs(artifacts map[string]ArtifactRef) map[string]events.ArtifactRef {
	if len(artifacts) == 0 {
		return nil
	}
	result := make(map[string]events.ArtifactRef, len(artifacts))
	for name, artifact := range artifacts {
		result[name] = events.ArtifactRef{
			Kind:     artifact.Kind,
			URI:      artifact.URI,
			Path:     artifact.Path,
			Size:     artifact.Size,
			Metadata: artifact.Metadata,
		}
	}
	return result
}
