package media

import (
	"context"
	"crypto/sha1"
	"encoding/xml"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
)

// DASHDownloader DASH 流媒体下载器（增强版）
type DASHDownloader struct {
	client      *http.Client
	outputDir   string
	userAgent   string
	referer     string
	concurrent  int
	timeout     time.Duration
	retryTimes  int
	progressCb  func(downloaded, total int64)
	ctx         context.Context
	cancel      context.CancelFunc
}

// DASHOptions DASH 下载选项
type DASHOptions struct {
	Quality       string // 清晰度：4k, 2k, 1080p, 720p, 480p, 360p, auto
	OutputFile    string
	SkipAudio     bool
	SkipVideo     bool
	DownloadDir   string
	Concurrent    int
	Timeout       time.Duration
	RetryTimes    int
	Progress      func(downloaded, total int64)
}

// DASHFormat DASH 格式信息
type DASHFormat struct {
	ID          string   `json:"id"`
	MimeType    string   `json:"mime_type"`
	Quality     string   `json:"quality"`
	Width       int      `json:"width"`
	Height      int      `json:"height"`
	Bandwidth   int      `json:"bandwidth"`
	Codecs      string   `json:"codecs"`
	FrameRate   float64  `json:"frame_rate"`
	AudioChan   string   `json:"audio_channel"`
	SegmentType string   `json:"segment_type"` // static, dynamic
	URLs        []string `json:"urls"`
	IsAudio     bool     `json:"is_audio"`
	IsVideo     bool     `json:"is_video"`
}

// DASHDownloadTask DASH 下载任务
type DASHDownloadTask struct {
	ID           string       `json:"id"`
	MPDURL       string       `json:"mpd_url"`
	Status       string       `json:"status"` // pending, downloading, completed, failed, paused
	Progress     float64      `json:"progress"`
	Downloaded   int64        `json:"downloaded"`
	Total        int64        `json:"total"`
	Speed        float64      `json:"speed"`
	ETA          time.Duration `json:"eta"`
	Error        string       `json:"error"`
	StartTime    time.Time    `json:"start_time"`
	CompleteTime time.Time    `json:"complete_time"`
	OutputFile   string       `json:"output_file"`
	SelectedVideo *DASHFormat `json:"selected_video"`
	SelectedAudio *DASHFormat `json:"selected_audio"`
}

// NewDASHDownloader 创建 DASH 下载器（增强版）
func NewDASHDownloader(outputDir string) *DASHDownloader {
	ctx, cancel := context.WithCancel(context.Background())
	return &DASHDownloader{
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
		timeout:    30 * time.Second,
		retryTimes: 3,
		ctx:        ctx,
		cancel:     cancel,
	}
}

// SetProgressCallback 设置进度回调
func (d *DASHDownloader) SetProgressCallback(cb func(downloaded, total int64)) {
	d.progressCb = cb
}

// SetConcurrent 设置并发数
func (d *DASHDownloader) SetConcurrent(count int) {
	d.concurrent = count
}

// SetTimeout 设置超时
func (d *DASHDownloader) SetTimeout(timeout time.Duration) {
	d.timeout = timeout
	d.client.Timeout = timeout
}

// SetReferer 设置 Referer
func (d *DASHDownloader) SetReferer(referer string) {
	d.referer = referer
}

// Close 关闭下载器
func (d *DASHDownloader) Close() {
	d.cancel()
}

