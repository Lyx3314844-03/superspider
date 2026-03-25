package media

import (
	"encoding/json"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
)

// MediaDownloader 媒体下载器
type MediaDownloader struct {
	client      *http.Client
	outputDir   string
	userAgent   string
}

// NewMediaDownloader 创建媒体下载器
func NewMediaDownloader(outputDir string) *MediaDownloader {
	return &MediaDownloader{
		client:    &http.Client{},
		outputDir: outputDir,
		userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	}
}

// DownloadResult 下载结果
type DownloadResult struct {
	URL      string `json:"url"`
	Path     string `json:"path"`
	Size     int64  `json:"size"`
	Error    string `json:"error,omitempty"`
	Success  bool   `json:"success"`
}

// DownloadImage 下载图片
func (md *MediaDownloader) DownloadImage(url, filename string) *DownloadResult {
	result := &DownloadResult{URL: url}
	
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		result.Error = err.Error()
		result.Success = false
		return result
	}
	
	req.Header.Set("User-Agent", md.userAgent)
	req.Header.Set("Referer", "https://www.google.com/")
	
	resp, err := md.client.Do(req)
	if err != nil {
		result.Error = err.Error()
		result.Success = false
		return result
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != 200 {
		result.Error = "HTTP " + resp.Status
		result.Success = false
		return result
	}
	
	// 创建输出目录
	os.MkdirAll(md.outputDir, 0755)
	
	// 生成文件名
	if filename == "" {
		filename = filepath.Base(url)
		if filename == "" {
			filename = "image.jpg"
		}
	}
	
	filepath := filepath.Join(md.outputDir, filename)
	
	// 保存文件
	file, err := os.Create(filepath)
	if err != nil {
		result.Error = err.Error()
		result.Success = false
		return result
	}
	defer file.Close()
	
	size, err := io.Copy(file, resp.Body)
	if err != nil {
		result.Error = err.Error()
		result.Success = false
		return result
	}
	
	result.Path = filepath
	result.Size = size
	result.Success = true
	
	return result
}

// DownloadImages 批量下载图片
func (md *MediaDownloader) DownloadImages(urls []string) []*DownloadResult {
	results := make([]*DownloadResult, 0, len(urls))
	
	for _, url := range urls {
		result := md.DownloadImage(url, "")
		results = append(results, result)
	}
	
	return results
}

// ExtractImagesFromHTML 从 HTML 中提取图片链接
func (md *MediaDownloader) ExtractImagesFromHTML(html string) []string {
	var images []string
	
	// 匹配 img 标签的 src 属性
	re := regexp.MustCompile(`<img[^>]+src=["']([^"']+)["']`)
	matches := re.FindAllStringSubmatch(html, -1)
	
	for _, match := range matches {
		if len(match) > 1 {
			images = append(images, match[1])
		}
	}
	
	return images
}

// DownloadVideo 下载视频
func (md *MediaDownloader) DownloadVideo(url, filename string) *DownloadResult {
	result := &DownloadResult{URL: url}
	
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		result.Error = err.Error()
		result.Success = false
		return result
	}
	
	req.Header.Set("User-Agent", md.userAgent)
	req.Header.Set("Range", "bytes=0-")
	
	resp, err := md.client.Do(req)
	if err != nil {
		result.Error = err.Error()
		result.Success = false
		return result
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != 200 && resp.StatusCode != 206 {
		result.Error = "HTTP " + resp.Status
		result.Success = false
		return result
	}
	
	// 创建输出目录
	videoDir := filepath.Join(md.outputDir, "videos")
	os.MkdirAll(videoDir, 0755)
	
	// 生成文件名
	if filename == "" {
		filename = "video.mp4"
	}
	
	filepath := filepath.Join(videoDir, filename)
	
	// 保存文件
	file, err := os.Create(filepath)
	if err != nil {
		result.Error = err.Error()
		result.Success = false
		return result
	}
	defer file.Close()
	
	size, err := io.Copy(file, resp.Body)
	if err != nil {
		result.Error = err.Error()
		result.Success = false
		return result
	}
	
	result.Path = filepath
	result.Size = size
	result.Success = true
	
	return result
}

