package distributed

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"path"
	"strings"
	"sync"
	"time"

	"gospider/core"
	"gospider/media"
	"gospider/network"
	runtimedispatch "gospider/runtime/dispatch"
)

// Worker 分布式工作节点
type Worker struct {
	ID          string
	Host        string
	Port        int
	redis       *RedisClient
	monitor     *network.VideoMonitor
	downloader  *media.HLSDownloader
	ffmpeg      *media.FFmpegWrapper
	executor    core.Executor
	running     bool
	currentTask *CrawlTask
	tasksDone   int
	mu          sync.Mutex
	outputDir   string
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

	coreConfig := core.DefaultConfig()
	coreConfig.Output.DownloadDir = config.OutputDir
	coreConfig.Media.OutputDir = config.OutputDir
	coreConfig.Output.ArtifactDir = config.OutputDir

	worker := &Worker{
		ID:         workerID,
		Host:       config.Host,
		Port:       config.Port,
		redis:      redisClient,
		monitor:    monitor,
		downloader: downloader,
		ffmpeg:     ffmpeg,
		outputDir:  config.OutputDir,
		tasksDone:  0,
	}

	worker.executor = runtimedispatch.NewExecutor(runtimedispatch.Options{
		Config:        coreConfig,
		MediaExecutor: &workerMediaExecutor{worker: worker},
	})

	return worker, nil
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

	stopHeartbeat := make(chan struct{})
	go func(taskID string) {
		ticker := time.NewTicker(10 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				_ = w.redis.HeartbeatTask(taskID, 30*time.Second)
			case <-stopHeartbeat:
				return
			}
		}
	}(task.ID)
	defer close(stopHeartbeat)

	job, err := taskToJobSpec(task, w.outputDir)
	if err != nil {
		log.Printf("[Worker %s] 任务编译失败：%v", w.ID, err)
		task.Error = err.Error()
		task.Data = ensureTaskData(task.Data)
		task.Data["compiled"] = false
		_ = w.redis.SaveTask(task)
		_ = w.redis.FailTask(task.ID, err.Error())
		return
	}

	task.Job = &job
	task.Data = ensureTaskData(task.Data)
	task.Data["compiled"] = true
	task.Data["runtime"] = string(job.Runtime)
	_ = w.redis.SaveTask(task)

	result, err := w.executor.Execute(context.Background(), job)
	task.Result = result
	mergeResultIntoTask(task, result)
	if result != nil {
		task.Error = result.Error
	}
	_ = w.redis.SaveTask(task)

	if err != nil {
		log.Printf("[Worker %s] 任务失败：%v", w.ID, err)
		_ = w.redis.FailTask(task.ID, err.Error())
		return
	}

	log.Printf("[Worker %s] 任务完成：%s", w.ID, task.ID)
	_ = w.redis.CompleteTask(task.ID)
	w.tasksDone++
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

type workerMediaExecutor struct {
	worker *Worker
}

func (e *workerMediaExecutor) Execute(_ context.Context, job core.JobSpec) (*core.JobResult, error) {
	if err := job.Validate(); err != nil {
		return nil, err
	}
	if job.Runtime != core.RuntimeMedia {
		return nil, fmt.Errorf("worker media executor cannot execute %q jobs", job.Runtime)
	}

	mediaType := "video"
	if len(job.Media.Types) > 0 && job.Media.Types[0] != "" {
		mediaType = strings.ToLower(job.Media.Types[0])
	}

	result := core.NewJobResult(job, core.StateFailed)
	result.Metadata["capability"] = "worker-media"

	switch mediaType {
	case "hls", "dash":
		taskID := metadataString(job.Metadata, "task_id", "media-task")
		outputFile := fmt.Sprintf("%s/%s.mp4", e.worker.outputDir, taskID)
		err := e.worker.downloader.DownloadWithFFmpeg(
			e.worker.ffmpeg.FFmpegPath,
			job.Target.URL,
			outputFile,
		)
		if err != nil {
			result.Error = err.Error()
			result.FinishedAt = time.Now()
			result.Finalize()
			return result, err
		}

		isDRM, drmType, _ := e.worker.ffmpeg.CheckDRM(outputFile)
		result.State = core.StateSucceeded
		result.AddMediaArtifact(core.MediaArtifact{
			Type: mediaType,
			URL:  job.Target.URL,
			Path: outputFile,
		})
		if isDRM {
			result.SetExtractField("drm_type", drmType)
		}
		result.Metadata["is_drm"] = isDRM
		result.FinishedAt = time.Now()
		result.Finalize()
		return result, nil
	case "image", "audio", "video":
		downloader := media.NewMediaDownloader(e.worker.outputDir)
		filename := inferOutputFilename(job.Target.URL, mediaType, metadataString(job.Metadata, "task_id", "media-task"))

		var download *media.DownloadResult
		switch mediaType {
		case "image":
			download = downloader.DownloadImage(job.Target.URL, filename)
		case "audio":
			download = downloader.DownloadAudio(job.Target.URL, filename)
		default:
			download = downloader.DownloadVideo(job.Target.URL, filename)
		}

		if download == nil {
			result.Error = "media download returned no result"
			result.FinishedAt = time.Now()
			result.Finalize()
			return result, fmt.Errorf("%s", result.Error)
		}
		if !download.Success {
			result.Error = download.Error
			result.FinishedAt = time.Now()
			result.Finalize()
			return result, fmt.Errorf("%s", download.Error)
		}

		result.State = core.StateSucceeded
		result.Metrics = &core.ResultMetrics{BytesIn: download.Size}
		result.AddMediaArtifact(core.MediaArtifact{
			Type: mediaType,
			URL:  download.URL,
			Path: download.Path,
		})
		result.FinishedAt = time.Now()
		result.Finalize()
		return result, nil
	default:
		result.Error = fmt.Sprintf("unsupported media type %q", mediaType)
		result.FinishedAt = time.Now()
		result.Finalize()
		return result, fmt.Errorf("%s", result.Error)
	}
}

