package main

import (
	"encoding/json"
	"fmt"
	"net"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"gospider/core"
	"gospider/media"
)

type doctorOptions struct {
	ConfigPath      string
	NetworkTargets  []string
	OverrideRedis   string
	CheckRedis      bool
	CheckFFmpeg     bool
	CheckBrowser    bool
	WritablePaths   []string
	AllowAutoCreate bool
}

type doctorCheck struct {
	Name    string
	Status  string
	Details string
}

type doctorReport struct {
	Checks []doctorCheck
	Config *core.Config
}

func (r doctorReport) AllPassed() bool {
	for _, check := range r.Checks {
		if check.Status == "failed" {
			return false
		}
	}
	return true
}

func (r doctorReport) HasWarnings() bool {
	for _, check := range r.Checks {
		if check.Status == "warning" {
			return true
		}
	}
	return false
}

func (r doctorReport) summaryText() string {
	passed := 0
	warning := 0
	failed := 0
	skipped := 0
	for _, check := range r.Checks {
		switch check.Status {
		case "passed":
			passed++
		case "warning":
			warning++
		case "skipped":
			skipped++
		default:
			failed++
		}
	}
	return fmt.Sprintf("%d passed, %d warning, %d failed, %d skipped", passed, warning, failed, skipped)
}

func passedCheck(name string, details string) doctorCheck {
	return doctorCheck{Name: name, Status: "passed", Details: details}
}

func failedCheck(name string, details string) doctorCheck {
	return doctorCheck{Name: name, Status: "failed", Details: details}
}

func warningCheck(name string, details string) doctorCheck {
	return doctorCheck{Name: name, Status: "warning", Details: details}
}

func skippedCheck(name string, details string) doctorCheck {
	return doctorCheck{Name: name, Status: "skipped", Details: details}
}

func loadDoctorConfig(configPath string) (*core.Config, string, error) {
	if configPath == "" {
		return core.DefaultConfig(), "使用默认配置", nil
	}

	if _, err := os.Stat(configPath); err != nil {
		if os.IsNotExist(err) && configPath == "gospider.yaml" {
			return core.DefaultConfig(), "未找到 gospider.yaml，使用默认配置", nil
		}
		return nil, "", fmt.Errorf("配置文件不可用: %w", err)
	}

	cfg, err := core.LoadConfig(configPath)
	if err != nil {
		return nil, "", err
	}
	if err := cfg.Validate(); err != nil {
		return nil, "", err
	}

	return cfg, fmt.Sprintf("已加载 %s", configPath), nil
}

func runDoctor(opts doctorOptions) doctorReport {
	report := doctorReport{}

	cfg, message, err := loadDoctorConfig(opts.ConfigPath)
	if err != nil {
		report.Checks = append(report.Checks, failedCheck("配置", err.Error()))
		return report
	}

	report.Config = cfg
	report.Checks = append(report.Checks, passedCheck("配置", message))

	report.Checks = append(report.Checks, passedCheck("Go 运行时", runtimeVersionSummary()))

	writablePaths := collectWritablePaths(cfg, opts.WritablePaths)
	for _, path := range writablePaths {
		report.Checks = append(report.Checks, checkWritablePath(path, opts.AllowAutoCreate))
	}

	for _, target := range opts.NetworkTargets {
		report.Checks = append(report.Checks, checkNetworkTarget(target))
	}

	if opts.CheckRedis {
		redisTarget := strings.TrimSpace(opts.OverrideRedis)
		if redisTarget == "" {
			redisTarget = strings.TrimSpace(cfg.Scheduler.RedisURL)
		}

		if redisTarget == "" {
			report.Checks = append(report.Checks, skippedCheck("Redis", "未配置，已跳过"))
		} else {
			report.Checks = append(report.Checks, checkRedisTarget(redisTarget))
		}
	}

	if opts.CheckFFmpeg {
		report.Checks = append(report.Checks, checkFFmpeg(cfg.Media.FFmpegPath))
	}

	if opts.CheckBrowser {
		report.Checks = append(report.Checks, checkBrowserDeps())
	}

	return report
}

