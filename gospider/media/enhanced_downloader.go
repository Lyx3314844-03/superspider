package media

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// EnhancedDownloader 增强下载器
type EnhancedDownloader struct {
	client      *http.Client
	outputDir   string
	userAgent   string
	concurrent  int
	retryTimes  int
	timeout     time.Duration
	progressCb  func(downloaded, total int64, url string)
	mu          sync.Mutex
}

// DownloadTask 下载任务
type DownloadTask struct {
	URL        string
	Filename   string
	OutputPath string
	Priority   int
	Status     string
	Error      string
	Downloaded int64
	Total      int64
	StartTime  time.Time
	EndTime    time.Time
}

// NewEnhancedDownloader 创建增强下载器
func NewEnhancedDownloader(outputDir string) *EnhancedDownloader {
	return &EnhancedDownloader{
		client: &http.Client{
			Timeout: 0, // 下载不超时
		},
		outputDir:  outputDir,
		userAgent:  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
		concurrent: 3,
		retryTimes: 3,
		timeout:    30 * time.Second,
	}
}

// SetProgressCallback 设置进度回调
func (ed *EnhancedDownloader) SetProgressCallback(cb func(downloaded, total int64, url string)) {
	ed.progressCb = cb
}

// SetConcurrent 设置并发数
func (ed *EnhancedDownloader) SetConcurrent(count int) {
	ed.concurrent = count
}

// DownloadWithProgress 带进度下载的单个文件
func (ed *EnhancedDownloader) DownloadWithProgress(url, filename string) (*DownloadResult, error) {
	return ed.DownloadWithProgressCtx(context.Background(), url, filename)
}

// DownloadWithProgressCtx 带进度和上下文的下载
func (ed *EnhancedDownloader) DownloadWithProgressCtx(ctx context.Context, url, filename string) (*DownloadResult, error) {
	var lastError error
	
	for attempt := 0; attempt < ed.retryTimes; attempt++ {
		result, err := ed.downloadOnce(ctx, url, filename)
		if err == nil {
			return result, nil
		}
		lastError = err
		
		// 检查是否取消
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(time.Second * 2):
			// 等待后重试
		}
	}
	
	return nil, fmt.Errorf("下载失败，已重试 %d 次：%v", ed.retryTimes, lastError)
}

// downloadOnce 单次下载
func (ed *EnhancedDownloader) downloadOnce(ctx context.Context, url, filename string) (*DownloadResult, error) {
	result := &DownloadResult{URL: url}

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		result.Error = err.Error()
		result.Success = false
		return result, err
	}

	req.Header.Set("User-Agent", ed.userAgent)

	// 检查是否有部分下载的文件
	outputPath := filepath.Join(ed.outputDir, filename)
	var startByte int64 = 0
	
	if info, err := os.Stat(outputPath); err == nil {
		startByte = info.Size()
		req.Header.Set("Range", fmt.Sprintf("bytes=%d-", startByte))
	}

	resp, err := ed.client.Do(req)
	if err != nil {
		result.Error = err.Error()
		result.Success = false
		return result, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 && resp.StatusCode != 206 {
		result.Error = "HTTP " + resp.Status
		result.Success = false
		return result, fmt.Errorf("HTTP 错误：%s", resp.Status)
	}

	// 创建输出目录
	os.MkdirAll(ed.outputDir, 0755)

	// 创建/打开文件
	var file *os.File
	if startByte > 0 {
		file, err = os.OpenFile(outputPath, os.O_APPEND|os.O_WRONLY, 0644)
	} else {
		file, err = os.Create(outputPath)
	}
	if err != nil {
		result.Error = err.Error()
		result.Success = false
		return result, err
	}
	defer file.Close()

	// 获取文件大小
	total := resp.ContentLength + startByte
	
	// 下载
	buffer := make([]byte, 32*1024)
	downloaded := startByte
	lastReport := time.Now()
	
	for {
		n, err := resp.Body.Read(buffer)
		if n > 0 {
			file.Write(buffer[:n])
			downloaded += int64(n)
			
			// 报告进度 (每 500ms)
			if time.Since(lastReport) > 500*time.Millisecond && ed.progressCb != nil {
				ed.progressCb(downloaded, total, url)
				lastReport = time.Now()
			}
		}
		
		if err != nil {
			if err == io.EOF {
				break
			}
			result.Error = err.Error()
			result.Success = false
			return result, err
		}
	}

	result.Path = outputPath
	result.Size = downloaded - startByte
	result.Success = true
	
	if ed.progressCb != nil {
		ed.progressCb(downloaded, total, url)
	}

	return result, nil
}

// BatchDownload 批量下载
func (ed *EnhancedDownloader) BatchDownload(urls []string, outputDir string) ([]*DownloadResult, error) {
	os.MkdirAll(outputDir, 0755)
	
	tasks := make([]*DownloadTask, len(urls))
	for i, url := range urls {
		filename := filepath.Base(url)
		if filename == "" {
			filename = fmt.Sprintf("file_%d", i)
		}
		tasks[i] = &DownloadTask{
			URL:      url,
			Filename: filename,
			Priority: 5,
			Status:   "pending",
		}
	}
	
	return ed.BatchDownloadTasks(tasks, outputDir)
}

