package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"gospider/distributed"
)

func main() {
	// 命令行参数
	workerID := flag.String("id", "", "工作节点 ID")
	host := flag.String("host", "localhost", "主机地址")
	port := flag.Int("port", 0, "端口（0=自动）")
	redisAddr := flag.String("redis", "localhost:6379", "Redis 地址")
	redisPassword := flag.String("redis-pass", "", "Redis 密码")
	redisDB := flag.Int("redis-db", 0, "Redis 数据库")
	outputDir := flag.String("output", "./downloads", "输出目录")
	ffmpegPath := flag.String("ffmpeg", "", "FFmpeg 路径")
	flag.Parse()

	fmt.Println("╔══════════════════════════════════════════════════════════╗")
	fmt.Println("║           gospider 分布式工作节点                         ║")
	fmt.Println("╚══════════════════════════════════════════════════════════╝")
	fmt.Println()

	// 创建输出目录
	os.MkdirAll(*outputDir, 0755)

	// 创建工作节点
	config := &distributed.WorkerConfig{
		ID:            *workerID,
		Host:          *host,
		Port:          *port,
		RedisAddr:     *redisAddr,
		RedisPassword: *redisPassword,
		RedisDB:       *redisDB,
		OutputDir:     *outputDir,
		FFmpegPath:    *ffmpegPath,
	}

	fmt.Println("📡 连接 Redis...")
	worker, err := distributed.NewWorker(config)
	if err != nil {
		log.Fatalf("创建工作节点失败：%v", err)
	}

	// 设置信号处理
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// 启动工作节点
	fmt.Println("🚀 启动工作节点...")
	if err := worker.Start(); err != nil {
		log.Fatalf("启动工作节点失败：%v", err)
	}

	fmt.Println("✅ 工作节点已启动")
	fmt.Println()
	fmt.Println("═══════════════════════════════════════════════════════════")
	fmt.Printf("   节点 ID: %s\n", worker.ID)
	fmt.Printf("   输出目录：%s\n", *outputDir)
	fmt.Println()
	fmt.Println("等待任务...")
	fmt.Println("按 Ctrl+C 停止节点...")
	fmt.Println()

	// 等待退出信号
	<-sigChan

	fmt.Println()
	fmt.Println("👋 正在关闭节点...")

	// 停止工作节点
	worker.Stop()

	fmt.Println("✅ 节点已关闭")
}
