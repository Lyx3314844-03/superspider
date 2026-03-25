package web

import (
	"encoding/json"
	"log"
	"net/http"
	"fmt"
	"sync"
	"time"

	"gospider/core"
)

// Stats 统计信息
type Stats struct {
	Name            string  `json:"name"`
	StartTime       string  `json:"start_time"`
	PagesScraped    int64   `json:"pages_scraped"`
	PagesFailed     int64   `json:"pages_failed"`
	ItemsScraped    int64   `json:"items_scraped"`
	BytesDownloaded int64   `json:"bytes_downloaded"`
	Duration        string  `json:"duration"`
	PagesPerSecond  float64 `json:"pages_per_second"`
}

// WebConsole Web 控制台
type WebConsole struct {
	port      int
	stats     *Stats
	startTime time.Time
	mu        sync.RWMutex
	server    *http.Server
	jobService *core.JobService
}

// NewWebConsole 创建 Web 控制台
func NewWebConsole(port int) *WebConsole {
	return &WebConsole{
		port: port,
		stats: &Stats{
			Name:      "gospider",
			StartTime: time.Now().Format("2006-01-02 15:04:05"),
		},
		startTime: time.Now(),
	}
}

// SetJobService attaches the shared job service to the web console.
func (wc *WebConsole) SetJobService(jobService *core.JobService) {
	wc.mu.Lock()
	defer wc.mu.Unlock()
	wc.jobService = jobService
}

// RenderState returns the normalized state payload used by the web surface.
func (wc *WebConsole) RenderState() map[string]interface{} {
	wc.mu.RLock()
	defer wc.mu.RUnlock()

	jobs := make([]core.JobSummary, 0)
	if wc.jobService != nil {
		jobs = wc.jobService.List()
	}

	return map[string]interface{}{
		"stats": wc.stats,
		"jobs":  jobs,
	}
}

// UpdateStats 更新统计
func (wc *WebConsole) UpdateStats(pagesScraped, pagesFailed, itemsScraped, bytesDownloaded int64) {
	wc.mu.Lock()
	defer wc.mu.Unlock()
	
	wc.stats.PagesScraped = pagesScraped
	wc.stats.PagesFailed = pagesFailed
	wc.stats.ItemsScraped = itemsScraped
	wc.stats.BytesDownloaded = bytesDownloaded
	
	duration := time.Since(wc.startTime)
	wc.stats.Duration = duration.String()
	
	if duration.Seconds() > 0 {
		wc.stats.PagesPerSecond = float64(pagesScraped) / duration.Seconds()
	}
}

// RecordPage 记录页面
func (wc *WebConsole) RecordPage(bytesDownloaded int64) {
	wc.mu.Lock()
	defer wc.mu.Unlock()
	
	wc.stats.PagesScraped++
	wc.stats.BytesDownloaded += bytesDownloaded
	
	duration := time.Since(wc.startTime)
	wc.stats.Duration = duration.String()
	
	if duration.Seconds() > 0 {
		wc.stats.PagesPerSecond = float64(wc.stats.PagesScraped) / duration.Seconds()
	}
}

// RecordItem 记录物品
func (wc *WebConsole) RecordItem() {
	wc.mu.Lock()
	defer wc.mu.Unlock()
	wc.stats.ItemsScraped++
}

// RecordError 记录错误
func (wc *WebConsole) RecordError() {
	wc.mu.Lock()
	defer wc.mu.Unlock()
	wc.stats.PagesFailed++
}

// Start 启动 Web 控制台
func (wc *WebConsole) Start() {
	mux := http.NewServeMux()
	
	// API 路由
	mux.HandleFunc("/api/stats", wc.handleStats)
	mux.HandleFunc("/api/spiders", wc.handleSpiders)
	mux.HandleFunc("/", wc.handleIndex)
	
	wc.server = &http.Server{
		Addr:    fmt.Sprintf(":%d", wc.port),
		Handler: mux,
	}
	
	log.Printf("Web Console started at http://localhost:%d", wc.port)
	
	if err := wc.server.ListenAndServe(); err != nil {
		log.Printf("Web Console error: %v", err)
	}
}

// Stop 停止 Web 控制台
func (wc *WebConsole) Stop() {
	if wc.server != nil {
		wc.server.Close()
	}
}

// handleStats 处理统计 API
func (wc *WebConsole) handleStats(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(wc.RenderState()["stats"])
}

// handleSpiders 处理爬虫 API
func (wc *WebConsole) handleSpiders(w http.ResponseWriter, r *http.Request) {
	wc.mu.RLock()
	jobs := make([]core.JobSummary, 0)
	if wc.jobService != nil {
		jobs = wc.jobService.List()
	}
	stats := wc.stats
	wc.mu.RUnlock()

	spiders := []map[string]interface{}{
		{
			"name":   "gospider",
			"status": "running",
			"stats":  stats,
			"jobs":   jobs,
		},
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(spiders)
}

// handleIndex 处理首页
func (wc *WebConsole) handleIndex(w http.ResponseWriter, r *http.Request) {
	html := `
<!DOCTYPE html>
<html>
<head>
    <title>GoSpider Web Console</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
        .card { background: #16213e; padding: 20px; border-radius: 10px; margin: 10px 0; }
        .stat { font-size: 24px; color: #00d9ff; }
        h1 { color: #00d9ff; }
    </style>
</head>
<body>
    <h1>🕷️ GoSpider Web Console</h1>
    <div class="card">
        <h2>爬虫统计</h2>
        <p>启动时间：<span id="start_time">-</span></p>
        <p>运行时长：<span id="duration">-</span></p>
        <p>爬取页面：<span id="pages_scraped" class="stat">-</span></p>
        <p>失败页面：<span id="pages_failed" class="stat">-</span></p>
        <p>提取物品：<span id="items_scraped" class="stat">-</span></p>
        <p>下载字节：<span id="bytes_downloaded" class="stat">-</span> KB</p>
        <p>页面/秒：<span id="pages_per_second" class="stat">-</span></p>
    </div>
    <script>
        fetch('/api/stats')
            .then(r => r.json())
            .then(data => {
                document.getElementById('start_time').textContent = data.start_time;
                document.getElementById('duration').textContent = data.duration;
                document.getElementById('pages_scraped').textContent = data.pages_scraped;
                document.getElementById('pages_failed').textContent = data.pages_failed;
                document.getElementById('items_scraped').textContent = data.items_scraped;
                document.getElementById('bytes_downloaded').textContent = Math.round(data.bytes_downloaded / 1024);
                document.getElementById('pages_per_second').textContent = data.pages_per_second.toFixed(2);
            });
    </script>
</body>
</html>
`
	w.Header().Set("Content-Type", "text/html")
	w.Write([]byte(html))
}
