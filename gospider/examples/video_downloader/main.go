package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/chromedp/chromedp"

	"gospider/media"
	"gospider/network"
)

func main() {
	// 命令行参数
	url := flag.String("url", "", "视频页面 URL")
	outputDir := flag.String("o", "./downloads", "输出目录")
	quality := flag.String("q", "best", "清晰度 (best, 1080p, 720p, 480p)")
	proxy := flag.String("proxy", "", "代理服务器")
	timeout := flag.Int("t", 120, "超时时间（秒）")
	flag.Parse()

	if *url == "" {
		fmt.Println("用法：video_downloader -url <视频 URL> [选项]")
		fmt.Println("\n选项:")
		flag.PrintDefaults()
		fmt.Println("\n示例:")
		fmt.Println("  video_downloader -url \"https://www.youku.tv/v/xxx\"")
		fmt.Println("  video_downloader -url \"https://www.youku.tv/v/xxx\" -q 1080p -o ./videos")
		os.Exit(1)
	}

	fmt.Println("=== gospider 视频下载器 ===")
	fmt.Printf("URL: %s\n", *url)
	fmt.Printf("输出目录：%s\n", *outputDir)
	fmt.Printf("清晰度：%s\n", *quality)
	fmt.Println()

	// 创建输出目录
	os.MkdirAll(*outputDir, 0755)

	// 创建视频监控器
	monitor := network.NewVideoMonitor()

	// 设置浏览器选项
	opts := append(chromedp.DefaultExecAllocatorOptions[:],
		chromedp.Flag("headless", true),
		chromedp.WindowSize(1920, 1080),
		chromedp.UserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
	)

	if *proxy != "" {
		opts = append(opts, chromedp.ProxyServer(*proxy))
	}

	allocCtx, cancel := chromedp.NewExecAllocator(context.Background(), opts...)
	defer cancel()

	ctx, cancel := chromedp.NewContext(allocCtx)
	defer cancel()

	ctx, cancel = context.WithTimeout(ctx, time.Duration(*timeout)*time.Second)
	defer cancel()

	// 设置监听
	monitor.SetupListener(ctx)

	fmt.Println("正在访问页面并捕获视频链接...")

	var title string
	err := chromedp.Run(ctx,
		chromedp.Navigate(*url),
		chromedp.Sleep(10*time.Second),
		chromedp.Title(&title),
	)

	if err != nil {
		fmt.Printf("访问页面失败：%v\n", err)
	}

	fmt.Printf("\n视频标题：%s\n\n", title)

	// 显示统计
	stats := monitor.GetStats()
	fmt.Printf("捕获到的请求:\n")
	fmt.Printf("  总计：%d\n", stats["total"])
	fmt.Printf("  视频：%d\n", stats["video"])
	fmt.Printf("  HLS:  %d\n", stats["hls"])
	fmt.Printf("  DASH: %d\n", stats["dash"])
	fmt.Printf("  音频：%d\n\n", stats["audio"])

	// 获取视频 URL
	videoURLs := monitor.GetVideoURLs()
	hlsURLs := monitor.GetHLSURLs()

	if len(videoURLs) == 0 && len(hlsURLs) == 0 {
		fmt.Println("未找到视频链接")
		os.Exit(1)
	}

	// 导出 URL
	urlsFile := filepath.Join(*outputDir, "video_urls.txt")
	monitor.ExportURLs(urlsFile)
	fmt.Printf("视频链接已导出到：%s\n\n", urlsFile)

	// 下载视频
	if len(hlsURLs) > 0 {
		fmt.Println("发现 HLS 流，使用 ffmpeg 下载...")
		
		// 检测 ffmpeg
		ffmpegPath, err := media.AutoDetectFFmpeg()
		if err != nil {
			fmt.Printf("FFmpeg 未安装：%v\n", err)
			fmt.Println("请安装 FFmpeg: winget install Gyan.FFmpeg")
		} else {
			fmt.Printf("FFmpeg 路径：%s\n\n", ffmpegPath)

			hlsDownloader := media.NewHLSDownloader(*outputDir)
			
			for i, hlsURL := range hlsURLs {
				outputFile := filepath.Join(*outputDir, fmt.Sprintf("video_%d.mp4", i))
				fmt.Printf("正在下载 HLS 流 %d/%d: %s\n", i+1, len(hlsURLs), hlsURL)
				
				err := hlsDownloader.DownloadWithFFmpeg(ffmpegPath, hlsURL, outputFile)
				if err != nil {
					fmt.Printf("下载失败：%v\n", err)
				} else {
					fmt.Printf("下载成功：%s\n\n", outputFile)
				}
			}
		}
	}

	if len(videoURLs) > 0 {
		fmt.Println("发现直接视频链接...")
		
		downloader := media.NewMediaDownloader(*outputDir)
		
		for i, videoURL := range videoURLs {
			outputFile := filepath.Join(*outputDir, fmt.Sprintf("video_direct_%d.mp4", i))
			fmt.Printf("正在下载 %d/%d: %s\n", i+1, len(videoURLs), videoURL)
			
			result := downloader.DownloadVideo(videoURL, outputFile)
			if result.Success {
				fmt.Printf("下载成功：%s (%.2f MB)\n\n", result.Path, float64(result.Size)/1024/1024)
			} else {
				fmt.Printf("下载失败：%s\n\n", result.Error)
			}
		}
	}

	// 检查 DRM
	fmt.Println("检查视频是否加密...")
	ffmpegPath, err := media.AutoDetectFFmpeg()
	if err == nil {
		ffmpeg := media.NewFFmpegWrapper(ffmpegPath, *outputDir)
		
		files, _ := filepath.Glob(filepath.Join(*outputDir, "*.mp4"))
		for _, file := range files {
			isDRM, drmType, _ := ffmpeg.CheckDRM(file)
			if isDRM {
				fmt.Printf("⚠️  %s - 检测到 DRM 加密：%s\n", filepath.Base(file), drmType)
				fmt.Println("   该视频需要解密才能播放")
			} else {
				fmt.Printf("✓ %s - 无 DRM 加密\n", filepath.Base(file))
			}
		}
	}

	fmt.Println("\n=== 下载完成 ===")
	fmt.Printf("文件保存在：%s\n", *outputDir)
}
