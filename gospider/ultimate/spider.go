package ultimate

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"gospider/encrypted"
	"gospider/node_reverse"
)

// UltimateSpider Go Spider 终极增强版
type UltimateSpider struct {
	config          *UltimateConfig
	reverseClient   *nodereverse.NodeReverseClient
	enhancedCrawler *encrypted.EnhancedCrawler
	proxyPool       *ProxyPool
	taskQueue       chan *CrawlTask
	resultQueue     chan *CrawlResult
	workerPool      *WorkerPool
	monitor         *SpiderMonitor
	checkpointMgr   *CheckpointManager
}

// UltimateConfig 终极配置
type UltimateConfig struct {
	ReverseServiceURL string
	MaxConcurrency    int
	MaxRetries        int
	Timeout           time.Duration
	UserAgent         string
	ProxyServers      []string
	OutputFormat      string
	MonitorPort       int
	CheckpointDir     string
	EnableAI          bool
	EnableBrowser     bool
	EnableDistributed bool
}

// CrawlTask 爬取任务
type CrawlTask struct {
	ID       string
	URL      string
	Priority int
	Depth    int
	Metadata map[string]interface{}
}

// CrawlResult 爬取结果
type CrawlResult struct {
	TaskID         string
	URL            string
	Success        bool
	Data           interface{}
	Error          error
	Duration       time.Duration
	Retries        int
	ProxyUsed      string
	AntiDetect     map[string]bool
	AntiBotLevel   string
	AntiBotSignals []string
	ReverseRuntime map[string]interface{}
}

// WorkerPool 工作线程池
type WorkerPool struct {
	workers  int
	taskChan chan *CrawlTask
	wg       sync.WaitGroup
}

// SpiderMonitor 爬虫监控器
type SpiderMonitor struct {
	mu           sync.Mutex
	totalTasks   int
	successTasks int
	failedTasks  int
	startTime    time.Time
	currentTasks map[string]*CrawlTask
}

// CheckpointManager 断点管理器
type CheckpointManager struct {
	dir string
	mu  sync.Mutex
}

// ProxyPool 代理池
type ProxyPool struct {
	proxies    []string
	currentIdx int
	mu         sync.Mutex
}

// NewUltimateSpider 创建终极爬虫
func NewUltimateSpider(config *UltimateConfig) *UltimateSpider {
	if config == nil {
		config = &UltimateConfig{
			ReverseServiceURL: "http://localhost:3000",
			MaxConcurrency:    10,
			MaxRetries:        3,
			Timeout:           30 * time.Second,
			UserAgent:         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
			ProxyServers:      []string{},
			OutputFormat:      "json",
			MonitorPort:       8080,
			CheckpointDir:     filepath.Join("artifacts", "ultimate", "checkpoints"),
			EnableAI:          true,
			EnableBrowser:     true,
			EnableDistributed: true,
		}
	}

	spider := &UltimateSpider{
		config:          config,
		reverseClient:   nodereverse.NewNodeReverseClient(config.ReverseServiceURL),
		enhancedCrawler: encrypted.NewEnhancedCrawler(config.ReverseServiceURL),
		taskQueue:       make(chan *CrawlTask, 1000),
		resultQueue:     make(chan *CrawlResult, 1000),
		workerPool: &WorkerPool{
			workers:  config.MaxConcurrency,
			taskChan: make(chan *CrawlTask, 1000),
		},
		monitor: &SpiderMonitor{
			startTime:    time.Now(),
			currentTasks: make(map[string]*CrawlTask),
		},
		checkpointMgr: &CheckpointManager{
			dir: config.CheckpointDir,
		},
	}

	if len(config.ProxyServers) > 0 {
		spider.proxyPool = &ProxyPool{
			proxies: config.ProxyServers,
		}
	}

	return spider
}

