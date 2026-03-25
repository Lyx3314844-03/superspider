package core

import (
	"context"
	"fmt"
	"math"
	"net/http"
	"runtime"
	"sync"
	"sync/atomic"
	"time"

	"gospider/queue"
	"gospider/storage"
)

// SpiderConfigV3 - 高性能配置
type SpiderConfigV3 struct {
	Name              string
	Concurrency       int           // 并发数 (自动设置为 CPU 核心数*10)
	MaxConnections    int           // 最大连接数
	MaxRequests       int           // 最大请求数
	MaxDepth          int           // 最大深度
	RequestTimeout    time.Duration // 请求超时
	RetryCount        int           // 重试次数
	UserAgent         string        // User-Agent
	ProxyURL          string        // 代理 URL
	Delay             time.Duration // 请求延迟
	RateLimit         float64       // 速率限制 (请求/秒)
	EnableCompression bool          // 启用压缩
	EnableKeepAlive   bool          // 启用长连接
	DisableRedirects  bool          // 禁用重定向
}

// DefaultSpiderConfigV3 - 默认配置 (性能优化)
func DefaultSpiderConfigV3() *SpiderConfigV3 {
	return &SpiderConfigV3{
		Name:              "default",
		Concurrency:       runtime.NumCPU() * 10, // 自动设置
		MaxConnections:    1000,
		MaxRequests:       100000,
		MaxDepth:          10,
		RequestTimeout:    30 * time.Second,
		RetryCount:        3,
		UserAgent:         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
		ProxyURL:          "",
		Delay:             0,
		RateLimit:         0,
		EnableCompression: true,  // 启用压缩减少传输
		EnableKeepAlive:   true,  // 启用长连接复用
		DisableRedirects:  false, // 跟随重定向
	}
}

// SpiderV3 - 高性能爬虫引擎
type SpiderV3 struct {
	config      *SpiderConfigV3
	queue       *queue.DedupQueue
	dataset     *storage.Dataset
	kvs         *storage.KeyValueStore
	httpClient  *http.Client
	ctx         context.Context
	cancel      context.CancelFunc
	running     int32
	requested   int64
	success     int64
	failed      int64
	items       int64
	startTime   time.Time
	endTime     time.Time
	rateLimiter *RateLimiterV3
	bloomFilter *BloomFilterV3
	requestPool *RequestPoolV3
	responsePool *ResponsePoolV3
}

// RequestPoolV3 - 请求对象池
type RequestPoolV3 struct {
	pool sync.Pool
}

func NewRequestPoolV3() *RequestPoolV3 {
	return &RequestPoolV3{
		pool: sync.Pool{
			New: func() interface{} {
				return &queue.Request{}
			},
		},
	}
}

func (p *RequestPoolV3) Get() *queue.Request {
	return p.pool.Get().(*queue.Request)
}

func (p *RequestPoolV3) Put(req *queue.Request) {
	// 重置字段
	req.URL = ""
	req.Method = ""
	req.Headers = nil
	req.Body = nil
	req.Meta = nil
	req.Priority = 0
	p.pool.Put(req)
}

// ResponsePoolV3 - 响应对象池
type ResponsePoolV3 struct {
	pool sync.Pool
}

func NewResponsePoolV3() *ResponsePoolV3 {
	return &ResponsePoolV3{
		pool: sync.Pool{
			New: func() interface{} {
				return &http.Response{}
			},
		},
	}
}

func (p *ResponsePoolV3) Get() *http.Response {
	return p.pool.Get().(*http.Response)
}

func (p *ResponsePoolV3) Put(resp *http.Response) {
	p.pool.Put(resp)
}

// RateLimiterV3 - 高性能速率限制器 (令牌桶算法)
type RateLimiterV3 struct {
	rate       float64
	capacity   float64
	tokens     float64
	lastUpdate time.Time
	mu         sync.Mutex
}

func NewRateLimiterV3(rate float64) *RateLimiterV3 {
	return &RateLimiterV3{
		rate:       rate,
		capacity:   rate,
		tokens:     rate,
		lastUpdate: time.Now(),
	}
}

