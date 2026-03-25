package media

import (
	"encoding/xml"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// LegacyDASHDownloader 保留旧版 DASH 下载器实现，避免与增强版 API 冲突。
type LegacyDASHDownloader struct {
	client     *http.Client
	outputDir  string
	userAgent  string
	concurrent int
}

// MPD MPD 播放列表
type MPD struct {
	XMLName     xml.Name `xml:"MPD"`
	Type        string   `xml:"type,attr"`
	MediaPres   string   `xml:"mediaPresentationDuration,attr"`
	Periods     []Period `xml:"Period"`
}

// Period 周期
type Period struct {
	Duration     string      `xml:"duration,attr"`
	AdaptationSets []AdaptationSet `xml:"AdaptationSet"`
}

// AdaptationSet 自适应集
type AdaptationSet struct {
	MimeType    string     `xml:"mimeType,attr"`
	Representations []Representation `xml:"Representation"`
}

// Representation 表示
type Representation struct {
	ID          string   `xml:"id,attr"`
	Width       int      `xml:"width,attr"`
	Height      int      `xml:"height,attr"`
	Bandwidth   int      `xml:"bandwidth,attr"`
	Codecs      string   `xml:"codecs,attr"`
	SegmentBase *SegmentBase `xml:"SegmentBase"`
	SegmentList *SegmentList `xml:"SegmentList"`
	SegmentTemplate *SegmentTemplate `xml:"SegmentTemplate"`
}

// SegmentBase 分段基础
type SegmentBase struct {
	Initialization *Initialization `xml:"Initialization"`
}

// SegmentList 分段列表
type SegmentList struct {
	Initialization *Initialization `xml:"Initialization"`
	SegmentURLs    []SegmentURL    `xml:"SegmentURL"`
}

// SegmentTemplate 分段模板
type SegmentTemplate struct {
	Media      string `xml:"media,attr"`
	Initialization string `xml:"initialization,attr"`
	StartNumber int    `xml:"startNumber,attr"`
	Timescale  int    `xml:"timescale,attr"`
	Duration   int    `xml:"duration,attr"`
}

// Initialization 初始化分段
type Initialization struct {
	SourceURL string `xml:"sourceURL,attr"`
	Range     string `xml:"range,attr"`
}

// SegmentURL 分段 URL
type SegmentURL struct {
	Media      string `xml:"media,attr"`
	MediaRange string `xml:"mediaRange,attr"`
}

// LegacyDASHFormat 是旧版下载器使用的格式表示。
type LegacyDASHFormat struct {
	ID        string
	Quality   string
	Width     int
	Height    int
	Bandwidth int
	Codecs    string
	URLs      []string
}

// NewLegacyDASHDownloader 创建旧版 DASH 下载器。
func NewLegacyDASHDownloader(outputDir string) *LegacyDASHDownloader {
	return &LegacyDASHDownloader{
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
		outputDir:  outputDir,
		userAgent:  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
		concurrent: 5,
	}
}

// DownloadMPD 下载 MPD 文件
func (d *LegacyDASHDownloader) DownloadMPD(mpdURL string) (*MPD, error) {
	req, err := http.NewRequest("GET", mpdURL, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("User-Agent", d.userAgent)

	resp, err := d.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var mpd MPD
	if err := xml.Unmarshal(body, &mpd); err != nil {
		return nil, err
	}

	return &mpd, nil
}

// ParseMPD 解析 MPD 提取格式信息
func (d *LegacyDASHDownloader) ParseMPD(mpd *MPD, baseURL string) []LegacyDASHFormat {
	formats := make([]LegacyDASHFormat, 0)

	for _, period := range mpd.Periods {
		for _, adaptation := range period.AdaptationSets {
			for _, rep := range adaptation.Representations {
				format := LegacyDASHFormat{
					ID:        rep.ID,
					Width:     rep.Width,
					Height:    rep.Height,
					Bandwidth: rep.Bandwidth,
					Codecs:    rep.Codecs,
					URLs:      make([]string, 0),
				}

				// 确定质量
				if rep.Height >= 2160 {
					format.Quality = "4K"
				} else if rep.Height >= 1440 {
					format.Quality = "2K"
				} else if rep.Height >= 1080 {
					format.Quality = "1080p"
				} else if rep.Height >= 720 {
					format.Quality = "720p"
				} else if rep.Height >= 480 {
					format.Quality = "480p"
				} else {
					format.Quality = "360p"
				}

				// 提取分段 URL
				if rep.SegmentList != nil {
					for _, seg := range rep.SegmentList.SegmentURLs {
						url := seg.Media
						if !strings.HasPrefix(url, "http") {
							url = baseURL + url
						}
						format.URLs = append(format.URLs, url)
					}
				}

				// 处理 SegmentTemplate
				if rep.SegmentTemplate != nil {
					// 动态 MPD 需要特殊处理
					fmt.Printf("注意：SegmentTemplate 需要动态生成 URL\n")
				}

				if len(format.URLs) > 0 {
					formats = append(formats, format)
				}
			}
		}
	}

	return formats
}

// DownloadDASH 下载 DASH 流
func (d *LegacyDASHDownloader) DownloadDASH(mpdURL, outputFile string) error {
	// 下载 MPD
	mpd, err := d.DownloadMPD(mpdURL)
	if err != nil {
		return fmt.Errorf("下载 MPD 失败：%v", err)
	}

	// 解析 MPD
	baseURL := mpdURL[:strings.LastIndex(mpdURL, "/")+1]
	formats := d.ParseMPD(mpd, baseURL)

	if len(formats) == 0 {
		return fmt.Errorf("未找到任何媒体流")
	}

	// 选择最佳视频和音频格式
	var bestVideo, bestAudio LegacyDASHFormat
	for _, format := range formats {
		if strings.Contains(format.Codecs, "avc") || strings.Contains(format.Codecs, "hevc") {
			if bestVideo.ID == "" || format.Bandwidth > bestVideo.Bandwidth {
				bestVideo = format
			}
		}
		if strings.Contains(format.Codecs, "mp4a") || strings.Contains(format.Codecs, "ac-3") {
			if bestAudio.ID == "" || format.Bandwidth > bestAudio.Bandwidth {
				bestAudio = format
			}
		}
	}

	fmt.Printf("选择视频格式：%s (%dx%d, %d kbps)\n", 
		bestVideo.Quality, bestVideo.Width, bestVideo.Height, bestVideo.Bandwidth/1000)
	
	if bestAudio.ID != "" {
		fmt.Printf("选择音频格式：%s (%d kbps)\n", bestAudio.Quality, bestAudio.Bandwidth/1000)
	}

	// 创建临时目录
	tempDir := filepath.Join(d.outputDir, "dash_temp")
	os.MkdirAll(tempDir, 0755)
	defer os.RemoveAll(tempDir)

	// 下载视频分段
	fmt.Println("正在下载视频分段...")
	videoFile := filepath.Join(tempDir, "video.mp4")
	if err := d.downloadSegments(bestVideo.URLs, videoFile); err != nil {
		return fmt.Errorf("下载视频失败：%v", err)
	}

	// 下载音频分段（如果有）
	audioFile := ""
	if bestAudio.ID != "" {
		fmt.Println("正在下载音频分段...")
		audioFile = filepath.Join(tempDir, "audio.mp4")
		if err := d.downloadSegments(bestAudio.URLs, audioFile); err != nil {
			return fmt.Errorf("下载音频失败：%v", err)
		}
	}

	// 合并音视频
	fmt.Println("正在合并音视频...")
	if audioFile != "" {
		ffmpeg := NewFFmpegWrapper("", d.outputDir)
		if ffmpegPath, err := AutoDetectFFmpeg(); err == nil {
			ffmpeg.FFmpegPath = ffmpegPath
			return ffmpeg.CombineAudioVideo(videoFile, audioFile, outputFile)
		}
		// 如果没有 ffmpeg，只保存视频
		os.Rename(videoFile, outputFile)
	} else {
		os.Rename(videoFile, outputFile)
	}

	return nil
}

// downloadSegments 下载分段
func (d *LegacyDASHDownloader) downloadSegments(urls []string, outputFile string) error {
	file, err := os.Create(outputFile)
	if err != nil {
		return err
	}
	defer file.Close()

	downloader := NewEnhancedDownloader(d.outputDir)
	downloader.SetConcurrent(d.concurrent)

	for i, url := range urls {
		tempFile := filepath.Join(d.outputDir, fmt.Sprintf("seg_%d.tmp", i))
		
		_, err := downloader.DownloadWithProgress(url, tempFile)
		if err != nil {
			return err
		}

		// 读取并写入
		data, err := os.ReadFile(tempFile)
		if err != nil {
			return err
		}
		file.Write(data)
		
		os.Remove(tempFile)
		
		fmt.Printf("\r进度：%d/%d", i+1, len(urls))
	}
	
	fmt.Println()
	return nil
}

// GetDASHInfo 获取 DASH 信息
func (d *LegacyDASHDownloader) GetDASHInfo(mpdURL string) (map[string]interface{}, error) {
	mpd, err := d.DownloadMPD(mpdURL)
	if err != nil {
		return nil, err
	}

	baseURL := mpdURL[:strings.LastIndex(mpdURL, "/")+1]
	formats := d.ParseMPD(mpd, baseURL)

	info := map[string]interface{}{
		"type": mpd.Type,
		"duration": mpd.MediaPres,
		"formats": formats,
		"total_formats": len(formats),
	}

	return info, nil
}

// SelectQuality 选择清晰度
func (d *LegacyDASHDownloader) SelectQuality(formats []LegacyDASHFormat, quality string) *LegacyDASHFormat {
	qualityMap := map[string]int{
		"4k": 2160,
		"2k": 1440,
		"1080p": 1080,
		"720p": 720,
		"480p": 480,
		"360p": 360,
	}

	targetHeight, ok := qualityMap[strings.ToLower(quality)]
	if !ok {
		targetHeight = 1080 // 默认 1080p
	}

	var best LegacyDASHFormat
	for _, format := range formats {
		if format.Height <= targetHeight {
			if best.ID == "" || format.Height > best.Height {
				best = format
			}
		}
	}

	return &best
}
