package main

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestAICommandFallsBackToHeuristicsWithoutAPIKey(t *testing.T) {
	t.Setenv("OPENAI_API_KEY", "")
	t.Setenv("AI_API_KEY", "")

	tempDir := t.TempDir()
	htmlPath := filepath.Join(tempDir, "page.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><head><title>Go AI Demo</title><meta name="description" content="Go summary"></head><body><h1>Go AI Demo</h1></body></html>`), 0o644); err != nil {
		t.Fatalf("write html fixture: %v", err)
	}

	oldStdout := os.Stdout
	reader, writer, err := os.Pipe()
	if err != nil {
		t.Fatalf("pipe stdout: %v", err)
	}
	os.Stdout = writer

	exitCode := aiCommand([]string{
		"--html-file", htmlPath,
		"--instructions", "提取标题和摘要",
		"--schema-json", `{"type":"object","properties":{"title":{"type":"string"},"summary":{"type":"string"},"url":{"type":"string"}}}`,
	})

	_ = writer.Close()
	os.Stdout = oldStdout
	output, _ := io.ReadAll(reader)

	if exitCode != 0 {
		t.Fatalf("expected zero exit code, got %d with output: %s", exitCode, string(output))
	}

	var payload map[string]any
	if err := json.Unmarshal(output, &payload); err != nil {
		t.Fatalf("parse json output: %v\n%s", err, string(output))
	}

	if payload["command"] != "ai" {
		t.Fatalf("expected ai command, got %#v", payload["command"])
	}
	if payload["runtime"] != "go" {
		t.Fatalf("expected go runtime, got %#v", payload["runtime"])
	}
	if payload["engine"] != "heuristic-fallback" {
		t.Fatalf("expected heuristic fallback engine, got %#v", payload["engine"])
	}

	result, ok := payload["result"].(map[string]any)
	if !ok {
		t.Fatalf("expected result object, got %#v", payload["result"])
	}
	if result["title"] != "Go AI Demo" {
		t.Fatalf("expected extracted title, got %#v", result["title"])
	}
	if result["summary"] != "Go summary" {
		t.Fatalf("expected extracted summary, got %#v", result["summary"])
	}
}

func TestScrapyGenspiderGeneratesAITemplate(t *testing.T) {
	projectDir := t.TempDir()
	manifestPath := filepath.Join(projectDir, "scrapy-project.json")
	if err := os.WriteFile(manifestPath, []byte("{\"name\":\"demo\",\"runtime\":\"go\"}\n"), 0o644); err != nil {
		t.Fatalf("write manifest: %v", err)
	}

	exitCode := scrapyCommand([]string{
		"genspider",
		"--project", projectDir,
		"--name", "demo_ai",
		"--domain", "example.com",
		"--ai",
	})
	if exitCode != 0 {
		t.Fatalf("expected zero exit code, got %d", exitCode)
	}

	content, err := os.ReadFile(filepath.Join(projectDir, "spiders", "demo_ai.go"))
	if err != nil {
		t.Fatalf("read generated spider: %v", err)
	}
	text := string(content)
	if !strings.Contains(text, `spiderai "gospider/ai"`) {
		t.Fatalf("expected AI import in template, got:\n%s", text)
	}
	if !strings.Contains(text, "ExtractStructured") {
		t.Fatalf("expected AI extraction call in template, got:\n%s", text)
	}
	if !strings.Contains(text, "LoadAIProjectAssets") {
		t.Fatalf("expected project helper usage in template, got:\n%s", text)
	}
}

