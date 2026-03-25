package core

import (
	"net/http"
	"time"
)

// JobResult is the normalized result envelope emitted by runtimes.
type JobResult struct {
	JobName     string
	Runtime     Runtime
	State       TaskState
	URL         string
	StatusCode  int
	Headers     http.Header
	Body        []byte
	Text        string
	Duration    time.Duration
	StartedAt   time.Time
	FinishedAt  time.Time
	Error       string
	Artifacts   []string
	Metadata    map[string]interface{}
	MediaRecord []MediaArtifact
}

// MediaArtifact captures a downloaded or discovered media output.
type MediaArtifact struct {
	Type string
	URL  string
	Path string
}
