package ai

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
)

// AIConfig - AI 配置
type AIConfig struct {
	APIKey      string  `json:"api_key"`
	BaseURL     string  `json:"base_url"`
	Model       string  `json:"model"`
	MaxTokens   int     `json:"max_tokens"`
	Temperature float64 `json:"temperature"`
}

// DefaultAIConfig - 默认配置
func DefaultAIConfig() *AIConfig {
	apiKey := os.Getenv("OPENAI_API_KEY")
	if apiKey == "" {
		apiKey = os.Getenv("AI_API_KEY")
	}

	baseURL := os.Getenv("OPENAI_BASE_URL")
	if baseURL == "" {
		baseURL = os.Getenv("AI_BASE_URL")
	}
	if baseURL == "" {
		baseURL = "https://api.openai.com/v1"
	}

	model := os.Getenv("OPENAI_MODEL")
	if model == "" {
		model = os.Getenv("AI_MODEL")
	}
	if model == "" {
		model = "gpt-3.5-turbo"
	}

	maxTokens := 2000
	if raw := strings.TrimSpace(os.Getenv("AI_MAX_TOKENS")); raw != "" {
		if parsed, err := strconv.Atoi(raw); err == nil && parsed > 0 {
			maxTokens = parsed
		}
	}

	temperature := 0.7
	if raw := strings.TrimSpace(os.Getenv("AI_TEMPERATURE")); raw != "" {
		if parsed, err := strconv.ParseFloat(raw, 64); err == nil {
			temperature = parsed
		}
	}

	return &AIConfig{
		APIKey:      apiKey,
		BaseURL:     baseURL,
		Model:       model,
		MaxTokens:   maxTokens,
		Temperature: temperature,
	}
}

// AIExtractor - AI 提取器
type AIExtractor struct {
	config *AIConfig
	client *http.Client
}

// NewAIExtractor - 创建 AI 提取器
func NewAIExtractor(config *AIConfig) *AIExtractor {
	return &AIExtractor{
		config: config,
		client: &http.Client{
			Timeout: 60 * time.Second,
		},
	}
}

// ChatMessage - 聊天消息
type ChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// ChatRequest - 聊天请求
type ChatRequest struct {
	Model       string        `json:"model"`
	Messages    []ChatMessage `json:"messages"`
	MaxTokens   int           `json:"max_tokens"`
	Temperature float64       `json:"temperature"`
}

// ChatResponse - 聊天响应
type ChatResponse struct {
	Choices []struct {
		Message ChatMessage `json:"message"`
	} `json:"choices"`
}

// ExtractStructured - 提取结构化数据
func (e *AIExtractor) ExtractStructured(content, instructions string, schema map[string]interface{}) (map[string]interface{}, error) {
	prompt := fmt.Sprintf(`请从以下内容中提取结构化数据。

提取要求：%s

期望的输出格式（JSON Schema）：
%v

页面内容：
%s

请直接返回符合 JSON Schema 的 JSON 对象，不要包含其他解释。`, instructions, schema, content)

	response, err := e.callLLM(prompt)
	if err != nil {
		return nil, err
	}

	// 尝试解析为 JSON
	var result map[string]interface{}
	if err := json.Unmarshal([]byte(response), &result); err != nil {
		return nil, fmt.Errorf("failed to parse JSON response: %v", err)
	}

	return result, nil
}

// UnderstandPage - 页面理解
func (e *AIExtractor) UnderstandPage(content, question string) (string, error) {
	prompt := fmt.Sprintf(`请分析以下网页内容并回答问题。

问题：%s

页面内容：
%s

请详细回答。`, question, content)

	return e.callLLM(prompt)
}

// GenerateSpiderConfig - 生成爬虫配置
func (e *AIExtractor) GenerateSpiderConfig(description string) (map[string]interface{}, error) {
	prompt := fmt.Sprintf(`根据以下自然语言描述，生成爬虫配置（JSON 格式）。

描述：%s

请返回以下格式的 JSON：
{
    "start_urls": ["起始 URL"],
    "rules": [
        {
            "name": "规则名称",
            "pattern": "URL 匹配模式",
            "extract": ["要提取的字段"],
            "follow_links": true/false
        }
    ],
    "settings": {
        "concurrency": 并发数，
        "max_depth": 最大深度，
        "delay": 请求延迟（毫秒）
    }
}

只返回 JSON，不要其他解释。`, description)

	response, err := e.callLLM(prompt)
	if err != nil {
		return nil, err
	}

	var result map[string]interface{}
	if err := json.Unmarshal([]byte(response), &result); err != nil {
		return nil, fmt.Errorf("failed to parse JSON response: %v", err)
	}

	return result, nil
}

