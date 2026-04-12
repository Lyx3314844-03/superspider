package media

import (
	"bufio"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// HLSDownloader HLS 流媒体下载器
type HLSDownloader struct {
	client      *http.Client
	outputDir   string
	userAgent   string
	referer     string
	concurrent  int
}

// NewHLSDownloader 创建 HLS 下载器
func NewHLSDownloader(outputDir string) *HLSDownloader {
	return &HLSDownloader{
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
		outputDir:  outputDir,
		userAgent:  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
		referer:    "",
		concurrent: 5,
	}
}

// SetReferer 设置 Referer
func (h *HLSDownloader) SetReferer(referer string) {
	h.referer = referer
}

// SetConcurrent 设置并发数
func (h *HLSDownloader) SetConcurrent(count int) {
	h.concurrent = count
}

// M3U8Playlist m3u8 播放列表结构
type M3U8Playlist struct {
	Version       int
	TargetDuration int
	MediaSegments []MediaSegment
	BaseURL       string
}

// MediaSegment 媒体分段
type MediaSegment struct {
	URL      string
	Duration float64
	Title    string
}

// ParseM3U8 解析 m3u8 文件
func (h *HLSDownloader) ParseM3U8(content string, baseURL string) (*M3U8Playlist, error) {
	playlist := &M3U8Playlist{
		BaseURL:       baseURL,
		MediaSegments: make([]MediaSegment, 0),
	}

	scanner := bufio.NewScanner(strings.NewReader(content))
	var currentSegment MediaSegment

	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())

		// 跳过空行
		if line == "" {
			continue
		}

		// EXTM3U 标签
		if line == "#EXTM3U" {
			continue
		}

		// EXT-X-VERSION
		if strings.HasPrefix(line, "#EXT-X-VERSION:") {
			fmt.Sscanf(line, "#EXT-X-VERSION:%d", &playlist.Version)
			continue
		}

		// EXT-X-TARGETDURATION
		if strings.HasPrefix(line, "#EXT-X-TARGETDURATION:") {
			fmt.Sscanf(line, "#EXT-X-TARGETDURATION:%d", &playlist.TargetDuration)
			continue
		}

		// EXTINF (分段信息)
		if strings.HasPrefix(line, "#EXTINF:") {
			parts := strings.Split(strings.TrimPrefix(line, "#EXTINF:"), ",")
			if len(parts) > 0 {
				fmt.Sscanf(parts[0], "%f", &currentSegment.Duration)
				if len(parts) > 1 {
					currentSegment.Title = parts[1]
				}
			}
			continue
		}

		// EXT-X-ENDLIST
		if line == "#EXT-X-ENDLIST" {
			continue
		}

		// 分段 URL
		if !strings.HasPrefix(line, "#") {
			currentSegment.URL = line
			// 处理相对路径
			if !strings.HasPrefix(line, "http") {
				if strings.HasPrefix(baseURL, "http") {
					// 拼接基础 URL
					lastSlash := strings.LastIndex(baseURL, "/")
					if lastSlash != -1 {
						currentSegment.URL = baseURL[:lastSlash+1] + line
					}
				}
			}
			playlist.MediaSegments = append(playlist.MediaSegments, currentSegment)
			currentSegment = MediaSegment{}
		}
	}

	return playlist, scanner.Err()
}

// DownloadM3U8 下载 m3u8 流
func (h *HLSDownloader) DownloadM3U8(m3u8URL, outputFile string) error {
	// 创建输出目录
	os.MkdirAll(h.outputDir, 0755)

	// 下载 m3u8 文件
	m3u8Content, err := h.downloadM3U8File(m3u8URL)
	if err != nil {
		return err
	}

	// 解析播放列表
	playlist, err := h.ParseM3U8(m3u8Content, m3u8URL)
	if err != nil {
		return err
	}

	if len(playlist.MediaSegments) == 0 {
		return fmt.Errorf("未找到媒体分段")
	}

	fmt.Printf("找到 %d 个媒体分段\n", len(playlist.MediaSegments))

	// 下载目录
	downloadDir := filepath.Join(h.outputDir, "temp_segments")
	os.MkdirAll(downloadDir, 0755)
	defer os.RemoveAll(downloadDir)

	// 并发下载分段
	segmentFiles := make([]string, len(playlist.MediaSegments))
	errors := make([]error, len(playlist.MediaSegments))
	var wg sync.WaitGroup
	sem := make(chan struct{}, h.concurrent)

	for i, segment := range playlist.MediaSegments {
		wg.Add(1)
		sem <- struct{}{}

		go func(idx int, seg MediaSegment) {
			defer wg.Done()
			defer func() { <-sem }()

			segmentFile := filepath.Join(downloadDir, fmt.Sprintf("seg_%04d.ts", idx))
			errors[idx] = h.downloadSegment(seg.URL, segmentFile)
			if errors[idx] == nil {
				segmentFiles[idx] = segmentFile
				fmt.Printf("下载完成：%d/%d\n", idx+1, len(playlist.MediaSegments))
			} else {
				fmt.Printf("下载失败：%d - %v\n", idx, errors[idx])
			}
		}(i, segment)
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
	return h.mergeSegments(segmentFiles, outputFile)
}

// downloadM3U8File 下载 m3u8 文件
func (h *HLSDownloader) downloadM3U8File(url string) (string, error) {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", err
	}

	req.Header.Set("User-Agent", h.userAgent)
	if h.referer != "" {
		req.Header.Set("Referer", h.referer)
	}

	resp, err := h.client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return "", fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	content, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	return string(content), nil
}

// downloadSegment 下载单个分段
func (h *HLSDownloader) downloadSegment(url, outputFile string) error {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}

	req.Header.Set("User-Agent", h.userAgent)
	if h.referer != "" {
		req.Header.Set("Referer", h.referer)
	}

	resp, err := h.client.Do(req)
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

// mergeSegments 合并 TS 分段
func (h *HLSDownloader) mergeSegments(segmentFiles []string, outputFile string) error {
	// 创建合并列表
	mergeFile, err := os.Create(outputFile)
	if err != nil {
		return err
	}
	defer mergeFile.Close()

	for _, segFile := range segmentFiles {
		segData, err := os.ReadFile(segFile)
		if err != nil {
			return err
		}
		mergeFile.Write(segData)
	}

	return nil
}

// DownloadWithFFmpeg 使用 ffmpeg 下载 HLS
func (h *HLSDownloader) DownloadWithFFmpeg(ffmpegPath, m3u8URL, outputFile string) error {
	ffmpeg := NewFFmpegWrapper(ffmpegPath, h.outputDir)
	return ffmpeg.DownloadHLS(m3u8URL, outputFile)
}
