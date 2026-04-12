package nodereverse

import (
	"gospider/core"
	"log"
)

// NodeReverseMiddleware Node.js逆向中间件
type NodeReverseMiddleware struct {
	Client *NodeReverseClient
}

// NewNodeReverseMiddleware 创建逆向中间件
func NewNodeReverseMiddleware(baseURL string) *NodeReverseMiddleware {
	return &NodeReverseMiddleware{
		Client: NewNodeReverseClient(baseURL),
	}
}

// ProcessRequest 请求中间件 - 自动识别和处理加密参数
func (m *NodeReverseMiddleware) ProcessRequest(req *core.Request) *core.Request {
	// 检查请求中是否包含加密参数
	if req.Headers == nil {
		req.Headers = make(map[string]string)
	}
	
	// 这里可以添加自动解密逻辑
	// 例如：如果检测到加密的参数，先调用逆向服务解密
	
	return req
}

// ProcessResponse 响应中间件 - 分析响应中的加密数据
func (m *NodeReverseMiddleware) ProcessResponse(resp *core.Response) *core.Response {
	// 分析响应内容是否包含加密数据
	content := string(resp.Body)

	// 尝试识别加密类型
	result, err := m.Client.AnalyzeCrypto(content)
	if err != nil {
		log.Printf("NodeReverse: AnalyzeCrypto failed: %v", err)
		return resp
	}

	if result.Success && len(result.CryptoTypes) > 0 {
		// 检测到加密算法，记录日志
		log.Printf("NodeReverse: Detected encryption in response: %v", result.CryptoTypes)

		// 可以在这里添加自动解密逻辑
	}

	return resp
}

// ExtractEncryptedParams 从JS代码中提取加密参数
func (m *NodeReverseMiddleware) ExtractEncryptedParams(jsCode string) (map[string]string, error) {
	result, err := m.Client.AnalyzeCrypto(jsCode)
	if err != nil {
		return nil, err
	}

	params := make(map[string]string)

	// 提取密钥
	for _, key := range result.Keys {
		params["key"] = key
		break // 使用第一个密钥
	}

	// 提取IV
	for _, iv := range result.Ivs {
		params["iv"] = iv
		break // 使用第一个 IV
	}

	return params, nil
}