// DownloadDASH 下载 DASH 流（增强版）
func (d *DASHDownloader) DownloadDASH(mpdURL string, opts *DASHOptions) (*DASHDownloadTask, error) {
	if opts == nil {
		opts = &DASHOptions{}
	}

	// 初始化任务
	task := &DASHDownloadTask{
		ID:        generateTaskID(mpdURL),
		MPDURL:    mpdURL,
		Status:    "pending",
		StartTime: time.Now(),
	}

	// 应用选项
	if opts.Quality == "" {
		opts.Quality = "auto"
	}
	if opts.Concurrent > 0 {
		d.concurrent = opts.Concurrent
	}
	if opts.Timeout > 0 {
		d.SetTimeout(opts.Timeout)
	}
	if opts.Progress != nil {
		d.progressCb = opts.Progress
	}

	// 创建输出目录
	outputDir := d.outputDir
	if opts.DownloadDir != "" {
		outputDir = opts.DownloadDir
	}
	os.MkdirAll(outputDir, 0755)

	// 确定输出文件名
	outputFile := opts.OutputFile
	if outputFile == "" {
		outputFile = filepath.Join(outputDir, fmt.Sprintf("dash_%s.mp4", task.ID[:8]))
	}
	task.OutputFile = outputFile

	// 开始下载
	task.Status = "downloading"

	// 下载并解析 MPD
	mpd, mpdContent, err := d.downloadMPD(mpdURL)
	if err != nil {
		task.Status = "failed"
		task.Error = fmt.Sprintf("下载 MPD 失败：%v", err)
		return task, err
	}

	// 解析 MPD 获取所有格式
	formats := d.parseMPD(mpd, mpdContent, mpdURL)
	if len(formats) == 0 {
		task.Status = "failed"
		task.Error = "未找到任何媒体流"
		return task, fmt.Errorf("未找到任何媒体流")
	}

	// 分离音视频格式
	var videoFormats, audioFormats []DASHFormat
	for _, f := range formats {
		if f.IsVideo {
			videoFormats = append(videoFormats, f)
		}
		if f.IsAudio {
			audioFormats = append(audioFormats, f)
		}
	}

	// 选择最佳格式
	var selectedVideo, selectedAudio *DASHFormat

	if !opts.SkipVideo && len(videoFormats) > 0 {
		selectedVideo = d.selectQuality(videoFormats, opts.Quality)
		task.SelectedVideo = selectedVideo
		fmt.Printf("选择视频格式：%s (%dx%d, %d kbps, %s)\n",
			selectedVideo.Quality, selectedVideo.Width, selectedVideo.Height,
			selectedVideo.Bandwidth/1000, selectedVideo.Codecs)
	}

	if !opts.SkipAudio && len(audioFormats) > 0 {
		selectedAudio = d.selectBestAudio(audioFormats)
		task.SelectedAudio = selectedAudio
		fmt.Printf("选择音频格式：%s (%d kbps, %s)\n",
			selectedAudio.Quality, selectedAudio.Bandwidth/1000, selectedAudio.Codecs)
	}

	// 计算总大小
	var totalSize int64
	for _, url := range selectedVideo.URLs {
		if size := d.getSegmentSize(url); size > 0 {
			totalSize += size
		}
	}
	if selectedAudio != nil {
		for _, url := range selectedAudio.URLs {
			if size := d.getSegmentSize(url); size > 0 {
				totalSize += size
			}
		}
	}
	task.Total = totalSize

	// 创建临时目录
	tempDir := filepath.Join(outputDir, fmt.Sprintf("dash_temp_%s", task.ID[:8]))
	os.MkdirAll(tempDir, 0755)

	// 下载视频分段
	var videoFile, audioFile string
	if selectedVideo != nil {
		fmt.Println("正在下载视频分段...")
		videoFile = filepath.Join(tempDir, "video.mp4")
		if err := d.downloadSegments(selectedVideo.URLs, videoFile, task); err != nil {
			task.Status = "failed"
			task.Error = fmt.Sprintf("下载视频失败：%v", err)
			return task, err
		}
	}

	// 下载音频分段
	if selectedAudio != nil {
		fmt.Println("正在下载音频分段...")
		audioFile = filepath.Join(tempDir, "audio.mp4")
		if err := d.downloadSegments(selectedAudio.URLs, audioFile, task); err != nil {
			task.Status = "failed"
			task.Error = fmt.Sprintf("下载音频失败：%v", err)
			return task, err
		}
	}

	// 合并音视频
	fmt.Println("正在合并音视频...")
	if videoFile != "" && audioFile != "" {
		ffmpeg := NewFFmpegWrapper("", outputDir)
		if ffmpegPath, err := AutoDetectFFmpeg(); err == nil {
			ffmpeg.FFmpegPath = ffmpegPath
			if err := ffmpeg.CombineAudioVideo(videoFile, audioFile, outputFile); err != nil {
				// FFmpeg 失败，只使用视频
				os.Rename(videoFile, outputFile)
			}
		} else {
			// 没有 ffmpeg，只保存视频
			os.Rename(videoFile, outputFile)
		}
	} else if videoFile != "" {
		os.Rename(videoFile, outputFile)
	} else if audioFile != "" {
		os.Rename(audioFile, outputFile)
	}

	// 清理临时目录
	os.RemoveAll(tempDir)

	// 完成任务
	task.Status = "completed"
	task.CompleteTime = time.Now()
	task.Progress = 100

	fmt.Printf("下载完成：%s\n", outputFile)
	return task, nil
}

