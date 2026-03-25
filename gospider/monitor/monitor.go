package monitor

import (
	"encoding/json"
	"fmt"
	"net/http"
	"sort"
	"sync"
	"time"

	"gospider/distributed"
)

// Monitor 监控器
type Monitor struct {
	redis      *distributed.RedisClient
	stats      *SystemStats
	mu         sync.RWMutex
	callbacks  []func(*SystemStats)
	interval   time.Duration
	running    bool
	startTime  time.Time
}

// SystemStats 系统统计
type SystemStats struct {
	Timestamp      time.Time              `json:"timestamp"`
	Uptime         string                 `json:"uptime"`
	Queues         map[string]int64       `json:"queues"`
	Workers        []WorkerStats          `json:"workers"`
	WorkersTotal   int                    `json:"workers_total"`
	WorkersActive  int                    `json:"workers_active"`
	TasksTotal     int64                  `json:"tasks_total"`
	TasksCompleted int64                  `json:"tasks_completed"`
	TasksFailed    int64                  `json:"tasks_failed"`
	Throughput     float64                `json:"throughput"` // 任务/秒
	Custom         map[string]interface{} `json:"custom,omitempty"`
}

// WorkerStats 工作节点统计
type WorkerStats struct {
	ID            string    `json:"id"`
	Host          string    `json:"host"`
	Port          int       `json:"port"`
	Status        string    `json:"status"`
	CurrentTask   string    `json:"current_task,omitempty"`
	TasksDone     int       `json:"tasks_done"`
	LastHeartbeat time.Time `json:"last_heartbeat"`
	IsOnline      bool      `json:"is_online"`
}

// TaskMetric 任务指标
type TaskMetric struct {
	Time     time.Time `json:"time"`
	TaskID   string    `json:"task_id"`
	Type     string    `json:"type"`
	Duration float64   `json:"duration"` // 秒
	Success  bool      `json:"success"`
	Error    string    `json:"error,omitempty"`
}

// NewMonitor 创建监控器
func NewMonitor(redisClient *distributed.RedisClient) *Monitor {
	return &Monitor{
		redis:     redisClient,
		interval:  5 * time.Second,
		startTime: time.Now(),
		callbacks: make([]func(*SystemStats), 0),
	}
}

// Start 启动监控
func (m *Monitor) Start() error {
	m.mu.Lock()
	m.running = true
	m.mu.Unlock()

	go m.monitorLoop()

	return nil
}

// Stop 停止监控
func (m *Monitor) Stop() error {
	m.mu.Lock()
	m.running = false
	m.mu.Unlock()

	return nil
}

// monitorLoop 监控循环
func (m *Monitor) monitorLoop() {
	ticker := time.NewTicker(m.interval)
	defer ticker.Stop()

	for range ticker.C {
		if !m.running {
			break
		}

		stats, err := m.CollectStats()
		if err != nil {
			fmt.Printf("收集统计失败：%v\n", err)
			continue
		}

		m.mu.Lock()
		m.stats = stats
		callbacks := make([]func(*SystemStats), len(m.callbacks))
		copy(callbacks, m.callbacks)
		m.mu.Unlock()

		// 触发回调
		for _, cb := range callbacks {
			go cb(stats)
		}
	}
}

// CollectStats 收集统计信息
func (m *Monitor) CollectStats() (*SystemStats, error) {
	stats := &SystemStats{
		Timestamp: time.Now(),
		Uptime:    time.Since(m.startTime).String(),
		Custom:    make(map[string]interface{}),
	}

	// 队列统计
	queueStats, err := m.redis.GetQueueStats()
	if err != nil {
		return nil, err
	}
	stats.Queues = queueStats

	// 计算总任务数
	stats.TasksTotal = queueStats["pending"] + queueStats["running"] + queueStats["completed"] + queueStats["failed"]
	stats.TasksCompleted = queueStats["completed"]
	stats.TasksFailed = queueStats["failed"]

	// 工作节点统计
	workers, err := m.redis.ListWorkers()
	if err != nil {
		return nil, err
	}

	stats.WorkersTotal = len(workers)
	stats.Workers = make([]WorkerStats, 0, len(workers))

	for _, w := range workers {
		// 检查是否在线（15 秒内有心跳）
		isOnline := time.Since(w.LastHeartbeat) < 15*time.Second

		if isOnline {
			stats.WorkersActive++
		}

		stats.Workers = append(stats.Workers, WorkerStats{
			ID:            w.ID,
			Host:          w.Host,
			Port:          w.Port,
			Status:        w.Status,
			CurrentTask:   w.CurrentTask,
			TasksDone:     w.TasksDone,
			LastHeartbeat: w.LastHeartbeat,
			IsOnline:      isOnline,
		})
	}

	// 按任务完成数排序
	sort.Slice(stats.Workers, func(i, j int) bool {
		return stats.Workers[i].TasksDone > stats.Workers[j].TasksDone
	})

	// 计算吞吐量（过去 1 分钟的任务完成数）
	if stats.Uptime != "" {
		uptime := time.Since(m.startTime)
		if uptime > 0 {
			stats.Throughput = float64(stats.TasksCompleted) / uptime.Seconds()
		}
	}

	return stats, nil
}