func (r *RateLimiterV3) Wait(ctx context.Context) error {
	if r.rate <= 0 {
		return nil
	}

	r.mu.Lock()
	now := time.Now()
	elapsed := now.Sub(r.lastUpdate).Seconds()
	r.tokens = min(r.capacity, r.tokens+elapsed*r.rate)
	r.lastUpdate = now

	if r.tokens < 1 {
		waitTime := time.Duration((1-r.tokens)/r.rate*1000) * time.Millisecond
		r.mu.Unlock()

		// 处理 nil context 情况
		if ctx == nil {
			time.After(waitTime)
			r.mu.Lock()
			r.tokens = 0
			r.mu.Unlock()
			return nil
		}

		select {
		case <-time.After(waitTime):
			r.mu.Lock()
			r.tokens = 0
			r.mu.Unlock()
		case <-ctx.Done():
			return ctx.Err()
		}
	} else {
		r.tokens--
		r.mu.Unlock()
	}

	return nil
}

// BloomFilterV3 - 高性能布隆过滤器
type BloomFilterV3 struct {
	bits        []byte
	numHashes   int
	expectedNum int64
}

func NewBloomFilterV3(expectedNum int64, fpp float64) *BloomFilterV3 {
	// 计算最优参数
	numBits := int(-float64(expectedNum) * 8 * math.Log(fpp) / (math.Log(2) * math.Log(2)))
	numHashes := int(float64(numBits) / float64(expectedNum) * math.Log(2))

	return &BloomFilterV3{
		bits:        make([]byte, numBits/8+1),
		numHashes:   numHashes,
		expectedNum: expectedNum,
	}
}

func (b *BloomFilterV3) Add(data []byte) {
	h1, h2 := hashBytes(data)
	for i := 0; i < b.numHashes; i++ {
		combinedHash := h1 + uint64(i)*h2
		bitIndex := combinedHash % uint64(len(b.bits)*8)
		byteIndex := bitIndex / 8
		bitMask := byte(1 << (bitIndex % 8))
		b.bits[byteIndex] |= bitMask
	}
}

func (b *BloomFilterV3) Contains(data []byte) bool {
	h1, h2 := hashBytes(data)
	for i := 0; i < b.numHashes; i++ {
		combinedHash := h1 + uint64(i)*h2
		bitIndex := combinedHash % uint64(len(b.bits)*8)
		byteIndex := bitIndex / 8
		bitMask := byte(1 << (bitIndex % 8))
		if b.bits[byteIndex]&bitMask == 0 {
			return false
		}
	}
	return true
}

func hashBytes(data []byte) (uint64, uint64) {
	// 使用 FNV-1a 哈希
	var h1 uint64 = 0xcbf29ce484222325
	var h2 uint64 = 0x811c9dc5

	for _, b := range data {
		h1 ^= uint64(b)
		h1 *= 0x100000001b3
		h2 ^= uint64(b)
		h2 *= 0x01000193
	}

	return h1, h2
}

// NewSpiderV3 - 创建高性能爬虫
func NewSpiderV3(config *SpiderConfigV3) *SpiderV3 {
	if config == nil {
		config = DefaultSpiderConfigV3()
	}

	ctx, cancel := context.WithCancel(context.Background())

	// 创建队列
	pq := queue.NewPriorityQueue()
	dedupQueue := queue.NewDedupQueue(pq)

	// 创建存储
	dataset := storage.NewDataset(config.Name)
	kvs := storage.NewKeyValueStore(config.Name)

	// 创建 HTTP 客户端 (性能优化)
	transport := &http.Transport{
		MaxIdleConns:        config.MaxConnections,
		MaxIdleConnsPerHost: config.MaxConnections / 10,
		IdleConnTimeout:     90 * time.Second,
		DisableCompression:  !config.EnableCompression,
		ForceAttemptHTTP2:   true,
	}

	httpClient := &http.Client{
		Transport: transport,
		Timeout:   config.RequestTimeout,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			if config.DisableRedirects {
				return http.ErrUseLastResponse
			}
			return nil
		},
	}

	// 创建速率限制器
	var rateLimiter *RateLimiterV3
	if config.RateLimit > 0 {
		rateLimiter = NewRateLimiterV3(config.RateLimit)
	}

	// 创建布隆过滤器
	bloomFilter := NewBloomFilterV3(1_000_000, 0.01)

	return &SpiderV3{
		config:       config,
		queue:        dedupQueue,
		dataset:      dataset,
		kvs:          kvs,
		httpClient:   httpClient,
		ctx:          ctx,
		cancel:       cancel,
		rateLimiter:  rateLimiter,
		bloomFilter:  bloomFilter,
		requestPool:  NewRequestPoolV3(),
		responsePool: NewResponsePoolV3(),
	}
}

