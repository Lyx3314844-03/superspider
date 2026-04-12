package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"gospider/core"
)

func TestLoadJobSpecFromFile(t *testing.T) {
	path := filepath.Join(t.TempDir(), "job.json")
	if err := os.WriteFile(path, []byte(`{
  "name": "job-http",
  "runtime": "http",
  "target": {
    "url": "https://example.com"
  },
  "output": {
    "format": "json"
  }
}`), 0644); err != nil {
		t.Fatalf("failed to write temp job: %v", err)
	}

	job, err := loadJobSpecFromFile(path)
	if err != nil {
		t.Fatalf("expected job to load: %v", err)
	}
	if job.Name != "job-http" {
		t.Fatalf("unexpected job name: %s", job.Name)
	}
	if job.Output.Path == "" {
		t.Fatal("expected default output path to be filled")
	}
}

func TestLoadJobSpecFromFileNormalizesBrowserActions(t *testing.T) {
	path := filepath.Join(t.TempDir(), "job-browser.json")
	if err := os.WriteFile(path, []byte(`{
  "name": "job-browser",
  "runtime": "browser",
  "target": {
    "url": "https://example.com"
  },
  "actions": [
    {
      "type": "goto",
      "url": "https://example.com"
    }
  ],
  "output": {
    "format": "json"
  }
}`), 0644); err != nil {
		t.Fatalf("failed to write temp browser job: %v", err)
	}

	job, err := loadJobSpecFromFile(path)
	if err != nil {
		t.Fatalf("expected browser job to load: %v", err)
	}
	if len(job.Actions) != 1 {
		t.Fatalf("expected top-level actions to be preserved, got %d", len(job.Actions))
	}
	if len(job.Browser.Actions) != 1 {
		t.Fatalf("expected browser actions to be normalized, got %d", len(job.Browser.Actions))
	}
	if job.Browser.Actions[0].Type != "goto" {
		t.Fatalf("expected goto action, got %#v", job.Browser.Actions[0])
	}
}

func TestValidateContractConfigRejectsUnsupportedDeclarativeComponent(t *testing.T) {
	cfg := defaultContractConfig()
	cfg.Scrapy.Pipelines = []string{"unknown-component"}

	err := validateContractConfig(cfg, "go")
	if err == nil {
		t.Fatal("expected unsupported declarative component to fail validation")
	}
	if !strings.Contains(err.Error(), "scrapy.pipelines contains unsupported component") {
		t.Fatalf("unexpected validation error: %v", err)
	}
}

func TestPrintCapabilitiesIncludesIntegratedRuntimes(t *testing.T) {
	originalStdout := os.Stdout
	reader, writer, err := os.Pipe()
	if err != nil {
		t.Fatalf("pipe failed: %v", err)
	}
	os.Stdout = writer
	defer func() { os.Stdout = originalStdout }()

	capabilitiesCommand()
	_ = writer.Close()

	var buf bytes.Buffer
	_, _ = buf.ReadFrom(reader)

	var payload map[string]interface{}
	if err := json.Unmarshal(buf.Bytes(), &payload); err != nil {
		t.Fatalf("expected json output: %v", err)
	}

	runtimes, ok := payload["runtimes"].([]interface{})
	if !ok || len(runtimes) == 0 {
		t.Fatalf("expected runtimes in payload: %#v", payload)
	}
	if payload["command"] != "capabilities" || payload["runtime"] != "go" {
		t.Fatalf("expected shared capability contract fields: %#v", payload)
	}
	entrypoints, ok := payload["entrypoints"].([]interface{})
	if !ok || len(entrypoints) == 0 {
		t.Fatalf("expected entrypoints in payload: %#v", payload)
	}
	if sharedContracts, ok := payload["shared_contracts"].([]interface{}); !ok || len(sharedContracts) == 0 {
		t.Fatalf("expected shared_contracts in payload: %#v", payload)
	}
	if kernelContracts, ok := payload["kernel_contracts"].(map[string]interface{}); !ok || len(kernelContracts) == 0 {
		t.Fatalf("expected kernel_contracts in payload: %#v", payload)
	}
	if operatorProducts, ok := payload["operator_products"].(map[string]interface{}); !ok || len(operatorProducts) == 0 {
		t.Fatalf("expected operator_products in payload: %#v", payload)
	}
	if observability, ok := payload["observability"].([]interface{}); !ok || len(observability) == 0 {
		t.Fatalf("expected observability in payload: %#v", payload)
	}
	var hasUltimate bool
	var hasCurl bool
	var hasNodeReverse bool
	var hasAntiBot bool
	var hasScrapy bool
	var hasJobdir bool
	var hasHttpCache bool
	var hasConsole bool
	for _, entrypoint := range entrypoints {
		if entrypoint == "ultimate" {
			hasUltimate = true
		}
		if entrypoint == "curl" {
			hasCurl = true
		}
		if entrypoint == "scrapy" {
			hasScrapy = true
		}
		if entrypoint == "jobdir" {
			hasJobdir = true
		}
		if entrypoint == "http-cache" {
			hasHttpCache = true
		}
		if entrypoint == "console" {
			hasConsole = true
		}
		if entrypoint == "node-reverse" {
			hasNodeReverse = true
		}
		if entrypoint == "anti-bot" {
			hasAntiBot = true
		}
	}
	if !hasUltimate {
		t.Fatalf("expected ultimate entrypoint in payload: %#v", payload)
	}
	if !hasCurl {
		t.Fatalf("expected curl entrypoint in payload: %#v", payload)
	}
	if !hasScrapy {
		t.Fatalf("expected scrapy entrypoint in payload: %#v", payload)
	}
	if !hasJobdir || !hasHttpCache || !hasConsole {
		t.Fatalf("expected shared operator entrypoints in payload: %#v", payload)
	}
	if !hasNodeReverse || !hasAntiBot {
		t.Fatalf("expected anti-bot and node-reverse entrypoints in payload: %#v", payload)
	}
	if !strings.Contains(buf.String(), "runtime.dispatch") {
		t.Fatalf("expected integrated modules in capabilities output: %s", buf.String())
	}
}

