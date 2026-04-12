package captcha

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"
)

// CaptchaSolver 验证码解决器
type CaptchaSolver struct {
	apiKey    string
	service   string
	timeout   time.Duration
	httpClient *http.Client
	pollInterval time.Duration
	maxPolls int
}

// NewCaptchaSolver 创建验证码解决器
func NewCaptchaSolver(apiKey, service string) *CaptchaSolver {
	return &CaptchaSolver{
		apiKey:  apiKey,
		service: service,
		timeout: 30 * time.Second,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
		pollInterval: 2 * time.Second,
		maxPolls: 30,
	}
}

// SolveResult 解决结果
type SolveResult struct {
	Success bool   `json:"success"`
	Text    string `json:"text"`
	Error   string `json:"error,omitempty"`
}

// SolveImage 解决图片验证码
func (cs *CaptchaSolver) SolveImage(imageData []byte) (*SolveResult, error) {
	switch cs.service {
	case "2captcha":
		return cs.solve2Captcha(imageData)
	case "anticaptcha":
		return cs.solveAntiCaptcha(imageData)
	default:
		return cs.solve2Captcha(imageData)
	}
}

// solve2Captcha 使用 2Captcha 解决
func (cs *CaptchaSolver) solve2Captcha(imageData []byte) (*SolveResult, error) {
	// 上传图片
	base64Image := base64.StdEncoding.EncodeToString(imageData)
	
	resp, err := cs.httpClient.PostForm(
		"http://2captcha.com/in.php",
		map[string][]string{
			"key":   {cs.apiKey},
			"method": {"base64"},
			"body":  {base64Image},
		},
	)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	
	body, _ := io.ReadAll(resp.Body)
	
	// 解析任务 ID
	var result map[string]string
	json.Unmarshal(body, &result)
	
	if result["status"] != "1" {
		return &SolveResult{
			Success: false,
			Error:   result["request"],
		}, nil
	}
	
	taskID := result["request"]
	
	// 轮询获取结果
	for i := 0; i < 30; i++ {
		time.Sleep(2 * time.Second)
		
		resp, err := cs.httpClient.Get(
			"http://2captcha.com/res.php?key=" + cs.apiKey + "&action=get&id=" + taskID,
		)
		if err != nil {
			continue
		}
		
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		
		var result map[string]string
		json.Unmarshal(body, &result)
		
		if result["status"] == "1" {
			return &SolveResult{
				Success: true,
				Text:    result["request"],
			}, nil
		}
		
		if result["request"] != "CAPCHA_NOT_READY" {
			return &SolveResult{
				Success: false,
				Error:   result["request"],
			}, nil
		}
	}
	
	return &SolveResult{
		Success: false,
		Error:   "Timeout",
	}, nil
}

// solveAntiCaptcha 使用 Anti-Captcha 解决
func (cs *CaptchaSolver) solveAntiCaptcha(imageData []byte) (*SolveResult, error) {
	// 实现 Anti-Captcha API 调用
	base64Image := base64.StdEncoding.EncodeToString(imageData)
	
	payload := map[string]interface{}{
		"clientKey": cs.apiKey,
		"task": map[string]interface{}{
			"type": "ImageToTextTask",
			"body": base64Image,
		},
	}
	
	jsonData, _ := json.Marshal(payload)
	
	resp, err := cs.httpClient.Post(
		"https://api.anti-captcha.com/createTask",
		"application/json",
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	
	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)
	
	if result["errorId"].(float64) != 0 {
		return &SolveResult{
			Success: false,
			Error:   result["errorDescription"].(string),
		}, nil
	}
	
	taskID := int(result["taskId"].(float64))
	
	// 轮询获取结果
	for i := 0; i < 30; i++ {
		time.Sleep(2 * time.Second)
		
		payload := map[string]interface{}{
			"clientKey": cs.apiKey,
			"taskId":    taskID,
		}
		
		jsonData, _ := json.Marshal(payload)
		
		resp, err := cs.httpClient.Post(
			"https://api.anti-captcha.com/getTaskResult",
			"application/json",
			bytes.NewBuffer(jsonData),
		)
		if err != nil {
			continue
		}
		
		var result map[string]interface{}
		json.NewDecoder(resp.Body).Decode(&result)
		resp.Body.Close()
		
		if result["status"].(string) == "ready" {
			solution := result["solution"].(map[string]interface{})
			return &SolveResult{
				Success: true,
				Text:    solution["text"].(string),
			}, nil
		}
	}
	
	return &SolveResult{
		Success: false,
		Error:   "Timeout",
	}, nil
}

