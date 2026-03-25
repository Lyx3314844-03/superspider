// gospider v1 - 统一配置系统
// 基于设计文档：docs/superpowers/specs/2026-03-22-gospider-v1-design.md

package core

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"gopkg.in/yaml.v3"
)

// ============================================================================
// v1.0 统一配置系统
// ============================================================================

// Config 全局项目配置 (gospider.yaml)
type Config struct {
	// 基本信息
	Name    string `json:"name" yaml:"name"`         // 项目名称
	Version string `json:"version" yaml:"version"`   // 项目版本

	// 并发配置
	Concurrency int `json:"concurrency" yaml:"concurrency"` // 默认并发数

	// 重试配置
	Retry RetryConfig `json:"retry" yaml:"retry"`

	// 超时配置
	Timeout TimeoutConfig `json:"timeout" yaml:"timeout"`

	// 输出路径
	Output OutputConfig `json:"output" yaml:"output"`

	// 浏览器默认配置
	Browser BrowserConfig `json:"browser" yaml:"browser"`

	// 媒体默认配置
	Media MediaConfig `json:"media" yaml:"media"`

	// 调度器默认配置
	Scheduler SchedulerConfig `json:"scheduler" yaml:"scheduler"`

	// Worker 默认配置
	Worker WorkerConfig `json:"worker" yaml:"worker"`

	// Web UI 默认配置
	Web WebConfig `json:"web" yaml:"web"`

	// 日志配置
	Log LogConfig `json:"log" yaml:"log"`
}

// RetryConfig 重试配置
type RetryConfig struct {
	Enabled   bool `json:"enabled" yaml:"enabled"`         // 是否启用重试
	MaxRetries int `json:"max_retries" yaml:"max_retries"` // 最大重试次数
	Delay     time.Duration `json:"delay" yaml:"delay"`     // 重试间隔
	Backoff   float64 `json:"backoff" yaml:"backoff"`       // 退避因子
}

// TimeoutConfig 超时配置
type TimeoutConfig struct {
	Request  time.Duration `json:"request" yaml:"request"`   // 请求超时
	Job      time.Duration `json:"job" yaml:"job"`           // 任务超时
	Browser  time.Duration `json:"browser" yaml:"browser"`   // 浏览器超时
	Download time.Duration `json:"download" yaml:"download"` // 下载超时
}

// OutputConfig 输出配置
type OutputConfig struct {
	Directory    string `json:"directory" yaml:"directory"`       // 默认输出目录
	Format       string `json:"format" yaml:"format"`             // 默认输出格式
	ArtifactDir  string `json:"artifact_dir" yaml:"artifact_dir"` // 工件目录
	DownloadDir  string `json:"download_dir" yaml:"download_dir"` // 下载目录
}

// BrowserConfig 浏览器配置
type BrowserConfig struct {
	Headless    bool          `json:"headless" yaml:"headless"`       // 无头模式
	Viewport    ViewportSpec  `json:"viewport" yaml:"viewport"`       // 默认视口
	UserAgent   string        `json:"user_agent" yaml:"user_agent"`   // 默认 User-Agent
	WaitLoad    bool          `json:"wait_load" yaml:"wait_load"`     // 等待页面加载
	BlockImages bool          `json:"block_images" yaml:"block_images"` // 阻止图片
	Timeout     time.Duration `json:"timeout" yaml:"timeout"`         // 浏览器超时
}

// MediaConfig 媒体配置
type MediaConfig struct {
	Enabled     bool     `json:"enabled" yaml:"enabled"`         // 是否启用媒体发现
	Download    bool     `json:"download" yaml:"download"`       // 是否下载媒体
	Types       []string `json:"types" yaml:"types"`             // 媒体类型
	OutputDir   string   `json:"output_dir" yaml:"output_dir"`   // 输出目录
	FFmpegPath  string   `json:"ffmpeg_path" yaml:"ffmpeg_path"` // FFmpeg 路径
}

// SchedulerConfig 调度器配置
type SchedulerConfig struct {
	Mode        string        `json:"mode" yaml:"mode"`           // 调度模式
	QueueName   string        `json:"queue_name" yaml:"queue_name"` // 队列名称
	RedisURL    string        `json:"redis_url" yaml:"redis_url"`   // Redis URL
	PollInterval time.Duration `json:"poll_interval" yaml:"poll_interval"` // 轮询间隔
}

// WorkerConfig Worker 配置
type WorkerConfig struct {
	ID          string `json:"id" yaml:"id"`                 // Worker ID
	Concurrency int    `json:"concurrency" yaml:"concurrency"` // 并发数
	QueueName   string `json:"queue_name" yaml:"queue_name"`   // 队列名称
}

// WebConfig Web UI 配置
type WebConfig struct {
	Host string `json:"host" yaml:"host"` // 监听地址
	Port int    `json:"port" yaml:"port"` // 监听端口
}

// LogConfig 日志配置
type LogConfig struct {
	Level  string `json:"level" yaml:"level"`   // 日志级别
	Format string `json:"format" yaml:"format"` // 日志格式：json|text
	File   string `json:"file" yaml:"file"`     // 日志文件
}

