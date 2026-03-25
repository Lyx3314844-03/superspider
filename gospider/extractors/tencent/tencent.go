package tencent

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"strings"
	"time"
)

// TencentExtractor 腾讯视频解析器
type TencentExtractor struct {
	client    *http.Client
	userAgent string
}

// VideoInfo 视频信息
type VideoInfo struct {
	Title       string       `json:"title"`
	Duration    int          `json:"duration"`
	CoverURL    string       `json:"cover_url"`
	Description string       `json:"description"`
	Formats     []VideoFormat `json:"formats"`
}

// VideoFormat 视频格式
type VideoFormat struct {
	Quality   string `json:"quality"`
	QualityID int    `json:"quality_id"`
	URL       string `json:"url"`
	Size      int64  `json:"size"`
}

// NewTencentExtractor 创建腾讯视频解析器
func NewTencentExtractor() *TencentExtractor {
	return &TencentExtractor{
		client: &http.Client{
			Timeout: 60 * time.Second,
			Transport: &http.Transport{
				MaxIdleConns:        100,
				MaxIdleConnsPerHost: 10,
				IdleConnTimeout:     90 * time.Second,
			},
		},
		userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	}
}

// Extract 提取视频信息
func (t *TencentExtractor) Extract(url string) (*VideoInfo, error) {
	// 从 URL 提取视频 ID
	videoID := t.extractVideoID(url)
	if videoID == "" {
		return nil, fmt.Errorf("无法从 URL 提取视频 ID")
	}

	fmt.Printf("视频 ID: %s\n", videoID)

	// 获取视频信息
	return t.getVideoInfo(videoID)
}

// extractVideoID 从 URL 提取视频 ID
func (t *TencentExtractor) extractVideoID(url string) string {
	// 匹配模式：/x/cover/{cover_id}/{video_id}.html
	re := regexp.MustCompile(`/x/cover/[^/]+/([a-zA-Z0-9]+)\.html`)
	matches := re.FindStringSubmatch(url)
	if len(matches) > 1 {
		return matches[1]
	}

	// 匹配模式：/x/page/{video_id}.html
	re2 := regexp.MustCompile(`/x/page/([a-zA-Z0-9]+)\.html`)
	matches2 := re2.FindStringSubmatch(url)
	if len(matches2) > 1 {
		return matches2[1]
	}

	return ""
}

// getVideoInfo 获取视频信息
func (t *TencentExtractor) getVideoInfo(videoID string) (*VideoInfo, error) {
	// 构造 API URL
	apiURL := fmt.Sprintf("https://vv.video.qq.com/getinfo?otype=json&appver=3.2.19.333&platform=11&defnpayver=1&defn=shd&vid=%s", videoID)

	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("User-Agent", t.userAgent)
	req.Header.Set("Referer", "https://v.qq.com/")

	resp, err := t.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	// 解析 JSONP 响应
	jsonStr := string(body)
	
	// 移除 JSONP 包装
	if idx := strings.Index(jsonStr, "("); idx != -1 {
		jsonStr = jsonStr[idx+1:]
	}
	if idx := strings.LastIndex(jsonStr, ")"); idx != -1 {
		jsonStr = jsonStr[:idx]
	}

	// 解析 JSON
	var result map[string]interface{}
	if err := json.Unmarshal([]byte(jsonStr), &result); err != nil {
		return nil, err
	}

	// 提取视频信息
	info := &VideoInfo{}

	if v, ok := result["title"]; ok {
		info.Title = v.(string)
	}

	if v, ok := result["desc"]; ok {
		info.Description = v.(string)
	}

	// 提取视频 URL
	if vl, ok := result["vl"]; ok {
		vlMap := vl.(map[string]interface{})
		
		if vi, ok := vlMap["vi"]; ok {
			viList := vi.([]interface{})
			if len(viList) > 0 {
				viMap := viList[0].(map[string]interface{})
				
				// 获取 ul (URL 列表)
				if ul, ok := result["ul"]; ok {
					ulMap := ul.(map[string]interface{})
					if ui, ok := ulMap["ui"]; ok {
						uiList := ui.([]interface{})
						if len(uiList) > 0 {
							uiMap := uiList[0].(map[string]interface{})
							if url, ok := uiMap["url"]; ok {
								baseURL := url.(string)
								
								// 获取 fvkey
								fvkey := ""
								if fv, ok := result["fvkey"]; ok {
									fvkey = fv.(string)
								}
								
								// 构造完整 URL
								if fn, ok := viMap["fn"]; ok {
									filename := fn.(string)
									if fvkey != "" {
										info.Formats = append(info.Formats, VideoFormat{
											Quality: "shd",
											URL:     fmt.Sprintf("%s%s?vkey=%s", baseURL, filename, fvkey),
										})
									}
								}
							}
						}
					}
				}
			}
		}
	}

	return info, nil
}

// GetDownloadURL 获取下载链接
func (t *TencentExtractor) GetDownloadURL(url string) (string, error) {
	info, err := t.Extract(url)
	if err != nil {
		return "", err
	}

	if len(info.Formats) > 0 {
		return info.Formats[0].URL, nil
	}

	return "", fmt.Errorf("未找到下载链接")
}
