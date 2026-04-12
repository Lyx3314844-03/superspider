package storage

import (
	"sort"
	"sync"
	"time"
)

// ArtifactRecord is the storage-layer representation of an output artifact.
type ArtifactRecord struct {
	Name     string                 `json:"name"`
	Kind     string                 `json:"kind,omitempty"`
	URI      string                 `json:"uri,omitempty"`
	Path     string                 `json:"path,omitempty"`
	Size     int64                  `json:"size,omitempty"`
	Metadata map[string]interface{} `json:"metadata,omitempty"`
}

// ResultRecord is the storage-layer representation of a normalized crawl result.
type ResultRecord struct {
	ID         string                    `json:"id"`
	Runtime    string                    `json:"runtime,omitempty"`
	State      string                    `json:"state,omitempty"`
	URL        string                    `json:"url,omitempty"`
	StatusCode int                       `json:"status_code,omitempty"`
	Extract    map[string]interface{}    `json:"extract,omitempty"`
	Artifacts  map[string]ArtifactRecord `json:"artifacts,omitempty"`
	Warnings   []string                  `json:"warnings,omitempty"`
	UpdatedAt  time.Time                 `json:"updated_at"`
}

// ResultStore defines the minimal normalized result indexing contract.
type ResultStore interface {
	Put(record ResultRecord) error
	Get(id string) (ResultRecord, bool)
	List(limit int) []ResultRecord
}

// MemoryResultStore is an in-memory result index for control-plane use.
type MemoryResultStore struct {
	mu      sync.RWMutex
	records map[string]ResultRecord
	order   []string
}

// NewMemoryResultStore creates an empty in-memory result store.
func NewMemoryResultStore() *MemoryResultStore {
	return &MemoryResultStore{
		records: make(map[string]ResultRecord),
		order:   make([]string, 0),
	}
}

// Put stores or replaces a result record.
func (s *MemoryResultStore) Put(record ResultRecord) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, exists := s.records[record.ID]; !exists {
		s.order = append(s.order, record.ID)
	}
	if record.UpdatedAt.IsZero() {
		record.UpdatedAt = time.Now()
	}
	s.records[record.ID] = record
	return nil
}

// Get returns a stored result record by id.
func (s *MemoryResultStore) Get(id string) (ResultRecord, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	record, ok := s.records[id]
	return record, ok
}

// List returns records ordered by most-recent update first.
func (s *MemoryResultStore) List(limit int) []ResultRecord {
	s.mu.RLock()
	defer s.mu.RUnlock()

	records := make([]ResultRecord, 0, len(s.records))
	for _, record := range s.records {
		records = append(records, record)
	}

	sort.Slice(records, func(i, j int) bool {
		if records[i].UpdatedAt.Equal(records[j].UpdatedAt) {
			return records[i].ID > records[j].ID
		}
		return records[i].UpdatedAt.After(records[j].UpdatedAt)
	})

	if limit > 0 && len(records) > limit {
		records = records[:limit]
	}
	return records
}
