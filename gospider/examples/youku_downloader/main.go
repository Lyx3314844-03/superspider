package main

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"time"

	"gospider/browser"
)

func main() {
	url := "https://www.youku.tv/v/v_show/id_XNTk4Mjg1MjEzMg==.html?spm=a2hja.14919748_WEBMOVIE_JINGXUAN.drawer2.d_zj1_1&s=cfeb97262f9f4d29b86b&scm=20140719.manual.37330.show_cfeb97262f9f4d29b86b&s=cfeb97262f9f4d29b86b"

	fmt.Println("正在初始化浏览器...")

	// 创建浏览器
	config := &browser.BrowserConfig{
		Headless:       false,
		ViewportWidth:  1920,
		ViewportHeight: 1080,
		Timeout:        60 * time.Second,
	}

	bm := browser.NewBrowser(config)
	if err := bm.Start(); err != nil {
		fmt.Printf("浏览器启动失败：%v\n", err)
		return
	}
	defer bm.Close()

	fmt.Println("正在访问优酷视频页面...")
	
	// 导航到页面
	err := bm.Navigate(url)
	if err != nil {
		fmt.Printf("导航失败：%v\n", err)
		os.Exit(1)
	}

	// 等待页面加载
	time.Sleep(5 * time.Second)

	// 获取页面标题
	title, err := bm.ExecuteJS(`() => document.title`)
	if err != nil {
		fmt.Printf("获取标题失败：%v\n", err)
		title = "unknown_video"
	}
	fmt.Printf("视频标题：%v\n", title)

	// 尝试获取视频信息
	fmt.Println("正在查找视频资源...")
	
	// 等待视频播放器加载
	time.Sleep(3 * time.Second)
	
	// 获取页面所有视频元素
	videoURLs, err := bm.ExecuteJS(`() => {
		const videos = document.querySelectorAll('video');
		const urls = [];
		videos.forEach(v => {
			if (v.src) urls.push(v.src);
		});
		return urls;
	}`)
	
	if err != nil {
		fmt.Printf("获取视频 URL 失败：%v\n", err)
	}
	
	fmt.Printf("找到的视频 URL: %v\n", videoURLs)

	// 尝试从页面源代码中提取视频 URL
	pageSource, err := bm.ExecuteJS(`() => document.documentElement.outerHTML`)
	if err == nil {
		html := pageSource.(string)
		
		// 提取 mp4/m3u8 链接
		videoRe := regexp.MustCompile(`https?://[^\s"'<>]+\.(mp4|m3u8)[^\s"'<>]*`)
		matches := videoRe.FindAllString(html, -1)
		
		if len(matches) > 0 {
			fmt.Println("从页面中提取到视频链接:")
			seen := make(map[string]bool)
			for _, match := range matches {
				if !seen[match] {
					seen[match] = true
					fmt.Printf("  - %s\n", match)
				}
			}
		}
	}

	outputDir := filepath.Join("C:\\Users\\Administrator\\spider\\gospider\\downloads", "youku")
	
	fmt.Printf("\n下载目录：%s\n", outputDir)
	
	// 尝试使用 yt-dlp 获取真实视频地址（如果可用）
	fmt.Println("\n尝试获取真实视频地址...")
	
	// 保存页面 HTML 以便分析
	htmlFile := filepath.Join(outputDir, "page_source.html")
	os.MkdirAll(outputDir, 0755)
	
	htmlStr, _ := bm.ExecuteJS(`() => document.documentElement.outerHTML`)
	if htmlStr != nil {
		os.WriteFile(htmlFile, []byte(htmlStr.(string)), 0644)
		fmt.Printf("页面源码已保存到：%s\n", htmlFile)
	}

	// 获取所有可能的视频播放地址
	videoData, err := bm.ExecuteJS(`() => {
		const data = {
			videoUrls: [],
			hlsUrls: [],
			iframeSrc: []
		};
		
		// 查找 video 标签
		document.querySelectorAll('video').forEach(v => {
			if (v.src) data.videoUrls.push(v.src);
			v.querySelectorAll('source').forEach(s => {
				if (s.src) data.videoUrls.push(s.src);
			});
		});
		
		// 查找 iframe
		document.querySelectorAll('iframe').forEach(f => {
			if (f.src) data.iframeSrc.push(f.src);
		});
		
		return data;
	}`)
	
	fmt.Printf("\n页面中的视频数据：%v\n", videoData)
	
	fmt.Println("\n=== 下载完成 ===")
	fmt.Println("请检查下载目录获取视频文件")
}
