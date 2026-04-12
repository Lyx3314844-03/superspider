package web

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"gospider/core"
	"gospider/events"
	"gospider/graph"
	"gospider/storage"
)

// Server - Web UI 服务器 (纯 Go 实现，无需外部依赖)
type Server struct {
	mux         *http.ServeMux
	tasks       *TaskManager
	port        string
	resultStore *storage.FileResultStore
	eventStore  *storage.FileEventStore
}

// TaskManager - 任务管理器
type TaskManager struct {
	mu      sync.RWMutex
	tasks   map[string]*TaskInfo
	results map[string][]TaskResult
	logs    map[string][]TaskLog
	cancels map[string]context.CancelFunc
}

// TaskInfo - 任务信息
type TaskInfo struct {
	ID         string                 `json:"id"`
	Name       string                 `json:"name"`
	URL        string                 `json:"url"`
	Status     string                 `json:"status"`
	Config     map[string]interface{} `json:"config"`
	CreatedAt  time.Time              `json:"created_at"`
	StartedAt  *time.Time             `json:"started_at,omitempty"`
	FinishedAt *time.Time             `json:"finished_at,omitempty"`
	Stats      TaskStats              `json:"stats"`
}

// TaskStats - 任务统计
type TaskStats struct {
	TotalRequests   int `json:"total_requests"`
	SuccessRequests int `json:"success_requests"`
	FailedRequests  int `json:"failed_requests"`
}

// TaskResult - 任务结果
type TaskResult struct {
	ID           string                  `json:"id"`
	TaskID       string                  `json:"task_id"`
	URL          string                  `json:"url"`
	FinalURL     string                  `json:"final_url"`
	Status       string                  `json:"status"`
	HTTPStatus   int                     `json:"http_status"`
	ContentType  string                  `json:"content_type"`
	Title        string                  `json:"title,omitempty"`
	Bytes        int                     `json:"bytes"`
	DurationMs   int64                   `json:"duration_ms"`
	CreatedAt    time.Time               `json:"created_at"`
	Artifacts    map[string]TaskArtifact `json:"artifacts,omitempty"`
	ArtifactRefs map[string]TaskArtifact `json:"artifact_refs,omitempty"`
}

type TaskArtifact struct {
	Kind   string                 `json:"kind"`
	Path   string                 `json:"path,omitempty"`
	RootID string                 `json:"root_id,omitempty"`
	Stats  map[string]interface{} `json:"stats,omitempty"`
}

// TaskLog - 任务日志
type TaskLog struct {
	ID        string    `json:"id"`
	TaskID    string    `json:"task_id"`
	Level     string    `json:"level"`
	Message   string    `json:"message"`
	CreatedAt time.Time `json:"created_at"`
}

// NewServer - 创建 Web 服务器
func NewServer(port string) *Server {
	server := &Server{
		mux: http.NewServeMux(),
		tasks: &TaskManager{
			tasks:   make(map[string]*TaskInfo),
			results: make(map[string][]TaskResult),
			logs:    make(map[string][]TaskLog),
			cancels: make(map[string]context.CancelFunc),
		},
		port:        port,
		resultStore: storage.NewFileResultStore(filepath.Join("artifacts", "control-plane", "results.jsonl")),
		eventStore:  storage.NewFileEventStore(filepath.Join("artifacts", "control-plane", "events.jsonl")),
	}

	server.setupRoutes()
	return server
}

func (s *Server) setupRoutes() {
	// API 路由
	s.mux.HandleFunc("/api/tasks", s.handleTasks)
	s.mux.HandleFunc("/api/tasks/", s.handleTaskDetail)
	s.mux.HandleFunc("/api/stats", s.handleStats)

	// 页面路由
	s.mux.HandleFunc("/", s.indexPage)
}

