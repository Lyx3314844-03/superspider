package core

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

// TestCheckpointManagerNew - 测试创建管理器
func TestCheckpointManagerNew(t *testing.T) {
	tempDir := t.TempDir()

	manager, err := NewCheckpointManager(tempDir, time.Second*5, 10)
	if err != nil {
		t.Fatal(err)
	}
	if manager == nil {
		t.Fatal("CheckpointManager 不应该为 nil")
	}

	// 验证目录创建
	if _, err := os.Stat(tempDir); os.IsNotExist(err) {
		t.Error("checkpoint 目录应该被创建")
	}

	manager.Close()
}

// TestCheckpointSaveAndLoad - 测试保存和加载
func TestCheckpointSaveAndLoad(t *testing.T) {
	tempDir := t.TempDir()
	manager, err := NewCheckpointManager(tempDir, 0, 10)
	if err != nil {
		t.Fatal(err)
	}
	defer manager.Close()

	spiderID := "test_spider"
	visitedURLs := []string{"http://a.com", "http://b.com"}
	pendingURLs := []string{"http://c.com"}
	stats := map[string]interface{}{
		"total":   100,
		"success": 95,
	}
	config := map[string]interface{}{
		"threads": 10,
	}

	// 保存
	err = manager.Save(spiderID, visitedURLs, pendingURLs, stats, config, true)
	if err != nil {
		t.Fatalf("保存失败：%v", err)
	}

	// 加载
	state, err := manager.Load(spiderID)
	if err != nil {
		t.Fatalf("加载失败：%v", err)
	}

	if state == nil {
		t.Fatal("state 不应该为 nil")
	}

	// 验证数据
	if state.SpiderID != spiderID {
		t.Errorf("SpiderID 不匹配：期望 %s, 得到 %s", spiderID, state.SpiderID)
	}

	if len(state.VisitedURLs) != 2 {
		t.Errorf("VisitedURLs 数量错误：期望 2, 得到 %d", len(state.VisitedURLs))
	}

	if len(state.PendingURLs) != 1 {
		t.Errorf("PendingURLs 数量错误：期望 1, 得到 %d", len(state.PendingURLs))
	}
}

// TestCheckpointSaveCached - 测试缓存保存
func TestCheckpointSaveCached(t *testing.T) {
	tempDir := t.TempDir()
	manager, err := NewCheckpointManager(tempDir, 0, 10)
	if err != nil {
		t.Fatal(err)
	}
	defer manager.Close()

	spiderID := "test_cached"

	// 保存到缓存（不立即保存）
	err = manager.Save(spiderID, []string{}, []string{}, map[string]interface{}{}, map[string]interface{}{}, false)
	if err != nil {
		t.Fatalf("保存失败：%v", err)
	}

	// 文件不应该存在
	filePath := filepath.Join(tempDir, spiderID+".checkpoint.json")
	if _, err := os.Stat(filePath); err == nil {
		t.Error("文件不应该存在（因为没立即保存）")
	}

	// 但从缓存应该能加载
	state, err := manager.Load(spiderID)
	if err != nil {
		t.Fatalf("加载失败：%v", err)
	}

	if state == nil {
		t.Error("state 不应该为 nil")
	}
}

// TestCheckpointLoadNonexistent - 测试加载不存在
func TestCheckpointLoadNonexistent(t *testing.T) {
	tempDir := t.TempDir()
	manager, err := NewCheckpointManager(tempDir, 0, 10)
	if err != nil {
		t.Fatal(err)
	}
	defer manager.Close()

	state, err := manager.Load("nonexistent")
	if err != nil {
		t.Fatalf("加载不应该失败：%v", err)
	}

	if state != nil {
		t.Error("state 应该为 nil")
	}
}

// TestCheckpointDelete - 测试删除
func TestCheckpointDelete(t *testing.T) {
	tempDir := t.TempDir()
	manager, err := NewCheckpointManager(tempDir, 0, 10)
	if err != nil {
		t.Fatal(err)
	}
	defer manager.Close()

	spiderID := "test_delete"

	// 先保存
	manager.Save(spiderID, []string{}, []string{}, map[string]interface{}{}, map[string]interface{}{}, true)

	// 删除
	err = manager.Delete(spiderID)
	if err != nil {
		t.Fatalf("删除失败：%v", err)
	}

	// 验证文件不存在
	filePath := filepath.Join(tempDir, spiderID+".checkpoint.json")
	if _, err := os.Stat(filePath); err == nil {
		t.Error("文件应该被删除")
	}
}