// downloadMPD 下载 MPD 文件
func (d *DASHDownloader) downloadMPD(mpdURL string) (*MPD, string, error) {
	req, err := http.NewRequest("GET", mpdURL, nil)
	if err != nil {
		return nil, "", err
	}

	req.Header.Set("User-Agent", d.userAgent)
	if d.referer != "" {
		req.Header.Set("Referer", d.referer)
	}

	resp, err := d.client.Do(req)
	if err != nil {
		return nil, "", err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, "", err
	}

	var mpd MPD
	if err := xml.Unmarshal(body, &mpd); err != nil {
		return nil, "", err
	}

	return &mpd, string(body), nil
}

// parseMPD 解析 MPD（增强版，支持 SegmentTemplate）
func (d *DASHDownloader) parseMPD(mpd *MPD, mpdContent string, baseURL string) []DASHFormat {
	formats := make([]DASHFormat, 0)
	basePath := baseURL[:strings.LastIndex(baseURL, "/")+1]

	for _, period := range mpd.Periods {
		for _, adaptation := range period.AdaptationSets {
			contentType := d.extractContentType(adaptation.MimeType)
			
			for _, rep := range adaptation.Representations {
				format := DASHFormat{
					ID:        rep.ID,
					MimeType:  adaptation.MimeType,
					Width:     rep.Width,
					Height:    rep.Height,
					Bandwidth: rep.Bandwidth,
					Codecs:    rep.Codecs,
					URLs:      make([]string, 0),
				}

				// 确定质量
				format.Quality = d.determineQuality(rep.Height)
				
				// 确定音视频类型
				format.IsVideo = contentType == "video" || rep.Width > 0
				format.IsAudio = contentType == "audio" || (strings.Contains(rep.Codecs, "mp4a") || strings.Contains(rep.Codecs, "ac-3"))

				// 处理不同类型的分段
				if rep.SegmentList != nil {
					// SegmentList - 静态 MPD
					for _, seg := range rep.SegmentList.SegmentURLs {
						url := seg.Media
						if !strings.HasPrefix(url, "http") {
							url = basePath + url
						}
						format.URLs = append(format.URLs, url)
					}
					format.SegmentType = "static"
				} else if rep.SegmentTemplate != nil {
					// SegmentTemplate - 动态或静态 MPD
					tmpl := rep.SegmentTemplate
					format.SegmentType = "dynamic"
					
					// 解析分段模板
					timescale := tmpl.Timescale
					if timescale == 0 {
						timescale = 1
					}
					
					duration := tmpl.Duration
					startNumber := tmpl.StartNumber
					if startNumber == 0 {
						startNumber = 1
					}

					// 计算分段数量
					var segmentCount int
					if mpd.Type == "static" {
						// 静态 MPD：从 duration 计算
						if duration > 0 && period.Duration != "" {
							periodSec := d.parseDuration(period.Duration)
							segmentDuration := float64(duration) / float64(timescale)
							segmentCount = int(periodSec / segmentDuration)
						}
					} else {
						// 动态 MPD：需要从其他途径获取
						segmentCount = 100 // 默认值
					}

					// 生成 URL
					for i := 0; i < segmentCount; i++ {
						num := startNumber + i
						url := tmpl.Media
						url = strings.ReplaceAll(url, "$Number$", fmt.Sprintf("%04d", num))
						url = strings.ReplaceAll(url, "$Number%04d$", fmt.Sprintf("%04d", num))
						url = strings.ReplaceAll(url, "$RepresentationID$", rep.ID)
						url = strings.ReplaceAll(url, "$Time$", fmt.Sprintf("%d", i*duration))
						
						if !strings.HasPrefix(url, "http") {
							url = basePath + url
						}
						format.URLs = append(format.URLs, url)
					}

					// 处理初始化分段
					if tmpl.Initialization != "" {
						initURL := tmpl.Initialization
						initURL = strings.ReplaceAll(initURL, "$RepresentationID$", rep.ID)
						if !strings.HasPrefix(initURL, "http") {
							initURL = basePath + initURL
						}
						// 初始化分段放在最前面
						format.URLs = append([]string{initURL}, format.URLs...)
					}
				} else if rep.SegmentBase != nil {
					// SegmentBase - 单文件
					if rep.SegmentBase.Initialization != nil {
						url := rep.SegmentBase.Initialization.SourceURL
						if !strings.HasPrefix(url, "http") {
							url = basePath + url
						}
						format.URLs = append(format.URLs, url)
					}
					format.SegmentType = "single"
				}

				if len(format.URLs) > 0 {
					formats = append(formats, format)
				}
			}
		}
	}

	return formats
}

