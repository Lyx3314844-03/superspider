package main

import (
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"gospider/extractors/tencent"
)

func main() {
	// 命令行参数
	url := flag.String("url", "https://v.qq.com/x/cover/mzc00200rgazpwa/c4102t9ai7s.html", "腾讯视频 URL")
	outputDir := flag.String("o", "./downloads/tencent", "输出目录")
	download := flag.Bool("d", true, "是否下载视频")
	flag.Parse()

	fmt.Println("╔══════════════════════════════════════════════════════════╗")
	fmt.Println("║           gospider 腾讯视频下载器                         ║")
	fmt.Println("╚══════════════════════════════════════════════════════════╝")
	fmt.Println()

	// 创建输出目录
	os.MkdirAll(*outputDir, 0755)

	// 创建解析器
	extractor := tencent.NewTencentExtractor()

	fmt.Printf("📺 解析视频：%s\n", *url)
	fmt.Println()

	// 提取视频信息
	info, err := extractor.Extract(*url)
	if err != nil {
		fmt.Printf("❌ 解析失败：%v\n", err)
		fmt.Println()
		fmt.Println("提示：腾讯视频可能有 DRM 保护或需要 VIP")
		os.Exit(1)
	}

	// 显示视频信息
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Printf("标题：%s\n", info.Title)
	fmt.Printf("描述：%s\n", info.Description)
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Println()

	if len(info.Formats) == 0 {
		fmt.Println("⚠️  未找到可用的视频格式")
		fmt.Println()
		fmt.Println("可能的原因:")
		fmt.Println("  1. 视频需要 VIP 会员")
		fmt.Println("  2. 视频有 DRM 保护")
		fmt.Println("  3. 视频链接已过期")
		fmt.Println()
		fmt.Println("建议:")
		fmt.Println("  - 使用浏览器播放视频后，使用网络监控工具捕获链接")
		fmt.Println("  - 使用 gospider 的 network monitor 功能")
		os.Exit(1)
	}

	// 显示可用格式
	fmt.Println("可用格式:")
	for i, format := range info.Formats {
		fmt.Printf("  %d. %s\n", i+1, format.Quality)
		fmt.Printf("     URL: %s\n", format.URL)
		fmt.Println()
	}

	if !*download {
		fmt.Println("✅ 解析完成，未下载视频")
		os.Exit(0)
	}

	// 下载视频
	fmt.Println("📥 开始下载视频...")
	fmt.Println()

	downloadURL := info.Formats[0].URL
	
	// 生成文件名
	filename := sanitizeFilename(info.Title) + ".mp4"
	outputFile := filepath.Join(*outputDir, filename)

	err = downloadVideo(downloadURL, outputFile)
	if err != nil {
		fmt.Printf("❌ 下载失败：%v\n", err)
		os.Exit(1)
	}

	fmt.Println()
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Printf("✅ 下载完成：%s\n", outputFile)
	fmt.Println("═══════════════════════════════════════════════════════════")
}

// downloadVideo 下载视频
func downloadVideo(url, outputFile string) error {
	fmt.Printf("下载链接：%s\n", url)
	fmt.Printf("保存位置：%s\n\n", outputFile)

	client := &http.Client{
		Timeout: 0, // 下载超时禁用
	}

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}

	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
	req.Header.Set("Referer", "https://v.qq.com/")

	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return fmt.Errorf("HTTP 状态码：%d", resp.StatusCode)
	}

	// 创建文件
	file, err := os.Create(outputFile)
	if err != nil {
		return err
	}
	defer file.Close()

	// 下载进度
	total := resp.ContentLength
	written := int64(0)
	buffer := make([]byte, 32*1024)

	startTime := time.Now()

	fmt.Println("下载进度:")
	for {
		n, err := resp.Body.Read(buffer)
		if n > 0 {
			written += int64(n)
			file.Write(buffer[:n])

			// 显示进度
			if total > 0 {
				percent := float64(written) / float64(total) * 100
				speed := float64(written) / time.Since(startTime).Seconds() / 1024 / 1024
				fmt.Printf("\r  [%5.1f%%] %.2f MB/s", percent, speed)
			}
		}

		if err != nil {
			if err == io.EOF {
				break
			}
			return err
		}
	}

	fmt.Println()
	fmt.Printf("\n  总大小：%.2f MB\n", float64(written)/1024/1024)
	fmt.Printf("  用时：%s\n", time.Since(startTime))

	return nil
}

// sanitizeFilename 清理文件名
func sanitizeFilename(filename string) string {
	// 替换非法字符
	illegal := []string{"\\", "/", ":", "*", "?", "\"", "<", ">", "|"}
	for _, c := range illegal {
		filename = strings.ReplaceAll(filename, c, "_")
	}
	return filename
}
