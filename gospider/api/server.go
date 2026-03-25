package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"

	"gospider/core"
	"gospider/distributed"
	"gospider/monitor"
)

// Server API 服务器
type Server struct {
	router  *chi.Mux
	redis   *distributed.RedisClient
	monitor *monitor.Monitor
	jobService *core.JobService
	addr    string
}

// Config API 配置
type Config struct {
	Host          string
	Port          int
	RedisAddr     string
	RedisPassword string
	RedisDB       int
	EnableCORS    bool
	EnableAuth    bool
	AuthToken     string
}

// NewServer 创建 API 服务器
func NewServer(config *Config, redisClient *distributed.RedisClient, mon *monitor.Monitor) *Server {
	r := chi.NewRouter()

	// 中间件
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.RealIP)
	r.Use(middleware.RequestID)

	// CORS
	if config.EnableCORS {
		r.Use(cors.Handler(cors.Options{
			AllowedOrigins:   []string{"https://*", "http://*"},
			AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
			AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-CSRF-Token"},
			ExposedHeaders:   []string{"Link"},
			AllowCredentials: true,
			MaxAge:           300,
		}))
	}

	s := &Server{
		router:  r,
		redis:   redisClient,
		monitor: mon,
		jobService: nil,
		addr:    fmt.Sprintf("%s:%d", config.Host, config.Port),
	}

	// 设置路由
	s.setupRoutes()

	return s
}

// NewServerWithJobService creates an API server backed by the shared in-memory job service.
func NewServerWithJobService(config *Config, jobService *core.JobService) *Server {
	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.RealIP)
	r.Use(middleware.RequestID)

	s := &Server{
		router:     r,
		jobService: jobService,
		addr:       fmt.Sprintf("%s:%d", config.Host, config.Port),
	}
	s.setupRoutes()
	return s
}

// setupRoutes 设置路由
func (s *Server) setupRoutes() {
	r := s.router

	// API v1
	r.Route("/api/v1", func(r chi.Router) {
		// 健康检查
		r.Get("/health", s.healthCheck)
		r.Get("/stats", s.getStats)

		// 任务管理
		r.Route("/tasks", func(r chi.Router) {
			r.Post("/", s.createTask)
			r.Get("/", s.listTasks)
			r.Get("/{taskID}", s.getTask)
			r.Delete("/{taskID}", s.deleteTask)
			r.Post("/{taskID}/cancel", s.cancelTask)
		})

		// 队列管理
		r.Route("/queue", func(r chi.Router) {
			r.Get("/stats", s.getQueueStats)
			r.Get("/pending", s.getPendingTasks)
			r.Get("/running", s.getRunningTasks)
			r.Get("/completed", s.getCompletedTasks)
			r.Get("/failed", s.getFailedTasks)
		})

		// 工作节点
		r.Route("/workers", func(r chi.Router) {
			r.Get("/", s.listWorkers)
			r.Get("/{workerID}", s.getWorker)
			r.Delete("/{workerID}", s.removeWorker)
		})

		// 下载任务
		r.Route("/download", func(r chi.Router) {
			r.Post("/video", s.downloadVideo)
			r.Post("/hls", s.downloadHLS)
		})
	})

	// 静态文件（可选的 Web UI）
	r.Handle("/ui/*", http.StripPrefix("/ui/", http.FileServer(http.Dir("./ui"))))
}

// Start 启动服务器
func (s *Server) Start() error {
	fmt.Printf("🚀 API 服务器启动在：%s\n", s.addr)
	fmt.Printf("📊 监控面板：http://%s/ui/\n", s.addr)
	fmt.Printf("📡 API 文档：http://%s/api/v1/health\n", s.addr)
	return http.ListenAndServe(s.addr, s.router)
}

// ===== 处理器函数 =====

// healthCheck 健康检查
func (s *Server) healthCheck(w http.ResponseWriter, r *http.Request) {
	health := s.monitor.GetHealthStatus()
	s.jsonResponse(w, health)
}

// getStats 获取统计信息
func (s *Server) getStats(w http.ResponseWriter, r *http.Request) {
	stats := s.monitor.GetStats()
	s.jsonResponse(w, stats)
}

