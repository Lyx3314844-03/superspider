// Gospider 会话管理模块

//! 会话池管理
//! 
//! 实现会话的创建、轮换、持久化等功能

package session

import (
	"crypto/rand"
	"encoding/hex"
	"net/http"
	"net/http/cookiejar"
	"sync"
	"time"
)

// Session - 会话结构
type Session struct {
	ID           string
	UserAgent    string
	Cookies      *cookiejar.Jar
	Headers      map[string]string
	ProxyURL     string
	CreatedAt    time.Time
	LastUsedAt   time.Time
	RequestCount int
	IsValid      bool
	mu           sync.RWMutex
}

// NewSession - 创建会话
func NewSession(userAgent string) (*Session, error) {
	cookies, err := cookiejar.New(nil)
	if err != nil {
		return nil, err
	}

	id, err := generateSessionID()
	if err != nil {
		return nil, err
	}

	now := time.Now()
	return &Session{
		ID:           id,
		UserAgent:    userAgent,
		Cookies:      cookies,
		Headers:      make(map[string]string),
		ProxyURL:     "",
		CreatedAt:    now,
		LastUsedAt:   now,
		RequestCount: 0,
		IsValid:      true,
	}, nil
}

// GetClient - 获取 HTTP 客户端
func (s *Session) GetClient() *http.Client {
	s.mu.RLock()
	defer s.mu.RUnlock()

	client := &http.Client{
		Jar:     s.Cookies,
		Timeout: 30 * time.Second,
	}

	// TODO: 添加代理支持
	// if s.ProxyURL != "" {
	// 	proxyURL, _ := url.Parse(s.ProxyURL)
	// 	client.Transport = &http.Transport{
	// 		Proxy: http.ProxyURL(proxyURL),
	// 	}
	// }

	return client
}

// AddCookie - 添加 Cookie
func (s *Session) AddCookie(name, value, domain string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	cookies := []*http.Cookie{
		{
			Name:   name,
			Value:  value,
			Domain: domain,
		},
	}

	s.Cookies.SetCookies(nil, cookies)
}

// AddHeader - 添加请求头
func (s *Session) AddHeader(key, value string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.Headers[key] = value
}

// MarkUsed - 标记已使用
func (s *Session) MarkUsed() {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.LastUsedAt = time.Now()
	s.RequestCount++
}

// GetAge - 获取会话年龄
func (s *Session) GetAge() time.Duration {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return time.Since(s.CreatedAt)
}

// GetIdleTime - 获取空闲时间
func (s *Session) GetIdleTime() time.Duration {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return time.Since(s.LastUsedAt)
}

// Reset - 重置会话
func (s *Session) Reset() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	cookies, err := cookiejar.New(nil)
	if err != nil {
		return err
	}

	s.Cookies = cookies
	s.Headers = make(map[string]string)
	s.RequestCount = 0
	s.LastUsedAt = time.Now()
	return nil
}

// Close - 关闭会话
func (s *Session) Close() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.IsValid = false
}

// SessionPool - 会话池
type SessionPool struct {
	sessions      map[string]*Session
	maxSessions   int
	maxAge        time.Duration
	maxIdleTime   time.Duration
	maxRequests   int
	userAgent     string
	currentIndex  int
	mu            sync.RWMutex
	autoRecycle   bool
	recycleTicker *time.Ticker
	stopChan      chan struct{}
}

// SessionPoolConfig - 会话池配置
type SessionPoolConfig struct {
	MaxSessions   int
	MaxAge        time.Duration
	MaxIdleTime   time.Duration
	MaxRequests   int
	UserAgent     string
	AutoRecycle   bool
	RecycleInterval time.Duration
}

// DefaultSessionPoolConfig - 默认配置
func DefaultSessionPoolConfig() *SessionPoolConfig {
	return &SessionPoolConfig{
		MaxSessions:     100,
		MaxAge:          30 * time.Minute,
		MaxIdleTime:     10 * time.Minute,
		MaxRequests:     1000,
		UserAgent:       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
		AutoRecycle:     true,
		RecycleInterval: 1 * time.Minute,
	}
}

// NewSessionPool - 创建会话池
func NewSessionPool(config *SessionPoolConfig) *SessionPool {
	if config == nil {
		config = DefaultSessionPoolConfig()
	}

	pool := &SessionPool{
		sessions:      make(map[string]*Session),
		maxSessions:   config.MaxSessions,
		maxAge:        config.MaxAge,
		maxIdleTime:   config.MaxIdleTime,
		maxRequests:   config.MaxRequests,
		userAgent:     config.UserAgent,
		currentIndex:  0,
		autoRecycle:   config.AutoRecycle,
		recycleTicker: nil,
		stopChan:      make(chan struct{}),
	}

	// 启动自动回收
	if pool.autoRecycle {
		pool.recycleTicker = time.NewTicker(config.RecycleInterval)
		go pool.autoRecycleLoop()
	}

	return pool
}

