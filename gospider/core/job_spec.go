// gospider v1 - 统一任务模型
// 基于设计文档：docs/superpowers/specs/2026-03-22-gospider-v1-design.md

package core

import (
	"encoding/json"
	"fmt"
	"time"
)

// ============================================================================
// v1.0 统一任务模型 - JobSpec
// ============================================================================

// JobSpec 是每个执行请求的统一规范化模型
// 所有入口点 (CLI, Web UI, Worker, 库调用) 都收敛到这个模型
type JobSpec struct {
	// 基本信息
	Name     string            `json:"name" yaml:"name"`                     // 任务名称
	Runtime  Runtime           `json:"runtime" yaml:"runtime"`               // 运行时：http|browser
	Priority int               `json:"priority,omitempty" yaml:"priority"`   // 优先级

	// 目标定义
	Target TargetSpec `json:"target" yaml:"target"` // 请求目标

	// 浏览器动作 (仅 browser 运行时)
	Actions []ActionSpec `json:"actions,omitempty" yaml:"actions"`

	// 提取规范
	Extract []ExtractSpec `json:"extract,omitempty" yaml:"extract"`

	// 输出规范
	Output OutputSpec `json:"output" yaml:"output"`

	// 调度规范
	Schedule ScheduleSpec `json:"schedule,omitempty" yaml:"schedule"`

	// 资源规范
	Resources ResourceSpec `json:"resources,omitempty" yaml:"resources"`

	// 媒体能力
	Media MediaSpec `json:"media,omitempty" yaml:"media"`

	// 元数据
	Metadata map[string]interface{} `json:"metadata,omitempty" yaml:"metadata"`
}

// TargetSpec 定义请求目标
type TargetSpec struct {
	URL     string            `json:"url" yaml:"url"`                                   // 目标 URL
	Method  string            `json:"method,omitempty" yaml:"method"`                   // HTTP 方法
	Headers map[string]string `json:"headers,omitempty" yaml:"headers"`                 // 请求头
	Cookies map[string]string `json:"cookies,omitempty" yaml:"cookies"`                 // Cookie
	Body    string            `json:"body,omitempty" yaml:"body"`                       // 请求体
	Timeout time.Duration     `json:"timeout,omitempty" yaml:"timeout"`                 // 超时时间
	Retries int               `json:"retries,omitempty" yaml:"retries"`                 // 重试次数
	Proxy   string            `json:"proxy,omitempty" yaml:"proxy"`                     // 代理地址
}

// ActionSpec 定义浏览器动作 (declarative browser actions)
type ActionSpec struct {
	Type      string                 `json:"type" yaml:"type"`             // 动作类型：goto|wait|click|type|scroll|select|hover|eval|screenshot|listen_network
	Selector  string                 `json:"selector,omitempty" yaml:"selector"` // CSS/XPath 选择器
	Value     string                 `json:"value,omitempty" yaml:"value"`       // 输入值/JS 代码
	URL       string                 `json:"url,omitempty" yaml:"url"`         // 用于 goto 动作
	Timeout   time.Duration          `json:"timeout,omitempty" yaml:"timeout"`   // 超时
	Optional  bool                   `json:"optional,omitempty" yaml:"optional"` // 是否可选
	SaveAs    string                 `json:"save_as,omitempty" yaml:"save_as"`   // 保存为字段名
	Mode      string                 `json:"mode,omitempty" yaml:"mode"`         // 模式：bottom|top|element (scroll)
	MaxScroll int                    `json:"max_scrolls,omitempty" yaml:"max_scrolls"` // 最大滚动次数
	Extra     map[string]interface{} `json:"extra,omitempty" yaml:"extra"`         // 额外参数
}

// ExtractSpec 定义提取规范
type ExtractSpec struct {
	Field string `json:"field" yaml:"field"`         // 字段名
	Type  string `json:"type" yaml:"type"`           // 提取类型：css|css_attr|xpath|regex|json_path|media
	Expr  string `json:"expr" yaml:"expr"`           // 表达式
	Attr  string `json:"attr,omitempty" yaml:"attr"` // 属性名 (css_attr 类型)
	Regex string `json:"regex,omitempty" yaml:"regex"` // 正则表达式 (regex 类型)
	Path  string `json:"path,omitempty" yaml:"path"`   // JSON 路径 (json_path 类型)
}

// OutputSpec 定义输出规范
type OutputSpec struct {
	Format    string `json:"format" yaml:"format"`             // 输出格式：json|jsonl|csv
	Path      string `json:"path,omitempty" yaml:"path"`       // 输出路径
	Directory string `json:"directory,omitempty" yaml:"directory"` // 输出目录
	Artifact  string `json:"artifact,omitempty" yaml:"artifact"`   // 工件名称
}

