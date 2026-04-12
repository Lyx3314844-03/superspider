package core

import (
	"crypto/tls"
	"encoding/json"
	"fmt"
	"math/rand"
	"net/http"
	"net/url"
	"sync"
	"time"
)

// HumanBehaviorSimulator - 人类行为模拟器
type HumanBehaviorSimulator struct {
	mu sync.Mutex
}

// NewHumanBehaviorSimulator - 创建人类行为模拟器
func NewHumanBehaviorSimulator() *HumanBehaviorSimulator {
	return &HumanBehaviorSimulator{}
}

// MouseMovement - 鼠标移动事件
type MouseMovement struct {
	X         int   `json:"x"`
	Y         int   `json:"y"`
	Timestamp int64 `json:"timestamp"`
	Type      string `json:"type"`
}

// ScrollEvent - 滚动事件
type ScrollEvent struct {
	Position  int   `json:"position"`
	Timestamp int64 `json:"timestamp"`
	Type      string `json:"type"`
}

// SimulateMouseMovement - 模拟鼠标移动
func (h *HumanBehaviorSimulator) SimulateMouseMovement(duration time.Duration) []MouseMovement {
	h.mu.Lock()
	defer h.mu.Unlock()

	var movements []MouseMovement
	startTime := time.Now()
	x, y := rand.Intn(700)+100, rand.Intn(500)+100

	for time.Since(startTime) < duration {
		dx := rand.NormFloat64() * 50
		dy := rand.NormFloat64() * 50
		x = max(0, min(1920, x+int(dx)))
		y = max(0, min(1080, y+int(dy)))

		movements = append(movements, MouseMovement{
			X:         x,
			Y:         y,
			Timestamp: time.Now().UnixMilli(),
			Type:      "mousemove",
		})

		time.Sleep(time.Duration(50+rand.Intn(150)) * time.Millisecond)
	}

	return movements
}

// SimulateScrolling - 模拟滚动
func (h *HumanBehaviorSimulator) SimulateScrolling(maxHeight int) []ScrollEvent {
	h.mu.Lock()
	defer h.mu.Unlock()

	var scrolls []ScrollEvent
	currentPos := 0
	maxScroll := min(maxHeight, rand.Intn(6000)+2000)

	for currentPos < maxScroll {
		step := rand.Intn(400) + 100
		currentPos = min(currentPos+step, maxScroll)

		scrolls = append(scrolls, ScrollEvent{
			Position:  currentPos,
			Timestamp: time.Now().UnixMilli(),
			Type:      "scroll",
		})

		if rand.Float64() < 0.3 {
			time.Sleep(time.Duration(500+rand.Intn(1500)) * time.Millisecond)
		}

		time.Sleep(time.Duration(100+rand.Intn(400)) * time.Millisecond)
	}

	return scrolls
}

// GenerateBehaviorHeaders - 生成行为模拟请求头
func (h *HumanBehaviorSimulator) GenerateBehaviorHeaders() map[string]string {
	return map[string]string{
		"Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
		"Accept-Language":           "zh-CN,zh;q=0.9,en;q=0.8",
		"Accept-Encoding":           "gzip, deflate, br",
		"Connection":                "keep-alive",
		"Upgrade-Insecure-Requests": "1",
		"Sec-Fetch-Dest":            "document",
		"Sec-Fetch-Mode":            "navigate",
		"Sec-Fetch-Site":            "none",
		"Sec-Fetch-User":            "?1",
		"DNT":                       "1",
		"Cache-Control":             "max-age=0",
	}
}

// CertificateManager - 证书管理器
type CertificateManager struct {
	certificates map[string]*tls.Certificate
	mu           sync.RWMutex
}

// NewCertificateManager - 创建证书管理器
func NewCertificateManager() *CertificateManager {
	return &CertificateManager{
		certificates: make(map[string]*tls.Certificate),
	}
}

// LoadCertificate - 加载 PEM 格式证书
func (cm *CertificateManager) LoadCertificate(name, certPath, keyPath string) error {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	cert, err := tls.LoadX509KeyPair(certPath, keyPath)
	if err != nil {
		return fmt.Errorf("加载证书失败: %w", err)
	}

	cm.certificates[name] = &cert
	return nil
}