// TestCheckpointList - 测试列出 checkpoint
func TestCheckpointList(t *testing.T) {
	tempDir := t.TempDir()
	manager, err := NewCheckpointManager(tempDir, 0, 10)
	if err != nil {
		t.Fatal(err)
	}
	defer manager.Close()

	// 保存多个
	for i := 0; i < 3; i++ {
		spiderID := "spider_" + string(rune('0'+i))
		manager.Save(spiderID, []string{}, []string{}, map[string]interface{}{}, map[string]interface{}{}, true)
	}

	checkpoints, err := manager.ListCheckpoints()
	if err != nil {
		t.Fatalf("列出失败：%v", err)
	}

	if len(checkpoints) != 3 {
		t.Errorf("checkpoint 数量错误：期望 3, 得到 %d", len(checkpoints))
	}
}

// TestCheckpointGetStats - 测试获取统计
func TestCheckpointGetStats(t *testing.T) {
	tempDir := t.TempDir()
	manager, err := NewCheckpointManager(tempDir, 0, 10)
	if err != nil {
		t.Fatal(err)
	}
	defer manager.Close()

	spiderID := "test_stats"
	stats := map[string]interface{}{
		"total":   100,
		"success": 95,
	}

	manager.Save(spiderID, []string{"url1", "url2"}, []string{"url3"}, stats, map[string]interface{}{}, true)

	resultStats, err := manager.GetStats(spiderID)
	if err != nil {
		t.Fatalf("获取统计失败：%v", err)
	}

	if resultStats == nil {
		t.Fatal("resultStats 不应该为 nil")
	}

	visitedCount, ok := resultStats["visited_count"].(int)
	if !ok || visitedCount != 2 {
		t.Errorf("visited_count 错误：期望 2, 得到 %v", visitedCount)
	}
}

// TestCheckpointAutoSave - 测试自动保存
func TestCheckpointAutoSave(t *testing.T) {
	tempDir := t.TempDir()
	manager, err := NewCheckpointManager(tempDir, time.Second, 10)
	if err != nil {
		t.Fatal(err)
	}
	defer manager.Close()

	spiderID := "test_auto"

	// 保存到缓存（不立即保存）
	manager.Save(spiderID, []string{"url1"}, []string{}, map[string]interface{}{}, map[string]interface{}{}, false)

	// 等待自动保存
	time.Sleep(time.Second * 2)

	// 检查文件是否被创建
	filePath := filepath.Join(tempDir, spiderID+".checkpoint.json")
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		t.Error("自动保存应该创建文件")
	}
}

// TestCheckpointChecksum - 测试校验和
func TestCheckpointChecksum(t *testing.T) {
	state := &CheckpointState{
		SpiderID:    "test",
		Timestamp:   "2026-03-23T10:00:00Z",
		VisitedURLs: []string{"url1"},
		PendingURLs: []string{},
		Stats:       map[string]interface{}{},
		Config:      map[string]interface{}{},
	}

	checksum1 := state.ComputeChecksum()
	checksum2 := state.ComputeChecksum()

	if checksum1 != checksum2 {
		t.Error("相同状态应该有相同校验和")
	}

	// 修改状态
	state.VisitedURLs = append(state.VisitedURLs, "url2")
	checksum3 := state.ComputeChecksum()

	if checksum1 == checksum3 {
		t.Error("不同状态应该有不同校验和")
	}
}

// TestCheckpointSaveFromSpider - 测试从当前主线爬虫保存
func TestCheckpointSaveFromSpider(t *testing.T) {
	tempDir := t.TempDir()
	manager, err := NewCheckpointManager(tempDir, 0, 10)
	if err != nil {
		t.Fatal(err)
	}
	defer manager.Close()

	config := DefaultSpiderConfig()
	config.Name = "test_spider"
	spider := NewSpider(config)

	err = manager.SaveFromSpider(spider, true)
	if err != nil {
		t.Fatalf("保存失败：%v", err)
	}

	state, err := manager.Load("test_spider")
	if err != nil {
		t.Fatalf("加载失败：%v", err)
	}

	if state == nil {
		t.Error("state 不应该为 nil")
	}
}

// TestCheckpointConcurrentSave - 测试并发保存
func TestCheckpointConcurrentSave(t *testing.T) {
	tempDir := t.TempDir()
	manager, err := NewCheckpointManager(tempDir, 0, 10)
	if err != nil {
		t.Fatal(err)
	}
	defer manager.Close()

	done := make(chan bool, 5)

	// 并发保存
	for i := 0; i < 5; i++ {
		go func(index int) {
			spiderID := "spider_" + string(rune('0'+index))
			manager.Save(spiderID, []string{"url"}, []string{}, map[string]interface{}{}, map[string]interface{}{}, true)
			done <- true
		}(i)
	}

	// 等待所有 goroutine 完成
	for i := 0; i < 5; i++ {
		<-done
	}

	// 验证
	checkpoints, _ := manager.ListCheckpoints()
	if len(checkpoints) != 5 {
		t.Errorf("checkpoint 数量错误：期望 5, 得到 %d", len(checkpoints))
	}
}

