package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"gospider/extractors/bilibili"
	"gospider/extractors/iqiyi"
	"gospider/extractors/tencent"
	"gospider/extractors/youku"
	"gospider/media"
)

func mediaCommand(args []string) {
	if len(args) > 0 && args[0] == "drm" {
		if code := mediaDRMCommand(args[1:]); code != 0 {
			os.Exit(code)
		}
		return
	}
	if len(args) > 0 && args[0] == "artifact" {
		if code := mediaArtifactCommand(args[1:]); code != 0 {
			os.Exit(code)
		}
		return
	}

	mediaCmd := flag.NewFlagSet("media", flag.ExitOnError)
	url := mediaCmd.String("url", "", "媒体 URL")
	outputDir := mediaCmd.String("output", "./media", "输出目录")
	download := mediaCmd.Bool("download", false, "下载媒体")
	platform := mediaCmd.String("platform", "auto", "平台类型 (auto, youtube, youku, iqiyi, tencent, bilibili)")
	htmlFile := mediaCmd.String("html-file", "", "浏览器抓取的 HTML artifact")
	networkFile := mediaCmd.String("network-file", "", "浏览器抓取的 network artifact")
	harFile := mediaCmd.String("har-file", "", "浏览器抓取的 HAR artifact")
	artifactDir := mediaCmd.String("artifact-dir", "", "浏览器产物目录，会自动发现 html/network/har")
	mediaCmd.Usage = func() {
		fmt.Println("Usage: gospider media [options]")
		fmt.Println("\nOptions:")
		mediaCmd.PrintDefaults()
		fmt.Println("\nExamples:")
		fmt.Println("  gospider media -url https://www.youtube.com/watch?v=xxx")
		fmt.Println("  gospider media -url https://v.youku.com/v_show/id_xxx.html -download")
		fmt.Println("  gospider media drm --content \"#EXTM3U ...\"")
	}
	_ = mediaCmd.Parse(args)

	if *url == "" {
		mediaCmd.Usage()
		os.Exit(1)
	}

	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Println("                    gospider 媒体下载器                     ")
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Printf("URL: %s\n", *url)
	fmt.Printf("输出目录：%s\n", *outputDir)
	fmt.Printf("下载：%v\n", *download)
	fmt.Println()

	if err := os.MkdirAll(*outputDir, 0755); err != nil {
		fmt.Printf("创建输出目录失败：%v\n", err)
		os.Exit(1)
	}

	*htmlFile, *networkFile, *harFile = resolveArtifactBundle(*artifactDir, *htmlFile, *networkFile, *harFile)
	if *htmlFile != "" || *networkFile != "" || *harFile != "" {
		if err := handleGenericArtifacts(*url, *outputDir, *download, *htmlFile, *networkFile, *harFile); err != nil {
			fmt.Printf("❌ 媒体命令失败：%v\n", err)
			os.Exit(1)
		}
		return
	}

	detectedPlatform := detectPlatform(*url)
	if *platform != "auto" {
		detectedPlatform = *platform
	}
	fmt.Printf("检测到平台：%s\n\n", detectedPlatform)

	var err error
	switch detectedPlatform {
	case "youtube":
		err = handleYouTube(*url, *outputDir, *download)
	case "youku":
		err = handleYouku(*url, *outputDir, *download)
	case "iqiyi":
		err = handleIqiyi(*url, *outputDir, *download)
	case "tencent":
		err = handleTencent(*url, *outputDir, *download)
	case "bilibili":
		err = handleBilibili(*url, *outputDir, *download)
	default:
		err = handleGeneric(*url, *outputDir, *download)
	}

	if err != nil {
		fmt.Printf("❌ 媒体命令失败：%v\n", err)
		os.Exit(1)
	}
}

