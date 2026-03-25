package network

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/chromedp/cdproto/network"
	"github.com/chromedp/chromedp"
)

// VideoMonitor 视频链接监控器
type VideoMonitor struct {
	mu            sync.Mutex
	requests      map[string]*RequestRecord
	videoRequests []*RequestRecord
	audioRequests []*RequestRecord
	hlsRequests   []*RequestRecord
	dashRequests  []*RequestRecord
	visited       map[string]bool
}

// RequestRecord 请求记录
type RequestRecord struct {
	URL           string
	Method        string
	Status        int64
	Type          string
	Headers       map[string]interface{}
	PostData      string
	Timestamp     time.Time
	ResponseID    string
	ResponseSize  int64     // 响应大小
	Duration      float64   // 请求耗时（毫秒）
}

// NewVideoMonitor 创建视频监控器
func NewVideoMonitor() *VideoMonitor {
	return &VideoMonitor{
		requests:      make(map[string]*RequestRecord),
		videoRequests: make([]*RequestRecord, 0),
		audioRequests: make([]*RequestRecord, 0),
		hlsRequests:   make([]*RequestRecord, 0),
		dashRequests:  make([]*RequestRecord, 0),
		visited:       make(map[string]bool),
	}
}

// SetupListener 设置网络监听
func (vm *VideoMonitor) SetupListener(ctx context.Context) {
	chromedp.ListenTarget(ctx, func(ev interface{}) {
		vm.mu.Lock()
		defer vm.mu.Unlock()

		switch ev := ev.(type) {
		case *network.EventRequestWillBeSent:
			req := &RequestRecord{
				URL:       ev.Request.URL,
				Method:    ev.Request.Method,
				Headers:   ev.Request.Headers,
				Timestamp: time.Now(),
			}
			if ev.Request.PostData != "" {
				req.PostData = ev.Request.PostData
			}
			vm.requests[string(ev.RequestID)] = req

		case *network.EventResponseReceived:
			if req, ok := vm.requests[string(ev.RequestID)]; ok {
				req.Status = ev.Response.Status
				req.Type = string(ev.Type)
				req.ResponseID = string(ev.RequestID)

				// 分类处理
				vm.classifyRequest(req)
			}
		}
	})
}

// classifyRequest 分类请求
func (vm *VideoMonitor) classifyRequest(req *RequestRecord) {
	// 跳过已处理的
	if vm.visited[req.URL] {
		return
	}
	vm.visited[req.URL] = true

	urlLower := strings.ToLower(req.URL)

	// HLS (.m3u8)
	if strings.Contains(urlLower, ".m3u8") || strings.Contains(urlLower, "m3u8") {
		vm.hlsRequests = append(vm.hlsRequests, req)
		fmt.Printf("[HLS] %s\n", req.URL)
		return
	}

	// DASH (.mpd)
	if strings.Contains(urlLower, ".mpd") || strings.Contains(urlLower, "dash") {
		vm.dashRequests = append(vm.dashRequests, req)
		fmt.Printf("[DASH] %s\n", req.URL)
		return
	}

	// 视频文件
	videoExts := []string{".mp4", ".webm", ".flv", ".avi", ".mov", ".mkv", ".ts", ".f4v"}
	for _, ext := range videoExts {
		if strings.Contains(urlLower, ext) {
			vm.videoRequests = append(vm.videoRequests, req)
			fmt.Printf("[VIDEO] %s\n", req.URL)
			return
		}
	}

	// 音频文件
	audioExts := []string{".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac"}
	for _, ext := range audioExts {
		if strings.Contains(urlLower, ext) {
			vm.audioRequests = append(vm.audioRequests, req)
			fmt.Printf("[AUDIO] %s\n", req.URL)
			return
		}
	}

	// 视频平台 API
	videoAPIs := []string{
		"youku", "iqiyi", "v.qq", "bilibili", "youtube",
		"video", "play", "stream", "media", "ups", "cdn",
	}
	for _, api := range videoAPIs {
		if strings.Contains(urlLower, api) && (req.Type == "Fetch" || req.Type == "XHR") {
			vm.videoRequests = append(vm.videoRequests, req)
			fmt.Printf("[API] %s\n", req.URL)
			return
		}
	}
}

// GetVideoURLs 获取所有视频 URL
func (vm *VideoMonitor) GetVideoURLs() []string {
	vm.mu.Lock()
	defer vm.mu.Unlock()

	urls := make([]string, 0)
	seen := make(map[string]bool)

	for _, req := range vm.videoRequests {
		if !seen[req.URL] {
			seen[req.URL] = true
			urls = append(urls, req.URL)
		}
	}

	for _, req := range vm.hlsRequests {
		if !seen[req.URL] {
			seen[req.URL] = true
			urls = append(urls, req.URL)
		}
	}

	for _, req := range vm.dashRequests {
		if !seen[req.URL] {
			seen[req.URL] = true
			urls = append(urls, req.URL)
		}
	}

	return urls
}

// GetHLSURLs 获取 HLS URL
func (vm *VideoMonitor) GetHLSURLs() []string {
	vm.mu.Lock()
	defer vm.mu.Unlock()

	urls := make([]string, 0)
	for _, req := range vm.hlsRequests {
		urls = append(urls, req.URL)
	}
	return urls
}

