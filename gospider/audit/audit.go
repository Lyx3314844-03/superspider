package audit

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type AuditEvent struct {
	Timestamp time.Time      `json:"timestamp"`
	JobID     string         `json:"job_id,omitempty"`
	StepID    string         `json:"step_id,omitempty"`
	Type      string         `json:"type"`
	Payload   map[string]any `json:"payload,omitempty"`
}

type AuditTrail interface {
	Append(event AuditEvent) error
	Events() []AuditEvent
}

type MemoryAuditTrail struct {
	mu     sync.RWMutex
	events []AuditEvent
}

func (t *MemoryAuditTrail) Append(event AuditEvent) error {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.events = append(t.events, event)
	return nil
}

func (t *MemoryAuditTrail) Events() []AuditEvent {
	t.mu.RLock()
	defer t.mu.RUnlock()
	events := make([]AuditEvent, len(t.events))
	copy(events, t.events)
	return events
}

type FileAuditTrail struct {
	Path string
	mu   sync.Mutex
}

func (t *FileAuditTrail) Append(event AuditEvent) error {
	if err := os.MkdirAll(filepath.Dir(t.Path), 0o755); err != nil {
		return err
	}
	data, err := json.Marshal(event)
	if err != nil {
		return err
	}
	t.mu.Lock()
	defer t.mu.Unlock()
	handle, err := os.OpenFile(t.Path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
	if err != nil {
		return err
	}
	defer handle.Close()
	if _, err := handle.Write(append(data, '\n')); err != nil {
		return err
	}
	return handle.Sync()
}

func (t *FileAuditTrail) Events() []AuditEvent {
	data, err := os.ReadFile(t.Path)
	if err != nil {
		return nil
	}
	lines := bytesToLines(data)
	events := make([]AuditEvent, 0, len(lines))
	for _, line := range lines {
		var event AuditEvent
		if err := json.Unmarshal(line, &event); err == nil {
			events = append(events, event)
		}
	}
	return events
}

type CompositeAuditTrail struct {
	trails []AuditTrail
}

func NewCompositeAuditTrail(trails ...AuditTrail) *CompositeAuditTrail {
	return &CompositeAuditTrail{trails: trails}
}

func (t *CompositeAuditTrail) Append(event AuditEvent) error {
	for _, trail := range t.trails {
		if trail == nil {
			continue
		}
		if err := trail.Append(event); err != nil {
			return err
		}
	}
	return nil
}

func (t *CompositeAuditTrail) Events() []AuditEvent {
	var all []AuditEvent
	for _, trail := range t.trails {
		if trail == nil {
			continue
		}
		all = append(all, trail.Events()...)
	}
	return all
}

func bytesToLines(data []byte) [][]byte {
	lines := make([][]byte, 0)
	start := 0
	for index, b := range data {
		if b == '\n' {
			if index > start {
				lines = append(lines, data[start:index])
			}
			start = index + 1
		}
	}
	if start < len(data) {
		lines = append(lines, data[start:])
	}
	return lines
}