func mediaArtifactCommand(args []string) int {
	cmd := flag.NewFlagSet("media artifact", flag.ContinueOnError)
	cmd.SetOutput(io.Discard)
	url := cmd.String("url", "https://example.com/", "原始页面 URL")
	artifactDir := cmd.String("artifact-dir", "", "artifact 目录")
	htmlFile := cmd.String("html-file", "", "HTML artifact")
	networkFile := cmd.String("network-file", "", "network artifact")
	harFile := cmd.String("har-file", "", "HAR artifact")
	outputDir := cmd.String("output", "./media", "输出目录")
	download := cmd.Bool("download", false, "解析后立即下载")
	if err := cmd.Parse(args); err != nil {
		fmt.Fprintln(os.Stderr, "usage: gospider media artifact --artifact-dir <dir> [--url <url>] [--download]")
		return 2
	}
	if strings.TrimSpace(*artifactDir) == "" && strings.TrimSpace(*htmlFile) == "" && strings.TrimSpace(*networkFile) == "" && strings.TrimSpace(*harFile) == "" {
		fmt.Fprintln(os.Stderr, "gospider media artifact requires --artifact-dir or explicit artifact files")
		return 2
	}

	*htmlFile, *networkFile, *harFile = resolveArtifactBundle(*artifactDir, *htmlFile, *networkFile, *harFile)
	if *htmlFile == "" && *networkFile == "" && *harFile == "" {
		fmt.Fprintln(os.Stderr, "no artifact files found")
		return 2
	}

	downloader := media.NewMultiPlatformDownloader(*outputDir)
	info, err := discoverArtifactInfo(downloader, *url, *htmlFile, *networkFile, *harFile)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		return 1
	}

	payload := map[string]any{
		"command":      "media artifact",
		"runtime":      "go",
		"url":          *url,
		"artifact_dir": *artifactDir,
		"html_file":    *htmlFile,
		"network_file": *networkFile,
		"har_file":     *harFile,
		"video":        infoToMap(info),
		"download": map[string]any{
			"requested": *download,
			"output":    "",
		},
	}

	if *download {
		if err := os.MkdirAll(*outputDir, 0755); err != nil {
			fmt.Fprintln(os.Stderr, err.Error())
			return 1
		}
		output, err := downloadArtifactInfo(downloader, info, *outputDir)
		if err != nil {
			fmt.Fprintln(os.Stderr, err.Error())
			return 1
		}
		payload["download"].(map[string]any)["output"] = strings.TrimSpace(output)
	}

	encoded, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		return 1
	}
	fmt.Println(string(encoded))
	return 0
}

func mediaDRMCommand(args []string) int {
	drmCmd := flag.NewFlagSet("media drm", flag.ContinueOnError)
	drmCmd.SetOutput(io.Discard)
	url := drmCmd.String("url", "", "远程 manifest 或页面 URL")
	input := drmCmd.String("input", "", "本地 manifest 或媒体文件路径")
	inlineContent := drmCmd.String("content", "", "直接传入 manifest 内容")
	contentFile := drmCmd.String("content-file", "", "本地 manifest 文本文件路径")
	if err := drmCmd.Parse(args); err != nil {
		fmt.Fprintln(os.Stderr, "usage: gospider media drm [--url <url> | --input <path> | --content <manifest> | --content-file <path>]")
		return 2
	}

	payload, err := inspectDRMTarget(*url, *input, *inlineContent, *contentFile)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		return 2
	}

	encoded, marshalErr := json.MarshalIndent(payload, "", "  ")
	if marshalErr != nil {
		fmt.Fprintln(os.Stderr, marshalErr.Error())
		return 1
	}
	fmt.Println(string(encoded))
	return 0
}

func detectPlatform(url string) string {
	lower := strings.ToLower(url)
	switch {
	case strings.Contains(lower, "youtube.com") || strings.Contains(lower, "youtu.be"):
		return "youtube"
	case strings.Contains(lower, "youku.com"):
		return "youku"
	case strings.Contains(lower, "iqiyi.com"):
		return "iqiyi"
	case strings.Contains(lower, "qq.com") || strings.Contains(lower, "v.qq.com"):
		return "tencent"
	case strings.Contains(lower, "bilibili.com") || strings.Contains(lower, "b23.tv"):
		return "bilibili"
	default:
		return "unknown"
	}
}

func resolveArtifactBundle(artifactDir, htmlFile, networkFile, harFile string) (string, string, string) {
	discover := func(current string, candidates []string, patterns []string) string {
		if strings.TrimSpace(current) != "" {
			return current
		}
		if strings.TrimSpace(artifactDir) == "" {
			return ""
		}
		root := filepath.Clean(artifactDir)
		for _, candidate := range candidates {
			path := filepath.Join(root, candidate)
			if info, err := os.Stat(path); err == nil && !info.IsDir() {
				return path
			}
		}
		for _, pattern := range patterns {
			if matches, err := filepath.Glob(filepath.Join(root, pattern)); err == nil {
				for _, path := range matches {
					if info, err := os.Stat(path); err == nil && !info.IsDir() {
						return path
					}
				}
			}
		}
		return ""
	}

	htmlFile = discover(htmlFile,
		[]string{"page.html", "content.html", "document.html", "browser.html", "response.html", "index.html"},
		[]string{"*page*.html", "*content*.html", "*.html"},
	)
	networkFile = discover(networkFile,
		[]string{"network.json", "requests.json", "trace.json", "network.log", "network.txt"},
		[]string{"*network*.json", "*request*.json", "*trace*.json", "*network*.txt"},
	)
	harFile = discover(harFile,
		[]string{"trace.har", "network.har", "session.har", "browser.har", "page.har"},
		[]string{"*.har"},
	)
	return htmlFile, networkFile, harFile
}

