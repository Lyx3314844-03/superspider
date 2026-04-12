package antibot

import (
	"bytes"
	"crypto/md5"
	"encoding/json"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"time"
)

// CloudflareBypass - Cloudflare 绕过器
type CloudflareBypass struct {
	uaRotator *UserAgentRotator
	client    *http.Client
}

// NewCloudflareBypass - 创建 Cloudflare 绕过器
func NewCloudflareBypass() *CloudflareBypass {
	return &CloudflareBypass{
		uaRotator: NewUserAgentRotator(),
		client: &http.Client{
			Timeout: 30 * time.Second,
			CheckRedirect: func(req *http.Request, via []*http.Request) error {
				return http.ErrUseLastResponse // 不自动跟随重定向
			},
		},
	}
}

// GetCloudflareHeaders - 获取绕过 Cloudflare 的请求头
func (cf *CloudflareBypass) GetCloudflareHeaders() map[string]string {
	return map[string]string{
		"User-Agent":              cf.uaRotator.GetBrowserUserAgent("chrome"),
		"Accept":                  "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
		"Accept-Language":         "en-US,en;q=0.9,zh-CN;q=0.8",
		"Accept-Encoding":         "gzip, deflate, br",
		"Connection":              "keep-alive",
		"Upgrade-Insecure-Requests": "1",
		"Sec-Fetch-Dest":          "document",
		"Sec-Fetch-Mode":          "navigate",
		"Sec-Fetch-Site":          "none",
		"Sec-Fetch-User":          "?1",
		"Sec-Ch-Ua":               `"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"`,
		"Sec-Ch-Ua-Mobile":        "?0",
		"Sec-Ch-Ua-Platform":      `"Windows"`,
		"Cache-Control":           "max-age=0",
	}
}

// SolveCloudflareChallenge - 解决 Cloudflare 挑战（需要浏览器自动化）
func (cf *CloudflareBypass) SolveCloudflareChallenge(targetURL string) (*http.Response, error) {
	// 第一步：初始请求获取挑战页面
	req, _ := http.NewRequest("GET", targetURL, nil)
	for k, v := range cf.GetCloudflareHeaders() {
		req.Header.Set(k, v)
	}

	resp, err := cf.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("初始请求失败: %w", err)
	}

	// 检查是否是 Cloudflare 挑战页面
	body, _ := io.ReadAll(resp.Body)
	resp.Body = io.NopCloser(bytes.NewBuffer(body))

	if strings.Contains(string(body), "cf-chl-bypass") || 
	   strings.Contains(string(body), "jschl_vc") ||
	   strings.Contains(string(body), "cf-wrapper") {
		// 检测到 Cloudflare 挑战
		// 注意：完整的解决方案需要使用 headless browser (如 chromedp)
		// 这里返回标记，让上层知道需要浏览器自动化
		return resp, fmt.Errorf("检测到 Cloudflare 挑战，需要浏览器自动化")
	}

	return resp, nil
}

// ExtractCloudflareParams - 提取 Cloudflare 挑战参数
func (cf *CloudflareBypass) ExtractCloudflareParams(html string) map[string]string {
	params := make(map[string]string)

	// 提取 jschl_vc
	re := regexp.MustCompile(`name="jschl_vc" value="([^"]+)"`)
	if matches := re.FindStringSubmatch(html); len(matches) > 1 {
		params["jschl_vc"] = matches[1]
	}

	// 提取 pass
	re = regexp.MustCompile(`name="pass" value="([^"]+)"`)
	if matches := re.FindStringSubmatch(html); len(matches) > 1 {
		params["pass"] = matches[1]
	}

	return params
}

// AkamaiBypass - Akamai 绕过器
type AkamaiBypass struct {
	uaRotator *UserAgentRotator
}

// NewAkamaiBypass - 创建 Akamai 绕过器
func NewAkamaiBypass() *AkamaiBypass {
	return &AkamaiBypass{
		uaRotator: NewUserAgentRotator(),
	}
}

