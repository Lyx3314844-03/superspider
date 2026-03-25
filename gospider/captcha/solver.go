package captcha

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"io"
	"net/http"
	"time"
)

// CaptchaSolver 验证码解决器
type CaptchaSolver struct {
	apiKey    string
	service   string
	timeout   time.Duration
	httpClient *http.Client
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
	// 实现 reCAPTCHA 解决
	return &SolveResult{
		Success: false,
		Error:   "Not implemented",
	}, nil
}

// SolveHCaptcha 解决 hCaptcha
func (cs *CaptchaSolver) SolveHCaptcha(siteKey, pageURL string) (*SolveResult, error) {
	// 实现 hCaptcha 解决
	return &SolveResult{
		Success: false,
		Error:   "Not implemented",
	}, nil
}

// ReportBad 报告错误的识别结果
func (cs *CaptchaSolver) ReportBad(taskID string) error {
	// 实现报告错误识别
	return nil
}
