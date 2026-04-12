package main

import (
	"fmt"
	"gospider/distributed"
	"gospider/core"
	"log"
)

func main() {
	// 创建分布式爬虫 (指向统一队列)
	spider := distributed.NewDistributedSpider("GoSpiderNode", "localhost:6379", "", 0)
	spider.SetThreadCount(2)

	fmt.Println("Go 分布式爬虫节点启动...")
	
	// 启动并设置回调
	spider.Start(func(req *core.Request) error {
		log.Printf("[Go] 正在处理: %s", req.URL)
		return nil
	})
}
