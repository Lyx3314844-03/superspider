package media

import (
	"encoding/json"
	"fmt"
	"html"
	"io"
	"net/http"
	neturl "net/url"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

// MultiPlatformDownloader downloads from multiple platforms
type MultiPlatformDownloader struct {
	OutputDir string
	Client    *http.Client
}

type UniversalVideoInfo struct {
	PageURL       string
	Platform      string
	Title         string
	Description   string
	CoverURL      string
	HLSURL        string
	DASHURL       string
	MP4URL        string
	DownloadURL   string
	CandidateURLs []string
}

// NewMultiPlatformDownloader creates a new downloader
func NewMultiPlatformDownloader(outputDir string) *MultiPlatformDownloader {
	if outputDir == "" {
		outputDir = "downloads"
	}
	os.MkdirAll(outputDir, 0755)
	return &MultiPlatformDownloader{
		OutputDir: outputDir,
		Client: &http.Client{
			Timeout: 60 * time.Second,
		},
	}
}

// DetectPlatform detects the platform from URL
func (d *MultiPlatformDownloader) DetectPlatform(url string) string {
	lower := strings.ToLower(url)
	if strings.Contains(lower, "youtube.com") || strings.Contains(lower, "youtu.be") {
		return "youtube"
	}
	if strings.Contains(lower, "tiktok.com") {
		return "tiktok"
	}
	if strings.Contains(lower, "instagram.com") {
		return "instagram"
	}
	if strings.Contains(lower, "twitter.com") || strings.Contains(lower, "x.com") {
		return "twitter"
	}
	if strings.Contains(lower, "bilibili.com") || strings.Contains(lower, "b23.tv") {
		return "bilibili"
	}
	return "generic"
}

// Download downloads media from URL
func (d *MultiPlatformDownloader) Download(url, quality string) (string, error) {
	platform := d.DetectPlatform(url)

	switch platform {
	case "youtube":
		return d.downloadYouTube(url, quality)
	case "tiktok":
		return d.downloadTikTok(url, quality)
	case "bilibili":
		return d.downloadBilibili(url, quality)
	default:
		return d.downloadGeneric(url)
	}
}

func cleanMediaText(value string) string {
	return strings.Join(strings.Fields(html.UnescapeString(value)), " ")
}

func normalizeMediaURL(pageURL, candidate string) string {
	value := strings.TrimSpace(
		strings.NewReplacer(`\/`, "/", `\u002F`, "/", `\u003A`, ":").Replace(
			html.UnescapeString(candidate),
		),
	)
	if value == "" || strings.HasPrefix(value, "data:") || strings.HasPrefix(value, "javascript:") {
		return ""
	}
	if strings.HasPrefix(value, "//") {
		if parsed, err := neturl.Parse(pageURL); err == nil && parsed.Scheme != "" {
			return parsed.Scheme + ":" + value
		}
		return "https:" + value
	}
	if parsed, err := neturl.Parse(value); err == nil && parsed.IsAbs() {
		return parsed.String()
	}
	base, err := neturl.Parse(pageURL)
	if err != nil {
		return value
	}
	resolved, err := base.Parse(value)
	if err != nil {
		return value
	}
	return resolved.String()
}

func classifyGenericMediaURL(raw string) string {
	lower := strings.ToLower(raw)
	switch {
	case strings.Contains(lower, ".m3u8"):
		return "hls"
	case strings.Contains(lower, ".mpd"), strings.Contains(lower, "dash"):
		return "dash"
	case strings.Contains(lower, ".mp4"), strings.Contains(lower, ".webm"), strings.Contains(lower, ".m4v"), strings.Contains(lower, ".mov"):
		return "mp4"
	default:
		return "download"
	}
}

func isMediaURL(raw string) bool {
	switch classifyGenericMediaURL(raw) {
	case "hls", "dash", "mp4":
		return true
	default:
		return false
	}
}

func appendCandidate(info *UniversalVideoInfo, candidate string) {
	if candidate == "" {
		return
	}
	for _, existing := range info.CandidateURLs {
		if existing == candidate {
			return
		}
	}
	info.CandidateURLs = append(info.CandidateURLs, candidate)
	switch classifyGenericMediaURL(candidate) {
	case "hls":
		if info.HLSURL == "" {
			info.HLSURL = candidate
		}
	case "dash":
		if info.DASHURL == "" {
			info.DASHURL = candidate
		}
	case "mp4":
		if info.MP4URL == "" {
			info.MP4URL = candidate
		}
	default:
		if info.DownloadURL == "" {
			info.DownloadURL = candidate
		}
	}
}

func (d *MultiPlatformDownloader) DiscoverVideoInfo(pageURL string) (*UniversalVideoInfo, error) {
	if normalized := normalizeMediaURL(pageURL, pageURL); normalized != "" && isMediaURL(normalized) {
		info := &UniversalVideoInfo{
			PageURL:  pageURL,
			Platform: "generic",
			Title:    "Unknown Video",
		}
		appendCandidate(info, normalized)
		return info, nil
	}

	resp, err := d.Client.Get(pageURL)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	return discoverVideoInfoFromHTML(pageURL, string(body)), nil
}

func discoverVideoInfoFromHTML(pageURL, htmlBody string) *UniversalVideoInfo {
	info := &UniversalVideoInfo{
		PageURL:  pageURL,
		Platform: "generic",
	}

	titlePatterns := []string{
		`(?is)<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']+)["']`,
		`(?is)<meta[^>]+name=["']twitter:title["'][^>]+content=["']([^"']+)["']`,
		`(?is)<title>([^<]+)</title>`,
	}
	for _, pattern := range titlePatterns {
		if match := regexp.MustCompile(pattern).FindStringSubmatch(htmlBody); len(match) > 1 {
			info.Title = cleanMediaText(match[1])
			if info.Title != "" {
				break
			}
		}
	}
	if info.Title == "" {
		info.Title = "Unknown Video"
	}

	descriptionPatterns := []string{
		`(?is)<meta[^>]+property=["']og:description["'][^>]+content=["']([^"']+)["']`,
		`(?is)<meta[^>]+name=["']description["'][^>]+content=["']([^"']+)["']`,
	}
	for _, pattern := range descriptionPatterns {
		if match := regexp.MustCompile(pattern).FindStringSubmatch(htmlBody); len(match) > 1 {
			info.Description = cleanMediaText(match[1])
			if info.Description != "" {
				break
			}
		}
	}

	coverPatterns := []string{
		`(?is)<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']`,
		`(?is)<meta[^>]+name=["']twitter:image["'][^>]+content=["']([^"']+)["']`,
		`(?is)<video[^>]+poster=["']([^"']+)["']`,
	}
	for _, pattern := range coverPatterns {
		if match := regexp.MustCompile(pattern).FindStringSubmatch(htmlBody); len(match) > 1 {
			info.CoverURL = normalizeMediaURL(pageURL, match[1])
			if info.CoverURL != "" {
				break
			}
		}
	}

	urlPatterns := []string{
		`(?is)<meta[^>]+(?:property|name)=["'](?:og:video(?::url)?|twitter:player:stream)["'][^>]+content=["']([^"']+)["']`,
		`(?is)<video[^>]+src=["']([^"']+)["']`,
		`(?is)<source[^>]+src=["']([^"']+)["']`,
		`(?is)\b(?:contentUrl|embedUrl|videoUrl|video_url|playAddr|play_url|m3u8Url|m3u8_url|dashUrl|dash_url|mp4Url|mp4_url)\b["']?\s*[:=]\s*["']([^"']+)["']`,
		`(https?://[^"'\\s<>]+(?:\\.m3u8|\\.mpd|\\.mp4|\\.webm|\\.m4v|\\.mov)[^"'\\s<>]*)`,
	}
	for _, pattern := range urlPatterns {
		re := regexp.MustCompile(pattern)
		for _, match := range re.FindAllStringSubmatch(htmlBody, -1) {
			if len(match) < 2 {
				continue
			}
			appendCandidate(info, normalizeMediaURL(pageURL, match[1]))
		}
	}

	ldjsonRe := regexp.MustCompile(`(?is)<script[^>]+type=["']application/ld\+json["'][^>]*>(.*?)</script>`)
	for _, match := range ldjsonRe.FindAllStringSubmatch(htmlBody, -1) {
		if len(match) < 2 {
			continue
		}
		var payload any
		if err := json.Unmarshal([]byte(strings.TrimSpace(match[1])), &payload); err == nil {
			collectVideoDataFromJSON(payload, pageURL, info)
		}
	}

	if info.HLSURL == "" && info.DASHURL == "" && info.MP4URL == "" && info.DownloadURL == "" {
		return nil
	}
	return info
}

func DiscoverVideoInfoFromArtifacts(
	pageURL string,
	htmlBody string,
	artifactTexts ...string,
) *UniversalVideoInfo {
	var info *UniversalVideoInfo
	if strings.TrimSpace(htmlBody) != "" {
		info = discoverVideoInfoFromHTML(pageURL, htmlBody)
	}
	if info == nil {
		info = &UniversalVideoInfo{
			PageURL:  pageURL,
			Platform: "generic-artifact",
			Title:    "Unknown Video",
		}
	}

	for _, artifactText := range artifactTexts {
		if strings.TrimSpace(artifactText) == "" {
			continue
		}
		for _, pattern := range []string{
			`(?is)\b(?:contentUrl|embedUrl|videoUrl|video_url|playAddr|play_url|m3u8Url|m3u8_url|dashUrl|dash_url|mp4Url|mp4_url)\b["']?\s*[:=]\s*["']([^"']+)["']`,
			`(https?://[^"'\\s<>]+(?:\\.m3u8|\\.mpd|\\.mp4|\\.webm|\\.m4v|\\.mov)[^"'\\s<>]*)`,
		} {
			re := regexp.MustCompile(pattern)
			for _, match := range re.FindAllStringSubmatch(artifactText, -1) {
				if len(match) < 2 {
					continue
				}
				appendCandidate(info, normalizeMediaURL(pageURL, match[1]))
			}
		}
		var payload any
		if err := json.Unmarshal([]byte(strings.TrimSpace(artifactText)), &payload); err == nil {
			collectVideoDataFromJSON(payload, pageURL, info)
		}
	}

	if info.Title == "" {
		info.Title = "Unknown Video"
	}
	if info.HLSURL == "" && info.DASHURL == "" && info.MP4URL == "" && info.DownloadURL == "" {
		return nil
	}
	return info
}

func collectVideoDataFromJSON(value any, pageURL string, info *UniversalVideoInfo) {
	switch typed := value.(type) {
	case []any:
		for _, item := range typed {
			collectVideoDataFromJSON(item, pageURL, info)
		}
	case map[string]any:
        if title, ok := typed["name"].(string); ok && strings.TrimSpace(title) != "" {
            info.Title = cleanMediaText(title)
        } else if title, ok := typed["headline"].(string); ok && strings.TrimSpace(title) != "" {
            info.Title = cleanMediaText(title)
        }
		if info.Description == "" {
			if desc, ok := typed["description"].(string); ok {
				info.Description = cleanMediaText(desc)
			}
		}
		if info.CoverURL == "" {
			if thumb, ok := typed["thumbnailUrl"].(string); ok {
				info.CoverURL = normalizeMediaURL(pageURL, thumb)
			}
		}
		for _, key := range []string{"contentUrl", "embedUrl", "url", "videoUrl", "video_url", "playAddr", "play_url", "m3u8Url", "m3u8_url", "dashUrl", "dash_url", "mp4Url", "mp4_url"} {
			if raw, ok := typed[key].(string); ok {
				appendCandidate(info, normalizeMediaURL(pageURL, raw))
			}
		}
		for _, nested := range typed {
			collectVideoDataFromJSON(nested, pageURL, info)
		}
	}
}

func sanitizeMediaFilename(title, fallback string) string {
	name := strings.TrimSpace(title)
	if name == "" {
		name = fallback
	}
	replacer := regexp.MustCompile(`[<>:"/\\|?*\x00-\x1f]`)
	name = replacer.ReplaceAllString(name, "")
	name = strings.TrimSpace(name)
	if name == "" {
		return fallback
	}
	return name
}

func (d *MultiPlatformDownloader) downloadYouTube(url, quality string) (string, error) {
	// Try yt-dlp first
	cmd := exec.Command("yt-dlp", "-f", "best", "-o", d.OutputDir+"/%(title)s_%(id)s.%(ext)s", url)
	output, err := cmd.CombinedOutput()
	if err == nil {
		return string(output), nil
	}

	// Fallback to API
	re := regexp.MustCompile(`(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})`)
	match := re.FindStringSubmatch(url)
	if match == nil {
		return "", fmt.Errorf("invalid YouTube URL")
	}

	resp, err := d.Client.Get(fmt.Sprintf("https://www.youtube.com/oembed?url=%s&format=json", url))
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}

	return fmt.Sprintf("Video: %v", result), nil
}