// SolveReCaptcha 解决 reCAPTCHA
func (cs *CaptchaSolver) SolveReCaptcha(siteKey, pageURL string) (*SolveResult, error) {
	if cs.apiKey == "" {
		return &SolveResult{Success: false, Error: "API key is required"}, nil
	}
	if siteKey == "" || pageURL == "" {
		return &SolveResult{Success: false, Error: "siteKey and pageURL are required"}, nil
	}

	switch cs.service {
	case "2captcha":
		token, err := cs.solve2CaptchaReCaptcha(siteKey, pageURL)
		if err != nil {
			return &SolveResult{Success: false, Error: err.Error()}, nil
		}
		return &SolveResult{Success: true, Text: token}, nil
	case "anticaptcha":
		token, err := cs.solveAntiCaptchaReCaptcha(siteKey, pageURL)
		if err != nil {
			return &SolveResult{Success: false, Error: err.Error()}, nil
		}
		return &SolveResult{Success: true, Text: token}, nil
	default:
		return &SolveResult{Success: false, Error: "unsupported service"}, nil
	}
}

// SolveHCaptcha 解决 hCaptcha
func (cs *CaptchaSolver) SolveHCaptcha(siteKey, pageURL string) (*SolveResult, error) {
	if cs.apiKey == "" {
		return &SolveResult{Success: false, Error: "API key is required"}, nil
	}
	if siteKey == "" || pageURL == "" {
		return &SolveResult{Success: false, Error: "siteKey and pageURL are required"}, nil
	}

	switch cs.service {
	case "2captcha":
		token, err := cs.solve2CaptchaHCaptcha(siteKey, pageURL)
		if err != nil {
			return &SolveResult{Success: false, Error: err.Error()}, nil
		}
		return &SolveResult{Success: true, Text: token}, nil
	case "anticaptcha":
		token, err := cs.solveAntiCaptchaHCaptcha(siteKey, pageURL)
		if err != nil {
			return &SolveResult{Success: false, Error: err.Error()}, nil
		}
		return &SolveResult{Success: true, Text: token}, nil
	default:
		return &SolveResult{Success: false, Error: "unsupported service"}, nil
	}
}

// ReportBad 报告错误的识别结果
func (cs *CaptchaSolver) ReportBad(taskID string) error {
	// 实现报告错误识别
	return nil
}

// SetPollingConfig 调整轮询间隔与最大轮询次数，便于测试和慢速 provider 调优。
func (cs *CaptchaSolver) SetPollingConfig(interval time.Duration, maxPolls int) {
	if interval > 0 {
		cs.pollInterval = interval
	}
	if maxPolls > 0 {
		cs.maxPolls = maxPolls
	}
}

func (cs *CaptchaSolver) solve2CaptchaReCaptcha(siteKey, pageURL string) (string, error) {
	formData := url.Values{}
	formData.Set("key", cs.apiKey)
	formData.Set("method", "userrecaptcha")
	formData.Set("googlekey", siteKey)
	formData.Set("pageurl", pageURL)
	formData.Set("json", "1")

	taskID, err := cs.submit2CaptchaTask(formData)
	if err != nil {
		return "", err
	}
	return cs.poll2CaptchaTask(taskID)
}

func (cs *CaptchaSolver) solve2CaptchaHCaptcha(siteKey, pageURL string) (string, error) {
	formData := url.Values{}
	formData.Set("key", cs.apiKey)
	formData.Set("method", "hcaptcha")
	formData.Set("sitekey", siteKey)
	formData.Set("pageurl", pageURL)
	formData.Set("json", "1")

	taskID, err := cs.submit2CaptchaTask(formData)
	if err != nil {
		return "", err
	}
	return cs.poll2CaptchaTask(taskID)
}

func (cs *CaptchaSolver) solveAntiCaptchaReCaptcha(siteKey, pageURL string) (string, error) {
	taskID, err := cs.createAntiCaptchaTask(map[string]interface{}{
		"type":       "NoCaptchaTaskProxyless",
		"websiteURL": pageURL,
		"websiteKey": siteKey,
	})
	if err != nil {
		return "", err
	}
	return cs.pollAntiCaptchaTask(taskID, "gRecaptchaResponse")
}