// GetAkamaiHeaders - 获取绕过 Akamai 的请求头
func (ak *AkamaiBypass) GetAkamaiHeaders() map[string]string {
	return map[string]string{
		"User-Agent":        ak.uaRotator.GetBrowserUserAgent("chrome"),
		"Accept":            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
		"Accept-Language":   "en-US,en;q=0.9,zh-CN;q=0.8",
		"Accept-Encoding":   "gzip, deflate, br",
		"Connection":        "keep-alive",
		"X-Requested-With":  "XMLHttpRequest",
		"Sec-Fetch-Dest":    "empty",
		"Sec-Fetch-Mode":    "cors",
		"Sec-Fetch-Site":    "same-origin",
		"Pragma":            "no-cache",
		"Cache-Control":     "no-cache",
	}
}

// DetectAkamai - 检测是否被 Akamai 拦截
func (ak *AkamaiBypass) DetectAkamai(html string, statusCode int) bool {
	akamaiIndicators := []string{
		"ak_bmsc",
		"bm_sz",
		"abck",
		"akamai",
		"bot manager",
		"access denied",
	}

	htmlLower := strings.ToLower(html)
	for _, indicator := range akamaiIndicators {
		if strings.Contains(htmlLower, indicator) {
			return true
		}
	}

	return statusCode == 403
}

// CaptchaSolver - 验证码解决器
type CaptchaSolver struct {
	APIKey    string
	Service   string // "2captcha", "anticaptcha", "capmonster"
	Endpoint  string
}

// NewCaptchaSolver - 创建验证码解决器
func NewCaptchaSolver(apiKey, service string) *CaptchaSolver {
	endpoints := map[string]string{
		"2captcha":    "https://2captcha.com",
		"anticaptcha": "https://api.anti-captcha.com",
		"capmonster":  "https://api.capmonster.cloud",
	}

	return &CaptchaSolver{
		APIKey:   apiKey,
		Service:  service,
		Endpoint: endpoints[service],
	}
}

// SolveImageCaptcha - 解决图片验证码
func (cs *CaptchaSolver) SolveImageCaptcha(imageData []byte) (string, error) {
	switch cs.Service {
	case "2captcha":
		return cs.solveWith2Captcha(imageData, "normal")
	case "anticaptcha":
		return cs.solveWithAntiCaptcha(imageData)
	default:
		return "", fmt.Errorf("不支持的验证码服务: %s", cs.Service)
	}
}

// SolveReCaptcha - 解决 Google reCAPTCHA
func (cs *CaptchaSolver) SolveReCaptcha(siteKey, pageURL string) (string, error) {
	switch cs.Service {
	case "2captcha":
		return cs.solve2CaptchaReCaptcha(siteKey, pageURL)
	case "anticaptcha":
		return cs.solveAntiCaptchaReCaptcha(siteKey, pageURL)
	default:
		return "", fmt.Errorf("不支持的验证码服务: %s", cs.Service)
	}
}

// SolveHCaptcha - 解决 hCaptcha
func (cs *CaptchaSolver) SolveHCaptcha(siteKey, pageURL string) (string, error) {
	switch cs.Service {
	case "2captcha":
		return cs.solve2CaptchaHCaptcha(siteKey, pageURL)
	default:
		return "", fmt.Errorf("不支持的 hCaptcha 服务: %s", cs.Service)
	}
}

