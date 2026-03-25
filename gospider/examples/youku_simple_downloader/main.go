package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"time"

	"github.com/chromedp/chromedp"
)

func main() {
	url := "https://www.youku.tv/v/v_show/id_XNTk4Mjg1MjEzMg==.html?spm=a2hja.14919748_WEBMOVIE_JINGXUAN.drawer2.d_zj1_1&s=cfeb97262f9f4d29b86b&scm=20140719.manual.37330.show_cfeb97262f9f4d29b86b&s=cfeb97262f9f4d29b86b"

	fmt.Println("=== 优酷视频下载器 ===")
	fmt.Println("正在初始化浏览器...")

	// 创建 chromedp 上下文
	opts := append(chromedp.DefaultExecAllocatorOptions[:],
		chromedp.Flag("headless", false),
		chromedp.WindowSize(1920, 1080),
		chromedp.UserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
	)

	allocCtx, cancel := chromedp.NewExecAllocator(context.Background(), opts...)
	defer cancel()

	ctx, cancel := chromedp.NewContext(allocCtx)
	defer cancel()

	// 设置超时
	ctx, cancel = context.WithTimeout(ctx, 120*time.Second)
	defer cancel()

	// 输出目录
	outputDir := filepath.Join("C:\\Users\\Administrator\\spider\\gospider\\downloads", "youku")
	os.MkdirAll(outputDir, 0755)

	fmt.Printf("下载目录：%s\n\n", outputDir)

	var title string
	var pageHTML string
	var allVideoURLs string

	// 导航到页面并提取信息
	err := chromedp.Run(ctx,
		chromedp.Navigate(url),
		
		// 等待页面加载
		chromedp.Sleep(5*time.Second),
		
		// 获取标题
		chromedp.Title(&title),
		
		// 获取页面 HTML
		chromedp.OuterHTML("html", &pageHTML),
		
		// 尝试获取视频播放器中的视频源
		chromedp.Evaluate(`() => {
			const result = { videoUrls: [], hlsUrls: [], dashUrls: [] };
			
			// 查找所有 video 标签
			document.querySelectorAll('video').forEach(v => {
				if (v.src) result.videoUrls.push(v.src);
				v.querySelectorAll('source').forEach(s => {
					if (s.src) result.videoUrls.push(s.src);
				});
			});
			
			// 查找 m3u8 链接
			const text = document.documentElement.outerHTML;
			const m3u8Regex = /https?:\/\/[^"'\s<>]+\.m3u8[^"'\s<>]*/gi;
			const m3u8Matches = text.match(m3u8Regex) || [];
			result.hlsUrls = [...new Set(m3u8Matches)];
			
			// 查找 mp4 链接
			const mp4Regex = /https?:\/\/[^"'\s<>]+\.mp4[^"'\s<>]*/gi;
			const mp4Matches = text.match(mp4Regex) || [];
			result.videoUrls = [...new Set([...result.videoUrls, ...mp4Matches])];
			
			return result;
		}`, &allVideoURLs),
	)

	if err != nil {
		fmt.Printf("执行失败：%v\n", err)
	}

	fmt.Printf("视频标题：%s\n\n", title)
	fmt.Printf("找到的视频链接:\n%s\n\n", allVideoURLs)

	// 保存页面源码
	htmlFile := filepath.Join(outputDir, "page_source.html")
	err = os.WriteFile(htmlFile, []byte(pageHTML), 0644)
	if err != nil {
		fmt.Printf("保存 HTML 失败：%v\n", err)
	} else {
		fmt.Printf("页面源码已保存到：%s\n", htmlFile)
	}

	// 从 HTML 中提取视频链接
	videoRe := regexp.MustCompile(`https?://[^\s"'<>]+\.(mp4|m3u8)[^\s"'<>]*`)
	matches := videoRe.FindAllString(pageHTML, -1)

	if len(matches) > 0 {
		fmt.Println("\n=== 提取到的视频链接 ===")
		seen := make(map[string]bool)
		for i, match := range matches {
			if !seen[match] {
				seen[match] = true
				fmt.Printf("%d. %s\n", i+1, match)
			}
		}

		// 保存视频链接到文件
		linksFile := filepath.Join(outputDir, "video_links.txt")
		content := fmt.Sprintf("标题：%s\n\n视频链接:\n", title)
		for _, link := range matches {
			if !seen[link] {
				continue
			}
			content += link + "\n"
		}
		os.WriteFile(linksFile, []byte(content), 0644)
		fmt.Printf("\n视频链接已保存到：%s\n", linksFile)
	} else {
		fmt.Println("\n未找到直接的 mp4/m3u8 视频链接")
		fmt.Println("优酷视频可能需要使用专用下载工具或 API 解析")
	}

	fmt.Println("\n=== 完成 ===")
	fmt.Println("提示：优酷视频通常有 DRM 保护，可能需要使用专用工具下载")
}