func taskToJobSpec(task *CrawlTask, outputDir string) (core.JobSpec, error) {
	if task == nil {
		return core.JobSpec{}, fmt.Errorf("task is required")
	}

	if task.Job != nil {
		job := *task.Job
		if job.Name == "" {
			job.Name = task.ID
		}
		if job.Target.URL == "" {
			job.Target.URL = task.URL
		}
		if job.Priority == 0 {
			job.Priority = task.Priority
		}
		job.Metadata = ensureJobMetadata(job.Metadata)
		job.Metadata["task_id"] = task.ID
		job.Metadata["worker_task_type"] = task.Type
		if job.Output.Directory == "" && outputDir != "" {
			job.Output.Directory = outputDir
		}
		if err := job.Validate(); err != nil {
			return core.JobSpec{}, err
		}
		return job, nil
	}

	job := core.JobSpec{
		Name:     task.ID,
		Priority: task.Priority,
		Target: core.TargetSpec{
			URL:    task.URL,
			Method: http.MethodGet,
		},
		Output: core.OutputSpec{
			Format:    "json",
			Directory: outputDir,
		},
		Metadata: map[string]interface{}{
			"task_id":          task.ID,
			"worker_task_type": task.Type,
		},
	}

	switch strings.ToLower(task.Type) {
	case "video", "image", "audio", "hls", "dash":
		job.Runtime = core.RuntimeMedia
		job.Media = core.MediaSpec{
			Enabled:   true,
			Download:  true,
			Types:     []string{strings.ToLower(task.Type)},
			OutputDir: outputDir,
		}
	case "page", "http":
		job.Runtime = core.RuntimeHTTP
	case "browser", "monitor":
		job.Runtime = core.RuntimeBrowser
		job.Browser = core.BrowserSpec{
			Capture: []string{"html"},
		}
	case "ai":
		job.Runtime = core.RuntimeAI
	default:
		return core.JobSpec{}, fmt.Errorf("未知任务类型：%s", task.Type)
	}

	if task.Data != nil {
		if body, ok := task.Data["body"].(string); ok && body != "" {
			job.Target.Body = body
		}
		if outputFormat, ok := task.Data["output_format"].(string); ok && outputFormat != "" {
			job.Output.Format = outputFormat
		}
		if mockExtract, ok := task.Data["mock_extract"].(map[string]interface{}); ok {
			job.Metadata["mock_extract"] = mockExtract
		}
		if content, ok := task.Data["content"].(string); ok && content != "" {
			job.Metadata["content"] = content
		}
	}

	if err := job.Validate(); err != nil {
		return core.JobSpec{}, err
	}
	return job, nil
}

func mergeResultIntoTask(task *CrawlTask, result *core.JobResult) {
	if task == nil || result == nil {
		return
	}
	task.Data = ensureTaskData(task.Data)
	task.Data["runtime"] = string(result.Runtime)
	task.Data["state"] = string(result.State)
	task.Data["status_code"] = result.StatusCode
	task.Data["warnings"] = append([]string(nil), result.Warnings...)

	if len(result.Extract) > 0 {
		task.Data["extract"] = result.Extract
	}
	if result.Metrics != nil {
		task.Data["metrics"] = result.Metrics
	}
	if result.AntiBot != nil {
		task.Data["anti_bot"] = result.AntiBot
	}
	if len(result.MediaRecord) > 0 {
		task.Data["media"] = result.MediaRecord
		for _, artifact := range result.MediaRecord {
			if artifact.Path != "" {
				task.Data["output_file"] = artifact.Path
				break
			}
		}
	}
	if len(result.ArtifactRefs) > 0 {
		task.Data["artifact_refs"] = result.ArtifactRefs
	}
	if len(result.Artifacts) > 0 {
		task.Data["artifacts"] = append([]string(nil), result.Artifacts...)
	}
	if result.Error != "" {
		task.Data["error"] = result.Error
	}
}

func ensureTaskData(data map[string]interface{}) map[string]interface{} {
	if data == nil {
		return make(map[string]interface{})
	}
	return data
}

func ensureJobMetadata(metadata map[string]interface{}) map[string]interface{} {
	if metadata == nil {
		return make(map[string]interface{})
	}
	return metadata
}

func metadataString(metadata map[string]interface{}, key, fallback string) string {
	if metadata == nil {
		return fallback
	}
	if raw, ok := metadata[key].(string); ok && raw != "" {
		return raw
	}
	return fallback
}

func inferOutputFilename(rawURL, mediaType, fallback string) string {
	parsed, err := url.Parse(rawURL)
	if err == nil {
		base := path.Base(parsed.Path)
		if base != "" && base != "." && base != "/" {
			return base
		}
	}

	switch mediaType {
	case "image":
		return fallback + ".jpg"
	case "audio":
		return fallback + ".mp3"
	default:
		return fallback + ".mp4"
	}
}
