// gospider v1 - 统一执行引擎
// 基于设计文档：docs/superpowers/specs/2026-03-22-gospider-v1-design.md

package core

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"
)

// ============================================================================
// v1.0 统一执行引擎
// ============================================================================

// JobRunner 任务执行器
type JobRunner struct {
	config   *Config
	service  *JobService
	executor Executor
	mu       sync.RWMutex
	running  map[string]bool
	stats    *EngineStats
}

// EngineStats 引擎统计信息
type EngineStats struct {
	mu           sync.RWMutex
	TotalJobs    int
	Running      int
	Succeeded    int
	Failed       int
	StartTime    time.Time
	LastJobStart time.Time
}

// NewJobRunner 创建任务执行器
func NewJobRunner(config *Config) *JobRunner {
	if config == nil {
		config = DefaultConfig()
	}

	return &JobRunner{
		config:  config,
		service: NewJobService(),
		running: make(map[string]bool),
		stats: &EngineStats{
			StartTime: time.Now(),
		},
	}
}

// SetExecutor 设置执行器
func (r *JobRunner) SetExecutor(executor Executor) {
	r.executor = executor
}

// Submit 提交任务
func (r *JobRunner) Submit(job *JobSpec) (JobSummary, error) {
	if job == nil {
		return JobSummary{}, NewConfigError("job is required")
	}

	if err := job.Validate(); err != nil {
		return JobSummary{}, WrapError(err, ErrConfigValidation, "job validation failed")
	}

	// 合并配置
	job = r.config.MergeConfig(job)

	// 提交到服务
	summary, err := r.service.Submit(*job)
	if err != nil {
		return JobSummary{}, WrapError(err, ErrConfigInvalid, "failed to submit job")
	}

	r.stats.mu.Lock()
	r.stats.TotalJobs++
	r.stats.mu.Unlock()

	return summary, nil
}

// Run 执行任务
func (r *JobRunner) Run(ctx context.Context, job *JobSpec) (*JobResult, error) {
	if job == nil {
		return nil, NewConfigError("job is required")
	}

	if err := job.Validate(); err != nil {
		return nil, WrapError(err, ErrConfigValidation, "job validation failed")
	}

	// 合并配置
	job = r.config.MergeConfig(job)

	// 更新统计
	r.stats.mu.Lock()
	r.stats.TotalJobs++
	r.stats.LastJobStart = time.Now()
	r.stats.Running++
	r.stats.mu.Unlock()

	r.mu.Lock()
	r.running[job.Name] = true
	r.mu.Unlock()

	defer func() {
		r.mu.Lock()
		delete(r.running, job.Name)
		r.mu.Unlock()

		r.stats.mu.Lock()
		r.stats.Running--
		r.stats.mu.Unlock()
	}()

	// 检查执行器
	if r.executor == nil {
		return nil, NewInfraError("executor not configured", nil)
	}

	// 创建执行上下文
	execCtx, cancel := context.WithTimeout(ctx, job.Resources.Timeout)
	defer cancel()

	// 执行任务
	result, err := r.executor.Execute(execCtx, *job)
	if err != nil {
		r.stats.mu.Lock()
		r.stats.Failed++
		r.stats.mu.Unlock()

		return nil, WrapWithJob(err, ErrRuntimeHTTP, "execution failed", job)
	}

	// 更新统计
	r.stats.mu.Lock()
	r.stats.Succeeded++
	r.stats.mu.Unlock()

	return result, nil
}

