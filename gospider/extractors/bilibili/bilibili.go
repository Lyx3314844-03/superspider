package bilibili

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"strings"
	"time"
)

// BilibiliExtractor B 站视频解析器
type BilibiliExtractor struct {
	client    *http.Client
	userAgent string
	referer   string
	cookie    string
	quality   int // 32=480P, 64=720P, 80=1080P, 112=4K
}

// BilibiliVideoInfo B 站视频信息
type BilibiliVideoInfo struct {
	BVID        string           `json:"bvid"`
	CID         string           `json:"cid"`
	Title       string           `json:"title"`
	Desc        string           `json:"desc"`
	Duration    int              `json:"duration"`
	Thumbnail   string           `json:"thumbnail"`
	Owner       string           `json:"owner"`
	Video       *BilibiliStream  `json:"video"`
	Audio       *BilibiliStream  `json:"audio"`
	DASHURL     string           `json:"dash_url"`
}

// BilibiliStream B 站流媒体信息
type BilibiliStream struct {
	ID        int      `json:"id"`
	Quality   string   `json:"quality"`
	Codecs    string   `json:"codecs"`
	Bandwidth int      `json:"bandwidth"`
	URL       string   `json:"url"`
	URLs      []string `json:"urls"`
	BaseURL   string   `json:"base_url"`
}

// NewBilibiliExtractor 创建 B 站视频解析器
func NewBilibiliExtractor() *BilibiliExtractor {
	return &BilibiliExtractor{
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
		userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
		referer:   "https://www.bilibili.com",
		quality:   80, // 默认 1080P
	}
}

// SetCookie 设置 Cookie（用于大会员视频）
func (e *BilibiliExtractor) SetCookie(cookie string) {
	e.cookie = cookie
}

// SetQuality 设置清晰度
func (e *BilibiliExtractor) SetQuality(quality int) {
	e.quality = quality
}

// Extract 解析 B 站视频
func (e *BilibiliExtractor) Extract(pageURL string) (*BilibiliVideoInfo, error) {
	// 提取 BVID 和 CID
	bvid, cid, err := e.extractIDs(pageURL)
	if err != nil {
		return nil, err
	}

	// 获取视频信息
	info, err := e.getVideoInfo(bvid, cid)
	if err != nil {
		return nil, err
	}

	info.BVID = bvid
	info.CID = cid

	// 获取播放地址
	if err := e.getPlayURLs(info, bvid, cid); err != nil {
		return nil, err
	}

	return info, nil
}

// extractIDs 从 URL 提取 BVID 和 CID
func (e *BilibiliExtractor) extractIDs(pageURL string) (string, string, error) {
	var bvid, cid string

	// 提取 BVID: BV1xx411c7mD
	bvidRe := regexp.MustCompile(`(BV[A-Za-z0-9]+)`)
	matches := bvidRe.FindStringSubmatch(pageURL)
	if len(matches) >= 2 {
		bvid = matches[1]
	}

	// 提取 CID
	cidRe := regexp.MustCompile(`cid=(\d+)`)
	matches = cidRe.FindStringSubmatch(pageURL)
	if len(matches) >= 2 {
		cid = matches[1]
	}

	if bvid == "" {
		return "", "", fmt.Errorf("无法从 URL 提取 BVID: %s", pageURL)
	}

	// 如果没有 CID，尝试通过 API 获取
	if cid == "" {
		cid, _ = e.getCIDByBVID(bvid)
	}

	return bvid, cid, nil
}

// getCIDByBVID 通过 BVID 获取 CID
func (e *BilibiliExtractor) getCIDByBVID(bvid string) (string, error) {
	url := fmt.Sprintf("https://api.bilibili.com/x/web-interface/view?bvid=%s", bvid)
	
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", err
	}

	req.Header.Set("User-Agent", e.userAgent)
	req.Header.Set("Referer", e.referer)

	resp, err := e.client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	var resp_data struct {
		Code int `json:"code"`
		Data struct {
			CID int `json:"cid"`
		} `json:"data"`
	}

	if err := json.Unmarshal(body, &resp_data); err != nil {
		return "", err
	}

	if resp_data.Code != 0 {
		return "", fmt.Errorf("API 返回错误：%d", resp_data.Code)
	}

	return fmt.Sprintf("%d", resp_data.Data.CID), nil
}

