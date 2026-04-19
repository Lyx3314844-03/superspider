package research

import (
	"path/filepath"
	"strings"
	"testing"
)

func TestResearchJobIsConstructible(t *testing.T) {
	job := ResearchJob{SeedURLs: []string{"https://example.com"}}
	if len(job.SeedURLs) != 1 || job.SeedURLs[0] != "https://example.com" {
		t.Fatalf("unexpected seed urls: %#v", job.SeedURLs)
	}
}

func TestResearchRuntimeRunsJob(t *testing.T) {
	runtime := NewResearchRuntime()
	result, err := runtime.Run(
		ResearchJob{
			SeedURLs: []string{"https://example.com"},
			ExtractSchema: map[string]interface{}{
				"properties": map[string]interface{}{
					"title": map[string]interface{}{"type": "string"},
				},
			},
		},
		"<title>Go Runtime Demo</title>",
	)
	if err != nil {
		t.Fatalf("expected runtime to succeed: %v", err)
	}
	extract := result["extract"].(map[string]interface{})
	if extract["title"] != "Go Runtime Demo" {
		t.Fatalf("unexpected extract: %#v", extract)
	}
}

func TestResearchRuntimeWritesJSONLDataset(t *testing.T) {
	runtime := NewResearchRuntime()
	outputPath := filepath.Join(t.TempDir(), "rows.jsonl")
	result, err := runtime.Run(
		ResearchJob{
			SeedURLs: []string{"https://example.com"},
			ExtractSchema: map[string]interface{}{
				"properties": map[string]interface{}{
					"title": map[string]interface{}{"type": "string"},
				},
			},
			Output: map[string]interface{}{
				"format": "jsonl",
				"path":   outputPath,
			},
		},
		"<title>Go Dataset Demo</title>",
	)
	if err != nil {
		t.Fatalf("expected runtime to succeed: %v", err)
	}
	dataset := result["dataset"].(map[string]interface{})
	if dataset["path"] != outputPath {
		t.Fatalf("unexpected dataset payload: %#v", dataset)
	}
}

func TestResearchRuntimeValidatesRequiredAndSchemaForSpecs(t *testing.T) {
	runtime := NewResearchRuntime()
	_, err := runtime.Run(
		ResearchJob{
			SeedURLs: []string{"https://example.com"},
			ExtractSchema: map[string]interface{}{
				"properties": map[string]interface{}{
					"price": map[string]interface{}{"type": "number"},
				},
			},
			ExtractSpecs: []map[string]interface{}{
				{
					"field":    "price",
					"type":     "regex",
					"expr":     `price:\s*(\w+)`,
					"required": true,
				},
			},
		},
		"<title>Demo</title>\nprice: free",
	)
	if err == nil || !strings.Contains(err.Error(), "schema.type=number") {
		t.Fatalf("expected schema validation error, got %v", err)
	}
}

func TestResearchRuntimeSupportsXPathAndJSONPathSpecs(t *testing.T) {
	runtime := NewResearchRuntime()
	cssResult, err := runtime.Run(
		ResearchJob{
			SeedURLs: []string{"https://example.com"},
			ExtractSpecs: []map[string]interface{}{
				{"field": "title", "type": "css", "expr": "title", "required": true},
				{"field": "cover", "type": "css_attr", "expr": "meta[name='og:image']", "attr": "content", "required": true},
			},
		},
		`<html><head><title>CSS Demo</title><meta name="og:image" content="https://img.example.com/cover.jpg" /></head></html>`,
	)
	if err != nil {
		t.Fatalf("expected css extraction to succeed: %v", err)
	}
	cssExtract := cssResult["extract"].(map[string]interface{})
	if cssExtract["title"] != "CSS Demo" || cssExtract["cover"] != "https://img.example.com/cover.jpg" {
		t.Fatalf("unexpected css extract: %#v", cssExtract)
	}

	result, err := runtime.Run(
		ResearchJob{
			SeedURLs: []string{"https://example.com"},
			ExtractSpecs: []map[string]interface{}{
				{"field": "title", "type": "xpath", "expr": "//title/text()", "required": true},
				{"field": "name", "type": "json_path", "path": "$.product.name", "required": true},
			},
		},
		`{"product":{"name":"Capsule"}}`,
	)
	if err == nil {
		t.Fatalf("expected xpath extraction to fail against pure json content")
	}

	result, err = runtime.Run(
		ResearchJob{
			SeedURLs: []string{"https://example.com"},
			ExtractSpecs: []map[string]interface{}{
				{"field": "title", "type": "xpath", "expr": "//title/text()", "required": true},
			},
		},
		"<html><title>XPath Demo</title></html>",
	)
	if err != nil {
		t.Fatalf("expected xpath extraction to succeed: %v", err)
	}
	extract := result["extract"].(map[string]interface{})
	if extract["title"] != "XPath Demo" {
		t.Fatalf("unexpected xpath extract: %#v", extract)
	}

	jsonResult, err := runtime.Run(
		ResearchJob{
			SeedURLs: []string{"https://example.com"},
			ExtractSpecs: []map[string]interface{}{
				{"field": "name", "type": "json_path", "path": "$.product.name", "required": true},
			},
		},
		`{"product":{"name":"Capsule"}}`,
	)
	if err != nil {
		t.Fatalf("expected json path extraction to succeed: %v", err)
	}
	jsonExtract := jsonResult["extract"].(map[string]interface{})
	if jsonExtract["name"] != "Capsule" {
		t.Fatalf("unexpected json extract: %#v", jsonExtract)
	}
}