// createTask 创建任务
func (s *Server) createTask(w http.ResponseWriter, r *http.Request) {
	if s.jobService != nil {
		var req struct {
			URL      string `json:"url"`
			Runtime  string `json:"runtime"`
			Priority int    `json:"priority"`
			Name     string `json:"name"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			s.errorResponse(w, "无效的请求体", http.StatusBadRequest)
			return
		}

		runtime := core.RuntimeHTTP
		if req.Runtime == string(core.RuntimeBrowser) {
			runtime = core.RuntimeBrowser
		}
		name := req.Name
		if name == "" {
			name = req.URL
		}

		summary, err := s.jobService.Submit(core.JobSpec{
			Name:     name,
			Runtime:  runtime,
			Target:   core.TargetSpec{URL: req.URL, Method: http.MethodGet},
			Priority: req.Priority,
		})
		if err != nil {
			s.errorResponse(w, err.Error(), http.StatusBadRequest)
			return
		}

		s.jsonResponse(w, map[string]interface{}{
			"task_id": summary.Name,
			"status":  string(summary.State),
		})
		return
	}

	var task distributed.CrawlTask
	if err := json.NewDecoder(r.Body).Decode(&task); err != nil {
		s.errorResponse(w, "无效的请求体", http.StatusBadRequest)
		return
	}

	// 生成任务 ID（如果未提供）
	if task.ID == "" {
		task.ID = generateTaskID()
	}

	// 设置默认优先级
	if task.Priority == 0 {
		task.Priority = 5
	}

	// 推送到队列
	if err := s.redis.PushTask(&task); err != nil {
		s.errorResponse(w, fmt.Sprintf("创建任务失败：%v", err), http.StatusInternalServerError)
		return
	}

	// 发布事件
	s.redis.PublishEvent("task:created", map[string]string{
		"task_id": task.ID,
		"type":    task.Type,
		"url":     task.URL,
	})

	s.jsonResponse(w, map[string]interface{}{
		"task_id": task.ID,
		"status":  "created",
	})
}

// listTasks 列出任务
func (s *Server) listTasks(w http.ResponseWriter, r *http.Request) {
	if s.jobService != nil {
		s.jsonResponse(w, s.jobService.List())
		return
	}

	// 这里简化实现，实际应该从 Redis 获取
	tasks := make([]distributed.CrawlTask, 0)
	s.jsonResponse(w, tasks)
}

// getTask 获取任务详情
func (s *Server) getTask(w http.ResponseWriter, r *http.Request) {
	taskID := chi.URLParam(r, "taskID")

	task, err := s.redis.GetTask(taskID)
	if err != nil {
		s.errorResponse(w, "任务不存在", http.StatusNotFound)
		return
	}

	s.jsonResponse(w, task)
}

// deleteTask 删除任务
func (s *Server) deleteTask(w http.ResponseWriter, r *http.Request) {
	taskID := chi.URLParam(r, "taskID")

	// 删除任务
	key := "gospider:task:" + taskID
	s.redis.DeleteKey(r.Context(), key)

	s.jsonResponse(w, map[string]string{
		"status": "deleted",
	})
}

// cancelTask 取消任务
func (s *Server) cancelTask(w http.ResponseWriter, r *http.Request) {
	taskID := chi.URLParam(r, "taskID")

	// 从待处理队列移除
	queueKey := "gospider:queue:pending"
	s.redis.ZRemKey(r.Context(), queueKey, taskID)

	s.jsonResponse(w, map[string]string{
		"status": "cancelled",
	})
}

// getQueueStats 获取队列统计
func (s *Server) getQueueStats(w http.ResponseWriter, r *http.Request) {
	stats, _ := s.redis.GetQueueStats()
	s.jsonResponse(w, stats)
}

// getPendingTasks 获取待处理任务
func (s *Server) getPendingTasks(w http.ResponseWriter, r *http.Request) {
	s.getQueueTasks(w, r, "pending")
}

// getRunningTasks 获取运行中任务
func (s *Server) getRunningTasks(w http.ResponseWriter, r *http.Request) {
	s.getQueueTasks(w, r, "running")
}

// getCompletedTasks 获取已完成任务
func (s *Server) getCompletedTasks(w http.ResponseWriter, r *http.Request) {
	s.getQueueTasks(w, r, "completed")
}

// getFailedTasks 获取失败任务
func (s *Server) getFailedTasks(w http.ResponseWriter, r *http.Request) {
	s.getQueueTasks(w, r, "failed")
}

// getQueueTasks 获取队列任务
func (s *Server) getQueueTasks(w http.ResponseWriter, r *http.Request, queueType string) {
	// 简化实现
	s.jsonResponse(w, []string{})
}

// listWorkers 列出工作节点
func (s *Server) listWorkers(w http.ResponseWriter, r *http.Request) {
	// 从监控器获取工作节点统计
	stats := s.monitor.GetStats()
	s.jsonResponse(w, stats.Workers)
}

// getWorker 获取工作节点详情
func (s *Server) getWorker(w http.ResponseWriter, r *http.Request) {
	workerID := chi.URLParam(r, "workerID")

	worker, err := s.redis.GetWorker(workerID)
	if err != nil {
		s.errorResponse(w, "工作节点不存在", http.StatusNotFound)
		return
	}

	s.jsonResponse(w, worker)
}

// removeWorker 移除工作节点
func (s *Server) removeWorker(w http.ResponseWriter, r *http.Request) {
	workerID := chi.URLParam(r, "workerID")

	if err := s.redis.RemoveWorker(workerID); err != nil {
		s.errorResponse(w, err.Error(), http.StatusInternalServerError)
		return
	}

	s.jsonResponse(w, map[string]string{
		"status": "removed",
	})
}

// downloadVideo 下载视频
func (s *Server) downloadVideo(w http.ResponseWriter, r *http.Request) {
	var req struct {
		URL     string `json:"url"`
		Quality string `json:"quality"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		s.errorResponse(w, "无效的请求体", http.StatusBadRequest)
		return
	}

	if req.URL == "" {
		s.errorResponse(w, "URL 不能为空", http.StatusBadRequest)
		return
	}

	// 创建下载任务
	task := &distributed.CrawlTask{
		ID:       generateTaskID(),
		URL:      req.URL,
		Type:     "video",
		Priority: 10,
		Data: map[string]interface{}{
			"quality": req.Quality,
		},
	}

	if err := s.redis.PushTask(task); err != nil {
		s.errorResponse(w, err.Error(), http.StatusInternalServerError)
		return
	}

	s.jsonResponse(w, map[string]interface{}{
		"task_id": task.ID,
		"status":  "queued",
	})
}

// downloadHLS 下载 HLS 流
func (s *Server) downloadHLS(w http.ResponseWriter, r *http.Request) {
	var req struct {
		M3U8URL string `json:"m3u8_url"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		s.errorResponse(w, "无效的请求体", http.StatusBadRequest)
		return
	}

	if req.M3U8URL == "" {
		s.errorResponse(w, "M3U8 URL 不能为空", http.StatusBadRequest)
		return
	}

	// 创建下载任务
	task := &distributed.CrawlTask{
		ID:       generateTaskID(),
		URL:      req.M3U8URL,
		Type:     "hls",
		Priority: 10,
	}

	if err := s.redis.PushTask(task); err != nil {
		s.errorResponse(w, err.Error(), http.StatusInternalServerError)
		return
	}

	s.jsonResponse(w, map[string]interface{}{
		"task_id": task.ID,
		"status":  "queued",
	})
}

// ===== 辅助函数 =====

// jsonResponse 返回 JSON 响应
func (s *Server) jsonResponse(w http.ResponseWriter, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	json.NewEncoder(w).Encode(data)
}

// errorResponse 返回错误响应
func (s *Server) errorResponse(w http.ResponseWriter, message string, status int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"error":   message,
		"status":  status,
	})
}

// generateTaskID 生成任务 ID
func generateTaskID() string {
	return fmt.Sprintf("task_%d", time.Now().UnixNano())
}
