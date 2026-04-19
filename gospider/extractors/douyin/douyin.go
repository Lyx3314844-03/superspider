package douyin

import (
	"fmt"
	"io"
	"net/http"
	"regexp"
	"strings"
	"time"
)

type VideoInfo struct {
	URL         string   `json:"url"`
	VideoID     string   `json:"video_id"`
	Platform    string   `json:"platform"`
	Title       string   `json:"title"`
	Description string   `json:"description"`
	CoverURL    string   `json:"cover_url"`
	Duration    int      `json:"duration"`
	Formats     []string `json:"formats"`
}

type Extractor struct {
	client *http.Client
}

func NewExtractor() *Extractor {
	return &Extractor{client: &http.Client{Timeout: 30 * time.Second}}
}

func (e *Extractor) Supports(url string) bool {
	return strings.Contains(strings.ToLower(url), "douyin.com")
}

func (e *Extractor) Extract(pageURL string) (*VideoInfo, error) {
	videoID := ExtractVideoID(pageURL)
	if videoID == "" {
		return nil, fmt.Errorf("invalid Douyin URL")
	}
	req, err := http.NewRequest(http.MethodGet, pageURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
	req.Header.Set("Referer", "https://www.douyin.com/")
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
		URL:         pageURL,
		VideoID:     videoID,
		Platform:    "Douyin",
		Title:       firstMatch(html, `<title[^>]*>([^<]+)</title>`, `"title"\s*:\s*"([^"]+)"`, `"desc"\s*:\s*"([^"]+)"`),
		Description: firstMatch(html, `"desc"\s*:\s*"([^"]+)"`, `"description"\s*:\s*"([^"]+)"`),
		CoverURL:    normalizeEscaped(firstMatch(html, `"dynamic_cover"\s*:\s*"([^"]+)"`, `"originCover"\s*:\s*"([^"]+)"`, `"cover"\s*:\s*"([^"]+)"`)),
	}
	if info.Title == "" {
		info.Title = "Douyin Video " + videoID
	}
	if duration := firstMatch(html, `"duration"\s*:\s*(\d+)`); duration != "" {
		fmt.Sscanf(duration, "%d", &info.Duration)
	}
	for _, candidate := range []string{
		normalizeEscaped(firstMatch(html, `"playAddr"\s*:\s*"([^"]+)"`, `"playUrl"\s*:\s*"([^"]+)"`)),
		normalizeEscaped(firstMatch(html, `"downloadAddr"\s*:\s*"([^"]+)"`, `"download_url"\s*:\s*"([^"]+)"`)),
	} {
		if candidate != "" && !contains(info.Formats, candidate) {
			info.Formats = append(info.Formats, candidate)
		}
	}
	return info, nil
}

func ExtractVideoID(pageURL string) string {
	for _, pattern := range []string{`/video/(\d+)`, `modal_id=(\d+)`} {
		if value := firstMatch(pageURL, pattern); value != "" {
			return value
		}
	}
	return ""
}

func firstMatch(text string, patterns ...string) string {
	for _, pattern := range patterns {
		re := regexp.MustCompile(pattern)
		matches := re.FindStringSubmatch(text)
		if len(matches) > 1 {
			return matches[1]
		}
	}
	return ""
}

func normalizeEscaped(value string) string {
	return strings.NewReplacer(`\/`, "/", `\u002F`, "/", `\u003A`, ":").Replace(strings.TrimSpace(value))
}

func contains(items []string, candidate string) bool {
	for _, item := range items {
		if item == candidate {
			return true
		}
	}
	return false
}