func discoverArtifactInfo(downloader *media.MultiPlatformDownloader, pageURL, htmlFile, networkFile, harFile string) (*media.UniversalVideoInfo, error) {
	readArtifact := func(path string) (string, error) {
		if strings.TrimSpace(path) == "" {
			return "", nil
		}
		raw, err := os.ReadFile(path)
		if err != nil {
			return "", err
		}
		return string(raw), nil
	}

	htmlText, err := readArtifact(htmlFile)
	if err != nil {
		return nil, err
	}
	networkText, err := readArtifact(networkFile)
	if err != nil {
		return nil, err
	}
	harText, err := readArtifact(harFile)
	if err != nil {
		return nil, err
	}

	info := mediaDiscoverFromArtifacts(downloader, pageURL, htmlText, networkText, harText)
	if info == nil {
		return nil, fmt.Errorf("未从 artifact 中发现可解析的视频流")
	}
	return info, nil
}

func infoToMap(info *media.UniversalVideoInfo) map[string]any {
	if info == nil {
		return map[string]any{}
	}
	return map[string]any{
		"title":        info.Title,
		"cover_url":    info.CoverURL,
		"hls_url":      info.HLSURL,
		"dash_url":     info.DASHURL,
		"mp4_url":      info.MP4URL,
		"download_url": info.DownloadURL,
	}
}

func downloadArtifactInfo(downloader *media.MultiPlatformDownloader, info *media.UniversalVideoInfo, outputDir string) (string, error) {
	if info == nil {
		return "", fmt.Errorf("missing discovered media info")
	}
	baseName := mediaFilename(info.Title, "artifact-media", ".mp4")
	switch {
	case info.HLSURL != "":
		outputFile := filepath.Join(outputDir, baseName)
		if !strings.HasSuffix(strings.ToLower(outputFile), ".ts") {
			outputFile += ".ts"
		}
		hls := media.NewHLSDownloader(outputDir)
		if err := hls.DownloadM3U8(info.HLSURL, outputFile); err != nil {
			return "", err
		}
		return outputFile, nil
	case info.DASHURL != "":
		outputFile := filepath.Join(outputDir, baseName)
		if !strings.HasSuffix(strings.ToLower(outputFile), ".mp4") {
			outputFile += ".mp4"
		}
		dash := media.NewLegacyDASHDownloader(outputDir)
		if err := dash.DownloadDASH(info.DASHURL, outputFile); err != nil {
			return "", err
		}
		return outputFile, nil
	default:
		downloadURL := firstNonEmpty(info.MP4URL, info.DownloadURL)
		if downloadURL == "" {
			return "", fmt.Errorf("未发现可下载的视频 URL")
		}
		return downloader.Download(downloadURL, "best")
	}
}

