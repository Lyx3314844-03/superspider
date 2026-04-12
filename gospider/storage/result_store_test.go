package storage

import "testing"

func TestMemoryResultStorePutGetAndList(t *testing.T) {
	store := NewMemoryResultStore()

	if err := store.Put(ResultRecord{
		ID:      "job-1",
		State:   "succeeded",
		Runtime: "http",
	}); err != nil {
		t.Fatalf("unexpected put error: %v", err)
	}
	if err := store.Put(ResultRecord{
		ID:      "job-2",
		State:   "failed",
		Runtime: "browser",
	}); err != nil {
		t.Fatalf("unexpected put error: %v", err)
	}

	record, ok := store.Get("job-1")
	if !ok {
		t.Fatal("expected stored record")
	}
	if record.State != "succeeded" {
		t.Fatalf("expected succeeded, got %s", record.State)
	}

	list := store.List(1)
	if len(list) != 1 {
		t.Fatalf("expected limited list of 1, got %d", len(list))
	}
}
