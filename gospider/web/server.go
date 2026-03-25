package web

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"sync"
	"time"

	"gospider/core"
)

// Server - Web UI 服务器 (纯 Go 实现，无需外部依赖)
type Server struct {
	mux  *http.ServeMux
	tasks *TaskManager
	port string
}

// TaskManager - 任务管理器
type TaskManager struct {
	mu    sync.RWMutex
	tasks map[string]*TaskInfo
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

// NewServer - 创建 Web 服务器
func NewServer(port string) *Server {
	server := &Server{
		mux:  http.NewServeMux(),
		tasks: &TaskManager{
			tasks: make(map[string]*TaskInfo),
		},
		port: port,
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
	s.tasks.mu.RLock()
	defer s.tasks.mu.RUnlock()

	taskList := make([]*TaskInfo, 0, len(s.tasks.tasks))
	for _, task := range s.tasks.tasks {
		taskList = append(taskList, task)
	}

	response := map[string]interface{}{
		"success": true,
		"data":    taskList,
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
	task := &TaskInfo{
		ID:        id,
		Name:      req.Name,
		URL:       req.URL,
		Status:    "pending",
		Config:    req.Config,
		CreatedAt: time.Now(),
		Stats:     TaskStats{},
	}

	s.tasks.tasks[id] = task

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
	defer s.tasks.mu.Unlock()

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

	now := time.Now()
	task.Status = "running"
	task.StartedAt = &now

	// TODO: 实际启动爬虫逻辑
	// go s.runTask(task)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "Task started",
	})
}

func (s *Server) stopTask(w http.ResponseWriter, r *http.Request, id string) {
	s.tasks.mu.Lock()
	defer s.tasks.mu.Unlock()

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

	now := time.Now()
	task.Status = "stopped"
	task.FinishedAt = &now

	// TODO: 实际停止爬虫逻辑

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "Task stopped",
	})
}

func (s *Server) deleteTask(w http.ResponseWriter, r *http.Request, id string) {
	s.tasks.mu.Lock()
	defer s.tasks.mu.Unlock()

	delete(s.tasks.tasks, id)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "Task deleted",
	})
}

func (s *Server) getTaskResults(w http.ResponseWriter, r *http.Request, id string) {
	// TODO: 实现结果查询
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    []interface{}{},
	})
}

func (s *Server) getTaskLogs(w http.ResponseWriter, r *http.Request, id string) {
	// TODO: 实现日志查询
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    []interface{}{},
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
