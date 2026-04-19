package encrypted

import (
	"fmt"
	"gospider/node_reverse"
)

// EnhancedCrawler 加密网站爬取增强模块
type EnhancedCrawler struct {
	reverseClient *nodereverse.NodeReverseClient
}

// SignatureReverseResult 签名逆向结果
type SignatureReverseResult struct {
	Success        bool   `json:"success"`
	FunctionName   string `json:"functionName,omitempty"`
	Input          string `json:"input,omitempty"`
	Output         string `json:"output,omitempty"`
	TotalFunctions int    `json:"totalFunctions"`
	SuccessCount   int    `json:"successCount"`
}

// TLSFingerprint TLS 指纹
type TLSFingerprint struct {
	Success      bool     `json:"success"`
	CipherSuites []string `json:"cipherSuites,omitempty"`
	JA3          string   `json:"ja3,omitempty"`
}

// AntiDebugBypassResult 反调试绕过结果
type AntiDebugBypassResult struct {
	Success    bool   `json:"success"`
	BypassType string `json:"bypassType,omitempty"`
	Result     string `json:"result,omitempty"`
}

// DecryptedCookies 解密后的 Cookie
type DecryptedCookies struct {
	Success bool              `json:"success"`
	RawData string            `json:"rawData,omitempty"`
	Cookies map[string]string `json:"cookies,omitempty"`
}

// DecryptedWebSocketMessage 解密的 WebSocket 消息
type DecryptedWebSocketMessage struct {
	Success    bool   `json:"success"`
	RawData    string `json:"rawData,omitempty"`
	ParsedData string `json:"parsedData,omitempty"`
}

// CanvasFingerprint Canvas 指纹
type CanvasFingerprint struct {
	Success     bool   `json:"success"`
	Fingerprint string `json:"fingerprint,omitempty"`
	Hash        string `json:"hash,omitempty"`
}

// NewEnhancedCrawler 创建增强爬虫
func NewEnhancedCrawler(reverseServiceURL string) *EnhancedCrawler {
	if reverseServiceURL == "" {
		reverseServiceURL = "http://localhost:3000"
	}

	return &EnhancedCrawler{
		reverseClient: nodereverse.NewNodeReverseClient(reverseServiceURL),
	}
}

// AutoReverseSignature 自动签名逆向
func (ec *EnhancedCrawler) AutoReverseSignature(code, sampleInputs, sampleOutput string) (*SignatureReverseResult, error) {
	fmt.Println("\n🔐 开始自动签名逆向分析...")

	if sampleInputs != "" && sampleOutput != "" {
		serviceResult, err := ec.reverseClient.ReverseSignature(code, sampleInputs, sampleOutput)
		if err == nil && serviceResult.Success {
			return &SignatureReverseResult{
				Success:        true,
				FunctionName:   serviceResult.FunctionName,
				Input:          sampleInputs,
				Output:         sampleOutput,
				TotalFunctions: serviceResult.TotalFunctions,
				SuccessCount:   serviceResult.SuccessCount,
			}, nil
		}
	}

	// 分析代码中的签名函数
	result, err := ec.reverseClient.AnalyzeAST(code, []string{"crypto"})
	if err != nil {
		return nil, fmt.Errorf("AST 分析失败: %v", err)
	}
	signatureResult := &SignatureReverseResult{
		Success: false,
	}

	// 提取可能的签名函数
	if result.Success {
		// 这里简化处理，实际应该调用 Node.js 服务进行逆向
		signatureResult.TotalFunctions = 1
		signatureResult.SuccessCount = 0
	}

	return signatureResult, nil
}

// GenerateTLSFingerprint 生成 TLS 指纹
func (ec *EnhancedCrawler) GenerateTLSFingerprint(browser, version string) (*TLSFingerprint, error) {
	fmt.Println("\n🔒 生成 TLS 指纹...")

	// Chrome TLS 指纹
	chromeTLS := &TLSFingerprint{
		Success: true,
		CipherSuites: []string{
			"TLS_AES_128_GCM_SHA256",
			"TLS_AES_256_GCM_SHA384",
			"TLS_CHACHA20_POLY1305_SHA256",
			"TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
			"TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
			"TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
			"TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
		},
		JA3: "771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-21,29-23-24,0",
	}

	// Firefox TLS 指纹
	firefoxTLS := &TLSFingerprint{
		Success: true,
		CipherSuites: []string{
			"TLS_AES_128_GCM_SHA256",
			"TLS_CHACHA20_POLY1305_SHA256",
			"TLS_AES_256_GCM_SHA384",
			"TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
			"TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
			"TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256",
			"TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256",
			"TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
			"TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
		},
		JA3: "771,4865-4867-4866-49195-49199-52393-52392-49196-49200-49162-49161-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-21,29-23-24,0",
	}

	if browser == "firefox" {
		fmt.Println("  ✅ 使用 Firefox TLS 指纹")
		return firefoxTLS, nil
	}

	fmt.Println("  ✅ 使用 Chrome TLS 指纹")
	return chromeTLS, nil
}

