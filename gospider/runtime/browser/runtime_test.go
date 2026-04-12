package browserruntime

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	browserpkg "gospider/browser"
	"gospider/core"
)

func TestBrowserRuntimeEmitsNormalizedResult(t *testing.T) {
	runtime := NewRuntime(func(ctx context.Context, job core.JobSpec) (string, error) {
		return "<html><title>browser</title><img src=\"https://cdn.example.com/a.jpg\"></html>", nil
	})

	job := core.JobSpec{
		Name:    "browser-fetch",
		Runtime: core.RuntimeBrowser,
		Target:  core.TargetSpec{URL: "https://example.com"},
	}

	result, err := runtime.Execute(context.Background(), job)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.State != core.StateSucceeded {
		t.Fatalf("expected succeeded, got %s", result.State)
	}
	if result.Runtime != core.RuntimeBrowser {
		t.Fatalf("expected browser runtime, got %s", result.Runtime)
	}
	if result.Text == "" {
		t.Fatal("expected browser result text")
	}
}

func TestBrowserRuntimePersistsArtifactsAndWarnings(t *testing.T) {
	runtime := NewRuntime(func(ctx context.Context, job core.JobSpec) (string, error) {
		if err := writeArtifact(screenshotArtifactPath(job), []byte("png")); err != nil {
			t.Fatalf("failed to create screenshot artifact: %v", err)
		}
		consoleData, err := json.Marshal([]browserpkg.ConsoleEntry{{
			Type: "log",
			Text: "browser ready",
		}})
		if err != nil {
			t.Fatalf("failed to marshal console artifact: %v", err)
		}
		if err := writeArtifact(consoleArtifactPath(job), consoleData); err != nil {
			t.Fatalf("failed to create console artifact: %v", err)
		}
		networkData, err := json.Marshal([]browserpkg.NetworkEntry{{
			RequestID:    "req-1",
			URL:          "https://example.com/api",
			Method:       "GET",
			ResourceType: "XHR",
			Status:       200,
			MIMEType:     "application/json",
		}})
		if err != nil {
			t.Fatalf("failed to marshal network artifact: %v", err)
		}
		if err := writeArtifact(networkArtifactPath(job), networkData); err != nil {
			t.Fatalf("failed to create network artifact: %v", err)
		}
		if err := writeArtifact(harArtifactPath(job), []byte(`{"log":{"entries":[{"request":{"url":"https://example.com/api"}}]}}`)); err != nil {
			t.Fatalf("failed to create har artifact: %v", err)
		}
		return "<html><title>browser</title></html>", nil
	})

	job := core.JobSpec{
		Name:    "browser-artifacts",
		Runtime: core.RuntimeBrowser,
		Target:  core.TargetSpec{URL: "https://example.com"},
		Output: core.OutputSpec{
			Format:    "artifact",
			Directory: t.TempDir(),
		},
		Browser: core.BrowserSpec{
			Profile: "chrome-stealth",
			Capture: []string{"html", "dom", "screenshot", "console", "network", "har"},
		},
		AntiBot: core.AntiBotSpec{
			SessionMode: "sticky",
			Stealth:     true,
		},
	}

	result, err := runtime.Execute(context.Background(), job)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if _, ok := result.ArtifactRefs["html"]; !ok {
		t.Fatal("expected html artifact ref")
	}
	if _, ok := result.ArtifactRefs["dom"]; !ok {
		t.Fatal("expected dom artifact ref")
	}
	if _, ok := result.ArtifactRefs["screenshot"]; !ok {
		t.Fatal("expected screenshot artifact ref")
	}
	if _, ok := result.ArtifactRefs["console"]; !ok {
		t.Fatal("expected console artifact ref")
	}
	if _, ok := result.ArtifactRefs["network"]; !ok {
		t.Fatal("expected network artifact ref")
	}
	if _, ok := result.ArtifactRefs["har"]; !ok {
		t.Fatal("expected har artifact ref")
	}
	if result.AntiBot == nil || result.AntiBot.SessionMode != "sticky" {
		t.Fatal("expected anti-bot trace to be preserved")
	}
	if len(result.Warnings) != 0 {
		t.Fatalf("expected no warnings, got %v", result.Warnings)
	}

	consoleBytes, err := os.ReadFile(result.ArtifactRefs["console"].Path)
	if err != nil {
		t.Fatalf("failed to read console artifact: %v", err)
	}
	if !strings.Contains(string(consoleBytes), "browser ready") {
		t.Fatalf("expected console artifact content, got %s", string(consoleBytes))
	}

	networkBytes, err := os.ReadFile(result.ArtifactRefs["network"].Path)
	if err != nil {
		t.Fatalf("failed to read network artifact: %v", err)
	}
	if !strings.Contains(string(networkBytes), "\"https://example.com/api\"") {
		t.Fatalf("expected network artifact content, got %s", string(networkBytes))
	}

	harBytes, err := os.ReadFile(result.ArtifactRefs["har"].Path)
	if err != nil {
		t.Fatalf("failed to read har artifact: %v", err)
	}
	if !strings.Contains(string(harBytes), "\"entries\"") {
		t.Fatalf("expected har artifact content, got %s", string(harBytes))
	}
}

