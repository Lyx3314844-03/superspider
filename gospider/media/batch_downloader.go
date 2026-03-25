package media

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// BatchDownloader 批量下载器
type BatchDownloader struct {
	client      *http.Client
	outputDir   string
	userAgent   string
	concurrent  int
	maxRetry    int
	timeout     time.Duration
	progressCb  func(url string, downloaded, total int64)
	completeCb  func(url string, success bool)
	ctx         context.Context
	cancel      context.CancelFunc
}

// BatchTask 批量下载任务
type BatchTask struct {
	ID           string              `json:"id"`
	URLs         []string            `json:"urls"`
	Status       string              `json:"status"`
	Total        int                 `json:"total"`
	Completed    int                 `json:"completed"`
	Failed       int                 `json:"failed"`
	Progress     float64             `json:"progress"`
	Downloaded   int64               `json:"downloaded"`
	TotalSize    int64               `json:"total_size"`
	Speed        float64             `json:"speed"`
	ETA          time.Duration       `json:"eta"`
	StartTime    time.Time           `json:"start_time"`
	CompleteTime time.Time           `json:"complete_time"`
	Results      []BatchDownloadResult `json:"results"`
	Error        string              `json:"error"`
}

// BatchDownloadResult 批量下载结果
type BatchDownloadResult struct {
	URL        string `json:"url"`
	Success    bool   `json:"success"`
	OutputFile string `json:"output_file"`
	Error      string `json:"error"`
	Size       int64  `json:"size"`
	Duration   time.Duration `json:"duration"`
}

// BatchOptions 批量下载选项
type BatchOptions struct {
	OutputDir    string
	Concurrent   int
	MaxRetry     int
	Timeout      time.Duration
	Pattern      string // 文件名模式
	Progress     func(url string, downloaded, total int64)
	Complete     func(url string, success bool)
}

// NewBatchDownloader 创建批量下载器
func NewBatchDownloader(outputDir string) *BatchDownloader {
	ctx, cancel := context.WithCancel(context.Background())
	return &BatchDownloader{
		client: &http.Client{
			Timeout: 30 * time.Second,
			Transport: &http.Transport{
				MaxIdleConns:        100,
				MaxIdleConnsPerHost: 10,
				IdleConnTimeout:     90 * time.Second,
			},
		},
		outputDir:  outputDir,
		userAgent:  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
		concurrent: 5,
		maxRetry:   3,
		timeout:    30 * time.Second,
		ctx:        ctx,
		cancel:     cancel,
	}
}

// SetProgressCallback 设置进度回调
func (d *BatchDownloader) SetProgressCallback(cb func(url string, downloaded, total int64)) {
	d.progressCb = cb
}

// SetCompleteCallback 设置完成回调
func (d *BatchDownloader) SetCompleteCallback(cb func(url string, success bool)) {
	d.completeCb = cb
}

// SetConcurrent 设置并发数
func (d *BatchDownloader) SetConcurrent(count int) {
	d.concurrent = count
}

// Close 关闭下载器
func (d *BatchDownloader) Close() {
	d.cancel()
}

// DownloadBatch 批量下载
func (d *BatchDownloader) DownloadBatch(urls []string, opts *BatchOptions) (*BatchTask, error) {
	if opts == nil {
		opts = &BatchOptions{}
	}

	// 初始化任务
	task := &BatchTask{
		ID:        generateBatchID(),
		URLs:      urls,
		Status:    "pending",
		Total:     len(urls),
		StartTime: time.Now(),
		Results:   make([]BatchDownloadResult, 0, len(urls)),
	}

	// 应用选项
	outputDir := d.outputDir
	if opts.OutputDir != "" {
		outputDir = opts.OutputDir
	}
	if opts.Concurrent > 0 {
		d.concurrent = opts.Concurrent
	}
	if opts.Timeout > 0 {
		d.timeout = opts.Timeout
		d.client.Timeout = opts.Timeout
	}
	if opts.Progress != nil {
		d.progressCb = opts.Progress
	}
	if opts.Complete != nil {
		d.completeCb = opts.Complete
	}

	// 创建输出目录
	os.MkdirAll(outputDir, 0755)

	// 开始下载
	task.Status = "downloading"

	// 并发下载
	var mu sync.Mutex
	var wg sync.WaitGroup
	sem := make(chan struct{}, d.concurrent)

	for i, url := range urls {
		// 检查取消
		select {
		case <-d.ctx.Done():
			task.Status = "cancelled"
			task.Error = "用户取消下载"
			return task, nil
		default:
		}

		wg.Add(1)
		sem <- struct{}{}

		go func(idx int, u string) {
			defer wg.Done()
			defer func() { <-sem }()

			result := d.downloadSingle(u, outputDir, opts.Pattern)
			
			mu.Lock()
			task.Results = append(task.Results, result)
			if result.Success {
				task.Completed++
				task.Downloaded += result.Size
			} else {
				task.Failed++
			}
			task.Progress = float64(task.Completed+task.Failed) / float64(task.Total) * 100
			mu.Unlock()

			// 回调
			if d.completeCb != nil {
				d.completeCb(u, result.Success)
			}
		}(i, url)
	}

	wg.Wait()

	// 完成任务
	task.Status = "completed"
	task.CompleteTime = time.Now()

	fmt.Printf("批量下载完成：成功 %d, 失败 %d\n", task.Completed, task.Failed)
	return task, nil
}

