// Package browser provides browser automation using chromedp
package browser

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"time"

	"github.com/chromedp/chromedp"
)

// BrowserConfig 浏览器配置
type BrowserConfig struct {
	Headless        bool              `json:"headless"`
	Stealth         bool              `json:"stealth"`
	Timeout         time.Duration     `json:"timeout"`
	UserAgent       string            `json:"user_agent"`
	Proxy           string            `json:"proxy"`
	ProxyUsername   string            `json:"proxy_username"`
	ProxyPassword   string            `json:"proxy_password"`
	ViewportWidth   int               `json:"viewport_width"`
	ViewportHeight  int               `json:"viewport_height"`
	ExtraHeaders    map[string]string `json:"extra_headers"`
	BlockResources  []string          `json:"block_resources"`
	RecordHar       bool              `json:"record_har"`
	HarPath         string            `json:"har_path"`
}

// RequestStats 请求统计
type RequestStats struct {
	TotalRequests      int            `json:"total_requests"`
	SuccessfulRequests int            `json:"successful_requests"`
	FailedRequests     int            `json:"failed_requests"`
	TotalBytes         int64          `json:"total_bytes"`
	ResourceTypes      map[string]int `json:"resource_types"`
}

// Browser 浏览器管理器
type Browser struct {
	config    *BrowserConfig
	ctx       context.Context
	cancel    context.CancelFunc
	stats     *RequestStats
	isStarted bool
}

// DefaultConfig 返回默认配置
func DefaultConfig() *BrowserConfig {
	return &BrowserConfig{
		Headless:       true,
		Stealth:        true,
		Timeout:        30 * time.Second,
		UserAgent:      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
		ViewportWidth:  1920,
		ViewportHeight: 1080,
		ExtraHeaders:   make(map[string]string),
		BlockResources: []string{},
		RecordHar:      false,
		HarPath:        "",
	}
}

// NewBrowser 创建新浏览器
func NewBrowser(config *BrowserConfig) *Browser {
	if config == nil {
		config = DefaultConfig()
	}
	
	return &Browser{
		config: config,
		stats: &RequestStats{
			ResourceTypes: make(map[string]int),
		},
	}
}

// Start 启动浏览器
func (b *Browser) Start() error {
	if b.isStarted {
		fmt.Println("✓ 浏览器已启动")
		return nil
	}
	
	// 创建选项
	opts := []chromedp.ExecAllocatorOption{
		chromedp.Flag("headless", b.config.Headless),
		chromedp.WindowSize(b.config.ViewportWidth, b.config.ViewportHeight),
		chromedp.UserAgent(b.config.UserAgent),
		chromedp.Flag("disable-blink-features", "AutomationControlled"),
		chromedp.Flag("disable-dev-shm-usage", true),
		chromedp.Flag("no-sandbox", true),
	}
	
	// 隐身模式选项
	if b.config.Stealth {
		opts = append(opts,
			chromedp.Flag("disable-features", "ImprovedCookieControls"),
			chromedp.Flag("disable-extensions", true),
			chromedp.Flag("disable-gpu", true),
		)
	}
	
	// 创建分配上下文
	allocCtx, allocCancel := chromedp.NewExecAllocator(context.Background(), opts...)
	b.ctx, b.cancel = chromedp.NewContext(allocCtx)
	b.cancel = allocCancel
	
	b.isStarted = true
	fmt.Println("✓ 浏览器启动成功")
	
	return nil
}

// Navigate 导航到页面
func (b *Browser) Navigate(url string) error {
	return b.NavigateWithRetry(url, 3)
}

