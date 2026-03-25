package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/chromedp/cdproto/network"
	"github.com/chromedp/chromedp"
)

// 网络请求记录
type RequestRecord struct {
	URL        string                 `json:"url"`
	Method     string                 `json:"method"`
	Status     int64                  `json:"status"`
	Type       string                 `json:"type"`
	Headers    map[string]interface{} `json:"headers"`
	PostData   string                 `json:"postData,omitempty"`
	ResponseID string                 `json:"responseId"`
	Timestamp  time.Time              `json:"timestamp"`
}

func main() {
	url := "https://www.youku.tv/v/v_show/id_XNTk4Mjg1MjEzMg==.html?spm=a2hja.14919748_WEBMOVIE_JINGXUAN.drawer2.d_zj1_1&s=cfeb97262f9f4d29b86b&scm=20140719.manual.37330.show_cfeb97262f9f4d29b86b&s=cfeb97262f9f4d29b86b"

	fmt.Println("=== 优酷视频下载器 - 网络监控版 ===")

	// 输出目录
	outputDir := filepath.Join("C:\\Users\\Administrator\\spider\\gospider\\downloads", "youku_network")
	os.MkdirAll(outputDir, 0755)

	// 存储网络请求
	var mu sync.Mutex
	requests := make(map[string]*RequestRecord)
	videoRequests := []*RequestRecord{}

	// 创建 chromedp 上下文
	opts := append(chromedp.DefaultExecAllocatorOptions[:],
		chromedp.Flag("headless", false),
		chromedp.WindowSize(1920, 1080),
		chromedp.UserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
	)

	allocCtx, cancel := chromedp.NewExecAllocator(context.Background(), opts...)
	defer cancel()

	ctx, cancel := chromedp.NewContext(allocCtx)
	defer cancel()

	ctx, cancel = context.WithTimeout(ctx, 120*time.Second)
	defer cancel()

	// 设置网络事件监听
	chromedp.ListenTarget(ctx, func(ev interface{}) {
		mu.Lock()
		defer mu.Unlock()

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
			requests[string(ev.RequestID)] = req

		case *network.EventResponseReceived:
			if req, ok := requests[string(ev.RequestID)]; ok {
				req.Status = ev.Response.Status
				req.Type = string(ev.Type)
				req.ResponseID = string(ev.RequestID)

				// 检查是否是视频相关的请求
				urlLower := strings.ToLower(req.URL)
				if strings.Contains(urlLower, ".m3u8") ||
					strings.Contains(urlLower, ".mp4") ||
					strings.Contains(urlLower, "youku") ||
					strings.Contains(urlLower, "aliyun") ||
					strings.Contains(urlLower, "video") ||
					strings.Contains(urlLower, "play") {
					videoRequests = append(videoRequests, req)
					fmt.Printf("\n[视频相关请求] %s (状态：%d)\n", req.URL, req.Status)
				}
			}
		}
	})

	fmt.Println("正在访问页面并监控网络请求...")

	var title string
	err := chromedp.Run(ctx,
		chromedp.Navigate(url),
		chromedp.Sleep(10*time.Second),
		chromedp.Title(&title),
	)

	if err != nil {
		fmt.Printf("执行失败：%v\n", err)
	}

	fmt.Printf("\n视频标题：%s\n", title)
	fmt.Printf("\n总共捕获 %d 个视频相关请求\n", len(videoRequests))

	// 保存结果
	resultFile := filepath.Join(outputDir, "video_requests.json")
	resultData := map[string]interface{}{
		"title":           title,
		"url":             url,
		"timestamp":       time.Now().Format("2006-01-02 15:04:05"),
		"videoRequests":   videoRequests,
		"totalRequests":   len(requests),
	}

	jsonData, _ := json.MarshalIndent(resultData, "", "  ")
	os.WriteFile(resultFile, jsonData, 0644)
	fmt.Printf("详细请求信息已保存到：%s\n", resultFile)

	// 提取独特的视频 URL
	seenURLs := make(map[string]bool)
	videoLinksFile := filepath.Join(outputDir, "video_links.txt")
	var linksContent strings.Builder
	linksContent.WriteString(fmt.Sprintf("标题：%s\n", title))
	linksContent.WriteString(fmt.Sprintf("源 URL: %s\n\n", url))
	linksContent.WriteString("找到的视频链接:\n")
	linksContent.WriteString("====================\n\n")

	for _, req := range videoRequests {
		if !seenURLs[req.URL] {
			seenURLs[req.URL] = true
			linksContent.WriteString(fmt.Sprintf("[%s] %s\n", req.Type, req.URL))
			if req.PostData != "" {
				linksContent.WriteString(fmt.Sprintf("POST 数据：%s\n", req.PostData))
			}
			linksContent.WriteString("\n")
		}
	}

	os.WriteFile(videoLinksFile, []byte(linksContent.String()), 0644)
	fmt.Printf("视频链接列表已保存到：%s\n", videoLinksFile)

	fmt.Println("\n=== 完成 ===")
	fmt.Println("提示：如果找到 m3u8 链接，可以使用 ffmpeg 或 N_m3u8DL-RE 等工具下载")
}