func (s *Server) handleTasks(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)

	if r.Method == "OPTIONS" {
		w.WriteHeader(http.StatusOK)
		return
	}

	switch r.Method {
	case "GET":
		s.listTasks(w, r)
	case "POST":
		s.createTask(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func (s *Server) handleTaskDetail(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)

	if r.Method == "OPTIONS" {
		w.WriteHeader(http.StatusOK)
		return
	}

	// 解析路径 /api/tasks/{id}/{action}
	path := strings.TrimPrefix(r.URL.Path, "/api/tasks/")
	parts := strings.Split(path, "/")

	if len(parts) == 0 || parts[0] == "" {
		http.Error(w, "Invalid path", http.StatusBadRequest)
		return
	}

	id := parts[0]
	action := ""
	if len(parts) > 1 {
		action = parts[1]
	}

	switch r.Method {
	case "GET":
		if action == "" {
			s.getTask(w, r, id)
		} else if action == "results" {
			s.getTaskResults(w, r, id)
		} else if action == "artifacts" {
			s.getTaskArtifacts(w, r, id)
		} else if action == "logs" {
			s.getTaskLogs(w, r, id)
		} else {
			http.Error(w, "Not found", http.StatusNotFound)
		}
	case "POST":
		switch action {
		case "start":
			s.startTask(w, r, id)
		case "stop":
			s.stopTask(w, r, id)
		default:
			http.Error(w, "Not found", http.StatusNotFound)
		}
	case "DELETE":
		s.deleteTask(w, r, id)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func (s *Server) handleStats(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)

	if r.Method != "GET" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	s.tasks.mu.RLock()
	defer s.tasks.mu.RUnlock()

	var total, running, completed int
	for _, task := range s.tasks.tasks {
		total++
		if task.Status == "running" {
			running++
		}
		if task.Status == "completed" {
			completed++
		}
	}

	response := map[string]interface{}{
		"success": true,
		"data": map[string]int{
			"total_tasks":     total,
			"running_tasks":   running,
			"completed_tasks": completed,
		},
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// API Handlers

func (s *Server) listTasks(w http.ResponseWriter, r *http.Request) {
	page, perPage := paginationParams(r, 1, 20)
	s.tasks.mu.RLock()
	taskList := make([]*TaskInfo, 0, len(s.tasks.tasks))
	for _, task := range s.tasks.tasks {
		taskList = append(taskList, task)
	}
	s.tasks.mu.RUnlock()
	start := (page - 1) * perPage
	if start < 0 {
		start = 0
	}
	end := start + perPage
	total := len(taskList)
	if start > total {
		start = total
	}
	if end > total {
		end = total
	}

	response := map[string]interface{}{
		"success": true,
		"data":    taskList[start:end],
		"pagination": map[string]int{
			"page":     page,
			"per_page": perPage,
			"total":    total,
		},
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func (s *Server) createTask(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Name   string                 `json:"name"`
		URL    string                 `json:"url"`
		Config map[string]interface{} `json:"config"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	if req.URL == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   "URL is required",
		})
		return
	}

	s.tasks.mu.Lock()
	defer s.tasks.mu.Unlock()

	id := generateTaskID()
	name := strings.TrimSpace(req.Name)
	if name == "" {
		name = "Unnamed Task"
	}
	task := &TaskInfo{
		ID:        id,
		Name:      name,
		URL:       req.URL,
		Status:    "pending",
		Config:    req.Config,
		CreatedAt: time.Now(),
		Stats:     TaskStats{},
	}

	s.tasks.tasks[id] = task
	s.tasks.logs[id] = append(s.tasks.logs[id], TaskLog{
		ID:        generateTaskID(),
		TaskID:    id,
		Level:     "info",
		Message:   "task created",
		CreatedAt: time.Now(),
	})
	s.persistEvent(events.TopicTaskCreated, map[string]interface{}{
		"task_id": id,
		"state":   "pending",
		"url":     task.URL,
		"runtime": "go",
	})

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    map[string]string{"id": id},
	})
}

func (s *Server) getTask(w http.ResponseWriter, r *http.Request, id string) {
	s.tasks.mu.RLock()
	defer s.tasks.mu.RUnlock()

	task, exists := s.tasks.tasks[id]
	if !exists {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   "Task not found",
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    task,
	})
}

func (s *Server) startTask(w http.ResponseWriter, r *http.Request, id string) {
	s.tasks.mu.Lock()
	task, exists := s.tasks.tasks[id]
	if !exists {
		s.tasks.mu.Unlock()
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   "Task not found",
		})
		return
	}

	if task.Status == "running" {
		s.tasks.mu.Unlock()
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusConflict)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   "Task is already running",
		})
		return
	}

	now := time.Now()
	task.Status = "running"
	task.StartedAt = &now
	task.FinishedAt = nil
	task.Stats = TaskStats{}

	ctx, cancel := context.WithCancel(context.Background())
	s.tasks.cancels[id] = cancel
	s.tasks.logs[id] = append(s.tasks.logs[id], TaskLog{
		ID:        generateTaskID(),
		TaskID:    id,
		Level:     "info",
		Message:   "task started",
		CreatedAt: now,
	})
	taskURL := task.URL
	s.persistEvent(events.TopicTaskRunning, map[string]interface{}{
		"task_id": id,
		"state":   "running",
		"url":     taskURL,
		"runtime": "go",
	})
	s.tasks.mu.Unlock()

	go s.runTask(id, taskURL, ctx)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "Task started",
		"data":    map[string]string{"message": "Task started"},
	})
}

func (s *Server) stopTask(w http.ResponseWriter, r *http.Request, id string) {
	s.tasks.mu.Lock()
	task, exists := s.tasks.tasks[id]
	if !exists {
		s.tasks.mu.Unlock()
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   "Task not found",
		})
		return
	}

	if cancel, ok := s.tasks.cancels[id]; ok {
		cancel()
		delete(s.tasks.cancels, id)
	}

	now := time.Now()
	task.Status = "stopped"
	task.FinishedAt = &now
	s.tasks.logs[id] = append(s.tasks.logs[id], TaskLog{
		ID:        generateTaskID(),
		TaskID:    id,
		Level:     "warning",
		Message:   "task stop requested",
		CreatedAt: now,
	})
	s.persistEvent(events.TopicTaskCancelled, map[string]interface{}{
		"task_id": id,
		"state":   "stopped",
		"url":     task.URL,
		"runtime": "go",
	})
	s.tasks.mu.Unlock()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "Task stopped",
		"data":    map[string]string{"message": "Task stopped"},
	})
}

func (s *Server) deleteTask(w http.ResponseWriter, r *http.Request, id string) {
	s.tasks.mu.Lock()
	if cancel, ok := s.tasks.cancels[id]; ok {
		cancel()
		delete(s.tasks.cancels, id)
	}

	delete(s.tasks.tasks, id)
	delete(s.tasks.results, id)
	delete(s.tasks.logs, id)
	s.tasks.mu.Unlock()
	s.persistEvent(events.TopicTaskDeleted, map[string]interface{}{
		"task_id": id,
		"runtime": "go",
	})

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "Task deleted",
		"data":    map[string]string{"message": "Task deleted"},
	})
}

func (s *Server) getTaskResults(w http.ResponseWriter, r *http.Request, id string) {
	page, perPage := paginationParams(r, 1, 20)

	s.tasks.mu.RLock()
	results := append([]TaskResult(nil), s.tasks.results[id]...)
	s.tasks.mu.RUnlock()

	paged, total := paginateResults(results, page, perPage)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    paged,
		"pagination": map[string]int{
			"page":     page,
			"per_page": perPage,
			"total":    total,
		},
	})
}

func (s *Server) getTaskArtifacts(w http.ResponseWriter, r *http.Request, id string) {
	s.tasks.mu.RLock()
	results := append([]TaskResult(nil), s.tasks.results[id]...)
	s.tasks.mu.RUnlock()

	artifacts := map[string]interface{}{}
	for _, result := range results {
		for name, artifact := range result.Artifacts {
			if _, exists := artifacts[name]; !exists {
				artifacts[name] = artifact
			}
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    artifacts,
	})
}

func (s *Server) getTaskLogs(w http.ResponseWriter, r *http.Request, id string) {
	page, perPage := paginationParams(r, 1, 50)

	s.tasks.mu.RLock()
	logs := append([]TaskLog(nil), s.tasks.logs[id]...)
	s.tasks.mu.RUnlock()

	paged, total := paginateLogs(logs, page, perPage)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    paged,
		"pagination": map[string]int{
			"page":     page,
			"per_page": perPage,
			"total":    total,
		},
	})
}

// Page Handlers

func (s *Server) indexPage(w http.ResponseWriter, r *http.Request) {
	html := `<!DOCTYPE html>
<html>
<head>
    <title>GoSpider Web UI</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        .api-link { color: #0066cc; }
    </style>
</head>
<body>
    <h1>🕷️ GoSpider Web UI</h1>
    <p>Welcome to GoSpider Web UI</p>
    <p>API Endpoints:</p>
    <ul>
        <li><a href="/api/tasks" class="api-link">GET /api/tasks</a> - List all tasks</li>
        <li><a href="/api/stats" class="api-link">GET /api/stats</a> - Get statistics</li>
    </ul>
</body>
</html>`
	w.Header().Set("Content-Type", "text/html")
	w.Write([]byte(html))
}

// Run - 启动服务器
func (s *Server) Run() error {
	addr := ":" + s.port
	fmt.Printf("🚀 Starting web UI at http://localhost%s\n", addr)
	return http.ListenAndServe(addr, s.mux)
}

func (s *Server) runTask(id string, targetURL string, ctx context.Context) {
	started := time.Now()
	s.appendLog(id, "info", fmt.Sprintf("fetching %s", targetURL))

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, targetURL, nil)
	if err != nil {
		s.finishTaskFailure(id, started, fmt.Sprintf("invalid request: %v", err))
		return
	}

	client := &http.Client{Timeout: 20 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		if ctx.Err() != nil {
			s.appendLog(id, "warning", "task cancelled before completion")
			return
		}
		s.finishTaskFailure(id, started, fmt.Sprintf("request failed: %v", err))
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(io.LimitReader(resp.Body, 1024*1024))
	if err != nil {
		s.finishTaskFailure(id, started, fmt.Sprintf("read failed: %v", err))
		return
	}

	result := TaskResult{
		ID:          generateTaskID(),
		TaskID:      id,
		URL:         targetURL,
		FinalURL:    resp.Request.URL.String(),
		Status:      "completed",
		HTTPStatus:  resp.StatusCode,
		ContentType: resp.Header.Get("Content-Type"),
		Title:       extractHTMLTitle(body),
		Bytes:       len(body),
		DurationMs:  time.Since(started).Milliseconds(),
		CreatedAt:   time.Now(),
	}
	if artifact, ok := buildGraphArtifact("go", id, result.ID, string(body)); ok {
		result.Artifacts = map[string]TaskArtifact{"graph": artifact}
		result.ArtifactRefs = map[string]TaskArtifact{"graph": artifact}
	}

	now := time.Now()
	s.tasks.mu.Lock()
	defer s.tasks.mu.Unlock()

	task, exists := s.tasks.tasks[id]
	if !exists {
		return
	}
	if task.Status == "stopped" {
		s.tasks.logs[id] = append(s.tasks.logs[id], TaskLog{
			ID:        generateTaskID(),
			TaskID:    id,
			Level:     "warning",
			Message:   "task finished after stop request; result discarded",
			CreatedAt: now,
		})
		return
	}

	task.Status = "completed"
	task.FinishedAt = &now
	task.Stats.TotalRequests = 1
	if resp.StatusCode >= 200 && resp.StatusCode < 400 {
		task.Stats.SuccessRequests = 1
	} else {
		task.Stats.FailedRequests = 1
		result.Status = "failed"
		task.Status = "failed"
	}
	s.tasks.results[id] = append(s.tasks.results[id], result)
	s.tasks.logs[id] = append(s.tasks.logs[id], TaskLog{
		ID:        generateTaskID(),
		TaskID:    id,
		Level:     "info",
		Message:   fmt.Sprintf("task finished with status %d in %dms", resp.StatusCode, result.DurationMs),
		CreatedAt: now,
	})
	s.persistResult(result)
	if task.Status == "completed" {
		s.persistEvent(events.TopicTaskSucceeded, map[string]interface{}{
			"task_id":     id,
			"state":       task.Status,
			"url":         targetURL,
			"status_code": resp.StatusCode,
			"runtime":     "go",
		})
	} else {
		s.persistEvent(events.TopicTaskFailed, map[string]interface{}{
			"task_id":     id,
			"state":       task.Status,
			"url":         targetURL,
			"status_code": resp.StatusCode,
			"runtime":     "go",
		})
	}
	delete(s.tasks.cancels, id)
}

func (s *Server) finishTaskFailure(id string, started time.Time, message string) {
	now := time.Now()
	s.tasks.mu.Lock()
	defer s.tasks.mu.Unlock()

	task, exists := s.tasks.tasks[id]
	if !exists {
		return
	}
	if task.Status == "stopped" {
		return
	}

	task.Status = "failed"
	task.FinishedAt = &now
	task.Stats.TotalRequests = 1
	task.Stats.FailedRequests = 1
	s.tasks.logs[id] = append(s.tasks.logs[id], TaskLog{
		ID:        generateTaskID(),
		TaskID:    id,
		Level:     "error",
		Message:   message,
		CreatedAt: now,
	})
	result := TaskResult{
		ID:         generateTaskID(),
		TaskID:     id,
		URL:        task.URL,
		FinalURL:   task.URL,
		Status:     "failed",
		DurationMs: time.Since(started).Milliseconds(),
		CreatedAt:  now,
	}
	s.tasks.results[id] = append(s.tasks.results[id], result)
	s.persistResult(result)
	s.persistEvent(events.TopicTaskFailed, map[string]interface{}{
		"task_id": id,
		"state":   "failed",
		"url":     task.URL,
		"runtime": "go",
		"error":   message,
	})
	delete(s.tasks.cancels, id)
}

func (s *Server) appendLog(id string, level string, message string) {
	s.tasks.mu.Lock()
	defer s.tasks.mu.Unlock()
	s.tasks.logs[id] = append(s.tasks.logs[id], TaskLog{
		ID:        generateTaskID(),
		TaskID:    id,
		Level:     level,
		Message:   message,
		CreatedAt: time.Now(),
	})
	s.persistEvent("task:log", map[string]interface{}{
		"task_id": id,
		"level":   level,
		"message": message,
		"runtime": "go",
	})
}

func paginationParams(r *http.Request, defaultPage int, defaultPerPage int) (int, int) {
	page := defaultPage
	perPage := defaultPerPage

	if raw := r.URL.Query().Get("page"); raw != "" {
		if value, err := strconv.Atoi(raw); err == nil && value > 0 {
			page = value
		}
	}
	if raw := r.URL.Query().Get("per_page"); raw != "" {
		if value, err := strconv.Atoi(raw); err == nil && value > 0 {
			perPage = value
		}
	}
	return page, perPage
}

func paginateResults(results []TaskResult, page int, perPage int) ([]TaskResult, int) {
	total := len(results)
	start := (page - 1) * perPage
	if start >= total {
		return []TaskResult{}, total
	}
	end := start + perPage
	if end > total {
		end = total
	}
	return results[start:end], total
}

func paginateLogs(logs []TaskLog, page int, perPage int) ([]TaskLog, int) {
	total := len(logs)
	start := (page - 1) * perPage
	if start >= total {
		return []TaskLog{}, total
	}
	end := start + perPage
	if end > total {
		end = total
	}
	return logs[start:end], total
}

func extractHTMLTitle(body []byte) string {
	content := string(body)
	lower := strings.ToLower(content)
	start := strings.Index(lower, "<title>")
	end := strings.Index(lower, "</title>")
	if start == -1 || end == -1 || end <= start+7 {
		return ""
	}
	return strings.TrimSpace(content[start+7 : end])
}

func (s *Server) persistResult(result TaskResult) {
	if s.resultStore == nil {
		return
	}
	_ = s.resultStore.Put(storage.ResultRecord{
		ID:         result.ID,
		Runtime:    "go",
		State:      result.Status,
		URL:        result.FinalURL,
		StatusCode: result.HTTPStatus,
		Extract: map[string]interface{}{
			"title":        result.Title,
			"content_type": result.ContentType,
			"bytes":        result.Bytes,
			"duration_ms":  result.DurationMs,
			"task_id":      result.TaskID,
			"artifacts":    result.Artifacts,
		},
		UpdatedAt: result.CreatedAt,
	})
}

func buildGraphArtifact(runtime string, taskID string, resultID string, html string) (TaskArtifact, bool) {
	if strings.TrimSpace(html) == "" {
		return TaskArtifact{}, false
	}
	builder := graph.NewBuilder()
	if err := builder.BuildFromHTML(html); err != nil {
		return TaskArtifact{}, false
	}
	payload := map[string]interface{}{
		"root_id": builder.RootID,
		"nodes":   builder.Nodes,
		"edges":   builder.Edges,
		"stats":   builder.Stats(),
	}
	path := filepath.Join("artifacts", "control-plane", "graphs", fmt.Sprintf("%s-%s-%s.json", runtime, taskID, resultID))
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return TaskArtifact{}, false
	}
	encoded, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return TaskArtifact{}, false
	}
	if err := os.WriteFile(path, encoded, 0o644); err != nil {
		return TaskArtifact{}, false
	}
	return TaskArtifact{
		Kind:   "graph",
		Path:   path,
		RootID: builder.RootID,
		Stats:  intMapToInterfaceMap(builder.Stats()),
	}, true
}

func intMapToInterfaceMap(source map[string]int) map[string]interface{} {
	result := make(map[string]interface{}, len(source))
	for key, value := range source {
		result[key] = value
	}
	return result
}

func (s *Server) persistEvent(topic string, payload map[string]interface{}) {
	if s.eventStore == nil {
		return
	}
	_ = s.eventStore.Put(events.New(topic, payload))
}

// AddTask - 添加任务（供内部使用）
func (s *Server) AddTask(task *TaskInfo) {
	s.tasks.mu.Lock()
	defer s.tasks.mu.Unlock()
	s.tasks.tasks[task.ID] = task
}

// UpdateTaskStats - 更新任务统计（供内部使用）
func (s *Server) UpdateTaskStats(id string, stats TaskStats) {
	s.tasks.mu.Lock()
	defer s.tasks.mu.Unlock()
	if task, exists := s.tasks.tasks[id]; exists {
		task.Stats = stats
	}
}

// generateTaskID - 生成任务 ID
func generateTaskID() string {
	return time.Now().Format("20060102150405")
}

// enableCORS - 启用 CORS
func enableCORS(w http.ResponseWriter) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
}

// CreateSpider - 根据任务创建爬虫实例
func CreateSpider(task *TaskInfo) *core.Spider {
	config := core.DefaultSpiderConfig()

	if task.Config != nil {
		if concurrency, ok := task.Config["concurrency"].(float64); ok {
			config.Concurrency = int(concurrency)
		}
		if depth, ok := task.Config["max_depth"].(float64); ok {
			config.MaxDepth = int(depth)
		}
	}

	return core.NewSpider(config)
}
