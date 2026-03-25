package extractor

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// AIExtractor AI 内容提取器
type AIExtractor struct {
	apiKey     string
	apiURL     string
	model      string
	timeout    time.Duration
	httpClient *http.Client
}

// NewAIExtractor 创建 AI 提取器
func NewAIExtractor(apiKey, apiURL, model string) *AIExtractor {
	return &AIExtractor{
		apiKey:  apiKey,
		apiURL:  apiURL,
		model:   model,
		timeout: 30 * time.Second,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// ExtractResult 提取结果
type ExtractResult struct {
	Data map[string]interface{} `json:"data"`
	Error string `json:"error,omitempty"`
}

// Extract 提取结构化数据
func (e *AIExtractor) Extract(content string, schema map[string]interface{}) (*ExtractResult, error) {
	// 构建请求
	payload := map[string]interface{}{
		"model": e.model,
		"messages": []map[string]string{
			{
				"role": "user",
				"content": "Extract structured data from the following content according to this schema:\n" + content,
			},
		},
	}
	
	jsonData, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}
	
	req, err := http.NewRequest("POST", e.apiURL, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, err
	}
	
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+e.apiKey)
	
	resp, err := e.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	
	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}
	
	// 解析响应
	extractResult := &ExtractResult{
		Data: make(map[string]interface{}),
	}
	
	if choices, ok := result["choices"].([]interface{}); ok && len(choices) > 0 {
		if choice, ok := choices[0].(map[string]interface{}); ok {
			if message, ok := choice["message"].(map[string]interface{}); ok {
				if content, ok := message["content"].(string); ok {
					// 尝试解析为 JSON
					json.Unmarshal([]byte(content), &extractResult.Data)
				}
			}
		}
	}
	
	return extractResult, nil
}

// Summarize 总结内容
func (e *AIExtractor) Summarize(content string, maxLength int) (string, error) {
	payload := map[string]interface{}{
		"model": e.model,
		"messages": []map[string]string{
			{
				"role": "user",
				"content": fmt.Sprintf("Summarize the following content in %d characters:\n%s", maxLength, content),
			},
		},
	}
	
	jsonData, err := json.Marshal(payload)
	if err != nil {
		return "", err
	}
	
	req, err := http.NewRequest("POST", e.apiURL, bytes.NewBuffer(jsonData))
	if err != nil {
		return "", err
	}
	
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+e.apiKey)
	
	resp, err := e.httpClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}
	
	var result map[string]interface{}
	json.Unmarshal(body, &result)
	
	if choices, ok := result["choices"].([]interface{}); ok && len(choices) > 0 {
		if choice, ok := choices[0].(map[string]interface{}); ok {
			if message, ok := choice["message"].(map[string]interface{}); ok {
				if content, ok := message["content"].(string); ok {
					return content, nil
				}
			}
		}
	}
	
	return "", nil
}

// ExtractKeywords 提取关键词
func (e *AIExtractor) ExtractKeywords(content string, maxKeywords int) ([]string, error) {
	_, err := e.Summarize(content, 500)
	if err != nil {
		return nil, err
	}

	// 简单实现，实际应该调用 AI
	keywords := []string{}
	// 这里可以添加关键词提取逻辑

	return keywords, nil
}

// SetTimeout 设置超时
func (e *AIExtractor) SetTimeout(timeout time.Duration) {
	e.timeout = timeout
	e.httpClient.Timeout = timeout
}
