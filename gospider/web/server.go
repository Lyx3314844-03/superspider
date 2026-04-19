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
	"gospider/research"
	"gospider/storage"
)

// Server - Web UI 服务器 (纯 Go 实现，无需外部依赖)
type Server struct {
	mux         *http.ServeMux
	tasks       *TaskManager
	port        string
	resultStore *storage.FileResultStore
	eventStore  *storage.FileEventStore
	research    *ResearchManager
}

// TaskManager - 任务管理器
type TaskManager struct {
	mu      sync.RWMutex
	tasks   map[string]*TaskInfo
	results map[string][]TaskResult
	logs    map[string][]TaskLog
	cancels map[string]context.CancelFunc
}

type ResearchRecord struct {
	ID        string                 `json:"id"`
	Mode      string                 `json:"mode"`
	URLs      []string               `json:"urls"`
	Status    string                 `json:"status"`
	CreatedAt time.Time              `json:"created_at"`
	Result    map[string]interface{} `json:"result,omitempty"`
}

type ResearchManager struct {
	mu      sync.RWMutex
	records []ResearchRecord
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
		research:    &ResearchManager{records: []ResearchRecord{}},
	}

	server.setupRoutes()
	return server
}

func (s *Server) setupRoutes() {
	// API 路由
	s.mux.HandleFunc("/api/tasks", s.handleTasks)
	s.mux.HandleFunc("/api/tasks/", s.handleTaskDetail)
	s.mux.HandleFunc("/api/stats", s.handleStats)
	s.mux.HandleFunc("/api/research/run", s.handleResearchRun)
	s.mux.HandleFunc("/api/research/async", s.handleResearchAsync)
	s.mux.HandleFunc("/api/research/soak", s.handleResearchSoak)
	s.mux.HandleFunc("/api/research/history", s.handleResearchHistory)

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

func (s *Server) handleResearchRun(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)
	if r.Method == "OPTIONS" {
		w.WriteHeader(http.StatusOK)
		return
	}
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	request, ok := decodeResearchRequest(w, r)
	if !ok {
		return
	}
	job, content, err := request.single()
	if err != nil {
		writeResearchError(w, err.Error(), http.StatusBadRequest)
		return
	}
	result, err := research.NewResearchRuntime().Run(job, content)
	if err != nil {
		writeResearchError(w, err.Error(), http.StatusBadRequest)
		return
	}
	s.recordResearch("run", job.SeedURLs, map[string]interface{}{"result": result})
	writeResearchJSON(w, map[string]interface{}{
		"success": true,
		"data": map[string]interface{}{
			"command": "research run",
			"runtime": "go",
			"result":  result,
		},
	})
}

func (s *Server) handleResearchAsync(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)
	if r.Method == "OPTIONS" {
		w.WriteHeader(http.StatusOK)
		return
	}
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	request, ok := decodeResearchRequest(w, r)
	if !ok {
		return
	}
	jobs, contents, err := request.multiple()
	if err != nil {
		writeResearchError(w, err.Error(), http.StatusBadRequest)
		return
	}
	runtime := research.NewAsyncResearchRuntime(&research.AsyncResearchConfig{
		MaxConcurrent: maxResearchInt(request.Concurrency, 5),
	})
	results := runtime.RunMultiple(jobs, contents)
	s.recordResearch("async", collectResearchURLs(jobs), map[string]interface{}{
		"results": results,
		"metrics": runtime.SnapshotMetrics(),
	})
	writeResearchJSON(w, map[string]interface{}{
		"success": true,
		"data": map[string]interface{}{
			"command": "research async",
			"runtime": "go",
			"results": results,
			"metrics": runtime.SnapshotMetrics(),
		},
	})
}

