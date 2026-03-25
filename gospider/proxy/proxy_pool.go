// Gospider 代理池模块

//! 代理池管理
//! 
//! 实现代理的添加、轮换、检查等功能

package proxy

import (
	"fmt"
	"math/rand"
	"net/http"
	"net/url"
	"sync"
	"time"
)

// Proxy - 代理结构
type Proxy struct {
	Host         string
	Port         int
	Username     string
	Password     string
	Protocol     string // http, https, socks5
	LastChecked  time.Time
	IsValid      bool
	ResponseTime float64
	SuccessCount int
	FailCount    int
	CreatedAt    time.Time
	mu           sync.RWMutex
}

// NewProxy - 创建代理
func NewProxy(host string, port int, username, password, protocol string) *Proxy {
	if protocol == "" {
		protocol = "http"
	}

	return &Proxy{
		Host:      host,
		Port:      port,
		Username:  username,
		Password:  password,
		Protocol:  protocol,
		IsValid:   true,
		CreatedAt: time.Now(),
	}
}

// URL - 获取代理 URL
func (p *Proxy) URL() string {
	p.mu.RLock()
	defer p.mu.RUnlock()

	if p.Username != "" && p.Password != "" {
		return fmt.Sprintf("%s://%s:%s@%s:%d",
			p.Protocol, p.Username, p.Password, p.Host, p.Port)
	}
	return fmt.Sprintf("%s://%s:%d", p.Protocol, p.Host, p.Port)
}

// Fingerprint - 获取代理指纹
func (p *Proxy) Fingerprint() string {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return fmt.Sprintf("%s:%d", p.Host, p.Port)
}

// MarkSuccess - 标记成功
func (p *Proxy) MarkSuccess(responseTime float64) {
	p.mu.Lock()
	defer p.mu.Unlock()

	p.IsValid = true
	p.ResponseTime = responseTime
	p.SuccessCount++
	p.FailCount = 0
	p.LastChecked = time.Now()
}

// MarkFailure - 标记失败
func (p *Proxy) MarkFailure() {
	p.mu.Lock()
	defer p.mu.Unlock()

	p.FailCount++
	if p.FailCount >= 3 {
		p.IsValid = false
	}
	p.LastChecked = time.Now()
}

// ProxyPool - 代理池
type ProxyPool struct {
	proxies       map[string]*Proxy
	currentIndex  int
	checkInterval time.Duration
	mu            sync.RWMutex
}

// NewProxyPool - 创建代理池
func NewProxyPool(checkInterval time.Duration) *ProxyPool {
	if checkInterval <= 0 {
		checkInterval = 5 * time.Minute
	}

	return &ProxyPool{
		proxies:       make(map[string]*Proxy),
		currentIndex:  0,
		checkInterval: checkInterval,
	}
}

// AddProxy - 添加代理
func (pp *ProxyPool) AddProxy(proxy *Proxy) {
	pp.mu.Lock()
	defer pp.mu.Unlock()

	pp.proxies[proxy.Fingerprint()] = proxy
}

// AddProxies - 批量添加代理
func (pp *ProxyPool) AddProxies(proxies []*Proxy) {
	for _, proxy := range proxies {
		pp.AddProxy(proxy)
	}
}

// RemoveProxy - 移除代理
func (pp *ProxyPool) RemoveProxy(fingerprint string) {
	pp.mu.Lock()
	defer pp.mu.Unlock()

	delete(pp.proxies, fingerprint)
}

// GetProxy - 获取代理（轮换）
func (pp *ProxyPool) GetProxy() *Proxy {
	pp.mu.RLock()
	defer pp.mu.RUnlock()

	validProxies := pp.getValidProxies()
	if len(validProxies) == 0 {
		return nil
	}

	// 轮询选择
	proxy := validProxies[pp.currentIndex%len(validProxies)]
	pp.currentIndex++

	return proxy
}

// GetBestProxy - 获取最佳代理（响应时间最短）
func (pp *ProxyPool) GetBestProxy() *Proxy {
	pp.mu.RLock()
	defer pp.mu.RUnlock()

	validProxies := pp.getValidProxies()
	if len(validProxies) == 0 {
		return nil
	}

	var best *Proxy
	minTime := float64(999999)

	for _, proxy := range validProxies {
		proxy.mu.RLock()
		rt := proxy.ResponseTime
		proxy.mu.RUnlock()

		if rt > 0 && rt < minTime {
			minTime = rt
			best = proxy
		}
	}

	if best == nil {
		return validProxies[0]
	}
	return best
}

// GetRandomProxy - 随机获取代理
func (pp *ProxyPool) GetRandomProxy() *Proxy {
	pp.mu.RLock()
	defer pp.mu.RUnlock()

	validProxies := pp.getValidProxies()
	if len(validProxies) == 0 {
		return nil
	}

	return validProxies[rand.Intn(len(validProxies))]
}

// getValidProxies - 获取有效代理列表
func (pp *ProxyPool) getValidProxies() []*Proxy {
	pp.mu.RLock()
	defer pp.mu.RUnlock()

	result := make([]*Proxy, 0)
	for _, proxy := range pp.proxies {
		proxy.mu.RLock()
		if proxy.IsValid {
			result = append(result, proxy)
		}
		proxy.mu.RUnlock()
	}

	return result
}

