package media

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

// YouTubeDownloader YouTube 视频下载器
type YouTubeDownloader struct {
	client    *http.Client
	outputDir string
	userAgent string
}

// YouTubeVideoData YouTube 视频数据
type YouTubeVideoData struct {
	Title       string       `json:"title"`
	VideoID     string       `json:"video_id"`
	Author      string       `json:"author"`
	Duration    int          `json:"duration"`
	Formats     []FormatInfo `json:"formats"`
	VideoURL    string       `json:"video_url"`
	AudioURL    string       `json:"audio_url"`
	Thumbnail   string       `json:"thumbnail"`
	Description string       `json:"description"`
}

// FormatInfo 格式信息
type FormatInfo struct {
	Itag      int    `json:"itag"`
	MimeType  string `json:"mime_type"`
	Quality   string `json:"quality"`
	Width     int    `json:"width"`
	Height    int    `json:"height"`
	Bitrate   int    `json:"bitrate"`
	URL       string `json:"url"`
	HasAudio  bool   `json:"has_audio"`
	HasVideo  bool   `json:"has_video"`
	Codecs    string `json:"codecs"`
}

// NewYouTubeDownloader 创建 YouTube 下载器
func NewYouTubeDownloader(outputDir string) *YouTubeDownloader {
	return &YouTubeDownloader{
		client: &http.Client{
			Timeout: 60 * time.Second,
		},
		outputDir: outputDir,
		userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	}
}

// ExtractVideoInfo 提取视频信息（需要浏览器渲染后的 HTML）
func (d *YouTubeDownloader) ExtractVideoInfo(html string) (*YouTubeVideoData, error) {
	// 查找 ytInitialPlayerResponse
	re := regexp.MustCompile(`ytInitialPlayerResponse\s*=\s*({.+?});`)
	match := re.FindStringSubmatch(html)
	
	if len(match) < 2 {
		// 尝试从 script 标签查找
		scriptRe := regexp.MustCompile(`<script[^>]*>\s*var\s+ytInitialPlayerResponse\s*=\s*({.+?});`)
		match = scriptRe.FindStringSubmatch(html)
	}
	
	if len(match) < 2 {
		return nil, fmt.Errorf("无法找到视频数据")
	}
	
	var playerResponse map[string]interface{}
	if err := json.Unmarshal([]byte(match[1]), &playerResponse); err != nil {
		return nil, fmt.Errorf("解析视频数据失败：%v", err)
	}
	
	videoData := &YouTubeVideoData{}
	
	// 提取视频详情
	if videoDetails, ok := playerResponse["videoDetails"].(map[string]interface{}); ok {
		videoData.Title = getString(videoDetails, "title")
		videoData.VideoID = getString(videoDetails, "videoId")
		videoData.Author = getString(videoDetails, "author")
		videoData.Duration = getInt(videoDetails, "lengthSeconds")
		videoData.Description = getString(videoDetails, "shortDescription")
		
		if thumbnail, ok := videoDetails["thumbnail"].(map[string]interface{}); ok {
			if thumbnails, ok := thumbnail["thumbnails"].([]interface{}); ok && len(thumbnails) > 0 {
				lastThumb := thumbnails[len(thumbnails)-1].(map[string]interface{})
				videoData.Thumbnail = getString(lastThumb, "url")
			}
		}
	}
	
	// 提取流媒体数据
	if streamingData, ok := playerResponse["streamingData"].(map[string]interface{}); ok {
		// 提取普通格式（带音频的视频）
		if formats, ok := streamingData["formats"].([]interface{}); ok {
			for _, f := range formats {
				if fm, ok := f.(map[string]interface{}); ok {
					formatInfo := FormatInfo{
						Itag:     getInt(fm, "itag"),
						MimeType: getString(fm, "mimeType"),
						Quality:  getString(fm, "quality"),
						Width:    getInt(fm, "width"),
						Height:   getInt(fm, "height"),
						Bitrate:  getInt(fm, "bitrate"),
						URL:      getString(fm, "url"),
						HasAudio: hasAudio(getString(fm, "mimeType")),
						HasVideo: hasVideo(getString(fm, "mimeType")),
						Codecs:   getString(fm, "codecs"),
					}
					videoData.Formats = append(videoData.Formats, formatInfo)
					if formatInfo.HasAudio && formatInfo.HasVideo && videoData.VideoURL == "" {
						videoData.VideoURL = formatInfo.URL
					}
				}
			}
		}
		
		// 提取自适应格式（分离的视频和音频）
		if adaptiveFormats, ok := streamingData["adaptiveFormats"].([]interface{}); ok {
			for _, f := range adaptiveFormats {
				if fm, ok := f.(map[string]interface{}); ok {
					formatInfo := FormatInfo{
						Itag:     getInt(fm, "itag"),
						MimeType: getString(fm, "mimeType"),
						Quality:  getString(fm, "quality"),
						Width:    getInt(fm, "width"),
						Height:   getInt(fm, "height"),
						Bitrate:  getInt(fm, "bitrate"),
						URL:      getString(fm, "url"),
						HasAudio: hasAudio(getString(fm, "mimeType")),
						HasVideo: hasVideo(getString(fm, "mimeType")),
						Codecs:   getString(fm, "codecs"),
					}
					videoData.Formats = append(videoData.Formats, formatInfo)
				}
			}
		}
	}
	
	if videoData.VideoURL == "" && len(videoData.Formats) > 0 {
		return nil, fmt.Errorf("未找到可下载的视频流")
	}
	
	return videoData, nil
}