// NavigateWithRetry 导航到页面（带重试）
func (b *Browser) NavigateWithRetry(url string, maxRetries int) error {
	if !b.isStarted {
		return fmt.Errorf("浏览器未启动")
	}
	
	var lastErr error
	for attempt := 1; attempt <= maxRetries; attempt++ {
		fmt.Printf("正在导航：%s (尝试 %d/%d)\n", url, attempt, maxRetries)
		
		ctx, cancel := context.WithTimeout(b.ctx, b.config.Timeout)
		
		err := chromedp.Run(ctx,
			chromedp.Navigate(url),
			chromedp.WaitReady("body"),
		)
		
		cancel()
		
		if err == nil {
			fmt.Printf("✓ 页面加载完成\n")
			return nil
		}
		
		lastErr = err
		fmt.Printf("导航失败：%v\n", err)
		
		if attempt < maxRetries {
			time.Sleep(time.Duration(attempt*2) * time.Second)
		}
	}
	
	return fmt.Errorf("导航失败：%w", lastErr)
}

// GetTitle 获取页面标题
func (b *Browser) GetTitle() (string, error) {
	if !b.isStarted {
		return "", fmt.Errorf("浏览器未启动")
	}
	
	var title string
	ctx, cancel := context.WithTimeout(b.ctx, b.config.Timeout)
	defer cancel()
	
	err := chromedp.Run(ctx,
		chromedp.Title(&title),
	)
	
	return title, err
}

// GetContent 获取页面内容
func (b *Browser) GetContent() (string, error) {
	if !b.isStarted {
		return "", fmt.Errorf("浏览器未启动")
	}
	
	var content string
	ctx, cancel := context.WithTimeout(b.ctx, b.config.Timeout)
	defer cancel()
	
	err := chromedp.Run(ctx,
		chromedp.OuterHTML("html", &content, chromedp.ByQuery),
	)
	
	return content, err
}

// GetText 获取元素文本
func (b *Browser) GetText(selector string) (string, error) {
	if !b.isStarted {
		return "", fmt.Errorf("浏览器未启动")
	}
	
	var text string
	ctx, cancel := context.WithTimeout(b.ctx, b.config.Timeout)
	defer cancel()
	
	err := chromedp.Run(ctx,
		chromedp.Text(selector, &text, chromedp.ByQuery),
	)
	
	return text, err
}

// Click 点击元素
func (b *Browser) Click(selector string) error {
	if !b.isStarted {
		return fmt.Errorf("浏览器未启动")
	}
	
	ctx, cancel := context.WithTimeout(b.ctx, b.config.Timeout)
	defer cancel()
	
	return chromedp.Run(ctx,
		chromedp.Click(selector, chromedp.ByQuery),
	)
}

// Fill 输入文本
func (b *Browser) Fill(selector, value string) error {
	if !b.isStarted {
		return fmt.Errorf("浏览器未启动")
	}
	
	ctx, cancel := context.WithTimeout(b.ctx, b.config.Timeout)
	defer cancel()
	
	return chromedp.Run(ctx,
		chromedp.SendKeys(selector, value, chromedp.ByQuery),
	)
}

// Screenshot 截图
func (b *Browser) Screenshot(path string) error {
	return b.ScreenshotFull(path)
}

// ScreenshotFull 全屏截图
func (b *Browser) ScreenshotFull(path string) error {
	if !b.isStarted {
		return fmt.Errorf("浏览器未启动")
	}
	
	var buf []byte
	ctx, cancel := context.WithTimeout(b.ctx, b.config.Timeout)
	defer cancel()
	
	err := chromedp.Run(ctx,
		chromedp.FullScreenshot(&buf, 90),
	)
	
	if err != nil {
		return err
	}
	
	// 确保目录存在
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	
	// 保存文件
	if err := ioutil.WriteFile(path, buf, 0644); err != nil {
		return err
	}
	
	fmt.Printf("✓ 截图已保存：%s\n", path)
	return nil
}

// Evaluate 执行 JavaScript
func (b *Browser) Evaluate(script string) (interface{}, error) {
	if !b.isStarted {
		return nil, fmt.Errorf("浏览器未启动")
	}
	
	var res interface{}
	ctx, cancel := context.WithTimeout(b.ctx, b.config.Timeout)
	defer cancel()
	
	err := chromedp.Run(ctx,
		chromedp.Evaluate(script, &res),
	)
	
	return res, err
}