// GetSession - 获取会话
func (sp *SessionPool) GetSession() *Session {
	sp.mu.Lock()
	defer sp.mu.Unlock()

	// 获取有效会话
	validSessions := sp.getValidSessions()
	if len(validSessions) == 0 {
		// 创建新会话
		if len(sp.sessions) < sp.maxSessions {
			session, err := NewSession(sp.userAgent)
			if err != nil {
				return nil
			}
			sp.sessions[session.ID] = session
			return session
		}
		return nil
	}

	// 轮询选择
	session := validSessions[sp.currentIndex%len(validSessions)]
	sp.currentIndex++
	session.MarkUsed()

	return session
}

// CreateSession - 创建新会话
func (sp *SessionPool) CreateSession() (*Session, error) {
	sp.mu.Lock()
	defer sp.mu.Unlock()

	if len(sp.sessions) >= sp.maxSessions {
		return nil, nil
	}

	session, err := NewSession(sp.userAgent)
	if err != nil {
		return nil, err
	}

	sp.sessions[session.ID] = session
	return session, nil
}

// RemoveSession - 移除会话
func (sp *SessionPool) RemoveSession(sessionID string) {
	sp.mu.Lock()
	defer sp.mu.Unlock()

	if session, exists := sp.sessions[sessionID]; exists {
		session.Close()
		delete(sp.sessions, sessionID)
	}
}

// GetSessionByID - 根据 ID 获取会话
func (sp *SessionPool) GetSessionByID(sessionID string) *Session {
	sp.mu.RLock()
	defer sp.mu.RUnlock()

	if session, exists := sp.sessions[sessionID]; exists {
		return session
	}
	return nil
}

// getValidSessions - 获取有效会话列表
func (sp *SessionPool) getValidSessions() []*Session {
	sp.mu.RLock()
	defer sp.mu.RUnlock()

	now := time.Now()
	result := make([]*Session, 0)

	for _, session := range sp.sessions {
		session.mu.RLock()
		age := now.Sub(session.CreatedAt)
		idleTime := now.Sub(session.LastUsedAt)

		if session.IsValid &&
			age < sp.maxAge &&
			idleTime < sp.maxIdleTime &&
			session.RequestCount < sp.maxRequests {
			result = append(result, session)
		}
		session.mu.RUnlock()
	}

	return result
}

// autoRecycleLoop - 自动回收循环
func (sp *SessionPool) autoRecycleLoop() {
	for {
		select {
		case <-sp.recycleTicker.C:
			sp.recycle()
		case <-sp.stopChan:
			return
		}
	}
}

// recycle - 回收过期会话
func (sp *SessionPool) recycle() {
	sp.mu.Lock()
	defer sp.mu.Unlock()

	now := time.Now()
	toRemove := make([]string, 0)

	for id, session := range sp.sessions {
		session.mu.RLock()
		age := now.Sub(session.CreatedAt)
		idleTime := now.Sub(session.LastUsedAt)

		if !session.IsValid ||
			age >= sp.maxAge ||
			idleTime >= sp.maxIdleTime ||
			session.RequestCount >= sp.maxRequests {
			toRemove = append(toRemove, id)
		}
		session.mu.RUnlock()
	}

	for _, id := range toRemove {
		if session, exists := sp.sessions[id]; exists {
			session.Close()
			delete(sp.sessions, id)
		}
	}
}

// GetStats - 获取统计信息
func (sp *SessionPool) GetStats() map[string]interface{} {
	sp.mu.RLock()
	defer sp.mu.RUnlock()

	total := len(sp.sessions)
	valid := 0
	invalid := 0

	for _, session := range sp.sessions {
		session.mu.RLock()
		if session.IsValid {
			valid++
		} else {
			invalid++
		}
		session.mu.RUnlock()
	}

	return map[string]interface{}{
		"total":         total,
		"valid":         valid,
		"invalid":       invalid,
		"validity_rate": float64(valid) / float64(total),
	}
}

// Size - 会话池大小
func (sp *SessionPool) Size() int {
	sp.mu.RLock()
	defer sp.mu.RUnlock()
	return len(sp.sessions)
}

// ValidSize - 有效会话数量
func (sp *SessionPool) ValidSize() int {
	sp.mu.RLock()
	defer sp.mu.RUnlock()

	count := 0
	for _, session := range sp.sessions {
		session.mu.RLock()
		if session.IsValid {
			count++
		}
		session.mu.RUnlock()
	}
	return count
}

// Clear - 清空会话池
func (sp *SessionPool) Clear() {
	sp.mu.Lock()
	defer sp.mu.Unlock()

	for _, session := range sp.sessions {
		session.Close()
	}
	sp.sessions = make(map[string]*Session)
}

// Close - 关闭会话池
func (sp *SessionPool) Close() {
	if sp.recycleTicker != nil {
		sp.recycleTicker.Stop()
		close(sp.stopChan)
	}
	sp.Clear()
}

// generateSessionID - 生成会话 ID
func generateSessionID() (string, error) {
	bytes := make([]byte, 16)
	if _, err := rand.Read(bytes); err != nil {
		return "", err
	}
	return hex.EncodeToString(bytes), nil
}
