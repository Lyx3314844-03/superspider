package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/chromedp/chromedp"
	"github.com/chromedp/cdproto/network"
)

// VideoMonitor 视频监控器
type VideoMonitor struct {
	mu            sync.Mutex
	requests      map[string]*RequestRecord
	videoRequests []*RequestRecord
	hlsRequests   []*RequestRecord
	visited       map[string]bool
}

// RequestRecord 请求记录
type RequestRecord struct {
	URL      string
	Method   string
	Status   int64
	Type     string
	Headers  map[string]interface{}
	PostData string
}

func NewVideoMonitor() *VideoMonitor {
	return &VideoMonitor{
		requests:      make(map[string]*RequestRecord),
		videoRequests: make([]*RequestRecord, 0),
		hlsRequests:   make([]*RequestRecord, 0),
		visited:       make(map[string]bool),
	}
}

func (vm *VideoMonitor) SetupListener(ctx context.Context) {
	chromedp.ListenTarget(ctx, func(ev interface{}) {
		vm.mu.Lock()
		defer vm.mu.Unlock()

		switch ev := ev.(type) {
		case *network.EventRequestWillBeSent:
			req := &RequestRecord{
				URL:     ev.Request.URL,
				Method:  ev.Request.Method,
				Headers: ev.Request.Headers,
			}
			if ev.Request.PostData != "" {
				req.PostData = ev.Request.PostData
			}
			vm.requests[string(ev.RequestID)] = req

		case *network.EventResponseReceived:
			if req, ok := vm.requests[string(ev.RequestID)]; ok {
				req.Status = ev.Response.Status
				req.Type = string(ev.Type)
				vm.classifyRequest(req)
			}
		}
	})
}

func (vm *VideoMonitor) classifyRequest(req *RequestRecord) {
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

	// 视频文件
	videoExts := []string{".mp4", ".webm", ".flv", ".ts", ".f4v"}
	for _, ext := range videoExts {
		if strings.Contains(urlLower, ext) {
			vm.videoRequests = append(vm.videoRequests, req)
			fmt.Printf("[VIDEO] %s\n", req.URL)
			return
		}
	}

	// 腾讯视频 API
	if strings.Contains(urlLower, "vv.video.qq.com") || 
	   strings.Contains(urlLower, "v.qq.com") ||
	   strings.Contains(urlLower, "gtimg.cn") ||
	   strings.Contains(urlLower, "myqcloud.com") {
		if req.Type == "Fetch" || req.Type == "XHR" || req.Type == "Script" {
			vm.videoRequests = append(vm.videoRequests, req)
			fmt.Printf("[TENCENT API] %s\n", req.URL)
		}
	}
}

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

	return urls
}

func (vm *VideoMonitor) ExportURLs(filename string) error {
	urls := vm.GetVideoURLs()

	content := "# 腾讯视频链接\n"
	content += fmt.Sprintf("# 提取时间：%s\n\n", time.Now().Format("2006-01-02 15:04:05"))

	for _, url := range urls {
		content += url + "\n"
	}

	return os.WriteFile(filename, []byte(content), 0644)
}

func main() {
	url := "https://v.qq.com/x/cover/mzc00200rgazpwa/c4102t9ai7s.html"

	fmt.Println("=== 腾讯视频下载器 ===")
	fmt.Printf("URL: %s\n\n", url)

	// 创建输出目录
	outputDir := "./downloads/tencent"
	os.MkdirAll(outputDir, 0755)

	// 创建监控器
	monitor := NewVideoMonitor()

	// 设置浏览器选项
	opts := append(chromedp.DefaultExecAllocatorOptions[:],
		chromedp.Flag("headless", false), // 有头模式，方便观察
		chromedp.WindowSize(1920, 1080),
		chromedp.UserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
	)

	allocCtx, cancel := chromedp.NewExecAllocator(context.Background(), opts...)
	defer cancel()

	ctx, cancel := chromedp.NewContext(allocCtx)
	defer cancel()

	ctx, cancel = context.WithTimeout(ctx, 120*time.Second)
	defer cancel()

	// 设置监听
	monitor.SetupListener(ctx)

	var title string

	fmt.Println("正在访问腾讯视频页面...")
	fmt.Println("请在浏览器中点击播放视频...")
	fmt.Println()

	err := chromedp.Run(ctx,
		chromedp.Navigate(url),
		chromedp.Sleep(5*time.Second),
		chromedp.Title(&title),
	)

	if err != nil {
		fmt.Printf("访问页面失败：%v\n", err)
	}

	fmt.Printf("\n视频标题：%s\n\n", title)

	// 等待更长时间以捕获更多请求
	fmt.Println("等待视频加载和请求捕获...")
	time.Sleep(30 * time.Second)

	// 显示结果
	urls := monitor.GetVideoURLs()
	
	fmt.Printf("\n═══════════════════════════════════════════\n")
	fmt.Printf("捕获到 %d 个视频链接\n", len(urls))
	fmt.Printf("═══════════════════════════════════════════\n\n")

	// 导出 URL
	urlsFile := filepath.Join(outputDir, "tencent_video_urls.txt")
	monitor.ExportURLs(urlsFile)
	fmt.Printf("视频链接已导出到：%s\n\n", urlsFile)

	// 显示 HLS 链接
	fmt.Println("HLS 链接:")
	for _, req := range monitor.hlsRequests {
		fmt.Printf("  - %s\n", req.URL)
	}

	fmt.Println("\n视频文件链接:")
	for _, req := range monitor.videoRequests {
		fmt.Printf("  - %s\n", req.URL)
	}

	fmt.Println("\n=== 完成 ===")
	fmt.Println("提示：如果找到 m3u8 链接，可以使用 ffmpeg 下载")
	fmt.Println("  ffmpeg -i \"m3u8_url\" -c copy output.mp4")
}