func TestScrapyPlanAIWritesPlanFiles(t *testing.T) {
	projectDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(projectDir, "scrapy-project.json"), []byte("{\"name\":\"demo\",\"runtime\":\"go\",\"url\":\"https://example.com\"}\n"), 0o644); err != nil {
		t.Fatalf("write manifest: %v", err)
	}
	htmlPath := filepath.Join(projectDir, "page.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><head><title>Plan Demo</title><meta name="description" content="Plan summary"></head><body><article>hello</article></body></html>`), 0o644); err != nil {
		t.Fatalf("write html fixture: %v", err)
	}

	exitCode := scrapyCommand([]string{
		"plan-ai",
		"--project", projectDir,
		"--html-file", htmlPath,
		"--name", "planned_ai",
	})
	if exitCode != 0 {
		t.Fatalf("expected zero exit code, got %d", exitCode)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "ai-plan.json")); err != nil {
		t.Fatalf("expected ai-plan.json: %v", err)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "ai-schema.json")); err != nil {
		t.Fatalf("expected ai-schema.json: %v", err)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "ai-blueprint.json")); err != nil {
		t.Fatalf("expected ai-blueprint.json: %v", err)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "ai-extract-prompt.txt")); err != nil {
		t.Fatalf("expected ai-extract-prompt.txt: %v", err)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "ai-auth.json")); err != nil {
		t.Fatalf("expected ai-auth.json: %v", err)
	}
	blueprint, err := os.ReadFile(filepath.Join(projectDir, "ai-blueprint.json"))
	if err != nil {
		t.Fatalf("read blueprint: %v", err)
	}
	if !strings.Contains(string(blueprint), `"crawler_type": "static_detail"`) || !strings.Contains(string(blueprint), `"job_templates":`) {
		t.Fatalf("expected crawler metadata in blueprint, got:\n%s", string(blueprint))
	}
}

func TestScrapyScaffoldAIWritesPlanSchemaAndSpider(t *testing.T) {
	projectDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(projectDir, "scrapy-project.json"), []byte("{\"name\":\"demo\",\"runtime\":\"go\",\"url\":\"https://example.com\"}\n"), 0o644); err != nil {
		t.Fatalf("write manifest: %v", err)
	}
	htmlPath := filepath.Join(projectDir, "page.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><head><title>Scaffold Demo</title><meta name="description" content="Scaffold summary"></head><body><article>hello</article></body></html>`), 0o644); err != nil {
		t.Fatalf("write html fixture: %v", err)
	}

	exitCode := scrapyCommand([]string{
		"scaffold-ai",
		"--project", projectDir,
		"--html-file", htmlPath,
		"--name", "scaffold_ai",
	})
	if exitCode != 0 {
		t.Fatalf("expected zero exit code, got %d", exitCode)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "ai-plan.json")); err != nil {
		t.Fatalf("expected ai-plan.json: %v", err)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "ai-schema.json")); err != nil {
		t.Fatalf("expected ai-schema.json: %v", err)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "ai-blueprint.json")); err != nil {
		t.Fatalf("expected ai-blueprint.json: %v", err)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "ai-extract-prompt.txt")); err != nil {
		t.Fatalf("expected ai-extract-prompt.txt: %v", err)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "ai-auth.json")); err != nil {
		t.Fatalf("expected ai-auth.json: %v", err)
	}
	blueprint, err := os.ReadFile(filepath.Join(projectDir, "ai-blueprint.json"))
	if err != nil {
		t.Fatalf("read blueprint: %v", err)
	}
	if !strings.Contains(string(blueprint), `"crawler_type": "static_detail"`) || !strings.Contains(string(blueprint), `"job_templates":`) {
		t.Fatalf("expected crawler metadata in blueprint, got:\n%s", string(blueprint))
	}
	content, err := os.ReadFile(filepath.Join(projectDir, "spiders", "scaffold_ai.go"))
	if err != nil {
		t.Fatalf("expected AI spider template: %v", err)
	}
	if !strings.Contains(string(content), "gospider-ai") {
		t.Fatalf("expected generated AI spider template, got:\n%s", string(content))
	}
	if !strings.Contains(string(content), "ApplyAIStartMeta") {
		t.Fatalf("expected project helper start meta support in generated AI spider, got:\n%s", string(content))
	}
}

func TestScrapySyncAIWritesAIJob(t *testing.T) {
	projectDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(projectDir, "scrapy-project.json"), []byte("{\"name\":\"demo\",\"runtime\":\"go\",\"url\":\"https://example.com\"}\n"), 0o644); err != nil {
		t.Fatalf("write manifest: %v", err)
	}
	htmlPath := filepath.Join(projectDir, "page.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><head><title>Sync Demo</title><meta name="description" content="Sync summary"></head><body><article>hello</article></body></html>`), 0o644); err != nil {
		t.Fatalf("write html fixture: %v", err)
	}

	exitCode := scrapyCommand([]string{
		"sync-ai",
		"--project", projectDir,
		"--html-file", htmlPath,
		"--name", "sync_ai",
	})
	if exitCode != 0 {
		t.Fatalf("expected zero exit code, got %d", exitCode)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "ai-job.json")); err != nil {
		t.Fatalf("expected ai-job.json: %v", err)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "ai-blueprint.json")); err != nil {
		t.Fatalf("expected ai-blueprint.json: %v", err)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "ai-auth.json")); err != nil {
		t.Fatalf("expected ai-auth.json: %v", err)
	}
}

