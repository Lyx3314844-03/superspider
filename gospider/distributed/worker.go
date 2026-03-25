package distributed

import (
	"fmt"
	"log"
	"os"
	"sync"
	"time"

	"gospider/media"
	"gospider/network"
)

// Worker 分布式工作节点
type Worker struct {
	ID           string
	Host         string
	Port         int
	redis        *RedisClient
	monitor      *network.VideoMonitor
	downloader   *media.HLSDownloader
	ffmpeg       *media.FFmpegWrapper
	running      bool
	currentTask  *CrawlTask
	tasksDone    int
	mu           sync.Mutex
	outputDir    string
}

// WorkerConfig 工作节点配置
type WorkerConfig struct {
	ID            string
	Host          string
	Port          int
	RedisAddr     string
	RedisPassword string
	RedisDB       int
	OutputDir     string
	FFmpegPath    string
}

// NewWorker 创建工作节点
func NewWorker(config *WorkerConfig) (*Worker, error) {
	// 连接 Redis
	redisClient, err := NewRedisClient(config.RedisAddr, config.RedisPassword, config.RedisDB)
	if err != nil {
		return nil, fmt.Errorf("连接 Redis 失败：%v", err)
	}

	// 创建监控器
	monitor := network.NewVideoMonitor()

	// 创建下载器
	downloader := media.NewHLSDownloader(config.OutputDir)

	// 创建 FFmpeg 封装器
	ffmpegPath := config.FFmpegPath
	if ffmpegPath == "" {
		ffmpegPath, _ = media.AutoDetectFFmpeg()
	}
	ffmpeg := media.NewFFmpegWrapper(ffmpegPath, config.OutputDir)

	workerID := config.ID
	if workerID == "" {
		hostname, _ := os.Hostname()
		workerID = fmt.Sprintf("%s:%d", hostname, config.Port)
	}

	return &Worker{
		ID:         workerID,
		Host:       config.Host,
		Port:       config.Port,
		redis:      redisClient,
		monitor:    monitor,
		downloader: downloader,
		ffmpeg:     ffmpeg,
		outputDir:  config.OutputDir,
		tasksDone:  0,
	}, nil
}

// Start 启动工作节点
func (w *Worker) Start() error {
	w.mu.Lock()
	w.running = true
	w.mu.Unlock()

	log.Printf("[Worker %s] 启动...", w.ID)

	// 注册工作节点
	workerInfo := &WorkerInfo{
		ID:        w.ID,
		Host:      w.Host,
		Port:      w.Port,
		Status:    "idle",
		TasksDone: 0,
	}

	if err := w.redis.RegisterWorker(workerInfo); err != nil {
		return err
	}

	// 启动心跳协程
	go w.heartbeatLoop()

	// 启动任务处理协程
	go w.processLoop()

	return nil
}

// Stop 停止工作节点
func (w *Worker) Stop() error {
	w.mu.Lock()
	w.running = false
	w.mu.Unlock()

	log.Printf("[Worker %s] 停止...", w.ID)

	// 更新状态为离线
	workerInfo, _ := w.redis.GetWorker(w.ID)
	if workerInfo != nil {
		workerInfo.Status = "offline"
		w.redis.RegisterWorker(workerInfo)
	}

	return w.redis.Close()
}

// heartbeatLoop 心跳循环
func (w *Worker) heartbeatLoop() {
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		if !w.running {
			break
		}

		w.mu.Lock()
		status := "idle"
		if w.currentTask != nil {
			status = "active"
		}
		w.mu.Unlock()

		// 更新心跳
		if err := w.redis.UpdateWorkerHeartbeat(w.ID); err != nil {
			log.Printf("[Worker %s] 更新心跳失败：%v", w.ID, err)
		}

		// 更新状态
		workerInfo, _ := w.redis.GetWorker(w.ID)
		if workerInfo != nil {
			workerInfo.Status = status
			workerInfo.TasksDone = w.tasksDone
			if w.currentTask != nil {
				workerInfo.CurrentTask = w.currentTask.ID
			}
			w.redis.RegisterWorker(workerInfo)
		}
	}
}

