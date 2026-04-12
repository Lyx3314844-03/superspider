package main

import (
	"fmt"
	"gospider/node_reverse"
)

// GoSpider 集成 Node.js 逆向服务示例
func main() {
	// 创建逆向客户端
	client := nodereverse.NewNodeReverseClient("http://localhost:3000")

	// 健康检查
	healthy, err := client.HealthCheck()
	if err != nil {
		fmt.Printf("健康检查失败: %v\n", err)
		return
	}
	fmt.Printf("服务健康状态: %v\n", healthy)

	// 示例1: 分析加密算法
	code := `
		var key = 'mysecretkey12345';
		var iv = 'myiv123456789012';
		var encrypted = CryptoJS.AES.encrypt(data, key, { iv: iv });
		var hash = CryptoJS.MD5(password);
	`

	cryptoResult, err := client.AnalyzeCrypto(code)
	if err != nil {
		fmt.Printf("加密分析失败: %v\n", err)
		return
	}

	fmt.Printf("\n加密分析结果:\n")
	fmt.Printf("  成功: %v\n", cryptoResult.Success)
	fmt.Printf("  识别的加密类型:\n")
	for _, crypto := range cryptoResult.CryptoTypes {
		fmt.Printf("    - %s (置信度: %.2f)\n", crypto.Name, crypto.Confidence)
	}
	if len(cryptoResult.Keys) > 0 {
		fmt.Printf("  检测到的密钥: %v\n", cryptoResult.Keys)
	}
	if len(cryptoResult.Ivs) > 0 {
		fmt.Printf("  检测到的 IV: %v\n", cryptoResult.Ivs)
	}

	// 示例2: 执行加密
	encryptReq := nodereverse.CryptoEncryptRequest{
		Algorithm: "AES",
		Data:      "Hello from GoSpider!",
		Key:       "mysecretkey12345",
		IV:        "myiv123456789012",
		Mode:      "CBC",
	}

	encryptResult, err := client.Encrypt(encryptReq)
	if err != nil {
		fmt.Printf("加密失败: %v\n", err)
		return
	}

	fmt.Printf("\n加密结果:\n")
	if encryptResult.Encrypted != "" {
		fmt.Printf("  加密数据: %s...\n", encryptResult.Encrypted[:min(50, len(encryptResult.Encrypted))])
	}

	// 示例3: 执行解密
	decryptReq := nodereverse.CryptoEncryptRequest{
		Algorithm: "AES",
		Data:      encryptResult.Encrypted,
		Key:       "mysecretkey12345",
		IV:        "myiv123456789012",
		Mode:      "CBC",
	}

	decryptResult, err := client.Decrypt(decryptReq)
	if err != nil {
		fmt.Printf("解密失败: %v\n", err)
		return
	}

	fmt.Printf("\n解密结果:\n")
	fmt.Printf("  解密数据: %s\n", decryptResult.Decrypted)

	// 示例4: AST 分析
	jsCode := `
		function encrypt(data, key) {
			return CryptoJS.AES.encrypt(data, key).toString();
		}

		function decrypt(data, key) {
			return CryptoJS.AES.decrypt(data, key).toString(CryptoJS.enc.Utf8);
		}
	`

	astResult, err := client.AnalyzeAST(jsCode, []string{"crypto", "obfuscation", "anti-debug"})
	if err != nil {
		fmt.Printf("AST分析失败: %v\n", err)
		return
	}

	fmt.Printf("\nAST 分析结果:\n")
	fmt.Printf("  成功: %v\n", astResult.Success)

	fmt.Printf("\n✅ GoSpider 集成 Node.js 逆向服务示例完成！\n")
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
