package downloader

import (
	"io"
	"net/http"
	"net/http/cookiejar"
	"time"
)

// Downloader 下载器接口
type Downloader interface {
	Download(req *Request) *Response
}

// Request 请求对象（避免循环依赖）
type Request struct {
	URL     string
	Method  string
	Headers map[string]string
	Body    io.Reader
}

// Response 响应对象（避免循环依赖）
type Response struct {
	URL        string
	StatusCode int
	Headers    http.Header
	Body       []byte
	Text       string
	Request    *Request
	Duration   time.Duration
	Error      error
}

// HTTPDownloader HTTP 下载器
type HTTPDownloader struct {
	client *http.Client
}

// NewDownloader 创建下载器
func NewDownloader() *HTTPDownloader {
	jar, _ := cookiejar.New(nil)
	return &HTTPDownloader{
		client: &http.Client{
			Timeout: 30 * time.Second,
			Jar:     jar,
		},
	}
}

// Download 下载页面
func (d *HTTPDownloader) Download(req *Request) *Response {
	startTime := time.Now()

	// 创建 HTTP 请求
	httpReq, err := http.NewRequest(req.Method, req.URL, req.Body)
	if err != nil {
		return &Response{
			URL:   req.URL,
			Error: err,
		}
	}

	// 设置请求头
	for key, value := range req.Headers {
		httpReq.Header.Set(key, value)
	}

	// 执行请求
	httpResp, err := d.client.Do(httpReq)
	duration := time.Since(startTime)

	if err != nil {
		return &Response{
			URL:      req.URL,
			Error:    err,
			Duration: duration,
		}
	}
	defer httpResp.Body.Close()

	// 读取响应体
	body, err := io.ReadAll(httpResp.Body)
	if err != nil {
		return &Response{
			URL:      req.URL,
			Error:    err,
			Duration: duration,
		}
	}

	return &Response{
		URL:        req.URL,
		StatusCode: httpResp.StatusCode,
		Headers:    httpResp.Header,
		Body:       body,
		Text:       string(body),
		Request:    req,
		Duration:   duration,
		Error:      nil,
	}
}

// SetTimeout 设置超时
func (d *HTTPDownloader) SetTimeout(timeout time.Duration) {
	d.client.Timeout = timeout
}

// SetCookie 设置 Cookie
func (d *HTTPDownloader) SetCookie(domain string, cookies map[string]string) {
	// Cookie 处理逻辑
}
