package proxy

import (
	"crypto/rand"
	"encoding/json"
	"os"
	"fmt"
	"math/big"
	"net/http"
	"net/url"
	"sync"
	"time"
)

// Proxy represents a proxy server
type Proxy struct {
	URL          string    `json:"url"`
	Username     string    `json:"username,omitempty"`
	Password     string    `json:"password,omitempty"`
	Protocol     string    `json:"protocol"`  // http, https, socks5
	Country      string    `json:"country"`
	Latency      int       `json:"latency"`   // ms
	SuccessRate  float64   `json:"success_rate"`
	LastChecked  time.Time `json:"last_checked"`
	IsWorking    bool      `json:"is_working"`
	UseCount     int       `json:"use_count"`
}

// ProxyPool manages a pool of proxies
type ProxyPool struct {
	mu       sync.RWMutex
	proxies  []*Proxy
	config   *Config
	metrics  *Metrics
}

// Config for proxy pool
type Config struct {
	MinSize         int           `json:"min_size"`
	MaxSize         int           `json:"max_size"`
	ValidationURL   string        `json:"validation_url"`
	MinSuccessRate  float64       `json:"min_success_rate"`
	CheckInterval   time.Duration `json:"check_interval"`
	Timeout         time.Duration `json:"timeout"`
	RotateOnFailure bool          `json:"rotate_on_failure"`
}

// Metrics tracks proxy pool metrics
type Metrics struct {
	mu                sync.RWMutex
	TotalRequests     int64 `json:"total_requests"`
	SuccessfulRequests int64 `json:"successful_requests"`
	FailedRequests    int64 `json:"failed_requests"`
	ProxiesRemoved    int64 `json:"proxies_removed"`
	ProxiesAdded      int64 `json:"proxies_added"`
}

// NewProxyPool creates a new proxy pool
func NewProxyPool(config *Config) *ProxyPool {
	if config == nil {
		config = &Config{
			MinSize:         10,
			MaxSize:         100,
			ValidationURL:   "https://www.baidu.com",
			MinSuccessRate:  0.8,
			CheckInterval:   5 * time.Minute,
			Timeout:         10 * time.Second,
			RotateOnFailure: true,
		}
	}
	
	return &ProxyPool{
		proxies: make([]*Proxy, 0),
		config:  config,
		metrics: &Metrics{},
	}
}

// AddProxy adds a proxy to the pool
func (p *ProxyPool) AddProxy(proxy *Proxy) error {
	p.mu.Lock()
	defer p.mu.Unlock()
	
	if len(p.proxies) >= p.config.MaxSize {
		return fmt.Errorf("proxy pool is full")
	}
	
	proxy.IsWorking = true
	proxy.LastChecked = time.Now()
	p.proxies = append(p.proxies, proxy)
	p.metrics.ProxiesAdded++
	
	return nil
}

// GetProxy returns a random working proxy
func (p *ProxyPool) GetProxy() *Proxy {
	p.mu.RLock()
	defer p.mu.RUnlock()
	
	if len(p.proxies) == 0 {
		return nil
	}
	
	// Filter working proxies
	var working []*Proxy
	for _, proxy := range p.proxies {
		if proxy.IsWorking {
			working = append(working, proxy)
		}
	}
	
	if len(working) == 0 {
		return nil
	}
	
	// Random selection with weighted by success rate
	n, _ := rand.Int(rand.Reader, big.NewInt(int64(len(working))))
	proxy := working[n.Int64()]
	proxy.UseCount++
	
	return proxy
}

// RemoveProxy removes a proxy from the pool
func (p *ProxyPool) RemoveProxy(url string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	
	for i, proxy := range p.proxies {
		if proxy.URL == url {
			p.proxies = append(p.proxies[:i], p.proxies[i+1:]...)
			p.metrics.ProxiesRemoved++
			return
		}
	}
}

// ValidateProxy checks if a proxy is working
func (p *ProxyPool) ValidateProxy(proxy *Proxy) bool {
	// 构建代理 URL
	var proxyURL *url.URL
	if proxy.Username != "" && proxy.Password != "" {
		proxyURL, _ = url.Parse(fmt.Sprintf("http://%s:%s@%s", proxy.Username, proxy.Password, proxy.URL))
	} else {
		proxyURL, _ = url.Parse("http://" + proxy.URL)
	}

	client := &http.Client{
		Timeout: p.config.Timeout,
		Transport: &http.Transport{
			Proxy: http.ProxyURL(proxyURL), // 修复: 使用代理本身
		},
	}

	start := time.Now()
	req, err := http.NewRequest("GET", p.config.ValidationURL, nil)
	if err != nil {
		return false
	}

	resp, err := client.Do(req)
	if err != nil {
		proxy.IsWorking = false
		proxy.LastChecked = time.Now()
		proxy.SuccessRate = 0
		return false
	}
	defer resp.Body.Close() // 修复: 在检查前 defer

	latency := int(time.Since(start).Milliseconds())

	if resp.StatusCode != 200 {
		proxy.IsWorking = false
		proxy.LastChecked = time.Now()
		proxy.SuccessRate = 0
		return false
	}

	proxy.Latency = latency
	proxy.LastChecked = time.Now()
	proxy.IsWorking = true
	proxy.SuccessRate = 1.0

	return true
}

