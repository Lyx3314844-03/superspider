package enhanced

import (
	"bufio"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"
)

// VideoItem 视频数据项
type VideoItem struct {
	Index       int    `json:"index"`
	Title       string `json:"title"`
	Duration    string `json:"duration"`
	Channel     string `json:"channel"`
	URL         string `json:"url"`
	Thumbnail   string `json:"thumbnail"`
	Views       string `json:"views"`
	Published   string `json:"published"`
	Description string `json:"description"`
}

// ToMap 转换为 map
func (v *VideoItem) ToMap() map[string]interface{} {
	return map[string]interface{}{
		"index":       v.Index,
		"title":       v.Title,
		"duration":    v.Duration,
		"channel":     v.Channel,
		"url":         v.URL,
		"thumbnail":   v.Thumbnail,
		"views":       v.Views,
		"published":   v.Published,
		"description": v.Description,
	}
}

// CrawlStats 爬取统计信息
type CrawlStats struct {
	TotalVideos   int    `json:"total_videos"`
	UniqueChannels int   `json:"unique_channels"`
	CrawlTime     int64  `json:"crawl_time"`
	StartTime     string `json:"start_time"`
	EndTime       string `json:"end_time"`
	TotalDuration string `json:"total_duration"`
}

// YouTubeSpiderBase 增强型 YouTube 爬虫基类
type YouTubeSpiderBase struct {
	Name         string
	Platform     string
	PlaylistURL  string
	Videos       []*VideoItem
	Stats        *CrawlStats
	Settings     map[string]interface{}
	startTime    time.Time
	endTime      time.Time
}

// NewYouTubeSpiderBase 创建爬虫基类
func NewYouTubeSpiderBase(playlistURL string, settings map[string]interface{}) *YouTubeSpiderBase {
	return &YouTubeSpiderBase{
		Name:        "youtube_spider",
		Platform:    "Go",
		PlaylistURL: playlistURL,
		Videos:      make([]*VideoItem, 0),
		Stats:       &CrawlStats{},
		Settings:    settings,
	}
}

// Start 启动爬虫（模板方法）
func (s *YouTubeSpiderBase) Start() []*VideoItem {
	s.beforeStart()

	defer func() {
		if r := recover(); r != nil {
			s.onError(fmt.Errorf("%v", r))
		}
	}()

	if err := s.initialize(); err != nil {
		s.onError(err)
		return s.Videos
	}

	if err := s.navigate(); err != nil {
		s.onError(err)
		return s.Videos
	}

	if err := s.waitAndScroll(); err != nil {
		s.onError(err)
		return s.Videos
	}

	if err := s.extractContent(); err != nil {
		s.onError(err)
		return s.Videos
	}

	if err := s.parseVideos(); err != nil {
		s.onError(err)
		return s.Videos
	}

	s.afterExtract()
	s.calculateStats()
	s.printResults()

	return s.Videos
}

func (s *YouTubeSpiderBase) beforeStart() {
	s.startTime = time.Now()
	s.Stats.StartTime = s.startTime.Format("2006-01-02 15:04:05")
	s.printHeader()
}

func (s *YouTubeSpiderBase) printHeader() {
	fmt.Println("\n" + strings.Repeat("╔", 30))
	fmt.Println(strings.Repeat("║", 10) + fmt.Sprintf(" %s - YouTube 爬虫 ", s.Platform) + strings.Repeat("║", 10))
	fmt.Println(strings.Repeat("╚", 30))
	fmt.Printf("\n📺 播放列表：%s\n\n", s.PlaylistURL)
}

// Initialize 初始化（子类实现）
func (s *YouTubeSpiderBase) initialize() error {
	return nil
}

// Navigate 导航到页面（子类实现）
func (s *YouTubeSpiderBase) navigate() error {
	return nil
}

// WaitAndScroll 等待和滚动（子类实现）
func (s *YouTubeSpiderBase) waitAndScroll() error {
	return nil
}

// ExtractContent 提取内容（子类实现）
func (s *YouTubeSpiderBase) extractContent() error {
	return nil
}

// ParseVideos 解析视频（子类实现）
func (s *YouTubeSpiderBase) parseVideos() error {
	return nil
}

func (s *YouTubeSpiderBase) afterExtract() {
	s.endTime = time.Now()
	s.Stats.EndTime = s.endTime.Format("2006-01-02 15:04:05")
	s.Stats.CrawlTime = int64(s.endTime.Sub(s.startTime).Seconds())
}

func (s *YouTubeSpiderBase) calculateStats() {
	s.Stats.TotalVideos = len(s.Videos)
	channelSet := make(map[string]bool)
	for _, video := range s.Videos {
		if video.Channel != "" {
			channelSet[video.Channel] = true
		}
	}
	s.Stats.UniqueChannels = len(channelSet)
}

func (s *YouTubeSpiderBase) printResults() {
	fmt.Println("\n" + strings.Repeat("═", 60))
	fmt.Println(strings.Repeat(" ", 20) + "爬取结果")
	fmt.Println(strings.Repeat("═", 60))
	fmt.Printf("共找到 %d 个视频\n", s.Stats.TotalVideos)
	fmt.Printf("唯一频道数：%d\n", s.Stats.UniqueChannels)
	fmt.Printf("爬取耗时：%.2f 秒\n", float64(s.Stats.CrawlTime))
	fmt.Println("\n前 20 个视频:")

	for i, video := range s.Videos {
		if i >= 20 {
			break
		}
		fmt.Printf("\n%2d. %s\n", i+1, video.Title)
		if video.Duration != "" {
			fmt.Printf("    ⏱️  时长：%s\n", video.Duration)
		}
		if video.Channel != "" {
			fmt.Printf("    👤  频道：%s\n", video.Channel)
		}
	}

	if len(s.Videos) > 20 {
		fmt.Printf("\n... 还有 %d 个视频\n", len(s.Videos)-20)
	}
}

