package web

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestServerTaskLifecycleProducesResultsAndLogs(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		_, _ = w.Write([]byte("<html><head><title>Go Demo</title></head><body>ok</body></html>"))
	}))
	defer upstream.Close()

	server := NewServer("0")
	api := httptest.NewServer(server.mux)
	defer api.Close()

	taskID := createTaskViaAPI(t, api.URL, upstream.URL)
	listPayload := getJSON(t, api.URL+"/api/tasks")
	if _, ok := listPayload["pagination"]; !ok {
		t.Fatalf("expected pagination envelope, got %#v", listPayload)
	}
	postJSON(t, http.MethodPost, api.URL+"/api/tasks/"+taskID+"/start", nil, http.StatusOK)

	waitForTaskStatus(t, api.URL, taskID, "completed")

	resultsPayload := getJSON(t, api.URL+"/api/tasks/"+taskID+"/results")
	results := resultsPayload["data"].([]interface{})
	if len(results) != 1 {
		t.Fatalf("expected one result, got %d", len(results))
	}
	result := results[0].(map[string]interface{})
	if result["title"] != "Go Demo" {
		t.Fatalf("expected title Go Demo, got %#v", result["title"])
	}
	artifacts := result["artifacts"].(map[string]interface{})
	graph := artifacts["graph"].(map[string]interface{})
	if graph["kind"] != "graph" {
		t.Fatalf("expected graph artifact, got %#v", graph)
	}
	artifactRefs := result["artifact_refs"].(map[string]interface{})
	if _, ok := artifactRefs["graph"]; !ok {
		t.Fatalf("expected graph artifact_ref, got %#v", artifactRefs)
	}
	if _, err := os.Stat(graph["path"].(string)); err != nil {
		t.Fatalf("expected persisted graph artifact, got error %v", err)
	}
	artifactsPayload := getJSON(t, api.URL+"/api/tasks/"+taskID+"/artifacts")
	artifactData := artifactsPayload["data"].(map[string]interface{})
	if artifactData["graph"] == nil {
		t.Fatalf("expected graph artifact endpoint payload, got %#v", artifactsPayload)
	}

	logsPayload := getJSON(t, api.URL+"/api/tasks/"+taskID+"/logs")
	logs := logsPayload["data"].([]interface{})
	if len(logs) < 2 {
		t.Fatalf("expected at least two logs, got %d", len(logs))
	}

	assertFileContains(t, filepath.Join("artifacts", "control-plane", "results.jsonl"), taskID)
	assertFileContains(t, filepath.Join("artifacts", "control-plane", "events.jsonl"), taskID)
}

func TestServerTaskCanBeStopped(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		select {
		case <-time.After(500 * time.Millisecond):
			w.Header().Set("Content-Type", "text/html")
			_, _ = w.Write([]byte("<title>slow</title>"))
		case <-r.Context().Done():
			return
		}
	}))
	defer upstream.Close()

	server := NewServer("0")
	api := httptest.NewServer(server.mux)
	defer api.Close()

	taskID := createTaskViaAPI(t, api.URL, upstream.URL)
	postJSON(t, http.MethodPost, api.URL+"/api/tasks/"+taskID+"/start", nil, http.StatusOK)
	postJSON(t, http.MethodPost, api.URL+"/api/tasks/"+taskID+"/stop", nil, http.StatusOK)

	waitForTaskStatus(t, api.URL, taskID, "stopped")

	logsPayload := getJSON(t, api.URL+"/api/tasks/"+taskID+"/logs")
	logs := logsPayload["data"].([]interface{})
	found := false
	for _, raw := range logs {
		entry := raw.(map[string]interface{})
		if entry["message"] == "task stop requested" {
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("expected stop log entry, got %#v", logs)
	}

	assertFileContains(t, filepath.Join("artifacts", "control-plane", "events.jsonl"), taskID)
}

func TestTaskLifecycleMutationResponsesExposeDataMessage(t *testing.T) {
	server := NewServer("0")
	api := httptest.NewServer(server.mux)
	defer api.Close()

	taskID := createTaskViaAPI(t, api.URL, "https://example.com")
	start := postJSON(t, http.MethodPost, api.URL+"/api/tasks/"+taskID+"/start", nil, http.StatusOK)
	if start["data"].(map[string]interface{})["message"] != "Task started" {
		t.Fatalf("unexpected start payload: %#v", start)
	}
	stop := postJSON(t, http.MethodPost, api.URL+"/api/tasks/"+taskID+"/stop", nil, http.StatusOK)
	if stop["data"].(map[string]interface{})["message"] != "Task stopped" {
		t.Fatalf("unexpected stop payload: %#v", stop)
	}
}

func createTaskViaAPI(t *testing.T, baseURL string, targetURL string) string {
	t.Helper()
	payload := map[string]interface{}{
		"name": "demo",
		"url":  targetURL,
	}
	response := postJSON(t, http.MethodPost, baseURL+"/api/tasks", payload, http.StatusOK)
	data := response["data"].(map[string]interface{})
	return data["id"].(string)
}

func postJSON(t *testing.T, method string, url string, payload map[string]interface{}, expectedStatus int) map[string]interface{} {
	t.Helper()
	var body bytes.Buffer
	if payload != nil {
		if err := json.NewEncoder(&body).Encode(payload); err != nil {
			t.Fatalf("encode payload: %v", err)
		}
	}

	req, err := http.NewRequestWithContext(context.Background(), method, url, &body)
	if err != nil {
		t.Fatalf("build request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("do request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != expectedStatus {
		t.Fatalf("expected status %d, got %d", expectedStatus, resp.StatusCode)
	}

	var decoded map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&decoded); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	return decoded
}

func getJSON(t *testing.T, url string) map[string]interface{} {
	t.Helper()
	resp, err := http.Get(url)
	if err != nil {
		t.Fatalf("http get: %v", err)
	}
	defer resp.Body.Close()

	var decoded map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&decoded); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	return decoded
}

func waitForTaskStatus(t *testing.T, baseURL string, taskID string, status string) {
	t.Helper()
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		payload := getJSON(t, baseURL+"/api/tasks/"+taskID)
		task := payload["data"].(map[string]interface{})
		if task["status"] == status {
			return
		}
		time.Sleep(50 * time.Millisecond)
	}
	t.Fatalf("task %s did not reach status %s", taskID, status)
}

func assertFileContains(t *testing.T, path string, needle string) {
	t.Helper()
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		content, err := os.ReadFile(path)
		if err == nil && strings.Contains(string(content), needle) {
			return
		}
		time.Sleep(25 * time.Millisecond)
	}
	t.Fatalf("expected %s to contain %s", path, needle)
}