// ScheduleSpec 定义调度规范
type ScheduleSpec struct {
	Mode      string `json:"mode,omitempty" yaml:"mode"`             // 调度模式：once|queued|distributed|scheduled
	Cron      string `json:"cron,omitempty" yaml:"cron"`             // Cron 表达式 (scheduled 模式)
	QueueName string `json:"queue_name,omitempty" yaml:"queue_name"` // 队列名称 (queued/distributed 模式)
	Delay     int    `json:"delay,omitempty" yaml:"delay"`           // 延迟秒数
}

// ResourceSpec 定义资源规范
type ResourceSpec struct {
	// 并发控制
	Concurrency int `json:"concurrency,omitempty" yaml:"concurrency"` // 并发数
	Timeout     time.Duration `json:"timeout,omitempty" yaml:"timeout"` // 超时
	Retries     int           `json:"retries,omitempty" yaml:"retries"`   // 重试次数

	// 下载配置
	DownloadDir string `json:"download_dir,omitempty" yaml:"download_dir"` // 下载目录
	TempDir     string `json:"temp_dir,omitempty" yaml:"temp_dir"`         // 临时目录

	// 浏览器配置
	Browser BrowserResourceSpec `json:"browser,omitempty" yaml:"browser"`

	// 速率限制
	RateLimit RateLimitSpec `json:"rate_limit,omitempty" yaml:"rate_limit"`
}

// BrowserResourceSpec 浏览器资源配置
type BrowserResourceSpec struct {
	Headless    bool          `json:"headless,omitempty" yaml:"headless"`       // 无头模式
	Viewport    ViewportSpec  `json:"viewport,omitempty" yaml:"viewport"`       // 视口大小
	UserAgent   string        `json:"user_agent,omitempty" yaml:"user_agent"`   // User-Agent
	WaitLoad    bool          `json:"wait_load,omitempty" yaml:"wait_load"`     // 等待页面加载
	BlockImages bool          `json:"block_images,omitempty" yaml:"block_images"` // 阻止图片
	Cookies     []CookieSpec  `json:"cookies,omitempty" yaml:"cookies"`         // Cookie
}

// ViewportSpec 视口配置
type ViewportSpec struct {
	Width  int `json:"width,omitempty" yaml:"width"`
	Height int `json:"height,omitempty" yaml:"height"`
}

// CookieSpec Cookie 配置
type CookieSpec struct {
	Name   string `json:"name" yaml:"name"`
	Value  string `json:"value" yaml:"value"`
	Domain string `json:"domain,omitempty" yaml:"domain"`
	Path   string `json:"path,omitempty" yaml:"path"`
}

// RateLimitSpec 速率限制配置
type RateLimitSpec struct {
	Enabled   bool          `json:"enabled,omitempty" yaml:"enabled"`   // 是否启用
	Requests  int           `json:"requests,omitempty" yaml:"requests"` // 请求数
	Interval  time.Duration `json:"interval,omitempty" yaml:"interval"` // 时间间隔
	Delay     time.Duration `json:"delay,omitempty" yaml:"delay"`       // 请求间隔
}

// MediaSpec 媒体能力配置
type MediaSpec struct {
	Enabled  bool     `json:"enabled,omitempty" yaml:"enabled"`   // 是否启用媒体发现
	Download bool     `json:"download,omitempty" yaml:"download"` // 是否下载媒体
	Types    []string `json:"types,omitempty" yaml:"types"`       // 媒体类型：video|audio|image|hls|dash
	OutputDir string  `json:"output_dir,omitempty" yaml:"output_dir"` // 输出目录
}

// ============================================================================
// 验证方法
// ============================================================================

// Validate 验证 JobSpec 的最小契约
func (j *JobSpec) Validate() error {
	if j.Name == "" {
		return fmt.Errorf("job name is required")
	}
	if j.Target.URL == "" {
		return fmt.Errorf("target.url is required")
	}
	switch j.Runtime {
	case RuntimeHTTP, RuntimeBrowser:
		// 有效
	default:
		return fmt.Errorf("unsupported runtime %q", j.Runtime)
	}
	return nil
}

// ToRequest 将 JobSpec 转换为 Request (向后兼容)
func (j *JobSpec) ToRequest() *Request {
	if j == nil {
		return nil
	}

	method := j.Target.Method
	if method == "" {
		method = "GET"
	}

	return &Request{
		URL:      j.Target.URL,
		Method:   method,
		Headers:  j.Target.Headers,
		Body:     j.Target.Body,
		Meta:     j.Metadata,
		Priority: j.Priority,
	}
}