// CheckProxy - 检查代理
func (pp *ProxyPool) CheckProxy(proxy *Proxy, testURL string, timeout time.Duration) bool {
	if testURL == "" {
		testURL = "https://www.google.com"
	}
	if timeout <= 0 {
		timeout = 10 * time.Second
	}

	proxyURL, err := url.Parse(proxy.URL())
	if err != nil {
		proxy.MarkFailure()
		return false
	}

	transport := &http.Transport{
		Proxy: http.ProxyURL(proxyURL),
	}

	client := &http.Client{
		Transport: transport,
		Timeout:   timeout,
	}

	start := time.Now()
	resp, err := client.Get(testURL)
	elapsed := time.Since(start).Seconds()

	if err != nil {
		proxy.MarkFailure()
		return false
	}
	defer resp.Body.Close()

	if resp.StatusCode == 200 {
		proxy.MarkSuccess(elapsed)
		return true
	}

	proxy.MarkFailure()
	return false
}

// CheckAllProxies - 检查所有代理
func (pp *ProxyPool) CheckAllProxies(testURL string) map[string]bool {
	results := make(map[string]bool)

	for _, proxy := range pp.proxies {
		results[proxy.Fingerprint()] = pp.CheckProxy(proxy, testURL, 0)
	}

	return results
}

// AutoCheck - 自动检查过期代理
func (pp *ProxyPool) AutoCheck(testURL string) {
	pp.mu.RLock()
	proxies := make([]*Proxy, 0, len(pp.proxies))
	for _, proxy := range pp.proxies {
		proxies = append(proxies, proxy)
	}
	pp.mu.RUnlock()

	now := time.Now()
	for _, proxy := range proxies {
		proxy.mu.RLock()
		shouldCheck := proxy.LastChecked.IsZero() ||
			now.Sub(proxy.LastChecked) > pp.checkInterval
		proxy.mu.RUnlock()

		if shouldCheck {
			go pp.CheckProxy(proxy, testURL, 0)
		}
	}
}

// GetStats - 获取统计信息
func (pp *ProxyPool) GetStats() map[string]interface{} {
	pp.mu.RLock()
	defer pp.mu.RUnlock()

	total := len(pp.proxies)
	valid := 0
	invalid := 0
	totalResponseTime := 0.0

	for _, proxy := range pp.proxies {
		proxy.mu.RLock()
		if proxy.IsValid {
			valid++
			if proxy.ResponseTime > 0 {
				totalResponseTime += proxy.ResponseTime
			}
		} else {
			invalid++
		}
		proxy.mu.RUnlock()
	}

	avgResponseTime := 0.0
	if valid > 0 {
		avgResponseTime = totalResponseTime / float64(valid)
	}

	return map[string]interface{}{
		"total":           total,
		"valid":           valid,
		"invalid":         invalid,
		"validity_rate":   float64(valid) / float64(total),
		"avg_response_time": avgResponseTime,
	}
}

// Clear - 清空代理池
func (pp *ProxyPool) Clear() {
	pp.mu.Lock()
	defer pp.mu.Unlock()

	pp.proxies = make(map[string]*Proxy)
	pp.currentIndex = 0
}

// Size - 代理池大小
func (pp *ProxyPool) Size() int {
	pp.mu.RLock()
	defer pp.mu.RUnlock()
	return len(pp.proxies)
}

// ValidSize - 有效代理数量
func (pp *ProxyPool) ValidSize() int {
	pp.mu.RLock()
	defer pp.mu.RUnlock()

	count := 0
	for _, proxy := range pp.proxies {
		proxy.mu.RLock()
		if proxy.IsValid {
			count++
		}
		proxy.mu.RUnlock()
	}
	return count
}

// ParseProxyString - 解析代理字符串
// 格式：host:port 或 username:password@host:port
func ParseProxyString(proxyStr string) (*Proxy, error) {
	var host, port, username, password, protocol string

	if idx := indexOf(proxyStr, "@"); idx != -1 {
		// 有认证信息
		auth := proxyStr[:idx]
		hostPort := proxyStr[idx+1:]

		if idx2 := indexOf(auth, ":"); idx2 != -1 {
			username = auth[:idx2]
			password = auth[idx2+1:]
		}

		if idx3 := indexOf(hostPort, ":"); idx3 != -1 {
			host = hostPort[:idx3]
			port = hostPort[idx3+1:]
		}
	} else {
		// 无认证信息
		if idx := indexOf(proxyStr, ":"); idx != -1 {
			host = proxyStr[:idx]
			port = proxyStr[idx+1:]
		}
	}

	if host == "" || port == "" {
		return nil, fmt.Errorf("invalid proxy format: %s", proxyStr)
	}

	var portNum int
	fmt.Sscanf(port, "%d", &portNum)

	return NewProxy(host, portNum, username, password, protocol), nil
}

// CreateProxyPool - 从代理列表创建代理池
func CreateProxyPool(proxyStrings []string, checkInterval time.Duration) (*ProxyPool, error) {
	pool := NewProxyPool(checkInterval)

	for _, proxyStr := range proxyStrings {
		proxy, err := ParseProxyString(proxyStr)
		if err != nil {
			return nil, err
		}
		pool.AddProxy(proxy)
	}

	return pool, nil
}

// indexOf - 查找子字符串位置
func indexOf(s, substr string) int {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return i
		}
	}
	return -1
}
