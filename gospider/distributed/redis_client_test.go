package distributed

import (
	"encoding/json"
	"testing"

	"gospider/core"
)

func TestTaskStatusNormalizesLegacyValues(t *testing.T) {
	var status TaskStatus
	if err := json.Unmarshal([]byte(`"completed"`), &status); err != nil {
		t.Fatalf("unexpected unmarshal error: %v", err)
	}
	if status.Core() != core.StateSucceeded {
		t.Fatalf("expected completed to normalize to succeeded, got %s", status.Core())
	}

	data, err := json.Marshal(TaskPending)
	if err != nil {
		t.Fatalf("unexpected marshal error: %v", err)
	}
	if string(data) != `"queued"` {
		t.Fatalf("expected queued JSON, got %s", string(data))
	}
}

func TestTaskRuntimeInfersFromNormalizedJob(t *testing.T) {
	task := &CrawlTask{
		Type: "video",
		Job: &core.JobSpec{
			Runtime: core.RuntimeAI,
		},
	}

	if runtime := taskRuntime(task); runtime != core.RuntimeAI {
		t.Fatalf("expected runtime %s, got %s", core.RuntimeAI, runtime)
	}
}