// selectQuality 选择清晰度
func (d *DASHDownloader) selectQuality(formats []DASHFormat, quality string) *DASHFormat {
	if quality == "auto" {
		// 选择最高清晰度
		var best DASHFormat
		for _, f := range formats {
			if best.ID == "" || f.Height > best.Height {
				best = f
			}
		}
		return &best
	}

	qualityMap := map[string]int{
		"4k":    2160,
		"2k":    1440,
		"1080":  1080,
		"1080p": 1080,
		"720":   720,
		"720p":  720,
		"480":   480,
		"480p":  480,
		"360":   360,
		"360p":  360,
	}

	targetHeight, ok := qualityMap[strings.ToLower(quality)]
	if !ok {
		targetHeight = 1080 // 默认 1080p
	}

	var best DASHFormat
	for _, f := range formats {
		if f.Height <= targetHeight {
			if best.ID == "" || f.Height > best.Height {
				best = f
			}
		}
	}

	if best.ID == "" {
		// 如果没有匹配的，选择最低的
		best = formats[0]
		for _, f := range formats {
			if f.Height < best.Height {
				best = f
			}
		}
	}

	return &best
}

// selectBestAudio 选择最佳音频
func (d *DASHDownloader) selectBestAudio(formats []DASHFormat) *DASHFormat {
	var best DASHFormat
	for _, f := range formats {
		if best.ID == "" || f.Bandwidth > best.Bandwidth {
			best = f
		}
	}
	return &best
}

// downloadSegments 下载分段（支持断点续传和进度）
func (d *DASHDownloader) downloadSegments(urls []string, outputFile string, task *DASHDownloadTask) error {
	// 检查是否已存在部分下载的文件
	downloadedSegments := make(map[int]bool)
	
	// 并发下载
	var mu sync.Mutex
	var downloaded int64
	var wg sync.WaitGroup
	sem := make(chan struct{}, d.concurrent)
	errors := make([]error, len(urls))

	for i, url := range urls {
		// 检查分段是否已下载
		segmentHash := d.hashURL(url)
		tempFile := filepath.Join(filepath.Dir(outputFile), fmt.Sprintf("seg_%s.tmp", segmentHash[:8]))
		
		if info, err := os.Stat(tempFile); err == nil && info.Size() > 0 {
			// 分段已下载
			mu.Lock()
			downloadedSegments[i] = true
			downloaded += info.Size()
			mu.Unlock()
			continue
		}

		wg.Add(1)
		sem <- struct{}{}

		go func(idx int, u string) {
			defer wg.Done()
			defer func() { <-sem }()

			// 检查取消
			select {
			case <-d.ctx.Done():
				errors[idx] = context.Canceled
				return
			default:
			}

			segmentHash := d.hashURL(u)
			tempFile := filepath.Join(filepath.Dir(outputFile), fmt.Sprintf("seg_%s.tmp", segmentHash[:8]))

			// 下载分段
			err := d.downloadSegmentWithRetry(u, tempFile, task)
			errors[idx] = err

			if err == nil {
				mu.Lock()
				if info, err := os.Stat(tempFile); err == nil {
					downloaded += info.Size()
					downloadedSegments[idx] = true
					
					// 更新进度
					if task.Total > 0 && d.progressCb != nil {
						d.progressCb(downloaded, task.Total)
					}
					task.Downloaded = downloaded
					task.Progress = float64(downloaded) / float64(task.Total) * 100
				}
				mu.Unlock()
			}
		}(i, url)
	}

	wg.Wait()

	// 检查错误
	var failed int
	for _, err := range errors {
		if err != nil {
			failed++
		}
	}

	if failed > 0 {
		return fmt.Errorf("有 %d 个分段下载失败", failed)
	}

	// 合并分段
	return d.mergeSegmentsInOrder(urls, outputFile, downloadedSegments)
}

// downloadSegmentWithRetry 下载单个分段（带重试）
func (d *DASHDownloader) downloadSegmentWithRetry(url, outputFile string, task *DASHDownloadTask) error {
	var lastErr error
	
	for i := 0; i < d.retryTimes; i++ {
		// 检查取消
		select {
		case <-d.ctx.Done():
			return context.Canceled
		default:
		}

		err := d.downloadSegment(url, outputFile)
		if err == nil {
			return nil
		}
		lastErr = err
		
		// 重试前等待
		if i < d.retryTimes-1 {
			time.Sleep(time.Duration(i+1) * time.Second)
		}
	}

	return lastErr
}