// RunBatch 批量执行任务
func (r *JobRunner) RunBatch(ctx context.Context, jobs []*JobSpec, concurrency int) ([]*JobResult, error) {
	if len(jobs) == 0 {
		return nil, nil
	}

	if concurrency <= 0 {
		concurrency = r.config.Concurrency
	}

	results := make([]*JobResult, 0, len(jobs))
	errors := make([]error, 0)

	var wg sync.WaitGroup
	sem := make(chan struct{}, concurrency)
	mu := sync.Mutex{}

	for i, job := range jobs {
		wg.Add(1)
		sem <- struct{}{}

		go func(idx int, j *JobSpec) {
			defer wg.Done()
			defer func() { <-sem }()

			result, err := r.Run(ctx, j)
			mu.Lock()
			defer mu.Unlock()

			if err != nil {
				errors = append(errors, err)
			} else {
				results = append(results, result)
			}
		}(i, job)
	}

	wg.Wait()

	if len(errors) > 0 {
		return results, fmt.Errorf("batch execution completed with %d errors", len(errors))
	}

	return results, nil
}

// GetStats 获取统计信息
func (r *JobRunner) GetStats() *EngineStats {
	r.stats.mu.RLock()
	defer r.stats.mu.RUnlock()

	return &EngineStats{
		TotalJobs:    r.stats.TotalJobs,
		Running:      r.stats.Running,
		Succeeded:    r.stats.Succeeded,
		Failed:       r.stats.Failed,
		StartTime:    r.stats.StartTime,
		LastJobStart: r.stats.LastJobStart,
	}
}

// IsRunning 检查任务是否运行中
func (r *JobRunner) IsRunning(jobName string) bool {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.running[jobName]
}

// Cancel 取消任务
func (r *JobRunner) Cancel(jobName string) error {
	// TODO: 实现取消逻辑
	return nil
}

// ============================================================================
// ExecutionContext 执行上下文
// ============================================================================

// ExecutionContext 任务执行上下文
type ExecutionContext struct {
	Job       *JobSpec
	Context   context.Context
	State     TaskState
	Result    *JobResult
	Errors    *ErrorCollector
	Metadata  map[string]interface{}
	mu        sync.RWMutex
}

// NewExecutionContext 创建执行上下文
func NewExecutionContext(ctx context.Context, job *JobSpec) *ExecutionContext {
	return &ExecutionContext{
		Job:      job,
		Context:  ctx,
		State:    StateCreated,
		Metadata: make(map[string]interface{}),
		Errors:   NewErrorCollector(),
	}
}

// SetState 设置状态
func (c *ExecutionContext) SetState(state TaskState) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if err := c.State.CanTransitionTo(state); err != nil {
		return err
	}

	c.State = state
	return nil
}

// GetState 获取状态
func (c *ExecutionContext) GetState() TaskState {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.State
}

// SetResult 设置结果
func (c *ExecutionContext) SetResult(result *JobResult) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.Result = result
}

// GetResult 获取结果
func (c *ExecutionContext) GetResult() *JobResult {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.Result
}

// AddError 添加错误
func (c *ExecutionContext) AddError(err *JobError) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.Errors.Add(err)
}

// HasErrors 是否有错误
func (c *ExecutionContext) HasErrors() bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.Errors.HasErrors()
}

// SetMetadata 设置元数据
func (c *ExecutionContext) SetMetadata(key string, value interface{}) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.Metadata[key] = value
}

// GetMetadata 获取元数据
func (c *ExecutionContext) GetMetadata(key string) interface{} {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.Metadata[key]
}

// ============================================================================
// SpiderEngine 爬虫引擎 (高层 API)
// ============================================================================

// SpiderEngine 爬虫引擎
type SpiderEngine struct {
	name    string
	config  *Config
	runner  *JobRunner
	mu      sync.RWMutex
	running bool
}

// NewSpiderEngine 创建爬虫引擎
func NewSpiderEngine(name string, config *Config) *SpiderEngine {
	if config == nil {
		config = DefaultConfig()
	}

	return &SpiderEngine{
		name:   name,
		config: config,
		runner: NewJobRunner(config),
	}
}

// WithExecutor 设置执行器
func (e *SpiderEngine) WithExecutor(executor Executor) *SpiderEngine {
	e.runner.SetExecutor(executor)
	return e
}

