package project

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"

	scrapyapi "gospider/scrapy"
)

func TestRunFromEnvAppliesDeclarativeComponentsFromProjectConfig(t *testing.T) {
	projectDir := t.TempDir()
	htmlPath := filepath.Join(projectDir, "page.html")
	outputPath := filepath.Join(projectDir, "artifacts", "exports", "items.json")
	configPath := filepath.Join(projectDir, "spider-framework.yaml")

	if err := os.MkdirAll(filepath.Dir(outputPath), 0755); err != nil {
		t.Fatalf("failed to prepare output dir: %v", err)
	}
	if err := os.WriteFile(htmlPath, []byte(`<html><title>Artifact Component</title></html>`), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}
	config := "" +
		"scrapy:\n" +
		"  pipelines:\n" +
		"    - field-injector\n" +
		"  spider_middlewares:\n" +
		"    - response-context\n" +
		"  component_config:\n" +
		"    field_injector:\n" +
		"      fields:\n" +
		"        component: configured\n"
	if err := os.WriteFile(configPath, []byte(config), 0644); err != nil {
		t.Fatalf("failed to write config: %v", err)
	}

	RegisterSpider("artifact-components", func() *scrapyapi.Spider {
		return scrapyapi.NewSpider("artifact-components", func(response *scrapyapi.Response) ([]any, error) {
			return []any{
				scrapyapi.NewItem().
					Set("title", response.CSS("title").Get()).
					Set("url", response.URL),
			}, nil
		})
	})

	restoreEnv := setArtifactEnv(t, map[string]string{
		"GOSPIDER_SCRAPY_RUNNER":   "1",
		"GOSPIDER_SCRAPY_PROJECT":  projectDir,
		"GOSPIDER_SCRAPY_SPIDER":   "artifact-components",
		"GOSPIDER_SCRAPY_URL":      "https://example.com",
		"GOSPIDER_SCRAPY_HTML_FILE": htmlPath,
		"GOSPIDER_SCRAPY_OUTPUT":   outputPath,
	})
	defer restoreEnv()

	originalStdout := os.Stdout
	reader, writer, err := os.Pipe()
	if err != nil {
		t.Fatalf("pipe failed: %v", err)
	}
	os.Stdout = writer
	defer func() { os.Stdout = originalStdout }()

	handled, err := RunFromEnv()
	_ = writer.Close()
	if err != nil {
		t.Fatalf("RunFromEnv failed: %v", err)
	}
	if !handled {
		t.Fatal("expected RunFromEnv to handle scrapy artifact execution")
	}

	var stdout bytes.Buffer
	_, _ = stdout.ReadFrom(reader)
	output := stdout.String()
	if !strings.Contains(output, `"runner": "artifact-project"`) {
		t.Fatalf("expected artifact-project payload, got: %s", output)
	}
	if !strings.Contains(output, `"settings_source":`) || !strings.Contains(output, `"pipelines": [`) {
		t.Fatalf("expected declarative assembly summary in payload, got: %s", output)
	}

	exported, err := os.ReadFile(outputPath)
	if err != nil {
		t.Fatalf("failed to read exported file: %v", err)
	}
	exportedText := string(exported)
	if !strings.Contains(exportedText, `"component": "configured"`) {
		t.Fatalf("expected declarative pipeline output, got: %s", exportedText)
	}
	if !strings.Contains(exportedText, `"response_url": "https://example.com"`) {
		t.Fatalf("expected declarative spider middleware output, got: %s", exportedText)
	}
}

func setArtifactEnv(t *testing.T, values map[string]string) func() {
	t.Helper()
	originals := map[string]*string{}
	for key, value := range values {
		if current, ok := os.LookupEnv(key); ok {
			copyValue := current
			originals[key] = &copyValue
		} else {
			originals[key] = nil
		}
		if err := os.Setenv(key, value); err != nil {
			t.Fatalf("failed to set env %s: %v", key, err)
		}
	}
	return func() {
		for key, original := range originals {
			if original == nil {
				_ = os.Unsetenv(key)
			} else {
				_ = os.Setenv(key, *original)
			}
		}
	}
}