// AddRequest - 添加请求 (性能优化)
func (s *SpiderV3) AddRequest(req *queue.Request) error {
	// 布隆过滤器去重
	urlBytes := []byte(req.URL)
	if s.bloomFilter.Contains(urlBytes) {
		return nil
	}
	s.bloomFilter.Add(urlBytes)

	return s.queue.Push(req)
}

// Run - 运行爬虫 (高性能版本)
func (s *SpiderV3) Run() error {
	atomic.StoreInt32(&s.running, 1)
	s.startTime = time.Now()

	// 设置 GOMAXPROCS
	runtime.GOMAXPROCS(runtime.NumCPU())

	// 启动工作协程
	var wg sync.WaitGroup
	for i := 0; i < s.config.Concurrency; i++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			s.worker(workerID)
		}(i)
	}

	// 等待完成
	wg.Wait()

	s.endTime = time.Now()
	atomic.StoreInt32(&s.running, 0)

	// 打印统计
	elapsed := s.endTime.Sub(s.startTime).Seconds()
	qps := float64(atomic.LoadInt64(&s.requested)) / elapsed

	fmt.Printf("\n%s\n", "==================================================")
	fmt.Printf("爬虫完成：%s\n", s.config.Name)
	fmt.Printf("总请求数：%d\n", atomic.LoadInt64(&s.requested))
	fmt.Printf("成功：%d\n", atomic.LoadInt64(&s.success))
	fmt.Printf("失败：%d\n", atomic.LoadInt64(&s.failed))
	fmt.Printf("抓取项：%d\n", atomic.LoadInt64(&s.items))
	fmt.Printf("耗时：%.2fs\n", elapsed)
	fmt.Printf("QPS: %.2f\n", qps)
	fmt.Printf("%s\n", "==================================================")

	return nil
}

// worker - 工作协程
func (s *SpiderV3) worker(_ int) {
	for {
		req, err := s.queue.Pop()
		if err != nil {
			if atomic.LoadInt32(&s.running) == 0 {
				return
			}
			time.Sleep(100 * time.Millisecond)
			continue
		}

		// 速率限制
		if s.rateLimiter != nil {
			if err := s.rateLimiter.Wait(context.Background()); err != nil {
				return
			}
		}

		// 处理请求
		s.processRequest(context.Background(), req)
	}
}

// processRequest - 处理请求
func (s *SpiderV3) processRequest(ctx context.Context, req *queue.Request) {
	defer func() {
		atomic.AddInt64(&s.requested, 1)
	}()

	// 创建 HTTP 请求
	httpReq, err := http.NewRequestWithContext(ctx, req.Method, req.URL, nil)
	if err != nil {
		atomic.AddInt64(&s.failed, 1)
		return
	}

	// 设置 headers
	for k, v := range req.Headers {
		httpReq.Header.Set(k, v)
	}

	// 发送请求
	resp, err := s.httpClient.Do(httpReq)
	if err != nil {
		atomic.AddInt64(&s.failed, 1)
		return
	}
	defer resp.Body.Close()

	atomic.AddInt64(&s.success, 1)

	// 处理响应
	// ... (解析、提取等)
}

// GetStats - 获取统计信息
func (s *SpiderV3) GetStats() map[string]interface{} {
	elapsed := s.endTime.Sub(s.startTime).Seconds()
	if elapsed == 0 {
		elapsed = 1
	}

	return map[string]interface{}{
		"total_requests":   atomic.LoadInt64(&s.requested),
		"success_requests": atomic.LoadInt64(&s.success),
		"failed_requests":  atomic.LoadInt64(&s.failed),
		"items_scraped":    atomic.LoadInt64(&s.items),
		"elapsed_seconds":  elapsed,
		"qps":              float64(atomic.LoadInt64(&s.requested)) / elapsed,
	}
}

// Stop - 停止爬虫
func (s *SpiderV3) Stop() {
	atomic.StoreInt32(&s.running, 0)
	s.cancel()
}

// IsRunning - 是否运行中
func (s *SpiderV3) IsRunning() bool {
	return atomic.LoadInt32(&s.running) == 1
}
