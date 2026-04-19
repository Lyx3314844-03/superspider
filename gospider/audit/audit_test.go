package audit

import (
	"path/filepath"
	"testing"
	"time"
)

func TestAuditTrailsPersistAndReplayEvents(t *testing.T) {
	file := &FileAuditTrail{Path: filepath.Join(t.TempDir(), "audit.jsonl")}
	memory := &MemoryAuditTrail{}
	composite := NewCompositeAuditTrail(memory, file)

	event := AuditEvent{
		Timestamp: time.Now(),
		JobID:     "job-1",
		Type:      "step.started",
		Payload:   map[string]any{"step": "goto"},
	}
	if err := composite.Append(event); err != nil {
		t.Fatalf("append failed: %v", err)
	}

	if len(memory.Events()) != 1 {
		t.Fatalf("expected memory replay, got %#v", memory.Events())
	}
	if len(file.Events()) != 1 {
		t.Fatalf("expected file replay, got %#v", file.Events())
	}
}