func inspectDRMTarget(url, input, inlineContent, contentFile string) (map[string]any, error) {
	sourceKind := ""
	sourceValue := ""
	content := ""

	switch {
	case strings.TrimSpace(contentFile) != "":
		raw, err := os.ReadFile(contentFile)
		if err != nil {
			return nil, fmt.Errorf("failed to read content file: %w", err)
		}
		sourceKind = "content-file"
		sourceValue = contentFile
		content = string(raw)
	case strings.TrimSpace(inlineContent) != "":
		sourceKind = "inline-content"
		sourceValue = "inline"
		content = inlineContent
	case strings.TrimSpace(input) != "":
		raw, err := os.ReadFile(input)
		if err != nil {
			return nil, fmt.Errorf("failed to read input file: %w", err)
		}
		sourceKind = "input"
		sourceValue = input
		ext := strings.ToLower(filepath.Ext(input))
		if ext == ".m3u8" || ext == ".mpd" || ext == ".txt" {
			content = string(raw)
		} else if ffmpegPath, err := media.AutoDetectFFmpeg(); err == nil {
			wrapper := media.NewFFmpegWrapper(ffmpegPath, filepath.Dir(input))
			isDRM, drmType, detectErr := wrapper.CheckDRM(input)
			if detectErr != nil {
				return nil, detectErr
			}
			return map[string]any{
				"command": "media drm",
				"runtime": "go",
				"source": map[string]any{"kind": sourceKind, "value": sourceValue},
				"manifest_type": "binary",
				"drm_info": map[string]any{
					"is_drm_protected": isDRM,
					"drm_type":         normalizeDRMType(drmType, isDRM),
				},
				"downloadable": !isDRM,
				"message":      drmMessage(normalizeDRMType(drmType, isDRM), !isDRM),
			}, nil
		} else {
			content = string(raw)
		}
	case strings.TrimSpace(url) != "":
		req, err := http.NewRequest(http.MethodGet, url, nil)
		if err != nil {
			return nil, err
		}
		req.Header.Set("User-Agent", "GoSpider/2.0 DRM Inspector")
		resp, err := (&http.Client{Timeout: 20 * time.Second}).Do(req)
		if err != nil {
			return nil, err
		}
		defer resp.Body.Close()
		raw, err := io.ReadAll(resp.Body)
		if err != nil {
			return nil, err
		}
		sourceKind = "url"
		sourceValue = url
		content = string(raw)
	default:
		return nil, fmt.Errorf("media drm requires --url, --input, --content, or --content-file")
	}

	manifestType := detectManifestType(sourceValue, content)
	isDRM, drmType := detectManifestDRM(content)
	downloadable := drmDownloadable(drmType, isDRM)
	return map[string]any{
		"command": "media drm",
		"runtime": "go",
		"source": map[string]any{
			"kind":  sourceKind,
			"value": sourceValue,
		},
		"manifest_type": manifestType,
		"drm_info": map[string]any{
			"is_drm_protected": isDRM,
			"drm_type":         drmType,
		},
		"downloadable": downloadable,
		"message":      drmMessage(drmType, downloadable),
	}, nil
}

func detectManifestType(sourceValue, content string) string {
	lowerSource := strings.ToLower(sourceValue)
	lowerContent := strings.ToLower(content)
	switch {
	case strings.HasSuffix(lowerSource, ".m3u8"), strings.Contains(lowerContent, "#extm3u"):
		return "m3u8"
	case strings.HasSuffix(lowerSource, ".mpd"), strings.Contains(lowerContent, "<mpd"):
		return "mpd"
	default:
		return "unknown"
	}
}

func detectManifestDRM(content string) (bool, string) {
	lower := strings.ToLower(content)
	switch {
	case strings.Contains(lower, "method=none"):
		return false, "none"
	case strings.Contains(lower, "widevine"), strings.Contains(lower, "edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"):
		return true, "widevine"
	case strings.Contains(lower, "playready"), strings.Contains(lower, "mspr:pro"), strings.Contains(lower, "9a04f079-9840-4286-ab92-e65be0885f95"):
		return true, "playready"
	case strings.Contains(lower, "fairplay"), strings.Contains(lower, "apple.streamingkeydelivery"), strings.Contains(lower, "com.apple.fps"), strings.Contains(lower, "94ce86fb-0790-4974-8fd1-3c54e7ef316f"):
		return true, "fairplay"
	case strings.Contains(lower, "clearkey"), strings.Contains(lower, "e2719d58-a985-b3c9-781a-b030af78d30e"):
		return true, "clearkey"
	case strings.Contains(lower, "sample-aes"):
		return true, "sample-aes"
	case strings.Contains(lower, "aes-128"), strings.Contains(lower, "#ext-x-key"):
		return true, "aes-128"
	case strings.Contains(lower, "<contentprotection"), strings.Contains(lower, "<cenc:pssh"):
		return true, "unknown"
	default:
		return false, "none"
	}
}

func drmDownloadable(drmType string, isDRM bool) bool {
	if !isDRM {
		return true
	}
	return drmType == "aes-128" || drmType == "clearkey"
}

func drmMessage(drmType string, downloadable bool) string {
	if drmType == "none" {
		return "未检测到 DRM，可直接下载"
	}
	if downloadable {
		return fmt.Sprintf("检测到 %s，加密流可在具备密钥/解密参数时处理", drmType)
	}
	return fmt.Sprintf("检测到 %s DRM，需要授权或专用密钥", drmType)
}

func normalizeDRMType(raw string, isDRM bool) string {
	if !isDRM {
		return "none"
	}
	value := strings.TrimSpace(strings.ToLower(raw))
	if value == "" {
		return "unknown"
	}
	switch {
	case strings.Contains(value, "widevine"):
		return "widevine"
	case strings.Contains(value, "playready"):
		return "playready"
	case strings.Contains(value, "fairplay"):
		return "fairplay"
	case strings.Contains(value, "cenc"), strings.Contains(value, "pssh"):
		return "unknown"
	default:
		return value
	}
}

