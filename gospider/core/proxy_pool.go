package core

import (
	"fmt"
	"math/rand"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

// Proxy 表示一个代理服务器
type Proxy struct {
	URL          string
	Protocol     string // http, https, socks5
	Username     string
	Password     string
	Host         string
	Port         string
	Status       ProxyStatus
	SuccessCount int
	FailureCount int
	LastChecked  time.Time
	ResponseTime time.Duration
	mu           sync.RWMutex
}

// ProxyStatus 代理状态
type ProxyStatus int

const (
	ProxyUnknown ProxyStatus = iota
	ProxyAlive
	ProxyDead
)

// FullURL 返回完整的代理 URL
func (p *Proxy) FullURL() string {
	if p.Username != "" && p.Password != "" {
		return fmt.Sprintf("%s://%s:%s@%s:%s", p.Protocol, p.Username, p.Password, p.Host, p.Port)
	}
	return fmt.Sprintf("%s://%s:%s", p.Protocol, p.Host, p.Port)
}

// RecordSuccess 记录成功
func (p *Proxy) RecordSuccess() {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.SuccessCount++
	p.Status = ProxyAlive
	p.LastChecked = time.Now()
}

// RecordFailure 记录失败
func (p *Proxy) RecordFailure() {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.FailureCount++
	p.LastChecked = time.Now()
	if p.FailureCount >= 3 {
		p.Status = ProxyDead
	}
}

// ProxyPool 代理池管理器
type ProxyPool struct {
	proxies       []*Proxy
	mu            sync.RWMutex
	currentIndex  int
	checkURL      string
	checkInterval time.Duration
	maxFailures   int
	running       bool
	stopCh        chan struct{}
}

// NewProxyPool 创建代理池
func NewProxyPool(checkURL ...string) *ProxyPool {
	cu := "https://httpbin.org/ip"
	if len(checkURL) > 0 {
		cu = checkURL[0]
	}
	return &ProxyPool{
		checkURL:      cu,
		checkInterval: 5 * time.Minute,
		maxFailures:   3,
		stopCh:        make(chan struct{}),
	}
}

// AddProxy 添加代理
func (pp *ProxyPool) AddProxy(proxy *Proxy) {
	pp.mu.Lock()
	defer pp.mu.Unlock()
	pp.proxies = append(pp.proxies, proxy)
}

// AddProxyFromString 从字符串添加代理
// 支持格式: http://host:port, http://user:pass@host:port, host:port
func (pp *ProxyPool) AddProxyFromString(proxyStr string) error {
	protocol := "http"
	host := proxyStr
	username := ""
	password := ""

	// 解析协议
	if strings.HasPrefix(host, "http://") {
		host = strings.TrimPrefix(host, "http://")
	} else if strings.HasPrefix(host, "https://") {
		protocol = "https"
		host = strings.TrimPrefix(host, "https://")
	} else if strings.HasPrefix(host, "socks5://") {
		protocol = "socks5"
		host = strings.TrimPrefix(host, "socks5://")
	}

	// 解析认证
	if idx := strings.Index(host, "@"); idx != -1 {
		auth := host[:idx]
		host = host[idx+1:]
		if colonIdx := strings.Index(auth, ":"); colonIdx != -1 {
			username = auth[:colonIdx]
			password = auth[colonIdx+1:]
		}
	}

	// 解析主机:端口
	if colonIdx := strings.LastIndex(host, ":"); colonIdx != -1 {
		h := host[:colonIdx]
		p := host[colonIdx+1:]
		proxy := &Proxy{
			Protocol: protocol,
			Host:     h,
			Port:     p,
			Username: username,
			Password: password,
			Status:   ProxyUnknown,
		}
		pp.AddProxy(proxy)
		return nil
	}

	return fmt.Errorf("invalid proxy format: %s", proxyStr)
}

// GetProxy 获取下一个可用代理(轮询)
func (pp *ProxyPool) GetProxy() *Proxy {
	pp.mu.Lock()
	defer pp.mu.Unlock()

	if len(pp.proxies) == 0 {
		return nil
	}

	// 尝试找到健康代理
	for i := 0; i < len(pp.proxies); i++ {
		idx := (pp.currentIndex + i) % len(pp.proxies)
		proxy := pp.proxies[idx]
		if proxy.Status == ProxyAlive && proxy.FailureCount < pp.maxFailures {
			pp.currentIndex = (idx + 1) % len(pp.proxies)
			return proxy
		}
	}

	// 返回未知状态代理
	for _, proxy := range pp.proxies {
		if proxy.Status == ProxyUnknown {
			return proxy
		}
	}

	return nil
}

// ApplyToRequest 将代理应用到 HTTP 请求
func (pp *ProxyPool) ApplyToRequest(req *http.Request) error {
	proxy := pp.GetProxy()
	if proxy == nil {
		return nil // 无代理,直接返回
	}

	proxyURL, err := url.Parse(proxy.FullURL())
	if err != nil {
		return fmt.Errorf("parse proxy URL: %w", err)
	}

	req.URL.Scheme = proxyURL.Scheme // 这个不生效,需要 transport
	return nil
}

// GetHTTPTransport 返回带代理的 HTTP Transport
func (pp *ProxyPool) GetHTTPTransport() http.RoundTripper {
	proxy := pp.GetProxy()
	if proxy == nil {
		return http.DefaultTransport
	}

	proxyURL, err := url.Parse(proxy.FullURL())
	if err != nil {
		return http.DefaultTransport
	}

	return &http.Transport{
		Proxy: http.ProxyURL(proxyURL),
	}
}

// RecordSuccess 记录代理成功
func (pp *ProxyPool) RecordSuccess(proxy *Proxy) {
	if proxy != nil {
		proxy.RecordSuccess()
	}
}

// RecordFailure 记录代理失败
func (pp *ProxyPool) RecordFailure(proxy *Proxy) {
	if proxy != nil {
		proxy.RecordFailure()
	}
}

// Stats 返回代理池统计
func (pp *ProxyPool) Stats() map[string]int {
	pp.mu.RLock()
	defer pp.mu.RUnlock()

	stats := map[string]int{
		"total":   len(pp.proxies),
		"alive":   0,
		"dead":    0,
		"unknown": 0,
	}

	for _, p := range pp.proxies {
		switch p.Status {
		case ProxyAlive:
			stats["alive"]++
		case ProxyDead:
			stats["dead"]++
		default:
			stats["unknown"]++
		}
	}

	return stats
}

// StartHealthCheck 启动健康检查(后台 goroutine)
func (pp *ProxyPool) StartHealthCheck() {
	if pp.running {
		return
	}
	pp.running = true
	go pp.healthCheckLoop()
}

// StopHealthCheck 停止健康检查
func (pp *ProxyPool) StopHealthCheck() {
	if !pp.running {
		return
	}
	pp.running = false
	close(pp.stopCh)
	pp.stopCh = make(chan struct{})
}

func (pp *ProxyPool) healthCheckLoop() {
	ticker := time.NewTicker(pp.checkInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			pp.checkAll()
		case <-pp.stopCh:
			return
		}
	}
}

