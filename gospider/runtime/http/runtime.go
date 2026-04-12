package httpruntime

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"gospider/core"
	"gospider/downloader"
	"gospider/graph"
)

// Runtime executes normalized HTTP jobs and returns normalized job results.
type Runtime struct{}

// NewRuntime creates the shared HTTP runtime.
func NewRuntime() *Runtime {
	return &Runtime{}
}

// Execute runs a normalized HTTP job through the shared downloader path.
func (r *Runtime) Execute(_ context.Context, job core.JobSpec) (*core.JobResult, error) {
	if err := job.Validate(); err != nil {
		return nil, err
	}
	if job.Runtime != core.RuntimeHTTP {
		return nil, fmt.Errorf("http runtime cannot execute %q jobs", job.Runtime)
	}

	method := coalesceMethod(job.Target.Method)
	headers := cloneHeaders(job.Target.Headers)
	userAgent := resolveUserAgent(headers)
	headers["User-Agent"] = userAgent
	if rateLimitPerSec := resolveRateLimit(job); rateLimitPerSec > 0 {
		time.Sleep(time.Duration(float64(time.Second) / rateLimitPerSec))
	}
	if err := enforceRobotsPolicy(job, userAgent); err != nil {
		result := core.NewJobResult(job, core.StateFailed)
		result.StatusCode = 403
		result.Error = err.Error()
		result.Metadata["policy"] = "respect_robots_txt"
		result.FinishedAt = time.Now()
		result.Finalize()
		return result, err
	}

	startedAt := time.Now()
	maxAttempts := resolveMaxAttempts(job)
	dl := downloader.NewDownloader()
	var lastResp *downloader.Response
	for attempt := 0; attempt < maxAttempts; attempt++ {
		lastResp = dl.Download(&downloader.Request{
			URL:     job.Target.URL,
			Method:  method,
			Headers: headers,
			Body:    bytes.NewReader([]byte(job.Target.Body)),
		})
		if !shouldRetry(lastResp, attempt, maxAttempts) {
			break
		}
		time.Sleep(retryDelay(attempt, retryAfterHeader(lastResp)))
	}

	resp := lastResp
	if resp == nil {
		resp = &downloader.Response{
			URL:      job.Target.URL,
			Error:    fmt.Errorf("http runtime returned no response"),
			Duration: 0,
		}
	}

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
	}
	result.EnsureEnvelope()
	extracted, extractErr := extractPayload(job, result.Text)
	if extractErr != nil {
		result.State = core.StateFailed
		result.Error = extractErr.Error()
		result.FinishedAt = time.Now()
		result.Finalize()
		return result, extractErr
	}
	for field, value := range extracted {
		result.SetExtractField(field, value)
	}
	attachGraphArtifact(job, result)
	result.Finalize()

	if resp.Error != nil {
		return result, resp.Error
	}
	return result, nil
}

func attachGraphArtifact(job core.JobSpec, result *core.JobResult) {
	if result == nil || strings.TrimSpace(result.Text) == "" {
		return
	}
	lowerContentType := strings.ToLower(result.Headers.Get("Content-Type"))
	if !strings.Contains(lowerContentType, "html") && !strings.Contains(strings.ToLower(result.Text), "<html") {
		return
	}

	builder := graph.NewBuilder()
	if err := builder.BuildFromHTML(result.Text); err != nil {
		return
	}

	path := graphArtifactPath(job)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return
	}
	payload := map[string]interface{}{
		"root_id": builder.RootID,
		"nodes":   builder.Nodes,
		"edges":   builder.Edges,
		"stats":   builder.Stats(),
	}
	encoded, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return
	}
	if err := os.WriteFile(path, encoded, 0o644); err != nil {
		return
	}

	result.SetArtifact("graph", core.ArtifactRef{
		Kind: "graph",
		Path: path,
		Metadata: map[string]interface{}{
			"root_id": builder.RootID,
			"stats":   intMapToAnyMap(builder.Stats()),
		},
	})
}

func graphArtifactPath(job core.JobSpec) string {
	baseDir := strings.TrimSpace(job.Output.Directory)
	if baseDir == "" {
		baseDir = filepath.Join("artifacts", "runtime", "graphs")
	}
	name := strings.TrimSpace(job.Name)
	if name == "" {
		name = "http-job"
	}
	safe := strings.NewReplacer("\\", "-", "/", "-", ":", "-", " ", "-").Replace(name)
	return filepath.Join(baseDir, safe+"-graph.json")
}

func intMapToAnyMap(source map[string]int) map[string]interface{} {
	result := make(map[string]interface{}, len(source))
	for key, value := range source {
		result[key] = value
	}
	return result
}

func enforceRobotsPolicy(job core.JobSpec, userAgent string) error {
	if !job.Policy.RespectRobotsTxt {
		return nil
	}
	checker := core.NewRobotsChecker(userAgent, time.Hour)
	if !checker.IsAllowed(job.Target.URL, userAgent) {
		return fmt.Errorf("robots.txt forbids %s", job.Target.URL)
	}
	if delay := checker.GetCrawlDelay(job.Target.URL); delay > 0 {
		time.Sleep(time.Duration(delay * float64(time.Second)))
	}
	return nil
}

func resolveUserAgent(headers map[string]string) string {
	if ua, ok := headers["User-Agent"]; ok && ua != "" {
		return ua
	}
	return "gospider/2.0"
}

func resolveRateLimit(job core.JobSpec) float64 {
	if job.Resources.RateLimitPerSec > 0 {
		return job.Resources.RateLimitPerSec
	}
	if job.Resources.RateLimit.Enabled {
		if job.Resources.RateLimit.Delay > 0 {
			return 1 / job.Resources.RateLimit.Delay.Seconds()
		}
		if job.Resources.RateLimit.Requests > 0 && job.Resources.RateLimit.Interval > 0 {
			return float64(job.Resources.RateLimit.Requests) / job.Resources.RateLimit.Interval.Seconds()
		}
	}
	return 0
}

func resolveMaxAttempts(job core.JobSpec) int {
	retries := 0
	if job.Resources.Retries > retries {
		retries = job.Resources.Retries
	}
	if job.Target.Retries > retries {
		retries = job.Target.Retries
	}
	// 至少执行一次；retries 表示额外重试次数
	return retries + 1
}

func shouldRetry(resp *downloader.Response, attempt, maxAttempts int) bool {
	if resp == nil || attempt >= maxAttempts-1 {
		return false
	}
	if resp.Error != nil {
		return true
	}
	switch resp.StatusCode {
	case 429, 500, 502, 503, 504:
		return true
	default:
		return false
	}
}

func retryAfterHeader(resp *downloader.Response) string {
	if resp == nil || resp.Headers == nil {
		return ""
	}
	return resp.Headers.Get("Retry-After")
}

func retryDelay(attempt int, retryAfter string) time.Duration {
	base := 500 * time.Millisecond
	delay := base * time.Duration(1<<attempt)
	if delay > 10*time.Second {
		delay = 10 * time.Second
	}
	if retryAfterDelay := parseRetryAfter(retryAfter); retryAfterDelay > delay {
		delay = retryAfterDelay
	}
	return delay
}

func parseRetryAfter(raw string) time.Duration {
	value := strings.TrimSpace(raw)
	if value == "" {
		return 0
	}
	if seconds, err := strconv.Atoi(value); err == nil && seconds >= 0 {
		return time.Duration(seconds) * time.Second
	}
	if ts, err := http.ParseTime(value); err == nil {
		if delta := time.Until(ts); delta > 0 {
			return delta
		}
	}
	return 0
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
