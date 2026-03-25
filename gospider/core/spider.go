// Gospider 核心爬虫模块

//! 爬虫核心实现
//! 
//! 吸收 Crawlee 的爬虫设计理念

package core

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"gospider/queue"
	"gospider/storage"
)

// SpiderConfig - 爬虫配置
type SpiderConfig struct {
	Name           string
	Concurrency    int           // 并发数
	MaxRequests    int           // 最大请求数
	MaxDepth       int           // 最大深度
	RequestTimeout time.Duration // 请求超时
	RetryCount     int           // 重试次数
	UserAgent      string        // User-Agent
	ProxyURL       string        // 代理 URL
	Delay          time.Duration // 请求延迟
}

// DefaultSpiderConfig returns defaults for the legacy Spider API.
func DefaultSpiderConfig() *SpiderConfig {
	return &SpiderConfig{
		Name:           "default",
		Concurrency:    5,
		MaxRequests:    1000,
		MaxDepth:       5,
		RequestTimeout: 30 * time.Second,
		RetryCount:     3,
		UserAgent:      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
		ProxyURL:       "",
		Delay:          100 * time.Millisecond,
	}
}

// Spider - 爬虫核心
type Spider struct {
	config      *SpiderConfig
	queue       *queue.DedupQueue
	dataset     *storage.Dataset
	kvs         *storage.KeyValueStore
	httpClient  *http.Client
	httpExecutor Executor
	ctx         context.Context
	cancel      context.CancelFunc
	wg          sync.WaitGroup
	mu          sync.RWMutex
	running     bool
	requested   int
	handled     int
	failed      int
	onRequest   func(*queue.Request) error
	onResponse  func(*queue.Request, *http.Response) error
	onError     func(*queue.Request, error)
}

// NewSpider - 创建爬虫
func NewSpider(config *SpiderConfig) *Spider {
	if config == nil {
		config = DefaultSpiderConfig()
	}

	ctx, cancel := context.WithCancel(context.Background())

	// 创建队列
	pq := queue.NewPriorityQueue()
	dedupQueue := queue.NewDedupQueue(pq)

	// 创建存储
	dataset := storage.NewDataset(config.Name)
	kvs := storage.NewKeyValueStore(config.Name)

	// 创建 HTTP 客户端
	transport := &http.Transport{
		MaxIdleConns:        100,
		MaxIdleConnsPerHost: 10,
		IdleConnTimeout:     90 * time.Second,
	}

	httpClient := &http.Client{
		Transport: transport,
		Timeout:   config.RequestTimeout,
	}

	return &Spider{
		config:     config,
		queue:      dedupQueue,
		dataset:    dataset,
		kvs:        kvs,
		httpClient: httpClient,
		ctx:        ctx,
		cancel:     cancel,
		running:    false,
	}
}

// AddRequest - 添加请求
func (s *Spider) AddRequest(req *queue.Request) error {
	return s.queue.Push(req)
}

// AddJob adds a normalized job by adapting it into the current request queue.
func (s *Spider) AddJob(job *JobSpec) error {
	if job == nil {
		return fmt.Errorf("job is required")
	}
	if err := job.Validate(); err != nil {
		return err
	}

	method := job.Target.Method
	if method == "" {
		method = "GET"
	}

	req := &queue.Request{
		URL:      job.Target.URL,
		Method:   method,
		Headers:  job.Target.Headers,
		Body:     []byte(job.Target.Body),
		Priority: job.Priority,
		Meta: map[string]interface{}{
			"job_name": job.Name,
			"runtime":  string(job.Runtime),
		},
	}
	return s.AddRequest(req)
}

// AddRequests - 批量添加请求
func (s *Spider) AddRequests(urls []string) error {
	for _, u := range urls {
		req := &queue.Request{
			URL:      u,
			Method:   "GET",
			Priority: 0,
		}
		if err := s.AddRequest(req); err != nil {
			return err
		}
	}
	return nil
}

// SetOnRequest - 设置请求回调
func (s *Spider) SetOnRequest(fn func(*queue.Request) error) {
	s.onRequest = fn
}

// SetOnResponse - 设置响应回调
func (s *Spider) SetOnResponse(fn func(*queue.Request, *http.Response) error) {
	s.onResponse = fn
}

// SetOnError - 设置错误回调
func (s *Spider) SetOnError(fn func(*queue.Request, error)) {
	s.onError = fn
}

// SetHTTPExecutor injects the normalized HTTP execution seam used by the spider.
func (s *Spider) SetHTTPExecutor(executor Executor) {
	s.httpExecutor = executor
}

// Run - 运行爬虫
func (s *Spider) Run() error {
	s.mu.Lock()
	if s.running {
		s.mu.Unlock()
		return fmt.Errorf("spider is already running")
	}
	s.running = true
	s.mu.Unlock()

	defer func() {
		s.mu.Lock()
		s.running = false
		s.mu.Unlock()
	}()

	// 启动工作协程
	for i := 0; i < s.config.Concurrency; i++ {
		s.wg.Add(1)
		go s.worker(i)
	}

	// 等待完成
	s.wg.Wait()

	log.Printf("Spider finished: requested=%d, handled=%d, failed=%d",
		s.requested, s.handled, s.failed)

	return nil
}

// Stop - 停止爬虫
func (s *Spider) Stop() {
	s.cancel()
	s.wg.Wait()
	s.mu.Lock()
	s.running = false
	s.mu.Unlock()
}

// IsRunning - 是否运行中
func (s *Spider) IsRunning() bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.running
}

