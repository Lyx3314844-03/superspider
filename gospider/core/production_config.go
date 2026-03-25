package core

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"gopkg.in/yaml.v3"
)

// ProductionConfig - 生产级配置
type ProductionConfig struct {
	Environment    string           `yaml:"environment" json:"environment"`
	AppName        string           `yaml:"app_name" json:"app_name"`
	AppVersion     string           `yaml:"app_version" json:"app_version"`
	Crawler        CrawlerConfig    `yaml:"crawler" json:"crawler"`
	Database       DatabaseConfig   `yaml:"database" json:"database"`
	Redis          RedisConfig      `yaml:"redis" json:"redis"`
	MessageQueue   MQConfig         `yaml:"message_queue" json:"message_queue"`
	Monitor        MonitorConfig    `yaml:"monitor" json:"monitor"`
	Security       SecurityConfig   `yaml:"security" json:"security"`
	configHash     string           `yaml:"-" json:"-"`
}

// CrawlerConfig - 爬虫配置
type CrawlerConfig struct {
	ThreadCount              int  `yaml:"thread_count" json:"thread_count"`
	MaxConnections           int  `yaml:"max_connections" json:"max_connections"`
	MaxRequestsPerSecond     int  `yaml:"max_requests_per_second" json:"max_requests_per_second"`
	MaxRetries               int  `yaml:"max_retries" json:"max_retries"`
	TimeoutSeconds           int  `yaml:"timeout_seconds" json:"timeout_seconds"`
	UserAgent                string `yaml:"user_agent" json:"user_agent"`
	FollowRedirects          bool `yaml:"follow_redirects" json:"follow_redirects"`
	EnableCookies            bool `yaml:"enable_cookies" json:"enable_cookies"`
	MaxDepth                 int  `yaml:"max_depth" json:"max_depth"`
	MaxConcurrentPerDomain   int  `yaml:"max_concurrent_per_domain" json:"max_concurrent_per_domain"`
	DelayBetweenRequestsMs   int  `yaml:"delay_between_requests_ms" json:"delay_between_requests_ms"`
	EnableProxyRotation      bool `yaml:"enable_proxy_rotation" json:"enable_proxy_rotation"`
	ProxyListFile            string `yaml:"proxy_list_file" json:"proxy_list_file"`
	EnableRobotsTxt          bool `yaml:"enable_robots_txt" json:"enable_robots_txt"`
	EnableRateLimiting       bool `yaml:"enable_rate_limiting" json:"enable_rate_limiting"`
}

// DatabaseConfig - 数据库配置
type DatabaseConfig struct {
	Driver                 string `yaml:"driver" json:"driver"`
	Host                   string `yaml:"host" json:"host"`
	Port                   int    `yaml:"port" json:"port"`
	Database               string `yaml:"database" json:"database"`
	Username               string `yaml:"username" json:"username"`
	Password               string `yaml:"password" json:"password"`
	MaxPoolSize            int    `yaml:"max_pool_size" json:"max_pool_size"`
	MinPoolSize            int    `yaml:"min_pool_size" json:"min_pool_size"`
	ConnectionTimeoutSecs  int    `yaml:"connection_timeout_secs" json:"connection_timeout_secs"`
	EnableSSL              bool   `yaml:"enable_ssl" json:"enable_ssl"`
	EnableHA               bool   `yaml:"enable_ha" json:"enable_ha"`
}

// RedisConfig - Redis 配置
type RedisConfig struct {
	Host            string   `yaml:"host" json:"host"`
	Port            int      `yaml:"port" json:"port"`
	Password        string   `yaml:"password" json:"password"`
	Database        int      `yaml:"database" json:"database"`
	MaxConnections  int      `yaml:"max_connections" json:"max_connections"`
	SocketTimeoutSecs int    `yaml:"socket_timeout_secs" json:"socket_timeout_secs"`
	EnableSSL       bool     `yaml:"enable_ssl" json:"enable_ssl"`
	EnableCluster   bool     `yaml:"enable_cluster" json:"enable_cluster"`
	ClusterNodes    []string `yaml:"cluster_nodes" json:"cluster_nodes"`
}