// GetStats 获取当前统计
func (m *Monitor) GetStats() *SystemStats {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if m.stats == nil {
		return &SystemStats{
			Timestamp: time.Now(),
			Uptime:    time.Since(m.startTime).String(),
			Queues:    make(map[string]int64),
			Workers:   make([]WorkerStats, 0),
			Custom:    make(map[string]interface{}),
		}
	}

	// 返回副本
	stats := *m.stats
	stats.Queues = make(map[string]int64)
	for k, v := range m.stats.Queues {
		stats.Queues[k] = v
	}
	stats.Workers = make([]WorkerStats, len(m.stats.Workers))
	copy(stats.Workers, m.stats.Workers)

	return &stats
}

// GetStatsJSON 获取统计 JSON
func (m *Monitor) GetStatsJSON() ([]byte, error) {
	stats := m.GetStats()
	return json.MarshalIndent(stats, "", "  ")
}

// OnStatsUpdate 注册统计更新回调
func (m *Monitor) OnStatsUpdate(callback func(*SystemStats)) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.callbacks = append(m.callbacks, callback)
}

// SetInterval 设置采集间隔
func (m *Monitor) SetInterval(interval time.Duration) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.interval = interval
}

// GetWorkerStats 获取特定工作节点统计
func (m *Monitor) GetWorkerStats(workerID string) (*WorkerStats, error) {
	stats := m.GetStats()

	for _, w := range stats.Workers {
		if w.ID == workerID {
			return &w, nil
		}
	}

	return nil, fmt.Errorf("未找到工作节点：%s", workerID)
}

// GetQueueStats 获取队列统计
func (m *Monitor) GetQueueStats() map[string]int64 {
	stats := m.GetStats()
	return stats.Queues
}

// GetHealthStatus 获取健康状态
func (m *Monitor) GetHealthStatus() HealthStatus {
	stats := m.GetStats()

	status := HealthStatus{
		Status:    "healthy",
		Timestamp: stats.Timestamp,
		Checks:    make(map[string]bool),
	}

	// 检查 Redis 连接
	status.Checks["redis"] = true // 如果能获取到统计，说明 Redis 正常

	// 检查是否有活跃工作节点
	status.Checks["workers"] = stats.WorkersActive > 0
	if !status.Checks["workers"] {
		status.Status = "warning"
		status.Message = "没有活跃的工作节点"
	}

	// 检查失败队列
	if stats.TasksFailed > 100 {
		status.Status = "warning"
		status.Message = "失败任务过多"
	}

	// 检查队列积压
	if stats.Queues["pending"] > 1000 {
		status.Status = "warning"
		status.Message = "队列积压严重"
	}

	return status
}

// HealthStatus 健康状态
type HealthStatus struct {
	Status    string            `json:"status"` // healthy, warning, critical
	Message   string            `json:"message,omitempty"`
	Timestamp time.Time         `json:"timestamp"`
	Checks    map[string]bool   `json:"checks"`
}

// HTTPHandler 创建 HTTP 处理器
func (m *Monitor) HTTPHandler() http.Handler {
	mux := http.NewServeMux()

	// 统计信息
	mux.HandleFunc("/stats", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		data, err := m.GetStatsJSON()
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.Write(data)
	})

	// 健康检查
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		health := m.GetHealthStatus()
		data, _ := json.Marshal(health)
		w.Write(data)
	})

	// 工作节点列表
	mux.HandleFunc("/workers", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		stats := m.GetStats()
		data, _ := json.MarshalIndent(stats.Workers, "", "  ")
		w.Write(data)
	})

	// 队列统计
	mux.HandleFunc("/queues", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		stats := m.GetQueueStats()
		data, _ := json.MarshalIndent(stats, "", "  ")
		w.Write(data)
	})

	return mux
}

// StartHTTPServer 启动 HTTP 监控服务器
func (m *Monitor) StartHTTPServer(addr string) error {
	handler := m.HTTPHandler()
	server := &http.Server{
		Addr:    addr,
		Handler: handler,
	}

	fmt.Printf("监控服务器启动在：%s\n", addr)
	return server.ListenAndServe()
}
