package storage

import (
	"path/filepath"
	"testing"
	"time"

	"gospider/events"
)

func TestFileResultStoreAppendsAndReads(t *testing.T) {
	path := filepath.Join(t.TempDir(), "results.jsonl")
	store := NewFileResultStore(path)
	if err := store.Put(ResultRecord{ID: "job-1", State: "succeeded", UpdatedAt: time.Now()}); err != nil {
		t.Fatalf("put failed: %v", err)
	}
	if err := store.Put(ResultRecord{ID: "job-2", State: "failed", UpdatedAt: time.Now()}); err != nil {
		t.Fatalf("put failed: %v", err)
	}
	list := store.List(0)
	if len(list) != 2 {
		t.Fatalf("expected 2 records, got %d", len(list))
	}
	if _, ok := store.Get("job-2"); !ok {
		t.Fatal("expected to read job-2")
	}
}

func TestFileEventStoreAppendsAndFilters(t *testing.T) {
	path := filepath.Join(t.TempDir(), "events.jsonl")
	store := NewFileEventStore(path)
	if err := store.Put(events.New(events.TopicTaskQueued, map[string]any{"task_id": "1"})); err != nil {
		t.Fatalf("put failed: %v", err)
	}
	if err := store.Put(events.New(events.TopicTaskResult, map[string]any{"task_id": "1"})); err != nil {
		t.Fatalf("put failed: %v", err)
	}
	list := store.List(10, events.TopicTaskResult)
	if len(list) != 1 {
		t.Fatalf("expected 1 filtered event, got %d", len(list))
	}
}