func TestPrintUsageMentionsUltimateCommand(t *testing.T) {
	output := captureStdout(t, func() {
		printUsage()
	})

	if !strings.Contains(output, "ultimate") {
		t.Fatalf("expected usage to mention ultimate command, got: %s", output)
	}
	if !strings.Contains(output, "curl convert") {
		t.Fatalf("expected usage to mention curl command, got: %s", output)
	}
	if !strings.Contains(output, "jobdir") || !strings.Contains(output, "http-cache") || !strings.Contains(output, "console") {
		t.Fatalf("expected usage to mention shared operator commands, got: %s", output)
	}
	if !strings.Contains(output, "node-reverse") || !strings.Contains(output, "anti-bot") {
		t.Fatalf("expected usage to mention anti-bot and node-reverse commands, got: %s", output)
	}
}

func TestCurlCommandConvertsToRestyTemplate(t *testing.T) {
	output := captureStdout(t, func() {
		if code := curlCommand([]string{
			"convert",
			"--command",
			`curl -X GET "https://example.com/api" -H "Accept: application/json"`,
			"--target",
			"resty",
		}); code != 0 {
			t.Fatalf("expected curl command to succeed, got %d", code)
		}
	})

	if !strings.Contains(output, `"command": "curl convert"`) {
		t.Fatalf("unexpected curl convert output: %s", output)
	}
	if !strings.Contains(output, `"target": "resty"`) {
		t.Fatalf("expected resty target in output: %s", output)
	}
	if !strings.Contains(output, "resty.New") || !strings.Contains(output, "https://example.com/api") {
		t.Fatalf("expected generated resty code, got: %s", output)
	}
}

func TestNodeReverseHealthCommandAgainstMockServer(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/health" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"status":"ok"}`))
	}))
	defer server.Close()

	output := captureStdout(t, func() {
		_ = nodeReverseHealthCommand([]string{"--base-url", server.URL})
	})

	if !strings.Contains(output, `"command": "node-reverse health"`) || !strings.Contains(output, `"healthy": true`) {
		t.Fatalf("unexpected node-reverse health output: %s", output)
	}
}

func TestNodeReverseDetectCommandAgainstMockServer(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/anti-bot/detect" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"success":true,"signals":["vendor:cloudflare"],"level":"high"}`))
	}))
	defer server.Close()

	htmlPath := filepath.Join(t.TempDir(), "blocked.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Blocked</title></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}

	output := captureStdout(t, func() {
		_ = nodeReverseDetectCommand([]string{"--base-url", server.URL, "--html-file", htmlPath, "--status-code", "403"})
	})

	if !strings.Contains(output, `"signals": [`) || !strings.Contains(output, `vendor:cloudflare`) {
		t.Fatalf("unexpected node-reverse detect output: %s", output)
	}
}

func TestNodeReverseFingerprintSpoofCommandAgainstMockServer(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/fingerprint/spoof" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"success":true,"browser":"chrome","platform":"windows","fingerprint":{"userAgent":"mock"}}`))
	}))
	defer server.Close()

	output := captureStdout(t, func() {
		_ = nodeReverseFingerprintSpoofCommand([]string{"--base-url", server.URL, "--browser", "chrome", "--platform", "windows"})
	})

	if !strings.Contains(output, `"browser": "chrome"`) || !strings.Contains(output, `"platform": "windows"`) {
		t.Fatalf("unexpected node-reverse fingerprint-spoof output: %s", output)
	}
}

func TestNodeReverseTLSFingerprintCommandAgainstMockServer(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/tls/fingerprint" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"success":true,"browser":"chrome","version":"120","fingerprint":{"ja3":"mock-ja3"}}`))
	}))
	defer server.Close()

	output := captureStdout(t, func() {
		_ = nodeReverseTLSFingerprintCommand([]string{"--base-url", server.URL, "--browser", "chrome", "--version", "120"})
	})

	if !strings.Contains(output, `"version": "120"`) || !strings.Contains(output, `mock-ja3`) {
		t.Fatalf("unexpected node-reverse tls-fingerprint output: %s", output)
	}
}

