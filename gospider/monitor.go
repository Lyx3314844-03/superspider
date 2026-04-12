package main

import (
	"fmt"
	"runtime"
	"sync"
	"time"
)

// Metrics 监控指标
type Metrics struct {
	TotalRequests   int64
	SuccessRequests int64
	FailedRequests  int64
	TotalBytes      int64
	StartTime       time.Time
	mu              sync.RWMutex
}

// Monitor 监控器
type Monitor struct {
	metrics *Metrics
}

// NewMonitor 新建监控器
func NewMonitor() *Monitor {
	return &Monitor{
		metrics: &Metrics{
			StartTime: time.Now(),
		},
	}
}

// RecordRequest 记录请求
func (m *Monitor) RecordRequest(success bool, bytes int64) {
	m.metrics.mu.Lock()
	defer m.metrics.mu.Unlock()
	
	m.metrics.TotalRequests++
	if success {
		m.metrics.SuccessRequests++
	} else {
		m.metrics.FailedRequests++
	}
	m.metrics.TotalBytes += bytes
}

// GetSuccessRate 获取成功率
func (m *Monitor) GetSuccessRate() float64 {
	m.metrics.mu.RLock()
	defer m.metrics.mu.RUnlock()
	
	if m.metrics.TotalRequests == 0 {
		return 0
	}
	return float64(m.metrics.SuccessRequests) / float64(m.metrics.TotalRequests) * 100
}

// GetStats 获取统计信息
func (m *Monitor) GetStats() map[string]interface{} {
	m.metrics.mu.RLock()
	defer m.metrics.mu.RUnlock()
	
	var memStats runtime.MemStats
	runtime.ReadMemStats(&memStats)
	
	return map[string]interface{}{
		"total_requests":    m.metrics.TotalRequests,
		"success_requests":  m.metrics.SuccessRequests,
		"failed_requests":   m.metrics.FailedRequests,
		"success_rate":      m.GetSuccessRate(),
		"total_bytes":       m.metrics.TotalBytes,
		"uptime_seconds":    time.Since(m.metrics.StartTime).Seconds(),
		"memory_alloc":      memStats.Alloc,
		"memory_sys":        memStats.Sys,
	}
}

// PrintStats 打印统计信息
func (m *Monitor) PrintStats() {
	stats := m.GetStats()
	fmt.Println("=== 性能统计 ===")
	fmt.Printf("总请求: %d\n", stats["total_requests"])
	fmt.Printf("成功: %d\n", stats["success_requests"])
	fmt.Printf("失败: %d\n", stats["failed_requests"])
	fmt.Printf("成功率: %.2f%%\n", stats["success_rate"])
	fmt.Printf("运行时长: %.2f秒\n", stats["uptime_seconds"])
	fmt.Printf("内存占用: %d bytes\n", stats["memory_alloc"])
}

// StartMonitoring 开始监控
func (m *Monitor) StartMonitoring(interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	
	for range ticker.C {
		m.PrintStats()
	}
}
