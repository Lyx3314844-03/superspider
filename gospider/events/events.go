package events

import (
	"time"
)

const (
	TopicTaskCreated   = "task:created"
	TopicTaskQueued    = "task:queued"
	TopicTaskRunning   = "task:running"
	TopicTaskSucceeded = "task:succeeded"
	TopicTaskFailed    = "task:failed"
	TopicTaskCancelled = "task:cancelled"
	TopicTaskDeleted   = "task:deleted"
	TopicTaskResult    = "task:result"
)

// Event is the normalized event envelope emitted by gospider control surfaces.
type Event struct {
	Topic     string      `json:"topic"`
	Timestamp time.Time   `json:"timestamp"`
	Payload   interface{} `json:"payload"`
}

// TaskLifecyclePayload is emitted on task state changes.
type TaskLifecyclePayload struct {
	TaskID    string    `json:"task_id"`
	State     string    `json:"state"`
	Runtime   string    `json:"runtime,omitempty"`
	URL       string    `json:"url,omitempty"`
	WorkerID  string    `json:"worker_id,omitempty"`
	UpdatedAt time.Time `json:"updated_at"`
	HasResult bool      `json:"has_result"`
}

// TaskResultPayload is emitted when a task produces a normalized result envelope.
type TaskResultPayload struct {
	TaskID       string                 `json:"task_id"`
	State        string                 `json:"state"`
	Runtime      string                 `json:"runtime,omitempty"`
	URL          string                 `json:"url,omitempty"`
	StatusCode   int                    `json:"status_code,omitempty"`
	Artifacts    []string               `json:"artifacts,omitempty"`
	ArtifactRefs map[string]ArtifactRef `json:"artifact_refs,omitempty"`
	UpdatedAt    time.Time              `json:"updated_at"`
}

// ArtifactRef is the event-safe artifact descriptor.
type ArtifactRef struct {
	Kind     string                 `json:"kind,omitempty"`
	URI      string                 `json:"uri,omitempty"`
	Path     string                 `json:"path,omitempty"`
	Size     int64                  `json:"size,omitempty"`
	Metadata map[string]interface{} `json:"metadata,omitempty"`
}

// TaskDeletedPayload is emitted when a task is deleted from the control plane.
type TaskDeletedPayload struct {
	TaskID    string    `json:"task_id"`
	DeletedAt time.Time `json:"deleted_at"`
}

// New creates a normalized event envelope.
func New(topic string, payload interface{}) Event {
	return Event{
		Topic:     topic,
		Timestamp: time.Now(),
		Payload:   payload,
	}
}