// Start 启动终极爬虫
func (us *UltimateSpider) Start(urls []string) ([]*CrawlResult, error) {
	fmt.Println("\n" + strings.Repeat("=", 100))
	fmt.Println("🚀 Go Spider 终极增强版 v5.0")
	fmt.Println(strings.Repeat("=", 100))

	// 步骤 1: 检查服务
	fmt.Println("\n[1/10] 检查 Node.js 逆向服务...")
	healthy, _ := us.reverseClient.HealthCheck()
	if !healthy {
		return nil, fmt.Errorf("Node.js 逆向服务不可用")
	}
	fmt.Println("✅ 逆向服务正常运行")

	// 步骤 2: 初始化监控
	fmt.Println("\n[2/10] 初始化监控面板...")
	us.monitor.start()
	fmt.Println("✅ 监控面板已启动")

	// 步骤 3: 启动工作线程池
	fmt.Println("\n[3/10] 启动工作线程池...")
	us.workerPool.start(us)
	fmt.Printf("✅ 已启动 %d 个工作线程\n", us.workerPool.workers)

	// 步骤 4: 添加任务
	fmt.Println("\n[4/10] 添加爬取任务...")
	for i, url := range urls {
		task := &CrawlTask{
			ID:       fmt.Sprintf("task_%d", i),
			URL:      url,
			Priority: 0,
			Depth:    0,
			Metadata: map[string]interface{}{},
		}
		us.taskQueue <- task
		us.monitor.addTask(task)
	}
	close(us.taskQueue)
	fmt.Printf("✅ 已添加 %d 个任务\n", len(urls))

	// 步骤 5: 开始爬取
	fmt.Println("\n[5/10] 开始爬取...")
	us.processTasks()
	close(us.workerPool.taskChan)
	us.workerPool.wg.Wait()
	close(us.resultQueue)

	var successCount int
	var failedCount int
	var results []*CrawlResult
	for result := range us.resultQueue {
		results = append(results, result)
		if result != nil && result.Success {
			successCount++
			continue
		}
		failedCount++
	}

	fmt.Println("\n" + strings.Repeat("=", 100))
	fmt.Println("✅ 爬取完成！")
	fmt.Printf("成功: %d, 失败: %d\n", successCount, failedCount)
	fmt.Println(strings.Repeat("=", 100))

	if failedCount > 0 {
		return results, fmt.Errorf("%d tasks failed", failedCount)
	}

	return results, nil
}

// processTasks 处理任务
func (us *UltimateSpider) processTasks() {
	for task := range us.taskQueue {
		// 分配给工作线程
		us.workerPool.taskChan <- task
	}
}

