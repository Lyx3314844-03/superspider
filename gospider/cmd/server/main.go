package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"gospider/api"
	"gospider/distributed"
	"gospider/monitor"
)

func main() {
	// 命令行参数
	redisAddr := flag.String("redis", "localhost:6379", "Redis 地址")
	redisPassword := flag.String("redis-pass", "", "Redis 密码")
	redisDB := flag.Int("redis-db", 0, "Redis 数据库")
	apiHost := flag.String("api-host", "0.0.0.0", "API 服务器地址")
	apiPort := flag.Int("api-port", 8080, "API 服务器端口")
	outputDir := flag.String("output", "./downloads", "输出目录")
	flag.Parse()

	fmt.Println("╔══════════════════════════════════════════════════════════╗")
	fmt.Println("║           gospider 分布式爬虫服务器                       ║")
	fmt.Println("╚══════════════════════════════════════════════════════════╝")
	fmt.Println()

	// 创建输出目录
	os.MkdirAll(*outputDir, 0755)

	// 连接 Redis
	fmt.Println("📡 连接 Redis...")
	redisClient, err := distributed.NewRedisClient(*redisAddr, *redisPassword, *redisDB)
	if err != nil {
		log.Fatalf("连接 Redis 失败：%v", err)
	}
	defer redisClient.Close()
	fmt.Println("✅ Redis 连接成功")

	// 创建监控器
	fmt.Println("📊 初始化监控器...")
	mon := monitor.NewMonitor(redisClient)
	if err := mon.Start(); err != nil {
		log.Fatalf("启动监控失败：%v", err)
	}
	fmt.Println("✅ 监控器已启动")

	// 创建 API 服务器
	fmt.Println("🚀 初始化 API 服务器...")
	apiConfig := &api.Config{
		Host:       *apiHost,
		Port:       *apiPort,
		EnableCORS: true,
	}
	apiServer := api.NewServer(apiConfig, redisClient, mon)

	// 设置信号处理
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// 启动 API 服务器（在后台）
	go func() {
		if err := apiServer.Start(); err != nil {
			log.Fatalf("API 服务器错误：%v", err)
		}
	}()

	// 打印使用信息
	fmt.Println()
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Println("📌 服务已启动")
	fmt.Println()
	fmt.Printf("   API 地址：http://%s:%d\n", *apiHost, *apiPort)
	fmt.Printf("   监控面板：http://%s:%d/ui/\n", *apiHost, *apiPort)
	fmt.Printf("   健康检查：http://%s:%d/api/v1/health\n", *apiHost, *apiPort)
	fmt.Printf("   统计信息：http://%s:%d/api/v1/stats\n", *apiHost, *apiPort)
	fmt.Println()
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Println("📖 快速开始:")
	fmt.Println()
	fmt.Println("   # 创建视频下载任务")
	fmt.Println("   curl -X POST http://localhost:8080/api/v1/download/video \\")
	fmt.Println("     -H 'Content-Type: application/json' \\")
	fmt.Println("     -d '{\"url\": \"https://example.com/video.mp4\"}'")
	fmt.Println()
	fmt.Println("   # 创建 HLS 下载任务")
	fmt.Println("   curl -X POST http://localhost:8080/api/v1/download/hls \\")
	fmt.Println("     -H 'Content-Type: application/json' \\")
	fmt.Println("     -d '{\"m3u8_url\": \"https://example.com/playlist.m3u8\"}'")
	fmt.Println()
	fmt.Println("   # 查看任务状态")
	fmt.Println("   curl http://localhost:8080/api/v1/tasks/{task_id}")
	fmt.Println()
	fmt.Println("   # 查看系统统计")
	fmt.Println("   curl http://localhost:8080/api/v1/stats")
	fmt.Println()
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Println("按 Ctrl+C 停止服务...")
	fmt.Println()

	// 等待退出信号
	<-sigChan

	fmt.Println()
	fmt.Println("👋 正在关闭服务...")

	// 停止监控器
	mon.Stop()

	fmt.Println("✅ 服务已关闭")
}