// GetAudioURLs 获取音频 URL
func (vm *VideoMonitor) GetAudioURLs() []string {
	vm.mu.Lock()
	defer vm.mu.Unlock()

	urls := make([]string, 0)
	for _, req := range vm.audioRequests {
		urls = append(urls, req.URL)
	}
	return urls
}

// GetStats 获取统计信息
func (vm *VideoMonitor) GetStats() map[string]int {
	vm.mu.Lock()
	defer vm.mu.Unlock()

	return map[string]int{
		"total":   len(vm.requests),
		"video":   len(vm.videoRequests),
		"audio":   len(vm.audioRequests),
		"hls":     len(vm.hlsRequests),
		"dash":    len(vm.dashRequests),
	}
}

// ExtractMediaInfo 提取媒体信息
func (vm *VideoMonitor) ExtractMediaInfo() map[string]interface{} {
	vm.mu.Lock()
	defer vm.mu.Unlock()

	info := make(map[string]interface{})

	// 提取视频信息
	videos := make([]map[string]string, 0)
	for _, req := range vm.videoRequests {
		video := map[string]string{
			"url":    req.URL,
			"type":   req.Type,
			"status": fmt.Sprintf("%d", req.Status),
		}
		videos = append(videos, video)
	}
	info["videos"] = videos

	// 提取 HLS 信息
	hls := make([]map[string]string, 0)
	for _, req := range vm.hlsRequests {
		hlsInfo := map[string]string{
			"url":    req.URL,
			"type":   "m3u8",
			"status": fmt.Sprintf("%d", req.Status),
		}
		hls = append(hls, hlsInfo)
	}
	info["hls"] = hls

	return info
}

// FilterBySize 按文件大小过滤 (需要响应头)
func (vm *VideoMonitor) FilterBySize(minSize, maxSize int64) []*RequestRecord {
	vm.mu.Lock()
	defer vm.mu.Unlock()

	// 这里需要扩展 RequestRecord 来存储响应大小
	// 暂时返回所有视频请求
	return vm.videoRequests
}

// FilterByDomain 按域名过滤
func (vm *VideoMonitor) FilterByDomain(domains []string) []*RequestRecord {
	vm.mu.Lock()
	defer vm.mu.Unlock()

	result := make([]*RequestRecord, 0)
	allRequests := append(vm.videoRequests, vm.hlsRequests...)
	allRequests = append(allRequests, vm.dashRequests...)

	for _, req := range allRequests {
		for _, domain := range domains {
			if strings.Contains(req.URL, domain) {
				result = append(result, req)
				break
			}
		}
	}

	return result
}

// ExportURLs 导出 URL 列表
func (vm *VideoMonitor) ExportURLs(filename string) error {
	urls := vm.GetVideoURLs()

	content := "# Video URLs extracted by gospider\n"
	content += fmt.Sprintf("# Extracted at: %s\n\n", time.Now().Format("2006-01-02 15:04:05"))

	for _, url := range urls {
		content += url + "\n"
	}

	return os.WriteFile(filename, []byte(content), 0644)
}

// ExportURLsJSON 导出 JSON 格式
func (vm *VideoMonitor) ExportURLsJSON(filename string) error {
	urls := vm.GetVideoURLs()
	records := vm.getAllRecords()

	data := map[string]interface{}{
		"extracted_at": time.Now().Format("2006-01-02 15:04:05"),
		"total":        len(urls),
		"urls":         urls,
		"details":      records,
	}

	jsonData, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(filename, jsonData, 0644)
}

// ExportURLsCSV 导出 CSV 格式
func (vm *VideoMonitor) ExportURLsCSV(filename string) error {
	records := vm.getAllRecords()

	content := "URL,Method,Status,Type,Size,Duration\n"
	for _, rec := range records {
		content += fmt.Sprintf("%s,%s,%d,%s,%d,%.0f\n",
			rec.URL, rec.Method, rec.Status, rec.Type, rec.ResponseSize, rec.Duration)
	}

	return os.WriteFile(filename, []byte(content), 0644)
}

// getAllRecords 获取所有记录
func (vm *VideoMonitor) getAllRecords() []*RequestRecord {
	vm.mu.Lock()
	defer vm.mu.Unlock()

	allRequests := append(vm.videoRequests, vm.hlsRequests...)
	allRequests = append(allRequests, vm.dashRequests...)
	allRequests = append(allRequests, vm.audioRequests...)

	return allRequests
}

// FindVideoPattern 查找特定模式的视频链接
func (vm *VideoMonitor) FindVideoPattern(pattern string) []*RequestRecord {
	vm.mu.Lock()
	defer vm.mu.Unlock()

	result := make([]*RequestRecord, 0)
	re := regexp.MustCompile(pattern)

	allRequests := append(vm.videoRequests, vm.hlsRequests...)
	allRequests = append(allRequests, vm.dashRequests...)

	for _, req := range allRequests {
		if re.MatchString(req.URL) {
			result = append(result, req)
		}
	}

	return result
}

// Clear 清空所有记录
func (vm *VideoMonitor) Clear() {
	vm.mu.Lock()
	defer vm.mu.Unlock()

	vm.requests = make(map[string]*RequestRecord)
	vm.videoRequests = make([]*RequestRecord, 0)
	vm.audioRequests = make([]*RequestRecord, 0)
	vm.hlsRequests = make([]*RequestRecord, 0)
	vm.dashRequests = make([]*RequestRecord, 0)
	vm.visited = make(map[string]bool)
}