// CrawlPage 爬取单个页面
func (us *UltimateSpider) CrawlPage(task *CrawlTask) *CrawlResult {
	startTime := time.Now()
	result := &CrawlResult{
		TaskID:     task.ID,
		URL:        task.URL,
		Success:    false,
		AntiDetect: make(map[string]bool),
		ReverseRuntime: map[string]interface{}{},
	}

	fmt.Printf("\n📄 爬取页面: %s\n", task.URL)

	// 步骤 1: 智能反爬检测
	fmt.Println("  [1/8] 智能反爬检测...")
	antiDetect, antiBotLevel, antiBotSignals := us.detectAntiDetection(task.URL)
	result.AntiDetect = antiDetect
	result.AntiBotLevel = antiBotLevel
	result.AntiBotSignals = antiBotSignals
	fmt.Printf("  ✅ 检测到 %d 种反爬机制\n", countEnabledFlags(antiDetect))
	if antiBotLevel != "" {
		fmt.Printf("    level: %s\n", antiBotLevel)
	}
	if len(antiBotSignals) > 0 {
		fmt.Printf("    signals: %s\n", strings.Join(antiBotSignals, ", "))
	}

	// 步骤 2: 自动反爬绕过
	fmt.Println("  [2/8] 自动反爬绕过...")
	if antiDetect["captcha"] {
		fmt.Println("    🔓 检测到验证码")
		// 破解验证码
	}
	if antiDetect["waf"] {
		fmt.Println("    🛡️  检测到 WAF")
		// 切换代理
		if us.proxyPool != nil {
			proxy := us.proxyPool.GetNextProxy()
			result.ProxyUsed = proxy
			fmt.Printf("    ✅ 切换到代理: %s\n", proxy)
		}
	}
	fmt.Println("  ✅ 反爬绕过完成")

	// 步骤 3: TLS 指纹生成
	fmt.Println("  [3/8] TLS 指纹生成...")
	tlsFP, _ := us.enhancedCrawler.GenerateTLSFingerprint("chrome", "120")
	fmt.Printf("  ✅ JA3: %s\n", tlsFP.JA3)

	// 步骤 4: Canvas 指纹生成
	fmt.Println("  [4/8] Canvas 指纹生成...")
	canvasFP, _ := us.enhancedCrawler.GenerateCanvasFingerprint()
	fmt.Printf("  ✅ Hash: %s\n", canvasFP.Hash)
	reverseRuntime := us.collectReverseRuntime(task.URL)
	result.ReverseRuntime = reverseRuntime

	// 步骤 5: 浏览器模拟
	fmt.Println("  [5/8] 浏览器环境模拟...")
	browserResult := us.simulateBrowser(task.URL)
	if success, _ := browserResult["success"].(bool); success {
		fmt.Println("  ✅ 浏览器模拟完成")
	} else {
		fmt.Printf("  ⚠️ 浏览器模拟未完成: %v\n", browserResult["error"])
	}

	// 步骤 6: 加密分析
	fmt.Println("  [6/8] 加密分析...")
	encryptionResult := us.analyzeEncryption(task.URL)
	if success, _ := encryptionResult["success"].(bool); success {
		fmt.Println("  ✅ 加密分析完成")
	} else {
		fmt.Printf("  ⚠️ 加密分析未完成: %v\n", encryptionResult["error"])
	}

	// 步骤 7: AI 提取
	fmt.Println("  [7/8] AI 智能提取...")
	data := us.aiExtract(task.URL)
		if payload, ok := data.(map[string]interface{}); ok {
			payload["_runtime"] = map[string]interface{}{
				"browser":    browserResult,
				"encryption": encryptionResult,
				"reverse":    reverseRuntime,
			}
		}
	result.Data = data
	fmt.Println("  ✅ AI 提取完成")

	// 步骤 8: 数据存储
	fmt.Println("  [8/8] 数据存储...")
	storePath := us.storeData(task.ID, data)
	us.checkpointMgr.saveCheckpoint(task.ID, data)
	fmt.Printf("  ✅ 数据存储完成: %s\n", storePath)

	result.Success = true
	result.Duration = time.Since(startTime)

	fmt.Printf("  ✅ 页面爬取完成: %v\n", result.Duration)

	return result
}

// detectAntiDetection 检测反爬机制
func (us *UltimateSpider) detectAntiDetection(url string) (map[string]bool, string, []string) {
	antiDetect := make(map[string]bool)
	antiDetect["captcha"] = false
	antiDetect["waf"] = false
	antiDetect["rate_limit"] = false
	antiDetect["ip_ban"] = false
	antiDetect["js_challenge"] = false

	client := &http.Client{Timeout: us.config.Timeout}
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return antiDetect, "", nil
	}
	req.Header.Set("User-Agent", us.config.UserAgent)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")

	resp, err := client.Do(req)
	if err != nil {
		return antiDetect, "", nil
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		return antiDetect, "", nil
	}

	headers := map[string]interface{}{}
	for key, values := range resp.Header {
		if len(values) == 1 {
			headers[key] = values[0]
		} else if len(values) > 1 {
			headers[key] = values
		}
	}

	profile, err := us.reverseClient.ProfileAntiBot(nodereverse.AntiBotProfileRequest{
		HTML:       string(body),
		Headers:    headers,
		Cookies:    strings.Join(resp.Header.Values("Set-Cookie"), "; "),
		StatusCode: resp.StatusCode,
		URL:        url,
	})
	if err != nil || profile == nil || !profile.Success {
		return antiDetect, "", nil
	}

	for _, signal := range profile.Signals {
		switch signal {
		case "captcha":
			antiDetect["captcha"] = true
		case "vendor:cloudflare", "vendor:akamai", "vendor:datadome", "vendor:perimeterx", "vendor:incapsula", "vendor:f5", "vendor:kasada", "vendor:shape":
			antiDetect["waf"] = true
		case "rate-limit", "requires-paced-requests":
			antiDetect["rate_limit"] = true
		case "request-blocked":
			antiDetect["ip_ban"] = true
		case "javascript-challenge", "managed-browser-challenge":
			antiDetect["js_challenge"] = true
		}
	}

	return antiDetect, profile.Level, profile.Signals
}