// DownloadAudio 下载音频
func (md *MediaDownloader) DownloadAudio(url, filename string) *DownloadResult {
	result := &DownloadResult{URL: url}
	
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		result.Error = err.Error()
		result.Success = false
		return result
	}
	
	req.Header.Set("User-Agent", md.userAgent)
	
	resp, err := md.client.Do(req)
	if err != nil {
		result.Error = err.Error()
		result.Success = false
		return result
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != 200 {
		result.Error = "HTTP " + resp.Status
		result.Success = false
		return result
	}
	
	// 创建输出目录
	audioDir := filepath.Join(md.outputDir, "audio")
	os.MkdirAll(audioDir, 0755)
	
	// 生成文件名
	if filename == "" {
		filename = "audio.mp3"
	}
	
	filepath := filepath.Join(audioDir, filename)
	
	// 保存文件
	file, err := os.Create(filepath)
	if err != nil {
		result.Error = err.Error()
		result.Success = false
		return result
	}
	defer file.Close()
	
	size, err := io.Copy(file, resp.Body)
	if err != nil {
		result.Error = err.Error()
		result.Success = false
		return result
	}
	
	result.Path = filepath
	result.Size = size
	result.Success = true
	
	return result
}

// VideoInfo 视频信息
type VideoInfo struct {
	Title       string `json:"title"`
	Duration    int    `json:"duration"`
	Thumbnail   string `json:"thumbnail"`
	Formats     []VideoFormat `json:"formats"`
}

// VideoFormat 视频格式
type VideoFormat struct {
	FormatID  string `json:"format_id"`
	Ext       string `json:"ext"`
	Resolution string `json:"resolution"`
	Filesize  int64  `json:"filesize"`
	URL       string `json:"url"`
}

// GetVideoInfo 获取视频信息（模拟实现）
func (md *MediaDownloader) GetVideoInfo(url string) (*VideoInfo, error) {
	// 实际应该调用 yt-dlp 或类似工具
	// 这里只是示例
	return &VideoInfo{
		Title: "Video Title",
	}, nil
}

// ExtractMediaURLs 从页面提取媒体 URL
func (md *MediaDownloader) ExtractMediaURLs(html string) MediaURLs {
	urls := MediaURLs{
		Images: make([]string, 0),
		Videos: make([]string, 0),
		Audios: make([]string, 0),
	}
	
	// 提取图片
	imgRe := regexp.MustCompile(`(https?://[^\s"'<>]+\.(?:jpg|jpeg|png|gif|webp))`)
	urls.Images = appendUnique(urls.Images, imgRe.FindAllString(html, -1)...)
	
	// 提取视频
	videoRe := regexp.MustCompile(`(https?://[^\s"'<>]+\.(?:mp4|webm|avi|mov|flv))`)
	urls.Videos = appendUnique(urls.Videos, videoRe.FindAllString(html, -1)...)
	
	// 提取音频
	audioRe := regexp.MustCompile(`(https?://[^\s"'<>]+\.(?:mp3|wav|ogg|flac|aac))`)
	urls.Audios = appendUnique(urls.Audios, audioRe.FindAllString(html, -1)...)
	
	return urls
}

// MediaURLs 媒体 URL 集合
type MediaURLs struct {
	Images []string `json:"images"`
	Videos []string `json:"videos"`
	Audios []string `json:"audios"`
}

func appendUnique(slice []string, items ...string) []string {
	for _, item := range items {
		found := false
		for _, existing := range slice {
			if existing == item {
				found = true
				break
			}
		}
		if !found {
			slice = append(slice, item)
		}
	}
	return slice
}

// DownloadAll 下载所有媒体
func (md *MediaDownloader) DownloadAll(urls MediaURLs) DownloadStats {
	stats := DownloadStats{}
	
	// 下载图片
	for _, url := range urls.Images {
		result := md.DownloadImage(url, "")
		if result.Success {
			stats.ImagesDownloaded++
			stats.TotalBytes += result.Size
		} else {
			stats.ImagesFailed++
		}
	}
	
	// 下载视频
	for _, url := range urls.Videos {
		result := md.DownloadVideo(url, "")
		if result.Success {
			stats.VideosDownloaded++
			stats.TotalBytes += result.Size
		} else {
			stats.VideosFailed++
		}
	}
	
	// 下载音频
	for _, url := range urls.Audios {
		result := md.DownloadAudio(url, "")
		if result.Success {
			stats.AudiosDownloaded++
			stats.TotalBytes += result.Size
		} else {
			stats.AudiosFailed++
		}
	}
	
	return stats
}

// DownloadStats 下载统计
type DownloadStats struct {
	ImagesDownloaded  int   `json:"images_downloaded"`
	ImagesFailed      int   `json:"images_failed"`
	VideosDownloaded  int   `json:"videos_downloaded"`
	VideosFailed      int   `json:"videos_failed"`
	AudiosDownloaded  int   `json:"audios_downloaded"`
	AudiosFailed      int   `json:"audios_failed"`
	TotalBytes        int64 `json:"total_bytes"`
}

func (ds *DownloadStats) String() string {
	data, _ := json.MarshalIndent(ds, "", "  ")
	return string(data)
}
