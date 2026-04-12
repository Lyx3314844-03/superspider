package encrypted

import (
	"bytes"
	"encoding/json"
	"fmt"
	nodereverse "gospider/node_reverse"
	"io"
	"net/http"
	"regexp"
	"strings"
	"time"
)

// EncryptedSiteCrawler - 加密网站爬虫
type EncryptedSiteCrawler struct {
	client         *http.Client
	reverseService string
	reverseClient  *nodereverse.NodeReverseClient
	userAgent      string
}

type pageFetchResult struct {
	HTML       string
	StatusCode int
	Headers    map[string]interface{}
	Cookies    string
}

// EncryptionInfo - 加密信息
type EncryptionInfo struct {
	Patterns         []string          `json:"patterns"`
	EncryptedScripts map[string]string `json:"encrypted_scripts"`
	ScriptCount      int               `json:"script_count"`
	WebpackModules   int               `json:"webpack_modules"`
}

// CrawlResult - 爬取结果
type CrawlResult struct {
	URL            string                 `json:"url"`
	HTML           string                 `json:"html"`
	EncryptionInfo EncryptionInfo         `json:"encryption_info"`
	AntiBotProfile map[string]interface{} `json:"anti_bot_profile,omitempty"`
	DecryptedData  []string               `json:"decrypted_data"`
	Success        bool                   `json:"success"`
	Error          string                 `json:"error,omitempty"`
}

// NewEncryptedSiteCrawler - 创建加密网站爬虫
func NewEncryptedSiteCrawler(reverseServiceURL string) *EncryptedSiteCrawler {
	return &EncryptedSiteCrawler{
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
		reverseService: reverseServiceURL,
		reverseClient:  nodereverse.NewNodeReverseClient(reverseServiceURL),
		userAgent:      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	}
}

// Crawl - 爬取加密网站
func (c *EncryptedSiteCrawler) Crawl(targetURL string) (*CrawlResult, error) {
	result := &CrawlResult{
		URL: targetURL,
		EncryptionInfo: EncryptionInfo{
			Patterns:         []string{},
			EncryptedScripts: make(map[string]string),
		},
		DecryptedData: []string{},
	}

	// 第一步：获取页面
	pageSnapshot, err := c.fetchPage(targetURL)
	if err != nil {
		result.Error = fmt.Sprintf("获取页面失败: %v", err)
		return result, err
	}
	result.HTML = pageSnapshot.HTML

	if c.reverseService != "" {
		profile, err := c.profileAntiBot(targetURL, pageSnapshot)
		if err == nil && profile != nil {
			result.AntiBotProfile = profile
			c.applyProfileHeaders(profile)
		}
	}

	// 第二步：分析加密信息
	encInfo := c.analyzeEncryption(pageSnapshot.HTML)
	result.EncryptionInfo = encInfo

	// 第三步：尝试解密
	if c.reverseService != "" {
		decrypted, err := c.decryptContent(pageSnapshot.HTML, encInfo)
		if err == nil {
			result.DecryptedData = decrypted
		}
	}

	result.Success = true
	return result, nil
}

// fetchPage - 获取页面内容
func (c *EncryptedSiteCrawler) fetchPage(url string) (*pageFetchResult, error) {
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("User-Agent", c.userAgent)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "en-US,en;q=0.9,zh-CN;q=0.8")

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	headers := map[string]interface{}{}
	for key, values := range resp.Header {
		if len(values) == 1 {
			headers[key] = values[0]
		} else if len(values) > 1 {
			headers[key] = values
		}
	}

	return &pageFetchResult{
		HTML:       string(body),
		StatusCode: resp.StatusCode,
		Headers:    headers,
		Cookies:    strings.Join(resp.Header.Values("Set-Cookie"), "; "),
	}, nil
}

func (c *EncryptedSiteCrawler) profileAntiBot(targetURL string, page *pageFetchResult) (map[string]interface{}, error) {
	if c.reverseClient == nil || page == nil {
		return nil, nil
	}

	response, err := c.reverseClient.ProfileAntiBot(nodereverse.AntiBotProfileRequest{
		HTML:       page.HTML,
		Headers:    page.Headers,
		Cookies:    page.Cookies,
		StatusCode: page.StatusCode,
		URL:        targetURL,
	})
	if err != nil || response == nil || !response.Success {
		return nil, err
	}

	profile := map[string]interface{}{
		"level":            response.Level,
		"score":            response.Score,
		"signals":          response.Signals,
		"recommendations":  response.Recommendations,
		"vendors":          response.Vendors,
		"requestBlueprint": response.RequestBlueprint,
		"mitigationPlan":   response.MitigationPlan,
	}

	fmt.Printf("🛡️  Anti-bot profile: level=%s score=%d\n", response.Level, response.Score)
	if len(response.Signals) > 0 {
		fmt.Printf("   signals: %s\n", strings.Join(response.Signals, ", "))
	}
	if len(response.Recommendations) > 0 {
		fmt.Printf("   next: %s\n", response.Recommendations[0])
	}

	return profile, nil
}

