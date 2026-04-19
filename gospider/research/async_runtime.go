package research

import (
	"sync"
	"time"

	asyncpkg "gospider/async"
)

type AsyncResearchResult struct {
	Seed       string                 `json:"seed"`
	Profile    SiteProfile            `json:"profile"`
	Extract    map[string]interface{} `json:"extract"`
	DurationMS float64                `json:"duration_ms"`
	Dataset    map[string]interface{} `json:"dataset,omitempty"`
	Error      string                 `json:"error,omitempty"`
}

type AsyncResearchConfig struct {
	MaxConcurrent  int     `json:"max_concurrent"`
	TimeoutSeconds float64 `json:"timeout_seconds"`
	EnableStreaming bool   `json:"enable_streaming"`
}

type AsyncRuntimeMetrics struct {
	MaxConcurrent    int     `json:"max_concurrent"`
	TasksStarted     int     `json:"tasks_started"`
	TasksCompleted   int     `json:"tasks_completed"`
	TasksFailed      int     `json:"tasks_failed"`
	CurrentInflight  int     `json:"current_inflight"`
	PeakInflight     int     `json:"peak_inflight"`
	AverageDurationMS float64 `json:"average_duration_ms"`
	MaxDurationMS    float64 `json:"max_duration_ms"`
	LastError        string  `json:"last_error"`

	totalDurationMS float64
}

type AsyncResearchRuntime struct {
	Config  AsyncResearchConfig
	runtime *asyncpkg.Runtime
	mu      sync.Mutex
	metrics AsyncRuntimeMetrics
}

func NewAsyncResearchRuntime(config *AsyncResearchConfig) *AsyncResearchRuntime {
	cfg := AsyncResearchConfig{
		MaxConcurrent:  5,
		TimeoutSeconds: 30,
	}
	if config != nil {
		if config.MaxConcurrent > 0 {
			cfg.MaxConcurrent = config.MaxConcurrent
		}
		if config.TimeoutSeconds > 0 {
			cfg.TimeoutSeconds = config.TimeoutSeconds
		}
		cfg.EnableStreaming = config.EnableStreaming
	}
	return &AsyncResearchRuntime{
		Config:  cfg,
		runtime: asyncpkg.NewRuntime(cfg.MaxConcurrent),
		metrics: AsyncRuntimeMetrics{MaxConcurrent: cfg.MaxConcurrent},
	}
}

func (r *AsyncResearchRuntime) RunSingle(job ResearchJob, content string) AsyncResearchResult {
	r.recordStart()
	started := time.Now()
	if delay := simulatedDelayMS(job); delay > 0 {
		time.Sleep(time.Duration(delay) * time.Millisecond)
	}
	resultMap, err := NewResearchRuntime().Run(job, content)
	durationMS := float64(time.Since(started).Milliseconds())
	if durationMS <= 0 {
		durationMS = 1
	}
	if err != nil {
		result := AsyncResearchResult{
			Seed:       firstSeed(job),
			DurationMS: durationMS,
			Error:      err.Error(),
		}
		r.recordFinish(durationMS, err.Error())
		return result
	}

	profile, _ := resultMap["profile"].(SiteProfile)
	extract, _ := resultMap["extract"].(map[string]interface{})
	dataset, _ := resultMap["dataset"].(map[string]interface{})
	result := AsyncResearchResult{
		Seed:       firstSeed(job),
		Profile:    profile,
		Extract:    extract,
		DurationMS: durationMS,
		Dataset:    dataset,
	}
	r.recordFinish(durationMS, "")
	return result
}

func (r *AsyncResearchRuntime) RunMultiple(jobs []ResearchJob, contents []string) []AsyncResearchResult {
	if len(contents) < len(jobs) {
		padded := make([]string, len(jobs))
		copy(padded, contents)
		contents = padded
	}
	results := make([]AsyncResearchResult, len(jobs))
	futures := make([]*asyncpkg.Future, len(jobs))
	for index, job := range jobs {
		jobCopy := job
		content := contents[index]
		futures[index] = r.runtime.Submit(func() (any, error) {
			result := r.RunSingle(jobCopy, content)
			return result, nil
		})
	}
	for index, future := range futures {
		value := future.Await()
		if value.Err != nil {
			results[index] = AsyncResearchResult{Seed: firstSeed(jobs[index]), Error: value.Err.Error()}
			continue
		}
		results[index] = value.Value.(AsyncResearchResult)
	}
	return results
}