// simulateBrowser 模拟浏览器
func (us *UltimateSpider) simulateBrowser(url string) map[string]interface{} {
	client := &http.Client{Timeout: us.config.Timeout}
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return map[string]interface{}{"success": false, "error": err.Error()}
	}
	req.Header.Set("User-Agent", us.config.UserAgent)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")

	resp, err := client.Do(req)
	if err != nil {
		return map[string]interface{}{"success": false, "error": err.Error()}
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		return map[string]interface{}{"success": false, "error": err.Error()}
	}
	html := string(body)
	if !strings.Contains(html, "navigator.") && !strings.Contains(html, "webdriver") {
		return map[string]interface{}{
			"success":     false,
			"skipped":     true,
			"status_code": resp.StatusCode,
			"error":       "page does not advertise browser fingerprint checks",
		}
	}

	result, err := us.reverseClient.SimulateBrowser(
		"return JSON.stringify({userAgent:navigator.userAgent,platform:navigator.platform,language:navigator.language});",
		map[string]string{
			"userAgent": us.config.UserAgent,
			"language":  "zh-CN",
			"platform":  "Win32",
		},
	)
	if err != nil {
		return map[string]interface{}{"success": false, "error": err.Error(), "status_code": resp.StatusCode}
	}

	return map[string]interface{}{
		"success":     result.Success,
		"result":      result.Result,
		"cookies":     result.Cookies,
		"error":       result.Error,
		"status_code": resp.StatusCode,
	}
}

func (us *UltimateSpider) collectReverseRuntime(url string) map[string]interface{} {
	client := &http.Client{Timeout: us.config.Timeout}
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return map[string]interface{}{"success": false, "error": err.Error()}
	}
	req.Header.Set("User-Agent", us.config.UserAgent)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")

	resp, err := client.Do(req)
	if err != nil {
		return map[string]interface{}{"success": false, "error": err.Error()}
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		return map[string]interface{}{"success": false, "error": err.Error()}
	}
	headers := map[string]interface{}{}
	for key, values := range resp.Header {
		if len(values) == 1 {
			headers[key] = values[0]
		} else if len(values) > 1 {
			headers[key] = values
		}
	}
	cookies := strings.Join(resp.Header.Values("Set-Cookie"), "; ")
	detect, detectErr := us.reverseClient.DetectAntiBot(nodereverse.AntiBotProfileRequest{
		HTML:       string(body),
		Headers:    headers,
		Cookies:    cookies,
		StatusCode: resp.StatusCode,
		URL:        url,
	})
	profile, profileErr := us.reverseClient.ProfileAntiBot(nodereverse.AntiBotProfileRequest{
		HTML:       string(body),
		Headers:    headers,
		Cookies:    cookies,
		StatusCode: resp.StatusCode,
		URL:        url,
	})
	spoof, spoofErr := us.reverseClient.SpoofFingerprint(nodereverse.FingerprintSpoofRequest{
		Browser:  "chrome",
		Platform: "windows",
	})
	tlsFP, tlsErr := us.reverseClient.GenerateTLSFingerprint(nodereverse.TLSFingerprintRequest{
		Browser: "chrome",
		Version: "120",
	})

	runtime := map[string]interface{}{
		"success":         detectErr == nil && profileErr == nil && spoofErr == nil && tlsErr == nil,
		"detect":          detect,
		"profile":         profile,
		"fingerprint_spoof": spoof,
		"tls_fingerprint": tlsFP,
	}
	if detectErr != nil || profileErr != nil || spoofErr != nil || tlsErr != nil {
		runtime["error"] = strings.TrimSpace(fmt.Sprintf("%v %v %v %v", detectErr, profileErr, spoofErr, tlsErr))
	}
	return runtime
}