// Submit 提交任务
func (e *SpiderEngine) Submit(job *JobSpec) (JobSummary, error) {
	return e.runner.Submit(job)
}

// Run 执行任务
func (e *SpiderEngine) Run(ctx context.Context, job *JobSpec) (*JobResult, error) {
	return e.runner.Run(ctx, job)
}

// RunHTTP 执行 HTTP 任务 (便捷方法)
func (e *SpiderEngine) RunHTTP(ctx context.Context, url string) (*JobResult, error) {
	job := &JobSpec{
		Name:     url,
		Runtime:  RuntimeHTTP,
		Target:   TargetSpec{URL: url, Method: "GET"},
		Output:   OutputSpec{Format: "json"},
		Schedule: ScheduleSpec{Mode: "once"},
	}

	return e.Run(ctx, job)
}

// RunBrowser 执行浏览器任务 (便捷方法)
func (e *SpiderEngine) RunBrowser(ctx context.Context, url string, actions []ActionSpec) (*JobResult, error) {
	job := &JobSpec{
		Name:     url,
		Runtime:  RuntimeBrowser,
		Target:   TargetSpec{URL: url, Method: "GET"},
		Actions:  actions,
		Output:   OutputSpec{Format: "json"},
		Schedule: ScheduleSpec{Mode: "once"},
		Resources: ResourceSpec{
			Browser: BrowserResourceSpec{
				Headless: e.config.Browser.Headless,
			},
		},
	}

	return e.Run(ctx, job)
}

// Start 启动引擎
func (e *SpiderEngine) Start() error {
	e.mu.Lock()
	defer e.mu.Unlock()

	if e.running {
		return fmt.Errorf("engine is already running")
	}

	e.running = true
	log.Printf("SpiderEngine %s started", e.name)
	return nil
}

// Stop 停止引擎
func (e *SpiderEngine) Stop() error {
	e.mu.Lock()
	defer e.mu.Unlock()

	e.running = false
	log.Printf("SpiderEngine %s stopped", e.name)
	return nil
}

// IsRunning 是否运行中
func (e *SpiderEngine) IsRunning() bool {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.running
}

// GetStats 获取统计信息
func (e *SpiderEngine) GetStats() *EngineStats {
	return e.runner.GetStats()
}

// GetConfig 获取配置
func (e *SpiderEngine) GetConfig() *Config {
	return e.config
}

// ============================================================================
// 使用示例
// ============================================================================

// ExampleSpiderEngine 使用示例
func ExampleSpiderEngine() {
	// 创建引擎
	config := DefaultConfig()
	config.Name = "example_engine"
	config.Concurrency = 5

	engine := NewSpiderEngine("MySpider", config)

	// 创建执行器 (这里使用 mock)
	executor := &MockExecutor{}
	engine.WithExecutor(executor)

	// 启动引擎
	engine.Start()
	defer engine.Stop()

	// 创建任务
	job := &JobSpec{
		Name:     "example_job",
		Runtime:  RuntimeHTTP,
		Target:   TargetSpec{URL: "https://example.com"},
		Extract: []ExtractSpec{
			{Field: "title", Type: "css", Expr: "title"},
		},
		Output: OutputSpec{Format: "json"},
	}

	// 执行任务
	ctx := context.Background()
	result, err := engine.Run(ctx, job)
	if err != nil {
		log.Printf("执行失败：%v", err)
		return
	}

	log.Printf("执行成功：%s", result.URL)
}

// MockExecutor Mock 执行器 (用于测试)
type MockExecutor struct{}

func (m *MockExecutor) Execute(ctx context.Context, job JobSpec) (*JobResult, error) {
	return &JobResult{
		JobName:   job.Name,
		Runtime:   job.Runtime,
		State:     StateSucceeded,
		URL:       job.Target.URL,
		Text:      "Mock response",
		StartedAt: time.Now(),
		FinishedAt: time.Now(),
	}, nil
}
