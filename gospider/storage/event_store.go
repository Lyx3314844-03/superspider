package storage

import (
	"sync"

	"gospider/events"
)

// EventStore defines the minimal event history contract.
type EventStore interface {
	Put(event events.Event) error
	List(limit int, topic string) []events.Event
}

// MemoryEventStore keeps a bounded in-memory event history.
type MemoryEventStore struct {
	mu      sync.RWMutex
	events  []events.Event
	maxSize int
}

// NewMemoryEventStore creates an in-memory event history store.
func NewMemoryEventStore(maxSize int) *MemoryEventStore {
	if maxSize <= 0 {
		maxSize = 1000
	}
	return &MemoryEventStore{
		events:  make([]events.Event, 0),
		maxSize: maxSize,
	}
}

// Put appends an event and trims old history when needed.
func (s *MemoryEventStore) Put(event events.Event) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.events = append(s.events, event)
	if len(s.events) > s.maxSize {
		s.events = append([]events.Event(nil), s.events[len(s.events)-s.maxSize:]...)
	}
	return nil
}

// List returns events ordered newest-first with optional topic filtering.
func (s *MemoryEventStore) List(limit int, topic string) []events.Event {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if limit <= 0 {
		limit = len(s.events)
	}

	result := make([]events.Event, 0, limit)
	for i := len(s.events) - 1; i >= 0; i-- {
		event := s.events[i]
		if topic != "" && event.Topic != topic {
			continue
		}
		result = append(result, event)
		if len(result) >= limit {
			break
		}
	}
	return result
}