func runtimeVersionSummary() string {
	return fmt.Sprintf("Go %s", strings.TrimPrefix(runtimeVersion(), "go"))
}

func runtimeVersion() string {
	return runtime.Version()
}

func collectWritablePaths(cfg *core.Config, extra []string) []string {
	seen := map[string]struct{}{}
	paths := []string{
		cfg.Output.Directory,
		cfg.Output.ArtifactDir,
		cfg.Output.DownloadDir,
		cfg.Media.OutputDir,
	}
	paths = append(paths, extra...)

	var result []string
	for _, path := range paths {
		path = strings.TrimSpace(path)
		if path == "" {
			continue
		}
		clean := filepath.Clean(path)
		if _, ok := seen[clean]; ok {
			continue
		}
		seen[clean] = struct{}{}
		result = append(result, clean)
	}
	return result
}

func checkWritablePath(path string, allowAutoCreate bool) doctorCheck {
	name := fmt.Sprintf("文件系统:%s", path)

	if allowAutoCreate {
		if err := os.MkdirAll(path, 0755); err != nil {
			return failedCheck(name, fmt.Sprintf("无法创建目录: %v", err))
		}
	} else {
		if _, err := os.Stat(path); err != nil {
			return failedCheck(name, fmt.Sprintf("目录不存在: %v", err))
		}
	}

	probeFile := filepath.Join(path, fmt.Sprintf(".gospider-doctor-%d.tmp", time.Now().UnixNano()))
	if err := os.WriteFile(probeFile, []byte("doctor"), 0644); err != nil {
		return failedCheck(name, fmt.Sprintf("无法写入: %v", err))
	}
	if err := os.Remove(probeFile); err != nil {
		return failedCheck(name, fmt.Sprintf("无法删除探针文件: %v", err))
	}

	return passedCheck(name, "可读写")
}

func checkNetworkTarget(target string) doctorCheck {
	name := fmt.Sprintf("网络:%s", target)
	address, err := normalizeDialTarget(target)
	if err != nil {
		return failedCheck(name, err.Error())
	}

	conn, err := net.DialTimeout("tcp", address, 3*time.Second)
	if err != nil {
		return failedCheck(name, fmt.Sprintf("连接失败: %v", err))
	}
	_ = conn.Close()

	return passedCheck(name, fmt.Sprintf("可连接 (%s)", address))
}

func normalizeDialTarget(target string) (string, error) {
	if strings.Contains(target, "://") {
		parsed, err := url.Parse(target)
		if err != nil {
			return "", fmt.Errorf("无效地址: %v", err)
		}
		host := parsed.Hostname()
		port := parsed.Port()
		if host == "" {
			return "", fmt.Errorf("缺少主机名")
		}
		if port == "" {
			switch parsed.Scheme {
			case "http":
				port = "80"
			case "https":
				port = "443"
			case "redis":
				port = "6379"
			default:
				return "", fmt.Errorf("无法推断端口")
			}
		}
		return net.JoinHostPort(host, port), nil
	}

	host, port, err := net.SplitHostPort(target)
	if err == nil && host != "" && port != "" {
		return target, nil
	}

	if strings.Count(target, ":") == 0 {
		return net.JoinHostPort(target, "80"), nil
	}

	return "", fmt.Errorf("目标必须是 URL 或 host:port: %s", target)
}

func checkRedisTarget(target string) doctorCheck {
	name := "Redis"
	address, err := normalizeDialTarget(target)
	if err != nil {
		return failedCheck(name, err.Error())
	}

	conn, err := net.DialTimeout("tcp", address, 3*time.Second)
	if err != nil {
		return failedCheck(name, fmt.Sprintf("连接失败: %v", err))
	}
	_ = conn.SetDeadline(time.Now().Add(3 * time.Second))
	if _, err := conn.Write([]byte("*1\r\n$4\r\nPING\r\n")); err != nil {
		_ = conn.Close()
		return failedCheck(name, fmt.Sprintf("PING 发送失败: %v", err))
	}

	buffer := make([]byte, 64)
	n, err := conn.Read(buffer)
	_ = conn.Close()
	if err != nil {
		return failedCheck(name, fmt.Sprintf("PING 读取失败: %v", err))
	}

	response := string(buffer[:n])
	if !strings.Contains(response, "PONG") {
		return failedCheck(name, fmt.Sprintf("收到异常响应: %q", response))
	}

	return passedCheck(name, fmt.Sprintf("可连接 (%s)", address))
}