func (d *MultiPlatformDownloader) downloadTikTok(url, quality string) (string, error) {
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
	resp, err := d.Client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	html := string(body)

	// Extract video ID
	re := regexp.MustCompile(`/video/(\d+)`)
	match := re.FindStringSubmatch(url)
	if match != nil {
	}

	// Extract video URL
	urlRe := regexp.MustCompile(`"playAddr"\s*:\s*"([^"]+)"`)
	urlMatch := urlRe.FindStringSubmatch(html)
	if urlMatch == nil {
		return "", fmt.Errorf("could not extract video URL")
	}

	videoURL := strings.ReplaceAll(urlMatch[1], `\/`, `/`)

	// Download
	filename := fmt.Sprintf("tiktok_%s.mp4", match[1])
	filepath := d.OutputDir + "/" + filename

	resp2, err := http.Get(videoURL)
	if err != nil {
		return "", err
	}
	defer resp2.Body.Close()

	out, err := os.Create(filepath)
	if err != nil {
		return "", err
	}
	defer out.Close()

	_, err = io.Copy(out, resp2.Body)
	if err != nil {
		return "", err
	}

	return filepath, nil
}

func (d *MultiPlatformDownloader) downloadBilibili(url, quality string) (string, error) {
	re := regexp.MustCompile(`(?:bilibili\.com/video/|b23\.tv/)([a-zA-Z0-9]+)`)
	match := re.FindStringSubmatch(url)
	if match == nil {
		return "", fmt.Errorf("invalid Bilibili URL")
	}

	bvid := match[1]
	apiURL := fmt.Sprintf("https://api.bilibili.com/x/player/pagelist?bvid=%s", bvid)

	resp, err := d.Client.Get(apiURL)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}

	// 修复: 安全的类型断言
	dataMap, ok := result["data"].(map[string]interface{})
	if !ok {
		return "", fmt.Errorf("unexpected response format")
	}
	data, ok := dataMap["pages"].([]interface{})
	if !ok {
		return fmt.Sprintf("Bilibili page found, unable to parse pages"), nil
	}
	return fmt.Sprintf("Bilibili has %d pages", len(data)), nil
}