func handleYouTube(url, outputDir string, download bool) error {
	fmt.Println("📺 YouTube 视频")
	meta, err := inspectYouTube(url)
	if err != nil {
		return err
	}

	fmt.Printf("标题：%s\n", meta.Title)
	if meta.Author != "" {
		fmt.Printf("作者：%s\n", meta.Author)
	}
	if meta.Thumbnail != "" {
		fmt.Printf("封面：%s\n", meta.Thumbnail)
	}
	fmt.Println()

	if !download {
		fmt.Println("使用 -download 参数开始下载")
		return nil
	}

	downloader := media.NewMultiPlatformDownloader(outputDir)
	output, err := downloader.Download(url, "best")
	if err != nil {
		return err
	}
	fmt.Printf("✅ 下载结果：%s\n", strings.TrimSpace(output))
	return nil
}

func handleYouku(url, outputDir string, download bool) error {
	fmt.Println("📺 优酷视频")
	extractor := youku.NewYoukuExtractor()
	info, err := extractor.Extract(url)
	if err != nil {
		return err
	}

	printYoukuInfo(info)
	if !download {
		fmt.Println("使用 -download 参数开始下载")
		return nil
	}

	streamURL, streamType := chooseYoukuStream(info)
	if streamURL == "" {
		return fmt.Errorf("未找到可下载的优酷流地址")
	}

	outputFile := filepath.Join(outputDir, mediaFilename(info.Title, info.VideoID, streamType.fileExt))
	switch streamType.kind {
	case "hls":
		downloader := media.NewHLSDownloader(outputDir)
		downloader.SetReferer("https://v.youku.com/")
		if err := downloader.DownloadM3U8(streamURL, outputFile); err != nil {
			return err
		}
	case "dash":
		downloader := media.NewLegacyDASHDownloader(outputDir)
		if err := downloader.DownloadDASH(streamURL, outputFile); err != nil {
			return err
		}
	default:
		return fmt.Errorf("未知的优酷流类型: %s", streamType.kind)
	}

	fmt.Printf("✅ 下载完成：%s\n", outputFile)
	return nil
}

func handleGeneric(url, outputDir string, download bool) error {
	fmt.Println("📺 通用视频解析")
	downloader := media.NewMultiPlatformDownloader(outputDir)
	info, err := downloader.DiscoverVideoInfo(url)
	if err != nil {
		return err
	}
	if info == nil {
		return fmt.Errorf("未发现可解析的视频流")
	}

	fmt.Printf("标题：%s\n", info.Title)
	if info.CoverURL != "" {
		fmt.Printf("封面：%s\n", info.CoverURL)
	}
	if info.HLSURL != "" {
		fmt.Printf("HLS：%s\n", info.HLSURL)
	}
	if info.DASHURL != "" {
		fmt.Printf("DASH：%s\n", info.DASHURL)
	}
	if info.MP4URL != "" {
		fmt.Printf("MP4：%s\n", info.MP4URL)
	}
	if info.DownloadURL != "" {
		fmt.Printf("下载：%s\n", info.DownloadURL)
	}
	fmt.Println()

	if !download {
		fmt.Println("使用 -download 参数开始下载")
		return nil
	}

	output, err := downloadArtifactInfo(downloader, info, outputDir)
	if err != nil {
		return err
	}
	fmt.Printf("✅ 下载结果：%s\n", strings.TrimSpace(output))
	return nil
}

func handleGenericArtifacts(url, outputDir string, download bool, htmlFile, networkFile, harFile string) error {
	fmt.Println("📺 通用视频 artifact 解析")
	downloader := media.NewMultiPlatformDownloader(outputDir)

	readArtifact := func(path string) (string, error) {
		if strings.TrimSpace(path) == "" {
			return "", nil
		}
		raw, err := os.ReadFile(path)
		if err != nil {
			return "", err
		}
		return string(raw), nil
	}

	htmlText, err := readArtifact(htmlFile)
	if err != nil {
		return err
	}
	networkText, err := readArtifact(networkFile)
	if err != nil {
		return err
	}
	harText, err := readArtifact(harFile)
	if err != nil {
		return err
	}

	info := mediaDiscoverFromArtifacts(downloader, url, htmlText, networkText, harText)
	if info == nil {
		return fmt.Errorf("未从 artifact 中发现可解析的视频流")
	}

	fmt.Printf("标题：%s\n", info.Title)
	if info.CoverURL != "" {
		fmt.Printf("封面：%s\n", info.CoverURL)
	}
	if info.HLSURL != "" {
		fmt.Printf("HLS：%s\n", info.HLSURL)
	}
	if info.DASHURL != "" {
		fmt.Printf("DASH：%s\n", info.DASHURL)
	}
	if info.MP4URL != "" {
		fmt.Printf("MP4：%s\n", info.MP4URL)
	}
	if info.DownloadURL != "" {
		fmt.Printf("下载：%s\n", info.DownloadURL)
	}
	fmt.Println()

	if !download {
		fmt.Println("使用 -download 参数开始下载")
		return nil
	}

	result, err := downloader.Download(url, "best")
	if err != nil {
		return err
	}
	fmt.Printf("✅ 下载结果：%s\n", strings.TrimSpace(result))
	return nil
}

