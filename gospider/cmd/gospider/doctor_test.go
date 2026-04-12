package main

import (
	"encoding/json"
	"net"
	"path/filepath"
	"strings"
	"testing"

	"gospider/core"
)

func TestRunDoctorPassesWithReachableTargets(t *testing.T) {
	root := t.TempDir()
	cfg := createDoctorTestConfig(t, root)

	networkListener := startTCPListener(t, func(conn net.Conn) {
		_ = conn.Close()
	})
	redisListener := startTCPListener(t, func(conn net.Conn) {
		defer conn.Close()
		buffer := make([]byte, 128)
		_, _ = conn.Read(buffer)
		_, _ = conn.Write([]byte("+PONG\r\n"))
	})

	report := runDoctor(doctorOptions{
		ConfigPath:      cfg,
		NetworkTargets:  []string{networkListener.Addr().String()},
		CheckRedis:      true,
		OverrideRedis:   "redis://" + redisListener.Addr().String(),
		CheckFFmpeg:     false,
		CheckBrowser:    false,
		AllowAutoCreate: true,
	})

	if !report.AllPassed() {
		t.Fatalf("expected doctor report to pass, got %#v", report.Checks)
	}

	output := renderDoctorReport(report)
	if !strings.Contains(output, "所有检查通过") {
		t.Fatalf("expected success summary, got:\n%s", output)
	}
}

func TestRunDoctorReportsRedisFailure(t *testing.T) {
	root := t.TempDir()
	cfg := createDoctorTestConfig(t, root)

	report := runDoctor(doctorOptions{
		ConfigPath:      cfg,
		NetworkTargets:  []string{},
		CheckRedis:      true,
		OverrideRedis:   "redis://127.0.0.1:1",
		CheckFFmpeg:     false,
		CheckBrowser:    false,
		AllowAutoCreate: true,
	})

	if report.AllPassed() {
		t.Fatalf("expected doctor report to fail")
	}

	var found bool
	for _, check := range report.Checks {
		if check.Name == "Redis" {
			found = true
			if check.Status != "failed" {
				t.Fatalf("expected Redis check to fail")
			}
		}
	}
	if !found {
		t.Fatalf("expected Redis check in report")
	}
}

func TestNormalizeDialTargetSupportsURLs(t *testing.T) {
	target, err := normalizeDialTarget("https://example.com")
	if err != nil {
		t.Fatalf("normalizeDialTarget returned error: %v", err)
	}
	if target != "example.com:443" {
		t.Fatalf("unexpected target: %s", target)
	}
}

func TestRenderDoctorReportJSON(t *testing.T) {
	report := doctorReport{
		Checks: []doctorCheck{
			{Name: "配置", Status: "passed", Details: "已加载 gospider.yaml"},
			{Name: "FFmpeg", Status: "warning", Details: "自动探测失败"},
			{Name: "Redis", Status: "failed", Details: "连接失败"},
		},
	}

	output, err := renderDoctorReportJSON(report)
	if err != nil {
		t.Fatalf("renderDoctorReportJSON returned error: %v", err)
	}

	var payload map[string]any
	if err := json.Unmarshal([]byte(output), &payload); err != nil {
		t.Fatalf("invalid json: %v\n%s", err, output)
	}

	if payload["summary"] != "failed" {
		t.Fatalf("expected failed summary, got %#v", payload["summary"])
	}

	if payload["command"] != "doctor" {
		t.Fatalf("expected doctor command, got %#v", payload["command"])
	}

	if payload["runtime"] != "go" {
		t.Fatalf("expected go runtime, got %#v", payload["runtime"])
	}

	if payload["exit_code"] != float64(1) {
		t.Fatalf("expected exit_code 1, got %#v", payload["exit_code"])
	}
	if payload["summary_text"] != "1 passed, 1 warning, 1 failed, 0 skipped" {
		t.Fatalf("expected summary_text, got %#v", payload["summary_text"])
	}

	checks, ok := payload["checks"].([]any)
	if !ok || len(checks) != 3 {
		t.Fatalf("expected 3 checks, got %#v", payload["checks"])
	}
}

func createDoctorTestConfig(t *testing.T, root string) string {
	t.Helper()

	cfg := coreDefaultConfigForDoctor(root)
	configPath := filepath.Join(root, "gospider.yaml")
	if err := cfg.SaveConfig(configPath); err != nil {
		t.Fatalf("failed to save config: %v", err)
	}
	return configPath
}

func coreDefaultConfigForDoctor(root string) *core.Config {
	cfg := core.DefaultConfig()
	cfg.Output.Directory = filepath.Join(root, "outputs")
	cfg.Output.ArtifactDir = filepath.Join(root, "artifacts")
	cfg.Output.DownloadDir = filepath.Join(root, "downloads")
	cfg.Media.OutputDir = filepath.Join(root, "media")
	return cfg
}

func startTCPListener(t *testing.T, handler func(net.Conn)) net.Listener {
	t.Helper()
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("failed to start listener: %v", err)
	}

	t.Cleanup(func() {
		_ = listener.Close()
	})

	go func() {
		for {
			conn, err := listener.Accept()
			if err != nil {
				return
			}
			go handler(conn)
		}
	}()

	return listener
}