func TestScrapyAuthValidateReportsAuthenticatedForNonLoginFixture(t *testing.T) {
	projectDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(projectDir, "scrapy-project.json"), []byte("{\"name\":\"demo\",\"runtime\":\"go\",\"url\":\"https://example.com\"}\n"), 0o644); err != nil {
		t.Fatalf("write manifest: %v", err)
	}
	htmlPath := filepath.Join(projectDir, "page.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><head><title>Dashboard</title></head><body><article>hello</article></body></html>`), 0o644); err != nil {
		t.Fatalf("write html fixture: %v", err)
	}

	oldStdout := os.Stdout
	reader, writer, err := os.Pipe()
	if err != nil {
		t.Fatalf("pipe stdout: %v", err)
	}
	os.Stdout = writer
	exitCode := scrapyCommand([]string{
		"auth-validate",
		"--project", projectDir,
		"--html-file", htmlPath,
	})
	_ = writer.Close()
	os.Stdout = oldStdout
	output, _ := io.ReadAll(reader)

	if exitCode != 0 {
		t.Fatalf("expected zero exit code, got %d with output: %s", exitCode, string(output))
	}
	var payload map[string]any
	if err := json.Unmarshal(output, &payload); err != nil {
		t.Fatalf("parse json output: %v\n%s", err, string(output))
	}
	if payload["command"] != "scrapy auth-validate" {
		t.Fatalf("expected auth-validate command, got %#v", payload["command"])
	}
	if payload["authenticated"] != true {
		t.Fatalf("expected authenticated=true, got %#v", payload["authenticated"])
	}
}

type fakeBrowserFetchRunner struct{}

func (fakeBrowserFetchRunner) Fetch(url string, screenshot string, htmlPath string, cfg contractConfig) (browserFetchResult, error) {
	if err := os.WriteFile(cfg.Browser.StorageStateFile, []byte("{}"), 0o644); err != nil {
		return browserFetchResult{}, err
	}
	if err := os.WriteFile(cfg.Browser.CookiesFile, []byte("[]"), 0o644); err != nil {
		return browserFetchResult{}, err
	}
	if htmlPath != "" {
		if err := os.MkdirAll(filepath.Dir(htmlPath), 0o755); err == nil {
			_ = os.WriteFile(htmlPath, []byte("<html><title>Auth Capture</title></html>"), 0o644)
		}
	}
	return browserFetchResult{Title: "Auth Capture", URL: url, HTMLPath: htmlPath}, nil
}

type reverseAwareFakeBrowserFetchRunner struct{}

func (reverseAwareFakeBrowserFetchRunner) Fetch(url string, screenshot string, htmlPath string, cfg contractConfig) (browserFetchResult, error) {
	if err := os.WriteFile(cfg.Browser.StorageStateFile, []byte("{}"), 0o644); err != nil {
		return browserFetchResult{}, err
	}
	if err := os.WriteFile(cfg.Browser.CookiesFile, []byte("[]"), 0o644); err != nil {
		return browserFetchResult{}, err
	}
	if htmlPath != "" {
		if err := os.MkdirAll(filepath.Dir(htmlPath), 0o755); err == nil {
			_ = os.WriteFile(htmlPath, []byte("<html><title>Auth Capture</title></html>"), 0o644)
		}
	}
	return browserFetchResult{Title: "Auth Capture", URL: url, HTMLPath: htmlPath}, nil
}

