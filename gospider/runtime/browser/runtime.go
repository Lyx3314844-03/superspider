package browserruntime

import (
	"context"
	"fmt"
	"time"

	"gospider/core"
)

// Executor abstracts the browser work so tests can inject a stub.
type Executor func(ctx context.Context, job core.JobSpec) (string, error)

// Runtime executes normalized browser jobs and returns normalized job results.
type Runtime struct {
	executor Executor
}

// NewRuntime creates a browser runtime with an optional executor override.
func NewRuntime(executor Executor) *Runtime {
	if executor == nil {
		executor = func(ctx context.Context, job core.JobSpec) (string, error) {
			return "", fmt.Errorf("no browser executor configured for %s", job.Target.URL)
		}
	}
	return &Runtime{executor: executor}
}

// Execute runs a browser job through the configured executor.
func (r *Runtime) Execute(ctx context.Context, job core.JobSpec) (*core.JobResult, error) {
	if err := job.Validate(); err != nil {
		return nil, err
	}
	if job.Runtime != core.RuntimeBrowser {
		return nil, fmt.Errorf("browser runtime cannot execute %q jobs", job.Runtime)
	}

	startedAt := time.Now()
	html, err := r.executor(ctx, job)
	finishedAt := time.Now()
	state := core.StateSucceeded
	errText := ""
	if err != nil {
		state = core.StateFailed
		errText = err.Error()
	}

	result := &core.JobResult{
		JobName:    job.Name,
		Runtime:    core.RuntimeBrowser,
		State:      state,
		URL:        job.Target.URL,
		Body:       []byte(html),
		Text:       html,
		StartedAt:  startedAt,
		FinishedAt: finishedAt,
		Duration:   finishedAt.Sub(startedAt),
		Error:      errText,
		Metadata:   map[string]interface{}{},
	}
	if err != nil {
		return result, err
	}
	return result, nil
}