func (cs *CaptchaSolver) solveAntiCaptchaHCaptcha(siteKey, pageURL string) (string, error) {
	taskID, err := cs.createAntiCaptchaTask(map[string]interface{}{
		"type":       "HCaptchaTaskProxyless",
		"websiteURL": pageURL,
		"websiteKey": siteKey,
	})
	if err != nil {
		return "", err
	}
	return cs.pollAntiCaptchaTask(taskID, "gRecaptchaResponse")
}

func (cs *CaptchaSolver) submit2CaptchaTask(formData url.Values) (string, error) {
	resp, err := cs.httpClient.PostForm("https://2captcha.com/in.php", formData)
	if err != nil {
		return "", fmt.Errorf("submit 2captcha task: %w", err)
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", fmt.Errorf("decode 2captcha response: %w", err)
	}
	if status, ok := result["status"].(float64); !ok || status != 1 {
		return "", fmt.Errorf("2captcha submit failed: %v", result["request"])
	}
	taskID, ok := result["request"].(string)
	if !ok || taskID == "" {
		return "", fmt.Errorf("2captcha returned invalid task id")
	}
	return taskID, nil
}

func (cs *CaptchaSolver) poll2CaptchaTask(taskID string) (string, error) {
	for i := 0; i < cs.maxPolls; i++ {
		time.Sleep(cs.pollInterval)
		resp, err := cs.httpClient.Get(
			"https://2captcha.com/res.php?key=" + cs.apiKey + "&action=get&id=" + taskID + "&json=1",
		)
		if err != nil {
			continue
		}

		var result map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			resp.Body.Close()
			continue
		}
		resp.Body.Close()

		if status, ok := result["status"].(float64); ok && status == 1 {
			if request, ok := result["request"].(string); ok && request != "" {
				return request, nil
			}
		}
		if request, ok := result["request"].(string); ok && request != "CAPCHA_NOT_READY" {
			return "", fmt.Errorf("2captcha poll failed: %s", request)
		}
	}
	return "", fmt.Errorf("2captcha solve timeout")
}

func (cs *CaptchaSolver) createAntiCaptchaTask(task map[string]interface{}) (int, error) {
	payload := map[string]interface{}{
		"clientKey": cs.apiKey,
		"task":      task,
	}
	jsonData, _ := json.Marshal(payload)
	resp, err := cs.httpClient.Post(
		"https://api.anti-captcha.com/createTask",
		"application/json",
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		return 0, fmt.Errorf("submit anti-captcha task: %w", err)
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return 0, fmt.Errorf("decode anti-captcha response: %w", err)
	}
	if errorID, ok := result["errorId"].(float64); ok && errorID != 0 {
		return 0, fmt.Errorf("anti-captcha submit failed: %v", result["errorDescription"])
	}
	taskID, ok := result["taskId"].(float64)
	if !ok {
		return 0, fmt.Errorf("anti-captcha returned invalid task id")
	}
	return int(taskID), nil
}

func (cs *CaptchaSolver) pollAntiCaptchaTask(taskID int, field string) (string, error) {
	for i := 0; i < cs.maxPolls; i++ {
		time.Sleep(cs.pollInterval)
		payload := map[string]interface{}{
			"clientKey": cs.apiKey,
			"taskId":    taskID,
		}
		jsonData, _ := json.Marshal(payload)
		resp, err := cs.httpClient.Post(
			"https://api.anti-captcha.com/getTaskResult",
			"application/json",
			bytes.NewBuffer(jsonData),
		)
		if err != nil {
			continue
		}

		var result map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			resp.Body.Close()
			continue
		}
		resp.Body.Close()

		if errorID, ok := result["errorId"].(float64); ok && errorID != 0 {
			return "", fmt.Errorf("anti-captcha poll failed: %v", result["errorDescription"])
		}
		if status, ok := result["status"].(string); ok && status == "ready" {
			if solution, ok := result["solution"].(map[string]interface{}); ok {
				if token, ok := solution[field].(string); ok && token != "" {
					return token, nil
				}
			}
			return "", fmt.Errorf("anti-captcha missing solution token")
		}
	}
	return "", fmt.Errorf("anti-captcha solve timeout")
}