// DefaultConfig 返回默认配置
func DefaultConfig() *Config {
	return &Config{
		Name:        "default",
		Version:     "1.0.0",
		Concurrency: 5,
		Retry: RetryConfig{
			Enabled:    true,
			MaxRetries: 3,
			Delay:      1 * time.Second,
			Backoff:    2.0,
		},
		Timeout: TimeoutConfig{
			Request:  30 * time.Second,
			Job:      5 * time.Minute,
			Browser:  2 * time.Minute,
			Download: 10 * time.Minute,
		},
		Output: OutputConfig{
			Directory:   "./outputs",
			Format:      "json",
			ArtifactDir: "./artifacts",
			DownloadDir: "./downloads",
		},
		Browser: BrowserConfig{
			Headless:    true,
			WaitLoad:    true,
			BlockImages: false,
			Timeout:     2 * time.Minute,
			Viewport: ViewportSpec{
				Width:  1920,
				Height: 1080,
			},
		},
		Media: MediaConfig{
			Enabled:   true,
			Download:  false,
			Types:     []string{"video", "audio", "image", "hls", "dash"},
			OutputDir: "./media",
		},
		Scheduler: SchedulerConfig{
			Mode:         "local",
			QueueName:    "default",
			PollInterval: 1 * time.Second,
		},
		Worker: WorkerConfig{
			ID:          "worker-1",
			Concurrency: 5,
			QueueName:   "default",
		},
		Web: WebConfig{
			Host: "localhost",
			Port: 8080,
		},
		Log: LogConfig{
			Level:  "info",
			Format: "text",
		},
	}
}

// LoadConfig 从文件加载配置
func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	config := DefaultConfig()

	// 根据文件扩展名选择解析方式
	ext := filepath.Ext(path)
	switch ext {
	case ".yaml", ".yml":
		if err := yaml.Unmarshal(data, config); err != nil {
			return nil, fmt.Errorf("failed to parse YAML config: %w", err)
		}
	case ".json":
		if err := json.Unmarshal(data, config); err != nil {
			return nil, fmt.Errorf("failed to parse JSON config: %w", err)
		}
	default:
		// 尝试 YAML
		if err := yaml.Unmarshal(data, config); err != nil {
			// 尝试 JSON
			if err2 := json.Unmarshal(data, config); err2 != nil {
				return nil, fmt.Errorf("failed to parse config (tried YAML and JSON): %w", err)
			}
		}
	}

	return config, nil
}

// SaveConfig 保存配置到文件
func (c *Config) SaveConfig(path string) error {
	// 创建目录
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}

	var data []byte
	var err error

	ext := filepath.Ext(path)
	switch ext {
	case ".yaml", ".yml":
		data, err = yaml.Marshal(c)
	case ".json":
		data, err = json.MarshalIndent(c, "", "  ")
	default:
		// 默认 YAML
		data, err = yaml.Marshal(c)
	}

	if err != nil {
		return err
	}

	return os.WriteFile(path, data, 0644)
}

// Validate 验证配置
func (c *Config) Validate() error {
	if c.Concurrency < 1 {
		return fmt.Errorf("concurrency must be at least 1")
	}
	if c.Retry.MaxRetries < 0 {
		return fmt.Errorf("max_retries must be non-negative")
	}
	if c.Timeout.Request <= 0 {
		return fmt.Errorf("request timeout must be positive")
	}
	if c.Web.Port < 1 || c.Web.Port > 65535 {
		return fmt.Errorf("web port must be between 1 and 65535")
	}
	return nil
}

// MergeConfig 合并配置 (job 配置覆盖全局配置)
func (c *Config) MergeConfig(job *JobSpec) *JobSpec {
	if job == nil {
		return nil
	}

	// 创建副本
	merged := *job

	// 合并超时
	if merged.Resources.Timeout == 0 && c.Timeout.Job > 0 {
		merged.Resources.Timeout = c.Timeout.Job
	}

	// 合并并发
	if merged.Resources.Concurrency == 0 && c.Concurrency > 0 {
		merged.Resources.Concurrency = c.Concurrency
	}

	// 合并重试
	if merged.Resources.Retries == 0 && c.Retry.MaxRetries > 0 {
		merged.Resources.Retries = c.Retry.MaxRetries
	}

	// 合并浏览器配置
	if merged.Runtime == RuntimeBrowser {
		if merged.Resources.Browser.Viewport.Width == 0 {
			merged.Resources.Browser.Viewport = c.Browser.Viewport
		}
		if merged.Resources.Browser.UserAgent == "" {
			merged.Resources.Browser.UserAgent = c.Browser.UserAgent
		}
	}

	// 合并输出配置
	if merged.Output.Path == "" && c.Output.Directory != "" {
		merged.Output.Directory = c.Output.Directory
	}

	// 合并媒体配置
	if !merged.Media.Enabled {
		merged.Media.Enabled = c.Media.Enabled
	}
	if merged.Media.OutputDir == "" && c.Media.OutputDir != "" {
		merged.Media.OutputDir = c.Media.OutputDir
	}

	return &merged
}

// ============================================================================
// 项目配置管理
// ============================================================================

// ProjectConfig 项目管理器
type ProjectConfig struct {
	config *Config
	path   string
}

// NewProjectConfig 创建项目配置
func NewProjectConfig(path string) *ProjectConfig {
	return &ProjectConfig{
		path: path,
	}
}

// Load 加载配置
func (p *ProjectConfig) Load() error {
	config, err := LoadConfig(p.path)
	if err != nil {
		return err
	}
	p.config = config
	return nil
}

// Get 获取配置
func (p *ProjectConfig) Get() *Config {
	if p.config == nil {
		return DefaultConfig()
	}
	return p.config
}

// Save 保存配置
func (p *ProjectConfig) Save() error {
	if p.config == nil {
		p.config = DefaultConfig()
	}
	return p.config.SaveConfig(p.path)
}

// Init 初始化项目配置
func (p *ProjectConfig) Init(name string) error {
	p.config = DefaultConfig()
	p.config.Name = name
	return p.Save()
}
