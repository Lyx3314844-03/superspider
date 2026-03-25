package youku

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"time"
)

// YoukuExtractor 优酷视频解析器
type YoukuExtractor struct {
	client    *http.Client
	userAgent string
	referer   string
	ckey      string // 授权密钥
}

// YoukuVideoInfo 优酷视频信息
type YoukuVideoInfo struct {
	VideoID     string         `json:"video_id"`
	Title       string         `json:"title"`
	Duration    int            `json:"duration"`
	Thumbnail   string         `json:"thumbnail"`
	Description string         `json:"description"`
	Streams     []YoukuStream  `json:"streams"`
	MPDURL      string         `json:"mpd_url"`
	M3U8URL     string         `json:"m3u8_url"`
}

// YoukuStream 优酷流媒体信息
type YoukuStream struct {
	StreamType   string     `json:"stream_type"` // hd2, fh, flv 等
	Quality      string     `json:"quality"`     // 1080P, 720P, 480P 等
	Width        int        `json:"width"`
	Height       int        `json:"height"`
	Size         int64      `json:"size"`
	DASHURL      string     `json:"dash_url"`
	HLSURL       string     `json:"hls_url"`
	SegmentURLs  []string   `json:"segment_urls"`
}

// NewYoukuExtractor 创建优酷视频解析器
func NewYoukuExtractor() *YoukuExtractor {
	return &YoukuExtractor{
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
		userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
		referer:   "https://v.youku.com/",
	}
}

// Extract 解析优酷视频
func (e *YoukuExtractor) Extract(pageURL string) (*YoukuVideoInfo, error) {
	// 提取视频 ID
	videoID, err := e.extractVideoID(pageURL)
	if err != nil {
		return nil, err
	}

	// 获取视频信息
	info, err := e.getVideoInfo(videoID)
	if err != nil {
		return nil, err
	}

	info.VideoID = videoID

	// 获取播放地址
	if err := e.getPlayURLs(info); err != nil {
		return nil, err
	}

	return info, nil
}

// extractVideoID 从 URL 提取视频 ID
func (e *YoukuExtractor) extractVideoID(pageURL string) (string, error) {
	// 格式：https://v.youku.com/v_show/id_XMTIzNDU2Nzg5MA==.html
	re := regexp.MustCompile(`/id_([A-Za-z0-9+=]+)`)
	matches := re.FindStringSubmatch(pageURL)
	
	if len(matches) < 2 {
		// 尝试从 iframe 或其他格式提取
		if strings.Contains(pageURL, "player.youku.com") {
			re = regexp.MustCompile(`embed/([A-Za-z0-9+=]+)`)
			matches = re.FindStringSubmatch(pageURL)
		}
	}

	if len(matches) < 2 {
		return "", fmt.Errorf("无法从 URL 提取视频 ID: %s", pageURL)
	}

	return matches[1], nil
}

// getVideoInfo 获取视频基本信息
func (e *YoukuExtractor) getVideoInfo(videoID string) (*YoukuVideoInfo, error) {
	// 获取视频详情页面
	pageURL := fmt.Sprintf("https://v.youku.com/v_show/id_%s.html", videoID)
	
	req, err := http.NewRequest("GET", pageURL, nil)
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

	info := &YoukuVideoInfo{}

	// 从页面提取视频信息
	info.Title = e.extractMetaTag(string(body), "videoTitle")
	info.Description = e.extractMetaTag(string(body), "videoDescription")
	info.Thumbnail = e.extractMetaTag(string(body), "thumbnail")

	// 提取 duration
	durationRe := regexp.MustCompile(`"seconds":\s*(\d+)`)
	matches := durationRe.FindStringSubmatch(string(body))
	if len(matches) >= 2 {
		fmt.Sscanf(matches[1], "%d", &info.Duration)
	}

	return info, nil
}

// extractMetaTag 提取 meta 标签内容
func (e *YoukuExtractor) extractMetaTag(html, name string) string {
	re := regexp.MustCompile(fmt.Sprintf(`<meta[^>]+name=["']%s["'][^>]+content=["']([^"']+)["']`, name))
	matches := re.FindStringSubmatch(html)
	if len(matches) >= 2 {
		return matches[1]
	}
	
	// 尝试 itemprop 格式
	re = regexp.MustCompile(fmt.Sprintf(`<meta[^>]+itemprop=["']%s["'][^>]+content=["']([^"']+)["']`, name))
	matches = re.FindStringSubmatch(html)
	if len(matches) >= 2 {
		return matches[1]
	}
	
	return ""
}

