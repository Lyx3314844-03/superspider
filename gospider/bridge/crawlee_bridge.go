package bridge

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// CrawleeBridgeClient Go 语言调用 Crawlee 桥接服务的客户端
type CrawleeBridgeClient struct {
	BridgeURL string
	Client    *http.Client
}

// CrawlRequest 请求结构
type CrawlRequest struct {
	URLs           []string `json:"urls"`
	OnPageScript   string   `json:"onPageScript,omitempty"`
	MaxConcurrency int      `json:"maxConcurrency,omitempty"`
}

// CrawlResponse 响应结构
type CrawlResponse struct {
	Success bool        `json:"success"`
	Data    interface{} `json:"data"`
	Error   string      `json:"error,omitempty"`
}

// NewCrawleeBridgeClient 创建新客户端
func NewCrawleeBridgeClient(bridgeURL string) *CrawleeBridgeClient {
	return &CrawleeBridgeClient{
		BridgeURL: bridgeURL,
		Client: &http.Client{
			Timeout: 120 * time.Second, // 增加超时时间
		},
	}
}

// Crawl 执行抓取
func (c *CrawleeBridgeClient) Crawl(urls []string, script string) (*CrawlResponse, error) {
	if len(urls) == 0 {
		return nil, fmt.Errorf("urls cannot be empty")
	}

	payload := CrawlRequest{
		URLs:           urls,
		OnPageScript:   script,
		MaxConcurrency: 2,
	}

	bodyBytes, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("marshal error: %v", err)
	}

	resp, err := c.Client.Post(c.BridgeURL+"/api/crawl", "application/json", bytes.NewBuffer(bodyBytes))
	if err != nil {
		return nil, fmt.Errorf("http request error: %v", err)
	}
	defer resp.Body.Close()

	// 检查 HTTP 状态码
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}

	var result CrawlResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("decode error: %v", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("bridge error: %s", result.Error)
	}

	return &result, nil
}
