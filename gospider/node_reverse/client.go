package nodereverse

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

const DefaultBaseURL = "http://localhost:3000"

// NodeReverseClient Node.js 逆向服务客户端
type NodeReverseClient struct {
	BaseURL    string
	HTTPClient *http.Client
}

// NewNodeReverseClient 创建新的逆向客户端
func NewNodeReverseClient(baseURL string) *NodeReverseClient {
	if baseURL == "" {
		baseURL = DefaultBaseURL
	}
	return &NodeReverseClient{
		BaseURL: baseURL,
		HTTPClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// CryptoAnalyzeRequest 加密分析请求
type CryptoAnalyzeRequest struct {
	Code string `json:"code"`
}

// CryptoAnalyzeResponse 加密分析响应
type CryptoAnalyzeResponse struct {
	Success     bool `json:"success"`
	CryptoTypes []struct {
		Name       string   `json:"name"`
		Confidence float64  `json:"confidence"`
		Modes      []string `json:"modes"`
	} `json:"cryptoTypes"`
	Keys     []string `json:"keys"`
	Ivs      []string `json:"ivs"`
	Analysis struct {
		HasKeyDerivation bool `json:"hasKeyDerivation"`
		HasRandomIV      bool `json:"hasRandomIV"`
	} `json:"analysis"`
}

// AnalyzeCrypto 分析代码中的加密算法
func (c *NodeReverseClient) AnalyzeCrypto(code string) (*CryptoAnalyzeResponse, error) {
	reqBody := CryptoAnalyzeRequest{Code: code}
	var result CryptoAnalyzeResponse

	err := c.doRequest("/api/crypto/analyze", reqBody, &result)
	if err != nil {
		return nil, err
	}

	return &result, nil
}

// CryptoEncryptRequest 加密请求
type CryptoEncryptRequest struct {
	Algorithm string `json:"algorithm"`
	Data      string `json:"data"`
	Key       string `json:"key"`
	IV        string `json:"iv,omitempty"`
	Mode      string `json:"mode,omitempty"`
}

// CryptoResponse 加密/解密响应
type CryptoResponse struct {
	Success   bool   `json:"success"`
	Encrypted string `json:"encrypted,omitempty"`
	Decrypted string `json:"decrypted,omitempty"`
	Hash      string `json:"hash,omitempty"`
	Error     string `json:"error,omitempty"`
}

// Encrypt 执行加密
func (c *NodeReverseClient) Encrypt(req CryptoEncryptRequest) (*CryptoResponse, error) {
	var result CryptoResponse
	err := c.doRequest("/api/crypto/encrypt", req, &result)
	return &result, err
}

// Decrypt 执行解密
func (c *NodeReverseClient) Decrypt(req CryptoEncryptRequest) (*CryptoResponse, error) {
	var result CryptoResponse
	err := c.doRequest("/api/crypto/decrypt", req, &result)
	return &result, err
}

// ExecuteJSRequest JS 执行请求
type ExecuteJSRequest struct {
	Code    string                 `json:"code"`
	Context map[string]interface{} `json:"context,omitempty"`
	Timeout int                    `json:"timeout,omitempty"`
}

// ExecuteJSResponse JS 执行响应
type ExecuteJSResponse struct {
	Success bool        `json:"success"`
	Result  interface{} `json:"result"`
	Error   string      `json:"error,omitempty"`
}

// ExecuteJS 执行 JavaScript 代码
func (c *NodeReverseClient) ExecuteJS(code string, context map[string]interface{}) (*ExecuteJSResponse, error) {
	req := ExecuteJSRequest{
		Code:    code,
		Context: context,
		Timeout: 5000,
	}

	var result ExecuteJSResponse
	err := c.doRequest("/api/js/execute", req, &result)
	return &result, err
}

// ASTAnalyzeRequest AST 分析请求
type ASTAnalyzeRequest struct {
	Code     string   `json:"code"`
	Analysis []string `json:"analysis,omitempty"`
}

// ASTAnalyzeResponse AST 分析响应
type ASTAnalyzeResponse struct {
	Success bool `json:"success"`
	Results struct {
		Crypto      []map[string]interface{} `json:"crypto"`
		Obfuscation []map[string]interface{} `json:"obfuscation"`
		AntiDebug   []map[string]interface{} `json:"antiDebug"`
		Functions   []map[string]interface{} `json:"functions"`
	} `json:"results"`
}

// AnalyzeAST 分析 AST
func (c *NodeReverseClient) AnalyzeAST(code string, analysisTypes []string) (*ASTAnalyzeResponse, error) {
	req := ASTAnalyzeRequest{
		Code:     code,
		Analysis: analysisTypes,
	}

	var result ASTAnalyzeResponse
	err := c.doRequest("/api/ast/analyze", req, &result)
	return &result, err
}

// BrowserSimulateRequest 浏览器模拟请求
type BrowserSimulateRequest struct {
	Code          string            `json:"code"`
	BrowserConfig map[string]string `json:"browserConfig,omitempty"`
}

// BrowserSimulateResponse 浏览器模拟响应
type BrowserSimulateResponse struct {
	Success bool        `json:"success"`
	Result  interface{} `json:"result"`
	Cookies string      `json:"cookies"`
	Error   string      `json:"error,omitempty"`
}

// SimulateBrowser 模拟浏览器环境
func (c *NodeReverseClient) SimulateBrowser(code string, config map[string]string) (*BrowserSimulateResponse, error) {
	req := BrowserSimulateRequest{
		Code:          code,
		BrowserConfig: config,
	}

	var result BrowserSimulateResponse
	err := c.doRequest("/api/browser/simulate", req, &result)
	return &result, err
}

// FunctionCallRequest 函数调用请求
type FunctionCallRequest struct {
	FunctionName string        `json:"functionName"`
	Args         []interface{} `json:"args"`
	Code         string        `json:"code"`
}

// FunctionCallResponse 函数调用响应
type FunctionCallResponse struct {
	Success bool        `json:"success"`
	Result  interface{} `json:"result"`
	Error   string      `json:"error,omitempty"`
}

// AntiBotProfileRequest 反爬检测/画像请求
type AntiBotProfileRequest struct {
	HTML       string                 `json:"html,omitempty"`
	JS         string                 `json:"js,omitempty"`
	Headers    map[string]interface{} `json:"headers,omitempty"`
	Cookies    string                 `json:"cookies,omitempty"`
	StatusCode int                    `json:"statusCode,omitempty"`
	URL        string                 `json:"url,omitempty"`
}

// AntiBotProfileResponse 反爬检测/画像响应
type AntiBotProfileResponse struct {
	Success          bool                     `json:"success"`
	Detection        map[string]bool          `json:"detection,omitempty"`
	Vendors          []map[string]interface{} `json:"vendors,omitempty"`
	Challenges       []map[string]interface{} `json:"challenges,omitempty"`
	Signals          []string                 `json:"signals,omitempty"`
	Score            int                      `json:"score,omitempty"`
	Level            string                   `json:"level,omitempty"`
	Recommendations  []string                 `json:"recommendations,omitempty"`
	RequestBlueprint map[string]interface{}   `json:"requestBlueprint,omitempty"`
	MitigationPlan   map[string]interface{}   `json:"mitigationPlan,omitempty"`
	Error            string                   `json:"error,omitempty"`
}

type FingerprintSpoofRequest struct {
	Browser  string `json:"browser,omitempty"`
	Platform string `json:"platform,omitempty"`
}

type FingerprintSpoofResponse struct {
	Success     bool                   `json:"success"`
	Fingerprint map[string]interface{} `json:"fingerprint,omitempty"`
	Browser     string                 `json:"browser,omitempty"`
	Platform    string                 `json:"platform,omitempty"`
	Error       string                 `json:"error,omitempty"`
}

type TLSFingerprintRequest struct {
	Browser string `json:"browser,omitempty"`
	Version string `json:"version,omitempty"`
}

type TLSFingerprintResponse struct {
	Success     bool                   `json:"success"`
	Fingerprint map[string]interface{} `json:"fingerprint,omitempty"`
	Browser     string                 `json:"browser,omitempty"`
	Version     string                 `json:"version,omitempty"`
	Error       string                 `json:"error,omitempty"`
}

// CallFunction 调用 JavaScript 函数
func (c *NodeReverseClient) CallFunction(functionName string, args []interface{}, code string) (*FunctionCallResponse, error) {
	req := FunctionCallRequest{
		FunctionName: functionName,
		Args:         args,
		Code:         code,
	}

	var result FunctionCallResponse
	err := c.doRequest("/api/function/call", req, &result)
	return &result, err
}

// DetectAntiBot 检测页面中的反爬特征
func (c *NodeReverseClient) DetectAntiBot(req AntiBotProfileRequest) (*AntiBotProfileResponse, error) {
	var result AntiBotProfileResponse
	err := c.doRequest("/api/anti-bot/detect", req, &result)
	return &result, err
}

// ProfileAntiBot 生成完整的反爬画像与规避计划
func (c *NodeReverseClient) ProfileAntiBot(req AntiBotProfileRequest) (*AntiBotProfileResponse, error) {
	var result AntiBotProfileResponse
	err := c.doRequest("/api/anti-bot/profile", req, &result)
	return &result, err
}

func (c *NodeReverseClient) SpoofFingerprint(req FingerprintSpoofRequest) (*FingerprintSpoofResponse, error) {
	var result FingerprintSpoofResponse
	err := c.doRequest("/api/fingerprint/spoof", req, &result)
	return &result, err
}

func (c *NodeReverseClient) GenerateTLSFingerprint(req TLSFingerprintRequest) (*TLSFingerprintResponse, error) {
	var result TLSFingerprintResponse
	err := c.doRequest("/api/tls/fingerprint", req, &result)
	return &result, err
}

// HealthCheck 健康检查
func (c *NodeReverseClient) HealthCheck() (bool, error) {
	resp, err := c.HTTPClient.Get(c.BaseURL + "/health")
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()

	return resp.StatusCode == 200, nil
}

// doRequest 执行 HTTP 请求
func (c *NodeReverseClient) doRequest(path string, reqBody interface{}, result interface{}) error {
	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return fmt.Errorf("JSON 序列化失败: %v", err)
	}

	req, err := http.NewRequest("POST", c.BaseURL+path, bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("创建请求失败: %v", err)
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return fmt.Errorf("请求失败: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return fmt.Errorf("服务器返回错误状态码: %d", resp.StatusCode)
	}

	if err := json.NewDecoder(resp.Body).Decode(result); err != nil {
		return fmt.Errorf("JSON 解析失败: %v", err)
	}

	return nil
}
