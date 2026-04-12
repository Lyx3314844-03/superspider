package storage

import (
	"encoding/json"
	"os"
	"sync"
)

// FileResultStore appends normalized results to a JSONL file.
type FileResultStore struct {
	mu   sync.Mutex
	path string
}

func NewFileResultStore(path string) *FileResultStore {
	return &FileResultStore{path: path}
}

func (s *FileResultStore) Put(record ResultRecord) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	payload, err := json.Marshal(record)
	if err != nil {
		return err
	}
	return appendWithAggregator(s.path, append(payload, '\n'))
}

func (s *FileResultStore) Get(id string) (ResultRecord, bool) {
	records := s.List(0)
	for i := len(records) - 1; i >= 0; i-- {
		if records[i].ID == id {
			return records[i], true
		}
	}
	return ResultRecord{}, false
}

func (s *FileResultStore) List(limit int) []ResultRecord {
	s.mu.Lock()
	defer s.mu.Unlock()
	handle, err := os.Open(s.path)
	if err != nil {
		return nil
	}
	defer handle.Close()
	decoder := json.NewDecoder(handle)
	records := make([]ResultRecord, 0)
	for {
		var record ResultRecord
		if err := decoder.Decode(&record); err != nil {
			break
		}
		records = append(records, record)
	}
	if limit > 0 && len(records) > limit {
		return records[len(records)-limit:]
	}
	return records
}