func mediaDiscoverFromArtifacts(downloader *media.MultiPlatformDownloader, pageURL, htmlText, networkText, harText string) *media.UniversalVideoInfo {
	return media.DiscoverVideoInfoFromArtifacts(pageURL, htmlText, networkText, harText)
}

func handleIqiyi(url, outputDir string, download bool) error {
	fmt.Println("📺 爱奇艺视频")
	extractor := iqiyi.NewIqiyiExtractor()
	info, err := extractor.Extract(url)
	if err != nil {
		return err
	}

	fmt.Printf("标题：%s\n", info.Title)
	if info.Duration > 0 {
		fmt.Printf("时长：%d 秒\n", info.Duration)
	}
	if info.CoverURL != "" {
		fmt.Printf("封面：%s\n", info.CoverURL)
	}
	if len(info.QualityOptions) > 0 {
		fmt.Printf("清晰度：%s\n", strings.Join(info.QualityOptions, ", "))
	}
	for _, stream := range info.Streams {
		fmt.Printf("  - %s HLS=%t DASH=%t\n", stream.Quality, stream.M3U8URL != "", stream.DASHURL != "")
	}
	if info.M3U8URL != "" {
		fmt.Printf("主 HLS：%s\n", info.M3U8URL)
	}
	if info.DASHURL != "" {
		fmt.Printf("主 DASH：%s\n", info.DASHURL)
	}
	fmt.Println()

	if !download {
		fmt.Println("使用 -download 参数开始下载")
		return nil
	}

	streamURL, streamType := chooseIqiyiStream(info)
	if streamURL == "" {
		return fmt.Errorf("未找到可下载的爱奇艺流地址")
	}

	outputFile := filepath.Join(outputDir, mediaFilename(info.Title, info.VideoID, streamType.fileExt))
	switch streamType.kind {
	case "hls":
		downloader := media.NewHLSDownloader(outputDir)
		downloader.SetReferer("https://www.iqiyi.com/")
		if err := downloader.DownloadM3U8(streamURL, outputFile); err != nil {
			return err
		}
	case "dash":
		downloader := media.NewLegacyDASHDownloader(outputDir)
		if err := downloader.DownloadDASH(streamURL, outputFile); err != nil {
			return err
		}
	default:
		return fmt.Errorf("未知的爱奇艺流类型: %s", streamType.kind)
	}

	fmt.Printf("✅ 下载完成：%s\n", outputFile)
	return nil
}

func handleTencent(url, outputDir string, download bool) error {
	fmt.Println("📺 腾讯视频")
	extractor := tencent.NewTencentExtractor()
	info, err := extractor.Extract(url)
	if err != nil {
		return err
	}

	fmt.Printf("标题：%s\n", info.Title)
	if info.Description != "" {
		fmt.Printf("描述：%s\n", info.Description)
	}
	fmt.Printf("可用格式：%d\n", len(info.Formats))
	for _, format := range info.Formats {
		fmt.Printf("  - %s %s\n", format.Quality, format.URL)
	}
	fmt.Println()

	if !download {
		fmt.Println("使用 -download 参数开始下载")
		return nil
	}

	downloadURL := chooseTencentURL(info)
	if downloadURL == "" {
		return fmt.Errorf("未找到可下载的腾讯视频直链")
	}

	downloader := media.NewMediaDownloader(outputDir)
	result := downloader.DownloadVideo(downloadURL, mediaFilename(info.Title, "tencent_video", ".mp4"))
	if !result.Success {
		return fmt.Errorf(result.Error)
	}

	fmt.Printf("✅ 下载完成：%s\n", result.Path)
	return nil
}