func TestBrowserRuntimeSupportsMockBrowserReplay(t *testing.T) {
	tmpdir := t.TempDir()
	fixture := filepath.Join(tmpdir, "fixture.html")
	if err := os.WriteFile(fixture, []byte("<html><title>Fixture Replay</title><body>browser replay</body></html>"), 0644); err != nil {
		t.Fatalf("failed to write fixture: %v", err)
	}

	runtime := NewRuntime(nil)
	job := core.JobSpec{
		Name:    "browser-mock-replay",
		Runtime: core.RuntimeBrowser,
		Target:  core.TargetSpec{URL: "https://example.com"},
		Output: core.OutputSpec{
			Directory: tmpdir,
		},
		Browser: core.BrowserSpec{
			Actions: []core.ActionSpec{
				{Type: "goto", URL: "https://example.com/replay"},
				{Type: "type", Selector: "#captcha", Value: "1234"},
				{Type: "hover", Selector: "#challenge"},
				{Type: "click", Selector: "#continue"},
			},
			Capture: []string{"html", "screenshot", "console", "network", "har"},
		},
		Metadata: map[string]interface{}{
			"mock_browser": map[string]interface{}{
				"html_fixture_path": fixture,
				"screenshot_text":   "replay-screenshot",
				"console_entries": []map[string]interface{}{
					{"type": "warning", "text": "challenge replay"},
				},
				"network_entries": []map[string]interface{}{
					{
						"request_id":    "req-1",
						"url":           "https://example.com/api",
						"method":        "GET",
						"resource_type": "XHR",
						"status":        200,
					},
				},
				"har": map[string]interface{}{
					"log": map[string]interface{}{
						"entries": []map[string]interface{}{
							{"request": map[string]interface{}{"url": "https://example.com/api"}},
						},
					},
				},
				"anti_bot": map[string]interface{}{
					"challenge":           "javascript",
					"fingerprint_profile": "replay-browser",
					"session_mode":        "sticky",
					"stealth":             true,
				},
				"recovery": map[string]interface{}{
					"strategy":  "challenge-bypass",
					"recovered": true,
				},
				"warnings": []interface{}{"synthetic browser replay"},
			},
		},
	}

	result, err := runtime.Execute(context.Background(), job)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(result.Text, "browser replay") {
		t.Fatalf("expected replay html content, got %s", result.Text)
	}
	if result.AntiBot == nil || result.AntiBot.Challenge != "javascript" {
		t.Fatal("expected mock anti-bot trace")
	}
	if result.Recovery == nil || result.Recovery["strategy"] != "challenge-bypass" {
		t.Fatalf("expected recovery trace, got %#v", result.Recovery)
	}
	if len(result.Warnings) != 1 || result.Warnings[0] != "synthetic browser replay" {
		t.Fatalf("expected replay warning, got %#v", result.Warnings)
	}
	actions, ok := result.Metadata["browser_actions"].([]string)
	if !ok {
		t.Fatalf("expected browser action log, got %#v", result.Metadata["browser_actions"])
	}
	if len(actions) != 4 || actions[0] != "goto:https://example.com/replay" || actions[1] != "type:#captcha=1234" || actions[2] != "hover:#challenge" || actions[3] != "click:#continue" {
		t.Fatalf("unexpected browser actions: %#v", actions)
	}
	if _, ok := result.ArtifactRefs["console"]; !ok {
		t.Fatal("expected console artifact ref")
	}
	if _, ok := result.ArtifactRefs["network"]; !ok {
		t.Fatal("expected network artifact ref")
	}
	if _, ok := result.ArtifactRefs["har"]; !ok {
		t.Fatal("expected har artifact ref")
	}
}
