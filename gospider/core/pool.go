package core

import (
	"sync"
	"sync/atomic"
	"time"
)

// WorkerPool 工作池（增强多线程）
type WorkerPool struct {
	workers   int
	taskChan  chan func()
	wg        sync.WaitGroup
	active    int32
	shutdown  int32
}

// NewWorkerPool 创建工作池
func NewWorkerPool(workers int, queueSize int) *WorkerPool {
	wp := &WorkerPool{
		workers:  workers,
		taskChan: make(chan func(), queueSize),
	}
	wp.start()
	return wp
}

// start 启动工作池
func (wp *WorkerPool) start() {
	for i := 0; i < wp.workers; i++ {
		wp.wg.Add(1)
		go wp.worker()
	}
}

// worker 工作协程
func (wp *WorkerPool) worker() {
	defer wp.wg.Done()
	
	for {
		if atomic.LoadInt32(&wp.shutdown) == 1 {
			return
		}
		
		select {
		case task, ok := <-wp.taskChan:
			if !ok {
				return
			}
			atomic.AddInt32(&wp.active, 1)
			task()
			atomic.AddInt32(&wp.active, -1)
		case <-time.After(100 * time.Millisecond):
			// 超时继续循环
		}
	}
}

// Submit 提交任务
func (wp *WorkerPool) Submit(task func()) bool {
	if atomic.LoadInt32(&wp.shutdown) == 1 {
		return false
	}
	
	select {
	case wp.taskChan <- task:
		return true
	default:
		return false
	}
}

// SubmitWait 提交任务（等待）
func (wp *WorkerPool) SubmitWait(task func()) {
	if atomic.LoadInt32(&wp.shutdown) == 1 {
		return
	}
	wp.taskChan <- task
}

// ActiveWorkers 获取活跃工作协程数
func (wp *WorkerPool) ActiveWorkers() int {
	return int(atomic.LoadInt32(&wp.active))
}

// Shutdown 关闭工作池
func (wp *WorkerPool) Shutdown() {
	atomic.StoreInt32(&wp.shutdown, 1)
	close(wp.taskChan)
	wp.wg.Wait()
}

// Wait 等待所有任务完成
func (wp *WorkerPool) Wait() {
	wp.wg.Wait()
}

// Stats 工作池统计
type PoolStats struct {
	Workers      int
	Active       int32
	Queued       int
	IsShutdown   bool
}

// GetStats 获取统计
func (wp *WorkerPool) GetStats() PoolStats {
	return PoolStats{
		Workers:    wp.workers,
		Active:     atomic.LoadInt32(&wp.active),
		Queued:     len(wp.taskChan),
		IsShutdown: atomic.LoadInt32(&wp.shutdown) == 1,
	}
}

// ConcurrentExecutor 并发执行器
type ConcurrentExecutor struct {
	maxConcurrent int
	semaphore     chan struct{}
	wg            sync.WaitGroup
}

// NewConcurrentExecutor 创建并发执行器
func NewConcurrentExecutor(maxConcurrent int) *ConcurrentExecutor {
	return &ConcurrentExecutor{
		maxConcurrent: maxConcurrent,
		semaphore:     make(chan struct{}, maxConcurrent),
	}
}

// Execute 执行任务
func (ce *ConcurrentExecutor) Execute(task func()) {
	ce.semaphore <- struct{}{}
	ce.wg.Add(1)
	
	go func() {
		defer ce.wg.Done()
		defer func() { <-ce.semaphore }()
		task()
	}()
}

// Wait 等待所有任务完成
func (ce *ConcurrentExecutor) Wait() {
	ce.wg.Wait()
}

// RateLimitedExecutor 限流执行器
type RateLimitedExecutor struct {
	rate       int
	interval   time.Duration
	tokens     chan struct{}
	shutdown   chan struct{}
}

// NewRateLimitedExecutor 创建限流执行器
func NewRateLimitedExecutor(rate int, interval time.Duration) *RateLimitedExecutor {
	rle := &RateLimitedExecutor{
		rate:     rate,
		interval: interval,
		tokens:   make(chan struct{}, rate),
		shutdown: make(chan struct{}),
	}
	rle.startTokenBucket()
	return rle
}

// startTokenBucket 启动令牌桶
func (rle *RateLimitedExecutor) startTokenBucket() {
	// 初始化令牌
	for i := 0; i < rle.rate; i++ {
		rle.tokens <- struct{}{}
	}
	
	go func() {
		ticker := time.NewTicker(rle.interval)
		defer ticker.Stop()
		
		for {
			select {
			case <-ticker.C:
				select {
				case rle.tokens <- struct{}{}:
				default:
				}
			case <-rle.shutdown:
				return
			}
		}
	}()
}

// Execute 执行任务（带限流）
func (rle *RateLimitedExecutor) Execute(task func()) {
	<-rle.tokens
	go task()
}

// Shutdown 关闭
func (rle *RateLimitedExecutor) Shutdown() {
	close(rle.shutdown)
}