func handleBilibili(url, outputDir string, download bool) error {
	fmt.Println("📺 Bilibili 视频")
	extractor := bilibili.NewBilibiliExtractor()
	if cookie := os.Getenv("GOSPIDER_BILIBILI_COOKIE"); strings.TrimSpace(cookie) != "" {
		extractor.SetCookie(cookie)
	}
	info, err := extractor.Extract(url)
	if err != nil {
		return err
	}

	fmt.Printf("标题：%s\n", info.Title)
	if info.Owner != "" {
		fmt.Printf("UP 主：%s\n", info.Owner)
	}
	if info.Duration > 0 {
		fmt.Printf("时长：%d 秒\n", info.Duration)
	}
	if info.Thumbnail != "" {
		fmt.Printf("封面：%s\n", info.Thumbnail)
	}
	if info.Video != nil {
		fmt.Printf("视频流：%s %s\n", info.Video.Quality, firstNonEmpty(info.Video.URL, info.Video.BaseURL))
	}
	if info.Audio != nil {
		fmt.Printf("音频流：%s\n", firstNonEmpty(info.Audio.URL, info.Audio.BaseURL))
	}
	fmt.Println()

	if !download {
		fmt.Println("使用 -download 参数开始下载")
		return nil
	}

	downloadURL := chooseBilibiliURL(info)
	if downloadURL == "" {
		return fmt.Errorf("未找到可下载的 Bilibili 视频流地址")
	}

	downloader := media.NewMediaDownloader(outputDir)
	result := downloader.DownloadVideo(downloadURL, mediaFilename(info.Title, info.BVID, ".mp4"))
	if !result.Success {
		return fmt.Errorf(result.Error)
	}

	fmt.Printf("✅ 下载完成：%s\n", result.Path)
	return nil
}

type youtubeMeta struct {
	Title     string `json:"title"`
	Author    string `json:"author_name"`
	Thumbnail string `json:"thumbnail_url"`
}

func inspectYouTube(videoURL string) (*youtubeMeta, error) {
	client := &http.Client{Timeout: 20 * time.Second}
	oembedURL := "https://www.youtube.com/oembed?format=json&url=" + videoURL

	req, err := http.NewRequest(http.MethodGet, oembedURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("YouTube oEmbed 请求失败: HTTP %d", resp.StatusCode)
	}

	var meta youtubeMeta
	if err := json.NewDecoder(resp.Body).Decode(&meta); err != nil {
		return nil, err
	}
	return &meta, nil
}

func printYoukuInfo(info *youku.YoukuVideoInfo) {
	fmt.Printf("标题：%s\n", info.Title)
	if info.Duration > 0 {
		fmt.Printf("时长：%d 秒\n", info.Duration)
	}
	if info.Thumbnail != "" {
		fmt.Printf("封面：%s\n", info.Thumbnail)
	}
	if info.Description != "" {
		fmt.Printf("描述：%s\n", info.Description)
	}
	fmt.Printf("流数量：%d\n", len(info.Streams))
	for _, stream := range info.Streams {
		fmt.Printf("  - %s %s HLS=%t DASH=%t\n", stream.Quality, stream.StreamType, stream.HLSURL != "", stream.DASHURL != "")
	}
	if info.M3U8URL != "" {
		fmt.Printf("主 HLS：%s\n", info.M3U8URL)
	}
	if info.MPDURL != "" {
		fmt.Printf("主 DASH：%s\n", info.MPDURL)
	}
	fmt.Println()
}

type preferredStream struct {
	kind    string
	fileExt string
}

func chooseYoukuStream(info *youku.YoukuVideoInfo) (string, preferredStream) {
	hasRankedStream := false
	for _, stream := range info.Streams {
		if youkuQualityScore(stream.Quality, stream.Width, stream.Height) > 0 {
			hasRankedStream = true
			break
		}
	}
	if !hasRankedStream {
		if info.M3U8URL != "" {
			return info.M3U8URL, preferredStream{kind: "hls", fileExt: ".ts"}
		}
		if info.MPDURL != "" {
			return info.MPDURL, preferredStream{kind: "dash", fileExt: ".mp4"}
		}
	}

	bestScore := -1
	bestURL := ""
	bestType := preferredStream{}
	for _, stream := range info.Streams {
		score := youkuQualityScore(stream.Quality, stream.Width, stream.Height)
		if stream.HLSURL != "" && score*10+1 > bestScore {
			bestScore = score*10 + 1
			bestURL = stream.HLSURL
			bestType = preferredStream{kind: "hls", fileExt: ".ts"}
		}
		if stream.DASHURL != "" && score*10 > bestScore {
			bestScore = score * 10
			bestURL = stream.DASHURL
			bestType = preferredStream{kind: "dash", fileExt: ".mp4"}
		}
	}
	if bestURL != "" {
		return bestURL, bestType
	}
	if info.M3U8URL != "" {
		return info.M3U8URL, preferredStream{kind: "hls", fileExt: ".ts"}
	}
	if info.MPDURL != "" {
		return info.MPDURL, preferredStream{kind: "dash", fileExt: ".mp4"}
	}
	for _, stream := range info.Streams {
		if stream.HLSURL != "" {
			return stream.HLSURL, preferredStream{kind: "hls", fileExt: ".ts"}
		}
		if stream.DASHURL != "" {
			return stream.DASHURL, preferredStream{kind: "dash", fileExt: ".mp4"}
		}
	}
	return "", preferredStream{}
}