// GetStats - 获取统计信息
func (s *Spider) GetStats() map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()

	return map[string]interface{}{
		"name":       s.config.Name,
		"running":    s.running,
		"requested":  s.requested,
		"handled":    s.handled,
		"failed":     s.failed,
		"queue_size": s.queue.Size(),
	}
}

// GetDataset - 获取数据集
func (s *Spider) GetDataset() *storage.Dataset {
	return s.dataset
}

// GetKVS - 获取键值存储
func (s *Spider) GetKVS() *storage.KeyValueStore {
	return s.kvs
}

// worker - 工作协程
func (s *Spider) worker(id int) {
	defer s.wg.Done()

	for {
		select {
		case <-s.ctx.Done():
			return
		default:
			// 检查是否达到最大请求数
			if s.config.MaxRequests > 0 && s.requested >= s.config.MaxRequests {
				return
			}

			// 获取请求
			req, err := s.queue.Pop()
			if err != nil {
				// 队列为空，等待
				time.Sleep(100 * time.Millisecond)
				continue
			}

			// 执行请求
			s.executeRequest(id, req)
		}
	}
}

// executeRequest - 执行请求
func (s *Spider) executeRequest(workerID int, req *queue.Request) {
	s.mu.Lock()
	s.requested++
	s.mu.Unlock()

	log.Printf("Worker %d: Processing %s", workerID, req.URL)

	// 请求回调
	if s.onRequest != nil {
		if err := s.onRequest(req); err != nil {
			log.Printf("Request callback error: %v", err)
			return
		}
	}

	if s.httpExecutor != nil {
		job := JobSpec{
			Name:    req.URL,
			Runtime: RuntimeHTTP,
			Target: TargetSpec{
				URL:     req.URL,
				Method:  req.Method,
				Headers: cloneRequestHeaders(req.Headers),
				Body:    string(req.Body),
			},
			Priority: req.Priority,
		}
		if job.Target.Method == "" {
			job.Target.Method = http.MethodGet
		}
		if job.Target.Headers == nil {
			job.Target.Headers = make(map[string]string)
		}
		if job.Target.Headers["User-Agent"] == "" {
			job.Target.Headers["User-Agent"] = s.config.UserAgent
		}

		result, err := s.httpExecutor.Execute(s.ctx, job)
		if err != nil {
			s.handleError(req, err)
			return
		}

		if result != nil && result.State == StateSucceeded {
			s.mu.Lock()
			s.handled++
			s.mu.Unlock()
		}

		if s.config.Delay > 0 {
			time.Sleep(s.config.Delay)
		}
		return
	}

	// 创建 HTTP 请求
	httpReq, err := http.NewRequest(req.Method, req.URL, nil)
	if err != nil {
		s.handleError(req, err)
		return
	}

	// 设置请求头
	for k, v := range req.Headers {
		httpReq.Header.Set(k, v)
	}
	if httpReq.Header.Get("User-Agent") == "" {
		httpReq.Header.Set("User-Agent", s.config.UserAgent)
	}

	// 发送请求
	resp, err := s.httpClient.Do(httpReq)
	if err != nil {
		s.handleError(req, err)
		return
	}
	defer resp.Body.Close()

	// 响应回调
	if s.onResponse != nil {
		if err := s.onResponse(req, resp); err != nil {
			log.Printf("Response callback error: %v", err)
			s.handleError(req, err)
			return
		}
	}

	s.mu.Lock()
	s.handled++
	s.mu.Unlock()

	// 延迟
	if s.config.Delay > 0 {
		time.Sleep(s.config.Delay)
	}
}

func cloneRequestHeaders(headers map[string]string) map[string]string {
	if headers == nil {
		return nil
	}
	cloned := make(map[string]string, len(headers))
	for k, v := range headers {
		cloned[k] = v
	}
	return cloned
}

// handleError - 处理错误
func (s *Spider) handleError(req *queue.Request, err error) {
	s.mu.Lock()
	s.failed++
	s.mu.Unlock()

	log.Printf("Request error: %s - %v", req.URL, err)

	// 错误回调
	if s.onError != nil {
		s.onError(req, err)
	}

	// 重试
	if req.RetryCount < s.config.RetryCount {
		req.RetryCount++
		req.Priority++ // 提高优先级
		s.queue.Push(req)
		log.Printf("Retrying request: %s (retry %d)", req.URL, req.RetryCount)
	}
}

// SaveResults - 保存结果
func (s *Spider) SaveResults(path string, format string) error {
	return s.dataset.Save(path, format)
}

// GetResults - 获取结果
func (s *Spider) GetResults() []map[string]interface{} {
	return s.dataset.ToList()
}

// Clear - 清空状态
func (s *Spider) Clear() {
	s.queue.Clear()
	s.dataset = storage.NewDataset(s.config.Name)
	s.kvs = storage.NewKeyValueStore(s.config.Name)
	s.requested = 0
	s.handled = 0
	s.failed = 0
}

// Example - 使用示例
func Example() {
	// 创建爬虫
	config := DefaultSpiderConfig()
	config.Name = "example"
	config.Concurrency = 5

	spider := NewSpider(config)

	// 添加请求
	spider.AddRequests([]string{
		"https://example.com/page1",
		"https://example.com/page2",
	})

	// 设置回调
	spider.SetOnResponse(func(req *queue.Request, resp *http.Response) error {
		// 处理响应
		data := map[string]interface{}{
			"url":    req.URL,
			"status": resp.StatusCode,
		}
		spider.GetDataset().Push(data)
		return nil
	})

	// 运行爬虫
	if err := spider.Run(); err != nil {
		log.Fatal(err)
	}

	// 保存结果
	spider.SaveResults("results.json", "json")

	// 获取统计
	stats := spider.GetStats()
	fmt.Printf("Stats: %+v\n", stats)
}