func checkFFmpeg(configuredPath string) doctorCheck {
	name := "FFmpeg"

	if configuredPath != "" {
		if _, err := os.Stat(configuredPath); err == nil {
			return passedCheck(name, fmt.Sprintf("已配置 (%s)", configuredPath))
		}
		return failedCheck(name, fmt.Sprintf("配置路径不可用: %s", configuredPath))
	}

	path, err := media.AutoDetectFFmpeg()
	if err != nil {
		return warningCheck(name, err.Error())
	}

	return passedCheck(name, fmt.Sprintf("已找到 (%s)", path))
}

func checkBrowserDeps() doctorCheck {
	name := "浏览器依赖"
	candidates := []string{
		"chrome",
		"chrome.exe",
		"chromium",
		"chromium-browser",
		"msedge",
		"msedge.exe",
		"chromedriver",
		"chromedriver.exe",
	}

	for _, candidate := range candidates {
		if path, err := exec.LookPath(candidate); err == nil {
			return passedCheck(name, fmt.Sprintf("已找到 %s", path))
		}
	}

	commonPaths := []string{
		`C:\Program Files\Google\Chrome\Application\chrome.exe`,
		`C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`,
		`C:\Program Files\Microsoft\Edge\Application\msedge.exe`,
		`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`,
	}
	for _, path := range commonPaths {
		if _, err := os.Stat(path); err == nil {
			return passedCheck(name, fmt.Sprintf("已找到 %s", path))
		}
	}

	return warningCheck(name, "未找到 Chrome/Edge/chromedriver")
}

func renderDoctorReport(report doctorReport) string {
	return renderDoctorReportForCommand(report, "doctor")
}

func renderDoctorReportForCommand(report doctorReport, commandName string) string {
	var builder strings.Builder
	builder.WriteString(fmt.Sprintf("gospider %s\n", commandName))
	builder.WriteString("================\n")

	for _, check := range report.Checks {
		icon := map[string]string{
			"passed":  "✓",
			"warning": "!",
			"skipped": "-",
			"failed":  "✗",
		}[check.Status]
		if icon == "" {
			icon = "✗"
		}
		builder.WriteString(fmt.Sprintf("%s %s [%s]: %s\n", icon, check.Name, check.Status, check.Details))
	}

	builder.WriteString("\n")
	if !report.AllPassed() {
		builder.WriteString("部分检查失败，请查看上述错误\n")
	} else if report.HasWarnings() {
		builder.WriteString("检查通过，但存在可选依赖告警\n")
	} else {
		builder.WriteString("所有检查通过 ✓\n")
	}

	return builder.String()
}

func renderDoctorReportJSON(report doctorReport) (string, error) {
	return renderDoctorReportJSONForCommand(report, "doctor")
}

func renderDoctorReportJSONForCommand(report doctorReport, commandName string) (string, error) {
	type jsonCheck struct {
		Name    string `json:"name"`
		Status  string `json:"status"`
		Details string `json:"details"`
	}

	summary := "passed"
	if !report.AllPassed() {
		summary = "failed"
	}

	checks := make([]jsonCheck, 0, len(report.Checks))
	for _, check := range report.Checks {
		checks = append(checks, jsonCheck{
			Name:    check.Name,
			Status:  check.Status,
			Details: check.Details,
		})
	}

	payload := map[string]any{
		"command":      commandName,
		"framework":    "gospider",
		"runtime":      "go",
		"version":      version,
		"summary":      summary,
		"summary_text": report.summaryText(),
		"exit_code":    map[bool]int{true: 0, false: 1}[report.AllPassed()],
		"checks":       checks,
		"shared_contracts": []string{
			"shared-cli",
			"shared-config",
			"scrapy-project",
			"scrapy-plugins-manifest",
			"web-control-plane",
		},
	}

	data, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return "", err
	}
	return string(data), nil
}
