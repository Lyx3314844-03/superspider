//go:build ignore

// Gospider 浏览器池模块
// 注意：此文件当前被禁用，因为 playwright-go API 有兼容性问题
// 当前生产主线使用 browser 包下的 chromedp 实现

package browser

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/playwright-community/playwright-go"
)

// PlaywrightBrowserOptions - Playwright 浏览器选项
type PlaywrightBrowserOptions struct {
	Headless          bool
	Width             int
	Height            int
	UserAgent         string
	Proxy             string
	Timeout           time.Duration
	Args              []string
	JavaScriptEnabled bool
}

// DefaultPlaywrightOptions - 默认 Playwright 选项
func DefaultPlaywrightOptions() *PlaywrightBrowserOptions {
	return &PlaywrightBrowserOptions{
		Headless:          true,
		Width:             1920,
		Height:            1080,
		UserAgent:         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
		Timeout:           30 * time.Second,
		JavaScriptEnabled: true,
	}
}

// BrowserInstance - 浏览器实例
type BrowserInstance struct {
	ID           string
	Browser      playwright.Browser
	Context      playwright.BrowserContext
	Page         playwright.Page
	CreatedAt    time.Time
	LastUsedAt   time.Time
	RequestCount int
	IsValid      bool
	mu           sync.RWMutex
}

