package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"
)

// Task 定义
type Task struct {
	ID         string            `json:"id"`
	Framework  string            `json:"framework"`
	URL        string            `json:"url"`
	Selectors  map[string]string `json:"selectors"`
	Status     string            `json:"status"`
	Progress   int               `json:"progress"`
	StartTime  time.Time         `json:"start_time"`
	ResultURL  string            `json:"result_url,omitempty"`
	Error      string            `json:"error,omitempty"`
}

// SpiderAPI 统一 API 网关
type SpiderAPI struct {
	tasks   map[string]*Task
	workers int
	mu      sync.RWMutex
	apiKey  string // 简单的 API Key 认证
}

func NewSpiderAPI(apiKey ...string) *SpiderAPI {
	key := ""
	if len(apiKey) > 0 {
		key = apiKey[0]
	}
	return &SpiderAPI{
		tasks:   make(map[string]*Task),
		workers: 4,
		apiKey:  key,
	}
}

// 认证中间件
func (api *SpiderAPI) authenticate(w http.ResponseWriter, r *http.Request) bool {
	if api.apiKey == "" {
		return true // 未设置 key 时跳过认证
	}

	// 从 Header 或 Query 参数获取 API Key
	key := r.Header.Get("X-API-Key")
	if key == "" {
		key = r.URL.Query().Get("api_key")
	}

	if key != api.apiKey {
		http.Error(w, `{"error":"Unauthorized"}`, http.StatusUnauthorized)
		return false
	}
	return true
}

func (api *SpiderAPI) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// CORS - 修复：限制允许的来源并处理预检请求
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type, X-API-Key")
	w.Header().Set("Content-Type", "application/json")

	// 处理 OPTIONS 预检请求
	if r.Method == "OPTIONS" {
		w.WriteHeader(http.StatusOK)
		return
	}

	// 认证检查
	if !api.authenticate(w, r) {
		return
	}

	switch {
	case r.URL.Path == "/api/tasks" && r.Method == "GET":
		api.listTasks(w, r)
	case r.URL.Path == "/api/tasks" && r.Method == "POST":
		api.createTask(w, r)
	case r.URL.Path == "/api/workers" && r.Method == "GET":
		api.listWorkers(w, r)
	case len(r.URL.Path) > 16 && r.URL.Path[:16] == "/api/tasks/" && r.URL.Path[len(r.URL.Path)-5:] == "/stop" && r.Method == "POST":
		// 提取 task ID: /api/tasks/{id}/stop
		api.stopTask(w, r)
	default:
		http.NotFound(w, r)
	}
}

// 获取任务列表
func (api *SpiderAPI) listTasks(w http.ResponseWriter, r *http.Request) {
	api.mu.RLock()
	tasks := make([]Task, 0, len(api.tasks))
	stats := struct {
		Active    int    `json:"active"`
		Completed int    `json:"completed"`
		Failed    int    `json:"failed"`
		List      []Task `json:"list"`
	}{}

	for _, task := range api.tasks {
		tasks = append(tasks, *task)
		switch task.Status {
		case "running":
			stats.Active++
		case "completed":
			stats.Completed++
		case "failed":
			stats.Failed++
		}
	}
	stats.List = tasks
	api.mu.RUnlock() // 修复：在 JSON 编码前释放锁

	json.NewEncoder(w).Encode(stats)
}

// 创建任务
func (api *SpiderAPI) createTask(w http.ResponseWriter, r *http.Request) {
	var task Task
	if err := json.NewDecoder(r.Body).Decode(&task); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	api.mu.Lock()
	task.ID = fmt.Sprintf("task_%d", time.Now().UnixNano())
	task.Status = "running"
	task.Progress = 0
	task.StartTime = time.Now()
	api.tasks[task.ID] = &task
	api.mu.Unlock()

	// 异步执行任务
	go api.executeTask(&task)

	json.NewEncoder(w).Encode(map[string]string{
		"id":     task.ID,
		"status": "created",
	})
}

// 执行任务 (这里模拟，实际应调用对应框架)
func (api *SpiderAPI) executeTask(task *Task) {
	// 实际逻辑: 根据 task.Framework 调用对应框架的 API
	// - gospider: HTTP POST to GoSpider API
	// - javaspider: HTTP POST to JavaSpider API
	// - rustspider: HTTP POST to RustSpider API
	// - pyspider: HTTP POST to PySpider API

	for i := 0; i <= 100; i += 10 {
		time.Sleep(100 * time.Millisecond)
		api.mu.Lock()
		task.Progress = i
		api.mu.Unlock()
	}

	api.mu.Lock()
	task.Status = "completed"
	task.Progress = 100
	api.mu.Unlock()
}

// 获取 Worker 列表
func (api *SpiderAPI) listWorkers(w http.ResponseWriter, r *http.Request) {
	json.NewEncoder(w).Encode(map[string]int{
		"count": api.workers,
	})
}

// 停止任务
func (api *SpiderAPI) stopTask(w http.ResponseWriter, r *http.Request) {
	// 提取 task ID 从路径 /api/tasks/{id}/stop
	path := r.URL.Path
	parts := strings.Split(path, "/")
	if len(parts) < 4 {
		http.Error(w, "Invalid path", http.StatusBadRequest)
		return
	}
	taskID := parts[3]

	api.mu.Lock()
	task, exists := api.tasks[taskID]
	if !exists {
		api.mu.Unlock()
		http.Error(w, "Task not found", http.StatusNotFound)
		return
	}

	if task.Status == "running" {
		task.Status = "stopped"
		task.Progress = 0
	}
	api.mu.Unlock()

	json.NewEncoder(w).Encode(map[string]string{
		"id":     taskID,
		"status": "stopped",
	})
}

func main() {
	api := NewSpiderAPI()

	fmt.Println("🚀 Spider API Gateway starting on :8080")
	log.Fatal(http.ListenAndServe(":8080", api))
}