// MQConfig - 消息队列配置
type MQConfig struct {
	Type             string `yaml:"type" json:"type"`
	Host             string `yaml:"host" json:"host"`
	Port             int    `yaml:"port" json:"port"`
	Username         string `yaml:"username" json:"username"`
	Password         string `yaml:"password" json:"password"`
	VirtualHost      string `yaml:"virtual_host" json:"virtual_host"`
	QueueName        string `yaml:"queue_name" json:"queue_name"`
	EnablePersistence bool  `yaml:"enable_persistence" json:"enable_persistence"`
	PrefetchCount    int    `yaml:"prefetch_count" json:"prefetch_count"`
}

// MonitorConfig - 监控配置
type MonitorConfig struct {
	Enabled           bool    `yaml:"enabled" json:"enabled"`
	PrometheusEndpoint string `yaml:"prometheus_endpoint" json:"prometheus_endpoint"`
	MetricsPort       int     `yaml:"metrics_port" json:"metrics_port"`
	EnableHealthCheck bool    `yaml:"enable_health_check" json:"enable_health_check"`
	EnableMetrics     bool    `yaml:"enable_metrics" json:"enable_metrics"`
	EnableTracing     bool    `yaml:"enable_tracing" json:"enable_tracing"`
	TracingEndpoint   string  `yaml:"tracing_endpoint" json:"tracing_endpoint"`
	SamplingRate      float64 `yaml:"sampling_rate" json:"sampling_rate"`
	EnableAlerting    bool    `yaml:"enable_alerting" json:"enable_alerting"`
	AlertManagerURL   string  `yaml:"alert_manager_url" json:"alert_manager_url"`
}

// SecurityConfig - 安全配置
type SecurityConfig struct {
	EnableAuthentication  bool     `yaml:"enable_authentication" json:"enable_authentication"`
	AuthType              string   `yaml:"auth_type" json:"auth_type"`
	JWTSecret             string   `yaml:"jwt_secret" json:"jwt_secret"`
	JWTExpirationSecs     int      `yaml:"jwt_expiration_secs" json:"jwt_expiration_secs"`
	EnableRateLimiting    bool     `yaml:"enable_rate_limiting" json:"enable_rate_limiting"`
	RateLimitRequests     int      `yaml:"rate_limit_requests" json:"rate_limit_requests"`
	RateLimitWindowSecs   int      `yaml:"rate_limit_window_secs" json:"rate_limit_window_secs"`
	EnableIPWhitelist     bool     `yaml:"enable_ip_whitelist" json:"enable_ip_whitelist"`
	IPWhitelist           []string `yaml:"ip_whitelist" json:"ip_whitelist"`
	EnableEncryption      bool     `yaml:"enable_encryption" json:"enable_encryption"`
	EncryptionAlgorithm   string   `yaml:"encryption_algorithm" json:"encryption_algorithm"`
}

