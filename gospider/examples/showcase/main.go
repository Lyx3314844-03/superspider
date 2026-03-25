package main

import (
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
	"gospider/core"
	"gospider/downloader"
	"gospider/parser"
	"gospider/queue"
)

/**
 通用网页爬虫示例
 演示如何使用 gospider 爬取一般网站
*/

func RunGeneralSpider() {
	fmt.Println("╔═══════════════════════════════════════════════════════════╗")
	fmt.Println("║           gospider 通用网页爬虫示例                        ║")
	fmt.Println("╚═══════════════════════════════════════════════════════════╝")
	fmt.Println()

	config := core.DefaultSpiderConfig()
	config.Name = "GeneralSpider"
	config.Concurrency = 5

	spider := core.NewSpider(config)
	spider.SetOnResponse(func(req *queue.Request, resp *http.Response) error {
		body, err := io.ReadAll(resp.Body)
		if err != nil {
			return err
		}

		// 提取标题
		htmlParser := parser.NewHTMLParser(string(body))
		title := htmlParser.CSSFirst("title")
		fmt.Printf("  📄 页面标题：%s\n", title)

		// 提取所有链接
		links := htmlParser.Links()
		fmt.Printf("  🔗 找到 %d 个链接\n", len(links))

		// 提取所有图片
		images := htmlParser.Images()
		fmt.Printf("  🖼️  找到 %d 张图片\n", len(images))

		return nil
	})

	// 设置起始 URL
	startURLs := []string{
		"https://www.example.com",
		"https://www.httpbin.org/html",
	}

	if err := spider.AddRequests(startURLs); err != nil {
		fmt.Printf("❌ 添加请求失败：%v\n", err)
		return
	}

	for _, url := range startURLs {
		fmt.Printf("\n🕷️  准备爬取：%s\n", url)
	}

	if err := spider.Run(); err != nil {
		fmt.Printf("❌ 爬取失败：%v\n", err)
	}

	fmt.Println("✅ 爬取完成!")
}

/**
 新闻网站爬虫示例
 爬取新闻标题、链接、发布时间等
*/

type NewsItem struct {
	Title     string
	Link      string
	Author    string
	PubTime   string
	Summary   string
}

func RunNewsSpider() {
	fmt.Println("╔═══════════════════════════════════════════════════════════╗")
	fmt.Println("║           gospider 新闻网站爬虫示例                          ║")
	fmt.Println("╚═══════════════════════════════════════════════════════════╝")
	fmt.Println()

	config := core.DefaultSpiderConfig()
	config.Name = "NewsSpider"
	config.Concurrency = 3
	spider := core.NewSpider(config)

	var newsItems []NewsItem

	// 添加新闻提取管道
	spider.SetOnResponse(func(req *queue.Request, resp *http.Response) error {
		body, err := io.ReadAll(resp.Body)
		if err != nil {
			return err
		}

		htmlParser := parser.NewHTMLParser(string(body))

		// 提取新闻标题（根据实际网站结构调整选择器）
		titles := htmlParser.CSS("h2 a, h3 a, .title a")
		for _, title := range titles {
			if title != "" {
				newsItems = append(newsItems, NewsItem{
					Title: title,
					Link:  req.URL,
				})
			}
		}

		return nil
	})

	// 示例 URL（实际使用时替换为真实新闻网站）
	if err := spider.AddRequests([]string{"https://www.httpbin.org/html"}); err != nil {
		fmt.Printf("❌ 添加请求失败：%v\n", err)
		return
	}
	fmt.Println("📰 开始爬取新闻...")
	if err := spider.Run(); err != nil {
		fmt.Printf("❌ 爬取失败：%v\n", err)
		return
	}

	fmt.Printf("\n✅ 共提取 %d 条新闻\n", len(newsItems))
	for i, news := range newsItems {
		fmt.Printf("%d. %s\n", i+1, news.Title)
	}
}