// FromRequest 从 Request 创建 JobSpec (向后兼容)
func FromRequest(req *Request, name string) *JobSpec {
	if req == nil {
		return nil
	}

	return &JobSpec{
		Name:     name,
		Runtime:  RuntimeHTTP,
		Target:   req.ToTargetSpec(),
		Priority: req.Priority,
		Metadata: req.Meta,
	}
}

// MarshalJSON 自定义 JSON 序列化 (处理时间 Duration)
func (j *JobSpec) MarshalJSON() ([]byte, error) {
	type Alias JobSpec
	return json.Marshal(&struct {
		*Alias
		TargetTimeout string `json:"target_timeout,omitempty"`
	}{
		Alias:         (*Alias)(j),
		TargetTimeout: j.Target.Timeout.String(),
	})
}

// UnmarshalJSON 自定义 JSON 反序列化 (处理时间 Duration)
func (j *JobSpec) UnmarshalJSON(data []byte) error {
	type Alias JobSpec
	aux := &struct {
		*Alias
		TargetTimeout string `json:"target_timeout,omitempty"`
	}{
		Alias: (*Alias)(j),
	}

	if err := json.Unmarshal(data, &aux); err != nil {
		return err
	}

	if aux.TargetTimeout != "" {
		duration, err := time.ParseDuration(aux.TargetTimeout)
		if err != nil {
			return err
		}
		j.Target.Timeout = duration
	}

	return nil
}

// ============================================================================
// 构建器模式
// ============================================================================

// JobBuilder JobSpec 构建器
type JobBuilder struct {
	job *JobSpec
}

// NewJob 创建新的 JobBuilder
func NewJob(name string) *JobBuilder {
	return &JobBuilder{
		job: &JobSpec{
			Name:     name,
			Runtime:  RuntimeHTTP,
			Target:   TargetSpec{Method: "GET"},
			Output:   OutputSpec{Format: "json"},
			Schedule: ScheduleSpec{Mode: "once"},
		},
	}
}

// SetRuntime 设置运行时
func (b *JobBuilder) SetRuntime(runtime Runtime) *JobBuilder {
	b.job.Runtime = runtime
	return b
}

// SetTarget 设置目标
func (b *JobBuilder) SetTarget(url string) *JobBuilder {
	b.job.Target.URL = url
	return b
}

// SetMethod 设置 HTTP 方法
func (b *JobBuilder) SetMethod(method string) *JobBuilder {
	b.job.Target.Method = method
	return b
}

// SetHeaders 设置请求头
func (b *JobBuilder) SetHeaders(headers map[string]string) *JobBuilder {
	b.job.Target.Headers = headers
	return b
}

// AddHeader 添加请求头
func (b *JobBuilder) AddHeader(key, value string) *JobBuilder {
	if b.job.Target.Headers == nil {
		b.job.Target.Headers = make(map[string]string)
	}
	b.job.Target.Headers[key] = value
	return b
}

// SetPriority 设置优先级
func (b *JobBuilder) SetPriority(priority int) *JobBuilder {
	b.job.Priority = priority
	return b
}

// AddAction 添加浏览器动作
func (b *JobBuilder) AddAction(action ActionSpec) *JobBuilder {
	b.job.Actions = append(b.job.Actions, action)
	return b
}

// AddExtract 添加提取规则
func (b *JobBuilder) AddExtract(extract ExtractSpec) *JobBuilder {
	b.job.Extract = append(b.job.Extract, extract)
	return b
}

// SetOutput 设置输出
func (b *JobBuilder) SetOutput(format, path string) *JobBuilder {
	b.job.Output = OutputSpec{
		Format: format,
		Path:   path,
	}
	return b
}

// SetMedia 设置媒体配置
func (b *JobBuilder) SetMedia(enabled, download bool) *JobBuilder {
	b.job.Media = MediaSpec{
		Enabled:  enabled,
		Download: download,
	}
	return b
}

// SetConcurrency 设置并发数
func (b *JobBuilder) SetConcurrency(concurrency int) *JobBuilder {
	b.job.Resources.Concurrency = concurrency
	return b
}

// SetTimeout 设置超时
func (b *JobBuilder) SetTimeout(timeout time.Duration) *JobBuilder {
	b.job.Resources.Timeout = timeout
	return b
}

// SetHeadless 设置浏览器无头模式
func (b *JobBuilder) SetHeadless(headless bool) *JobBuilder {
	b.job.Resources.Browser.Headless = headless
	return b
}

// Build 构建 JobSpec
func (b *JobBuilder) Build() (*JobSpec, error) {
	if err := b.job.Validate(); err != nil {
		return nil, err
	}
	return b.job, nil
}
