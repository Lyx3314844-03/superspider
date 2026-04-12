package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"math/rand"
	"net/http"
	"net/url"
	"os"
	"sync"
	"time"
)

// UserAgentPool User-Agent 轮换池
type UserAgentPool struct {
	userAgents []string
	mu         sync.RWMutex
}

// 预设 User-Agent 列表
var defaultUserAgents = []string{
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
	"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
}

// NewUserAgentPool 创建 User-Agent 池
func NewUserAgentPool() *UserAgentPool {
	return &UserAgentPool{
		userAgents: defaultUserAgents,
	}
}

// GetRandom 获取随机 User-Agent
func (p *UserAgentPool) GetRandom() string {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.userAgents[rand.Intn(len(p.userAgents))]
}

// Add 添加 User-Agent
func (p *UserAgentPool) Add(ua string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.userAgents = append(p.userAgents, ua)
}

// Remove 移除 User-Agent
func (p *UserAgentPool) Remove(ua string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	for i, u := range p.userAgents {
		if u == ua {
			p.userAgents = append(p.userAgents[:i], p.userAgents[i+1:]...)
			return
		}
	}
}

// ProxyPool 代理池
type ProxyPool struct {
	proxies   []string
	mu        sync.RWMutex
	httpClient *http.Client
}

// NewProxyPool 创建代理池
func NewProxyPool() *ProxyPool {
	return &ProxyPool{
		proxies: make([]string, 0),
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// Add 添加代理
func (p *ProxyPool) Add(proxyURL string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.proxies = append(p.proxies, proxyURL)
}

// Remove 移除代理
func (p *ProxyPool) Remove(proxyURL string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	for i, proxy := range p.proxies {
		if proxy == proxyURL {
			p.proxies = append(p.proxies[:i], p.proxies[i+1:]...)
			return
		}
	}
}

// GetRandom 获取随机代理
func (p *ProxyPool) GetRandom() string {
	p.mu.RLock()
	defer p.mu.RUnlock()
	if len(p.proxies) == 0 {
		return ""
	}
	return p.proxies[rand.Intn(len(p.proxies))]
}

// Validate 验证代理是否可用
func (p *ProxyPool) Validate(proxyURL string) bool {
	if proxyURL == "" {
		return true
	}
	_, err := url.Parse(proxyURL)
	if err != nil {
		return false
	}
	
	// 测试代理连接
	client := &http.Client{
		Timeout: 5 * time.Second,
		Transport: &http.Transport{
			Proxy: func(*http.Request) (*url.URL, error) {
				return url.Parse(proxyURL)
			},
		},
	}
	
	_, err = client.Get("http://www.google.com")
	return err == nil
}

// TestAll 测试所有代理
func (p *ProxyPool) TestAll() map[string]bool {
	results := make(map[string]bool)
	p.mu.RLock()
	proxies := make([]string, len(p.proxies))
	copy(proxies, p.proxies)
	p.mu.RUnlock()
	
	var wg sync.WaitGroup
	var mu sync.Mutex
	
	for _, proxy := range proxies {
		wg.Add(1)
		go func(proxyURL string) {
			defer wg.Done()
			result := p.Validate(proxyURL)
			mu.Lock()
			results[proxyURL] = result
			mu.Unlock()
		}(proxy)
	}
	
	wg.Wait()
	return results
}

// LoadFromFile 从文件加载代理
func (p *ProxyPool) LoadFromFile(filename string) error {
	file, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer file.Close()
	
	p.mu.Lock()
	defer p.mu.Unlock()
	
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		proxy := scanner.Text()
		if proxy != "" && !contains(p.proxies, proxy) {
			p.proxies = append(p.proxies, proxy)
		}
	}
	return scanner.Err()
}

// SaveToFile 保存代理到文件
func (p *ProxyPool) SaveToFile(filename string) error {
	p.mu.RLock()
	proxies := make([]string, len(p.proxies))
	copy(proxies, p.proxies)
	p.mu.RUnlock()
	
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()
	
	writer := bufio.NewWriter(file)
	for _, proxy := range proxies {
		fmt.Fprintln(writer, proxy)
	}
	return writer.Flush()
}

// helpers
func contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}

// 导出为 JSON 格式
func (p *ProxyPool) ToJSON() (string, error) {
	p.mu.RLock()
	defer p.mu.RUnlock()
	data, err := json.Marshal(p.proxies)
	if err != nil {
		return "", err
	}
	return string(data), nil
}

// 从 JSON 导入
func (p *ProxyPool) FromJSON(jsonStr string) error {
	var proxies []string
	if err := json.Unmarshal([]byte(jsonStr), &proxies); err != nil {
		return err
	}
	
	p.mu.Lock()
	defer p.mu.Unlock()
	p.proxies = proxies
	return nil
}

// 请求模拟检测
type RequestSimulator struct {
	uaPool     *UserAgentPool
	proxyPool  *ProxyPool
}

// NewRequestSimulator 创建请求模拟器
func NewRequestSimulator() *RequestSimulator {
	return &RequestSimulator{
		uaPool:    NewUserAgentPool(),
		proxyPool: NewProxyPool(),
	}
}

// BuildRequest 构建模拟请求
func (rs *RequestSimulator) BuildRequest(targetURL string) (*http.Request, error) {
	req, err := http.NewRequest("GET", targetURL, nil)
	if err != nil {
		return nil, err
	}
	
	req.Header.Set("User-Agent", rs.uaPool.GetRandom())
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
	req.Header.Set("Accept-Encoding", "gzip, deflate")
	req.Header.Set("Connection", "keep-alive")
	
	return req, nil
}

// SetProxy 设置代理
func (rs *RequestSimulator) SetProxy(proxyURL string) {
	rs.proxyPool.Add(proxyURL)
}

// GetProxy 获取随机代理
func (rs *RequestSimulator) GetProxy() string {
	return rs.proxyPool.GetRandom()
}
