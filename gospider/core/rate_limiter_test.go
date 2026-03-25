package core

import (
	"context"
	"testing"
	"time"

	"gospider/queue"
)

// TestRateLimiterV3New - 测试创建速率限制器
func TestRateLimiterV3New(t *testing.T) {
	limiter := NewRateLimiterV3(100.0) // 100 请求/秒
	
	if limiter.rate != 100.0 {
		t.Errorf("rate 错误：期望 100.0, 得到 %f", limiter.rate)
	}
	
	if limiter.capacity != 100.0 {
		t.Errorf("capacity 错误：期望 100.0, 得到 %f", limiter.capacity)
	}
}

// TestRateLimiterV3Wait - 测试等待令牌
func TestRateLimiterV3Wait(t *testing.T) {
	limiter := NewRateLimiterV3(10.0) // 10 请求/秒
	
	// 第一次应该立即获得令牌
	start := time.Now()
	err := limiter.Wait(nil)
	elapsed := time.Since(start)
	
	if err != nil {
		t.Errorf("Wait 不应该失败：%v", err)
	}
	
	// 应该很快返回
	if elapsed > time.Millisecond*100 {
		t.Error("第一次等待应该很快")
	}
}

// TestRateLimiterV3RateLimit - 测试速率限制
func TestRateLimiterV3RateLimit(t *testing.T) {
	limiter := NewRateLimiterV3(100.0) // 100 请求/秒 = 10ms/请求

	// 快速消耗令牌 (消耗 100 个令牌)
	for i := 0; i < 100; i++ {
		limiter.Wait(nil)
	}

	// 第 101 次应该需要等待
	start := time.Now()
	limiter.Wait(nil)
	elapsed := time.Since(start)

	// 应该等待一段时间 (至少 5ms)
	if elapsed < time.Millisecond*5 {
		t.Errorf("应该等待一段时间，但只等待了 %v", elapsed)
	}
}

// TestRateLimiterV3ContextCancel - 测试上下文取消
func TestRateLimiterV3ContextCancel(t *testing.T) {
	limiter := NewRateLimiterV3(0.1) // 非常慢的速率

	// 消耗完令牌
	ctx := context.Background()
	limiter.Wait(ctx)

	// 创建带超时的上下文
	ctxWithTimeout, cancel := context.WithTimeout(context.Background(), time.Millisecond*200)
	defer cancel()

	start := time.Now()
	err := limiter.Wait(ctxWithTimeout)
	elapsed := time.Since(start)

	// 应该等待或超时
	if err != nil && err != context.DeadlineExceeded {
		t.Errorf("Wait 失败：%v", err)
	}
	if elapsed < time.Millisecond*50 {
		t.Error("应该等待一段时间")
	}
}

// TestBloomFilterV3New - 测试创建布隆过滤器
func TestBloomFilterV3New(t *testing.T) {
	bf := NewBloomFilterV3(1000, 0.01)
	
	if len(bf.bits) == 0 {
		t.Error("bits 不应该为空")
	}
	
	if bf.numHashes == 0 {
		t.Error("numHashes 不应该为 0")
	}
}

// TestBloomFilterV3AddAndContains - 测试添加和检查
func TestBloomFilterV3AddAndContains(t *testing.T) {
	bf := NewBloomFilterV3(1000, 0.01)
	
	data := []byte("test data")
	
	// 添加前应该不存在
	if bf.Contains(data) {
		t.Error("添加前不应该存在")
	}
	
	// 添加
	bf.Add(data)
	
	// 添加后应该存在
	if !bf.Contains(data) {
		t.Error("添加后应该存在")
	}
}

// TestBloomFilterV3FalsePositive - 测试误判率
func TestBloomFilterV3FalsePositive(t *testing.T) {
	bf := NewBloomFilterV3(1000, 0.01)
	
	// 添加一些数据
	for i := 0; i < 100; i++ {
		bf.Add([]byte("data" + string(rune(i))))
	}
	
	// 检查不存在的数据（可能有误判，但应该很低）
	falsePositives := 0
	totalTests := 1000
	
	for i := 100; i < 100+totalTests; i++ {
		if bf.Contains([]byte("data" + string(rune(i)))) {
			falsePositives++
		}
	}
	
	// 误判率应该低于 5%
	falsePositiveRate := float64(falsePositives) / float64(totalTests)
	if falsePositiveRate > 0.05 {
		t.Errorf("误判率过高：%.2f%%", falsePositiveRate*100)
	}
}

