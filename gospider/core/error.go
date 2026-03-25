// gospider v1 - 统一错误模型
// 基于设计文档：docs/superpowers/specs/2026-03-22-gospider-v1-design.md

package core

import (
	"encoding/json"
	"fmt"
	"time"
)

// ============================================================================
// v1.0 统一错误模型
// ============================================================================

// ErrorCode 错误代码
type ErrorCode string

const (
	// 配置错误
	ErrConfigInvalid     ErrorCode = "CONFIG_INVALID"
	ErrConfigMissing     ErrorCode = "CONFIG_MISSING"
	ErrConfigType        ErrorCode = "CONFIG_TYPE"
	ErrConfigValidation  ErrorCode = "CONFIG_VALIDATION"

	// 运行时错误
	ErrRuntimeHTTP       ErrorCode = "RUNTIME_HTTP"
	ErrRuntimeBrowser    ErrorCode = "RUNTIME_BROWSER"
	ErrRuntimeTimeout    ErrorCode = "RUNTIME_TIMEOUT"
	ErrRuntimeCancelled  ErrorCode = "RUNTIME_CANCELLED"

	// 提取错误
	ErrExtractNotFound     ErrorCode = "EXTRACT_NOT_FOUND"
	ErrExtractParse        ErrorCode = "EXTRACT_PARSE"
	ErrExtractType         ErrorCode = "EXTRACT_TYPE"

	// 输出错误
	ErrOutputWrite       ErrorCode = "OUTPUT_WRITE"
	ErrOutputFormat      ErrorCode = "OUTPUT_FORMAT"
	ErrOutputPath        ErrorCode = "OUTPUT_PATH"

	// 基础设施错误
	ErrInfraNetwork      ErrorCode = "INFRA_NETWORK"
	ErrInfraStorage      ErrorCode = "INFRA_STORAGE"
	ErrInfraQueue        ErrorCode = "INFRA_QUEUE"
	ErrInfraWorker       ErrorCode = "INFRA_WORKER"

	// 用户代码错误
	ErrUserCode          ErrorCode = "USER_CODE"
	ErrUserCodePanic     ErrorCode = "USER_CODE_PANIC"
)

// ErrorStage 错误发生的阶段
type ErrorStage string

const (
	StageInit       ErrorStage = "init"
	StageValidate   ErrorStage = "validate"
	StageQueue      ErrorStage = "queue"
	StageSchedule   ErrorStage = "schedule"
	StageExecute    ErrorStage = "execute"
	StageExtract    ErrorStage = "extract"
	StageOutput     ErrorStage = "output"
	StageCleanup    ErrorStage = "cleanup"
)

// JobError 统一的错误结构
type JobError struct {
	// 错误信息
	Code     ErrorCode   `json:"code"`              // 错误代码
	Category string      `json:"category"`          // 错误分类
	Stage    ErrorStage  `json:"stage"`             // 发生阶段
	Message  string      `json:"message"`           // 错误消息

	// 上下文信息
	JobID    string      `json:"job_id,omitempty"`  // 任务 ID
	JobName  string      `json:"job_name,omitempty"`// 任务名称
	Runtime  Runtime     `json:"runtime,omitempty"` // 运行时类型
	URL      string      `json:"url,omitempty"`     // 相关 URL

	// 错误详情
	Cause    error       `json:"-"`                 // 原始错误
	Retryable bool       `json:"retryable"`         // 是否可重试
	Timestamp time.Time  `json:"timestamp"`         // 时间戳

	// 堆栈信息 (可选)
	Stack    []string    `json:"stack,omitempty"`   // 调用堆栈
}

// Error 实现 error 接口
func (e *JobError) Error() string {
	if e.Cause != nil {
		return fmt.Sprintf("[%s] %s: %v", e.Code, e.Message, e.Cause)
	}
	return fmt.Sprintf("[%s] %s", e.Code, e.Message)
}

// Unwrap 实现 errors.Unwrap 接口
func (e *JobError) Unwrap() error {
	return e.Cause
}

// WithJobID 设置任务 ID
func (e *JobError) WithJobID(jobID string) *JobError {
	e.JobID = jobID
	return e
}

// WithJobName 设置任务名称
func (e *JobError) WithJobName(jobName string) *JobError {
	e.JobName = jobName
	return e
}

// WithRuntime 设置运行时类型
func (e *JobError) WithRuntime(runtime Runtime) *JobError {
	e.Runtime = runtime
	return e
}

// WithURL 设置相关 URL
func (e *JobError) WithURL(url string) *JobError {
	e.URL = url
	return e
}

// WithStage 设置阶段
func (e *JobError) WithStage(stage ErrorStage) *JobError {
	e.Stage = stage
	return e
}

// WithRetryable 设置是否可重试
func (e *JobError) WithRetryable(retryable bool) *JobError {
	e.Retryable = retryable
	return e
}

// WithCause 设置原始错误
func (e *JobError) WithCause(cause error) *JobError {
	e.Cause = cause
	return e
}

// WithStack 设置调用堆栈
func (e *JobError) WithStack(stack []string) *JobError {
	e.Stack = stack
	return e
}

// MarshalJSON 自定义 JSON 序列化
func (e *JobError) MarshalJSON() ([]byte, error) {
	type Alias JobError
	causeMsg := ""
	if e.Cause != nil {
		causeMsg = e.Cause.Error()
	}
	return json.Marshal(&struct {
		*Alias
		Cause string `json:"cause,omitempty"`
	}{
		Alias: (*Alias)(e),
		Cause: causeMsg,
	})
}