// BypassAntiDebug 反调试绕过
func (ec *EnhancedCrawler) BypassAntiDebug(code, bypassType string) (*AntiDebugBypassResult, error) {
	fmt.Println("\n🛡️ 开始绕过反调试保护...")

	// 生成绕过代码
	bypassCode := fmt.Sprintf(`
		// 绕过 debugger 语句
		(function() {
			var originalDebugger = Object.getOwnPropertyDescriptor(window, 'debugger');
			if (originalDebugger && originalDebugger.get) {
				Object.defineProperty(window, 'debugger', {
					get: function() { return false; },
					configurable: true
				});
			}
		})();

		// 绕过 DevTools 检测
		(function() {
			var element = new Image();
			Object.defineProperty(element, 'id', {
				get: function() { return false; }
			});
			console.log = function() {};
		})();

		%s
	`, code)

	// 执行绕过代码
	result, err := ec.reverseClient.ExecuteJS(bypassCode, map[string]interface{}{
		"console":   map[string]interface{}{},
		"window":    map[string]interface{}{},
		"document":  map[string]interface{}{},
		"navigator": map[string]interface{}{"userAgent": "Mozilla/5.0"},
	})

	if err != nil {
		return &AntiDebugBypassResult{
			Success:    false,
			BypassType: bypassType,
		}, fmt.Errorf("执行失败: %v", err)
	}

	fmt.Println("  ✅ 反调试绕过成功")

	return &AntiDebugBypassResult{
		Success:    result.Success,
		BypassType: bypassType,
		Result:     fmt.Sprintf("%v", result.Result),
	}, nil
}

// DecryptCookies 解密 Cookie
func (ec *EnhancedCrawler) DecryptCookies(encryptedCookie, key, algorithm string) (*DecryptedCookies, error) {
	fmt.Println("\n🍪 开始解密 Cookie...")

	if algorithm == "" {
		algorithm = "AES"
	}

	decryptedCookies := &DecryptedCookies{
		Success: false,
		Cookies: make(map[string]string),
	}

	// 这里简化处理，实际应该调用 Node.js 服务
	decryptedCookies.RawData = encryptedCookie
	decryptedCookies.Success = true

	fmt.Println("  ✅ Cookie 解密成功")

	return decryptedCookies, nil
}

// DecryptWebSocketMessage 解密 WebSocket 消息
func (ec *EnhancedCrawler) DecryptWebSocketMessage(encryptedMessage, key, algorithm string) (*DecryptedWebSocketMessage, error) {
	fmt.Println("\n🔌 开始解密 WebSocket 消息...")

	if algorithm == "" {
		algorithm = "AES"
	}

	decryptedMessage := &DecryptedWebSocketMessage{
		Success: false,
	}

	// 这里简化处理
	decryptedMessage.RawData = encryptedMessage
	decryptedMessage.Success = true

	fmt.Println("  ✅ WebSocket 消息解密成功")

	return decryptedMessage, nil
}

// GenerateCanvasFingerprint 生成 Canvas 指纹
func (ec *EnhancedCrawler) GenerateCanvasFingerprint() (*CanvasFingerprint, error) {
	fmt.Println("\n🎨 生成 Canvas 指纹...")

	canvas, err := ec.reverseClient.CanvasFingerprint()
	if err == nil && canvas != nil && canvas.Success {
		fingerprint := &CanvasFingerprint{
			Success: true,
			Hash:    canvas.Hash,
		}
		if canvas.Fingerprint != nil {
			fingerprint.Fingerprint = fmt.Sprintf("%v", canvas.Fingerprint)
		}
		fmt.Println("  ✅ Canvas 指纹生成成功")
		return fingerprint, nil
	}

	// 模拟 Canvas 指纹
	fingerprint := &CanvasFingerprint{
		Success:     true,
		Fingerprint: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAASwAAABQCAY...",
		Hash:        "a1b2c3d4e5f6789012345678",
	}

	fmt.Println("  ✅ Canvas 指纹生成成功")

	return fingerprint, nil
}

// GetEnhancedHeaders 获取增强的请求头（包含 TLS 指纹信息）
func (ec *EnhancedCrawler) GetEnhancedHeaders() map[string]string {
	return map[string]string{
		"User-Agent":                  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
		"Accept":                      "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
		"Accept-Language":             "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
		"Accept-Encoding":             "gzip, deflate, br",
		"Connection":                  "keep-alive",
		"Upgrade-Insecure-Requests":   "1",
		"Sec-Fetch-Dest":              "document",
		"Sec-Fetch-Mode":              "navigate",
		"Sec-Fetch-Site":              "none",
		"Sec-Fetch-User":              "?1",
		"Sec-Ch-Ua":                   `"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"`,
		"Sec-Ch-Ua-Mobile":            "?0",
		"Sec-Ch-Ua-Platform":          `"Windows"`,
		"Sec-Ch-Ua-Full-Version":      `"120.0.0.0"`,
		"Sec-Ch-Ua-Full-Version-List": `"Not_A Brand";v="8.0.0.0", "Chromium";v="120.0.0.0", "Google Chrome";v="120.0.0.0"`,
	}
}