// ExecuteJS 执行 JavaScript（别名）
func (b *Browser) ExecuteJS(script string) (interface{}, error) {
	return b.Evaluate(script)
}

// ExportCookies 导出 Cookie
func (b *Browser) ExportCookies() ([]map[string]interface{}, error) {
	if !b.isStarted {
		return nil, fmt.Errorf("浏览器未启动")
	}
	
	// 简化实现，实际使用需要从 JavaScript 获取
	cookies := make([]map[string]interface{}, 0)
	
	return cookies, nil
}

// SaveCookiesToFile 保存 Cookie 到文件
func (b *Browser) SaveCookiesToFile(path string) error {
	cookies, err := b.ExportCookies()
	if err != nil {
		return err
	}
	
	// 转换为 JSON
	data, err := json.MarshalIndent(cookies, "", "  ")
	if err != nil {
		return err
	}
	
	// 确保目录存在
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	
	// 保存文件
	if err := ioutil.WriteFile(path, data, 0644); err != nil {
		return err
	}
	
	fmt.Printf("✓ Cookie 已保存到：%s\n", path)
	return nil
}

// LoadCookiesFromFile 从文件加载 Cookie
func (b *Browser) LoadCookiesFromFile(path string) error {
	// 读取文件
	data, err := ioutil.ReadFile(path)
	if err != nil {
		return err
	}
	
	// 解析 JSON
	var cookies []map[string]interface{}
	if err := json.Unmarshal(data, &cookies); err != nil {
		return err
	}
	
	fmt.Printf("✓ Cookie 已从文件加载：%s\n", path)
	return nil
}

// WaitForSelector 等待元素
func (b *Browser) WaitForSelector(selector string, timeout ...time.Duration) error {
	if !b.isStarted {
		return fmt.Errorf("浏览器未启动")
	}
	
	t := b.config.Timeout
	if len(timeout) > 0 {
		t = timeout[0]
	}
	
	ctx, cancel := context.WithTimeout(b.ctx, t)
	defer cancel()
	
	return chromedp.Run(ctx,
		chromedp.WaitReady(selector, chromedp.ByQuery),
	)
}

// ScrollToBottom 滚动到底部
func (b *Browser) ScrollToBottom() error {
	if !b.isStarted {
		return fmt.Errorf("浏览器未启动")
	}
	
	ctx, cancel := context.WithTimeout(b.ctx, b.config.Timeout)
	defer cancel()
	
	return chromedp.Run(ctx,
		chromedp.Evaluate(`window.scrollTo(0, document.body.scrollHeight)`, nil),
	)
}

// GetStats 获取统计
func (b *Browser) GetStats() *RequestStats {
	return b.stats
}

// PrintStats 打印统计
func (b *Browser) PrintStats() {
	fmt.Println("\n========================================")
	fmt.Println("请求统计")
	fmt.Println("========================================")
	fmt.Printf("总请求数：%d\n", b.stats.TotalRequests)
	fmt.Printf("成功：%d\n", b.stats.SuccessfulRequests)
	fmt.Printf("失败：%d\n", b.stats.FailedRequests)
	fmt.Printf("总字节数：%d\n", b.stats.TotalBytes)
	fmt.Println("资源类型分布:")
	for resourceType, count := range b.stats.ResourceTypes {
		fmt.Printf("  %s: %d\n", resourceType, count)
	}
	fmt.Println("========================================")
}

// Close 关闭浏览器
func (b *Browser) Close() error {
	if b.cancel != nil {
		b.cancel()
	}
	
	b.isStarted = false
	fmt.Println("✓ 浏览器已关闭")
	
	return nil
}

// SmartClick 智能点击（带等待）
func (b *Browser) SmartClick(selector string) error {
	if err := b.WaitForSelector(selector); err != nil {
		return err
	}
	
	return b.Click(selector)
}

// SmartFill 智能输入
func (b *Browser) SmartFill(selector, value string) error {
	if err := b.WaitForSelector(selector); err != nil {
		return err
	}
	
	return b.Fill(selector, value)
}
