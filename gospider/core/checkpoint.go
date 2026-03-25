package core

import (
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"time"
)

// CheckpointState - 爬虫状态
type CheckpointState struct {
	SpiderID     string                 `json:"spider_id"`
	Timestamp    string                 `json:"timestamp"`
	VisitedURLs  []string               `json:"visited_urls"`
	PendingURLs  []string               `json:"pending_urls"`
	Stats        map[string]interface{} `json:"stats"`
	Config       map[string]interface{} `json:"config"`
	Checksum     string                 `json:"checksum"`
}

// ComputeChecksum - 计算校验和
func (s *CheckpointState) ComputeChecksum() string {
	content := map[string]interface{}{
		"spider_id":     s.SpiderID,
		"visited_count": len(s.VisitedURLs),
		"pending_count": len(s.PendingURLs),
		"stats":         s.Stats,
	}
	
	data, _ := json.Marshal(content)
	hash := md5.Sum(data)
	return hex.EncodeToString(hash[:])
}

// CheckpointManager - 断点管理器
type CheckpointManager struct {
	checkpointDir   string
	autoSaveInterval time.Duration
	maxCheckpoints  int
	
	stateCache map[string]*CheckpointState
	cacheMu    sync.RWMutex
	
	autoSaveTicker *time.Ticker
	stopAutoSave   chan struct{}
	wg             sync.WaitGroup
}

// NewCheckpointManager - 创建断点管理器
func NewCheckpointManager(
	checkpointDir string,
	autoSaveInterval time.Duration,
	maxCheckpoints int,
) *CheckpointManager {
	// 创建 checkpoint 目录
	if err := os.MkdirAll(checkpointDir, 0755); err != nil {
		panic(fmt.Sprintf("创建 checkpoint 目录失败：%v", err))
	}
	
	manager := &CheckpointManager{
		checkpointDir:  checkpointDir,
		autoSaveInterval: autoSaveInterval,
		maxCheckpoints: maxCheckpoints,
		stateCache:     make(map[string]*CheckpointState),
		stopAutoSave:   make(chan struct{}),
	}
	
	// 启动自动保存
	if autoSaveInterval > 0 {
		manager.startAutoSave()
	}
	
	return manager
}

// startAutoSave - 启动自动保存
func (m *CheckpointManager) startAutoSave() {
	m.autoSaveTicker = time.NewTicker(m.autoSaveInterval)
	
	m.wg.Add(1)
	go func() {
		defer m.wg.Done()
		
		for {
			select {
			case <-m.autoSaveTicker.C:
				m.autoSaveAll()
			case <-m.stopAutoSave:
				m.autoSaveTicker.Stop()
				return
			}
		}
	}()
}

// Save - 保存爬虫状态
func (m *CheckpointManager) Save(
	spiderID string,
	visitedURLs []string,
	pendingURLs []string,
	stats map[string]interface{},
	config map[string]interface{},
	immediate bool,
) error {
	state := &CheckpointState{
		SpiderID:    spiderID,
		Timestamp:   time.Now().Format(time.RFC3339),
		VisitedURLs: visitedURLs,
		PendingURLs: pendingURLs,
		Stats:       stats,
		Config:      config,
	}
	state.Checksum = state.ComputeChecksum()
	
	// 保存到缓存
	m.cacheMu.Lock()
	m.stateCache[spiderID] = state
	m.cacheMu.Unlock()
	
	// 立即保存
	if immediate {
		if err := m.saveState(spiderID, state); err != nil {
			return err
		}
	}
	
	return nil
}

// SaveFromSpider - 从爬虫对象保存状态
func (m *CheckpointManager) SaveFromSpider(spider *SpiderV3, immediate bool) error {
	stats := spider.GetStats()
	
	return m.Save(
		spider.config.Name,
		[]string{},
		[]string{},
		stats,
		map[string]interface{}{},
		immediate,
	)
}

// Load - 加载爬虫状态
func (m *CheckpointManager) Load(spiderID string) (*CheckpointState, error) {
	// 先从缓存加载
	m.cacheMu.RLock()
	cached, ok := m.stateCache[spiderID]
	m.cacheMu.RUnlock()
	
	if ok {
		return cached, nil
	}
	
	// 从存储加载
	state, err := m.loadState(spiderID)
	if err != nil {
		return nil, err
	}
	
	if state == nil {
		return nil, nil
	}
	
	// 验证校验和
	expectedChecksum := state.ComputeChecksum()
	if expectedChecksum != state.Checksum {
		return nil, fmt.Errorf("checkpoint 校验和失败：%s", spiderID)
	}
	
	// 保存到缓存
	m.cacheMu.Lock()
	m.stateCache[spiderID] = state
	m.cacheMu.Unlock()
	
	return state, nil
}