func (s *YouTubeSpiderBase) onError(err error) {
	fmt.Printf("\n❌ 爬取失败：%v\n", err)
}

func (s *YouTubeSpiderBase) cleanup() {
	// 清理资源
}

// SaveToFile 保存到文件
func (s *YouTubeSpiderBase) SaveToFile(filename, format string) (string, error) {
	if filename == "" {
		timestamp := time.Now().Format("20060102_150405")
		filename = fmt.Sprintf("youtube_playlist_%s.%s", timestamp, format)
	}

	var err error
	switch strings.ToLower(format) {
	case "json":
		err = s.saveJSON(filename)
	case "txt":
		err = s.saveTxt(filename)
	case "csv":
		err = s.saveCSV(filename)
	default:
		return "", fmt.Errorf("不支持的格式：%s", format)
	}

	if err != nil {
		return "", err
	}

	fmt.Printf("💾 结果已保存到：%s\n", filename)
	return filename, nil
}

func (s *YouTubeSpiderBase) saveJSON(filename string) error {
	data := map[string]interface{}{
		"playlist_url": s.PlaylistURL,
		"crawl_stats":  s.Stats,
		"videos":       s.Videos,
	}

	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	encoder.SetEscapeHTML(false)
	return encoder.Encode(data)
}

func (s *YouTubeSpiderBase) saveTxt(filename string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := bufio.NewWriter(file)
	defer writer.Flush()

	fmt.Fprintln(writer, "YouTube 播放列表视频列表")
	fmt.Fprintln(writer, strings.Repeat("═", 60))
	fmt.Fprintln(writer)
	fmt.Fprintf(writer, "播放列表 URL: %s\n", s.PlaylistURL)
	fmt.Fprintf(writer, "爬取时间：%s\n", s.Stats.StartTime)
	fmt.Fprintf(writer, "视频总数：%d\n", s.Stats.TotalVideos)
	fmt.Fprintf(writer, "唯一频道数：%d\n", s.Stats.UniqueChannels)
	fmt.Fprintf(writer, "爬取耗时：%.2f 秒\n\n", float64(s.Stats.CrawlTime))
	fmt.Fprintln(writer, strings.Repeat("═", 60))
	fmt.Fprintln(writer)

	for i, video := range s.Videos {
		fmt.Fprintf(writer, "%d. %s\n", i+1, video.Title)
		if video.Duration != "" {
			fmt.Fprintf(writer, "   时长：%s\n", video.Duration)
		}
		if video.Channel != "" {
			fmt.Fprintf(writer, "   频道：%s\n", video.Channel)
		}
		if video.URL != "" {
			fmt.Fprintf(writer, "   链接：%s\n", video.URL)
		}
		fmt.Fprintln(writer)
	}

	return nil
}

func (s *YouTubeSpiderBase) saveCSV(filename string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// 写入表头
	headers := []string{"index", "title", "duration", "channel", "url", "thumbnail", "views", "published"}
	if err := writer.Write(headers); err != nil {
		return err
	}

	// 写入数据
	for i, video := range s.Videos {
		record := []string{
			strconv.Itoa(i + 1),
			video.Title,
			video.Duration,
			video.Channel,
			video.URL,
			video.Thumbnail,
			video.Views,
			video.Published,
		}
		if err := writer.Write(record); err != nil {
			return err
		}
	}

	return nil
}

// 工具函数

// ParseDurationToSeconds 将时长字符串转换为秒
func ParseDurationToSeconds(duration string) int {
	if duration == "" {
		return 0
	}

	parts := strings.Split(duration, ":")
	seconds := 0

	switch len(parts) {
	case 1:
		seconds, _ = strconv.Atoi(parts[0])
	case 2:
		minutes, _ := strconv.Atoi(parts[0])
		secs, _ := strconv.Atoi(parts[1])
		seconds = minutes*60 + secs
	case 3:
		hours, _ := strconv.Atoi(parts[0])
		minutes, _ := strconv.Atoi(parts[1])
		secs, _ := strconv.Atoi(parts[2])
		seconds = hours*3600 + minutes*60 + secs
	}

	return seconds
}

// FormatSecondsToDuration 将秒转换为时长字符串
func FormatSecondsToDuration(seconds int) string {
	if seconds < 60 {
		return fmt.Sprintf("%d秒", seconds)
	} else if seconds < 3600 {
		minutes := seconds / 60
		secs := seconds % 60
		return fmt.Sprintf("%d分%d秒", minutes, secs)
	} else {
		hours := seconds / 3600
		minutes := (seconds % 3600) / 60
		secs := seconds % 60
		return fmt.Sprintf("%d小时%d分%d秒", hours, minutes, secs)
	}
}

// ExtractVideoID 从 URL 提取视频 ID
func ExtractVideoID(url string) string {
	patterns := []string{
		`v=([a-zA-Z0-9_-]+)`,
		`youtu\.be/([a-zA-Z0-9_-]+)`,
		`embed/([a-zA-Z0-9_-]+)`,
	}

	for _, pattern := range patterns {
		re := regexp.MustCompile(pattern)
		matches := re.FindStringSubmatch(url)
		if len(matches) > 1 {
			return matches[1]
		}
	}

	return ""
}

// BuildYouTubeURL 构建 YouTube URL
func BuildYouTubeURL(videoID, playlistID string, index int) string {
	base := fmt.Sprintf("https://www.youtube.com/watch?v=%s", videoID)

	if playlistID != "" {
		base += fmt.Sprintf("&list=%s", playlistID)
	}
	if index > 0 {
		base += fmt.Sprintf("&index=%d", index)
	}

	return base
}