// getVideoInfo 获取视频基本信息
func (e *BilibiliExtractor) getVideoInfo(bvid, cid string) (*BilibiliVideoInfo, error) {
	url := fmt.Sprintf("https://api.bilibili.com/x/web-interface/view?bvid=%s", bvid)
	
	req, err := http.NewRequest("GET", url, nil)
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

	var resp_data struct {
		Code int `json:"code"`
		Data struct {
			BVID       string `json:"bvid"`
			Title      string `json:"title"`
			Desc       string `json:"desc"`
			Duration   int    `json:"duration"`
			Pic        string `json:"pic"`
			Owner      struct {
				Name string `json:"name"`
			} `json:"owner"`
		} `json:"data"`
	}

	if err := json.Unmarshal(body, &resp_data); err != nil {
		return nil, err
	}

	if resp_data.Code != 0 {
		return nil, fmt.Errorf("API 返回错误：%d", resp_data.Code)
	}

	info := &BilibiliVideoInfo{
		Title:     resp_data.Data.Title,
		Desc:      resp_data.Data.Desc,
		Duration:  resp_data.Data.Duration,
		Thumbnail: resp_data.Data.Pic,
		Owner:     resp_data.Data.Owner.Name,
	}

	return info, nil
}

// getPlayURLs 获取播放地址
func (e *BilibiliExtractor) getPlayURLs(info *BilibiliVideoInfo, bvid, cid string) error {
	// 调用播放 API
	url := fmt.Sprintf("https://api.bilibili.com/x/player/playurl?bvid=%s&cid=%s&qn=%d&fnval=16&fnver=0&fourk=1", 
		bvid, cid, e.quality)
	
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}

	req.Header.Set("User-Agent", e.userAgent)
	req.Header.Set("Referer", e.referer)
	if e.cookie != "" {
		req.Header.Set("Cookie", e.cookie)
	}

	resp, err := e.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}

	var resp_data struct {
		Code int `json:"code"`
		Data struct {
			Quality   int    `json:"quality"`
			Format    string `json:"format"`
			Timelength int   `json:"timelength"`
			VideoCodecid int `json:"video_codecid"`
			DASH      struct {
				Duration     int     `json:"duration"`
				MinBufferTime float64 `json:"minBufferTime"`
				Video        []struct {
					ID        int    `json:"id"`
					BaseURL   string `json:"base_url"`
					Bandwidth int    `json:"bandwidth"`
					Codecs    string `json:"codecs"`
					Width     int    `json:"width"`
					Height    int    `json:"height"`
					FrameRate string `json:"frameRate"`
				} `json:"video"`
				Audio []struct {
					ID        int    `json:"id"`
					BaseURL   string `json:"base_url"`
					Bandwidth int    `json:"bandwidth"`
					Codecs    string `json:"codecs"`
				} `json:"audio"`
			} `json:"dash"`
			DURL []struct {
				URL  string `json:"url"`
				Size int64  `json:"size"`
			} `json:"durl"`
		} `json:"data"`
	}

	if err := json.Unmarshal(body, &resp_data); err != nil {
		return err
	}

	if resp_data.Code != 0 {
		return fmt.Errorf("播放 API 错误：%d", resp_data.Code)
	}

	// 提取视频流
	if len(resp_data.Data.DASH.Video) > 0 {
		videoStream := resp_data.Data.DASH.Video[0]
		info.Video = &BilibiliStream{
			ID:        videoStream.ID,
			Quality:   e.qualityToString(videoStream.ID),
			Codecs:    videoStream.Codecs,
			Bandwidth: videoStream.Bandwidth,
			BaseURL:   videoStream.BaseURL,
		}
	}

	// 提取音频流
	if len(resp_data.Data.DASH.Audio) > 0 {
		audioStream := resp_data.Data.DASH.Audio[0]
		info.Audio = &BilibiliStream{
			ID:        audioStream.ID,
			Quality:   "audio",
			Codecs:    audioStream.Codecs,
			Bandwidth: audioStream.Bandwidth,
			BaseURL:   audioStream.BaseURL,
		}
	}

	// 生成 DASH MPD URL（如果需要）
	if info.Video != nil {
		// B 站使用 DASH 协议，可以直接使用 base_url
		info.DASHURL = info.Video.BaseURL
	}

	// 备用：提取 DURL（旧格式，单文件）
	if len(resp_data.Data.DURL) > 0 && info.Video == nil {
		info.Video = &BilibiliStream{
			URL:  resp_data.Data.DURL[0].URL,
			URLs: make([]string, 0),
		}
		for _, durl := range resp_data.Data.DURL {
			info.Video.URLs = append(info.Video.URLs, durl.URL)
		}
	}

	return nil
}

