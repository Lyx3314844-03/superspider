package iqiyi

import (
	"fmt"
	"io"
	"net/http"
	"regexp"
	"strings"
	"time"
)

// IqiyiExtractor 爱奇艺视频解析器
type IqiyiExtractor struct {
	client    *http.Client
	userAgent string
	referer   string
}

type StreamInfo struct {
	Quality string `json:"quality"`
	M3U8URL string `json:"m3u8_url"`
	DASHURL string `json:"dash_url"`
}

// VideoInfo 爱奇艺视频信息
type VideoInfo struct {
	VideoID        string       `json:"video_id"`
	Title          string       `json:"title"`
	M3U8URL        string       `json:"m3u8_url"`
	DASHURL        string       `json:"dash_url"`
	CoverURL       string       `json:"cover_url"`
	Duration       int          `json:"duration"`
	QualityOptions []string     `json:"quality_options"`
	Streams        []StreamInfo `json:"streams"`
}

// NewIqiyiExtractor 创建爱奇艺视频解析器
func NewIqiyiExtractor() *IqiyiExtractor {
	return &IqiyiExtractor{
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
		userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
		referer:   "https://www.iqiyi.com/",
	}
}

// Extract 解析爱奇艺视频
func (e *IqiyiExtractor) Extract(pageURL string) (*VideoInfo, error) {
	videoID := e.extractVideoID(pageURL)
	if videoID == "" {
		return nil, fmt.Errorf("无法从 URL 提取爱奇艺视频 ID: %s", pageURL)
	}

	req, err := http.NewRequest(http.MethodGet, pageURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", e.userAgent)
	req.Header.Set("Referer", e.referer)

	resp, err := e.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	html := string(body)

	info := &VideoInfo{
		VideoID: videoID,
		Title:   e.extractTitle(html, videoID),
	}
	e.extractVideoData(html, info)
	return info, nil
}

func (e *IqiyiExtractor) extractVideoID(pageURL string) string {
	patterns := []string{
		`/v_([A-Za-z0-9]+)\.html`,
		`/play/([A-Za-z0-9]+)`,
		`curid=([^&]+)`,
	}

	for _, pattern := range patterns {
		if matches := regexp.MustCompile(pattern).FindStringSubmatch(pageURL); len(matches) >= 2 {
			return matches[1]
		}
	}
	return ""
}

func (e *IqiyiExtractor) extractTitle(html, videoID string) string {
	match := regexp.MustCompile(`<title>([^<]+)</title>`).FindStringSubmatch(html)
	if len(match) >= 2 {
		title := strings.TrimSpace(match[1])
		title = regexp.MustCompile(`\s*-?\s*爱奇艺.*$`).ReplaceAllString(title, "")
		if title != "" {
			return title
		}
	}
	return "IQIYI Video " + videoID
}

func (e *IqiyiExtractor) extractVideoData(html string, info *VideoInfo) {
	if matches := regexp.MustCompile(`(https?://[^"\s]+\.m3u8[^"\s]*)`).FindStringSubmatch(html); len(matches) >= 2 {
		info.M3U8URL = matches[1]
	}

	dashPatterns := []string{
		`"(?:dash|dash_url|dashUrl|mpd|mpd_url|mpdUrl)"\s*:\s*"(https?://[^"]+)"`,
		`(https?://[^"\s]+(?:\.mpd|/dash[^"\s]*)[^"\s]*)`,
	}
	for _, pattern := range dashPatterns {
		if matches := regexp.MustCompile(pattern).FindStringSubmatch(html); len(matches) >= 2 {
			info.DASHURL = strings.TrimSpace(matches[1])
			break
		}
	}

	if matches := regexp.MustCompile(`(?:property|name)=["']og:image["'][^>]+content=["']([^"']+)["']`).FindStringSubmatch(html); len(matches) >= 2 {
		info.CoverURL = matches[1]
	}

	if matches := regexp.MustCompile(`"duration"\s*:\s*(\d+)`).FindStringSubmatch(html); len(matches) >= 2 {
		fmt.Sscanf(matches[1], "%d", &info.Duration)
	}

	if matches := regexp.MustCompile(`"quality"\s*:\s*\[([^\]]+)\]`).FindStringSubmatch(html); len(matches) >= 2 {
		for _, quality := range strings.Split(matches[1], ",") {
			trimmed := strings.Trim(strings.TrimSpace(quality), `"`)
			if trimmed != "" {
				info.QualityOptions = append(info.QualityOptions, trimmed)
			}
		}
	}

	streams := e.extractStreamCandidates(html)
	if len(streams) > 0 {
		info.Streams = streams
		if info.M3U8URL == "" {
			for _, stream := range streams {
				if stream.M3U8URL != "" {
					info.M3U8URL = stream.M3U8URL
					break
				}
			}
		}
		if info.DASHURL == "" {
			for _, stream := range streams {
				if stream.DASHURL != "" {
					info.DASHURL = stream.DASHURL
					break
				}
			}
		}
		for _, stream := range streams {
			if stream.Quality == "" {
				continue
			}
			seen := false
			for _, existing := range info.QualityOptions {
				if existing == stream.Quality {
					seen = true
					break
				}
			}
			if !seen {
				info.QualityOptions = append(info.QualityOptions, stream.Quality)
			}
		}
	}
}

func (e *IqiyiExtractor) extractStreamCandidates(html string) []StreamInfo {
	qualities := regexp.MustCompile(`"quality"\s*:\s*"([^"]+)"`).FindAllStringSubmatch(html, -1)
	m3u8s := regexp.MustCompile(`"(?:m3u8|m3u8Url|hls(?:_url|Url)?)"\s*:\s*"(https?://[^"]+)"`).FindAllStringSubmatch(html, -1)
	dashes := regexp.MustCompile(`"(?:dash|dash_url|dashUrl|mpd(?:_url|Url)?)"\s*:\s*"(https?://[^"]+)"`).FindAllStringSubmatch(html, -1)

	maxLen := len(qualities)
	if len(m3u8s) > maxLen {
		maxLen = len(m3u8s)
	}
	if len(dashes) > maxLen {
		maxLen = len(dashes)
	}

	streams := make([]StreamInfo, 0, maxLen)
	for index := 0; index < maxLen; index++ {
		stream := StreamInfo{}
		if index < len(qualities) {
			stream.Quality = strings.TrimSpace(qualities[index][1])
		}
		if index < len(m3u8s) {
			stream.M3U8URL = strings.TrimSpace(m3u8s[index][1])
		}
		if index < len(dashes) {
			stream.DASHURL = strings.TrimSpace(dashes[index][1])
		}
		if stream.Quality != "" || stream.M3U8URL != "" || stream.DASHURL != "" {
			streams = append(streams, stream)
		}
	}
	return streams
}
