package main

import (
	"bytes"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type fakeBrowserRunner struct {
	title   string
	content string
}

func (f *fakeBrowserRunner) Fetch(url string, screenshot string, htmlPath string, cfg contractConfig) (browserFetchResult, error) {
	if screenshot != "" {
		_ = os.WriteFile(screenshot, []byte("png"), 0644)
	}
	if htmlPath != "" {
		_ = os.WriteFile(htmlPath, []byte(f.content), 0644)
	}
	return browserFetchResult{
		Title:          f.title,
		URL:            url,
		HTMLPath:       htmlPath,
		ScreenshotPath: screenshot,
	}, nil
}

func captureStdout(t *testing.T, fn func()) string {
	t.Helper()
	original := os.Stdout
	reader, writer, err := os.Pipe()
	if err != nil {
		t.Fatalf("pipe failed: %v", err)
	}
	os.Stdout = writer
	defer func() {
		os.Stdout = original
	}()

	done := make(chan string, 1)
	go func() {
		var buf bytes.Buffer
		_, _ = io.Copy(&buf, reader)
		done <- buf.String()
	}()

	fn()

	_ = writer.Close()
	output := <-done
	_ = reader.Close()
	return output
}

func TestConfigCommandWritesSharedContract(t *testing.T) {
	output := filepath.Join(t.TempDir(), "spider-framework.yaml")

	configCommand([]string{"init", "--output", output})

	data, err := os.ReadFile(output)
	if err != nil {
		t.Fatalf("expected config file to exist: %v", err)
	}
	content := string(data)
	if !strings.Contains(content, "runtime: go") {
		t.Fatalf("expected runtime marker, got:\n%s", content)
	}
	if !strings.Contains(content, "checkpoint_dir: artifacts/checkpoints") {
		t.Fatalf("expected storage contract, got:\n%s", content)
	}
	if !strings.Contains(content, "network_targets:") {
		t.Fatalf("expected doctor contract, got:\n%s", content)
	}
	if !strings.Contains(content, "anti_bot:") {
		t.Fatalf("expected anti_bot contract, got:\n%s", content)
	}
	if !strings.Contains(content, "node_reverse:") {
		t.Fatalf("expected node_reverse contract, got:\n%s", content)
	}
}

func TestBrowserCommandFetchUsesInjectedSession(t *testing.T) {
	originalFactory := browserFetchRunnerFactory
	defer func() { browserFetchRunnerFactory = originalFactory }()
	browserFetchRunnerFactory = func() browserFetchRunner {
		return &fakeBrowserRunner{
			title:   "Fake Title",
			content: "<html>fake</html>",
		}
	}

	tempDir := t.TempDir()
	screenshot := filepath.Join(tempDir, "page.png")
	htmlPath := filepath.Join(tempDir, "page.html")

	output := captureStdout(t, func() {
		browserCommand([]string{
			"fetch",
			"--url", "https://example.com",
			"--screenshot", screenshot,
			"--html", htmlPath,
		})
	})

	if !strings.Contains(output, "title: Fake Title") {
		t.Fatalf("expected title output, got: %s", output)
	}

	if _, err := os.Stat(screenshot); err != nil {
		t.Fatalf("expected screenshot file: %v", err)
	}
	data, err := os.ReadFile(htmlPath)
	if err != nil {
		t.Fatalf("expected html file: %v", err)
	}
	if string(data) != "<html>fake</html>" {
		t.Fatalf("unexpected html content: %s", string(data))
	}
}

func TestLoadContractConfigRejectsRuntimeMismatch(t *testing.T) {
	configPath := filepath.Join(t.TempDir(), "wrong-runtime.yaml")
	content := []byte("version: 1\nproject:\n  name: bad-runtime\nruntime: python\ncrawl:\n  urls:\n    - https://example.com\n")
	if err := os.WriteFile(configPath, content, 0644); err != nil {
		t.Fatalf("failed to write config: %v", err)
	}

	_, err := loadContractConfig(configPath)
	if err == nil {
		t.Fatal("expected runtime mismatch to be rejected")
	}
	if !strings.Contains(err.Error(), "runtime mismatch") {
		t.Fatalf("unexpected error: %v", err)
	}
}