// Download 下载视频
func (d *YouTubeDownloader) Download(videoURL string, html string) (string, error) {
	videoData, err := d.ExtractVideoInfo(html)
	if err != nil {
		return "", err
	}
	
	fmt.Printf("\n📺 YouTube 视频信息:\n")
	fmt.Printf("  标题：%s\n", videoData.Title)
	fmt.Printf("  作者：%s\n", videoData.Author)
	fmt.Printf("  时长：%d秒\n", videoData.Duration)
	fmt.Printf("  可用格式：%d\n", len(videoData.Formats))
	
	// 选择最佳格式（带音频的视频）
	var bestFormat FormatInfo
	for _, f := range videoData.Formats {
		if f.HasAudio && f.HasVideo {
			if bestFormat.Height == 0 || f.Height > bestFormat.Height {
				bestFormat = f
			}
		}
	}
	
	if bestFormat.URL == "" {
		return "", fmt.Errorf("未找到合适的视频格式")
	}
	
	fmt.Printf("  选择格式：%s (%dx%d)\n", bestFormat.Quality, bestFormat.Width, bestFormat.Height)
	
	// 清理文件名
	safeTitle := sanitizeFileName(videoData.Title)
	outputFile := filepath.Join(d.outputDir, fmt.Sprintf("%s_%s.mp4", safeTitle, videoData.VideoID))
	
	// 下载视频
	fmt.Printf("\n⬇️  正在下载...\n")
	if err := d.downloadFile(bestFormat.URL, outputFile); err != nil {
		return "", err
	}
	
	fmt.Printf("✅ 下载完成：%s\n", outputFile)
	return outputFile, nil
}

// downloadFile 下载文件
func (d *YouTubeDownloader) downloadFile(fileURL, outputFile string) error {
	req, err := http.NewRequest("GET", fileURL, nil)
	if err != nil {
		return err
	}
	
	req.Header.Set("User-Agent", d.userAgent)
	req.Header.Set("Referer", "https://www.youtube.com/")
	
	resp, err := d.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("下载失败：HTTP %d", resp.StatusCode)
	}
	
	file, err := os.Create(outputFile)
	if err != nil {
		return err
	}
	defer file.Close()
	
	_, err = io.Copy(file, resp.Body)
	return err
}

// 辅助函数
func getString(m map[string]interface{}, key string) string {
	if v, ok := m[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}

func getInt(m map[string]interface{}, key string) int {
	if v, ok := m[key]; ok {
		switch val := v.(type) {
		case int:
			return val
		case float64:
			return int(val)
		case string:
			var i int
			fmt.Sscanf(val, "%d", &i)
			return i
		}
	}
	return 0
}

func hasAudio(mimeType string) bool {
	return strings.Contains(mimeType, "mp4a") || 
		   strings.Contains(mimeType, "opus") || 
		   strings.Contains(mimeType, "ac-3") ||
		   strings.Contains(mimeType, "webma")
}

func hasVideo(mimeType string) bool {
	return strings.Contains(mimeType, "video/") ||
		   strings.Contains(mimeType, "avc") ||
		   strings.Contains(mimeType, "vp9") ||
		   strings.Contains(mimeType, "vp8") ||
		   strings.Contains(mimeType, "hevc")
}

func sanitizeFileName(name string) string {
	// 移除非法字符
	invalidChars := []string{"<", ">", ":", "\"", "/", "\\", "|", "?", "*"}
	for _, c := range invalidChars {
		name = strings.ReplaceAll(name, c, "")
	}
	name = strings.TrimSpace(name)
	// 限制长度
	if len(name) > 100 {
		name = name[:100]
	}
	return name
}

// ExtractVideoID 从 URL 提取视频 ID
func ExtractVideoID(videoURL string) (string, error) {
	parsed, err := url.Parse(videoURL)
	if err != nil {
		return "", err
	}
	
	// youtu.be 短链接
	if strings.Contains(parsed.Host, "youtu.be") {
		return strings.TrimPrefix(parsed.Path, "/"), nil
	}
	
	// 标准链接
	videoID := parsed.Query().Get("v")
	if videoID != "" {
		return videoID, nil
	}
	
	// /embed/ 或 /v/ 格式
	parts := strings.Split(parsed.Path, "/")
	for i, part := range parts {
		if part == "embed" || part == "v" {
			if i+1 < len(parts) {
				return parts[i+1], nil
			}
		}
	}
	
	return "", fmt.Errorf("无法提取视频 ID")
}