// DefaultProductionConfig - 默认生产配置
func DefaultProductionConfig() *ProductionConfig {
	return &ProductionConfig{
		Environment: "production",
		AppName:     "GoSpider",
		AppVersion:  "3.0.0",
		Crawler: CrawlerConfig{
			ThreadCount:              50,
			MaxConnections:           1000,
			MaxRequestsPerSecond:     500,
			MaxRetries:               3,
			TimeoutSeconds:           30,
			UserAgent:                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
			FollowRedirects:          true,
			EnableCookies:            true,
			MaxDepth:                 10,
			MaxConcurrentPerDomain:   10,
			DelayBetweenRequestsMs:   100,
			EnableProxyRotation:      false,
			ProxyListFile:            "proxies.txt",
			EnableRobotsTxt:          true,
			EnableRateLimiting:       true,
		},
		Database: DatabaseConfig{
			Driver:                "postgresql",
			Host:                  "localhost",
			Port:                  5432,
			Database:              "gospider",
			Username:              "gospider",
			Password:              "changeme",
			MaxPoolSize:           50,
			MinPoolSize:           10,
			ConnectionTimeoutSecs: 30,
			EnableSSL:             true,
			EnableHA:              true,
		},
		Redis: RedisConfig{
			Host:            "localhost",
			Port:            6379,
			Password:        "",
			Database:        0,
			MaxConnections:  100,
			SocketTimeoutSecs: 5,
			EnableSSL:       false,
			EnableCluster:   false,
		},
		MessageQueue: MQConfig{
			Type:             "rabbitmq",
			Host:             "localhost",
			Port:             5672,
			Username:         "guest",
			Password:         "guest",
			VirtualHost:      "/",
			QueueName:        "gospider.requests",
			EnablePersistence: true,
			PrefetchCount:    10,
		},
		Monitor: MonitorConfig{
			Enabled:            true,
			PrometheusEndpoint: "/metrics",
			MetricsPort:        9090,
			EnableHealthCheck:  true,
			EnableMetrics:      true,
			EnableTracing:      true,
			TracingEndpoint:    "http://localhost:4317",
			SamplingRate:       0.1,
			EnableAlerting:     true,
			AlertManagerURL:    "http://localhost:9093",
		},
		Security: SecurityConfig{
			EnableAuthentication:  true,
			AuthType:              "jwt",
			JWTSecret:             "changeme",
			JWTExpirationSecs:     86400,
			EnableRateLimiting:    true,
			RateLimitRequests:     1000,
			RateLimitWindowSecs:   60,
			EnableIPWhitelist:     false,
			EnableEncryption:      true,
			EncryptionAlgorithm:   "AES-256-GCM",
		},
	}
}

// LoadProductionConfig - 加载生产配置
func LoadProductionConfig(environment string) (*ProductionConfig, error) {
	configPaths := []string{
		fmt.Sprintf("config/application-%s.yaml", environment),
		"config/application.yaml",
		"application.yaml",
	}

	var configData map[string]interface{}
	var loadedPath string

	for _, path := range configPaths {
		data, err := ioutil.ReadFile(path)
		if err == nil {
			configData = make(map[string]interface{})
			if err := yaml.Unmarshal(data, &configData); err != nil {
				return nil, fmt.Errorf("failed to parse config file %s: %w", path, err)
			}
			loadedPath = path
			break
		}
	}

	if configData == nil {
		return nil, fmt.Errorf("no config file found in %v", configPaths)
	}

	config := DefaultProductionConfig()
	config.Environment = environment

	// 合并配置
	if err := mergeConfig(config, configData); err != nil {
		return nil, err
	}

	// 环境变量覆盖
	applyEnvOverrides(config)

	// 计算配置哈希
	config.computeHash()

	fmt.Printf("Loaded production config from %s\n", loadedPath)
	return config, nil
}

// mergeConfig - 合并配置
func mergeConfig(config *ProductionConfig, data map[string]interface{}) error {
	// 使用 JSON 作为中间格式进行转换
	jsonData, err := json.Marshal(data)
	if err != nil {
		return err
	}

	return json.Unmarshal(jsonData, config)
}

// applyEnvOverrides - 应用环境变量覆盖
func applyEnvOverrides(config *ProductionConfig) {
	// 爬虫配置
	if val := os.Getenv("CRAWLER_THREAD_COUNT"); val != "" {
		if n, err := strconv.Atoi(val); err == nil {
			config.Crawler.ThreadCount = n
		}
	}

	// 数据库配置
	if val := os.Getenv("DATABASE_HOST"); val != "" {
		config.Database.Host = val
	}
	if val := os.Getenv("DATABASE_PASSWORD"); val != "" {
		config.Database.Password = val
	}

	// Redis 配置
	if val := os.Getenv("REDIS_HOST"); val != "" {
		config.Redis.Host = val
	}
	if val := os.Getenv("REDIS_PASSWORD"); val != "" {
		config.Redis.Password = val
	}

	// 安全配置
	if val := os.Getenv("JWT_SECRET"); val != "" {
		config.Security.JWTSecret = val
	}
}

// computeHash - 计算配置哈希
func (c *ProductionConfig) computeHash() {
	data, _ := json.Marshal(c)
	hash := sha256.Sum256(data)
	c.configHash = hex.EncodeToString(hash[:])
}

