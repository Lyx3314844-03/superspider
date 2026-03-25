package httpruntime

import (
	"bytes"
	"context"
	"fmt"
	"net/http"
	"time"

	"gospider/core"
	"gospider/downloader"
)

// Runtime executes normalized HTTP jobs and returns normalized job results.
type Runtime struct {
	downloader *downloader.HTTPDownloader
}

// NewRuntime creates the shared HTTP runtime.
func NewRuntime() *Runtime {
	return &Runtime{
		downloader: downloader.NewDownloader(),
	}
}

// Execute runs a normalized HTTP job through the shared downloader path.
func (r *Runtime) Execute(_ context.Context, job core.JobSpec) (*core.JobResult, error) {
	if err := job.Validate(); err != nil {
		return nil, err
	}
	if job.Runtime != core.RuntimeHTTP {
		return nil, fmt.Errorf("http runtime cannot execute %q jobs", job.Runtime)
	}

	startedAt := time.Now()
	resp := r.downloader.Download(&downloader.Request{
		URL:     job.Target.URL,
		Method:  coalesceMethod(job.Target.Method),
		Headers: cloneHeaders(job.Target.Headers),
		Body:    bytes.NewReader([]byte(job.Target.Body)),
	})

	state := core.StateSucceeded
	errText := ""
	if resp.Error != nil {
		state = core.StateFailed
		errText = resp.Error.Error()
	}

	result := &core.JobResult{
		JobName:    job.Name,
		Runtime:    core.RuntimeHTTP,
		State:      state,
		URL:        resp.URL,
		StatusCode: resp.StatusCode,
		Headers:    resp.Headers,
		Body:       resp.Body,
		Text:       resp.Text,
		Duration:   resp.Duration,
		StartedAt:  startedAt,
		FinishedAt: startedAt.Add(resp.Duration),
		Error:      errText,
		Metadata:   make(map[string]interface{}),
	}

	if resp.Error != nil {
		return result, resp.Error
	}
	return result, nil
}

func coalesceMethod(method string) string {
	if method == "" {
		return http.MethodGet
	}
	return method
}

func cloneHeaders(headers map[string]string) map[string]string {
	if headers == nil {
		return map[string]string{}
	}
	cloned := make(map[string]string, len(headers))
	for k, v := range headers {
		cloned[k] = v
	}
	return cloned
}
