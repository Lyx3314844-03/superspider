package core

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// AIProvider AI 提供商
type AIProvider string

const (
	ProviderOpenAI  AIProvider = "openai"
	ProviderOllama  AIProvider = "ollama"
	ProviderCustom  AIProvider = "custom"
)

// AIConfig AI 提取器配置
type AIConfig struct {
	Provider AIProvider
	APIKey   string
	Model    string
	BaseURL  string
	Timeout  time.Duration
}

// DefaultAIConfig 返回默认配置 (OpenAI)
func DefaultAIConfig() AIConfig {
	return AIConfig{
		Provider: ProviderOpenAI,
		Model:    "gpt-4o-mini",
		Timeout:  30 * time.Second,
	}
}

// AIExtractor AI 提取器
type AIExtractor struct {
	config AIConfig
	client *http.Client
}

// NewAIExtractor 创建 AI 提取器
func NewAIExtractor(cfg AIConfig) *AIExtractor {
	if cfg.Timeout == 0 {
		cfg.Timeout = 30 * time.Second
	}
	if cfg.BaseURL == "" {
		switch cfg.Provider {
		case ProviderOpenAI:
			cfg.BaseURL = "https://api.openai.com/v1"
		case ProviderOllama:
			cfg.BaseURL = "http://localhost:11434/v1"
		}
	}

	return &AIExtractor{
		config: cfg,
		client: &http.Client{Timeout: cfg.Timeout},
	}
}

// Extract 从 HTML 提取结构化数据
func (e *AIExtractor) Extract(html, schema string) (map[string]interface{}, error) {
	prompt := fmt.Sprintf(
		"Extract structured data from the following HTML according to this schema:\n\n"+
			"Schema: %s\n\n"+
			"HTML:\n%s\n\n"+
			"Return ONLY valid JSON matching the schema.",
		schema, html,
	)

	return e.callLLM(prompt)
}

// Summarize 总结页面内容
func (e *AIExtractor) Summarize(html string, maxWords int) (map[string]interface{}, error) {
	prompt := fmt.Sprintf(
		"Summarize the following HTML content in %d words or less. Return JSON with 'summary' key.",
		maxWords,
	)

	return e.callLLM(prompt + "\n\n" + html)
}

// ExtractLinks 提取并分类链接
func (e *AIExtractor) ExtractLinks(html string) (map[string]interface{}, error) {
	prompt := fmt.Sprintf(
		"Extract and categorize all links from the following HTML. "+
			"Categorize as: navigation, content, external, internal, media. "+
			"Return JSON object with arrays for each category:\n\n%s",
		html,
	)

	return e.callLLM(prompt)
}

// callLLM 调用 LLM API
func (e *AIExtractor) callLLM(prompt string) (map[string]interface{}, error) {
	body := map[string]interface{}{
		"model": e.config.Model,
		"messages": []map[string]string{
			{"role": "system", "content": "You are a web scraping assistant. Return ONLY valid JSON."},
			{"role": "user", "content": prompt},
		},
		"response_format": map[string]string{"type": "json_object"},
		"temperature":     0.0,
	}

	jsonBody, err := json.Marshal(body)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	req, err := http.NewRequest("POST", e.config.BaseURL+"/chat/completions", bytes.NewReader(jsonBody))
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+e.config.APIKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := e.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("HTTP request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API error %d: %s", resp.StatusCode, string(respBody))
	}

	var aiResp struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&aiResp); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}

	if len(aiResp.Choices) == 0 {
		return nil, fmt.Errorf("no response from AI")
	}

	var result map[string]interface{}
	if err := json.Unmarshal([]byte(aiResp.Choices[0].Message.Content), &result); err != nil {
		return nil, fmt.Errorf("parse AI response JSON: %w", err)
	}

	return result, nil
}