// HasChanged - 检查配置是否变更
func (c *ProductionConfig) HasChanged(other *ProductionConfig) bool {
	return c.configHash != other.configHash
}

// Validate - 校验配置
func (c *ProductionConfig) Validate() error {
	fmt.Println("Validating production configuration...")

	var errors []string

	// 校验爬虫配置
	if c.Crawler.ThreadCount <= 0 {
		errors = append(errors, "crawler.thread_count must be positive")
	}
	if c.Crawler.MaxConnections <= 0 {
		errors = append(errors, "crawler.max_connections must be positive")
	}

	// 校验数据库配置
	if c.Database.MaxPoolSize <= 0 {
		errors = append(errors, "database.max_pool_size must be positive")
	}

	// 校验 Redis 配置
	if c.Redis.Port <= 0 || c.Redis.Port > 65535 {
		errors = append(errors, "redis.port must be between 1 and 65535")
	}

	// 校验监控配置
	if c.Monitor.Enabled && (c.Monitor.MetricsPort <= 0 || c.Monitor.MetricsPort > 65535) {
		errors = append(errors, "monitor.metrics_port must be between 1 and 65535")
	}

	// 校验安全配置
	if c.Security.EnableAuthentication && c.Security.AuthType == "jwt" {
		if len(c.Security.JWTSecret) < 32 {
			errors = append(errors, "security.jwt_secret must be at least 32 characters")
		}
	}

	if len(errors) > 0 {
		for _, err := range errors {
			fmt.Printf("Configuration validation failed: %s\n", err)
		}
		return fmt.Errorf("configuration validation failed: %s", strings.Join(errors, ", "))
	}

	fmt.Println("Production configuration validation passed")
	return nil
}

// PrintSummary - 打印配置摘要
func (c *ProductionConfig) PrintSummary() {
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("Production Configuration Summary")
	fmt.Println(strings.Repeat("=", 60))
	fmt.Printf("Environment: %s\n", c.Environment)
	fmt.Printf("App Name: %s\n", c.AppName)
	fmt.Printf("App Version: %s\n", c.AppVersion)
	fmt.Println("")
	fmt.Println("Crawler:")
	fmt.Printf("  - Thread Count: %d\n", c.Crawler.ThreadCount)
	fmt.Printf("  - Max Connections: %d\n", c.Crawler.MaxConnections)
	fmt.Printf("  - Max Requests/sec: %d\n", c.Crawler.MaxRequestsPerSecond)
	fmt.Println("")
	fmt.Printf("Database: %s:%d/%s\n", c.Database.Host, c.Database.Port, c.Database.Database)
	fmt.Printf("Redis: %s:%d\n", c.Redis.Host, c.Redis.Port)
	fmt.Printf("Message Queue: %s (%s:%d)\n", c.MessageQueue.Type, c.MessageQueue.Host, c.MessageQueue.Port)
	fmt.Println("")
	fmt.Printf("Monitor: %s\n", map[bool]string{true: "enabled", false: "disabled"}[c.Monitor.Enabled])
	fmt.Printf("Security: %s\n", map[bool]string{true: "enabled", false: "disabled"}[c.Security.EnableAuthentication])
	fmt.Println(strings.Repeat("=", 60))
}

// Save - 保存配置到文件
func (c *ProductionConfig) Save(path string) error {
	data, err := yaml.Marshal(c)
	if err != nil {
		return err
	}

	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}

	return ioutil.WriteFile(path, data, 0644)
}

// WatchForChanges - 监听配置变更
func (c *ProductionConfig) WatchForChanges(interval time.Duration, onChange func(*ProductionConfig)) {
	go func() {
		ticker := time.NewTicker(interval)
		defer ticker.Stop()

		for range ticker.C {
			newConfig, err := LoadProductionConfig(c.Environment)
			if err != nil {
				fmt.Printf("Failed to reload config: %v\n", err)
				continue
			}

			if c.HasChanged(newConfig) {
				fmt.Println("Configuration changed, reloading...")
				onChange(newConfig)
				*c = *newConfig
			}
		}
	}()
}