func TestScrapyAuthCaptureWritesAuthAssets(t *testing.T) {
	projectDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(projectDir, "scrapy-project.json"), []byte("{\"name\":\"demo\",\"runtime\":\"go\",\"url\":\"https://example.com\"}\n"), 0o644); err != nil {
		t.Fatalf("write manifest: %v", err)
	}
	if err := os.WriteFile(filepath.Join(projectDir, "ai-auth.json"), []byte("{\"actions\":[{\"type\":\"assert\",\"url_contains\":\"/dashboard\"},{\"type\":\"save_as\",\"value\":\"url\",\"save_as\":\"final_url\"}]}"), 0o644); err != nil {
		t.Fatalf("write auth seed: %v", err)
	}
	oldFactory := browserFetchRunnerFactory
	browserFetchRunnerFactory = func() browserFetchRunner { return fakeBrowserFetchRunner{} }
	defer func() { browserFetchRunnerFactory = oldFactory }()

	exitCode := scrapyCommand([]string{
		"auth-capture",
		"--project", projectDir,
		"--url", "https://example.com",
	})
	if exitCode != 0 {
		t.Fatalf("expected zero exit code, got %d", exitCode)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "ai-auth.json")); err != nil {
		t.Fatalf("expected ai-auth.json: %v", err)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "artifacts", "auth", "auth-state.json")); err != nil {
		t.Fatalf("expected state file: %v", err)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "artifacts", "auth", "auth-cookies.json")); err != nil {
		t.Fatalf("expected cookies file: %v", err)
	}
	authPayload, err := os.ReadFile(filepath.Join(projectDir, "ai-auth.json"))
	if err != nil {
		t.Fatalf("read ai-auth.json: %v", err)
	}
	text := string(authPayload)
	if !strings.Contains(text, "\"actions\"") || !strings.Contains(text, "\"final_url\"") || !strings.Contains(text, "\"url_contains\"") {
		t.Fatalf("expected actions to be preserved in ai-auth.json, got:\n%s", text)
	}
	if !strings.Contains(text, "\"action_examples\"") {
		t.Fatalf("expected action_examples in ai-auth.json, got:\n%s", text)
	}
}

func TestScrapyAuthCaptureCanStoreReverseRuntime(t *testing.T) {
	projectDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(projectDir, "scrapy-project.json"), []byte("{\"name\":\"demo\",\"runtime\":\"go\",\"url\":\"https://example.com\"}\n"), 0o644); err != nil {
		t.Fatalf("write manifest: %v", err)
	}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		switch r.URL.Path {
		case "/api/anti-bot/detect":
			_, _ = w.Write([]byte(`{"success":true,"signals":["vendor:test"],"level":"medium"}`))
		case "/api/anti-bot/profile":
			_, _ = w.Write([]byte(`{"success":true,"signals":["vendor:test"],"level":"medium"}`))
		case "/api/fingerprint/spoof":
			_, _ = w.Write([]byte(`{"success":true,"fingerprint":{"ua":"mock"}}`))
		case "/api/tls/fingerprint":
			_, _ = w.Write([]byte(`{"success":true,"fingerprint":{"ja3":"mock-ja3"}}`))
		case "/api/crypto/analyze":
			_, _ = w.Write([]byte(`{"success":true,"cryptoTypes":[{"name":"AES","confidence":0.9}]}`))
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()
	seed := `{"actions":[],"capture_reverse_profile":true,"node_reverse_base_url":"` + server.URL + `"}`
	if err := os.WriteFile(filepath.Join(projectDir, "ai-auth.json"), []byte(seed), 0o644); err != nil {
		t.Fatalf("write auth seed: %v", err)
	}
	oldFactory := browserFetchRunnerFactory
	browserFetchRunnerFactory = func() browserFetchRunner { return reverseAwareFakeBrowserFetchRunner{} }
	defer func() { browserFetchRunnerFactory = oldFactory }()

	exitCode := scrapyCommand([]string{
		"auth-capture",
		"--project", projectDir,
		"--url", "https://example.com",
	})
	if exitCode != 0 {
		t.Fatalf("expected zero exit code, got %d", exitCode)
	}
	authPayload, err := os.ReadFile(filepath.Join(projectDir, "ai-auth.json"))
	if err != nil {
		t.Fatalf("read ai-auth.json: %v", err)
	}
	text := string(authPayload)
	if !strings.Contains(text, "\"reverse_runtime\"") || !strings.Contains(text, "\"mock-ja3\"") || !strings.Contains(text, "\"crypto_analysis\"") || !strings.Contains(text, "\"AES\"") {
		t.Fatalf("expected reverse_runtime summary in ai-auth.json, got:\n%s", text)
	}
}