func (c *EncryptedSiteCrawler) applyProfileHeaders(profile map[string]interface{}) {
	blueprint, ok := profile["requestBlueprint"].(map[string]interface{})
	if !ok {
		return
	}
	headers, ok := blueprint["headers"].(map[string]interface{})
	if !ok {
		return
	}
	for key, value := range headers {
		if strings.EqualFold(key, "user-agent") {
			if userAgent, ok := value.(string); ok && userAgent != "" {
				c.userAgent = userAgent
				return
			}
		}
	}
}

// analyzeEncryption - 分析页面加密情况
func (c *EncryptedSiteCrawler) analyzeEncryption(html string) EncryptionInfo {
	info := EncryptionInfo{
		Patterns:         []string{},
		EncryptedScripts: make(map[string]string),
	}

	// 检测 Webpack
	if strings.Contains(html, "webpack") {
		info.Patterns = append(info.Patterns, "webpack")
	}

	// 检测混淆
	if strings.Contains(html, "_0x") || strings.Contains(html, "\\x") {
		info.Patterns = append(info.Patterns, "obfuscation")
	}

	// 检测加密脚本
	scriptRegex := regexp.MustCompile(`<script[^>]*>([\s\S]*?)</script>`)
	scripts := scriptRegex.FindAllStringSubmatch(html, -1)

	for i, script := range scripts {
		if len(script) > 1 {
			content := script[1]
			// 检查是否包含加密特征
			if strings.Contains(content, "_0x") ||
				strings.Contains(content, "eval(") ||
				strings.Contains(content, "atob(") ||
				strings.Contains(content, "btoa(") {
				key := fmt.Sprintf("script_%d", i)
				info.EncryptedScripts[key] = content[:min(200, len(content))]
			}
		}
	}
	info.ScriptCount = len(info.EncryptedScripts)

	// 检测 Webpack 模块
	webpackRegex := regexp.MustCompile(`\["(\w+)",\s*"(\w+)"\]`)
	info.WebpackModules = len(webpackRegex.FindAllString(html, -1))

	return info
}

// decryptContent - 使用逆向服务解密内容
func (c *EncryptedSiteCrawler) decryptContent(html string, info EncryptionInfo) ([]string, error) {
	if c.reverseService == "" {
		return nil, fmt.Errorf("未配置逆向服务")
	}

	// 调用逆向服务
	payload := map[string]interface{}{
		"html":     html,
		"patterns": info.Patterns,
	}

	jsonPayload, _ := json.Marshal(payload)
	resp, err := http.Post(c.reverseService+"/decrypt", "application/json", bytes.NewBuffer(jsonPayload))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)

	if decrypted, ok := result["decrypted"].([]interface{}); ok {
		var decryptedStrings []string
		for _, item := range decrypted {
			if s, ok := item.(string); ok {
				decryptedStrings = append(decryptedStrings, s)
			}
		}
		return decryptedStrings, nil
	}

	return nil, fmt.Errorf("解密失败")
}

// ExtractWebpackModules - 提取 Webpack 模块
func (c *EncryptedSiteCrawler) ExtractWebpackModules(html string) []string {
	var modules []string

	// 查找 Webpack 打包代码
	webpackRegex := regexp.MustCompile(`\(function\([^)]*\)\s*\{[\s\S]*?\}\)\(\[([\s\S]*?)\]\)`)
	matches := webpackRegex.FindAllStringSubmatch(html, -1)

	for _, match := range matches {
		if len(match) > 1 {
			modules = append(modules, match[1])
		}
	}

	return modules
}

// AnalyzeObfuscation - 分析代码混淆
func (c *EncryptedSiteCrawler) AnalyzeObfuscation(script string) map[string]interface{} {
	analysis := make(map[string]interface{})

	// 检测十六进制混淆
	hexCount := strings.Count(script, "\\x")
	analysis["hex_obfuscation"] = hexCount

	// 检测 base64 编码
	base64Count := strings.Count(script, "atob(") + strings.Count(script, "btoa(")
	analysis["base64_encoding"] = base64Count

	// 检测变量混淆
	varRegex := regexp.MustCompile(`var\s+_0x\w+`)
	varCount := len(varRegex.FindAllString(script, -1))
	analysis["obfuscated_vars"] = varCount

	// 检测 eval 使用
	evalCount := strings.Count(script, "eval(")
	analysis["eval_usage"] = evalCount

	// 综合评分
	score := 0
	if hexCount > 10 {
		score += 30
	}
	if base64Count > 5 {
		score += 20
	}
	if varCount > 20 {
		score += 30
	}
	if evalCount > 0 {
		score += 20
	}
	analysis["obfuscation_score"] = min(100, score)

	return analysis
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