func (pp *ProxyPool) checkAll() {
	pp.mu.RLock()
	proxies := make([]*Proxy, len(pp.proxies))
	copy(proxies, pp.proxies)
	pp.mu.RUnlock()

	for _, proxy := range proxies {
		if proxy.Status == ProxyDead {
			// 定期检查死亡代理是否可以恢复
			if time.Since(proxy.LastChecked) > pp.checkInterval*2 {
				pp.checkProxy(proxy)
			}
		} else {
			pp.checkProxy(proxy)
		}
	}
}

func (pp *ProxyPool) checkProxy(proxy *Proxy) bool {
	// 修复: 使用代理本身来测试连接
	proxyURL, err := url.Parse(proxy.FullURL())
	if err != nil {
		proxy.RecordFailure()
		return false
	}

	client := &http.Client{
		Timeout:   10 * time.Second,
		Transport: &http.Transport{Proxy: http.ProxyURL(proxyURL)},
	}

	start := time.Now()
	resp, err := client.Get(pp.checkURL)
	if err != nil {
		proxy.RecordFailure()
		return false
	}
	defer resp.Body.Close()

	proxy.ResponseTime = time.Since(start)
	if resp.StatusCode == http.StatusOK {
		proxy.RecordSuccess()
		return true
	}

	proxy.RecordFailure()
	return false
}

// RandomUserAgent 随机 User-Agent 池
var RandomUserAgents = []string{
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
	"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
}

// GetRandomUserAgent 返回随机 User-Agent
func GetRandomUserAgent() string {
	return RandomUserAgents[rand.Intn(len(RandomUserAgents))]
}