// TestCheckpointLargeData - 测试大数据保存
func TestCheckpointLargeData(t *testing.T) {
	tempDir := t.TempDir()
	manager, err := NewCheckpointManager(tempDir, 0, 10)
	if err != nil {
		t.Fatal(err)
	}
	defer manager.Close()

	spiderID := "test_large"
	visitedURLs := make([]string, 1000)
	for i := 0; i < 1000; i++ {
		visitedURLs[i] = "http://example.com/page" + string(rune(i))
	}

	err = manager.Save(spiderID, visitedURLs, []string{}, map[string]interface{}{}, map[string]interface{}{}, true)
	if err != nil {
		t.Fatalf("保存失败：%v", err)
	}

	state, err := manager.Load(spiderID)
	if err != nil {
		t.Fatalf("加载失败：%v", err)
	}

	if len(state.VisitedURLs) != 1000 {
		t.Errorf("VisitedURLs 数量错误：期望 1000, 得到 %d", len(state.VisitedURLs))
	}
}

// TestCheckpointSpecialCharacters - 测试特殊字符
func TestCheckpointSpecialCharacters(t *testing.T) {
	tempDir := t.TempDir()
	manager, err := NewCheckpointManager(tempDir, 0, 10)
	if err != nil {
		t.Fatal(err)
	}
	defer manager.Close()

	spiderID := "test_special"
	visitedURLs := []string{
		"http://example.com/page?param=value&other=123",
		"http://example.com/page with spaces",
		"http://example.com/page/中文/unicode",
	}

	err = manager.Save(spiderID, visitedURLs, []string{}, map[string]interface{}{}, map[string]interface{}{}, true)
	if err != nil {
		t.Fatalf("保存失败：%v", err)
	}

	state, err := manager.Load(spiderID)
	if err != nil {
		t.Fatalf("加载失败：%v", err)
	}

	if len(state.VisitedURLs) != 3 {
		t.Errorf("VisitedURLs 数量错误：期望 3, 得到 %d", len(state.VisitedURLs))
	}
}

// TestCheckpointClose - 测试关闭
func TestCheckpointClose(t *testing.T) {
	tempDir := t.TempDir()
	manager, err := NewCheckpointManager(tempDir, 0, 10)
	if err != nil {
		t.Fatal(err)
	}

	spiderID := "test_close"

	// 保存到缓存（不立即保存）
	manager.Save(spiderID, []string{"url1"}, []string{}, map[string]interface{}{}, map[string]interface{}{}, false)

	// 关闭（应该保存所有缓存）
	manager.Close()

	// 检查文件是否存在
	filePath := filepath.Join(tempDir, spiderID+".checkpoint.json")
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		t.Error("关闭时应该保存所有缓存状态")
	}
}

func TestCheckpointRetentionKeepsRecentHistory(t *testing.T) {
	tempDir := t.TempDir()
	manager, err := NewCheckpointManager(tempDir, 0, 2)
	if err != nil {
		t.Fatal(err)
	}
	defer manager.Close()

	for i := 0; i < 3; i++ {
		err = manager.Save("history_spider", []string{"url"}, []string{}, map[string]interface{}{"seq": i}, map[string]interface{}{}, true)
		if err != nil {
			t.Fatalf("save failed: %v", err)
		}
		time.Sleep(10 * time.Millisecond)
	}

	history, err := filepath.Glob(filepath.Join(tempDir, "history_spider.checkpoint.*.json"))
	if err != nil {
		t.Fatalf("failed to list history files: %v", err)
	}
	if len(history) != 2 {
		t.Fatalf("expected 2 retained checkpoint versions, got %d (%v)", len(history), history)
	}
}

// BenchmarkCheckpointSave - 基准测试：保存
func BenchmarkCheckpointSave(b *testing.B) {
	tempDir := b.TempDir()
	manager, err := NewCheckpointManager(tempDir, 0, 10)
	if err != nil {
		b.Fatal(err)
	}
	defer manager.Close()

	spiderID := "benchmark"
	visitedURLs := []string{"http://example.com/page"}
	stats := map[string]interface{}{"total": 100}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		manager.Save(spiderID, visitedURLs, []string{}, stats, map[string]interface{}{}, true)
	}
}

// BenchmarkCheckpointLoad - 基准测试：加载
func BenchmarkCheckpointLoad(b *testing.B) {
	tempDir := b.TempDir()
	manager, err := NewCheckpointManager(tempDir, 0, 10)
	if err != nil {
		b.Fatal(err)
	}
	defer manager.Close()

	spiderID := "benchmark"
	manager.Save(spiderID, []string{"url"}, []string{}, map[string]interface{}{}, map[string]interface{}{}, true)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		manager.Load(spiderID)
	}
}