// downloadSegment 下载单个分段
func (d *DASHDownloader) downloadSegment(url, outputFile string) error {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}

	req.Header.Set("User-Agent", d.userAgent)
	if d.referer != "" {
		req.Header.Set("Referer", d.referer)
	}

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

// mergeSegmentsInOrder 按顺序合并分段
func (d *DASHDownloader) mergeSegmentsInOrder(urls []string, outputFile string, downloaded map[int]bool) error {
	outFile, err := os.Create(outputFile)
	if err != nil {
		return err
	}
	defer outFile.Close()

	for i, url := range urls {
		if !downloaded[i] {
			continue
		}

		segmentHash := d.hashURL(url)
		tempFile := filepath.Join(filepath.Dir(outputFile), fmt.Sprintf("seg_%s.tmp", segmentHash[:8]))
		
		data, err := os.ReadFile(tempFile)
		if err != nil {
			return err
		}
		outFile.Write(data)

		os.Remove(tempFile)
	}

	return nil
}

// getSegmentSize 获取分段大小
func (d *DASHDownloader) getSegmentSize(url string) int64 {
	req, err := http.NewRequest("HEAD", url, nil)
	if err != nil {
		return 0
	}

	resp, err := d.client.Do(req)
	if err != nil {
		return 0
	}
	defer resp.Body.Close()

	if resp.ContentLength > 0 {
		return resp.ContentLength
	}

	return 0
}

// 辅助函数
func (d *DASHDownloader) extractContentType(mimeType string) string {
	if strings.Contains(mimeType, "video") {
		return "video"
	}
	if strings.Contains(mimeType, "audio") {
		return "audio"
	}
	return "other"
}

func (d *DASHDownloader) determineQuality(height int) string {
	if height >= 2160 {
		return "4K"
	} else if height >= 1440 {
		return "2K"
	} else if height >= 1080 {
		return "1080p"
	} else if height >= 720 {
		return "720p"
	} else if height >= 480 {
		return "480p"
	}
	return "360p"
}

func (d *DASHDownloader) parseDuration(duration string) float64 {
	// ISO 8601 duration format: PT1H2M3S
	re := regexp.MustCompile(`PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?`)
	matches := re.FindStringSubmatch(duration)
	if len(matches) < 4 {
		return 0
	}

	var hours, minutes, seconds float64
	if matches[1] != "" {
		hours, _ = strconv.ParseFloat(matches[1], 64)
	}
	if matches[2] != "" {
		minutes, _ = strconv.ParseFloat(matches[2], 64)
	}
	if matches[3] != "" {
		seconds, _ = strconv.ParseFloat(matches[3], 64)
	}

	return hours*3600 + minutes*60 + seconds
}

func (d *DASHDownloader) hashURL(url string) string {
	h := sha1.New()
	h.Write([]byte(url))
	return hex.EncodeToString(h.Sum(nil))
}

func generateTaskID(url string) string {
	h := sha1.New()
	h.Write([]byte(url))
	return hex.EncodeToString(h.Sum(nil))[:16]
}

// GetDASHInfo 获取 DASH 信息
func (d *DASHDownloader) GetDASHInfo(mpdURL string) (map[string]interface{}, error) {
	mpd, content, err := d.downloadMPD(mpdURL)
	if err != nil {
		return nil, err
	}

	formats := d.parseMPD(mpd, content, mpdURL)

	// 分离音视频
	var videoFormats, audioFormats []DASHFormat
	for _, f := range formats {
		if f.IsVideo {
			videoFormats = append(videoFormats, f)
		}
		if f.IsAudio {
			audioFormats = append(audioFormats, f)
		}
	}

	info := map[string]interface{}{
		"type":           mpd.Type,
		"duration":       mpd.MediaPres,
		"video_formats":  videoFormats,
		"audio_formats":  audioFormats,
		"total_video":    len(videoFormats),
		"total_audio":    len(audioFormats),
		"available_qualities": d.getAvailableQualities(videoFormats),
	}

	return info, nil
}

func (d *DASHDownloader) getAvailableQualities(formats []DASHFormat) []string {
	qualities := make(map[string]bool)
	for _, f := range formats {
		qualities[f.Quality] = true
	}

	result := make([]string, 0, len(qualities))
	for q := range qualities {
		result = append(result, q)
	}
	return result
}

// SaveTaskInfo 保存任务信息
func (task *DASHDownloadTask) SaveTaskInfo(outputFile string) error {
	infoFile := strings.TrimSuffix(outputFile, filepath.Ext(outputFile)) + ".json"
	data, err := json.MarshalIndent(task, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(infoFile, data, 0644)
}
