package antibot

import (
	"fmt"
	"math/rand"
	"net/http"
	"net/url"
	"sync"
	"time"
)

// UserAgentRotator - User-Agent 轮换器
type UserAgentRotator struct {
	chromeUAs   []string
	firefoxUAs  []string
	safariUAs   []string
	edgeUAs     []string
	mobileUAs   []string
	uaPool      []string
	usageCount  map[string]int
	mu          sync.RWMutex
}

// NewUserAgentRotator - 创建 User-Agent 轮换器
func NewUserAgentRotator() *UserAgentRotator {
	rotator := &UserAgentRotator{
		chromeUAs: []string{
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
			"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
		},
		firefoxUAs: []string{
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
			"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
		},
		safariUAs: []string{
			"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
		},
		edgeUAs: []string{
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
		},
		mobileUAs: []string{
			"Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
		},
		usageCount: make(map[string]int),
	}
	
	rotator.initializePool()
	return rotator
}

func (r *UserAgentRotator) initializePool() {
	r.uaPool = append(r.uaPool, r.chromeUAs...)
	r.uaPool = append(r.uaPool, r.firefoxUAs...)
	r.uaPool = append(r.uaPool, r.safariUAs...)
	r.uaPool = append(r.uaPool, r.edgeUAs...)
	r.uaPool = append(r.uaPool, r.mobileUAs...)
	
	for _, ua := range r.uaPool {
		r.usageCount[ua] = 0
	}
}

// GetRandomUserAgent - 获取随机 User-Agent
func (r *UserAgentRotator) GetRandomUserAgent() string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	
	index := rand.Intn(len(r.uaPool))
	ua := r.uaPool[index]
	r.usageCount[ua]++
	return ua
}

// GetBrowserUserAgent - 获取指定浏览器的 User-Agent
func (r *UserAgentRotator) GetBrowserUserAgent(browser string) string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	
	var pool []string
	switch browser {
	case "chrome":
		pool = r.chromeUAs
	case "firefox":
		pool = r.firefoxUAs
	case "safari":
		pool = r.safariUAs
	case "edge":
		pool = r.edgeUAs
	case "mobile":
		pool = r.mobileUAs
	default:
		pool = r.uaPool
	}
	
	index := rand.Intn(len(pool))
	ua := pool[index]
	r.usageCount[ua]++
	return ua
}

// ProxyInfo - 代理信息
type ProxyInfo struct {
	IP         string
	Port       int
	Protocol   string
	Username   string
	Password   string
	Country    string
	AddedTime  time.Time
	IsHealthy  bool
	LastCheck  time.Time
}

// ProxyPool - 代理池
type ProxyPool struct {
	proxies           []*ProxyInfo
	usageCount        map[string]int
	healthStatus      map[string]bool
	lastCheck         map[string]time.Time
	mu                sync.RWMutex
	healthCheckInterval time.Duration
	timeout           time.Duration
}

// NewProxyPool - 创建代理池
func NewProxyPool(healthCheckInterval, timeout time.Duration) *ProxyPool {
	pool := &ProxyPool{
		proxies:             make([]*ProxyInfo, 0),
		usageCount:          make(map[string]int),
		healthStatus:        make(map[string]bool),
		lastCheck:           make(map[string]time.Time),
		healthCheckInterval: healthCheckInterval,
		timeout:             timeout,
	}
	
	// 启动健康检查
	go pool.startHealthCheck()
	
	return pool
}

// AddProxy - 添加代理
func (p *ProxyPool) AddProxy(protocol, ip string, port int, username, password, country string) {
	proxy := &ProxyInfo{
		IP:        ip,
		Port:      port,
		Protocol:  protocol,
		Username:  username,
		Password:  password,
		Country:   country,
		AddedTime: time.Now(),
		IsHealthy: true,
	}
	
	p.mu.Lock()
	defer p.mu.Unlock()
	
	p.proxies = append(p.proxies, proxy)
	key := fmt.Sprintf("%s:%d", ip, port)
	p.usageCount[key] = 0
	p.healthStatus[key] = true
}

// GetRandomProxy - 获取随机代理
func (p *ProxyPool) GetRandomProxy() *ProxyInfo {
	p.mu.RLock()
	defer p.mu.RUnlock()
	
	healthyProxies := p.getHealthyProxies()
	if len(healthyProxies) == 0 {
		return nil
	}
	
	proxy := healthyProxies[rand.Intn(len(healthyProxies))]
	key := fmt.Sprintf("%s:%d", proxy.IP, proxy.Port)
	p.usageCount[key]++
	return proxy
}

// GetHealthyProxies - 获取健康代理
func (p *ProxyPool) getHealthyProxies() []*ProxyInfo {
	p.mu.RLock()
	defer p.mu.RUnlock()
	
	var healthy []*ProxyInfo
	for _, proxy := range p.proxies {
		if p.healthStatus[fmt.Sprintf("%s:%d", proxy.IP, proxy.Port)] {
			healthy = append(healthy, proxy)
		}
	}
	return healthy
}

// ToHTTPProxy - 转换为 HTTP 代理
func (p *ProxyInfo) ToHTTPProxy() (*url.URL, error) {
	proxyURL := fmt.Sprintf("%s://%s:%d", p.Protocol, p.IP, p.Port)
	return url.Parse(proxyURL)
}

