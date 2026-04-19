package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"

	"gospider/core"
	"gospider/distributed"
	"gospider/events"
	"gospider/graph"
	"gospider/monitor"
	"gospider/research"
)

// Server API 服务器
type Server struct {
	router      *chi.Mux
	redis       *distributed.RedisClient
	monitor     *monitor.Monitor
	jobService  *core.JobService
	addr        string
	authToken   string
	authEnabled bool
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
		router:      r,
		redis:       redisClient,
		monitor:     mon,
		jobService:  nil,
		addr:        fmt.Sprintf("%s:%d", config.Host, config.Port),
		authToken:   strings.TrimSpace(config.AuthToken),
		authEnabled: config.EnableAuth && strings.TrimSpace(config.AuthToken) != "",
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
		router:      r,
		jobService:  jobService,
		addr:        fmt.Sprintf("%s:%d", config.Host, config.Port),
		authToken:   strings.TrimSpace(config.AuthToken),
		authEnabled: config.EnableAuth && strings.TrimSpace(config.AuthToken) != "",
	}
	s.setupRoutes()
	return s
}

// setupRoutes 设置路由
func (s *Server) setupRoutes() {
	r := s.router

	r.Group(func(r chi.Router) {
		if s.authEnabled {
			r.Use(s.authMiddleware)
		}
		r.Post("/api/graph/extract", s.extractGraph)
	})

	// API v1
	r.Route("/api/v1", func(r chi.Router) {
		// 健康检查
		r.Get("/health", s.healthCheck)
		r.Group(func(r chi.Router) {
			if s.authEnabled {
				r.Use(s.authMiddleware)
			}

			r.Get("/stats", s.getStats)
			r.Get("/events", s.listEvents)
			r.Post("/graph/extract", s.extractGraph)
			r.Post("/research/run", s.runResearch)
			r.Post("/research/async", s.runResearchAsync)
			r.Post("/research/soak", s.runResearchSoak)

			// 任务管理
			r.Route("/tasks", func(r chi.Router) {
				r.Post("/", s.createTask)
				r.Get("/", s.listTasks)
				r.Get("/{taskID}", s.getTask)
				r.Get("/{taskID}/result", s.getTaskResult)
				r.Get("/{taskID}/artifacts", s.getTaskArtifacts)
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
	})

	// 静态文件（可选的 Web UI）
	r.Handle("/ui/*", http.StripPrefix("/ui/", http.FileServer(http.Dir("./ui"))))
}

func (s *Server) authMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !s.isAuthorized(r) {
			s.errorResponse(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func (s *Server) isAuthorized(r *http.Request) bool {
	if !s.authEnabled {
		return true
	}
	token := strings.TrimSpace(r.Header.Get("Authorization"))
	if strings.HasPrefix(strings.ToLower(token), "bearer ") {
		token = strings.TrimSpace(token[7:])
	}
	if token == "" {
		token = strings.TrimSpace(r.Header.Get("X-API-Token"))
	}
	return token != "" && token == s.authToken
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
	if s.monitor == nil {
		s.jsonResponse(w, map[string]interface{}{
			"status": "healthy",
			"mode":   "memory",
		})
		return
	}

	health := s.monitor.GetHealthStatus()
	s.jsonResponse(w, health)
}

// getStats 获取统计信息
func (s *Server) getStats(w http.ResponseWriter, r *http.Request) {
	if s.monitor == nil && s.jobService != nil {
		s.jsonResponse(w, map[string]interface{}{
			"mode": "memory",
			"jobs": s.jobService.Stats(),
		})
		return
	}

	stats := s.monitor.GetStats()
	s.jsonResponse(w, stats)
}

// listEvents 获取事件流历史
func (s *Server) listEvents(w http.ResponseWriter, r *http.Request) {
	topic := strings.TrimSpace(r.URL.Query().Get("topic"))
	limit := parseLimit(r.URL.Query().Get("limit"))

	if s.jobService != nil {
		s.jsonResponse(w, s.jobService.ListEvents(limit, topic))
		return
	}
	if s.redis == nil {
		s.jsonResponse(w, []events.Event{})
		return
	}

	result, err := s.redis.ListEvents(limit, topic)
	if err != nil {
		s.errorResponse(w, err.Error(), http.StatusInternalServerError)
		return
	}
	s.jsonResponse(w, result)
}

// createTask 创建任务
func (s *Server) createTask(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		s.errorResponse(w, "无法读取请求体", http.StatusBadRequest)
		return
	}

	if s.jobService != nil {
		job, err := decodeJobSpecPayload(body)
		if err != nil {
			s.errorResponse(w, "无效的请求体", http.StatusBadRequest)
			return
		}

		summary, err := s.jobService.Submit(job)
		if err != nil {
			s.errorResponse(w, err.Error(), http.StatusBadRequest)
			return
		}

		s.jsonResponse(w, map[string]interface{}{
			"task_id": summary.Name,
			"name":    summary.Name,
			"runtime": summary.Runtime,
			"status":  string(summary.State),
		})
		return
	}

	task, err := decodeDistributedTaskPayload(body)
	if err != nil {
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
	_ = s.redis.PublishEvent(events.TopicTaskCreated, events.New(events.TopicTaskCreated, events.TaskLifecyclePayload{
		TaskID:    task.ID,
		State:     string(task.CoreState()),
		Runtime:   string(inferTaskRuntime(task)),
		URL:       task.URL,
		WorkerID:  task.WorkerID,
		UpdatedAt: task.UpdatedAt,
		HasResult: task.Result != nil,
	}))

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

	opts := distributed.TaskListOptions{
		Statuses: parseTaskStateFilters(r.URL.Query().Get("status")),
		Runtime:  core.Runtime(strings.TrimSpace(r.URL.Query().Get("runtime"))),
		WorkerID: strings.TrimSpace(r.URL.Query().Get("worker_id")),
		Limit:    parseLimit(r.URL.Query().Get("limit")),
	}

	tasks, err := s.redis.ListTasks(opts)
	if err != nil {
		s.errorResponse(w, err.Error(), http.StatusInternalServerError)
		return
	}
	s.jsonResponse(w, tasks)
}

// getTask 获取任务详情
func (s *Server) getTask(w http.ResponseWriter, r *http.Request) {
	taskID := chi.URLParam(r, "taskID")

	if s.jobService != nil {
		record, ok := s.jobService.Get(taskID)
		if !ok {
			s.errorResponse(w, "任务不存在", http.StatusNotFound)
			return
		}
		s.jsonResponse(w, record)
		return
	}

	task, err := s.redis.GetTask(taskID)
	if err != nil {
		s.errorResponse(w, "任务不存在", http.StatusNotFound)
		return
	}

	s.jsonResponse(w, task)
}

// getTaskResult 获取任务执行结果
func (s *Server) getTaskResult(w http.ResponseWriter, r *http.Request) {
	taskID := chi.URLParam(r, "taskID")

	if s.jobService != nil {
		record, ok := s.jobService.Get(taskID)
		if !ok {
			s.errorResponse(w, "任务不存在", http.StatusNotFound)
			return
		}
		if record.Result == nil {
			s.errorResponse(w, "任务结果不存在", http.StatusNotFound)
			return
		}
		s.jsonResponse(w, record.Result)
		return
	}

	task, err := s.redis.GetTask(taskID)
	if err != nil {
		s.errorResponse(w, "任务不存在", http.StatusNotFound)
		return
	}
	if task.Result == nil {
		s.errorResponse(w, "任务结果不存在", http.StatusNotFound)
		return
	}
	s.jsonResponse(w, task.Result)
}

// getTaskArtifacts 获取任务工件清单
func (s *Server) getTaskArtifacts(w http.ResponseWriter, r *http.Request) {
	taskID := chi.URLParam(r, "taskID")

	if s.jobService != nil {
		record, ok := s.jobService.Get(taskID)
		if !ok {
			s.errorResponse(w, "任务不存在", http.StatusNotFound)
			return
		}
		if record.Result == nil {
			s.errorResponse(w, "任务结果不存在", http.StatusNotFound)
			return
		}
		s.jsonResponse(w, artifactPayload(record.Result))
		return
	}

	task, err := s.redis.GetTask(taskID)
	if err != nil {
		s.errorResponse(w, "任务不存在", http.StatusNotFound)
		return
	}
	if task.Result == nil {
		s.errorResponse(w, "任务结果不存在", http.StatusNotFound)
		return
	}
	s.jsonResponse(w, artifactPayload(task.Result))
}

// deleteTask 删除任务
func (s *Server) deleteTask(w http.ResponseWriter, r *http.Request) {
	taskID := chi.URLParam(r, "taskID")

	if s.jobService != nil {
		if !s.jobService.Delete(taskID) {
			s.errorResponse(w, "任务不存在", http.StatusNotFound)
			return
		}
		s.jsonResponse(w, map[string]string{
			"status": "deleted",
		})
		return
	}

	// 删除任务
	if err := s.redis.DeleteTask(taskID); err != nil {
		s.errorResponse(w, err.Error(), http.StatusInternalServerError)
		return
	}

	s.jsonResponse(w, map[string]string{
		"status": "deleted",
	})
}

// cancelTask 取消任务
func (s *Server) cancelTask(w http.ResponseWriter, r *http.Request) {
	taskID := chi.URLParam(r, "taskID")

	if s.jobService != nil {
		summary, err := s.jobService.Cancel(taskID)
		if err != nil {
			if _, ok := s.jobService.Get(taskID); !ok {
				s.errorResponse(w, "任务不存在", http.StatusNotFound)
				return
			}
			s.errorResponse(w, err.Error(), http.StatusConflict)
			return
		}
		s.jsonResponse(w, summary)
		return
	}

	task, err := s.redis.CancelTask(taskID)
	if err != nil {
		s.errorResponse(w, "任务不存在", http.StatusNotFound)
		return
	}
	s.jsonResponse(w, task)
}

// getQueueStats 获取队列统计
func (s *Server) getQueueStats(w http.ResponseWriter, r *http.Request) {
	if s.redis == nil && s.jobService != nil {
		s.jsonResponse(w, s.jobService.Stats())
		return
	}
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
	if s.redis == nil {
		s.jsonResponse(w, []string{})
		return
	}

	opts := distributed.TaskListOptions{
		Statuses: []core.TaskState{queueTypeToState(queueType)},
		Runtime:  core.Runtime(strings.TrimSpace(r.URL.Query().Get("runtime"))),
		WorkerID: strings.TrimSpace(r.URL.Query().Get("worker_id")),
		Limit:    parseLimit(r.URL.Query().Get("limit")),
	}
	tasks, err := s.redis.ListTasks(opts)
	if err != nil {
		s.errorResponse(w, err.Error(), http.StatusInternalServerError)
		return
	}
	s.jsonResponse(w, tasks)
}

// listWorkers 列出工作节点
func (s *Server) listWorkers(w http.ResponseWriter, r *http.Request) {
	if s.monitor == nil {
		s.jsonResponse(w, []string{})
		return
	}

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

func (s *Server) extractGraph(w http.ResponseWriter, r *http.Request) {
	var req struct {
		HTML string `json:"html"`
		URL  string `json:"url"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		s.graphError(w, "无效的请求体", http.StatusBadRequest)
		return
	}

	html, err := resolveGraphHTML(strings.TrimSpace(req.HTML), strings.TrimSpace(req.URL))
	if err != nil {
		s.graphError(w, err.Error(), http.StatusBadRequest)
		return
	}

	builder := graph.NewBuilder()
	if err := builder.BuildFromHTML(html); err != nil {
		s.graphError(w, err.Error(), http.StatusBadRequest)
		return
	}

	s.jsonResponse(w, map[string]interface{}{
		"success": true,
		"data": map[string]interface{}{
			"root_id": builder.RootID,
			"nodes":   builder.Nodes,
			"edges":   builder.Edges,
			"stats":   builder.Stats(),
		},
	})
}

func (s *Server) runResearch(w http.ResponseWriter, r *http.Request) {
	var req researchRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		s.errorResponse(w, "invalid research request body", http.StatusBadRequest)
		return
	}
	job, err := req.toJob()
	if err != nil {
		s.errorResponse(w, err.Error(), http.StatusBadRequest)
		return
	}
	result, err := research.NewResearchRuntime().Run(job, req.Content)
	if err != nil {
		s.errorResponse(w, err.Error(), http.StatusBadRequest)
		return
	}
	s.jsonResponse(w, map[string]interface{}{
		"command": "research run",
		"runtime": "go",
		"result":  result,
	})
}

func (s *Server) runResearchAsync(w http.ResponseWriter, r *http.Request) {
	var req researchRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		s.errorResponse(w, "invalid research request body", http.StatusBadRequest)
		return
	}
	jobs, contents, err := req.toJobs()
	if err != nil {
		s.errorResponse(w, err.Error(), http.StatusBadRequest)
		return
	}
	runtime := research.NewAsyncResearchRuntime(&research.AsyncResearchConfig{
		MaxConcurrent: maxIntValue(req.Concurrency, 1),
	})
	results := runtime.RunMultiple(jobs, contents)
	s.jsonResponse(w, map[string]interface{}{
		"command": "research async",
		"runtime": "go",
		"results": results,
		"metrics": runtime.SnapshotMetrics(),
	})
}

func (s *Server) runResearchSoak(w http.ResponseWriter, r *http.Request) {
	var req researchRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		s.errorResponse(w, "invalid research request body", http.StatusBadRequest)
		return
	}
	jobs, contents, err := req.toJobs()
	if err != nil {
		s.errorResponse(w, err.Error(), http.StatusBadRequest)
		return
	}
	runtime := research.NewAsyncResearchRuntime(&research.AsyncResearchConfig{
		MaxConcurrent: maxIntValue(req.Concurrency, 1),
	})
	report := runtime.RunSoak(jobs, contents, maxIntValue(req.Rounds, 1))
	s.jsonResponse(w, map[string]interface{}{
		"command": "research soak",
		"runtime": "go",
		"report":  report,
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
		"error":  message,
		"status": status,
	})
}

// generateTaskID 生成任务 ID
func generateTaskID() string {
	return fmt.Sprintf("task_%d", time.Now().UnixNano())
}

func resolveGraphHTML(htmlBody, targetURL string) (string, error) {
	if htmlBody != "" {
		return htmlBody, nil
	}
	if targetURL == "" {
		return "", fmt.Errorf("html or url is required")
	}
	resp, err := http.Get(targetURL)
	if err != nil {
		return "", fmt.Errorf("failed to fetch url: %w", err)
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read url body: %w", err)
	}
	return string(body), nil
}

func (s *Server) graphError(w http.ResponseWriter, message string, status int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"success": false,
		"error":   message,
		"status":  status,
	})
}

type createTaskRequest struct {
	Name      string                 `json:"name"`
	Runtime   core.Runtime           `json:"runtime"`
	Priority  int                    `json:"priority"`
	URL       string                 `json:"url"`
	Target    *createTaskTarget      `json:"target"`
	Browser   *createTaskBrowser     `json:"browser"`
	Actions   []createTaskAction     `json:"actions"`
	Extract   []core.ExtractSpec     `json:"extract"`
	Output    *core.OutputSpec       `json:"output"`
	Resources *createTaskResources   `json:"resources"`
	Media     *core.MediaSpec        `json:"media"`
	AntiBot   *core.AntiBotSpec      `json:"anti_bot"`
	Policy    *core.PolicySpec       `json:"policy"`
	Schedule  *core.ScheduleSpec     `json:"schedule"`
	Metadata  map[string]interface{} `json:"metadata"`
}

type researchRequest struct {
	URL        string                   `json:"url"`
	URLs       []string                 `json:"urls"`
	Content    string                   `json:"content"`
	Contents   []string                 `json:"contents"`
	Schema     map[string]interface{}   `json:"schema"`
	SchemaJSON string                   `json:"schema_json"`
	Output     map[string]interface{}   `json:"output"`
	Rounds     int                      `json:"rounds"`
	Concurrency int                     `json:"concurrency"`
	Policy     map[string]interface{}   `json:"policy"`
}

func (r researchRequest) toJob() (research.ResearchJob, error) {
	urls := r.URLs
	if len(urls) == 0 && strings.TrimSpace(r.URL) != "" {
		urls = []string{r.URL}
	}
	if len(urls) == 0 {
		return research.ResearchJob{}, fmt.Errorf("research request requires url or urls")
	}
	schema, err := r.schemaMap()
	if err != nil {
		return research.ResearchJob{}, err
	}
	return research.ResearchJob{
		SeedURLs:      urls,
		ExtractSchema: schema,
		Policy:        cloneAnyMap(r.Policy),
		Output:        cloneAnyMap(r.Output),
	}, nil
}

func (r researchRequest) toJobs() ([]research.ResearchJob, []string, error) {
	urls := r.URLs
	if len(urls) == 0 && strings.TrimSpace(r.URL) != "" {
		urls = []string{r.URL}
	}
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
			ExtractSchema: cloneAnyMap(schema),
			Policy:        cloneAnyMap(r.Policy),
			Output:        cloneAnyMap(r.Output),
		})
		if len(r.Contents) > index && strings.TrimSpace(r.Contents[index]) != "" {
			contents = append(contents, r.Contents[index])
		} else {
			contents = append(contents, r.Content)
		}
	}
	return jobs, contents, nil
}

func (r researchRequest) schemaMap() (map[string]interface{}, error) {
	if len(r.Schema) > 0 {
		return cloneAnyMap(r.Schema), nil
	}
	if strings.TrimSpace(r.SchemaJSON) == "" {
		return map[string]interface{}{}, nil
	}
	var schema map[string]interface{}
	if err := json.Unmarshal([]byte(r.SchemaJSON), &schema); err != nil {
		return nil, fmt.Errorf("invalid schema_json: %w", err)
	}
	return schema, nil
}

func cloneAnyMap(source map[string]interface{}) map[string]interface{} {
	if source == nil {
		return map[string]interface{}{}
	}
	clone := make(map[string]interface{}, len(source))
	for key, value := range source {
		clone[key] = value
	}
	return clone
}

func maxIntValue(value int, minimum int) int {
	if value < minimum {
		return minimum
	}
	return value
}

type createTaskTarget struct {
	URL            string            `json:"url"`
	Method         string            `json:"method"`
	Headers        map[string]string `json:"headers"`
	Cookies        map[string]string `json:"cookies"`
	Body           string            `json:"body"`
	TimeoutMS      int64             `json:"timeout_ms"`
	Retries        int               `json:"retries"`
	Proxy          string            `json:"proxy"`
	AllowedDomains []string          `json:"allowed_domains"`
}

type createTaskBrowser struct {
	Headless    bool               `json:"headless"`
	Viewport    core.ViewportSpec  `json:"viewport"`
	UserAgent   string             `json:"user_agent"`
	WaitLoad    bool               `json:"wait_load"`
	BlockImages bool               `json:"block_images"`
	Cookies     []core.CookieSpec  `json:"cookies"`
	Profile     string             `json:"profile"`
	Actions     []createTaskAction `json:"actions"`
	Capture     []string           `json:"capture"`
}

type createTaskAction struct {
	Type      string                 `json:"type"`
	Selector  string                 `json:"selector"`
	Value     string                 `json:"value"`
	URL       string                 `json:"url"`
	TimeoutMS int64                  `json:"timeout_ms"`
	Optional  bool                   `json:"optional"`
	SaveAs    string                 `json:"save_as"`
	Mode      string                 `json:"mode"`
	MaxScroll int                    `json:"max_scrolls"`
	Extra     map[string]interface{} `json:"extra"`
}

type createTaskResources struct {
	Concurrency     int                       `json:"concurrency"`
	TimeoutMS       int64                     `json:"timeout_ms"`
	Retries         int                       `json:"retries"`
	DownloadDir     string                    `json:"download_dir"`
	TempDir         string                    `json:"temp_dir"`
	Browser         *core.BrowserResourceSpec `json:"browser"`
	RateLimit       *core.RateLimitSpec       `json:"rate_limit"`
	RateLimitPerSec float64                   `json:"rate_limit_per_sec"`
}

func decodeJobSpecRequest(r *http.Request) (core.JobSpec, error) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		return core.JobSpec{}, err
	}
	return decodeJobSpecPayload(body)
}

func decodeJobSpecPayload(body []byte) (core.JobSpec, error) {
	var req createTaskRequest
	if err := json.NewDecoder(bytes.NewReader(body)).Decode(&req); err != nil {
		return core.JobSpec{}, err
	}

	job := core.JobSpec{
		Name:     req.Name,
		Runtime:  req.Runtime,
		Priority: req.Priority,
		Extract:  req.Extract,
		Metadata: req.Metadata,
	}

	if req.Target != nil {
		job.Target = core.TargetSpec{
			URL:            req.Target.URL,
			Method:         req.Target.Method,
			Headers:        req.Target.Headers,
			Cookies:        req.Target.Cookies,
			Body:           req.Target.Body,
			Timeout:        time.Duration(req.Target.TimeoutMS) * time.Millisecond,
			Retries:        req.Target.Retries,
			Proxy:          req.Target.Proxy,
			AllowedDomains: req.Target.AllowedDomains,
		}
	} else if req.URL != "" {
		job.Target = core.TargetSpec{
			URL:    req.URL,
			Method: http.MethodGet,
		}
	}

	if req.Output != nil {
		job.Output = *req.Output
	}
	if req.Resources != nil {
		job.Resources = core.ResourceSpec{
			Concurrency:     req.Resources.Concurrency,
			Timeout:         time.Duration(req.Resources.TimeoutMS) * time.Millisecond,
			Retries:         req.Resources.Retries,
			DownloadDir:     req.Resources.DownloadDir,
			TempDir:         req.Resources.TempDir,
			RateLimitPerSec: req.Resources.RateLimitPerSec,
		}
		if req.Resources.Browser != nil {
			job.Resources.Browser = *req.Resources.Browser
		}
		if req.Resources.RateLimit != nil {
			job.Resources.RateLimit = *req.Resources.RateLimit
		}
	}
	if req.Media != nil {
		job.Media = *req.Media
	}
	if req.AntiBot != nil {
		job.AntiBot = *req.AntiBot
	}
	if req.Policy != nil {
		job.Policy = *req.Policy
	}
	if req.Schedule != nil {
		job.Schedule = *req.Schedule
	}
	if req.Browser != nil {
		job.Browser = core.BrowserSpec{
			BrowserResourceSpec: core.BrowserResourceSpec{
				Headless:    req.Browser.Headless,
				Viewport:    req.Browser.Viewport,
				UserAgent:   req.Browser.UserAgent,
				WaitLoad:    req.Browser.WaitLoad,
				BlockImages: req.Browser.BlockImages,
				Cookies:     req.Browser.Cookies,
			},
			Profile: req.Browser.Profile,
			Capture: append([]string(nil), req.Browser.Capture...),
		}
		for _, action := range req.Browser.Actions {
			job.Browser.Actions = append(job.Browser.Actions, toCoreAction(action))
		}
	}
	for _, action := range req.Actions {
		job.Actions = append(job.Actions, toCoreAction(action))
	}

	if job.Runtime == "" {
		job.Runtime = core.RuntimeHTTP
	}
	if job.Target.Method == "" && job.Target.URL != "" {
		job.Target.Method = http.MethodGet
	}
	if err := job.Validate(); err != nil {
		return core.JobSpec{}, err
	}
	return job, nil
}

func decodeDistributedTaskPayload(body []byte) (distributed.CrawlTask, error) {
	var task distributed.CrawlTask
	if err := json.NewDecoder(bytes.NewReader(body)).Decode(&task); err != nil {
		return distributed.CrawlTask{}, err
	}

	if task.URL != "" || task.Job != nil {
		if task.Data == nil {
			task.Data = make(map[string]interface{})
		}
		return task, nil
	}

	job, err := decodeJobSpecPayload(body)
	if err != nil {
		return distributed.CrawlTask{}, err
	}

	task = distributed.CrawlTask{
		URL:      job.Target.URL,
		Type:     inferDistributedTaskType(job),
		Priority: job.Priority,
		Job:      &job,
		Data: map[string]interface{}{
			"submitted_via": "job_spec",
		},
	}
	return task, nil
}

func inferDistributedTaskType(job core.JobSpec) string {
	switch job.Runtime {
	case core.RuntimeMedia:
		if len(job.Media.Types) > 0 && job.Media.Types[0] != "" {
			return job.Media.Types[0]
		}
		return "video"
	case core.RuntimeBrowser:
		return "browser"
	case core.RuntimeAI:
		return "ai"
	default:
		return "page"
	}
}

func parseTaskStateFilters(raw string) []core.TaskState {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil
	}
	parts := strings.Split(raw, ",")
	states := make([]core.TaskState, 0, len(parts))
	seen := make(map[core.TaskState]struct{})
	for _, part := range parts {
		state := queueTypeToState(strings.TrimSpace(part))
		if state == "" {
			continue
		}
		if _, ok := seen[state]; ok {
			continue
		}
		seen[state] = struct{}{}
		states = append(states, state)
	}
	return states
}

func queueTypeToState(queueType string) core.TaskState {
	switch strings.ToLower(strings.TrimSpace(queueType)) {
	case "pending", "queued":
		return core.StateQueued
	case "running":
		return core.StateRunning
	case "completed", "succeeded", "success":
		return core.StateSucceeded
	case "failed":
		return core.StateFailed
	case "cancelled", "canceled":
		return core.StateCancelled
	default:
		return core.TaskState(strings.ToLower(strings.TrimSpace(queueType)))
	}
}

func parseLimit(raw string) int {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return 0
	}
	limit, err := strconv.Atoi(raw)
	if err != nil || limit < 0 {
		return 0
	}
	return limit
}

func artifactPayload(result *core.JobResult) map[string]interface{} {
	if result == nil {
		return map[string]interface{}{
			"artifacts":     []string{},
			"artifact_refs": map[string]core.ArtifactRef{},
		}
	}
	return map[string]interface{}{
		"artifacts":     result.Artifacts,
		"artifact_refs": result.ArtifactRefs,
		"media":         result.MediaRecord,
	}
}

func inferTaskRuntime(task distributed.CrawlTask) core.Runtime {
	if task.Job != nil {
		return task.Job.Runtime
	}
	switch strings.ToLower(task.Type) {
	case "video", "image", "audio", "hls", "dash":
		return core.RuntimeMedia
	case "browser", "monitor":
		return core.RuntimeBrowser
	case "ai":
		return core.RuntimeAI
	default:
		return core.RuntimeHTTP
	}
}

func toCoreAction(action createTaskAction) core.ActionSpec {
	return core.ActionSpec{
		Type:      action.Type,
		Selector:  action.Selector,
		Value:     action.Value,
		URL:       action.URL,
		Timeout:   time.Duration(action.TimeoutMS) * time.Millisecond,
		Optional:  action.Optional,
		SaveAs:    action.SaveAs,
		Mode:      action.Mode,
		MaxScroll: action.MaxScroll,
		Extra:     action.Extra,
	}
}