// saveState - 保存状态到存储
func (m *CheckpointManager) saveState(spiderID string, state *CheckpointState) error {
	filePath := filepath.Join(m.checkpointDir, spiderID+".checkpoint.json")
	tempPath := filePath + ".tmp"
	
	// 序列化
	data, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return fmt.Errorf("序列化失败：%w", err)
	}
	
	// 写入临时文件
	if err := ioutil.WriteFile(tempPath, data, 0644); err != nil {
		return fmt.Errorf("写入临时文件失败：%w", err)
	}
	
	// 原子替换
	if err := os.Rename(tempPath, filePath); err != nil {
		return fmt.Errorf("原子替换失败：%w", err)
	}
	
	// 清理旧 checkpoint
	m.cleanupOldCheckpoints(spiderID)
	
	return nil
}

// loadState - 从存储加载状态
func (m *CheckpointManager) loadState(spiderID string) (*CheckpointState, error) {
	filePath := filepath.Join(m.checkpointDir, spiderID+".checkpoint.json")
	
	// 检查文件是否存在
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return nil, nil
	}
	
	// 读取文件
	data, err := ioutil.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("读取文件失败：%w", err)
	}
	
	// 反序列化
	var state CheckpointState
	if err := json.Unmarshal(data, &state); err != nil {
		return nil, fmt.Errorf("反序列化失败：%w", err)
	}
	
	return &state, nil
}

// autoSaveAll - 自动保存所有缓存状态
func (m *CheckpointManager) autoSaveAll() {
	m.cacheMu.RLock()
	defer m.cacheMu.RUnlock()
	
	for spiderID, state := range m.stateCache {
		if err := m.saveState(spiderID, state); err != nil {
			fmt.Printf("自动保存失败 %s: %v\n", spiderID, err)
		}
	}
}

// cleanupOldCheckpoints - 清理旧的 checkpoint
func (m *CheckpointManager) cleanupOldCheckpoints(spiderID string) {
	// TODO: 实现多版本保留
}

// Delete - 删除 checkpoint
func (m *CheckpointManager) Delete(spiderID string) error {
	// 从缓存删除
	m.cacheMu.Lock()
	delete(m.stateCache, spiderID)
	m.cacheMu.Unlock()
	
	// 从存储删除
	filePath := filepath.Join(m.checkpointDir, spiderID+".checkpoint.json")
	if _, err := os.Stat(filePath); err == nil {
		if err := os.Remove(filePath); err != nil {
			return fmt.Errorf("删除文件失败：%w", err)
		}
	}
	
	return nil
}

// ListCheckpoints - 列出所有 checkpoint
func (m *CheckpointManager) ListCheckpoints() ([]string, error) {
	var checkpoints []string
	
	err := filepath.Walk(m.checkpointDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		
		if !info.IsDir() && filepath.Ext(path) == ".json" {
			filename := info.Name()
			if len(filename) > len(".checkpoint.json") && 
				filepath.Ext(filename[:len(filename)-len(".json")]) == ".checkpoint" {
				
				spiderID := filename[:len(filename)-len(".checkpoint.json")]
				checkpoints = append(checkpoints, spiderID)
			}
		}
		
		return nil
	})
	
	if err != nil {
		return nil, err
	}
	
	sort.Strings(checkpoints)
	return checkpoints, nil
}

// GetStats - 获取 checkpoint 统计
func (m *CheckpointManager) GetStats(spiderID string) (map[string]interface{}, error) {
	m.cacheMu.RLock()
	state, ok := m.stateCache[spiderID]
	m.cacheMu.RUnlock()
	
	if !ok {
		var err error
		state, err = m.loadState(spiderID)
		if err != nil {
			return nil, err
		}
	}
	
	if state == nil {
		return nil, nil
	}
	
	return map[string]interface{}{
		"spider_id":     state.SpiderID,
		"timestamp":     state.Timestamp,
		"visited_count": len(state.VisitedURLs),
		"pending_count": len(state.PendingURLs),
		"stats":         state.Stats,
		"checksum":      state.Checksum,
	}, nil
}

// Close - 关闭管理器
func (m *CheckpointManager) Close() error {
	// 停止自动保存
	if m.autoSaveTicker != nil {
		close(m.stopAutoSave)
		m.wg.Wait()
	}
	
	// 保存所有缓存状态
	m.cacheMu.RLock()
	defer m.cacheMu.RUnlock()
	
	for spiderID, state := range m.stateCache {
		if err := m.saveState(spiderID, state); err != nil {
			fmt.Printf("关闭时保存失败 %s: %v\n", spiderID, err)
		}
	}
	
	return nil
}
