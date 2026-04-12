package core

import (
	"crypto/md5"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// PageCacheEntry 页面缓存条目
type PageCacheEntry struct {
	URL           string
	ETag          string
	LastModified  string
	ContentHash   string
	LastCrawled   time.Time
	StatusCode    int
	ContentChanged bool
}

// IncrementalCrawler 增量爬取管理器
type IncrementalCrawler struct {
	enabled            bool
	minChangeInterval  time.Duration
	cache              map[string]*PageCacheEntry
	mu                 sync.RWMutex
	storePath          string
}

// NewIncrementalCrawler 创建增量爬取管理器
func NewIncrementalCrawler(enabled bool, minChangeInterval time.Duration) *IncrementalCrawler {
	return &IncrementalCrawler{
		enabled:           enabled,
		minChangeInterval: minChangeInterval,
		cache:             make(map[string]*PageCacheEntry),
	}
}

// SetEnabled 启用/禁用增量爬取
func (ic *IncrementalCrawler) SetEnabled(enabled bool) {
	ic.enabled = enabled
}

// ShouldSkip 检查是否应该跳过此 URL(内容未变更)
func (ic *IncrementalCrawler) ShouldSkip(rawURL string, etag string, lastModified string) bool {
	if !ic.enabled {
		return false
	}

	ic.mu.RLock()
	entry, exists := ic.cache[rawURL]
	ic.mu.RUnlock()

	if !exists {
		return false
	}

	// 检查最小变更间隔
	if time.Since(entry.LastCrawled) < ic.minChangeInterval {
		return true
	}

	// ETag 比较
	if etag != "" && entry.ETag != "" && etag == entry.ETag {
		entry.ContentChanged = false
		return true
	}

	// Last-Modified 比较
	if lastModified != "" && entry.LastModified != "" && lastModified == entry.LastModified {
		entry.ContentChanged = false
		return true
	}

	return false
}

// GetConditionalHeaders 获取条件请求头
func (ic *IncrementalCrawler) GetConditionalHeaders(rawURL string) map[string]string {
	headers := make(map[string]string)

	ic.mu.RLock()
	entry, exists := ic.cache[rawURL]
	ic.mu.RUnlock()

	if exists {
		if entry.ETag != "" {
			headers["If-None-Match"] = entry.ETag
		}
		if entry.LastModified != "" {
			headers["If-Modified-Since"] = entry.LastModified
		}
	}

	return headers
}

// UpdateCache 更新缓存
// 返回 true 表示内容已变更, false 表示未变更
func (ic *IncrementalCrawler) UpdateCache(rawURL string, etag string, lastModified string, content []byte, statusCode int) bool {
	contentHash := ""
	if len(content) > 0 {
		contentHash = fmt.Sprintf("%x", md5.Sum(content))
	}

	ic.mu.Lock()
	defer ic.mu.Unlock()

	if entry, exists := ic.cache[rawURL]; exists {
		// 检查内容是否真的变更
		if entry.ContentHash == contentHash {
			entry.LastCrawled = time.Now()
			entry.ContentChanged = false
			return false
		}
	}

	// 创建或更新缓存
	ic.cache[rawURL] = &PageCacheEntry{
		URL:            rawURL,
		ETag:           etag,
		LastModified:   lastModified,
		ContentHash:    contentHash,
		LastCrawled:    time.Now(),
		StatusCode:     statusCode,
		ContentChanged: true,
	}

	return true
}

// GetCacheStats 获取缓存统计
func (ic *IncrementalCrawler) GetCacheStats() map[string]int {
	ic.mu.RLock()
	defer ic.mu.RUnlock()

	total := len(ic.cache)
	changed := 0
	for _, entry := range ic.cache {
		if entry.ContentChanged {
			changed++
		}
	}

	return map[string]int{
		"total":     total,
		"changed":   changed,
		"unchanged": total - changed,
	}
}

// ClearCache 清除所有缓存
func (ic *IncrementalCrawler) ClearCache() {
	ic.mu.Lock()
	defer ic.mu.Unlock()
	ic.cache = make(map[string]*PageCacheEntry)
}

// RemoveURL 移除指定 URL 的缓存
func (ic *IncrementalCrawler) RemoveURL(rawURL string) {
	ic.mu.Lock()
	defer ic.mu.Unlock()
	delete(ic.cache, rawURL)
}

// DeltaToken returns a stable token for the cached entry.
func (ic *IncrementalCrawler) DeltaToken(rawURL string) string {
	ic.mu.RLock()
	entry, exists := ic.cache[rawURL]
	ic.mu.RUnlock()
	if !exists {
		return ""
	}
	payload := map[string]interface{}{
		"url":           entry.URL,
		"etag":          entry.ETag,
		"last_modified": entry.LastModified,
		"content_hash":  entry.ContentHash,
		"status_code":   entry.StatusCode,
	}
	data, _ := json.Marshal(payload)
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

// Snapshot returns the serializable cache state.
func (ic *IncrementalCrawler) Snapshot() map[string]interface{} {
	ic.mu.RLock()
	defer ic.mu.RUnlock()
	entries := make(map[string]PageCacheEntry, len(ic.cache))
	for rawURL, entry := range ic.cache {
		entries[rawURL] = *entry
	}
	return map[string]interface{}{
		"enabled":             ic.enabled,
		"min_change_interval": int64(ic.minChangeInterval / time.Second),
		"entries":             entries,
	}
}

// Restore replaces the in-memory cache from a serialized snapshot.
func (ic *IncrementalCrawler) Restore(snapshot map[string]interface{}) error {
	data, err := json.Marshal(snapshot)
	if err != nil {
		return err
	}
	var decoded struct {
		Enabled           bool                      `json:"enabled"`
		MinChangeInterval int64                     `json:"min_change_interval"`
		Entries           map[string]PageCacheEntry `json:"entries"`
	}
	if err := json.Unmarshal(data, &decoded); err != nil {
		return err
	}
	ic.mu.Lock()
	defer ic.mu.Unlock()
	ic.enabled = decoded.Enabled
	if decoded.MinChangeInterval > 0 {
		ic.minChangeInterval = time.Duration(decoded.MinChangeInterval) * time.Second
	}
	ic.cache = make(map[string]*PageCacheEntry, len(decoded.Entries))
	for rawURL, entry := range decoded.Entries {
		copy := entry
		ic.cache[rawURL] = &copy
	}
	return nil
}

// Save writes the cache state to disk.
func (ic *IncrementalCrawler) Save(path string) error {
	if path == "" {
		path = ic.storePath
	}
	if path == "" {
		return nil
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(ic.Snapshot(), "", "  ")
	if err != nil {
		return err
	}
	ic.storePath = path
	return os.WriteFile(path, data, 0o644)
}

// Load restores the cache state from disk.
func (ic *IncrementalCrawler) Load(path string) error {
	if path == "" {
		path = ic.storePath
	}
	if path == "" {
		return nil
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	ic.storePath = path
	var snapshot map[string]interface{}
	if err := json.Unmarshal(data, &snapshot); err != nil {
		return err
	}
	return ic.Restore(snapshot)
}
