// Package browser provides browser automation using chromedp
package browser

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/chromedp/cdproto/cdp"
	cdpnetwork "github.com/chromedp/cdproto/network"
	cdpruntime "github.com/chromedp/cdproto/runtime"
	"github.com/chromedp/chromedp"
	"gospider/parser"
)

// BrowserConfig 浏览器配置
type BrowserConfig struct {
	Headless       bool              `json:"headless"`
	Stealth        bool              `json:"stealth"`
	Timeout        time.Duration     `json:"timeout"`
	UserAgent      string            `json:"user_agent"`
	Proxy          string            `json:"proxy"`
	ProxyUsername  string            `json:"proxy_username"`
	ProxyPassword  string            `json:"proxy_password"`
	ViewportWidth  int               `json:"viewport_width"`
	ViewportHeight int               `json:"viewport_height"`
	ExtraHeaders   map[string]string `json:"extra_headers"`
	BlockResources []string          `json:"block_resources"`
	RecordHar      bool              `json:"record_har"`
	HarPath        string            `json:"har_path"`
}

// RequestStats 请求统计
type RequestStats struct {
	TotalRequests      int            `json:"total_requests"`
	SuccessfulRequests int            `json:"successful_requests"`
	FailedRequests     int            `json:"failed_requests"`
	TotalBytes         int64          `json:"total_bytes"`
	ResourceTypes      map[string]int `json:"resource_types"`
}

type ConsoleEntry struct {
	Type      string    `json:"type"`
	Text      string    `json:"text"`
	Timestamp time.Time `json:"timestamp"`
}

type NetworkEntry struct {
	RequestID         string    `json:"request_id"`
	URL               string    `json:"url"`
	Method            string    `json:"method,omitempty"`
	ResourceType      string    `json:"resource_type,omitempty"`
	Status            float64   `json:"status,omitempty"`
	MIMEType          string    `json:"mime_type,omitempty"`
	StartedAt         time.Time `json:"started_at,omitempty"`
	FinishedAt        time.Time `json:"finished_at,omitempty"`
	EncodedDataLength float64   `json:"encoded_data_length,omitempty"`
}

type RealtimeEntry struct {
	Protocol  string    `json:"protocol"`
	Direction string    `json:"direction,omitempty"`
	RequestID string    `json:"request_id,omitempty"`
	URL       string    `json:"url,omitempty"`
	EventName string    `json:"event_name,omitempty"`
	EventID   string    `json:"event_id,omitempty"`
	Opcode    float64   `json:"opcode,omitempty"`
	Data      string    `json:"data,omitempty"`
	Error     string    `json:"error,omitempty"`
	Timestamp time.Time `json:"timestamp"`
}

