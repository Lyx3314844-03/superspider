package middleware

import (
	"gospider/core"
	"math/rand"
	"time"
)

// RequestMiddleware 请求中间件接口
type RequestMiddleware interface {
	ProcessRequest(req *core.Request) *core.Request
}

// ResponseMiddleware 响应中间件接口
type ResponseMiddleware interface {
	ProcessResponse(resp *core.Response) *core.Response
}

// UserAgentMiddleware 用户代理中间件
type UserAgentMiddleware struct {
	UserAgents []string
	Random bool
}

// NewUserAgentMiddleware 创建用户代理中间件
func NewUserAgentMiddleware(userAgents []string, random bool) *UserAgentMiddleware {
	return &UserAgentMiddleware{
		UserAgents: userAgents,
		Random: random,
	}
}

// ProcessRequest 处理请求
func (m *UserAgentMiddleware) ProcessRequest(req *core.Request) *core.Request {
	if m.Random && len(m.UserAgents) > 0 {
		rand.Seed(time.Now().UnixNano())
		req.SetHeader("User-Agent", m.UserAgents[rand.Intn(len(m.UserAgents))])
	} else if len(m.UserAgents) > 0 {
		req.SetHeader("User-Agent", m.UserAgents[0])
	}
	return req
}

// DefaultUserAgents 默认用户代理列表
var DefaultUserAgents = []string{
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
	"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

// CookieMiddleware Cookie 中间件
type CookieMiddleware struct {
	Cookies map[string]string
	AutoHandle bool
}

// NewCookieMiddleware 创建 Cookie 中间件
func NewCookieMiddleware(cookies map[string]string, autoHandle bool) *CookieMiddleware {
	return &CookieMiddleware{
		Cookies: cookies,
		AutoHandle: autoHandle,
	}
}

// ProcessRequest 处理请求
func (m *CookieMiddleware) ProcessRequest(req *core.Request) *core.Request {
	for key, value := range m.Cookies {
		req.SetHeader("Cookie", key+"="+value)
	}
	return req
}

// ProcessResponse 处理响应
func (m *CookieMiddleware) ProcessResponse(resp *core.Response) *core.Response {
	if m.AutoHandle {
		// 自动处理 Cookie
		if cookies, ok := resp.Headers["Set-Cookie"]; ok {
			for _, cookie := range cookies {
				// 解析并保存 Cookie
				_ = cookie
			}
		}
	}
	return resp
}

// RetryMiddleware 重试中间件
type RetryMiddleware struct {
	MaxRetries int
	RetryCodes []int
}

// NewRetryMiddleware 创建重试中间件
func NewRetryMiddleware(maxRetries int, retryCodes []int) *RetryMiddleware {
	if len(retryCodes) == 0 {
		retryCodes = []int{500, 502, 503, 504, 408, 429}
	}
	return &RetryMiddleware{
		MaxRetries: maxRetries,
		RetryCodes: retryCodes,
	}
}

// ProcessResponse 处理响应
func (m *RetryMiddleware) ProcessResponse(resp *core.Response) *core.Response {
	for _, code := range m.RetryCodes {
		if resp.StatusCode == code {
			// 需要重试
			return resp
		}
	}
	return resp
}

// ShouldRetry 是否应该重试
func (m *RetryMiddleware) ShouldRetry(resp *core.Response, retryCount int) bool {
	if retryCount >= m.MaxRetries {
		return false
	}
	for _, code := range m.RetryCodes {
		if resp.StatusCode == code {
			return true
		}
	}
	return false
}

// RedirectMiddleware 重定向中间件
type RedirectMiddleware struct {
	MaxRedirects int
	AutoRedirect bool
}

// NewRedirectMiddleware 创建重定向中间件
func NewRedirectMiddleware(maxRedirects int, autoRedirect bool) *RedirectMiddleware {
	return &RedirectMiddleware{
		MaxRedirects: maxRedirects,
		AutoRedirect: autoRedirect,
	}
}

// ProcessResponse 处理响应
func (m *RedirectMiddleware) ProcessResponse(resp *core.Response) *core.Response {
	if m.AutoRedirect && resp.StatusCode >= 300 && resp.StatusCode < 400 {
		// 处理重定向
		if location, ok := resp.Headers["Location"]; ok && len(location) > 0 {
			// 返回重定向信息
			_ = location[0]
		}
	}
	return resp
}

// MiddlewareChain 中间件链
type MiddlewareChain struct {
	RequestMiddlewares  []RequestMiddleware
	ResponseMiddlewares []ResponseMiddleware
}

// NewMiddlewareChain 创建中间件链
func NewMiddlewareChain() *MiddlewareChain {
	return &MiddlewareChain{
		RequestMiddlewares:  make([]RequestMiddleware, 0),
		ResponseMiddlewares: make([]ResponseMiddleware, 0),
	}
}

// AddRequestMiddleware 添加请求中间件
func (c *MiddlewareChain) AddRequestMiddleware(mw RequestMiddleware) {
	c.RequestMiddlewares = append(c.RequestMiddlewares, mw)
}

// AddResponseMiddleware 添加响应中间件
func (c *MiddlewareChain) AddResponseMiddleware(mw ResponseMiddleware) {
	c.ResponseMiddlewares = append(c.ResponseMiddlewares, mw)
}

// ProcessRequest 处理请求链
func (c *MiddlewareChain) ProcessRequest(req *core.Request) *core.Request {
	for _, mw := range c.RequestMiddlewares {
		req = mw.ProcessRequest(req)
	}
	return req
}

// ProcessResponse 处理响应链
func (c *MiddlewareChain) ProcessResponse(resp *core.Response) *core.Response {
	for _, mw := range c.ResponseMiddlewares {
		resp = mw.ProcessResponse(resp)
	}
	return resp
}