// ============================================================================
// 错误构建器
// ============================================================================

// NewError 创建新的 JobError
func NewError(code ErrorCode, message string) *JobError {
	return &JobError{
		Code:      code,
		Message:   message,
		Timestamp: time.Now(),
		Retryable: isRetryable(code),
	}
}

// NewConfigError 创建配置错误
func NewConfigError(message string) *JobError {
	return &JobError{
		Code:      ErrConfigInvalid,
		Category:  "config",
		Message:   message,
		Stage:     StageValidate,
		Timestamp: time.Now(),
		Retryable: false,
	}
}

// NewRuntimeError 创建运行时错误
func NewRuntimeError(message string, cause error) *JobError {
	return &JobError{
		Code:      ErrRuntimeHTTP,
		Category:  "runtime",
		Message:   message,
		Stage:     StageExecute,
		Cause:     cause,
		Timestamp: time.Now(),
		Retryable: true,
	}
}

// NewExtractError 创建提取错误
func NewExtractError(message string, cause error) *JobError {
	return &JobError{
		Code:      ErrExtractNotFound,
		Category:  "extract",
		Message:   message,
		Stage:     StageExtract,
		Cause:     cause,
		Timestamp: time.Now(),
		Retryable: false,
	}
}

// NewOutputError 创建输出错误
func NewOutputError(message string, cause error) *JobError {
	return &JobError{
		Code:      ErrOutputWrite,
		Category:  "output",
		Message:   message,
		Stage:     StageOutput,
		Cause:     cause,
		Timestamp: time.Now(),
		Retryable: true,
	}
}

// NewInfraError 创建基础设施错误
func NewInfraError(message string, cause error) *JobError {
	return &JobError{
		Code:      ErrInfraNetwork,
		Category:  "infra",
		Message:   message,
		Stage:     StageExecute,
		Cause:     cause,
		Timestamp: time.Now(),
		Retryable: true,
	}
}

// isRetryable 判断错误代码是否可重试
func isRetryable(code ErrorCode) bool {
	retryableCodes := map[ErrorCode]bool{
		ErrRuntimeHTTP:      true,
		ErrRuntimeTimeout:   true,
		ErrInfraNetwork:     true,
		ErrInfraQueue:       true,
		ErrInfraWorker:      true,
		ErrOutputWrite:      true,
	}
	return retryableCodes[code]
}

// ============================================================================
// 错误包装器
// ============================================================================

// WrapError 包装现有错误为 JobError
func WrapError(err error, code ErrorCode, message string) *JobError {
	if err == nil {
		return nil
	}

	if jobErr, ok := err.(*JobError); ok {
		return jobErr
	}

	return &JobError{
		Code:      code,
		Message:   message,
		Cause:     err,
		Timestamp: time.Now(),
		Retryable: isRetryable(code),
	}
}

// WrapWithStage 包装错误并设置阶段
func WrapWithStage(err error, code ErrorCode, message string, stage ErrorStage) *JobError {
	jobErr := WrapError(err, code, message)
	if jobErr != nil {
		jobErr.Stage = stage
	}
	return jobErr
}

// WrapWithJob 包装错误并设置任务信息
func WrapWithJob(err error, code ErrorCode, message string, job *JobSpec) *JobError {
	jobErr := WrapError(err, code, message)
	if jobErr != nil && job != nil {
		jobErr.JobName = job.Name
		jobErr.Runtime = job.Runtime
		jobErr.URL = job.Target.URL
	}
	return jobErr
}

// ============================================================================
// 错误收集器
// ============================================================================

// ErrorCollector 错误收集器
type ErrorCollector struct {
	errors []*JobError
}

// NewErrorCollector 创建错误收集器
func NewErrorCollector() *ErrorCollector {
	return &ErrorCollector{}
}

// Add 添加错误
func (c *ErrorCollector) Add(err *JobError) {
	if err != nil {
		c.errors = append(c.errors, err)
	}
}

// HasErrors 是否有错误
func (c *ErrorCollector) HasErrors() bool {
	return len(c.errors) > 0
}

// Count 错误数量
func (c *ErrorCollector) Count() int {
	return len(c.errors)
}

// All 获取所有错误
func (c *ErrorCollector) All() []*JobError {
	return c.errors
}

// First 获取第一个错误
func (c *ErrorCollector) First() *JobError {
	if len(c.errors) == 0 {
		return nil
	}
	return c.errors[0]
}

// Retryable 获取所有可重试的错误
func (c *ErrorCollector) Retryable() []*JobError {
	var result []*JobError
	for _, err := range c.errors {
		if err.Retryable {
			result = append(result, err)
		}
	}
	return result
}

// ByStage 按阶段获取错误
func (c *ErrorCollector) ByStage(stage ErrorStage) []*JobError {
	var result []*JobError
	for _, err := range c.errors {
		if err.Stage == stage {
			result = append(result, err)
		}
	}
	return result
}

// ByCategory 按分类获取错误
func (c *ErrorCollector) ByCategory(category string) []*JobError {
	var result []*JobError
	for _, err := range c.errors {
		if err.Category == category {
			result = append(result, err)
		}
	}
	return result
}