func (d *MultiPlatformDownloader) downloadGeneric(url string) (string, error) {
	info, err := d.DiscoverVideoInfo(url)
	if err != nil {
		return "", err
	}
	if info == nil {
		return "", fmt.Errorf("could not discover media url from page")
	}

	baseName := sanitizeMediaFilename(info.Title, fmt.Sprintf("download_%d", time.Now().Unix()))

	switch {
	case info.HLSURL != "":
		outputFile := filepath.Join(d.OutputDir, baseName+".ts")
		downloader := NewHLSDownloader(d.OutputDir)
		if err := downloader.DownloadM3U8(info.HLSURL, outputFile); err != nil {
			return "", err
		}
		return outputFile, nil
	case info.DASHURL != "":
		outputFile := filepath.Join(d.OutputDir, baseName+".mp4")
		downloader := NewLegacyDASHDownloader(d.OutputDir)
		if err := downloader.DownloadDASH(info.DASHURL, outputFile); err != nil {
			return "", err
		}
		return outputFile, nil
	}

	downloadURL := info.MP4URL
	if downloadURL == "" {
		downloadURL = info.DownloadURL
	}
	if downloadURL == "" {
		return "", fmt.Errorf("no downloadable media url discovered")
	}

	resp, err := http.Get(downloadURL)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	ext := ".mp4"
	if parsed, err := neturl.Parse(downloadURL); err == nil {
		candidateExt := strings.ToLower(filepath.Ext(parsed.Path))
		if candidateExt != "" && len(candidateExt) <= 5 {
			ext = candidateExt
		}
	}
	filepath := filepath.Join(d.OutputDir, baseName+ext)

	out, err := os.Create(filepath)
	if err != nil {
		return "", err
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)
	if err != nil {
		return "", fmt.Errorf("download failed: %v", err)
	}
	return filepath, nil
}