// processLoop 任务处理循环
func (w *Worker) processLoop() {
	for {
		if !w.running {
			break
		}

		// 获取任务
		task, err := w.redis.PopTask(w.ID)
		if err != nil {
			log.Printf("[Worker %s] 获取任务失败：%v", w.ID, err)
			time.Sleep(5 * time.Second)
			continue
		}

		if task == nil {
			// 队列为空，等待
			time.Sleep(2 * time.Second)
			continue
		}

		// 处理任务
		w.processTask(task)
	}
}

// processTask 处理单个任务
func (w *Worker) processTask(task *CrawlTask) {
	log.Printf("[Worker %s] 处理任务：%s - %s", w.ID, task.ID, task.URL)

	w.mu.Lock()
	w.currentTask = task
	w.mu.Unlock()

	defer func() {
		w.mu.Lock()
		w.currentTask = nil
		w.mu.Unlock()
	}()

	var err error

	switch task.Type {
	case "video":
		err = w.downloadVideo(task)
	case "hls":
		err = w.downloadHLS(task)
	case "monitor":
		err = w.monitorPage(task)
	default:
		err = fmt.Errorf("未知任务类型：%s", task.Type)
	}

	if err != nil {
		log.Printf("[Worker %s] 任务失败：%v", w.ID, err)
		w.redis.FailTask(task.ID, err.Error())
	} else {
		log.Printf("[Worker %s] 任务完成：%s", w.ID, task.ID)
		w.redis.CompleteTask(task.ID)
		w.tasksDone++
	}
}

// downloadVideo 下载视频
func (w *Worker) downloadVideo(task *CrawlTask) error {
	url := task.URL
	outputFile := fmt.Sprintf("%s/%s.mp4", w.outputDir, task.ID)

	// 使用基础下载器
	downloader := media.NewMediaDownloader(w.outputDir)
	result := downloader.DownloadVideo(url, outputFile)

	if !result.Success {
		return fmt.Errorf("下载失败：%s", result.Error)
	}

	// 更新任务数据
	task.Data["output_file"] = result.Path
	task.Data["file_size"] = result.Size

	return w.redis.SaveTask(task)
}

// downloadHLS 下载 HLS 流
func (w *Worker) downloadHLS(task *CrawlTask) error {
	m3u8URL := task.URL
	outputFile := fmt.Sprintf("%s/%s.mp4", w.outputDir, task.ID)

	// 使用 HLS 下载器
	err := w.downloader.DownloadWithFFmpeg(
		w.ffmpeg.FFmpegPath,
		m3u8URL,
		outputFile,
	)

	if err != nil {
		return err
	}

	// 检查 DRM
	isDRM, drmType, _ := w.ffmpeg.CheckDRM(outputFile)
	task.Data["output_file"] = outputFile
	task.Data["is_drm"] = isDRM
	if isDRM {
		task.Data["drm_type"] = drmType
	}

	return w.redis.SaveTask(task)
}

// monitorPage 监控页面捕获链接
func (w *Worker) monitorPage(task *CrawlTask) error {
	// 这个任务类型需要浏览器支持
	// 暂时标记为完成
	task.Data["status"] = "not_implemented"
	return w.redis.SaveTask(task)
}

// GetStatus 获取工作节点状态
func (w *Worker) GetStatus() map[string]interface{} {
	w.mu.Lock()
	defer w.mu.Unlock()

	status := map[string]interface{}{
		"id":         w.ID,
		"running":    w.running,
		"tasks_done": w.tasksDone,
		"output_dir": w.outputDir,
	}

	if w.currentTask != nil {
		status["current_task"] = w.currentTask.ID
		status["current_task_url"] = w.currentTask.URL
	}

	return status
}