// Browser 浏览器管理器
type Browser struct {
	config          *BrowserConfig
	ctx             context.Context
	cancel          context.CancelFunc
	stats           *RequestStats
	mu              sync.RWMutex
	consoleEntries  []ConsoleEntry
	networkEntries  []NetworkEntry
	realtimeEntries []RealtimeEntry
	networkIndex    map[string]int
	websocketURLs   map[string]string
	isStarted       bool
	behaviorProfile BehaviorProfile
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
		consoleEntries:  make([]ConsoleEntry, 0),
		networkEntries:  make([]NetworkEntry, 0),
		realtimeEntries: make([]RealtimeEntry, 0),
		networkIndex:    make(map[string]int),
		websocketURLs:   make(map[string]string),
		behaviorProfile: DefaultBehaviorProfile(),
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
	if b.config.Proxy != "" {
		opts = append(opts, chromedp.ProxyServer(b.config.Proxy))
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
	taskCtx, taskCancel := chromedp.NewContext(allocCtx)
	b.ctx = taskCtx
	b.cancel = func() {
		taskCancel()
		allocCancel()
	}

	if err := chromedp.Run(taskCtx, cdpnetwork.Enable(), cdpruntime.Enable()); err != nil {
		allocCancel()
		taskCancel()
		return err
	}
	if len(b.config.BlockResources) > 0 {
		if err := chromedp.Run(taskCtx, cdpnetwork.SetBlockedURLS(b.config.BlockResources)); err != nil {
			allocCancel()
			taskCancel()
			return err
		}
	}
	if len(b.config.ExtraHeaders) > 0 {
		headers := cdpnetwork.Headers{}
		for key, value := range b.config.ExtraHeaders {
			headers[key] = value
		}
		_ = chromedp.Run(taskCtx, cdpnetwork.SetExtraHTTPHeaders(headers))
	}
	chromedp.ListenTarget(taskCtx, b.listenTarget)

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

// GetURL returns the current page URL.
func (b *Browser) GetURL() (string, error) {
	value, err := b.Evaluate("window.location.href")
	if err != nil {
		return "", err
	}
	if current, ok := value.(string); ok {
		return current, nil
	}
	return fmt.Sprint(value), nil
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
	time.Sleep(RandomizedActionDelay("click", b.behaviorProfile, time.Now()))

	ctx, cancel := context.WithTimeout(b.ctx, b.config.Timeout)
	defer cancel()

	return chromedp.Run(ctx,
		chromedp.Click(selector, chromedp.ByQuery),
	)
}

func (b *Browser) AnalyzeLocators(target parser.LocatorTarget) (*parser.LocatorPlan, error) {
	html, err := b.GetContent()
	if err != nil {
		return nil, err
	}
	return parser.NewLocatorAnalyzer().Analyze(html, target)
}

func (b *Browser) AnalyzeDevTools() (*parser.DevToolsReport, error) {
	html, err := b.GetContent()
	if err != nil {
		return nil, err
	}
	network := make([]parser.DevToolsNetworkArtifact, 0, len(b.GetNetworkEntries()))
	for _, entry := range b.GetNetworkEntries() {
		network = append(network, parser.DevToolsNetworkArtifact{
			URL:          entry.URL,
			Method:       entry.Method,
			Status:       int(entry.Status),
			ResourceType: strings.ToLower(entry.ResourceType),
		})
	}
	console := make([]map[string]string, 0, len(b.GetConsoleEntries()))
	for _, entry := range b.GetConsoleEntries() {
		console = append(console, map[string]string{
			"type": entry.Type,
			"text": entry.Text,
		})
	}
	return parser.NewDevToolsAnalyzer().Analyze(html, network, console)
}

func (b *Browser) DevToolsAnalyze() (*parser.DevToolsReport, error) {
	return b.AnalyzeDevTools()
}

func (b *Browser) AutoClick(target parser.LocatorTarget) (*parser.LocatorCandidate, error) {
	if !b.isStarted {
		return nil, fmt.Errorf("浏览器未启动")
	}
	plan, err := b.AnalyzeLocators(target)
	if err != nil {
		return nil, err
	}
	var lastErr error
	for _, candidate := range plan.Candidates {
		if err := b.clickCandidate(candidate); err == nil {
			return &candidate, nil
		} else {
			lastErr = err
		}
	}
	return nil, fmt.Errorf("auto click target not found: %w", lastErr)
}

// Fill 输入文本
func (b *Browser) Fill(selector, value string) error {
	if !b.isStarted {
		return fmt.Errorf("浏览器未启动")
	}
	time.Sleep(RandomizedActionDelay("type", b.behaviorProfile, time.Now()))

	ctx, cancel := context.WithTimeout(b.ctx, b.config.Timeout)
	defer cancel()

	return chromedp.Run(ctx,
		chromedp.SendKeys(selector, value, chromedp.ByQuery),
	)
}

func (b *Browser) AutoFill(target parser.LocatorTarget, value string) (*parser.LocatorCandidate, error) {
	if !b.isStarted {
		return nil, fmt.Errorf("浏览器未启动")
	}
	plan, err := b.AnalyzeLocators(target)
	if err != nil {
		return nil, err
	}
	var lastErr error
	for _, candidate := range plan.Candidates {
		if err := b.fillCandidate(candidate, value); err == nil {
			return &candidate, nil
		} else {
			lastErr = err
		}
	}
	return nil, fmt.Errorf("auto fill target not found: %w", lastErr)
}

func (b *Browser) clickCandidate(candidate parser.LocatorCandidate) error {
	ctx, cancel := context.WithTimeout(b.ctx, b.config.Timeout)
	defer cancel()
	if candidate.Kind == "xpath" {
		expr, _ := json.Marshal(candidate.Expr)
		return chromedp.Run(ctx, chromedp.Evaluate(fmt.Sprintf(`(() => {
			const node = document.evaluate(%s, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
			if (!node) throw new Error("xpath not found");
			node.click();
		})()`, expr), nil))
	}
	return chromedp.Run(ctx, chromedp.Click(candidate.Expr, chromedp.ByQuery))
}

func (b *Browser) fillCandidate(candidate parser.LocatorCandidate, value string) error {
	ctx, cancel := context.WithTimeout(b.ctx, b.config.Timeout)
	defer cancel()
	if candidate.Kind == "xpath" {
		expr, _ := json.Marshal(candidate.Expr)
		valueJSON, _ := json.Marshal(value)
		return chromedp.Run(ctx, chromedp.Evaluate(fmt.Sprintf(`(() => {
			const node = document.evaluate(%s, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
			if (!node) throw new Error("xpath not found");
			node.value = %s;
			node.dispatchEvent(new Event("input", {bubbles: true}));
			node.dispatchEvent(new Event("change", {bubbles: true}));
		})()`, expr, valueJSON), nil))
	}
	return chromedp.Run(ctx, chromedp.SendKeys(candidate.Expr, value, chromedp.ByQuery))
}

// UploadFile uploads one or more files through an <input type="file"> element.
func (b *Browser) UploadFile(selector string, filePaths ...string) error {
	if !b.isStarted {
		return fmt.Errorf("浏览器未启动")
	}
	normalized, err := normalizeUploadPaths(filePaths)
	if err != nil {
		return err
	}

	ctx, cancel := context.WithTimeout(b.ctx, b.config.Timeout)
	defer cancel()

	return chromedp.Run(ctx,
		chromedp.SetUploadFiles(selector, normalized, chromedp.ByQuery),
	)
}

// Hover 将鼠标移动到元素上方并触发常见 hover 事件。
func (b *Browser) Hover(selector string) error {
	if !b.isStarted {
		return fmt.Errorf("浏览器未启动")
	}
	time.Sleep(RandomizedActionDelay("hover", b.behaviorProfile, time.Now()))

	selectorJSON, err := json.Marshal(selector)
	if err != nil {
		return err
	}

	script := fmt.Sprintf(`(() => {
		const selector = %s;
		const element = document.querySelector(selector);
		if (!element) {
			throw new Error("selector not found: " + selector);
		}
		element.scrollIntoView({block: "center", inline: "center"});
		const rect = element.getBoundingClientRect();
		const init = {
			view: window,
			bubbles: true,
			cancelable: true,
			clientX: rect.left + rect.width / 2,
			clientY: rect.top + rect.height / 2
		};
		for (const eventName of ["mouseover", "mouseenter", "mousemove"]) {
			element.dispatchEvent(new MouseEvent(eventName, init));
		}
		return true;
	})()`, string(selectorJSON))

	_, err = b.ExecuteJS(script)
	return err
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
	if err := os.WriteFile(path, buf, 0644); err != nil {
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

// GetShadowText returns text from an element reached through open Shadow DOM roots.
func (b *Browser) GetShadowText(selectorPath ...string) (string, error) {
	value, err := b.ExecuteShadowDOM("target.textContent || ''", selectorPath...)
	if err != nil {
		return "", err
	}
	if text, ok := value.(string); ok {
		return text, nil
	}
	return fmt.Sprint(value), nil
}

// GetShadowContent returns HTML from an element reached through open Shadow DOM roots.
func (b *Browser) GetShadowContent(selectorPath ...string) (string, error) {
	value, err := b.ExecuteShadowDOM("target.outerHTML || target.textContent || ''", selectorPath...)
	if err != nil {
		return "", err
	}
	if text, ok := value.(string); ok {
		return text, nil
	}
	return fmt.Sprint(value), nil
}

// ExecuteShadowDOM evaluates an expression against an element reached through open Shadow DOM roots.
func (b *Browser) ExecuteShadowDOM(expression string, selectorPath ...string) (interface{}, error) {
	if !b.isStarted {
		return nil, fmt.Errorf("浏览器未启动")
	}
	script, err := buildShadowTraversalScript(selectorPath, expression)
	if err != nil {
		return nil, err
	}
	return b.ExecuteJS(script)
}

// ExecuteInFrame executes JavaScript inside a same-origin iframe selected from the top document.
func (b *Browser) ExecuteInFrame(frameSelector, script string) (interface{}, error) {
	if !b.isStarted {
		return nil, fmt.Errorf("浏览器未启动")
	}

	frameScript, err := buildFrameEvalScript(frameSelector, script)
	if err != nil {
		return nil, err
	}
	return b.ExecuteJS(frameScript)
}

// GetFrameContent returns the current HTML content of a same-origin iframe.
func (b *Browser) GetFrameContent(frameSelector string) (string, error) {
	value, err := b.ExecuteInFrame(frameSelector, "document.documentElement.outerHTML")
	if err != nil {
		return "", err
	}
	if text, ok := value.(string); ok {
		return text, nil
	}
	return fmt.Sprint(value), nil
}

// ClickInFrame clicks an element inside a same-origin iframe.
func (b *Browser) ClickInFrame(frameSelector, selector string) error {
	if !b.isStarted {
		return fmt.Errorf("浏览器未启动")
	}
	time.Sleep(RandomizedActionDelay("click", b.behaviorProfile, time.Now()))

	script, err := buildFrameMutationScript(frameSelector, selector, "click", "")
	if err != nil {
		return err
	}
	_, err = b.ExecuteJS(script)
	return err
}

// FillInFrame fills an input element inside a same-origin iframe.
func (b *Browser) FillInFrame(frameSelector, selector, value string) error {
	if !b.isStarted {
		return fmt.Errorf("浏览器未启动")
	}
	time.Sleep(RandomizedActionDelay("type", b.behaviorProfile, time.Now()))

	script, err := buildFrameMutationScript(frameSelector, selector, "fill", value)
	if err != nil {
		return err
	}
	_, err = b.ExecuteJS(script)
	return err
}

// ExportCookies 导出 Cookie
func (b *Browser) ExportCookies() ([]map[string]interface{}, error) {
	if !b.isStarted {
		return nil, fmt.Errorf("浏览器未启动")
	}

	ctx, cancel := context.WithTimeout(b.ctx, b.config.Timeout)
	defer cancel()

	cdpCookies, err := cdpnetwork.GetCookies().Do(ctx)
	if err != nil {
		return nil, err
	}
	cookies := make([]map[string]interface{}, 0, len(cdpCookies))
	for _, cookie := range cdpCookies {
		cookies = append(cookies, cookieToMap(cookie))
	}

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
	if err := os.WriteFile(path, data, 0644); err != nil {
		return err
	}

	fmt.Printf("✓ Cookie 已保存到：%s\n", path)
	return nil
}

// LoadCookiesFromFile 从文件加载 Cookie
func (b *Browser) LoadCookiesFromFile(path string) error {
	// 验证路径安全性
	if path == "" {
		return fmt.Errorf("路径不能为空")
	}

	// 检查文件扩展名
	if filepath.Ext(path) != ".json" {
		return fmt.Errorf("Cookie 文件必须是 .json 格式")
	}

	// 读取文件
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}

	// 解析 JSON
	var cookies []map[string]interface{}
	if err := json.Unmarshal(data, &cookies); err != nil {
		return err
	}
	params := make([]*cdpnetwork.CookieParam, 0, len(cookies))
	for _, cookie := range cookies {
		param, err := cookieParamFromMap(cookie)
		if err != nil {
			return err
		}
		params = append(params, param)
	}
	if len(params) > 0 {
		ctx, cancel := context.WithTimeout(b.ctx, b.config.Timeout)
		defer cancel()
		if err := cdpnetwork.SetCookies(params).Do(ctx); err != nil {
			return err
		}
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
	time.Sleep(RandomizedActionDelay("scroll", b.behaviorProfile, time.Now()))

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
	b.mu.RLock()
	defer b.mu.RUnlock()
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

func (b *Browser) GetConsoleEntries() []ConsoleEntry {
	b.mu.RLock()
	defer b.mu.RUnlock()
	result := make([]ConsoleEntry, len(b.consoleEntries))
	copy(result, b.consoleEntries)
	return result
}

func (b *Browser) GetNetworkEntries() []NetworkEntry {
	b.mu.RLock()
	defer b.mu.RUnlock()
	result := make([]NetworkEntry, len(b.networkEntries))
	copy(result, b.networkEntries)
	return result
}

func (b *Browser) GetRealtimeEntries() []RealtimeEntry {
	b.mu.RLock()
	defer b.mu.RUnlock()
	result := make([]RealtimeEntry, len(b.realtimeEntries))
	copy(result, b.realtimeEntries)
	return result
}

func (b *Browser) SaveConsoleToFile(path string) error {
	data, err := json.MarshalIndent(b.GetConsoleEntries(), "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}

func (b *Browser) SaveNetworkToFile(path string) error {
	data, err := json.MarshalIndent(b.GetNetworkEntries(), "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}

func (b *Browser) SaveRealtimeToFile(path string) error {
	data, err := json.MarshalIndent(b.GetRealtimeEntries(), "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}

func (b *Browser) SaveHARToFile(path string) error {
	entries := make([]map[string]interface{}, 0)
	for _, entry := range b.GetNetworkEntries() {
		elapsed := 0.0
		if !entry.StartedAt.IsZero() && !entry.FinishedAt.IsZero() {
			elapsed = entry.FinishedAt.Sub(entry.StartedAt).Seconds() * 1000
		}
		entries = append(entries, map[string]interface{}{
			"startedDateTime": entry.StartedAt.Format(time.RFC3339Nano),
			"time":            elapsed,
			"request": map[string]interface{}{
				"method": entry.Method,
				"url":    entry.URL,
			},
			"response": map[string]interface{}{
				"status": entry.Status,
				"content": map[string]interface{}{
					"mimeType": entry.MIMEType,
					"size":     entry.EncodedDataLength,
				},
			},
			"_resourceType": entry.ResourceType,
		})
	}
	payload := map[string]interface{}{
		"log": map[string]interface{}{
			"version": "1.2",
			"creator": map[string]interface{}{
				"name":    "gospider",
				"version": "2.0.0",
			},
			"entries": entries,
		},
	}
	data, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
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

func (b *Browser) listenTarget(ev interface{}) {
	switch e := ev.(type) {
	case *cdpnetwork.EventRequestWillBeSent:
		b.recordRequestStart(string(e.RequestID), e.Request.URL, e.Request.Method, string(e.Type))
	case *cdpnetwork.EventResponseReceived:
		b.recordResponse(string(e.RequestID), e.Response.URL, string(e.Type), float64(e.Response.Status), e.Response.MimeType)
	case *cdpnetwork.EventLoadingFinished:
		b.recordLoadingFinished(string(e.RequestID), e.EncodedDataLength)
	case *cdpnetwork.EventLoadingFailed:
		b.recordLoadingFailed(string(e.RequestID))
	case *cdpruntime.EventConsoleAPICalled:
		b.recordConsole(string(e.Type), consoleText(e.Args))
	case *cdpruntime.EventExceptionThrown:
		b.recordConsole("exception", e.ExceptionDetails.Text)
	case *cdpnetwork.EventWebSocketCreated:
		b.recordWebSocketCreated(string(e.RequestID), e.URL)
	case *cdpnetwork.EventWebSocketFrameSent:
		b.recordWebSocketFrame(string(e.RequestID), "sent", e.Response)
	case *cdpnetwork.EventWebSocketFrameReceived:
		b.recordWebSocketFrame(string(e.RequestID), "received", e.Response)
	case *cdpnetwork.EventWebSocketFrameError:
		b.recordRealtime(RealtimeEntry{
			Protocol:  "websocket",
			Direction: "error",
			RequestID: string(e.RequestID),
			Error:     e.ErrorMessage,
		})
	case *cdpnetwork.EventEventSourceMessageReceived:
		b.recordRealtime(RealtimeEntry{
			Protocol:  "sse",
			Direction: "received",
			RequestID: string(e.RequestID),
			URL:       b.urlForRequestID(string(e.RequestID)),
			EventName: e.EventName,
			EventID:   e.EventID,
			Data:      e.Data,
		})
	}
}

func consoleText(args []*cdpruntime.RemoteObject) string {
	parts := make([]string, 0, len(args))
	for _, arg := range args {
		switch {
		case arg == nil:
			continue
		case arg.Description != "":
			parts = append(parts, arg.Description)
		case len(arg.Value) > 0:
			parts = append(parts, strings.Trim(string(arg.Value), "\""))
		default:
			parts = append(parts, string(arg.Type))
		}
	}
	return strings.Join(parts, " ")
}

func (b *Browser) recordRequestStart(requestID, url, method, resourceType string) {
	b.mu.Lock()
	defer b.mu.Unlock()

	entry := NetworkEntry{
		RequestID:    requestID,
		URL:          url,
		Method:       method,
		ResourceType: resourceType,
		StartedAt:    time.Now(),
	}
	b.networkIndex[requestID] = len(b.networkEntries)
	b.networkEntries = append(b.networkEntries, entry)
	b.stats.TotalRequests++
	b.stats.ResourceTypes[resourceType] = b.stats.ResourceTypes[resourceType] + 1
}

func (b *Browser) recordResponse(requestID, url, resourceType string, status float64, mimeType string) {
	b.mu.Lock()
	defer b.mu.Unlock()

	index, ok := b.networkIndex[requestID]
	if !ok {
		entry := NetworkEntry{
			RequestID:    requestID,
			URL:          url,
			ResourceType: resourceType,
			Status:       status,
			MIMEType:     mimeType,
			StartedAt:    time.Now(),
		}
		b.networkIndex[requestID] = len(b.networkEntries)
		b.networkEntries = append(b.networkEntries, entry)
		index = len(b.networkEntries) - 1
	}

	b.networkEntries[index].URL = url
	b.networkEntries[index].ResourceType = resourceType
	b.networkEntries[index].Status = status
	b.networkEntries[index].MIMEType = mimeType
	if status >= 400 {
		b.stats.FailedRequests++
	} else {
		b.stats.SuccessfulRequests++
	}
}

func (b *Browser) recordLoadingFinished(requestID string, encodedLength float64) {
	b.mu.Lock()
	defer b.mu.Unlock()
	if index, ok := b.networkIndex[requestID]; ok {
		b.networkEntries[index].FinishedAt = time.Now()
		b.networkEntries[index].EncodedDataLength = encodedLength
	}
	b.stats.TotalBytes += int64(encodedLength)
}

func (b *Browser) recordLoadingFailed(requestID string) {
	b.mu.Lock()
	defer b.mu.Unlock()
	if index, ok := b.networkIndex[requestID]; ok {
		b.networkEntries[index].FinishedAt = time.Now()
	}
	b.stats.FailedRequests++
}

func (b *Browser) recordConsole(kind, text string) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.consoleEntries = append(b.consoleEntries, ConsoleEntry{
		Type:      kind,
		Text:      text,
		Timestamp: time.Now(),
	})
}

func (b *Browser) recordWebSocketCreated(requestID, url string) {
	b.mu.Lock()
	b.websocketURLs[requestID] = url
	b.mu.Unlock()
	b.recordRealtime(RealtimeEntry{
		Protocol:  "websocket",
		Direction: "open",
		RequestID: requestID,
		URL:       url,
	})
}

func (b *Browser) recordWebSocketFrame(requestID, direction string, frame *cdpnetwork.WebSocketFrame) {
	entry := RealtimeEntry{
		Protocol:  "websocket",
		Direction: direction,
		RequestID: requestID,
		URL:       b.urlForRequestID(requestID),
	}
	if frame != nil {
		entry.Opcode = frame.Opcode
		entry.Data = frame.PayloadData
	}
	b.recordRealtime(entry)
}

func (b *Browser) recordRealtime(entry RealtimeEntry) {
	b.mu.Lock()
	defer b.mu.Unlock()
	if entry.URL == "" {
		entry.URL = b.websocketURLs[entry.RequestID]
	}
	if entry.Timestamp.IsZero() {
		entry.Timestamp = time.Now()
	}
	b.realtimeEntries = append(b.realtimeEntries, entry)
}

func (b *Browser) urlForRequestID(requestID string) string {
	b.mu.RLock()
	defer b.mu.RUnlock()
	if url := b.websocketURLs[requestID]; url != "" {
		return url
	}
	if index, ok := b.networkIndex[requestID]; ok && index < len(b.networkEntries) {
		return b.networkEntries[index].URL
	}
	return ""
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

func normalizeUploadPaths(paths []string) ([]string, error) {
	if len(paths) == 0 {
		return nil, fmt.Errorf("至少需要一个上传文件路径")
	}
	normalized := make([]string, 0, len(paths))
	for _, raw := range paths {
		if strings.TrimSpace(raw) == "" {
			return nil, fmt.Errorf("上传文件路径不能为空")
		}
		absolute, err := filepath.Abs(raw)
		if err != nil {
			return nil, err
		}
		if _, err := os.Stat(absolute); err != nil {
			return nil, err
		}
		normalized = append(normalized, absolute)
	}
	return normalized, nil
}

func cookieToMap(cookie *cdpnetwork.Cookie) map[string]interface{} {
	if cookie == nil {
		return map[string]interface{}{}
	}
	return map[string]interface{}{
		"name":       cookie.Name,
		"value":      cookie.Value,
		"domain":     cookie.Domain,
		"path":       cookie.Path,
		"expires":    cookie.Expires,
		"httpOnly":   cookie.HTTPOnly,
		"secure":     cookie.Secure,
		"sameSite":   cookie.SameSite.String(),
		"session":    cookie.Session,
		"sourcePort": cookie.SourcePort,
	}
}

func cookieParamFromMap(cookie map[string]interface{}) (*cdpnetwork.CookieParam, error) {
	name, _ := cookie["name"].(string)
	value, _ := cookie["value"].(string)
	if strings.TrimSpace(name) == "" {
		return nil, fmt.Errorf("Cookie name cannot be empty")
	}
	param := &cdpnetwork.CookieParam{
		Name:  name,
		Value: value,
	}
	if url, _ := cookie["url"].(string); strings.TrimSpace(url) != "" {
		param.URL = url
	}
	if domain, _ := cookie["domain"].(string); strings.TrimSpace(domain) != "" {
		param.Domain = domain
	}
	if path, _ := cookie["path"].(string); strings.TrimSpace(path) != "" {
		param.Path = path
	}
	if secure, ok := cookie["secure"].(bool); ok {
		param.Secure = secure
	}
	if httpOnly, ok := cookie["httpOnly"].(bool); ok {
		param.HTTPOnly = httpOnly
	}
	if sameSite, _ := cookie["sameSite"].(string); sameSite != "" {
		param.SameSite = cdpnetwork.CookieSameSite(sameSite)
	}
	if expires, ok := numberFromCookie(cookie["expires"]); ok && expires > 0 {
		ts := cdp.TimeSinceEpoch(time.Unix(int64(expires), 0))
		param.Expires = &ts
	}
	return param, nil
}

func numberFromCookie(value interface{}) (float64, bool) {
	switch typed := value.(type) {
	case float64:
		return typed, true
	case int:
		return float64(typed), true
	case int64:
		return float64(typed), true
	case json.Number:
		parsed, err := typed.Float64()
		return parsed, err == nil
	default:
		return 0, false
	}
}

func normalizeShadowPath(selectors []string) ([]string, error) {
	if len(selectors) == 0 {
		return nil, fmt.Errorf("至少需要一个 Shadow DOM 选择器")
	}
	normalized := make([]string, 0, len(selectors))
	for _, selector := range selectors {
		selector = strings.TrimSpace(selector)
		if selector == "" {
			return nil, fmt.Errorf("Shadow DOM 选择器不能为空")
		}
		normalized = append(normalized, selector)
	}
	return normalized, nil
}

func splitShadowPath(path string) []string {
	parts := strings.Split(path, ">>>")
	selectors := make([]string, 0, len(parts))
	for _, part := range parts {
		if trimmed := strings.TrimSpace(part); trimmed != "" {
			selectors = append(selectors, trimmed)
		}
	}
	return selectors
}

func SplitShadowPathForRuntime(path string) []string {
	return splitShadowPath(path)
}

func buildShadowTraversalScript(selectors []string, expression string) (string, error) {
	normalized, err := normalizeShadowPath(selectors)
	if err != nil {
		return "", err
	}
	if strings.TrimSpace(expression) == "" {
		return "", fmt.Errorf("Shadow DOM 表达式不能为空")
	}
	selectorsJSON, err := json.Marshal(normalized)
	if err != nil {
		return "", err
	}
	return fmt.Sprintf(`(() => {
		const selectors = %s;
		let root = document;
		let target = null;
		for (let index = 0; index < selectors.length; index++) {
			const selector = selectors[index];
			target = root.querySelector(selector);
			if (!target) {
				throw new Error("shadow selector not found: " + selector);
			}
			if (index < selectors.length - 1) {
				if (!target.shadowRoot) {
					throw new Error("open shadowRoot not found: " + selector);
				}
				root = target.shadowRoot;
			}
		}
		return (%s);
	})()`, string(selectorsJSON), expression), nil
}

func buildFrameEvalScript(frameSelector, script string) (string, error) {
	frameJSON, err := json.Marshal(frameSelector)
	if err != nil {
		return "", err
	}
	scriptJSON, err := json.Marshal(script)
	if err != nil {
		return "", err
	}
	return fmt.Sprintf(`(() => {
		const frameSelector = %s;
		const frame = document.querySelector(frameSelector);
		if (!frame) {
			throw new Error("frame not found: " + frameSelector);
		}
		const win = frame.contentWindow;
		const doc = frame.contentDocument;
		if (!win || !doc) {
			throw new Error("iframe is not same-origin or not loaded: " + frameSelector);
		}
		return win.eval(%s);
	})()`, string(frameJSON), string(scriptJSON)), nil
}

func buildFrameMutationScript(frameSelector, selector, mode, value string) (string, error) {
	frameJSON, err := json.Marshal(frameSelector)
	if err != nil {
		return "", err
	}
	selectorJSON, err := json.Marshal(selector)
	if err != nil {
		return "", err
	}
	valueJSON, err := json.Marshal(value)
	if err != nil {
		return "", err
	}
	return fmt.Sprintf(`(() => {
		const frameSelector = %s;
		const selector = %s;
		const value = %s;
		const frame = document.querySelector(frameSelector);
		if (!frame) {
			throw new Error("frame not found: " + frameSelector);
		}
		const doc = frame.contentDocument;
		if (!doc) {
			throw new Error("iframe is not same-origin or not loaded: " + frameSelector);
		}
		const target = doc.querySelector(selector);
		if (!target) {
			throw new Error("selector not found in frame: " + selector);
		}
		target.scrollIntoView({block: "center", inline: "center"});
		if (%q === "click") {
			target.dispatchEvent(new MouseEvent("mouseover", {view: window, bubbles: true, cancelable: true}));
			target.dispatchEvent(new MouseEvent("mousedown", {view: window, bubbles: true, cancelable: true}));
			target.click();
			target.dispatchEvent(new MouseEvent("mouseup", {view: window, bubbles: true, cancelable: true}));
			return true;
		}
		target.focus();
		target.value = value;
		target.dispatchEvent(new Event("input", {bubbles: true}));
		target.dispatchEvent(new Event("change", {bubbles: true}));
		return true;
	})()`, string(frameJSON), string(selectorJSON), string(valueJSON), mode), nil
}