func TestAsyncResearchRuntimeRunsMultipleJobs(t *testing.T) {
	runtime := NewAsyncResearchRuntime(&AsyncResearchConfig{MaxConcurrent: 2})
	jobs := []ResearchJob{
		{SeedURLs: []string{"https://example.com/1"}, ExtractSchema: map[string]interface{}{"properties": map[string]interface{}{"title": map[string]interface{}{"type": "string"}}}},
		{SeedURLs: []string{"https://example.com/2"}, ExtractSchema: map[string]interface{}{"properties": map[string]interface{}{"title": map[string]interface{}{"type": "string"}}}},
	}
	results := runtime.RunMultiple(jobs, []string{"<title>One</title>", "<title>Two</title>"})
	if len(results) != 2 {
		t.Fatalf("expected 2 results, got %d", len(results))
	}
	if results[0].Error != "" || results[1].Error != "" {
		t.Fatalf("expected successful results: %#v", results)
	}
	metrics := runtime.SnapshotMetrics()
	if metrics["tasks_completed"].(int) != 2 {
		t.Fatalf("unexpected metrics: %#v", metrics)
	}
}

func TestAsyncResearchRuntimeRunStreamAndSoak(t *testing.T) {
	runtime := NewAsyncResearchRuntime(&AsyncResearchConfig{MaxConcurrent: 2})
	jobs := []ResearchJob{
		{SeedURLs: []string{"https://example.com/1"}, ExtractSchema: map[string]interface{}{"properties": map[string]interface{}{"title": map[string]interface{}{"type": "string"}}}, Policy: map[string]interface{}{"simulate_delay_ms": 10}},
		{SeedURLs: []string{"https://example.com/2"}, ExtractSchema: map[string]interface{}{"properties": map[string]interface{}{"title": map[string]interface{}{"type": "string"}}}, Policy: map[string]interface{}{"simulate_delay_ms": 10}},
	}
	streamCount := 0
	for result := range runtime.RunStream(jobs, []string{"<title>One</title>", "<title>Two</title>"}) {
		if result.Error != "" {
			t.Fatalf("unexpected stream error: %#v", result)
		}
		streamCount++
	}
	if streamCount != 2 {
		t.Fatalf("expected 2 stream results, got %d", streamCount)
	}
	report := runtime.RunSoak(jobs, []string{"<title>One</title>", "<title>Two</title>"}, 2)
	if !report["stable"].(bool) || report["results"].(int) != 4 {
		t.Fatalf("unexpected soak report: %#v", report)
	}
}

func TestExperimentTrackerRecordsAndComparesExperiments(t *testing.T) {
	tracker := NewExperimentTracker()
	record := tracker.Record(
		"exp-1",
		[]string{"https://example.com"},
		[]map[string]interface{}{
			{"seed": "https://example.com", "extract": map[string]interface{}{"title": "Demo"}, "duration_ms": 100.0},
		},
		map[string]interface{}{"type": "object"},
		nil,
	)
	if record.ID != "exp-001" {
		t.Fatalf("unexpected record id: %#v", record)
	}
	comparison := tracker.Compare()
	summary := comparison["summary"].(map[string]interface{})
	if summary["total_experiments"].(int) != 1 {
		t.Fatalf("unexpected comparison summary: %#v", comparison)
	}
	rows := tracker.ToRows()
	if len(rows) != 1 || rows[0]["experiment_name"] != "exp-1" {
		t.Fatalf("unexpected tracker rows: %#v", rows)
	}
}