// downloadSingle 下载单个文件
func (d *BatchDownloader) downloadSingle(url, outputDir, pattern string) BatchDownloadResult {
	result := BatchDownloadResult{
		URL:     url,
		Success: false,
	}

	startTime := time.Now()

	// 重试下载
	var lastErr error
	for i := 0; i < d.maxRetry; i++ {
		// 检查取消
		select {
		case <-d.ctx.Done():
			result.Error = "用户取消"
			return result
		default:
		}

		outputFile := d.generateFilename(url, outputDir, pattern)
		
		// 检查是否已存在
		if info, err := os.Stat(outputFile); err == nil && info.Size() > 0 {
			result.Success = true
			result.OutputFile = outputFile
			result.Size = info.Size()
			result.Duration = time.Since(startTime)
			fmt.Printf("[已存在] %s\n", outputFile)
			return result
		}

		err := d.downloadFile(url, outputFile)
		if err == nil {
			result.Success = true
			result.OutputFile = outputFile
			if info, _ := os.Stat(outputFile); info != nil {
				result.Size = info.Size()
			}
			result.Duration = time.Since(startTime)
			return result
		}

		lastErr = err
		
		// 重试前等待
		if i < d.maxRetry-1 {
			time.Sleep(time.Duration(i+1) * time.Second)
		}
	}

	result.Error = lastErr.Error()
	return result
}

// downloadFile 下载文件
func (d *BatchDownloader) downloadFile(url, outputFile string) error {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}

	req.Header.Set("User-Agent", d.userAgent)

	resp, err := d.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	file, err := os.Create(outputFile)
	if err != nil {
		return err
	}
	defer file.Close()

	_, err = io.Copy(file, resp.Body)
	return err
}

// generateFilename 生成文件名
func (d *BatchDownloader) generateFilename(url, outputDir, pattern string) string {
	if pattern != "" {
		// 使用自定义模式
		return filepath.Join(outputDir, pattern)
	}

	// 从 URL 生成文件名
	idx := strings.LastIndex(url, "/")
	if idx == -1 {
		return filepath.Join(outputDir, "download")
	}

	filename := url[idx+1:]
	if filename == "" || filename == "?" {
		filename = fmt.Sprintf("download_%d", time.Now().Unix())
	}

	// 清理文件名
	filename = strings.Map(func(r rune) rune {
		if r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9' || r == '.' || r == '-' || r == '_' {
			return r
		}
		return '_'
	}, filename)

	return filepath.Join(outputDir, filename)
}

// DownloadFromList 从文件列表批量下载
func (d *BatchDownloader) DownloadFromList(listFile string, opts *BatchOptions) (*BatchTask, error) {
	// 读取文件列表
	file, err := os.Open(listFile)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var urls []string
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		// 跳过空行和注释
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		urls = append(urls, line)
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}

	if len(urls) == 0 {
		return nil, fmt.Errorf("文件列表为空")
	}

	fmt.Printf("从文件列表读取到 %d 个 URL\n", len(urls))
	return d.DownloadBatch(urls, opts)
}