func (s *Server) handleResearchSoak(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)
	if r.Method == "OPTIONS" {
		w.WriteHeader(http.StatusOK)
		return
	}
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	request, ok := decodeResearchRequest(w, r)
	if !ok {
		return
	}
	jobs, contents, err := request.multiple()
	if err != nil {
		writeResearchError(w, err.Error(), http.StatusBadRequest)
		return
	}
	runtime := research.NewAsyncResearchRuntime(&research.AsyncResearchConfig{
		MaxConcurrent: maxResearchInt(request.Concurrency, 5),
	})
	report := runtime.RunSoak(jobs, contents, maxResearchInt(request.Rounds, 1))
	s.recordResearch("soak", collectResearchURLs(jobs), map[string]interface{}{"report": report})
	writeResearchJSON(w, map[string]interface{}{
		"success": true,
		"data": map[string]interface{}{
			"command": "research soak",
			"runtime": "go",
			"report":  report,
		},
	})
}

func (s *Server) handleResearchHistory(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)
	if r.Method == "OPTIONS" {
		w.WriteHeader(http.StatusOK)
		return
	}
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	records := s.research.list()
	writeResearchJSON(w, map[string]interface{}{
		"success": true,
		"data":    records,
	})
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
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; margin: 0; background: linear-gradient(135deg, #f4f7fb 0%, #e8eefc 100%); color: #1f2937; }
        .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
        header { background: white; border-radius: 16px; padding: 24px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08); margin-bottom: 20px; }
        h1 { margin: 0 0 8px 0; color: #1d4ed8; }
        p { color: #475569; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 20px; }
        .panel { background: white; border-radius: 16px; padding: 20px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08); }
        .panel h2 { margin: 0 0 14px 0; font-size: 18px; color: #0f172a; }
        .field { margin-bottom: 12px; }
        .field label { display: block; font-size: 13px; color: #475569; margin-bottom: 6px; }
        .field input, .field textarea, .field select { width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 10px; font-size: 14px; }
        .field textarea { min-height: 96px; resize: vertical; }
        .btn-row { display: flex; gap: 10px; flex-wrap: wrap; }
        button { border: none; border-radius: 10px; padding: 11px 16px; cursor: pointer; font-weight: 600; }
        .primary { background: #2563eb; color: white; }
        .secondary { background: #e2e8f0; color: #0f172a; }
        .pill { display: inline-block; padding: 4px 10px; background: #dbeafe; color: #1d4ed8; border-radius: 999px; font-size: 12px; font-weight: 700; margin-bottom: 12px; }
        pre { background: #0f172a; color: #dbeafe; border-radius: 12px; padding: 14px; overflow: auto; max-height: 420px; font-size: 12px; }
        .links a { color: #2563eb; text-decoration: none; display: inline-block; margin-right: 12px; margin-top: 6px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🕷️ GoSpider 控制台</h1>
            <p>基础任务控制和研究运行时已经合并到同一个 Web UI。下面的 research 面板可以直接触发 run / async / soak。</p>
            <div class="links">
                <a href="/api/tasks">/api/tasks</a>
                <a href="/api/stats">/api/stats</a>
                <a href="/api/research/run">/api/research/run</a>
            </div>
        </header>
        <div class="grid">
            <section class="panel">
                <div class="pill">Task Panel</div>
                <h2>任务面板</h2>
                <div class="field">
                    <label>任务名称</label>
                    <input id="task-name" value="demo-task" />
                </div>
                <div class="field">
                    <label>URL</label>
                    <input id="task-url" value="https://example.com" />
                </div>
                <div class="btn-row">
                    <button class="primary" onclick="createTask()">创建任务</button>
                    <button class="secondary" onclick="refreshTasks()">刷新任务</button>
                </div>
                <pre id="task-output">等待任务数据...</pre>
            </section>
            <section class="panel">
                <div class="pill">Research Panel</div>
                <h2>Research 面板</h2>
                <div class="field">
                    <label>模式</label>
                    <select id="research-mode">
                        <option value="run">run</option>
                        <option value="async">async</option>
                        <option value="soak">soak</option>
                    </select>
                </div>
                <div class="field">
                    <label>URL 列表（每行一个）</label>
                    <textarea id="research-urls">https://example.com/article
https://example.com/list</textarea>
                </div>
                <div class="field">
                    <label>Schema JSON</label>
                    <textarea id="research-schema">{"properties":{"title":{"type":"string"}}}</textarea>
                </div>
                <div class="field">
                    <label>Inline Content</label>
                    <textarea id="research-content"><title>Research Demo</title></textarea>
                </div>
                <div class="btn-row">
                    <button class="primary" onclick="runResearch()">执行 research</button>
                    <button class="secondary" onclick="loadResearchExample()">示例</button>
                </div>
                <pre id="research-output">等待 research 结果...</pre>
                <div class="pill" style="margin-top:16px;">Recent Research</div>
                <pre id="research-history">等待 research 历史...</pre>
            </section>
        </div>
    </div>
    <script>
        async function refreshTasks() {
            const res = await fetch('/api/tasks');
            document.getElementById('task-output').textContent = JSON.stringify(await res.json(), null, 2);
        }
        async function createTask() {
            const payload = {
                name: document.getElementById('task-name').value,
                url: document.getElementById('task-url').value
            };
            const res = await fetch('/api/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            document.getElementById('task-output').textContent = JSON.stringify(await res.json(), null, 2);
        }
        function loadResearchExample() {
            document.getElementById('research-schema').value = '{"properties":{"title":{"type":"string"},"price":{"type":"string"}}}';
            document.getElementById('research-content').value = '<title>Research Demo</title>\nprice: 42';
        }
        async function runResearch() {
            const mode = document.getElementById('research-mode').value;
            const urls = document.getElementById('research-urls').value.split('\n').map(v => v.trim()).filter(Boolean);
            const payload = {
                urls,
                url: urls[0] || '',
                content: document.getElementById('research-content').value,
                schema_json: document.getElementById('research-schema').value,
                concurrency: 2,
                rounds: 2
            };
            const res = await fetch('/api/research/' + mode, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            document.getElementById('research-output').textContent = JSON.stringify(await res.json(), null, 2);
            refreshResearchHistory();
        }
        async function refreshResearchHistory() {
            const res = await fetch('/api/research/history');
            document.getElementById('research-history').textContent = JSON.stringify(await res.json(), null, 2);
        }
        refreshTasks();
        refreshResearchHistory();
    </script>
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

type researchRequest struct {
	URL         string                 `json:"url"`
	URLs        []string               `json:"urls"`
	Content     string                 `json:"content"`
	Contents    []string               `json:"contents"`
	Schema      map[string]interface{} `json:"schema"`
	SchemaJSON  string                 `json:"schema_json"`
	Output      map[string]interface{} `json:"output"`
	Concurrency int                    `json:"concurrency"`
	Rounds      int                    `json:"rounds"`
	Policy      map[string]interface{} `json:"policy"`
}

func decodeResearchRequest(w http.ResponseWriter, r *http.Request) (researchRequest, bool) {
	var request researchRequest
	if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
		writeResearchError(w, "invalid research request body", http.StatusBadRequest)
		return researchRequest{}, false
	}
	return request, true
}

func (r researchRequest) single() (research.ResearchJob, string, error) {
	urls := researchURLs(r)
	if len(urls) == 0 {
		return research.ResearchJob{}, "", fmt.Errorf("research request requires url or urls")
	}
	schema, err := r.schemaMap()
	if err != nil {
		return research.ResearchJob{}, "", err
	}
	return research.ResearchJob{
		SeedURLs:      []string{urls[0]},
		ExtractSchema: schema,
		Output:        cloneResearchMap(r.Output),
		Policy:        cloneResearchMap(r.Policy),
	}, r.Content, nil
}

func (r researchRequest) multiple() ([]research.ResearchJob, []string, error) {
	urls := researchURLs(r)
	if len(urls) == 0 {
		return nil, nil, fmt.Errorf("research request requires url or urls")
	}
	schema, err := r.schemaMap()
	if err != nil {
		return nil, nil, err
	}
	jobs := make([]research.ResearchJob, 0, len(urls))
	contents := make([]string, 0, len(urls))
	for index, url := range urls {
		jobs = append(jobs, research.ResearchJob{
			SeedURLs:      []string{url},
			ExtractSchema: cloneResearchMap(schema),
			Output:        cloneResearchMap(r.Output),
			Policy:        cloneResearchMap(r.Policy),
		})
		if index < len(r.Contents) && strings.TrimSpace(r.Contents[index]) != "" {
			contents = append(contents, r.Contents[index])
		} else {
			contents = append(contents, r.Content)
		}
	}
	return jobs, contents, nil
}

func (r researchRequest) schemaMap() (map[string]interface{}, error) {
	if len(r.Schema) > 0 {
		return cloneResearchMap(r.Schema), nil
	}
	if strings.TrimSpace(r.SchemaJSON) == "" {
		return map[string]interface{}{}, nil
	}
	schema := map[string]interface{}{}
	if err := json.Unmarshal([]byte(r.SchemaJSON), &schema); err != nil {
		return nil, fmt.Errorf("invalid schema_json: %w", err)
	}
	return schema, nil
}

func researchURLs(r researchRequest) []string {
	urls := make([]string, 0, len(r.URLs)+1)
	if strings.TrimSpace(r.URL) != "" {
		urls = append(urls, r.URL)
	}
	for _, url := range r.URLs {
		if strings.TrimSpace(url) != "" {
			urls = append(urls, url)
		}
	}
	return urls
}

func writeResearchJSON(w http.ResponseWriter, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(payload)
}

func writeResearchError(w http.ResponseWriter, message string, status int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"success": false,
		"error":   message,
	})
}

func cloneResearchMap(source map[string]interface{}) map[string]interface{} {
	if source == nil {
		return map[string]interface{}{}
	}
	clone := make(map[string]interface{}, len(source))
	for key, value := range source {
		clone[key] = value
	}
	return clone
}

func maxResearchInt(value int, defaultValue int) int {
	if value <= 0 {
		return defaultValue
	}
	return value
}

func collectResearchURLs(jobs []research.ResearchJob) []string {
	urls := make([]string, 0, len(jobs))
	for _, job := range jobs {
		if len(job.SeedURLs) > 0 {
			urls = append(urls, job.SeedURLs[0])
		}
	}
	return urls
}

func (m *ResearchManager) list() []ResearchRecord {
	m.mu.RLock()
	defer m.mu.RUnlock()
	result := make([]ResearchRecord, len(m.records))
	copy(result, m.records)
	return result
}

func (s *Server) recordResearch(mode string, urls []string, payload map[string]interface{}) {
	record := ResearchRecord{
		ID:        generateTaskID(),
		Mode:      mode,
		URLs:      append([]string{}, urls...),
		Status:    "completed",
		CreatedAt: time.Now(),
		Result:    cloneResearchMap(payload),
	}
	s.research.mu.Lock()
	s.research.records = append([]ResearchRecord{record}, s.research.records...)
	if len(s.research.records) > 20 {
		s.research.records = s.research.records[:20]
	}
	s.research.mu.Unlock()
	if err := persistResearchRecord(record); err != nil {
		// best-effort history persistence should not break runtime responses
	}
}

func persistResearchRecord(record ResearchRecord) error {
	path := filepath.Join("artifacts", "control-plane", "research-history.jsonl")
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	handle, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
	if err != nil {
		return err
	}
	defer handle.Close()
	encoded, err := json.Marshal(record)
	if err != nil {
		return err
	}
	if _, err := handle.Write(append(encoded, '\n')); err != nil {
		return err
	}
	return handle.Sync()
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