func TestAntiBotProfileCommandDetectsBlockedFixture(t *testing.T) {
	htmlPath := filepath.Join(t.TempDir(), "blocked.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Blocked</title><body>Access denied. captcha required.</body></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}

	output := captureStdout(t, func() {
		_ = antiBotProfileCommand([]string{"--html-file", htmlPath, "--status-code", "403"})
	})

	if !strings.Contains(output, `"command": "anti-bot profile"`) || !strings.Contains(output, `"blocked": true`) {
		t.Fatalf("unexpected anti-bot profile output: %s", output)
	}
	if !strings.Contains(output, "captcha") {
		t.Fatalf("expected anti-bot signals in output: %s", output)
	}
}

func TestProfileSiteCommandBuildsSiteProfile(t *testing.T) {
	htmlPath := filepath.Join(t.TempDir(), "detail.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Demo</title><article>author price</article></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		switch r.URL.Path {
		case "/api/anti-bot/detect":
			_, _ = w.Write([]byte(`{"success":true,"signals":["vendor:test"]}`))
		case "/api/anti-bot/profile":
			_, _ = w.Write([]byte(`{"success":true,"signals":["vendor:test"],"level":"medium"}`))
		case "/api/fingerprint/spoof":
			_, _ = w.Write([]byte(`{"success":true,"browser":"chrome"}`))
		case "/api/tls/fingerprint":
			_, _ = w.Write([]byte(`{"success":true,"fingerprint":{"ja3":"mock-ja3"}}`))
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	output := captureStdout(t, func() {
		_ = profileSiteCommand([]string{"--html-file", htmlPath, "--base-url", server.URL})
	})

	if !strings.Contains(output, `"command": "profile-site"`) || !strings.Contains(output, `"page_type": "detail"`) {
		t.Fatalf("unexpected profile-site output: %s", output)
	}
	if !strings.Contains(output, `"framework": "gospider"`) {
		t.Fatalf("expected framework marker in profile-site output: %s", output)
	}
	if !strings.Contains(output, `"recommended_runtime": "python"`) {
		t.Fatalf("expected recommended runtime in output: %s", output)
	}
	if !strings.Contains(output, `"reverse":`) || !strings.Contains(output, `mock-ja3`) {
		t.Fatalf("expected reverse summary in output: %s", output)
	}
}

func TestSitemapDiscoverCommandReadsLocalSitemap(t *testing.T) {
	sitemapPath := filepath.Join(t.TempDir(), "sitemap.xml")
	if err := os.WriteFile(sitemapPath, []byte(`<?xml version="1.0"?><urlset><url><loc>https://example.com/a</loc></url><url><loc>https://example.com/b</loc></url></urlset>`), 0644); err != nil {
		t.Fatalf("failed to write sitemap fixture: %v", err)
	}

	output := captureStdout(t, func() {
		_ = sitemapDiscoverCommand([]string{"--sitemap-file", sitemapPath})
	})

	if !strings.Contains(output, `"command": "sitemap-discover"`) || !strings.Contains(output, `"url_count": 2`) {
		t.Fatalf("unexpected sitemap-discover output: %s", output)
	}
}

func TestPluginsListCommandReadsManifest(t *testing.T) {
	manifestPath := filepath.Join(t.TempDir(), "manifest.json")
	if err := os.WriteFile(manifestPath, []byte(`{"entrypoints":[{"id":"shared-cli"},{"id":"web-control-plane"}]}`), 0644); err != nil {
		t.Fatalf("failed to write manifest fixture: %v", err)
	}

	output := captureStdout(t, func() {
		_ = pluginsCommand([]string{"list", "--manifest", manifestPath})
	})

	if !strings.Contains(output, `"command": "plugins list"`) || !strings.Contains(output, `"shared-cli"`) {
		t.Fatalf("unexpected plugins output: %s", output)
	}
}

func TestPluginsRunDispatchesBuiltInPlugin(t *testing.T) {
	htmlPath := filepath.Join(t.TempDir(), "page.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Demo</title></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}

	output := captureStdout(t, func() {
		_ = pluginsRunCommand([]string{"--plugin", "selector-studio", "--html-file", htmlPath, "--type", "css", "--expr", "title"})
	})

	if !strings.Contains(output, `"command": "selector-studio"`) {
		t.Fatalf("unexpected plugins run output: %s", output)
	}
}

func TestSelectorStudioCommandExtractsValues(t *testing.T) {
	htmlPath := filepath.Join(t.TempDir(), "page.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Demo</title><article><h1>Title</h1></article></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}

	output := captureStdout(t, func() {
		_ = selectorStudioCommand([]string{"--html-file", htmlPath, "--type", "css", "--expr", "title"})
	})

	if !strings.Contains(output, `"command": "selector-studio"`) || !strings.Contains(output, `"count": 1`) {
		t.Fatalf("unexpected selector-studio output: %s", output)
	}
	if !strings.Contains(output, `"framework": "gospider"`) {
		t.Fatalf("expected framework marker in selector-studio output: %s", output)
	}
}

func TestScrapyDemoCommandExportsResults(t *testing.T) {
	htmlPath := filepath.Join(t.TempDir(), "page.html")
	outputPath := filepath.Join(t.TempDir(), "scrapy-demo.json")
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Demo</title></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}

	output := captureStdout(t, func() {
		_ = scrapyCommand([]string{"demo", "--url", "https://example.com", "--html-file", htmlPath, "--output", outputPath})
	})

	if !strings.Contains(output, `"command": "scrapy demo"`) {
		t.Fatalf("unexpected scrapy demo output: %s", output)
	}
	content, err := os.ReadFile(outputPath)
	if err != nil {
		t.Fatalf("expected scrapy export file: %v", err)
	}
	if !strings.Contains(string(content), "Demo") {
		t.Fatalf("expected scrapy export content, got %s", string(content))
	}
}

func TestScrapyRunCommandReadsProjectManifest(t *testing.T) {
	projectDir := t.TempDir()
	htmlPath := filepath.Join(projectDir, "page.html")
	outputPath := filepath.Join(projectDir, "artifacts", "exports", "items.json")
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Manifest Demo</title></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}
	if err := os.WriteFile(filepath.Join(projectDir, "scrapy-project.json"), []byte(`{
  "name": "demo-project",
  "runtime": "go",
  "entry": "main.go",
  "url": "https://example.com",
  "output": "artifacts/exports/items.json"
}`), 0644); err != nil {
		t.Fatalf("failed to write scrapy project manifest: %v", err)
	}

	output := captureStdout(t, func() {
		_ = scrapyCommand([]string{"run", "--project", projectDir, "--html-file", htmlPath})
	})

	if !strings.Contains(output, `"command": "scrapy run"`) {
		t.Fatalf("unexpected scrapy run output: %s", output)
	}
	content, err := os.ReadFile(outputPath)
	if err != nil {
		t.Fatalf("expected scrapy project export file: %v", err)
	}
	if !strings.Contains(string(content), "Manifest Demo") {
		t.Fatalf("expected scrapy project export content, got %s", string(content))
	}
}

func TestScrapyInitCommandCreatesProject(t *testing.T) {
	projectDir := filepath.Join(t.TempDir(), "init-project")

	output := captureStdout(t, func() {
		_ = scrapyCommand([]string{"init", "--path", projectDir})
	})

	if !strings.Contains(output, `"command": "scrapy init"`) {
		t.Fatalf("unexpected scrapy init output: %s", output)
	}
	for _, relative := range []string{"scrapy-project.json", "main.go", "spider-framework.yaml"} {
		if _, err := os.Stat(filepath.Join(projectDir, relative)); err != nil {
			t.Fatalf("expected generated file %s: %v", relative, err)
		}
	}
}

func TestScrapyListValidateAndGenspiderCommands(t *testing.T) {
	projectDir := filepath.Join(t.TempDir(), "init-project")
	_ = scrapyCommand([]string{"init", "--path", projectDir})
	htmlPath := filepath.Join(projectDir, "page.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Selected Spider</title></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}

	listOutput := captureStdout(t, func() {
		_ = scrapyCommand([]string{"list", "--project", projectDir})
	})
	if !strings.Contains(listOutput, `"command": "scrapy list"`) {
		t.Fatalf("unexpected scrapy list output: %s", listOutput)
	}
	if !strings.Contains(listOutput, `"runner": "http"`) {
		t.Fatalf("expected resolved runner in list output: %s", listOutput)
	}
	if !strings.Contains(listOutput, `"url_source": "scrapy.spiders"`) {
		t.Fatalf("expected url source in list output: %s", listOutput)
	}

	validateOutput := captureStdout(t, func() {
		_ = scrapyCommand([]string{"validate", "--project", projectDir})
	})
	if !strings.Contains(validateOutput, `"summary": "passed"`) {
		t.Fatalf("unexpected scrapy validate output: %s", validateOutput)
	}

	genspiderOutput := captureStdout(t, func() {
		_ = scrapyCommand([]string{"genspider", "--name", "news", "--domain", "example.com", "--project", projectDir})
	})
	if !strings.Contains(genspiderOutput, `"command": "scrapy genspider"`) {
		t.Fatalf("unexpected scrapy genspider output: %s", genspiderOutput)
	}
	if _, err := os.Stat(filepath.Join(projectDir, "spiders", "news.go")); err != nil {
		t.Fatalf("expected generated spider file: %v", err)
	}

	runOutput := captureStdout(t, func() {
		_ = scrapyCommand([]string{"run", "--project", projectDir, "--spider", "news", "--html-file", htmlPath})
	})
	if !strings.Contains(runOutput, `"spider": "news"`) || !strings.Contains(runOutput, `"resolved_runner": "http"`) {
		t.Fatalf("expected selected spider in run output: %s", runOutput)
	}
}

func TestScrapyRunUsesRealProjectSpiderImplementation(t *testing.T) {
	projectDir := filepath.Join(t.TempDir(), "real-project")
	_ = scrapyCommand([]string{"init", "--path", projectDir})

	htmlPath := filepath.Join(projectDir, "page.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Real Project Demo</title></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}

	output := captureStdout(t, func() {
		_ = scrapyCommand([]string{"run", "--project", projectDir, "--spider", "demo", "--html-file", htmlPath})
	})

	if !strings.Contains(output, `"project_runner": "built-in-metadata-runner"`) || !strings.Contains(output, `"runner": "http"`) || !strings.Contains(output, `"spider": "demo"`) {
		t.Fatalf("expected built-in metadata project runner payload, got: %s", output)
	}
	if !strings.Contains(output, `"plugins": [`) || !strings.Contains(output, `field-injector`) || !strings.Contains(output, `"settings_source":`) {
		t.Fatalf("expected assembly summary in source project payload, got: %s", output)
	}
	if !strings.Contains(output, `"runner_source": "html-fixture"`) {
		t.Fatalf("expected runner source in payload, got: %s", output)
	}
	if !strings.Contains(output, `"url_source": "html-fixture"`) {
		t.Fatalf("expected url source in payload, got: %s", output)
	}

	content, err := os.ReadFile(filepath.Join(projectDir, "artifacts", "exports", "demo.json"))
	if err != nil {
		t.Fatalf("expected real project output file: %v", err)
	}
	if !strings.Contains(string(content), "Real Project Demo") {
		t.Fatalf("expected real project spider output, got %s", string(content))
	}
	if !strings.Contains(string(content), "\"plugin\": \"project-plugin\"") {
		t.Fatalf("expected project plugin mutation, got %s", string(content))
	}
}

func TestScrapyRunProjectIncludesReverseSummaryWhenConfigured(t *testing.T) {
	projectDir := filepath.Join(t.TempDir(), "reverse-project")
	_ = scrapyCommand([]string{"init", "--path", projectDir})

	reverseServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		switch r.URL.Path {
		case "/api/anti-bot/detect":
			_, _ = w.Write([]byte(`{"success":true,"signals":["vendor:test"]}`))
		case "/api/anti-bot/profile":
			_, _ = w.Write([]byte(`{"success":true,"signals":["vendor:test"],"level":"medium"}`))
		case "/api/fingerprint/spoof":
			_, _ = w.Write([]byte(`{"success":true,"browser":"chrome"}`))
		case "/api/tls/fingerprint":
			_, _ = w.Write([]byte(`{"success":true,"fingerprint":{"ja3":"mock-ja3"}}`))
		default:
			http.NotFound(w, r)
		}
	}))
	defer reverseServer.Close()

	configPath := filepath.Join(projectDir, "spider-framework.yaml")
	configBytes, err := os.ReadFile(configPath)
	if err != nil {
		t.Fatalf("failed to read config: %v", err)
	}
	updatedConfig := strings.ReplaceAll(string(configBytes), "http://localhost:3000", reverseServer.URL)
	if err := os.WriteFile(configPath, []byte(updatedConfig), 0644); err != nil {
		t.Fatalf("failed to update config: %v", err)
	}

	htmlPath := filepath.Join(projectDir, "page.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Reverse Project Demo</title></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}

	output := captureStdout(t, func() {
		_ = scrapyCommand([]string{"run", "--project", projectDir, "--spider", "demo", "--html-file", htmlPath})
	})

	if !strings.Contains(output, `"project_runner": "built-in-metadata-runner"`) || !strings.Contains(output, `"runner": "http"`) || !strings.Contains(output, `"spider": "demo"`) {
		t.Fatalf("expected built-in metadata project runner payload, got: %s", output)
	}
	if !strings.Contains(output, `"reverse":`) {
		t.Fatalf("expected reverse summary in payload, got: %s", output)
	}
}

func TestScrapyShellCommandExtractsValues(t *testing.T) {
	htmlPath := filepath.Join(t.TempDir(), "page.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Shell Demo</title></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}

	output := captureStdout(t, func() {
		_ = scrapyCommand([]string{"shell", "--html-file", htmlPath, "--type", "css", "--expr", "title"})
	})

	if !strings.Contains(output, `"command": "scrapy shell"`) || !strings.Contains(output, "Shell Demo") {
		t.Fatalf("unexpected scrapy shell output: %s", output)
	}
}

func TestScrapyExportCommandUsesProjectOutput(t *testing.T) {
	projectDir := t.TempDir()
	sourcePath := filepath.Join(projectDir, "artifacts", "exports", "items.json")
	if err := os.MkdirAll(filepath.Dir(sourcePath), 0755); err != nil {
		t.Fatalf("failed to prepare export dir: %v", err)
	}
	if err := os.WriteFile(filepath.Join(projectDir, "scrapy-project.json"), []byte(`{
  "name": "demo-project",
  "runtime": "go",
  "entry": "main.go",
  "url": "https://example.com",
  "output": "artifacts/exports/items.json"
}`), 0644); err != nil {
		t.Fatalf("failed to write scrapy project manifest: %v", err)
	}
	if err := os.WriteFile(sourcePath, []byte(`[{"title":"Demo","url":"https://example.com"}]`), 0644); err != nil {
		t.Fatalf("failed to write source data: %v", err)
	}
	outputPath := filepath.Join(projectDir, "artifacts", "exports", "items.csv")

	output := captureStdout(t, func() {
		_ = scrapyCommand([]string{"export", "--project", projectDir, "--format", "csv", "--output", outputPath})
	})

	if !strings.Contains(output, `"command": "scrapy export"`) {
		t.Fatalf("unexpected scrapy export output: %s", output)
	}
	if _, err := os.Stat(outputPath); err != nil {
		t.Fatalf("expected exported file: %v", err)
	}
}

func TestScrapyProfileCommandUsesProjectAndSpider(t *testing.T) {
	projectDir := t.TempDir()
	htmlPath := filepath.Join(projectDir, "page.html")
	if err := os.MkdirAll(filepath.Join(projectDir, "spiders"), 0755); err != nil {
		t.Fatalf("failed to prepare spiders dir: %v", err)
	}
	if err := os.WriteFile(filepath.Join(projectDir, "scrapy-project.json"), []byte(`{
  "name": "demo-project",
  "runtime": "go",
  "entry": "main.go",
  "url": "https://example.com",
  "output": "artifacts/exports/items.json"
}`), 0644); err != nil {
		t.Fatalf("failed to write scrapy project manifest: %v", err)
	}
	if err := os.WriteFile(filepath.Join(projectDir, "spiders", "news.go"), []byte("// scrapy: url=https://example.com/news\n"), 0644); err != nil {
		t.Fatalf("failed to write spider metadata: %v", err)
	}
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Profile Demo</title><a href='/a'>A</a><img src='x.png'></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}

	output := captureStdout(t, func() {
		_ = scrapyCommand([]string{"profile", "--project", projectDir, "--spider", "news", "--html-file", htmlPath})
	})

	if !strings.Contains(output, `"command": "scrapy profile"`) || !strings.Contains(output, `"spider": "news"`) || !strings.Contains(output, `"link_count": 1`) {
		t.Fatalf("unexpected scrapy profile output: %s", output)
	}
	if !strings.Contains(output, `"url_source": "html-fixture"`) {
		t.Fatalf("expected url source in profile output: %s", output)
	}
}

func TestScrapyBenchCommandUsesHtmlFixture(t *testing.T) {
	htmlPath := filepath.Join(t.TempDir(), "page.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Bench Demo</title><a href='/a'>A</a></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}

	output := captureStdout(t, func() {
		_ = scrapyCommand([]string{"bench", "--html-file", htmlPath})
	})

	if !strings.Contains(output, `"command": "scrapy bench"`) || !strings.Contains(output, `"title": "Bench Demo"`) {
		t.Fatalf("unexpected scrapy bench output: %s", output)
	}
	if !strings.Contains(output, `"url_source": "html-fixture"`) {
		t.Fatalf("expected url source in bench output: %s", output)
	}
}

func TestScrapyDoctorCommandReportsProjectHealth(t *testing.T) {
	projectDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(projectDir, "scrapy-project.json"), []byte(`{
  "name": "demo-project",
  "runtime": "go",
  "entry": "main.go",
  "url": "https://example.com",
  "output": "artifacts/exports/items.json"
}`), 0644); err != nil {
		t.Fatalf("failed to write scrapy project manifest: %v", err)
	}
	if err := os.WriteFile(filepath.Join(projectDir, "main.go"), []byte("// scrapy: url=https://example.com\n"), 0644); err != nil {
		t.Fatalf("failed to write main.go: %v", err)
	}

	output := captureStdout(t, func() {
		_ = scrapyCommand([]string{"doctor", "--project", projectDir})
	})

	if !strings.Contains(output, `"command": "scrapy doctor"`) {
		t.Fatalf("unexpected scrapy doctor output: %s", output)
	}
}

func TestProjectRunnerLoadsRegisteredPlugin(t *testing.T) {
	projectDir := filepath.Join(t.TempDir(), "plugin-project")
	_ = scrapyCommand([]string{"init", "--path", projectDir})

	if err := os.WriteFile(filepath.Join(projectDir, "scrapy-plugins.json"), []byte(`{
  "plugins": [
    {
      "name": "field-injector",
      "priority": 5,
      "config": {
        "fields": {
          "plugin": "yes",
          "pipeline": "active"
        }
      }
    }
  ]
}`), 0644); err != nil {
		t.Fatalf("failed to write plugin manifest: %v", err)
	}
	htmlPath := filepath.Join(projectDir, "page.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Plugin Demo</title></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}

	output := captureStdout(t, func() {
		_ = scrapyCommand([]string{"run", "--project", projectDir, "--spider", "demo", "--html-file", htmlPath})
	})

	if !strings.Contains(output, `"project_runner": "built-in-metadata-runner"`) || !strings.Contains(output, `"runner": "http"`) {
		t.Fatalf("expected built-in metadata project runner output: %s", output)
	}
	if !strings.Contains(string(mustReadFile(t, filepath.Join(projectDir, "scrapy-plugins.json"))), "field-injector") {
		t.Fatalf("expected field-injector manifest to be used")
	}
	exported, err := os.ReadFile(filepath.Join(projectDir, "artifacts", "exports", "demo.json"))
	if err != nil {
		t.Fatalf("expected export output: %v", err)
	}
	if !strings.Contains(string(exported), `"plugin": "yes"`) || !strings.Contains(string(exported), `"pipeline": "active"`) {
		t.Fatalf("expected plugin-mutated export, got %s", string(exported))
	}
}

func TestScrapyRunAppliesDeclarativeComponentsFromProjectConfig(t *testing.T) {
	projectDir := filepath.Join(t.TempDir(), "component-project")
	_ = scrapyCommand([]string{"init", "--path", projectDir})

	configPath := filepath.Join(projectDir, "spider-framework.yaml")
	updatedConfig := "version: 1\nproject:\n  name: component-project\nruntime: go\ncrawl:\n  urls:\n    - https://example.com\n  concurrency: 5\n  max_requests: 100\n  max_depth: 3\n  timeout_seconds: 30\nsitemap:\n  enabled: false\n  url: https://example.com/sitemap.xml\n  max_urls: 50\nbrowser:\n  enabled: true\n  headless: true\n  timeout_seconds: 30\n  user_agent: ''\n  screenshot_path: artifacts/browser/page.png\n  html_path: artifacts/browser/page.html\nanti_bot:\n  enabled: true\n  profile: chrome-stealth\n  proxy_pool: local\n  session_mode: sticky\n  stealth: true\n  challenge_policy: browser\n  captcha_provider: 2captcha\n  captcha_api_key: ''\nnode_reverse:\n  enabled: true\n  base_url: http://localhost:3000\nmiddleware:\n  user_agent_rotation: true\n  respect_robots_txt: true\n  min_request_interval_ms: 200\npipeline:\n  console: true\n  dataset: true\n  jsonl_path: artifacts/exports/results.jsonl\nauto_throttle:\n  enabled: true\n  start_delay_ms: 200\n  max_delay_ms: 5000\n  target_response_time_ms: 2000\nplugins:\n  enabled: true\n  manifest: contracts/integration-catalog.json\nscrapy:\n  runner: http\n  pipelines:\n    - field-injector\n  spider_middlewares:\n    - response-context\n  component_config:\n    field_injector:\n      fields:\n        component: configured\nstorage:\n  checkpoint_dir: artifacts/checkpoints\n  dataset_dir: artifacts/datasets\n  export_dir: artifacts/exports\nexport:\n  format: json\n  output_path: artifacts/exports/results.json\ndoctor:\n  network_targets:\n    - https://example.com\n"
	if err := os.WriteFile(configPath, []byte(updatedConfig), 0644); err != nil {
		t.Fatalf("failed to update config: %v", err)
	}

	htmlPath := filepath.Join(projectDir, "page.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Component Demo</title></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}

	output := captureStdout(t, func() {
		_ = scrapyCommand([]string{"run", "--project", projectDir, "--spider", "demo", "--html-file", htmlPath})
	})

	listOutput := captureStdout(t, func() {
		_ = scrapyCommand([]string{"list", "--project", projectDir})
	})
	if !strings.Contains(listOutput, `"pipelines": [`) || !strings.Contains(listOutput, `"field-injector"`) {
		t.Fatalf("expected declarative pipelines in list output: %s", listOutput)
	}
	if !strings.Contains(listOutput, `"spider_middlewares": [`) || !strings.Contains(listOutput, `"response-context"`) {
		t.Fatalf("expected declarative spider middlewares in list output: %s", listOutput)
	}

	validateOutput := captureStdout(t, func() {
		_ = scrapyCommand([]string{"validate", "--project", projectDir})
	})
	if !strings.Contains(validateOutput, `"components"`) || !strings.Contains(validateOutput, `pipeline:field-injector`) || !strings.Contains(validateOutput, `spider_middleware:response-context`) {
		t.Fatalf("expected declarative component checks in validate output: %s", validateOutput)
	}

	if !strings.Contains(output, `"resolved_runner": "http"`) {
		t.Fatalf("expected resolved runner in output: %s", output)
	}
	if !strings.Contains(output, `"pipelines": [`) || !strings.Contains(output, `declarativeFieldInjectorPipeline`) {
		t.Fatalf("expected declarative pipeline names in output: %s", output)
	}
	if !strings.Contains(output, `declarativeResponseContextSpiderMiddleware`) {
		t.Fatalf("expected declarative spider middleware names in output: %s", output)
	}
	exported, err := os.ReadFile(filepath.Join(projectDir, "artifacts", "exports", "demo.json"))
	if err != nil {
		t.Fatalf("expected export output: %v", err)
	}
	exportedText := string(exported)
	if !strings.Contains(exportedText, `"component": "configured"`) {
		t.Fatalf("expected declarative pipeline field, got %s", exportedText)
	}
	if !strings.Contains(exportedText, `"response_url": "https://example.com"`) {
		t.Fatalf("expected declarative spider middleware field, got %s", exportedText)
	}
}

func TestScrapyRunAppliesSpiderSpecificDeclarativeOverrides(t *testing.T) {
	projectDir := filepath.Join(t.TempDir(), "component-project")
	_ = scrapyCommand([]string{"init", "--path", projectDir})

	configPath := filepath.Join(projectDir, "spider-framework.yaml")
	updatedConfig := "version: 1\nproject:\n  name: component-project\nruntime: go\ncrawl:\n  urls:\n    - https://example.com\n  concurrency: 5\n  max_requests: 100\n  max_depth: 3\n  timeout_seconds: 30\nsitemap:\n  enabled: false\n  url: https://example.com/sitemap.xml\n  max_urls: 50\nbrowser:\n  enabled: true\n  headless: true\n  timeout_seconds: 30\n  user_agent: ''\n  screenshot_path: artifacts/browser/page.png\n  html_path: artifacts/browser/page.html\nanti_bot:\n  enabled: true\n  profile: chrome-stealth\n  proxy_pool: local\n  session_mode: sticky\n  stealth: true\n  challenge_policy: browser\n  captcha_provider: 2captcha\n  captcha_api_key: ''\nnode_reverse:\n  enabled: true\n  base_url: http://localhost:3000\nmiddleware:\n  user_agent_rotation: true\n  respect_robots_txt: true\n  min_request_interval_ms: 200\npipeline:\n  console: true\n  dataset: true\n  jsonl_path: artifacts/exports/results.jsonl\nauto_throttle:\n  enabled: true\n  start_delay_ms: 200\n  max_delay_ms: 5000\n  target_response_time_ms: 2000\nplugins:\n  enabled: true\n  manifest: contracts/integration-catalog.json\nscrapy:\n  runner: http\n  pipelines:\n    - field-injector\n  component_config:\n    field_injector:\n      fields:\n        scope: global\n  spiders:\n    demo:\n      runner: http\n      url: https://example.com\n      spider_middlewares:\n        - response-context\n      component_config:\n        field_injector:\n          fields:\n            scope: demo\n            spider_only: demo-only\nstorage:\n  checkpoint_dir: artifacts/checkpoints\n  dataset_dir: artifacts/datasets\n  export_dir: artifacts/exports\nexport:\n  format: json\n  output_path: artifacts/exports/results.json\ndoctor:\n  network_targets:\n    - https://example.com\n"
	if err := os.WriteFile(configPath, []byte(updatedConfig), 0644); err != nil {
		t.Fatalf("failed to update config: %v", err)
	}

	htmlPath := filepath.Join(projectDir, "page.html")
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Spider Override Demo</title></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}

	output := captureStdout(t, func() {
		_ = scrapyCommand([]string{"run", "--project", projectDir, "--spider", "demo", "--html-file", htmlPath})
	})

	if !strings.Contains(output, `declarativeFieldInjectorPipeline`) || !strings.Contains(output, `declarativeResponseContextSpiderMiddleware`) {
		t.Fatalf("expected spider-specific declarative components in output: %s", output)
	}

	listOutput := captureStdout(t, func() {
		_ = scrapyCommand([]string{"list", "--project", projectDir})
	})
	if !strings.Contains(listOutput, `"pipelines": [`) || !strings.Contains(listOutput, `"spider_middlewares": [`) {
		t.Fatalf("expected spider payload component arrays in list output: %s", listOutput)
	}

	exported, err := os.ReadFile(filepath.Join(projectDir, "artifacts", "exports", "demo.json"))
	if err != nil {
		t.Fatalf("expected export output: %v", err)
	}
	exportedText := string(exported)
	if !strings.Contains(exportedText, `"scope": "demo"`) || !strings.Contains(exportedText, `"spider_only": "demo-only"`) {
		t.Fatalf("expected spider-specific component_config override, got %s", exportedText)
	}
	if !strings.Contains(exportedText, `"response_url": "https://example.com"`) {
		t.Fatalf("expected spider-specific middleware field, got %s", exportedText)
	}
}

func mustReadFile(t *testing.T, path string) []byte {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("failed to read %s: %v", path, err)
	}
	return data
}

func TestPrintAndPersistJobResultWritesOutputPath(t *testing.T) {
	outputPath := filepath.Join(t.TempDir(), "job-result.json")
	job := &core.JobSpec{
		Name: "job-ai",
		Output: core.OutputSpec{
			Path: outputPath,
		},
	}
	result := core.NewJobResult(*job, core.StateSucceeded)
	result.SetExtractField("title", "persisted")
	result.FinishedAt = result.StartedAt
	result.Finalize()

	printAndPersistJobResult(job, result)

	content, err := os.ReadFile(outputPath)
	if err != nil {
		t.Fatalf("expected output file to be written: %v", err)
	}
	if !strings.Contains(string(content), "\"title\": \"persisted\"") {
		t.Fatalf("expected persisted extract content, got %s", string(content))
	}
}

func TestCLIJobResultPayloadUsesArtifactEnvelope(t *testing.T) {
	result := core.NewJobResult(core.JobSpec{Name: "graph-job"}, core.StateSucceeded)
	result.SetArtifact("graph", core.ArtifactRef{
		Kind: "graph",
		Path: "artifacts/runtime/graphs/graph-job.json",
		Metadata: map[string]interface{}{
			"root_id": "document",
			"stats": map[string]interface{}{
				"total_nodes": 3,
				"total_edges": 1,
			},
		},
	})
	result.Finalize()

	payload := cliJobResultPayload(result)
	artifacts := payload["artifacts"].(map[string]map[string]interface{})
	if artifacts["graph"]["kind"] != "graph" {
		t.Fatalf("expected graph artifact envelope, got %#v", artifacts)
	}
	if payload["artifact_refs"].(map[string]map[string]interface{})["graph"]["path"] != "artifacts/runtime/graphs/graph-job.json" {
		t.Fatalf("expected artifact_refs to mirror artifacts envelope")
	}
}

func TestInjectedJobFailureUsesMetadataContract(t *testing.T) {
	job := &core.JobSpec{
		Metadata: map[string]interface{}{
			"fail_job": "offline injected failure",
		},
	}

	err := injectedJobFailure(job)
	if err == nil {
		t.Fatal("expected injected job failure")
	}
	if !strings.Contains(err.Error(), "offline injected failure") {
		t.Fatalf("unexpected injected failure: %v", err)
	}
}

func TestUltimateCommandRunsWithMockServices(t *testing.T) {
	pageServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		_, _ = w.Write([]byte(`<html><title>Ultimate Page</title><script>navigator.userAgent; CryptoJS.AES.encrypt("x","y")</script></html>`))
	}))
	defer pageServer.Close()

	reverseServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		switch r.URL.Path {
		case "/health":
			_, _ = w.Write([]byte(`{"status":"ok"}`))
		case "/api/anti-bot/detect":
			_, _ = w.Write([]byte(`{"success":true,"signals":["vendor:test"],"level":"medium","detection":{"hasCloudflare":true}}`))
		case "/api/anti-bot/profile":
			_, _ = w.Write([]byte(`{"success":true,"signals":["vendor:test"],"level":"medium","score":12,"vendors":[],"challenges":[],"recommendations":["keep cookies"],"requestBlueprint":{"headers":{"User-Agent":"GoSpiderTest"}},"mitigationPlan":{}}`))
		case "/api/fingerprint/spoof":
			_, _ = w.Write([]byte(`{"success":true,"browser":"chrome","platform":"windows","fingerprint":{"userAgent":"mock"}}`))
		case "/api/tls/fingerprint":
			_, _ = w.Write([]byte(`{"success":true,"browser":"chrome","version":"120","fingerprint":{"ja3":"mock-ja3"}}`))
		case "/api/browser/simulate":
			_, _ = w.Write([]byte(`{"success":true,"result":{"ok":true},"cookies":"session=1"}`))
		case "/api/crypto/analyze":
			_, _ = w.Write([]byte(`{"success":true,"cryptoTypes":[{"name":"AES","confidence":0.9,"modes":["CBC"]}],"keys":["secret"],"ivs":["iv"],"analysis":{"hasKeyDerivation":true,"hasRandomIV":false}}`))
		default:
			http.NotFound(w, r)
		}
	}))
	defer reverseServer.Close()

	tempDir := t.TempDir()
	configPath := filepath.Join(tempDir, "spider-framework.yaml")
	configBody := strings.Join([]string{
		"version: 1",
		"project:",
		"  name: go-ultimate-test",
		"runtime: go",
		"crawl:",
		"  urls:",
		"    - " + pageServer.URL,
		"  concurrency: 1",
		"  max_requests: 1",
		"  max_depth: 1",
		"  timeout_seconds: 5",
		"browser:",
		"  enabled: true",
		"  headless: true",
		"  timeout_seconds: 5",
		"  user_agent: GoSpiderUltimateTest",
		"  screenshot_path: artifacts/browser/page.png",
		"  html_path: artifacts/browser/page.html",
		"storage:",
		"  checkpoint_dir: " + filepath.ToSlash(filepath.Join(tempDir, "checkpoints")),
		"  dataset_dir: " + filepath.ToSlash(filepath.Join(tempDir, "datasets")),
		"  export_dir: " + filepath.ToSlash(filepath.Join(tempDir, "exports")),
		"export:",
		"  format: json",
		"  output_path: " + filepath.ToSlash(filepath.Join(tempDir, "exports", "results.json")),
		"doctor:",
		"  network_targets:",
		"    - https://example.com",
	}, "\n")
	if err := os.WriteFile(configPath, []byte(configBody), 0644); err != nil {
		t.Fatalf("failed to write config: %v", err)
	}

	output := captureStdout(t, func() {
		ultimateCommand([]string{
			"--config", configPath,
			"--reverse-service-url", reverseServer.URL,
		})
	})

	if !strings.Contains(output, "Go Spider 终极增强版") {
		t.Fatalf("expected ultimate banner, got: %s", output)
	}
	if !strings.Contains(output, `"command": "ultimate"`) {
		t.Fatalf("expected ultimate payload, got: %s", output)
	}
	if !strings.Contains(output, `"runtime": "go"`) {
		t.Fatalf("expected go runtime payload, got: %s", output)
	}
	if !strings.Contains(output, `"summary": "passed"`) {
		t.Fatalf("expected passed summary, got: %s", output)
	}
	if !strings.Contains(output, `"reverse":`) || !strings.Contains(output, `mock-ja3`) {
		t.Fatalf("expected reverse runtime summary in output, got: %s", output)
	}
	if !strings.Contains(output, "成功: 1, 失败: 0") {
		t.Fatalf("expected successful ultimate run, got: %s", output)
	}
	if _, err := os.Stat(filepath.Join(tempDir, "checkpoints", "task_0.json")); err != nil {
		t.Fatalf("expected checkpoint output: %v", err)
	}
}