// 2Captcha 实现
func (cs *CaptchaSolver) solveWith2Captcha(imageData []byte, captchaType string) (string, error) {
	// 提交验证码任务
	formData := url.Values{}
	formData.Set("key", cs.APIKey)
	formData.Set("method", "base64")
	formData.Set("body", fmt.Sprintf("%x", imageData))
	formData.Set("json", "1")

	resp, err := http.PostForm(cs.Endpoint+"/in.php", formData)
	if err != nil {
		return "", fmt.Errorf("提交验证码失败: %w", err)
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", fmt.Errorf("解析响应失败: %w", err)
	}

	if status, ok := result["status"].(float64); !ok || status != 1 {
		return "", fmt.Errorf("提交失败: %v", result["request"])
	}

	taskID, ok := result["request"].(string)
	if !ok {
		return "", fmt.Errorf("无效的 task ID")
	}

	// 轮询结果
	for i := 0; i < 30; i++ {
		time.Sleep(5 * time.Second)

		resp, _ := http.Get(fmt.Sprintf("%s/res.php?key=%s&action=get&id=%s&json=1",
			cs.Endpoint, cs.APIKey, taskID))
		
		var pollResult map[string]interface{}
		json.NewDecoder(resp.Body).Decode(&pollResult)
		resp.Body.Close()

		if pollResult["status"].(float64) == 1 {
			return pollResult["request"].(string), nil
		}
	}

	return "", fmt.Errorf("验证码解决超时")
}

func (cs *CaptchaSolver) solve2CaptchaReCaptcha(siteKey, pageURL string) (string, error) {
	formData := url.Values{}
	formData.Set("key", cs.APIKey)
	formData.Set("method", "userrecaptcha")
	formData.Set("googlekey", siteKey)
	formData.Set("pageurl", pageURL)
	formData.Set("json", "1")

	resp, err := http.PostForm(cs.Endpoint+"/in.php", formData)
	if err != nil {
		return "", fmt.Errorf("提交 reCAPTCHA 失败: %w", err)
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", fmt.Errorf("解析响应失败: %w", err)
	}

	if status, ok := result["status"].(float64); !ok || status != 1 {
		return "", fmt.Errorf("提交失败: %v", result["request"])
	}

	taskID, ok := result["request"].(string)
	if !ok {
		return "", fmt.Errorf("无效的 task ID")
	}

	// 轮询结果（reCAPTCHA 需要更长时间）
	for i := 0; i < 60; i++ {
		time.Sleep(5 * time.Second)

		resp, _ := http.Get(fmt.Sprintf("%s/res.php?key=%s&action=get&id=%s&json=1",
			cs.Endpoint, cs.APIKey, taskID))
		
		var pollResult map[string]interface{}
		json.NewDecoder(resp.Body).Decode(&pollResult)
		resp.Body.Close()

		if pollResult["status"].(float64) == 1 {
			return pollResult["request"].(string), nil
		}
	}

	return "", fmt.Errorf("reCAPTCHA 解决超时")
}

func (cs *CaptchaSolver) solve2CaptchaHCaptcha(siteKey, pageURL string) (string, error) {
	formData := url.Values{}
	formData.Set("key", cs.APIKey)
	formData.Set("method", "hcaptcha")
	formData.Set("sitekey", siteKey)
	formData.Set("pageurl", pageURL)
	formData.Set("json", "1")

	resp, err := http.PostForm(cs.Endpoint+"/in.php", formData)
	if err != nil {
		return "", fmt.Errorf("提交 hCaptcha 失败: %w", err)
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", fmt.Errorf("解析响应失败: %w", err)
	}

	taskID, ok := result["request"].(string)
	if !ok {
		return "", fmt.Errorf("无效的 task ID")
	}

	// 轮询结果
	for i := 0; i < 60; i++ {
		time.Sleep(5 * time.Second)

		resp, err := http.Get(fmt.Sprintf("%s/res.php?key=%s&action=get&id=%s&json=1",
			cs.Endpoint, cs.APIKey, taskID))
		if err != nil {
			continue // 轮询失败继续尝试
		}

		var pollResult map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&pollResult); err != nil {
			resp.Body.Close()
			continue
		}
		resp.Body.Close()

		if status, ok := pollResult["status"].(float64); ok && status == 1 {
			if request, ok := pollResult["request"].(string); ok {
				return request, nil
			}
		}
	}

	return "", fmt.Errorf("hCaptcha 解决超时")
}