// qualityToString 清晰度 ID 转字符串
func (e *BilibiliExtractor) qualityToString(quality int) string {
	qualityMap := map[int]string{
		6:   "240P",
		16:  "360P",
		32:  "480P",
		64:  "720P",
		74:  "720P60",
		80:  "1080P",
		112: "1080P+",
		116: "1080P60",
		120: "4K",
		125: "HDR",
		126: "杜比",
		127: "8K",
	}
	
	if name, ok := qualityMap[quality]; ok {
		return name
	}
	return fmt.Sprintf("Q%d", quality)
}

// DownloadBilibiliVideo 下载 B 站视频的便捷函数
func DownloadBilibiliVideo(videoURL, outputDir string) (*BilibiliVideoInfo, error) {
	extractor := NewBilibiliExtractor()
	
	fmt.Printf("解析 B 站视频：%s\n", videoURL)
	info, err := extractor.Extract(videoURL)
	if err != nil {
		return nil, err
	}

	fmt.Printf("视频标题：%s\n", info.Title)
	fmt.Printf("UP 主：%s\n", info.Owner)
	fmt.Printf("视频时长：%d 秒\n", info.Duration)

	if info.Video != nil {
		fmt.Printf("视频质量：%s (%s)\n", info.Video.Quality, info.Video.Codecs)
	}

	return info, nil
}

// GetVideoTitle 获取视频标题（快速）
func (e *BilibiliExtractor) GetVideoTitle(pageURL string) (string, error) {
	bvid, _, err := e.extractIDs(pageURL)
	if err != nil {
		return "", err
	}

	info, err := e.getVideoInfo(bvid, "")
	if err != nil {
		return "", err
	}

	return info.Title, nil
}

// GetAvailableQualities 获取可用清晰度列表
func (e *BilibiliExtractor) GetAvailableQualities() map[int]string {
	return map[int]string{
		6:   "240P 极速",
		16:  "360P 流畅",
		32:  "480P 清晰",
		64:  "720P 高清",
		74:  "720P60 高帧率",
		80:  "1080P 高清",
		112: "1080P+ 高码率",
		116: "1080P60 高帧率",
		120: "4K 超清",
		125: "HDR 真彩",
		126: "杜比视界",
		127: "8K 超高清",
	}
}

// ParseVideoURL 解析 B 站视频 URL 的便捷函数
func ParseVideoURL(pageURL string) (bvid string, cid string, err error) {
	// 提取 BVID
	bvidRe := regexp.MustCompile(`(BV[A-Za-z0-9]+)`)
	matches := bvidRe.FindStringSubmatch(pageURL)
	if len(matches) >= 2 {
		bvid = matches[1]
	}

	// 提取 CID
	cidRe := regexp.MustCompile(`cid=(\d+)`)
	matches = cidRe.FindStringSubmatch(pageURL)
	if len(matches) >= 2 {
		cid = matches[1]
	}

	if bvid == "" {
		return "", "", fmt.Errorf("无法从 URL 提取 BVID")
	}

	return bvid, cid, nil
}

// IsBilibiliURL 判断是否为 B 站 URL
func IsBilibiliURL(pageURL string) bool {
	return strings.Contains(pageURL, "bilibili.com") || 
		   strings.Contains(pageURL, "b23.tv")
}