// LoadPFXCertificate - 加载 PFX/PKCS#12 格式证书
func (cm *CertificateManager) LoadPFXCertificate(name, pfxPath, password string) error {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	// 简化实现：直接尝试作为 PEM 加载
	// 实际应使用 golang.org/x/crypto/pkcs12
	cert, err := tls.LoadX509KeyPair(pfxPath, pfxPath)
	if err != nil {
		return fmt.Errorf("解析证书失败: %w", err)
	}

	cm.certificates[name] = &cert
	return nil
}

// GetTLSConfig - 获取带有证书的 TLS 配置
func (cm *CertificateManager) GetTLSConfig(name string) (*tls.Config, error) {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	cert, exists := cm.certificates[name]
	if !exists {
		return nil, fmt.Errorf("证书 %s 未找到", name)
	}

	return &tls.Config{
		Certificates: []tls.Certificate{*cert},
	}, nil
}

// GetHTTPClient - 获取带有证书的 HTTP 客户端
func (cm *CertificateManager) GetHTTPClient(name string) (*http.Client, error) {
	tlsConfig, err := cm.GetTLSConfig(name)
	if err != nil {
		return nil, err
	}

	transport := &http.Transport{
		TLSClientConfig: tlsConfig,
	}

	return &http.Client{
		Transport: transport,
		Timeout:   30 * time.Second,
	}, nil
}

// APIKeyManager - API Key 管理器
type APIKeyManager struct {
	apiKeys    map[string][]APIKeyInfo
	usageStats map[string]*KeyUsageStats
	mu         sync.RWMutex
}

// APIKeyInfo - API Key 信息
type APIKeyInfo struct {
	Key       string            `json:"key"`
	Metadata  map[string]string `json:"metadata"`
	AddedAt   time.Time         `json:"added_at"`
	Active    bool              `json:"active"`
}

// KeyUsageStats - Key 使用统计
type KeyUsageStats struct {
	Total  int `json:"total"`
	Failed int `json:"failed"`
}

// NewAPIKeyManager - 创建 API Key 管理器
func NewAPIKeyManager() *APIKeyManager {
	return &APIKeyManager{
		apiKeys:    make(map[string][]APIKeyInfo),
		usageStats: make(map[string]*KeyUsageStats),
	}
}

// AddKey - 添加 API Key
func (akm *APIKeyManager) AddKey(service, key string, metadata map[string]string) {
	akm.mu.Lock()
	defer akm.mu.Unlock()

	if _, exists := akm.usageStats[service]; !exists {
		akm.usageStats[service] = &KeyUsageStats{}
	}

	akm.apiKeys[service] = append(akm.apiKeys[service], APIKeyInfo{
		Key:      key,
		Metadata: metadata,
		AddedAt:  time.Now(),
		Active:   true,
	})
}

// GetKey - 获取可用的 API Key（轮询）
func (akm *APIKeyManager) GetKey(service string) (string, bool) {
	akm.mu.Lock()
	defer akm.mu.Unlock()

	keys, exists := akm.apiKeys[service]
	if !exists {
		return "", false
	}

	var activeKeys []APIKeyInfo
	for _, k := range keys {
		if k.Active {
			activeKeys = append(activeKeys, k)
		}
	}

	if len(activeKeys) == 0 {
		return "", false
	}

	// 轮询
	stats := akm.usageStats[service]
	keyInfo := activeKeys[stats.Total%len(activeKeys)]
	stats.Total++

	return keyInfo.Key, true
}

// MarkKeyFailed - 标记 Key 失败
func (akm *APIKeyManager) MarkKeyFailed(service, key string) {
	akm.mu.Lock()
	defer akm.mu.Unlock()

	if keys, exists := akm.apiKeys[service]; exists {
		for i := range keys {
			if keys[i].Key == key {
				keys[i].Active = false
				akm.usageStats[service].Failed++
				break
			}
		}
	}
}

// ProxyConfig - 代理配置
type ProxyConfig struct {
	TargetIP    string    `json:"target_ip"`
	ProxyURL    string    `json:"proxy_url"`
	ConfiguredAt time.Time `json:"configured_at"`
}

// WhitelistIPManager - IP 白名单管理器
type WhitelistIPManager struct {
	whitelistedIPs map[string]bool
	proxyConfigs   map[string]*ProxyConfig
	mu             sync.RWMutex
}

// NewWhitelistIPManager - 创建 IP 白名单管理器
func NewWhitelistIPManager() *WhitelistIPManager {
	return &WhitelistIPManager{
		whitelistedIPs: make(map[string]bool),
		proxyConfigs:   make(map[string]*ProxyConfig),
	}
}