func (cs *CaptchaSolver) solveWithAntiCaptcha(imageData []byte) (string, error) {
	// Anti-Captcha 实现（简化版）
	payload := map[string]interface{}{
		"clientKey": cs.APIKey,
		"task": map[string]interface{}{
			"type": "ImageToTextTask",
			"body": fmt.Sprintf("%x", imageData),
		},
	}

	jsonPayload, _ := json.Marshal(payload)
	resp, err := http.Post(cs.Endpoint+"/createTask", "application/json", bytes.NewBuffer(jsonPayload))
	if err != nil {
		return "", fmt.Errorf("提交 Anti-Captcha 失败: %w", err)
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", fmt.Errorf("解析响应失败: %w", err)
	}

	taskID, ok := result["taskId"].(float64)
	if !ok {
		return "", fmt.Errorf("无效的 task ID")
	}

	// 轮询结果
	for i := 0; i < 30; i++ {
		time.Sleep(5 * time.Second)

		payload := map[string]interface{}{
			"clientKey": cs.APIKey,
			"taskId":    taskID,
		}
		jsonPayload, _ := json.Marshal(payload)
		resp, err := http.Post(cs.Endpoint+"/getTaskResult", "application/json", bytes.NewBuffer(jsonPayload))
		if err != nil {
			continue
		}

		var pollResult map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&pollResult); err != nil {
			resp.Body.Close()
			continue
		}
		resp.Body.Close()

		if pollResult["status"] == "ready" {
			if solution, ok := pollResult["solution"].(map[string]interface{}); ok {
				if text, ok := solution["text"].(string); ok {
					return text, nil
				}
			}
		}
	}

	return "", fmt.Errorf("验证码解决超时")
}

func (cs *CaptchaSolver) solveAntiCaptchaReCaptcha(siteKey, pageURL string) (string, error) {
	// Anti-Captcha reCAPTCHA 实现
	payload := map[string]interface{}{
		"clientKey": cs.APIKey,
		"task": map[string]interface{}{
			"type":       "NoCaptchaTask",
			"websiteURL": pageURL,
			"websiteKey": siteKey,
		},
	}

	jsonPayload, _ := json.Marshal(payload)
	resp, err := http.Post(cs.Endpoint+"/createTask", "application/json", bytes.NewBuffer(jsonPayload))
	if err != nil {
		return "", fmt.Errorf("提交 Anti-Captcha reCAPTCHA 失败: %w", err)
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", fmt.Errorf("解析响应失败: %w", err)
	}

	taskID, ok := result["taskId"].(float64)
	if !ok {
		return "", fmt.Errorf("无效的 task ID")
	}

	// 轮询结果
	for i := 0; i < 60; i++ {
		time.Sleep(5 * time.Second)

		payload := map[string]interface{}{
			"clientKey": cs.APIKey,
			"taskId":    taskID,
		}
		jsonPayload, _ := json.Marshal(payload)
		resp, err := http.Post(cs.Endpoint+"/getTaskResult", "application/json", bytes.NewBuffer(jsonPayload))
		if err != nil {
			continue
		}

		var pollResult map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&pollResult); err != nil {
			resp.Body.Close()
			continue
		}
		resp.Body.Close()

		if pollResult["status"] == "ready" {
			if solution, ok := pollResult["solution"].(map[string]interface{}); ok {
				if token, ok := solution["gRecaptchaResponse"].(string); ok {
					return token, nil
				}
			}
		}
	}

	return "", fmt.Errorf("reCAPTCHA 解决超时")
}

// BrowserFingerprintGenerator - 浏览器指纹生成器（避免与 enhancer.go 冲突）
type BrowserFingerprintGenerator struct {
	screenResolutions []string
	timezones         []string
	locales           []string
	platforms         []string
}

