package events

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
)

// Bus is the minimal event publish/list contract used by control-plane workflows.
type Bus interface {
	Publish(Event) error
	List(limit int, topic string) []Event
}

// MemoryBus keeps a bounded in-memory history.
type MemoryBus struct {
	mu      sync.Mutex
	maxSize int
	events  []Event
}

func NewMemoryBus(maxSize int) *MemoryBus {
	if maxSize <= 0 {
		maxSize = 256
	}
	return &MemoryBus{maxSize: maxSize, events: make([]Event, 0, maxSize)}
}

func (b *MemoryBus) Publish(event Event) error {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.events = append(b.events, event)
	if len(b.events) > b.maxSize {
		b.events = append([]Event(nil), b.events[len(b.events)-b.maxSize:]...)
	}
	return nil
}

func (b *MemoryBus) List(limit int, topic string) []Event {
	b.mu.Lock()
	defer b.mu.Unlock()
	if limit <= 0 || limit > len(b.events) {
		limit = len(b.events)
	}
	result := make([]Event, 0, limit)
	for idx := len(b.events) - 1; idx >= 0; idx-- {
		event := b.events[idx]
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

// FileBus appends events to a JSONL file and mirrors them in memory for quick listing.
type FileBus struct {
	path   string
	memory *MemoryBus
	mu     sync.Mutex
}

func NewFileBus(path string) *FileBus {
	return &FileBus{
		path:   path,
		memory: NewMemoryBus(1024),
	}
}

func (b *FileBus) Publish(event Event) error {
	b.mu.Lock()
	defer b.mu.Unlock()
	if err := b.memory.Publish(event); err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(b.path), 0o755); err != nil {
		return err
	}
	file, err := os.OpenFile(b.path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	defer file.Close()
	data, err := json.Marshal(event)
	if err != nil {
		return err
	}
	if _, err := file.Write(append(data, '\n')); err != nil {
		return err
	}
	return nil
}

func (b *FileBus) List(limit int, topic string) []Event {
	return b.memory.List(limit, topic)
}