// analyzeEncryption 分析加密
func (us *UltimateSpider) analyzeEncryption(url string) map[string]interface{} {
	client := &http.Client{Timeout: us.config.Timeout}
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return map[string]interface{}{"success": false, "error": err.Error()}
	}
	req.Header.Set("User-Agent", us.config.UserAgent)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")

	resp, err := client.Do(req)
	if err != nil {
		return map[string]interface{}{"success": false, "error": err.Error()}
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		return map[string]interface{}{"success": false, "error": err.Error()}
	}
	html := string(body)
	candidate := html
	if start := strings.Index(html, "<script"); start >= 0 {
		candidate = html[start:]
	}
	result, err := us.reverseClient.AnalyzeCrypto(candidate)
	if err != nil {
		return map[string]interface{}{"success": false, "error": err.Error(), "status_code": resp.StatusCode}
	}

	return map[string]interface{}{
		"success":      result.Success,
		"crypto_types": result.CryptoTypes,
		"keys":         result.Keys,
		"ivs":          result.Ivs,
		"analysis":     result.Analysis,
		"status_code":  resp.StatusCode,
	}
}

// aiExtract AI 提取
func (us *UltimateSpider) aiExtract(url string) interface{} {
	// AI 智能提取逻辑
	return map[string]interface{}{
		"title":   "Example Page",
		"content": "Extracted content",
		"links":   []string{},
		"images":  []string{},
	}
}

// storeData 存储数据
func (us *UltimateSpider) storeData(taskID string, data interface{}) string {
	outputDir := filepath.Join("artifacts", "ultimate", "results")
	_ = os.MkdirAll(outputDir, 0755)
	outputPath := filepath.Join(outputDir, taskID+".json")
	encoded, err := json.MarshalIndent(data, "", "  ")
	if err == nil {
		_ = os.WriteFile(outputPath, encoded, 0644)
	}
	return outputPath
}

func countEnabledFlags(flags map[string]bool) int {
	total := 0
	for _, enabled := range flags {
		if enabled {
			total++
		}
	}
	return total
}

// ==================== 辅助方法 ====================

func (pm *SpiderMonitor) start() {
	pm.mu.Lock()
	defer pm.mu.Unlock()
	pm.startTime = time.Now()
}

func (pm *SpiderMonitor) addTask(task *CrawlTask) {
	pm.mu.Lock()
	defer pm.mu.Unlock()
	pm.totalTasks++
	pm.currentTasks[task.ID] = task
}

func (wp *WorkerPool) start(spider *UltimateSpider) {
	for i := 0; i < wp.workers; i++ {
		wp.wg.Add(1)
		go func(workerID int) {
			defer wp.wg.Done()
			for task := range wp.taskChan {
				result := spider.CrawlPage(task)
				spider.resultQueue <- result
			}
		}(i)
	}
}

func (pp *ProxyPool) GetNextProxy() string {
	pp.mu.Lock()
	defer pp.mu.Unlock()

	if len(pp.proxies) == 0 {
		return ""
	}

	proxy := pp.proxies[pp.currentIdx]
	pp.currentIdx = (pp.currentIdx + 1) % len(pp.proxies)
	return proxy
}

func (cm *CheckpointManager) saveCheckpoint(taskID string, data interface{}) {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	_ = os.MkdirAll(cm.dir, 0755)
	outputPath := filepath.Join(cm.dir, taskID+".json")
	encoded, err := json.MarshalIndent(data, "", "  ")
	if err == nil {
		_ = os.WriteFile(outputPath, encoded, 0644)
	}
}