func chooseTencentURL(info *tencent.VideoInfo) string {
	bestScore := -1
	bestURL := ""
	for _, format := range info.Formats {
		if format.URL == "" {
			continue
		}
		score := tencentQualityScore(format)
		if score > bestScore {
			bestScore = score
			bestURL = format.URL
		}
	}
	return bestURL
}

func chooseBilibiliURL(info *bilibili.BilibiliVideoInfo) string {
	if info == nil {
		return ""
	}
	if info.Video != nil {
		if info.Video.URL != "" {
			return info.Video.URL
		}
		if info.Video.BaseURL != "" {
			return info.Video.BaseURL
		}
		if len(info.Video.URLs) > 0 {
			return info.Video.URLs[0]
		}
	}
	if info.DASHURL != "" {
		return info.DASHURL
	}
	return ""
}

func chooseIqiyiStream(info *iqiyi.VideoInfo) (string, preferredStream) {
	bestScore := -1
	bestURL := ""
	bestType := preferredStream{}

	for _, stream := range info.Streams {
		score := iqiyiQualityScore(stream.Quality)
		if stream.M3U8URL != "" && score*10+1 > bestScore {
			bestScore = score*10 + 1
			bestURL = stream.M3U8URL
			bestType = preferredStream{kind: "hls", fileExt: ".ts"}
		}
		if stream.DASHURL != "" && score*10 > bestScore {
			bestScore = score * 10
			bestURL = stream.DASHURL
			bestType = preferredStream{kind: "dash", fileExt: ".mp4"}
		}
	}
	if bestURL != "" {
		return bestURL, bestType
	}
	if info.M3U8URL != "" {
		return info.M3U8URL, preferredStream{kind: "hls", fileExt: ".ts"}
	}
	if info.DASHURL != "" {
		return info.DASHURL, preferredStream{kind: "dash", fileExt: ".mp4"}
	}
	return "", preferredStream{}
}

func iqiyiQualityScore(quality string) int {
	normalized := strings.ToLower(strings.TrimSpace(quality))
	switch {
	case strings.Contains(normalized, "4k"):
		return 6
	case strings.Contains(normalized, "1080"):
		return 5
	case strings.Contains(normalized, "720"):
		return 4
	case strings.Contains(normalized, "480"):
		return 3
	case strings.Contains(normalized, "360"):
		return 2
	case normalized != "":
		return 1
	default:
		return 0
	}
}

func youkuQualityScore(quality string, width int, height int) int {
	score := iqiyiQualityScore(quality)
	if score > 0 {
		return score
	}
	switch {
	case height >= 2160 || width >= 3840:
		return 6
	case height >= 1080 || width >= 1920:
		return 5
	case height >= 720 || width >= 1280:
		return 4
	case height >= 480 || width >= 854:
		return 3
	case height >= 360 || width >= 640:
		return 2
	case height > 0 || width > 0:
		return 1
	default:
		return 0
	}
}

func tencentQualityScore(format tencent.VideoFormat) int {
	if format.QualityID > 0 {
		return format.QualityID
	}
	return iqiyiQualityScore(format.Quality)
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return ""
}

func mediaFilename(title, fallback, ext string) string {
	name := strings.TrimSpace(title)
	if name == "" {
		name = fallback
	}
	if name == "" {
		name = "media"
	}
	replacer := strings.NewReplacer(
		"<", "", ">", "", ":", "", "\"", "",
		"/", "", "\\", "", "|", "", "?", "", "*", "",
	)
	name = replacer.Replace(name)
	name = strings.TrimSpace(name)
	if len(name) > 100 {
		name = name[:100]
	}
	if ext == "" {
		ext = ".mp4"
	}
	if !strings.HasPrefix(ext, ".") {
		ext = "." + ext
	}
	return name + ext
}