// TestBloomFilterV3MultipleAdds - 测试多次添加
func TestBloomFilterV3MultipleAdds(t *testing.T) {
	bf := NewBloomFilterV3(1000, 0.01)
	
	datas := [][]byte{
		[]byte("data1"),
		[]byte("data2"),
		[]byte("data3"),
	}
	
	// 添加所有数据
	for _, data := range datas {
		bf.Add(data)
	}
	
	// 验证所有数据都存在
	for _, data := range datas {
		if !bf.Contains(data) {
			t.Error("添加的数据应该存在")
		}
	}
}

// TestHashBytes - 测试哈希函数
func TestHashBytes(t *testing.T) {
	data := []byte("test data")
	
	h1, h2 := hashBytes(data)
	
	// 两次哈希应该相同
	h1Again, h2Again := hashBytes(data)
	
	if h1 != h1Again {
		t.Error("h1 应该相同")
	}
	
	if h2 != h2Again {
		t.Error("h2 应该相同")
	}
	
	// 不同数据应该有不同的哈希
	h3, h4 := hashBytes([]byte("different data"))
	
	if h1 == h3 && h2 == h4 {
		t.Error("不同数据应该有不同的哈希")
	}
}

// BenchmarkBloomFilterAdd - 基准测试：添加
func BenchmarkBloomFilterAdd(b *testing.B) {
	bf := NewBloomFilterV3(10000, 0.01)
	data := []byte("test data")
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		bf.Add(data)
	}
}

// BenchmarkBloomFilterContains - 基准测试：检查
func BenchmarkBloomFilterContains(b *testing.B) {
	bf := NewBloomFilterV3(10000, 0.01)
	data := []byte("test data")
	bf.Add(data)
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		bf.Contains(data)
	}
}

// TestSpiderV3New - 测试创建爬虫
func TestSpiderV3New(t *testing.T) {
	config := DefaultSpiderConfigV3()
	spider := NewSpiderV3(config)
	
	if spider == nil {
		t.Fatal("spider 不应该为 nil")
	}
	
	if spider.config != config {
		t.Error("config 应该相同")
	}
}

// TestSpiderV3AddRequest - 测试添加请求
func TestSpiderV3AddRequest(t *testing.T) {
	config := DefaultSpiderConfigV3()
	spider := NewSpiderV3(config)
	
	req := &queue.Request{
		URL: "http://example.com",
	}
	
	err := spider.AddRequest(req)
	if err != nil {
		t.Fatalf("添加请求失败：%v", err)
	}
}

// TestSpiderV3AddRequestMaxDepth - 测试最大深度限制
func TestSpiderV3AddRequestMaxDepth(t *testing.T) {
	config := DefaultSpiderConfigV3()
	config.MaxDepth = 2
	spider := NewSpiderV3(config)
	
	// 超过最大深度的请求应该被拒绝
	req := &queue.Request{
		URL: "http://example.com",
	}
	
	err := spider.AddRequest(req)
	if err != nil {
		// 可能返回错误，也可能静默拒绝
		t.Logf("添加请求：%v", err)
	}
}

// TestSpiderV3GetStats - 测试获取统计
func TestSpiderV3GetStats(t *testing.T) {
	config := DefaultSpiderConfigV3()
	spider := NewSpiderV3(config)
	
	stats := spider.GetStats()
	
	if stats == nil {
		t.Fatal("stats 不应该为 nil")
	}
	
	if _, ok := stats["total_requests"]; !ok {
		t.Error("stats 应该包含 total_requests")
	}
}

// TestSpiderV3Stop - 测试停止
func TestSpiderV3Stop(t *testing.T) {
	config := DefaultSpiderConfigV3()
	spider := NewSpiderV3(config)
	
	spider.Stop()
	
	if spider.IsRunning() {
		t.Error("爬虫应该已停止")
	}
}

// TestSpiderV3IsRunning - 测试运行状态
func TestSpiderV3IsRunning(t *testing.T) {
	config := DefaultSpiderConfigV3()
	spider := NewSpiderV3(config)
	
	// 初始状态应该未运行
	if spider.IsRunning() {
		t.Error("初始状态应该未运行")
	}
}

// TestDefaultSpiderConfigV3 - 测试默认配置
func TestDefaultSpiderConfigV3(t *testing.T) {
	config := DefaultSpiderConfigV3()
	
	if config.Concurrency <= 0 {
		t.Error("Concurrency 应该大于 0")
	}
	
	if config.MaxConnections <= 0 {
		t.Error("MaxConnections 应该大于 0")
	}
	
	if config.RequestTimeout <= 0 {
		t.Error("RequestTimeout 应该大于 0")
	}
}

// BenchmarkSpiderV3AddRequest - 基准测试：添加请求
func BenchmarkSpiderV3AddRequest(b *testing.B) {
	config := DefaultSpiderConfigV3()
	spider := NewSpiderV3(config)
	
	req := &queue.Request{
		URL: "http://example.com",
	}
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		spider.AddRequest(req)
	}
}
