package browser

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestNormalizeUploadPathsRejectsEmptyAndMissingFiles(t *testing.T) {
	if _, err := normalizeUploadPaths(nil); err == nil {
		t.Fatal("expected empty upload list to fail")
	}
	if _, err := normalizeUploadPaths([]string{"  "}); err == nil {
		t.Fatal("expected blank upload path to fail")
	}
	if _, err := normalizeUploadPaths([]string{"does-not-exist.txt"}); err == nil {
		t.Fatal("expected missing file to fail")
	}
}

func TestNormalizeUploadPathsReturnsAbsolutePaths(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "fixture.txt")
	if err := os.WriteFile(path, []byte("fixture"), 0644); err != nil {
		t.Fatalf("write fixture: %v", err)
	}

	normalized, err := normalizeUploadPaths([]string{path})
	if err != nil {
		t.Fatalf("normalize upload paths: %v", err)
	}
	if len(normalized) != 1 {
		t.Fatalf("expected one normalized path, got %d", len(normalized))
	}
	if !filepath.IsAbs(normalized[0]) {
		t.Fatalf("expected absolute path, got %s", normalized[0])
	}
}

func TestBuildFrameEvalScriptIncludesSameOriginGuard(t *testing.T) {
	script, err := buildFrameEvalScript("#app-frame", "document.title")
	if err != nil {
		t.Fatalf("build frame eval script: %v", err)
	}
	if !strings.Contains(script, "frame not found") {
		t.Fatalf("expected frame-not-found guard, got %s", script)
	}
	if !strings.Contains(script, "same-origin or not loaded") {
		t.Fatalf("expected same-origin guard, got %s", script)
	}
	if !strings.Contains(script, "document.title") {
		t.Fatalf("expected embedded script, got %s", script)
	}
}

func TestBuildFrameMutationScriptSupportsClickAndFill(t *testing.T) {
	clickScript, err := buildFrameMutationScript("#frame", "#submit", "click", "")
	if err != nil {
		t.Fatalf("build click frame script: %v", err)
	}
	if !strings.Contains(clickScript, `=== "click"`) {
		t.Fatalf("expected click branch, got %s", clickScript)
	}

	fillScript, err := buildFrameMutationScript("#frame", "#email", "fill", "user@example.com")
	if err != nil {
		t.Fatalf("build fill frame script: %v", err)
	}
	if !strings.Contains(fillScript, "user@example.com") {
		t.Fatalf("expected fill value in script, got %s", fillScript)
	}
	if !strings.Contains(fillScript, `dispatchEvent(new Event("input"`) {
		t.Fatalf("expected input event dispatch, got %s", fillScript)
	}
}

func TestBuildShadowTraversalScriptSupportsOpenShadowPath(t *testing.T) {
	script, err := buildShadowTraversalScript([]string{"app-shell", "button.primary"}, "target.textContent")
	if err != nil {
		t.Fatalf("build shadow traversal script: %v", err)
	}
	if !strings.Contains(script, "open shadowRoot not found") {
		t.Fatalf("expected open shadow-root guard, got %s", script)
	}
	if !strings.Contains(script, "button.primary") {
		t.Fatalf("expected nested selector in script, got %s", script)
	}
	if !strings.Contains(script, "target.textContent") {
		t.Fatalf("expected expression in script, got %s", script)
	}
}

func TestSplitShadowPathForRuntimeTrimsSegments(t *testing.T) {
	path := SplitShadowPathForRuntime(" app-shell >>>  user-card >>> button ")
	if len(path) != 3 {
		t.Fatalf("expected three path segments, got %#v", path)
	}
	if path[0] != "app-shell" || path[1] != "user-card" || path[2] != "button" {
		t.Fatalf("unexpected path segments: %#v", path)
	}
}

func TestRealtimeEntriesAreCopied(t *testing.T) {
	b := NewBrowser(nil)
	b.recordRealtime(RealtimeEntry{Protocol: "websocket", Direction: "received", Data: "hello"})

	entries := b.GetRealtimeEntries()
	if len(entries) != 1 || entries[0].Data != "hello" {
		t.Fatalf("unexpected realtime entries: %#v", entries)
	}
	entries[0].Data = "mutated"
	if b.GetRealtimeEntries()[0].Data != "hello" {
		t.Fatal("expected realtime entries to be copied")
	}
}