// getPlayURLs 获取播放地址
func (e *YoukuExtractor) getPlayURLs(info *YoukuVideoInfo) error {
	// 优酷使用 DASH 协议，需要获取 MPD 地址
	// 这里模拟获取播放地址的过程
	
	// 注意：实际使用中需要调用优酷的 UPS API 获取真实播放地址
	// 需要 ckey 授权，这里仅提供框架
	
	// 构建 UPS API 请求
	upsURL := "https://ups.youku.com/ups/get.json"
	params := url.Values{}
	params.Set("vid", info.VideoID)
	params.Set("ccode", "0502")
	params.Set("client_ip", "192.168.1.1")
	params.Set("utid", generateUTID())
	params.Set("cna", generateCNA())
	
	if e.ckey != "" {
		params.Set("ckey", e.ckey)
	}

	req, err := http.NewRequest("GET", upsURL+"?"+params.Encode(), nil)
	if err != nil {
		return err
	}

	req.Header.Set("User-Agent", e.userAgent)
	req.Header.Set("Referer", e.referer)

	resp, err := e.client.Do(req)
	if err != nil {
		// UPS API 可能需要授权，返回错误信息
		info.MPDURL = ""
		info.M3U8URL = ""
		return fmt.Errorf("获取播放地址失败：%v (可能需要 VIP 授权)", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}

	// 解析 UPS API 响应
	var upsResp UPSResponse
	if err := json.Unmarshal(body, &upsResp); err != nil {
		return err
	}

	if upsResp.Data.Error != nil {
		return fmt.Errorf("UPS API 错误：%s", upsResp.Data.Error.Note)
	}

	// 提取流媒体信息
	for _, stream := range upsResp.Data.Streams {
		youkuStream := YoukuStream{
			StreamType: stream.StreamType,
			Quality:    stream.Quality,
			Width:      stream.Width,
			Height:     stream.Height,
			Size:       stream.Size,
		}

		// 提取 DASH URL
		if stream.DASHURL != "" {
			youkuStream.DASHURL = stream.DASHURL
			if info.MPDURL == "" {
				info.MPDURL = stream.DASHURL
			}
		}

		// 提取 HLS URL
		if stream.HLSURL != "" {
			youkuStream.HLSURL = stream.HLSURL
			if info.M3U8URL == "" {
				info.M3U8URL = stream.HLSURL
			}
		}

		info.Streams = append(info.Streams, youkuStream)
	}

	return nil
}

// SetCKey 设置授权密钥
func (e *YoukuExtractor) SetCKey(ckey string) {
	e.ckey = ckey
}

// UPSResponse UPS API 响应
type UPSResponse struct {
	Data struct {
		Error  *struct {
			Code int    `json:"code"`
			Note string `json:"note"`
		} `json:"error"`
		Streams []struct {
			StreamType string `json:"stream_type"`
			Quality    string `json:"quality"`
			Width      int    `json:"width"`
			Height     int    `json:"height"`
			Size       int64  `json:"size"`
			DASHURL    string `json:"dash_url"`
			HLSURL     string `json:"hls_url"`
		} `json:"streams"`
		Video struct {
			Title       string `json:"title"`
			Duration    int    `json:"duration"`
			Thumbnail   string `json:"thumbnail"`
			Description string `json:"description"`
		} `json:"video"`
	} `json:"data"`
}

// generateUTID 生成 UTID
func generateUTID() string {
	// 简化实现，实际需要根据优酷的算法生成
	return fmt.Sprintf("utid_%d", time.Now().Unix())
}

// generateCNA 生成 CNA Cookie
func generateCNA() string {
	// 简化实现
	return "cna_dummy_value"
}

// DownloadYoukuVideo 下载优酷视频的便捷函数
func DownloadYoukuVideo(videoURL, outputDir string) (*YoukuVideoInfo, error) {
	extractor := NewYoukuExtractor()
	
	fmt.Printf("解析优酷视频：%s\n", videoURL)
	info, err := extractor.Extract(videoURL)
	if err != nil {
		return nil, err
	}

	fmt.Printf("视频标题：%s\n", info.Title)
	fmt.Printf("视频时长：%d 秒\n", info.Duration)
	fmt.Printf("可用清晰度：%d 种\n", len(info.Streams))

	for _, stream := range info.Streams {
		fmt.Printf("  - %s (%dx%d)\n", stream.Quality, stream.Width, stream.Height)
	}

	return info, nil
}