// AddWhitelistedIP - 添加白名单 IP
func (wim *WhitelistIPManager) AddWhitelistedIP(ip string) {
	wim.mu.Lock()
	defer wim.mu.Unlock()
	wim.whitelistedIPs[ip] = true
}

// ConfigureProxyForIP - 为特定 IP 配置代理
func (wim *WhitelistIPManager) ConfigureProxyForIP(targetIP, proxyURL string) {
	wim.mu.Lock()
	defer wim.mu.Unlock()

	wim.proxyConfigs[targetIP] = &ProxyConfig{
		TargetIP:    targetIP,
		ProxyURL:    proxyURL,
		ConfiguredAt: time.Now(),
	}
}

// GetHTTPClientForTarget - 获取针对目标 IP 的 HTTP 客户端
func (wim *WhitelistIPManager) GetHTTPClientForTarget(targetIP string) (*http.Client, error) {
	wim.mu.RLock()
	defer wim.mu.RUnlock()

	transport := &http.Transport{
		TLSClientConfig: &tls.Config{InsecureSkipVerify: false},
	}

	if config, exists := wim.proxyConfigs[targetIP]; exists {
		proxyURL, err := url.Parse(config.ProxyURL)
		if err != nil {
			return nil, fmt.Errorf("解析代理 URL 失败: %w", err)
		}
		transport.Proxy = http.ProxyURL(proxyURL)
	}

	return &http.Client{
		Transport: transport,
		Timeout:   30 * time.Second,
	}, nil
}

// AdvancedCrawler - 高级爬虫
type AdvancedCrawler struct {
	BehaviorSimulator *HumanBehaviorSimulator
	CertManager       *CertificateManager
	APIKeyManager     *APIKeyManager
	IPManager         *WhitelistIPManager
}

// NewAdvancedCrawler - 创建高级爬虫
func NewAdvancedCrawler() *AdvancedCrawler {
	return &AdvancedCrawler{
		BehaviorSimulator: NewHumanBehaviorSimulator(),
		CertManager:       NewCertificateManager(),
		APIKeyManager:     NewAPIKeyManager(),
		IPManager:         NewWhitelistIPManager(),
	}
}

// CreateAdvancedSession - 创建高级 Session
func (ac *AdvancedCrawler) CreateAdvancedSession(certName, proxyURL, apiKeyService string) (*http.Client, error) {
	var client *http.Client
	var err error

	// 配置证书
	if certName != "" {
		client, err = ac.CertManager.GetHTTPClient(certName)
		if err != nil {
			return nil, fmt.Errorf("获取证书客户端失败: %w", err)
		}
	} else {
		client = &http.Client{Timeout: 30 * time.Second}
	}

	// 配置代理
	if proxyURL != "" {
		transport, ok := client.Transport.(*http.Transport)
		if !ok {
			transport = &http.Transport{}
			client.Transport = transport
		}

		parsedURL, err := url.Parse(proxyURL)
		if err != nil {
			return nil, fmt.Errorf("解析代理 URL 失败: %w", err)
		}
		transport.Proxy = http.ProxyURL(parsedURL)
	}

	return client, nil
}

// CrawlWithBehavior - 使用行为模拟爬取
func (ac *AdvancedCrawler) CrawlWithBehavior(targetURL string, client *http.Client) (string, error) {
	if client == nil {
		var err error
		client, err = ac.CreateAdvancedSession("", "", "")
		if err != nil {
			return "", err
		}
	}

	// 生成行为模拟
	movements := ac.BehaviorSimulator.SimulateMouseMovement(2 * time.Second)
	scrolls := ac.BehaviorSimulator.SimulateScrolling(3000)

	// 创建请求
	req, err := http.NewRequest("GET", targetURL, nil)
	if err != nil {
		return "", fmt.Errorf("创建请求失败: %w", err)
	}

	// 添加行为头
	for k, v := range ac.BehaviorSimulator.GenerateBehaviorHeaders() {
		req.Header.Set(k, v)
	}

	// 添加行为指纹
	behaviorData := map[string]interface{}{
		"mouse_movements_count": len(movements),
		"scrolls_count":        len(scrolls),
	}
	behaviorJSON, _ := json.Marshal(behaviorData)
	req.Header.Set("X-Behavior-Fingerprint", string(behaviorJSON))

	// 执行请求
	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("请求失败: %w", err)
	}
	defer resp.Body.Close()

	// 读取响应
	buf := make([]byte, 1024*1024) // 1MB 缓冲区
	n, _ := resp.Body.Read(buf)
	return string(buf[:n]), nil
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