// NewBrowserInstance - 创建浏览器实例
func NewBrowserInstance(options *PlaywrightBrowserOptions) (*BrowserInstance, error) {
	if options == nil {
		options = DefaultPlaywrightOptions()
	}

	// 启动浏览器
	browser, err := playwright.Chromium.Launch(playwright.BrowserTypeLaunchOptions{
		Headless: playwright.Bool(options.Headless),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to launch browser: %w", err)
	}

	// 创建上下文
	context, err := browser.NewContext(playwright.BrowserNewContextOptions{
		UserAgent: playwright.String(options.UserAgent),
		Viewport: &playwright.ViewportSize{
			Width:  options.Width,
			Height: options.Height,
		},
	})
	if err != nil {
		browser.Close()
		return nil, fmt.Errorf("failed to create context: %w", err)
	}

	// 创建页面
	page, err := context.NewPage()
	if err != nil {
		context.Close()
		browser.Close()
		return nil, fmt.Errorf("failed to create page: %w", err)
	}

	id, err := generateBrowserID()
	if err != nil {
		return nil, err
	}

	now := time.Now()
	return &BrowserInstance{
		ID:           id,
		Browser:      browser,
		Context:      context,
		Page:         page,
		CreatedAt:    now,
		LastUsedAt:   now,
		RequestCount: 0,
		IsValid:      true,
	}, nil
}

// Navigate - 导航到 URL
func (bi *BrowserInstance) Navigate(url string) error {
	bi.mu.Lock()
	defer bi.mu.Unlock()

	_, err := bi.Page.Goto(url, playwright.PageGotoOptions{
		WaitUntil: playwright.WaitUntilStateDomcontentloaded,
		Timeout:   playwright.Float(30000),
	})
	return err
}

// Screenshot - 截图
func (bi *BrowserInstance) Screenshot(path string) error {
	bi.mu.Lock()
	defer bi.mu.Unlock()

	_, err := bi.Page.Screenshot(playwright.PageScreenshotOptions{
		Path: playwright.String(path),
	})
	return err
}

// Evaluate - 执行 JavaScript
func (bi *BrowserInstance) Evaluate(script string) (interface{}, error) {
	bi.mu.Lock()
	defer bi.mu.Unlock()

	return bi.Page.Evaluate(script)
}

// Click - 点击元素
func (bi *BrowserInstance) Click(selector string) error {
	bi.mu.Lock()
	defer bi.mu.Unlock()

	return bi.Page.Click(selector)
}

// Fill - 填充表单
func (bi *BrowserInstance) Fill(selector, value string) error {
	bi.mu.Lock()
	defer bi.mu.Unlock()

	return bi.Page.Fill(selector, value)
}

// Content - 获取页面内容
func (bi *BrowserInstance) Content() (string, error) {
	bi.mu.RLock()
	defer bi.mu.RUnlock()

	return bi.Page.Content()
}

// MarkUsed - 标记已使用
func (bi *BrowserInstance) MarkUsed() {
	bi.mu.Lock()
	defer bi.mu.Unlock()

	bi.LastUsedAt = time.Now()
	bi.RequestCount++
}

// Close - 关闭浏览器实例
func (bi *BrowserInstance) Close() {
	bi.mu.Lock()
	defer bi.mu.Unlock()

	bi.IsValid = false

	if bi.Page != nil {
		bi.Page.Close()
	}
	if bi.Context != nil {
		bi.Context.Close()
	}
	if bi.Browser != nil {
		bi.Browser.Close()
	}
}

// BrowserPool - 浏览器池
type BrowserPool struct {
	instances     map[string]*BrowserInstance
	maxInstances  int
	maxAge        time.Duration
	maxIdleTime   time.Duration
	maxRequests   int
	options       *PlaywrightBrowserOptions
	currentIndex  int
	mu            sync.RWMutex
	autoRecycle   bool
	recycleTicker *time.Ticker
	stopChan      chan struct{}
}

// BrowserPoolConfig - 浏览器池配置
type BrowserPoolConfig struct {
	MaxInstances    int
	MaxAge          time.Duration
	MaxIdleTime     time.Duration
	MaxRequests     int
	Options         *PlaywrightBrowserOptions
	AutoRecycle     bool
	RecycleInterval time.Duration
}

// DefaultBrowserPoolConfig - 默认配置
func DefaultBrowserPoolConfig() *BrowserPoolConfig {
	return &BrowserPoolConfig{
		MaxInstances:    5,
		MaxAge:          15 * time.Minute,
		MaxIdleTime:     5 * time.Minute,
		MaxRequests:     100,
		Options:         DefaultPlaywrightOptions(),
		AutoRecycle:     true,
		RecycleInterval: 30 * time.Second,
	}
}

// NewBrowserPool - 创建浏览器池
func NewBrowserPool(config *BrowserPoolConfig) (*BrowserPool, error) {
	if config == nil {
		config = DefaultBrowserPoolConfig()
	}

	// 初始化 Playwright
	err := playwright.Install()
	if err != nil {
		return nil, fmt.Errorf("failed to install playwright: %w", err)
	}

	pool := &BrowserPool{
		instances:     make(map[string]*BrowserInstance),
		maxInstances:  config.MaxInstances,
		maxAge:        config.MaxAge,
		maxIdleTime:   config.MaxIdleTime,
		maxRequests:   config.MaxRequests,
		options:       config.Options,
		currentIndex:  0,
		autoRecycle:   config.AutoRecycle,
		recycleTicker: nil,
		stopChan:      make(chan struct{}),
	}

	// 启动自动回收
	if pool.autoRecycle {
		pool.recycleTicker = time.NewTicker(config.RecycleInterval)
		go pool.autoRecycleLoop()
	}

	return pool, nil
}

// GetBrowser - 获取浏览器实例
func (bp *BrowserPool) GetBrowser() *BrowserInstance {
	bp.mu.Lock()
	defer bp.mu.Unlock()

	// 获取有效实例
	validInstances := bp.getValidInstances()
	if len(validInstances) == 0 {
		// 创建新实例
		if len(bp.instances) < bp.maxInstances {
			instance, err := NewBrowserInstance(bp.options)
			if err != nil {
				return nil
			}
			bp.instances[instance.ID] = instance
			return instance
		}
		return nil
	}

	// 轮询选择
	instance := validInstances[bp.currentIndex%len(validInstances)]
	bp.currentIndex++
	instance.MarkUsed()

	return instance
}

// CreateBrowser - 创建新浏览器实例
func (bp *BrowserPool) CreateBrowser() (*BrowserInstance, error) {
	bp.mu.Lock()
	defer bp.mu.Unlock()

	if len(bp.instances) >= bp.maxInstances {
		return nil, nil
	}

	instance, err := NewBrowserInstance(bp.options)
	if err != nil {
		return nil, err
	}

	bp.instances[instance.ID] = instance
	return instance, nil
}

// RemoveBrowser - 移除浏览器实例
func (bp *BrowserPool) RemoveBrowser(instanceID string) {
	bp.mu.Lock()
	defer bp.mu.Unlock()

	if instance, exists := bp.instances[instanceID]; exists {
		instance.Close()
		delete(bp.instances, instanceID)
	}
}

// getValidInstances - 获取有效实例列表
func (bp *BrowserPool) getValidInstances() []*BrowserInstance {
	bp.mu.RLock()
	defer bp.mu.RUnlock()

	now := time.Now()
	result := make([]*BrowserInstance, 0)

	for _, instance := range bp.instances {
		instance.mu.RLock()
		age := now.Sub(instance.CreatedAt)
		idleTime := now.Sub(instance.LastUsedAt)

		if instance.IsValid &&
			age < bp.maxAge &&
			idleTime < bp.maxIdleTime &&
			instance.RequestCount < bp.maxRequests {
			result = append(result, instance)
		}
		instance.mu.RUnlock()
	}

	return result
}

// autoRecycleLoop - 自动回收循环
func (bp *BrowserPool) autoRecycleLoop() {
	for {
		select {
		case <-bp.recycleTicker.C:
			bp.recycle()
		case <-bp.stopChan:
			return
		}
	}
}

// recycle - 回收过期实例
func (bp *BrowserPool) recycle() {
	bp.mu.Lock()
	defer bp.mu.Unlock()

	now := time.Now()
	toRemove := make([]string, 0)

	for id, instance := range bp.instances {
		instance.mu.RLock()
		age := now.Sub(instance.CreatedAt)
		idleTime := now.Sub(instance.LastUsedAt)

		if !instance.IsValid ||
			age >= bp.maxAge ||
			idleTime >= bp.maxIdleTime ||
			instance.RequestCount >= bp.maxRequests {
			toRemove = append(toRemove, id)
		}
		instance.mu.RUnlock()
	}

	for _, id := range toRemove {
		if instance, exists := bp.instances[id]; exists {
			instance.Close()
			delete(bp.instances, id)
		}
	}
}

// GetStats - 获取统计信息
func (bp *BrowserPool) GetStats() map[string]interface{} {
	bp.mu.RLock()
	defer bp.mu.RUnlock()

	total := len(bp.instances)
	valid := 0
	invalid := 0

	for _, instance := range bp.instances {
		instance.mu.RLock()
		if instance.IsValid {
			valid++
		} else {
			invalid++
		}
		instance.mu.RUnlock()
	}

	return map[string]interface{}{
		"total":         total,
		"valid":         valid,
		"invalid":       invalid,
		"validity_rate": float64(valid) / float64(total),
	}
}

// Size - 浏览器池大小
func (bp *BrowserPool) Size() int {
	bp.mu.RLock()
	defer bp.mu.RUnlock()
	return len(bp.instances)
}

// ValidSize - 有效实例数量
func (bp *BrowserPool) ValidSize() int {
	bp.mu.RLock()
	defer bp.mu.RUnlock()

	count := 0
	for _, instance := range bp.instances {
		instance.mu.RLock()
		if instance.IsValid {
			count++
		}
		instance.mu.RUnlock()
	}
	return count
}

// Clear - 清空浏览器池
func (bp *BrowserPool) Clear() {
	bp.mu.Lock()
	defer bp.mu.Unlock()

	for _, instance := range bp.instances {
		instance.Close()
	}
	bp.instances = make(map[string]*BrowserInstance)
}

// Close - 关闭浏览器池
func (bp *BrowserPool) Close() {
	if bp.recycleTicker != nil {
		bp.recycleTicker.Stop()
		close(bp.stopChan)
	}
	bp.Clear()
}

// generateBrowserID - 生成浏览器 ID
func generateBrowserID() (string, error) {
	// 简单实现，实际应该用更安全的随机数生成
	return fmt.Sprintf("browser_%d", time.Now().UnixNano()), nil
}

// Scraper - 网页爬虫
type Scraper struct {
	pool *BrowserPool
}

// NewScraper - 创建爬虫
func NewScraper(poolSize int) (*Scraper, error) {
	config := DefaultBrowserPoolConfig()
	config.MaxInstances = poolSize

	pool, err := NewBrowserPool(config)
	if err != nil {
		return nil, err
	}

	return &Scraper{
		pool: pool,
	}, nil
}

// Scrape - 爬取网页
func (s *Scraper) Scrape(url string) (string, error) {
	browser := s.pool.GetBrowser()
	if browser == nil {
		return "", fmt.Errorf("no available browser")
	}
	defer browser.MarkUsed()

	// 导航到 URL
	if err := browser.Navigate(url); err != nil {
		return "", err
	}

	// 等待页面加载
	time.Sleep(2 * time.Second)

	// 获取内容
	return browser.Content()
}

// ScrapeWithScreenshot - 爬取网页并截图
func (s *Scraper) ScrapeWithScreenshot(url, screenshotPath string) (string, error) {
	browser := s.pool.GetBrowser()
	if browser == nil {
		return "", fmt.Errorf("no available browser")
	}
	defer browser.MarkUsed()

	// 导航到 URL
	if err := browser.Navigate(url); err != nil {
		return "", err
	}

	// 等待页面加载
	time.Sleep(2 * time.Second)

	// 截图
	if err := browser.Screenshot(screenshotPath); err != nil {
		return "", err
	}

	// 获取内容
	return browser.Content()
}

// Close - 关闭爬虫
func (s *Scraper) Close() {
	if s.pool != nil {
		s.pool.Close()
	}
}