func (r *AsyncResearchRuntime) RunStream(jobs []ResearchJob, contents []string) <-chan AsyncResearchResult {
	if len(contents) < len(jobs) {
		padded := make([]string, len(jobs))
		copy(padded, contents)
		contents = padded
	}
	stream := make(chan AsyncResearchResult, len(jobs))
	go func() {
		defer close(stream)
		results := make(chan AsyncResearchResult, len(jobs))
		for index, job := range jobs {
			jobCopy := job
			content := contents[index]
			r.runtime.Go(func() {
				results <- r.RunSingle(jobCopy, content)
			})
		}
		for range jobs {
			stream <- <-results
		}
	}()
	return stream
}

func (r *AsyncResearchRuntime) ResetMetrics() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.metrics = AsyncRuntimeMetrics{MaxConcurrent: r.Config.MaxConcurrent}
}

func (r *AsyncResearchRuntime) RunSoak(jobs []ResearchJob, contents []string, rounds int) map[string]interface{} {
	if rounds < 1 {
		rounds = 1
	}
	started := time.Now()
	r.ResetMetrics()
	allResults := make([]AsyncResearchResult, 0, len(jobs)*rounds)
	for i := 0; i < rounds; i++ {
		allResults = append(allResults, r.RunMultiple(jobs, contents)...)
	}
	failures := 0
	for _, result := range allResults {
		if result.Error != "" {
			failures++
		}
	}
	metrics := r.SnapshotMetrics()
	successes := len(allResults) - failures
	successRate := 0.0
	if len(allResults) > 0 {
		successRate = float64(successes) / float64(len(allResults))
	}
	return map[string]interface{}{
		"jobs":           len(jobs),
		"rounds":         rounds,
		"results":        len(allResults),
		"successes":      successes,
		"failures":       failures,
		"success_rate":   successRate,
		"duration_ms":    float64(time.Since(started).Milliseconds()),
		"peak_inflight":  metrics["peak_inflight"],
		"max_concurrent": r.Config.MaxConcurrent,
		"stable":         metrics["current_inflight"].(int) == 0 && failures == 0 && metrics["tasks_completed"].(int) == len(allResults),
	}
}

func (r *AsyncResearchRuntime) SnapshotMetrics() map[string]interface{} {
	r.mu.Lock()
	defer r.mu.Unlock()
	return map[string]interface{}{
		"max_concurrent":     r.metrics.MaxConcurrent,
		"tasks_started":      r.metrics.TasksStarted,
		"tasks_completed":    r.metrics.TasksCompleted,
		"tasks_failed":       r.metrics.TasksFailed,
		"current_inflight":   r.metrics.CurrentInflight,
		"peak_inflight":      r.metrics.PeakInflight,
		"average_duration_ms": r.metrics.AverageDurationMS,
		"max_duration_ms":    r.metrics.MaxDurationMS,
		"last_error":         r.metrics.LastError,
	}
}

func (r *AsyncResearchRuntime) recordStart() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.metrics.TasksStarted++
	r.metrics.CurrentInflight++
	if r.metrics.CurrentInflight > r.metrics.PeakInflight {
		r.metrics.PeakInflight = r.metrics.CurrentInflight
	}
}

func (r *AsyncResearchRuntime) recordFinish(durationMS float64, errText string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.metrics.TasksCompleted++
	if errText != "" {
		r.metrics.TasksFailed++
		r.metrics.LastError = errText
	}
	if r.metrics.CurrentInflight > 0 {
		r.metrics.CurrentInflight--
	}
	r.metrics.totalDurationMS += durationMS
	r.metrics.AverageDurationMS = r.metrics.totalDurationMS / float64(r.metrics.TasksCompleted)
	if durationMS > r.metrics.MaxDurationMS {
		r.metrics.MaxDurationMS = durationMS
	}
}

func firstSeed(job ResearchJob) string {
	if len(job.SeedURLs) == 0 {
		return ""
	}
	return job.SeedURLs[0]
}

func simulatedDelayMS(job ResearchJob) int {
	if job.Policy == nil {
		return 0
	}
	switch value := job.Policy["simulate_delay_ms"].(type) {
	case int:
		return value
	case float64:
		return int(value)
	default:
		return 0
	}
}