// NewBrowserFingerprintGenerator - 创建浏览器指纹生成器
func NewBrowserFingerprintGenerator() *BrowserFingerprintGenerator {
	return &BrowserFingerprintGenerator{
		screenResolutions: []string{"1920x1080", "1366x768", "1536x864", "1440x900", "2560x1440"},
		timezones:         []string{"Asia/Shanghai", "America/New_York", "Europe/London", "Asia/Tokyo"},
		locales:           []string{"zh-CN", "en-US", "en-GB", "ja-JP"},
		platforms:         []string{"Win32", "MacIntel", "Linux x86_64"},
	}
}

// GenerateFingerprint - 生成完整的浏览器指纹
func (bfg *BrowserFingerprintGenerator) GenerateFingerprint() map[string]interface{} {
	return map[string]interface{}{
		"user_agent":      bfg.getRandomUserAgent(),
		"screen":          bfg.screenResolutions[rand.Intn(len(bfg.screenResolutions))],
		"timezone":        bfg.timezones[rand.Intn(len(bfg.timezones))],
		"locale":          bfg.locales[rand.Intn(len(bfg.locales))],
		"platform":        bfg.platforms[rand.Intn(len(bfg.platforms))],
		"webdriver":       false,
		"languages":       []string{"zh-CN", "zh", "en"},
		"plugins":         bfg.generateFakePlugins(),
		"canvas":          bfg.generateCanvasHash(),
		"webgl":           bfg.generateWebGLHash(),
	}
}

// GenerateStealthHeaders - 生成隐身请求头（避免检测）
func (bfg *BrowserFingerprintGenerator) GenerateStealthHeaders() map[string]string {
	return map[string]string{
		"User-Agent":             bfg.getRandomUserAgent(),
		"Accept":                 "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
		"Accept-Language":        "zh-CN,zh;q=0.9,en;q=0.8",
		"Accept-Encoding":        "gzip, deflate, br",
		"Connection":             "keep-alive",
		"Upgrade-Insecure-Requests": "1",
		"Sec-Fetch-Dest":         "document",
		"Sec-Fetch-Mode":         "navigate",
		"Sec-Fetch-Site":         "none",
		"Sec-Fetch-User":         "?1",
		"Sec-Ch-Ua":              `"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"`,
		"Sec-Ch-Ua-Mobile":       "?0",
		"Sec-Ch-Ua-Platform":     `"Windows"`,
		"Sec-Ch-Ua-Full-Version": `"120.0.0.0"`,
		"Sec-Ch-Ua-Arch":         `"x86"`,
		"Sec-Ch-Ua-Bitness":      `"64"`,
		"Sec-Ch-Ua-Model":        `""`,
		"Sec-Ch-Ua-Platform-Version": `"15.0.0"`,
		"DNT":                    "1",
		"Cache-Control":          "max-age=0",
	}
}

func (bfg *BrowserFingerprintGenerator) getRandomUserAgent() string {
	rotator := NewUserAgentRotator()
	return rotator.GetRandomUserAgent()
}

func (bfg *BrowserFingerprintGenerator) generateFakePlugins() []string {
	return []string{
		"Chrome PDF Plugin",
		"Chrome PDF Viewer",
		"Native Client",
		"Widevine Content Decryption Module",
	}
}

func (bfg *BrowserFingerprintGenerator) generateCanvasHash() string {
	data := fmt.Sprintf("canvas_%d_%d", rand.Intn(10000), time.Now().UnixNano())
	hash := md5.Sum([]byte(data))
	return fmt.Sprintf("%x", hash)
}

func (bfg *BrowserFingerprintGenerator) generateWebGLHash() string {
	data := fmt.Sprintf("webgl_%d_%d", rand.Intn(10000), time.Now().UnixNano())
	hash := md5.Sum([]byte(data))
	return fmt.Sprintf("%x", hash)
}