/**
 图片批量下载示例
 爬取网页中的所有图片并下载
*/

func RunImageDownloader() {
	fmt.Println("╔═══════════════════════════════════════════════════════════╗")
	fmt.Println("║           gospider 图片批量下载示例                          ║")
	fmt.Println("╚═══════════════════════════════════════════════════════════╝")
	fmt.Println()

	url := "https://www.httpbin.org/html"
	fmt.Printf("🖼️  准备下载图片：%s\n\n", url)

	// 创建下载器
	dl := downloader.NewDownloader()

	// 创建请求
	req := &downloader.Request{
		URL:    url,
		Method: "GET",
	}

	// 下载页面
	resp := dl.Download(req)
	if resp.Error != nil {
		fmt.Printf("❌ 下载失败：%v\n", resp.Error)
		return
	}

	// 解析 HTML
	htmlParser := parser.NewHTMLParser(resp.Text)

	// 提取图片
	images := htmlParser.Images()
	fmt.Printf("📸 找到 %d 张图片:\n", len(images))

	for i, img := range images {
		fmt.Printf("  %d. %s\n", i+1, img)
	}

	fmt.Println("\n✅ 图片提取完成!")
}

/**
 API 数据抓取示例
 爬取 JSON API 数据
*/

func RunAPIScraper() {
	fmt.Println("╔═══════════════════════════════════════════════════════════╗")
	fmt.Println("║           gospider API 数据抓取示例                          ║")
	fmt.Println("╚═══════════════════════════════════════════════════════════╝")
	fmt.Println()

	// API URL
	apiURL := "https://api.github.com/repos/golang/go"
	fmt.Printf("🔌 请求 API: %s\n\n", apiURL)

	// 创建下载器
	dl := downloader.NewDownloader()

	// 创建请求
	req := &downloader.Request{
		URL:    apiURL,
		Method: "GET",
		Headers: map[string]string{
			"Accept": "application/vnd.github.v3+json",
			"User-Agent": "gospider/1.0",
		},
	}

	// 发送请求
	resp := dl.Download(req)
	if resp.Error != nil {
		fmt.Printf("❌ 请求失败：%v\n", resp.Error)
		return
	}

	// 解析 JSON
	jsonParser := parser.NewJSONParser(resp.Text)

	// 提取字段
	name := jsonParser.Get("name")
	description := jsonParser.Get("description")
	stars := jsonParser.Get("stargazers_count")
	forks := jsonParser.Get("forks_count")
	language := jsonParser.Get("language")

	fmt.Println("📊 仓库信息:")
	fmt.Printf("  名称：%s\n", getString(name))
	fmt.Printf("  描述：%s\n", getString(description))
	fmt.Printf("  Stars: %s\n", getString(stars))
	fmt.Printf("  Forks: %s\n", getString(forks))
	fmt.Printf("  语言：%s\n", getString(language))

	fmt.Println("\n✅ API 数据获取完成!")
}

func getString(v interface{}) string {
	if v == nil {
		return "N/A"
	}
	return fmt.Sprintf("%v", v)
}

/**
 批量运行所有示例
*/

func RunAllExamples() {
	fmt.Println("\n" + strings.Repeat("═", 60))
	fmt.Println("  gospider 示例集合")
	fmt.Println(strings.Repeat("═", 60) + "\n")

	// 示例 1: 通用爬虫
	RunGeneralSpider()
	time.Sleep(1 * time.Second)

	// 示例 2: 新闻爬虫
	// RunNewsSpider()
	// time.Sleep(1 * time.Second)

	// 示例 3: 图片下载
	// RunImageDownloader()
	// time.Sleep(1 * time.Second)

	// 示例 4: API 抓取
	RunAPIScraper()

	fmt.Println("\n" + strings.Repeat("═", 60))
	fmt.Println("  所有示例运行完成!")
	fmt.Println(strings.Repeat("═", 60) + "\n")
}

func main() {
	RunAllExamples()
}
