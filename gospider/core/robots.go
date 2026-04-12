package core

import (
	"bufio"
	"log"
	"net/http"
	"net/url"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
)

// RobotsChecker robots.txt 检查器
type RobotsChecker struct {
	userAgent     string
	cacheTimeout  time.Duration
	parsers       map[string]*robotsCacheEntry
	mu            sync.RWMutex
	respectRobots bool
	httpClient    *http.Client
}

type robotsCacheEntry struct {
	parser    *SimpleRobotsParser
	timestamp time.Time
}

// SimpleRobotsParser 简化的 robots.txt 解析
type SimpleRobotsParser struct {
	rules map[string]*robotsRuleSet
}

type robotsRuleSet struct {
	allow      []string
	disallow   []string
	crawlDelay float64
}

// NewRobotsChecker 创建 robots.txt 检查器
func NewRobotsChecker(userAgent string, cacheTimeout time.Duration) *RobotsChecker {
	if userAgent == "" {
		userAgent = "*"
	}
	if cacheTimeout == 0 {
		cacheTimeout = time.Hour
	}
	return &RobotsChecker{
		userAgent:     userAgent,
		cacheTimeout:  cacheTimeout,
		parsers:       make(map[string]*robotsCacheEntry),
		respectRobots: true,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// SetRespectRobots 设置是否遵守 robots.txt
func (rc *RobotsChecker) SetRespectRobots(respect bool) {
	rc.respectRobots = respect
}

// IsAllowed 检查 URL 是否允许爬取
func (rc *RobotsChecker) IsAllowed(rawURL string, userAgent ...string) bool {
	if !rc.respectRobots {
		return true
	}

	u, err := url.Parse(rawURL)
	if err != nil {
		return true // 解析失败,默认允许
	}

	domain := u.Scheme + "://" + u.Host
	ua := rc.userAgent
	if len(userAgent) > 0 {
		ua = userAgent[0]
	}

	parser := rc.getParser(domain)
	if parser == nil {
		return true // 无法获取,默认允许
	}

	return parser.isAllowed(u.Path, ua)
}

// GetCrawlDelay 获取爬取延迟(秒)
func (rc *RobotsChecker) GetCrawlDelay(rawURL string) float64 {
	u, err := url.Parse(rawURL)
	if err != nil {
		return 0
	}

	domain := u.Scheme + "://" + u.Host
	parser := rc.getParser(domain)
	if parser == nil {
		return 0
	}

	return parser.crawlDelayFor(rc.userAgent)
}

func (rc *RobotsChecker) getParser(domain string) *SimpleRobotsParser {
	rc.mu.RLock()
	entry, exists := rc.parsers[domain]
	rc.mu.RUnlock()

	if exists && time.Since(entry.timestamp) < rc.cacheTimeout {
		return entry.parser
	}

	// 尝试加载 robots.txt
	robotsURL := domain + "/robots.txt"
	parser := rc.loadRobotsTxt(robotsURL)

	rc.mu.Lock()
	rc.parsers[domain] = &robotsCacheEntry{
		parser:    parser,
		timestamp: time.Now(),
	}
	rc.mu.Unlock()

	return parser
}

func (rc *RobotsChecker) loadRobotsTxt(robotsURL string) *SimpleRobotsParser {
	req, err := http.NewRequest(http.MethodGet, robotsURL, nil)
	if err != nil {
		log.Printf("[robots] invalid url %s: %v", robotsURL, err)
		return newSimpleRobotsParser()
	}
	req.Header.Set("User-Agent", rc.userAgent)

	resp, err := rc.httpClient.Do(req)
	if err != nil {
		log.Printf("[robots] fetch failed %s: %v", robotsURL, err)
		return newSimpleRobotsParser()
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		log.Printf("[robots] no policy (%d) for %s", resp.StatusCode, robotsURL)
		return newSimpleRobotsParser()
	}

	parser := newSimpleRobotsParser()
	scanner := bufio.NewScanner(resp.Body)
	lines := make([]string, 0, 64)
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}
	if err := scanner.Err(); err != nil {
		log.Printf("[robots] read failed %s: %v", robotsURL, err)
		return newSimpleRobotsParser()
	}
	parser.parse(lines)
	return parser
}

func (rp *SimpleRobotsParser) isAllowed(path string, userAgent string) bool {
	if rp == nil {
		return true
	}
	if path == "" {
		path = "/"
	}
	rules := rp.rulesFor(userAgent)
	if rules == nil {
		return true
	}

	bestAllow := -1
	bestDisallow := -1
	for _, rule := range rules.allow {
		if matchesRobotsRule(path, rule) && len(rule) > bestAllow {
			bestAllow = len(rule)
		}
	}
	for _, rule := range rules.disallow {
		if matchesRobotsRule(path, rule) && len(rule) > bestDisallow {
			bestDisallow = len(rule)
		}
	}

	if bestAllow < 0 && bestDisallow < 0 {
		return true
	}
	return bestAllow >= bestDisallow
}

// ClearCache 清除缓存
func (rc *RobotsChecker) ClearCache() {
	rc.mu.Lock()
	defer rc.mu.Unlock()
	rc.parsers = make(map[string]*robotsCacheEntry)
}

func newSimpleRobotsParser() *SimpleRobotsParser {
	return &SimpleRobotsParser{
		rules: make(map[string]*robotsRuleSet),
	}
}

func (rp *SimpleRobotsParser) parse(lines []string) {
	currentAgents := make([]string, 0, 2)
	groupHasDirective := false
	for _, line := range lines {
		raw := strings.TrimSpace(stripRobotsComment(line))
		if raw == "" {
			continue
		}

		lower := strings.ToLower(raw)
		switch {
		case strings.HasPrefix(lower, "user-agent:"):
			if groupHasDirective {
				currentAgents = currentAgents[:0]
				groupHasDirective = false
			}
			ua := strings.TrimSpace(raw[len("user-agent:"):])
			if ua == "" {
				continue
			}
			normalized := strings.ToLower(ua)
			currentAgents = append(currentAgents, normalized)
			rp.ensureRuleSet(normalized)
		case strings.HasPrefix(lower, "allow:"):
			value := strings.TrimSpace(raw[len("allow:"):])
			for _, ua := range currentAgents {
				rp.rules[ua].allow = append(rp.rules[ua].allow, value)
			}
			groupHasDirective = true
		case strings.HasPrefix(lower, "disallow:"):
			value := strings.TrimSpace(raw[len("disallow:"):])
			for _, ua := range currentAgents {
				rp.rules[ua].disallow = append(rp.rules[ua].disallow, value)
			}
			groupHasDirective = true
		case strings.HasPrefix(lower, "crawl-delay:"):
			value := strings.TrimSpace(raw[len("crawl-delay:"):])
			delay, err := strconv.ParseFloat(value, 64)
			if err != nil || delay < 0 {
				continue
			}
			for _, ua := range currentAgents {
				rp.rules[ua].crawlDelay = delay
			}
			groupHasDirective = true
		}
	}
}

func (rp *SimpleRobotsParser) rulesFor(userAgent string) *robotsRuleSet {
	if rp == nil || len(rp.rules) == 0 {
		return nil
	}
	ua := strings.ToLower(strings.TrimSpace(userAgent))
	if ua == "" {
		ua = "*"
	}
	if rules, ok := rp.rules[ua]; ok {
		return rules
	}
	if rules, ok := rp.rules["*"]; ok {
		return rules
	}
	return nil
}

func (rp *SimpleRobotsParser) crawlDelayFor(userAgent string) float64 {
	rules := rp.rulesFor(userAgent)
	if rules == nil {
		return 0
	}
	return rules.crawlDelay
}

func (rp *SimpleRobotsParser) ensureRuleSet(userAgent string) {
	if _, ok := rp.rules[userAgent]; !ok {
		rp.rules[userAgent] = &robotsRuleSet{}
	}
}

func stripRobotsComment(line string) string {
	if idx := strings.Index(line, "#"); idx >= 0 {
		return line[:idx]
	}
	return line
}

func matchesRobotsRule(path string, rule string) bool {
	if rule == "" {
		return false
	}
	if !strings.ContainsAny(rule, "*$") {
		return strings.HasPrefix(path, rule)
	}
	pattern := regexp.QuoteMeta(rule)
	pattern = strings.ReplaceAll(pattern, `\*`, ".*")
	if strings.HasSuffix(pattern, `\$`) {
		pattern = strings.TrimSuffix(pattern, `\$`) + "$"
	}
	re, err := regexp.Compile("^" + pattern)
	if err != nil {
		return strings.HasPrefix(path, rule)
	}
	return re.MatchString(path)
}
