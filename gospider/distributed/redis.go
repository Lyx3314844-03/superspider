package distributed

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/go-redis/redis/v8"
	"gospider/core"
	"log"
	"time"
)

// RedisScheduler 分布式调度器
type RedisScheduler struct {
	client     *redis.Client
	ctx        context.Context
	queueKey   string
	visitedKey string
	statsKey   string
}

// NewRedisScheduler 创建分布式调度器
func NewRedisScheduler(addr, password string, db int, spiderName string) *RedisScheduler {
	client := redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: password,
		DB:       db,
	})

	ctx := context.Background()

	return &RedisScheduler{
		client:     client,
		ctx:        ctx,
		queueKey:   "gospider:" + spiderName + ":queue",
		visitedKey: "gospider:" + spiderName + ":visited",
		statsKey:   "gospider:" + spiderName + ":stats",
	}
}

// AddRequest 添加请求到队列
func (rs *RedisScheduler) AddRequest(req *core.Request) error {
	data, err := json.Marshal(req)
	if err != nil {
		return err
	}

	// 检查是否已访问
	visited, _ := rs.client.Exists(rs.ctx, rs.visitedKey+":"+req.URL).Result()
	if visited > 0 {
		return nil
	}

	// 添加到队列
	_, err = rs.client.LPush(rs.ctx, rs.queueKey, data).Result()
	if err != nil {
		return err
	}

	// 标记为已访问
	rs.client.Set(rs.ctx, rs.visitedKey+":"+req.URL, "1", 24*time.Hour)

	return nil
}

// NextRequest 从队列获取下一个请求
func (rs *RedisScheduler) NextRequest() (*core.Request, error) {
	result, err := rs.client.RPop(rs.ctx, rs.queueKey).Result()
	if err != nil {
		return nil, err
	}

	var req core.Request
	err = json.Unmarshal([]byte(result), &req)
	if err != nil {
		return nil, err
	}

	return &req, nil
}

// UpdateStats 更新统计
func (rs *RedisScheduler) UpdateStats(field string, value int64) {
	rs.client.HIncrBy(rs.ctx, rs.statsKey, field, value)
}

// GetStats 获取统计
func (rs *RedisScheduler) GetStats() map[string]int64 {
	result, _ := rs.client.HGetAll(rs.ctx, rs.statsKey).Result()
	stats := make(map[string]int64)
	for k, v := range result {
		// 尝试将字符串转换为 int64
		var intVal int64
		fmt.Sscanf(v, "%d", &intVal)
		stats[k] = intVal
	}
	return stats
}

// QueueLen 获取队列长度
func (rs *RedisScheduler) QueueLen() int64 {
	result, _ := rs.client.LLen(rs.ctx, rs.queueKey).Result()
	return result
}

// VisitedCount 获取已访问数量
func (rs *RedisScheduler) VisitedCount() int64 {
	result, _ := rs.client.DBSize(rs.ctx).Result()
	return result
}

// Close 关闭连接
func (rs *RedisScheduler) Close() {
	rs.client.Close()
}

// DistributedSpider 分布式爬虫
type DistributedSpider struct {
	name        string
	redisAddr   string
	redisPass   string
	redisDB     int
	threadCount int
}

// NewDistributedSpider 创建分布式爬虫
func NewDistributedSpider(name, redisAddr, redisPass string, redisDB int) *DistributedSpider {
	return &DistributedSpider{
		name:        name,
		redisAddr:   redisAddr,
		redisPass:   redisPass,
		redisDB:     redisDB,
		threadCount: 5,
	}
}

// SetThreadCount 设置线程数
func (ds *DistributedSpider) SetThreadCount(count int) {
	ds.threadCount = count
}

// Start 启动分布式爬虫
func (ds *DistributedSpider) Start(callback func(*core.Request) error) {
	scheduler := NewRedisScheduler(ds.redisAddr, ds.redisPass, ds.redisDB, ds.name)
	defer scheduler.Close()

	log.Printf("Distributed Spider [%s] started", ds.name)

	// 启动工作协程
	for i := 0; i < ds.threadCount; i++ {
		go func() {
			for {
				req, err := scheduler.NextRequest()
				if err != nil {
					time.Sleep(100 * time.Millisecond)
					continue
				}

				if err := callback(req); err != nil {
					log.Printf("Error processing %s: %v", req.URL, err)
					scheduler.UpdateStats("failed", 1)
				} else {
					scheduler.UpdateStats("success", 1)
				}
			}
		}()
	}

	// 保持运行
	select {}
}

// AddStartURL 添加起始 URL
func (ds *DistributedSpider) AddStartURL(url string) error {
	scheduler := NewRedisScheduler(ds.redisAddr, ds.redisPass, ds.redisDB, ds.name)
	defer scheduler.Close()

	req := core.NewRequest(url, nil)
	return scheduler.AddRequest(req)
}