// ValidateAll validates all proxies in the pool
func (p *ProxyPool) ValidateAll() {
	p.mu.RLock()
	proxies := make([]*Proxy, len(p.proxies))
	copy(proxies, p.proxies)
	p.mu.RUnlock()

	var wg sync.WaitGroup
	pool := p // 保存 pool 引用
	for _, proxy := range proxies {
		wg.Add(1)
		go func(proxy *Proxy) {
			defer wg.Done()
			if !pool.ValidateProxy(proxy) {
				proxy.IsWorking = false
				proxy.SuccessRate = 0
			}
		}(proxy)
	}
	wg.Wait()
	
	// Remove proxies with low success rate
	p.mu.Lock()
	var remaining []*Proxy
	for _, proxy := range p.proxies {
		if proxy.SuccessRate >= p.config.MinSuccessRate {
			remaining = append(remaining, proxy)
		}
	}
	p.proxies = remaining
	p.mu.Unlock()
}

// RecordSuccess records a successful request through a proxy
func (p *ProxyPool) RecordSuccess(proxyURL string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	
	p.metrics.TotalRequests++
	p.metrics.SuccessfulRequests++
	
	for _, proxy := range p.proxies {
		if proxy.URL == proxyURL {
			// Update success rate (exponential moving average)
			proxy.SuccessRate = 0.9*proxy.SuccessRate + 0.1*1.0
			break
		}
	}
}

// RecordFailure records a failed request through a proxy
func (p *ProxyPool) RecordFailure(proxyURL string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	
	p.metrics.TotalRequests++
	p.metrics.FailedRequests++
	
	for _, proxy := range p.proxies {
		if proxy.URL == proxyURL {
			proxy.SuccessRate = 0.9*proxy.SuccessRate + 0.1*0.0
			if p.config.RotateOnFailure && proxy.SuccessRate < p.config.MinSuccessRate {
				proxy.IsWorking = false
			}
			break
		}
	}
}

// GetMetrics returns current pool metrics
func (p *ProxyPool) GetMetrics() map[string]interface{} {
	p.mu.RLock()
	defer p.mu.RUnlock()
	
	working := 0
	for _, proxy := range p.proxies {
		if proxy.IsWorking {
			working++
		}
	}
	
	return map[string]interface{}{
		"total_proxies":    len(p.proxies),
		"working_proxies":  working,
		"total_requests":   p.metrics.TotalRequests,
		"success_rate":     float64(p.metrics.SuccessfulRequests) / float64(maxInt64(1, p.metrics.TotalRequests)),
		"proxies_added":    p.metrics.ProxiesAdded,
		"proxies_removed":  p.metrics.ProxiesRemoved,
	}
}

// StartAutoValidation starts automatic proxy validation
func (p *ProxyPool) StartAutoValidation() {
	ticker := time.NewTicker(p.config.CheckInterval)
	go func() {
		for range ticker.C {
			p.ValidateAll()
		}
	}()
}

// ImportFromFile imports proxies from a JSON file
func (p *ProxyPool) ImportFromFile(filepath string) error {
	data, err := os.ReadFile(filepath)
	if err != nil {
		return err
	}
	
	var proxies []Proxy
	if err := json.Unmarshal(data, &proxies); err != nil {
		return err
	}
	
	for _, proxy := range proxies {
		p.AddProxy(&proxy)
	}
	
	return nil
}

// ExportToFile exports proxies to a JSON file
func (p *ProxyPool) ExportToFile(filepath string) error {
	p.mu.RLock()
	defer p.mu.RUnlock()
	
	data, err := json.MarshalIndent(p.proxies, "", "  ")
	if err != nil {
		return err
	}
	
	return os.WriteFile(filepath, data, 0644)
}

func maxInt64(a, b int64) int64 {
	if a > b {
		return a
	}
	return b
}

func init() {
	fmt.Println("Proxy pool module loaded")
}