// callLLM - 调用 LLM
func (e *AIExtractor) callLLM(prompt string) (string, error) {
	if e.config.APIKey == "" {
		return "", fmt.Errorf("API key is required")
	}

	requestBody, err := json.Marshal(ChatRequest{
		Model: e.config.Model,
		Messages: []ChatMessage{
			{Role: "user", Content: prompt},
		},
		MaxTokens:   e.config.MaxTokens,
		Temperature: e.config.Temperature,
	})
	if err != nil {
		return "", err
	}

	url := e.config.BaseURL + "/chat/completions"
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(requestBody))
	if err != nil {
		return "", err
	}

	req.Header.Set("Authorization", "Bearer "+e.config.APIKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := e.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("API error: %s - %s", resp.Status, string(body))
	}

	var chatResp ChatResponse
	if err := json.NewDecoder(resp.Body).Decode(&chatResp); err != nil {
		return "", err
	}

	if len(chatResp.Choices) == 0 {
		return "", fmt.Errorf("no response from API")
	}

	return chatResp.Choices[0].Message.Content, nil
}

// SpiderAssistant - 智能爬虫助手
type SpiderAssistant struct {
	extractor *AIExtractor
}

// NewSpiderAssistant - 创建智能爬虫助手
func NewSpiderAssistant(apiKey string) *SpiderAssistant {
	config := &AIConfig{
		APIKey:      apiKey,
		BaseURL:     "https://api.openai.com/v1",
		Model:       "gpt-3.5-turbo",
		MaxTokens:   2000,
		Temperature: 0.7,
	}
	return &SpiderAssistant{
		extractor: NewAIExtractor(config),
	}
}

// PageAnalysis - 页面分析结果
type PageAnalysis struct {
	PageType    string     `json:"page_type"`
	MainContent string     `json:"main_content"`
	Links       []LinkInfo `json:"links"`
	Entities    []Entity   `json:"entities"`
}

// LinkInfo - 链接信息
type LinkInfo struct {
	URL      string `json:"url"`
	Text     string `json:"text"`
	LinkType string `json:"link_type"`
}

// Entity - 实体信息
type Entity struct {
	Name       string `json:"name"`
	EntityType string `json:"entity_type"`
	Value      string `json:"value"`
}

// AnalyzePage - 分析页面
func (a *SpiderAssistant) AnalyzePage(content string) (*PageAnalysis, error) {
	prompt := fmt.Sprintf(`请分析以下网页内容，返回结构化信息。

页面内容：
%s

请返回以下格式的 JSON：
{
    "page_type": "页面类型（如：文章页、列表页、商品页等）",
    "main_content": "主要内容摘要",
    "links": [
        {"url": "链接", "text": "链接文本", "link_type": "链接类型"}
    ],
    "entities": [
        {"name": "实体名", "entity_type": "实体类型", "value": "值"}
    ]
}`, content)

	response, err := a.extractor.callLLM(prompt)
	if err != nil {
		return nil, err
	}

	var analysis PageAnalysis
	if err := json.Unmarshal([]byte(response), &analysis); err != nil {
		return nil, fmt.Errorf("failed to parse JSON response: %v", err)
	}

	return &analysis, nil
}

// ShouldCrawl - 判断是否需要爬取该页面
func (a *SpiderAssistant) ShouldCrawl(content, criteria string) (bool, error) {
	prompt := fmt.Sprintf(`请判断是否应该爬取以下页面。

爬取标准：%s

页面内容：
%s

请只返回 true 或 false。`, criteria, content)

	response, err := a.extractor.callLLM(prompt)
	if err != nil {
		return false, err
	}

	// 简单判断
	response = strings.TrimSpace(response)
	return strings.EqualFold(response, "true") || strings.EqualFold(response, "True"), nil
}

// ExtractFields - 提取指定字段
func (a *SpiderAssistant) ExtractFields(content string, fields []string) (map[string]interface{}, error) {
	fieldsJSON, _ := json.Marshal(fields)

	prompt := fmt.Sprintf(`请从以下内容中提取指定字段。

需要提取的字段：%s

页面内容：
%s

请返回包含这些字段的 JSON 对象。`, string(fieldsJSON), content)

	response, err := a.extractor.callLLM(prompt)
	if err != nil {
		return nil, err
	}

	var result map[string]interface{}
	if err := json.Unmarshal([]byte(response), &result); err != nil {
		return nil, fmt.Errorf("failed to parse JSON response: %v", err)
	}

	return result, nil
}