// SaveTaskInfo 保存任务信息
func (task *BatchTask) SaveTaskInfo(outputFile string) error {
	infoFile := strings.TrimSuffix(outputFile, filepath.Ext(outputFile)) + "_batch.json"
	data, err := json.MarshalIndent(task, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(infoFile, data, 0644)
}

func generateBatchID() string {
	return fmt.Sprintf("batch_%d", time.Now().Unix())
}

// ResumeDownloader 断点续传下载器
type ResumeDownloader struct {
	client     *http.Client
	outputDir  string
	userAgent  string
	stateFile  string
	progressCb func(downloaded, total int64)
}

// DownloadState 下载状态
type DownloadState struct {
	URL         string    `json:"url"`
	OutputFile  string    `json:"output_file"`
	Downloaded  int64     `json:"downloaded"`
	Total       int64     `json:"total"`
	ETag        string    `json:"etag"`
	LastModified string   `json:"last_modified"`
	StartTime   time.Time `json:"start_time"`
	UpdateTime  time.Time `json:"update_time"`
}

// NewResumeDownloader 创建断点续传下载器
func NewResumeDownloader(outputDir string) *ResumeDownloader {
	return &ResumeDownloader{
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
		outputDir: outputDir,
		userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	}
}

// SetProgressCallback 设置进度回调
func (d *ResumeDownloader) SetProgressCallback(cb func(downloaded, total int64)) {
	d.progressCb = cb
}

// DownloadWithResume 断点续传下载
func (d *ResumeDownloader) DownloadWithResume(url string, outputFile string) error {
	// 状态文件
	d.stateFile = outputFile + ".state"

	// 尝试加载状态
	var state *DownloadState
	if info, err := os.Stat(d.stateFile); err == nil && info.Size() > 0 {
		state, _ = d.loadState()
	}

	// 创建请求
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}

	req.Header.Set("User-Agent", d.userAgent)

	// 如果有状态，添加 Range 头
	if state != nil && state.Downloaded > 0 {
		req.Header.Set("Range", fmt.Sprintf("bytes=%d-", state.Downloaded))
		if state.ETag != "" {
			req.Header.Set("If-Range", state.ETag)
		}
	}

	resp, err := d.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	// 处理响应
	var file *os.File
	var startOffset int64 = 0

	if resp.StatusCode == http.StatusPartialContent {
		// 断点续传成功
		fmt.Printf("继续下载，已从 %d 字节开始\n", state.Downloaded)
		file, err = os.OpenFile(outputFile, os.O_WRONLY|os.O_APPEND, 0644)
		startOffset = state.Downloaded
	} else {
		// 全新下载或部分不支持
		if state != nil && state.Downloaded > 0 {
			fmt.Println("服务器不支持断点续传，重新开始下载")
		}
		file, err = os.Create(outputFile)
	}

	if err != nil {
		return err
	}
	defer file.Close()

	// 获取总大小
	totalSize := startOffset + resp.ContentLength
	if state != nil && totalSize < state.Downloaded {
		totalSize = state.Downloaded + resp.ContentLength
	}

	// 更新状态
	if state == nil {
		state = &DownloadState{
			URL:        url,
			OutputFile: outputFile,
			StartTime:  time.Now(),
		}
	}
	state.Downloaded = startOffset
	state.Total = totalSize
	state.ETag = resp.Header.Get("ETag")
	state.LastModified = resp.Header.Get("Last-Modified")

	// 下载
	buf := make([]byte, 32*1024)
	for {
		n, err := resp.Body.Read(buf)
		if n > 0 {
			_, werr := file.Write(buf[:n])
			if werr != nil {
				return werr
			}

			state.Downloaded += int64(n)
			state.UpdateTime = time.Now()

			// 保存状态
			d.saveState(state)

			// 进度回调
			if d.progressCb != nil {
				d.progressCb(state.Downloaded, totalSize)
			}
		}

		if err != nil {
			if err == io.EOF {
				// 下载完成，删除状态文件
				os.Remove(d.stateFile)
				fmt.Printf("下载完成：%s (%.2f MB)\n", outputFile, float64(state.Downloaded)/1024/1024)
				return nil
			}
			return err
		}
	}
}

// loadState 加载状态
func (d *ResumeDownloader) loadState() (*DownloadState, error) {
	data, err := os.ReadFile(d.stateFile)
	if err != nil {
		return nil, err
	}

	var state DownloadState
	if err := json.Unmarshal(data, &state); err != nil {
		return nil, err
	}

	return &state, nil
}

// saveState 保存状态
func (d *ResumeDownloader) saveState(state *DownloadState) error {
	data, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(d.stateFile, data, 0644)
}

// GetDownloadProgress 获取下载进度
func (d *ResumeDownloader) GetDownloadProgress(outputFile string) (*DownloadState, error) {
	stateFile := outputFile + ".state"
	
	info, err := os.Stat(stateFile)
	if err != nil {
		return nil, err
	}

	if info.Size() == 0 {
		return nil, fmt.Errorf("状态文件为空")
	}

	return d.loadState()
}

// CleanStateFiles 清理状态文件
func (d *ResumeDownloader) CleanStateFiles() error {
	pattern := filepath.Join(d.outputDir, "*.state")
	files, err := filepath.Glob(pattern)
	if err != nil {
		return err
	}

	for _, file := range files {
		os.Remove(file)
	}

	fmt.Printf("清理了 %d 个状态文件\n", len(files))
	return nil
}
