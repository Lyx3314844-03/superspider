package main

import (
	"flag"
	"fmt"
	"os"

	"gospider/core"
	"gospider/queue"
)

const version = "2.0.0"

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	// 版本检查
	if os.Args[1] == "version" || os.Args[1] == "-v" || os.Args[1] == "--version" {
		fmt.Printf("gospider version %s\n", version)
		os.Exit(0)
	}

	// 命令处理
	command := os.Args[1]
	switch command {
	case "crawl":
		crawlCmd := flag.NewFlagSet("crawl", flag.ExitOnError)
		url := crawlCmd.String("url", "", "target URL to crawl")
		depth := crawlCmd.Int("depth", 3, "crawl depth")
		concurrency := crawlCmd.Int("concurrency", 5, "concurrency level")
		_ = crawlCmd.Parse(os.Args[2:])

		if *url == "" {
			fmt.Println("Error: --url is required")
			os.Exit(1)
		}

		fmt.Printf("Starting crawl: %s (depth=%d, concurrency=%d)\n", *url, *depth, *concurrency)

		// 创建配置
		config := core.DefaultSpiderConfig()
		config.Concurrency = *concurrency

		// 创建爬虫实例
		spider := core.NewSpider(config)

		// 添加请求
		req := &queue.Request{
			URL:      *url,
			Method:   "GET",
			Headers:  map[string]string{"User-Agent": "gospider/2.0"},
			Priority: 0,
		}
		if err := spider.AddRequest(req); err != nil {
			fmt.Printf("Failed to add request: %v\n", err)
			os.Exit(1)
		}

		fmt.Println("Crawl started successfully")

	case "doctor":
		// 运行诊断
		fmt.Println("Running diagnostics...")
		// 诊断逻辑在 doctor.go 中实现
	default:
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Printf("gospider %s - A powerful web crawler\n\n", version)
	fmt.Println("Usage:")
	fmt.Println("  gospider <command> [options]")
	fmt.Println()
	fmt.Println("Commands:")
	fmt.Println("  crawl      Crawl a website")
	fmt.Println("  doctor     Run diagnostics")
	fmt.Println("  version    Show version")
	fmt.Println()
	fmt.Println("Examples:")
	fmt.Println("  gospider crawl --url https://example.com --depth 3 --concurrency 5")
	fmt.Println("  gospider doctor")
	fmt.Println("  gospider version")
}