// MusicDownloader downloads music from various platforms
type MusicDownloader struct {
	OutputDir string
	Client    *http.Client
}

// NewMusicDownloader creates a new music downloader
func NewMusicDownloader(outputDir string) *MusicDownloader {
	if outputDir == "" {
		outputDir = "downloads/music"
	}
	os.MkdirAll(outputDir, 0755)
	return &MusicDownloader{
		OutputDir: outputDir,
		Client: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// SearchNetease searches NetEase Cloud Music
func (m *MusicDownloader) SearchNetease(query string, limit int) ([]map[string]interface{}, error) {
	apiURL := fmt.Sprintf("https://music.163.com/api/search/get?s=%s&type=1&limit=%d", query, limit)
	resp, err := m.Client.Get(apiURL)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	songs := result["result"].(map[string]interface{})["songs"].([]interface{})
	results := make([]map[string]interface{}, 0, len(songs))

	for _, s := range songs {
		song := s.(map[string]interface{})
		artists := song["artists"].([]interface{})
		artist := ""
		if len(artists) > 0 {
			artist = artists[0].(map[string]interface{})["name"].(string)
		}
		results = append(results, map[string]interface{}{
			"id":     song["id"],
			"title":  song["name"],
			"artist": artist,
		})
	}

	return results, nil
}

// DownloadNetease downloads from NetEase
func (m *MusicDownloader) DownloadNetease(songID int) (string, error) {
	// Get download URL
	apiURL := fmt.Sprintf("https://music.163.com/api/song/enhance/download/url?id=%d&br=320000", songID)
	resp, err := m.Client.Get(apiURL)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}

	data := result["data"].(map[string]interface{})
	url := data["url"].(string)

	// Download
	resp2, err := http.Get(url)
	if err != nil {
		return "", err
	}
	defer resp2.Body.Close()

	filename := fmt.Sprintf("music_%d.mp3", songID)
	filepath := m.OutputDir + "/" + filename

	out, err := os.Create(filepath)
	if err != nil {
		return "", err
	}
	defer out.Close()

	io.Copy(out, resp2.Body)
	return filepath, nil
}

// DownloadPlaylist downloads entire playlist
func (m *MusicDownloader) DownloadPlaylist(playlistID int) ([]string, error) {
	apiURL := fmt.Sprintf("https://music.163.com/api/playlist/detail?id=%d", playlistID)
	resp, err := m.Client.Get(apiURL)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)

	tracks := result["result"].(map[string]interface{})["tracks"].([]interface{})
	var files []string

	for _, t := range tracks {
		track := t.(map[string]interface{})
		songID := int(track["id"].(float64))
		if filepath, err := m.DownloadNetease(songID); err == nil {
			files = append(files, filepath)
		}
	}

	return files, nil
}

func init() {
	fmt.Println("Multi-platform media downloader loaded")
}