// startHealthCheck - 启动健康检查
func (p *ProxyPool) startHealthCheck() {
	ticker := time.NewTicker(p.healthCheckInterval)
	defer ticker.Stop()
	
	for range ticker.C {
		p.healthCheckAll()
	}
}

// healthCheckAll - 健康检查所有代理
func (p *ProxyPool) healthCheckAll() {
	p.mu.Lock()
	defer p.mu.Unlock()
	
	healthyCount := 0
	unhealthyCount := 0
	
	for _, proxy := range p.proxies {
		isHealthy := p.checkProxyHealth(proxy)
		key := fmt.Sprintf("%s:%d", proxy.IP, proxy.Port)
		p.healthStatus[key] = isHealthy
		p.lastCheck[key] = time.Now()
		
		if isHealthy {
			healthyCount++
		} else {
			unhealthyCount++
		}
	}
}

// checkProxyHealth - 检查代理健康
func (p *ProxyPool) checkProxyHealth(proxy *ProxyInfo) bool {
	proxyURL, err := proxy.ToHTTPProxy()
	if err != nil {
		return false
	}
	
	client := &http.Client{
		Timeout: p.timeout,
		Transport: &http.Transport{
			Proxy: http.ProxyURL(proxyURL),
		},
	}
	
	resp, err := client.Get("https://www.google.com")
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	
	return resp.StatusCode == 200 || resp.StatusCode == 302
}

// RequestHeadersGenerator - 请求头生成器
type RequestHeadersGenerator struct {
	uaRotator *UserAgentRotator
	acceptHeaders []string
	acceptLanguages []string
}

// NewRequestHeadersGenerator - 创建请求头生成器
func NewRequestHeadersGenerator() *RequestHeadersGenerator {
	return &RequestHeadersGenerator{
		uaRotator: NewUserAgentRotator(),
		acceptHeaders: []string{
			"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
			"text/html,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
		},
		acceptLanguages: []string{
			"en-US,en;q=0.9",
			"zh-CN,zh;q=0.9,en;q=0.8",
		},
	}
}

// GenerateHeaders - 生成随机请求头
func (g *RequestHeadersGenerator) GenerateHeaders(browser string) map[string]string {
	return map[string]string{
		"User-Agent": g.uaRotator.GetBrowserUserAgent(browser),
		"Accept": g.acceptHeaders[rand.Intn(len(g.acceptHeaders))],
		"Accept-Language": g.acceptLanguages[rand.Intn(len(g.acceptLanguages))],
		"Accept-Encoding": "gzip, deflate, br",
		"Connection": "keep-alive",
		"Upgrade-Insecure-Requests": "1",
	}
}

// AntiBotManager - 反反爬管理器
type AntiBotManager struct {
	UARotator     *UserAgentRotator
	ProxyPool     *ProxyPool
	HeadersGen    *RequestHeadersGenerator
	MinDelay      time.Duration
	MaxDelay      time.Duration
	cookies       map[string]map[string]string
	mu            sync.RWMutex
}

// NewAntiBotManager - 创建反反爬管理器
func NewAntiBotManager() *AntiBotManager {
	return &AntiBotManager{
		UARotator:  NewUserAgentRotator(),
		ProxyPool:  NewProxyPool(5*time.Minute, 5*time.Second),
		HeadersGen: NewRequestHeadersGenerator(),
		MinDelay:   time.Second,
		MaxDelay:   3 * time.Second,
		cookies:    make(map[string]map[string]string),
	}
}

// GetRandomHeaders - 获取随机请求头
func (m *AntiBotManager) GetRandomHeaders(browser string) map[string]string {
	return m.HeadersGen.GenerateHeaders(browser)
}

// GetProxy - 获取代理
func (m *AntiBotManager) GetProxy() *ProxyInfo {
	return m.ProxyPool.GetRandomProxy()
}

// AddRandomDelay - 添加随机延迟
func (m *AntiBotManager) AddRandomDelay() {
	delay := m.MinDelay + time.Duration(rand.Int63n(int64(m.MaxDelay-m.MinDelay)))
	time.Sleep(delay)
}

// SetDelay - 设置延迟范围
func (m *AntiBotManager) SetDelay(min, max time.Duration) {
	m.MinDelay = min
	m.MaxDelay = max
}

// GetCookies - 获取 Cookie
func (m *AntiBotManager) GetCookies(domain string) map[string]string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	
	if cookies, ok := m.cookies[domain]; ok {
		return cookies
	}
	return nil
}

// SetCookies - 设置 Cookie
func (m *AntiBotManager) SetCookies(domain string, cookies map[string]string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	
	m.cookies[domain] = cookies
}

// GetStats - 获取统计信息
func (m *AntiBotManager) GetStats() map[string]interface{} {
	return map[string]interface{}{
		"ua_stats": map[string]interface{}{
			"total_uas": len(m.UARotator.uaPool),
		},
		"proxy_stats": map[string]interface{}{
			"total_proxies": len(m.ProxyPool.proxies),
		},
		"delay_range": map[string]time.Duration{
			"min": m.MinDelay,
			"max": m.MaxDelay,
		},
	}
}
