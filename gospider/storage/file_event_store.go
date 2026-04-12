package storage

import (
	"encoding/json"
	"os"
	"sync"

	"gospider/events"
)

// FileEventStore appends normalized events to a JSONL file.
type FileEventStore struct {
	mu   sync.Mutex
	path string
}

func NewFileEventStore(path string) *FileEventStore {
	return &FileEventStore{path: path}
}

func (s *FileEventStore) Put(event events.Event) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	payload, err := json.Marshal(event)
	if err != nil {
		return err
	}
	return appendWithAggregator(s.path, append(payload, '\n'))
}

func (s *FileEventStore) List(limit int, topic string) []events.Event {
	s.mu.Lock()
	defer s.mu.Unlock()
	handle, err := os.Open(s.path)
	if err != nil {
		return nil
	}
	defer handle.Close()
	decoder := json.NewDecoder(handle)
	result := make([]events.Event, 0)
	for {
		var event events.Event
		if err := decoder.Decode(&event); err != nil {
			break
		}
		if topic != "" && event.Topic != topic {
			continue
		}
		result = append(result, event)
	}
	if limit > 0 && len(result) > limit {
		return result[len(result)-limit:]
	}
	return result
}
