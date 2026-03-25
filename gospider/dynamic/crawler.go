package dynamic

import (
	"time"
	"log"
	"context"
	"github.com/chromedp/chromedp"
)

// DynamicCrawler 动态爬虫（增强版）
type DynamicCrawler struct {
	ctx    context.Context
	cancel context.CancelFunc
	opts   []chromedp.ExecAllocatorOption
	wait   *DynamicWait
}

// NewDynamicCrawler 创建动态爬虫
func NewDynamicCrawler(headless bool, timeout time.Duration) *DynamicCrawler {
	opts := append(chromedp.DefaultExecAllocatorOptions[:],
		chromedp.Flag("headless", headless),
		chromedp.Flag("disable-gpu", true),
		chromedp.Flag("no-sandbox", true),
		chromedp.Flag("disable-dev-shm-usage", true),
		chromedp.WindowSize(1920, 1080),
	)

	ctx, cancel := chromedp.NewExecAllocator(context.Background(), opts...)

	return &DynamicCrawler{
		ctx:    ctx,
		cancel: cancel,
		opts:   opts,
		wait:   NewDynamicWait(timeout, 500*time.Millisecond),
	}
}

// Navigate 导航到页面
func (dc *DynamicCrawler) Navigate(url string) error {
	ctx, cancel := chromedp.NewContext(dc.ctx)
	defer cancel()
	
	var title string
	err := chromedp.Run(ctx,
		chromedp.Navigate(url),
		chromedp.Title(&title),
	)
	log.Printf("Navigated to: %s (Title: %s)", url, title)
	return err
}

// WaitForLoad 等待页面加载
func (dc *DynamicCrawler) WaitForLoad(timeout time.Duration) error {
	ctx, cancel := chromedp.NewContext(dc.ctx)
	ctx, cancel = context.WithTimeout(ctx, timeout)
	defer cancel()

	return chromedp.Run(ctx,
		chromedp.WaitReady(`document`, chromedp.ByQuery),
	)
}

// WaitForNetworkIdle 等待网络空闲
func (dc *DynamicCrawler) WaitForNetworkIdle(timeout time.Duration) error {
	ctx, cancel := chromedp.NewContext(dc.ctx)
	ctx, cancel = context.WithTimeout(ctx, timeout)
	defer cancel()

	return chromedp.Run(ctx,
		chromedp.Sleep(time.Second),
	)
}

// ScrollAndLoad 滚动并加载（无限滚动支持）
func (dc *DynamicCrawler) ScrollAndLoad(pauseMs int, maxScrolls int) int {
	ctx, cancel := chromedp.NewContext(dc.ctx)
	defer cancel()

	scrollCount := 0
	var lastHeight float64

	for i := 0; i < maxScrolls; i++ {
		// 获取当前高度
		var height float64
		err := chromedp.Run(ctx,
			chromedp.Evaluate(`document.body.scrollHeight`, &height),
		)
		if err != nil {
			break
		}

		// 滚动到底部
		err = chromedp.Run(ctx,
			chromedp.Evaluate(`window.scrollTo(0, document.body.scrollHeight)`, nil),
		)
		if err != nil {
			break
		}

		scrollCount++
		time.Sleep(time.Duration(pauseMs) * time.Millisecond)

		// 检查高度是否变化
		if height == lastHeight && lastHeight > 0 {
			break
		}
		lastHeight = height
	}

	return scrollCount
}

// ClickAndWait 点击并等待
func (dc *DynamicCrawler) ClickAndWait(selector string, waitTimeout time.Duration) error {
	ctx, cancel := chromedp.NewContext(dc.ctx)
	ctx, cancel = context.WithTimeout(ctx, waitTimeout)
	defer cancel()

	err := chromedp.Run(ctx,
		chromedp.Click(selector, chromedp.NodeVisible),
		chromedp.WaitReady(`document`, chromedp.ByQuery),
	)
	return err
}

// FillAndWait 填写并等待
func (dc *DynamicCrawler) FillAndWait(selector, text string, waitTimeout time.Duration) error {
	ctx, cancel := chromedp.NewContext(dc.ctx)
	ctx, cancel = context.WithTimeout(ctx, waitTimeout)
	defer cancel()

	err := chromedp.Run(ctx,
		chromedp.SendKeys(selector, text, chromedp.NodeVisible),
		chromedp.WaitReady(`document`, chromedp.ByQuery),
	)
	return err
}

// GetContent 获取内容
func (dc *DynamicCrawler) GetContent() (string, error) {
	ctx, cancel := chromedp.NewContext(dc.ctx)
	defer cancel()
	
	var html string
	err := chromedp.Run(ctx,
		chromedp.OuterHTML(`html`, &html, chromedp.ByQuery),
	)
	return html, err
}

// Screenshot 截图
func (dc *DynamicCrawler) Screenshot(selector string) ([]byte, error) {
	ctx, cancel := chromedp.NewContext(dc.ctx)
	defer cancel()
	
	var buf []byte
	err := chromedp.Run(ctx,
		chromedp.Screenshot(selector, &buf, chromedp.NodeVisible),
	)
	return buf, err
}

// ExecuteJS 执行 JavaScript
func (dc *DynamicCrawler) ExecuteJS(script string) (interface{}, error) {
	ctx, cancel := chromedp.NewContext(dc.ctx)
	defer cancel()
	
	var result interface{}
	err := chromedp.Run(ctx,
		chromedp.Evaluate(script, &result),
	)
	return result, err
}

// Close 关闭
func (dc *DynamicCrawler) Close() {
	if dc.cancel != nil {
		dc.cancel()
	}
}

// DynamicWait 动态等待（引用）
func (dc *DynamicCrawler) Wait() *DynamicWait {
	return dc.wait
}
