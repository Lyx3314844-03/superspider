package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/chromedp/cdproto/network"
	"github.com/chromedp/chromedp"
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
	URL        string
	Method     string
	Status     int64
	Type       string
	Headers    map[string]interface{}
	PostData   string
	Timestamp  time.Time
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

	// 跳过静态资源
	if strings.Contains(urlLower, ".css") || 
	   strings.Contains(urlLower, ".js") ||
	   strings.Contains(urlLower, ".jpg") ||
	   strings.Contains(urlLower, ".png") {
		return
	}

	// HLS (.m3u8)
	if strings.Contains(urlLower, ".m3u8") || strings.Contains(urlLower, "m3u8") {
		vm.hlsRequests = append(vm.hlsRequests, req)
		fmt.Printf("[HLS] %s\n", req.URL)
		return
	}

	// 视频文件 (.mp4, .ts)
	if strings.Contains(urlLower, ".mp4") || strings.Contains(urlLower, ".ts") {
		vm.videoRequests = append(vm.videoRequests, req)
		fmt.Printf("[VIDEO] %s (状态：%d)\n", req.URL, req.Status)
		return
	}

	// 腾讯视频 API
	if strings.Contains(urlLower, "vv.video.qq.com") || 
	   strings.Contains(urlLower, "gtimg.cn") ||
	   strings.Contains(urlLower, "myqcloud.com") ||
	   strings.Contains(urlLower, "liveplay.myqcloud.com") {
		vm.videoRequests = append(vm.videoRequests, req)
		fmt.Printf("[TENCENT API] %s\n", req.URL)
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
	content += fmt.Sprintf("# 提取时间：%s\n", time.Now().Format("2006-01-02 15:04:05"))
	content += fmt.Sprintf("# 总数：%d\n\n", len(urls))

	for i, url := range urls {
		content += fmt.Sprintf("%d. %s\n", i+1, url)
	}

	return os.WriteFile(filename, []byte(content), 0644)
}

func main() {
	url := "https://v.qq.com/x/cover/mzc00200rgazpwa/c4102t9ai7s.html"

	fmt.Println("╔══════════════════════════════════════════════════════════╗")
	fmt.Println("║         gospider 腾讯视频下载器 - 浏览器监控版            ║")
	fmt.Println("╚══════════════════════════════════════════════════════════╝")
	fmt.Println()

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
		chromedp.Flag("disable-blink-features", "AutomationControlled"),
	)

	allocCtx, cancel := chromedp.NewExecAllocator(context.Background(), opts...)
	defer cancel()

	ctx, cancel := chromedp.NewContext(allocCtx)
	defer cancel()

	ctx, cancel = context.WithTimeout(ctx, 180*time.Second)
	defer cancel()

	// 设置监听
	monitor.SetupListener(ctx)

	var title string

	fmt.Println("📺 正在访问腾讯视频页面...")
	fmt.Println()
	fmt.Println("⚠️  请在浏览器中:")
	fmt.Println("  1. 点击播放视频")
	fmt.Println("  2. 等待视频开始播放（约 5-10 秒）")
	fmt.Println("  3. 程序会自动捕获视频链接")
	fmt.Println()

	err := chromedp.Run(ctx,
		chromedp.Navigate(url),
		chromedp.Sleep(3*time.Second),
		chromedp.Title(&title),
	)

	if err != nil {
		fmt.Printf("❌ 访问页面失败：%v\n", err)
		os.Exit(1)
	}

	fmt.Printf("\n✅ 页面加载完成：%s\n", title)
	fmt.Println()
	fmt.Println("⏳ 等待视频播放并捕获网络请求...")
	fmt.Println("   （如果视频没有自动播放，请手动点击播放按钮）")
	fmt.Println()

	// 等待更长时间以捕获更多请求
	time.Sleep(60 * time.Second)

	// 显示结果
	urls := monitor.GetVideoURLs()
	
	fmt.Println()
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Printf("捕获到 %d 个视频相关链接\n", len(urls))
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Println()

	// 导出 URL
	urlsFile := filepath.Join(outputDir, "tencent_video_urls.txt")
	monitor.ExportURLs(urlsFile)
	fmt.Printf("📁 视频链接已导出到：%s\n\n", urlsFile)

	// 分类显示
	if len(monitor.hlsRequests) > 0 {
		fmt.Println("📡 HLS 流媒体链接:")
		for i, req := range monitor.hlsRequests {
			fmt.Printf("  %d. %s\n", i+1, req.URL)
		}
		fmt.Println()
	}

	if len(monitor.videoRequests) > 0 {
		fmt.Println("🎬 视频文件链接:")
		for i, req := range monitor.videoRequests {
			fmt.Printf("  %d. %s\n", i+1, req.URL)
		}
		fmt.Println()
	}

	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Println()
	fmt.Println("💡 下载提示:")
	fmt.Println()
	fmt.Println("  使用 ffmpeg 下载 HLS 流:")
	fmt.Println("    ffmpeg -i \"m3u8_url\" -c copy output.mp4")
	fmt.Println()
	fmt.Println("  使用 gospider HLS 下载器:")
	fmt.Println("    go run examples/video_downloader.go -url \"m3u8_url\"")
	fmt.Println()

	fmt.Println("✅ 完成！")
}