// BatchDownloadTasks 批量下载任务
func (ed *EnhancedDownloader) BatchDownloadTasks(tasks []*DownloadTask, outputDir string) ([]*DownloadResult, error) {
	os.MkdirAll(outputDir, 0755)
	
	results := make([]*DownloadResult, len(tasks))
	errors := make([]error, len(tasks))
	
	// 创建任务通道
	taskChan := make(chan int, len(tasks))
	for i := range tasks {
		taskChan <- i
	}
	close(taskChan)
	
	// 并发下载
	var wg sync.WaitGroup
	sem := make(chan struct{}, ed.concurrent)
	
	for i := range tasks {
		wg.Add(1)
		sem <- struct{}{}
		
		go func(idx int) {
			defer wg.Done()
			defer func() { <-sem }()
			
			task := tasks[idx]
			task.Status = "running"
			task.StartTime = time.Now()
			
			ctx := context.Background()
			result, err := ed.DownloadWithProgressCtx(ctx, task.URL, task.Filename)
			
			task.EndTime = time.Now()
			
			if err != nil {
				task.Status = "failed"
				task.Error = err.Error()
				errors[idx] = err
			} else {
				task.Status = "completed"
				task.Downloaded = result.Size
				task.Total = result.Size
			}
			
			results[idx] = result
		}(i)
	}
	
	wg.Wait()
	
	// 检查错误
	var hasError bool
	for _, err := range errors {
		if err != nil {
			hasError = true
			break
		}
	}
	
	if hasError {
		return results, fmt.Errorf("部分下载失败")
	}
	
	return results, nil
}

// DownloadWithResume 支持断点续传的下载
func (ed *EnhancedDownloader) DownloadWithResume(url, filename string) (*DownloadResult, error) {
	outputPath := filepath.Join(ed.outputDir, filename)
	
	// 检查文件是否已完整下载
	if info, err := os.Stat(outputPath); err == nil {
		// 文件存在，可以尝试续传
		fmt.Printf("发现已有文件：%s (%.2f MB)\n", filename, float64(info.Size())/1024/1024)
	}
	
	return ed.DownloadWithProgress(url, filename)
}

// GetFileSize 获取远程文件大小
func (ed *EnhancedDownloader) GetFileSize(url string) (int64, error) {
	req, err := http.NewRequest("HEAD", url, nil)
	if err != nil {
		return 0, err
	}
	
	req.Header.Set("User-Agent", ed.userAgent)
	
	resp, err := ed.client.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	
	if resp.ContentLength > 0 {
		return resp.ContentLength, nil
	}
	
	return 0, fmt.Errorf("无法获取文件大小")
}

// CancelDownload 取消下载 (通过 context)
func (ed *EnhancedDownloader) CancelDownload(ctx context.Context) {
	// context 已取消，下载会自动停止
}

// EnhancedDownloadStats 下载统计（增强版）
type EnhancedDownloadStats struct {
	TotalFiles    int
	Completed     int
	Failed        int
	TotalBytes    int64
	TotalTime     time.Duration
	AverageSpeed  float64
}

// CalculateStats 计算下载统计
func (ed *EnhancedDownloader) CalculateStats(tasks []*DownloadTask) *EnhancedDownloadStats {
	stats := &EnhancedDownloadStats{
		TotalFiles: len(tasks),
	}
	
	for _, task := range tasks {
		if task.Status == "completed" {
			stats.Completed++
			stats.TotalBytes += task.Downloaded
		} else if task.Status == "failed" {
			stats.Failed++
		}
		
		if !task.EndTime.IsZero() {
			stats.TotalTime += task.EndTime.Sub(task.StartTime)
		}
	}
	
	if stats.TotalTime > 0 {
		stats.AverageSpeed = float64(stats.TotalBytes) / stats.TotalTime.Seconds()
	}
	
	return stats
}

// FormatSpeed 格式化速度显示
func FormatSpeed(bytesPerSecond float64) string {
	if bytesPerSecond < 1024 {
		return fmt.Sprintf("%.0f B/s", bytesPerSecond)
	} else if bytesPerSecond < 1024*1024 {
		return fmt.Sprintf("%.1f KB/s", bytesPerSecond/1024)
	} else {
		return fmt.Sprintf("%.1f MB/s", bytesPerSecond/1024/1024)
	}
}

// FormatSize 格式化大小显示
func FormatSize(bytes int64) string {
	if bytes < 1024 {
		return fmt.Sprintf("%d B", bytes)
	} else if bytes < 1024*1024 {
		return fmt.Sprintf("%.1f KB", float64(bytes)/1024)
	} else if bytes < 1024*1024*1024 {
		return fmt.Sprintf("%.1f MB", float64(bytes)/1024/1024)
	} else {
		return fmt.Sprintf("%.1f GB", float64(bytes)/1024/1024/1024)
	}
}

// SimpleProgressBar 简单进度条
type SimpleProgressBar struct {
	Total     int64
	Current   int64
	Width     int
	StartTime time.Time
}

// NewProgressBar 创建进度条
func NewProgressBar(total int64) *SimpleProgressBar {
	return &SimpleProgressBar{
		Total:     total,
		Width:     50,
		StartTime: time.Now(),
	}
}

// Update 更新进度
func (pb *SimpleProgressBar) Update(current int64) {
	pb.Current = current
	pb.Render()
}

// Render 渲染进度条
func (pb *SimpleProgressBar) Render() {
	if pb.Total <= 0 {
		return
	}
	
	percent := float64(pb.Current) / float64(pb.Total) * 100
	filled := int(percent / 100 * float64(pb.Width))
	
	// 计算速度
	elapsed := time.Since(pb.StartTime).Seconds()
	speed := float64(pb.Current) / elapsed
	
	// 渲染
	bar := strings.Repeat("█", filled) + strings.Repeat("░", pb.Width-filled)
	
	fmt.Printf("\r[%s] %.1f%% %s/%s %s", 
		bar, 
		percent,
		FormatSize(pb.Current),
		FormatSize(pb.Total),
		FormatSpeed(speed),
	)
	
	if pb.Current >= pb.Total {
		fmt.Println()
	}
}
