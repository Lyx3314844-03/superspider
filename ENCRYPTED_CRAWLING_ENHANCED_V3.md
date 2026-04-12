# 🔐 加密网站爬取增强功能指南 v3.0

## 📋 概述

四个爬虫框架现已全面升级！新增强大的加密网站爬取增强功能，通过集成 Node.js 逆向服务 v3.0，现在可以轻松应对：

### ✨ v3.0 新增功能

| 功能 | 说明 | 适用场景 |
|------|------|---------|
| **自动签名逆向** | 自动分析并还原网站签名算法 | 逆向 API 签名 |
| **动态参数解密** | 解密动态生成的请求参数 | 解密加密参数 |
| **TLS 指纹伪造** | 生成真实浏览器 TLS 指纹 | 绕过 TLS 指纹检测 |
| **反调试绕过** | 绕过 debugger/反调试保护 | 执行反调试代码 |
| **Cookie 加密处理** | 解密加密的 Cookie | 处理加密 Cookie |
| **WebSocket 消息加解密** | 处理 WebSocket 加密消息 | 解密 WS 通信 |
| **Canvas 指纹生成** | 生成 Canvas 浏览器指纹 | 绕过 Canvas 指纹检测 |

---

## 🚀 快速开始

### 步骤 1: 启动增强版 Node.js 逆向服务

```bash
cd C:\Users\Administrator\spider\node-reverse-server
node server-enhanced.js
```

**预期输出**:
```
╔══════════════════════════════════════════════════════════╗
║          Node.js Reverse Engineering Service             ║
║                    Version 3.0.0-Enhanced                ║
╠══════════════════════════════════════════════════════════╣
║  Server running on: http://localhost:3000               ║
║                                                          ║
║  🆕 v3.0 新增功能:                                       ║
║  • POST /api/signature/auto-reverse - 自动签名逆向      ║
║  • POST /api/param/decrypt       - 动态参数解密         ║
║  • POST /api/tls/fingerprint     - TLS指纹生成          ║
║  • POST /api/anti-debug/bypass   - 反调试绕过           ║
║  • POST /api/cookie/decrypt        - Cookie加密处理     ║
║  • POST /api/websocket/decrypt     - WebSocket消息解密  ║
║  • POST /api/canvas/fingerprint  - Canvas指纹生成       ║
╚══════════════════════════════════════════════════════════╝
```

### 步骤 2: 验证服务

```bash
curl http://localhost:3000/health
```

---

## 🎯 各框架使用方法

### 1. Java Spider 增强功能

#### 创建增强爬虫实例

```java
import com.javaspider.encrypted.EncryptedSiteCrawlerEnhanced;
import com.javaspider.encrypted.EncryptedSiteCrawlerEnhanced.*;

public class EnhancedExample {
    public static void main(String[] args) throws Exception {
        // 创建增强爬虫
        EncryptedSiteCrawlerEnhanced crawler = new EncryptedSiteCrawlerEnhanced();
        
        // 1. 自动签名逆向
        SignatureReverseResult sigResult = crawler.autoReverseSignature(
            "function sign(data) { return md5(data + 'secret'); }",
            "test_data",
            "expected_output"
        );
        System.out.println("签名函数: " + sigResult.functionName);
        
        // 2. TLS 指纹生成
        TLSFingerprint tlsFP = crawler.generateTLSFingerprint("chrome", "120");
        System.out.println("JA3 指纹: " + tlsFP.ja3);
        
        // 3. 反调试绕过
        AntiDebugBypassResult bypassResult = crawler.bypassAntiDebug(
            "debugger; console.log('test');",
            "all"
        );
        System.out.println("绕过成功: " + bypassResult.success);
        
        // 4. Cookie 解密
        DecryptedCookies cookies = crawler.decryptCookie(
            "encrypted_cookie_base64",
            "mysecretkey12345",
            "AES"
        );
        System.out.println("解密 Cookie 数量: " + cookies.cookies.size());
        
        // 5. WebSocket 消息解密
        DecryptedWebSocketMessage wsMsg = crawler.decryptWebSocketMessage(
            "encrypted_ws_message",
            "mysecretkey12345",
            "AES"
        );
        System.out.println("WS 消息解密成功: " + wsMsg.success);
        
        // 6. Canvas 指纹生成
        CanvasFingerprint canvasFP = crawler.generateCanvasFingerprint();
        System.out.println("Canvas Hash: " + canvasFP.hash);
    }
}
```

#### 完整示例 - 爬取加密 API

```java
import com.javaspider.encrypted.EncryptedSiteCrawlerEnhanced;

public class EncryptedAPICrawler {
    public static void main(String[] args) throws Exception {
        EncryptedSiteCrawlerEnhanced crawler = new EncryptedSiteCrawlerEnhanced();
        
        // 步骤 1: 逆向签名算法
        String apiCode = "function generateSign(params) { return md5(params + secret); }";
        SignatureReverseResult sigResult = crawler.autoReverseSignature(
            apiCode, "param1=value1", "abc123"
        );
        
        if (sigResult.success) {
            System.out.println("✅ 找到签名函数: " + sigResult.functionName);
        }
        
        // 步骤 2: 生成 TLS 指纹
        TLSFingerprint tlsFP = crawler.generateTLSFingerprint("chrome", "120");
        System.out.println("✅ TLS 指纹: " + tlsFP.ja3);
        
        // 步骤 3: 生成请求头
        Map<String, String> headers = crawler.getEnhancedHeaders();
        
        // 步骤 4: 发送请求
        // 使用生成的指纹和请求头访问加密 API
    }
}
```

---

### 2. Go Spider 增强功能

#### 使用增强爬虫

```go
package main

import (
    "fmt"
    "gospider/encrypted"
)

func main() {
    // 创建增强爬虫
    crawler := encrypted.NewEnhancedCrawler("http://localhost:3000")
    
    // 1. 自动签名逆向
    sigResult, _ := crawler.AutoReverseSignature(
        "function sign(data) { return md5(data + 'secret'); }",
        "test_data",
        "expected_output",
    )
    fmt.Printf("签名函数: %s\n", sigResult.FunctionName)
    
    // 2. TLS 指纹生成
    tlsFP, _ := crawler.GenerateTLSFingerprint("chrome", "120")
    fmt.Printf("JA3 指纹: %s\n", tlsFP.JA3)
    
    // 3. 反调试绕过
    bypassResult, _ := crawler.BypassAntiDebug(
        "debugger; console.log('test');",
        "all",
    )
    fmt.Printf("绕过成功: %v\n", bypassResult.Success)
    
    // 4. Cookie 解密
    cookies, _ := crawler.DecryptCookies(
        "encrypted_cookie_base64",
        "mysecretkey12345",
        "AES",
    )
    fmt.Printf("解密 Cookie 数量: %d\n", len(cookies.Cookies))
    
    // 5. Canvas 指纹生成
    canvasFP, _ := crawler.GenerateCanvasFingerprint()
    fmt.Printf("Canvas Hash: %s\n", canvasFP.Hash)
    
    // 6. 获取增强请求头
    headers := crawler.GetEnhancedHeaders()
    fmt.Printf("请求头数量: %d\n", len(headers))
}
```

---

### 3. Python Spider 增强功能

#### 使用增强爬虫

```python
from pyspider.encrypted import EncryptedSiteCrawlerEnhanced

# 创建增强爬虫
crawler = EncryptedSiteCrawlerEnhanced("http://localhost:3000")

# 1. 自动签名逆向
sig_result = crawler.auto_reverse_signature(
    "function sign(data) { return md5(data + 'secret'); }",
    "test_data",
    "expected_output"
)
print(f"签名函数: {sig_result.get('function_name')}")

# 2. TLS 指纹生成
tls_fp = crawler.generate_tls_fingerprint("chrome", "120")
print(f"JA3 指纹: {tls_fp['ja3']}")

# 3. 反调试绕过
bypass_result = crawler.bypass_anti_debug(
    "debugger; console.log('test');",
    "all"
)
print(f"绕过成功: {bypass_result.get('success')}")

# 4. Cookie 解密
cookies = crawler.decrypt_cookies(
    "encrypted_cookie_base64",
    "mysecretkey12345",
    "AES"
)
print(f"解密 Cookie 数量: {len(cookies.get('cookies', {}))}")

# 5. WebSocket 消息解密
ws_msg = crawler.decrypt_websocket_message(
    "encrypted_ws_message",
    "mysecretkey12345",
    "AES"
)
print(f"WS 消息解密成功: {ws_msg.get('success')}")

# 6. Canvas 指纹生成
canvas_fp = crawler.generate_canvas_fingerprint()
print(f"Canvas Hash: {canvas_fp['hash']}")

# 7. 获取增强请求头
headers = crawler.get_enhanced_headers()
print(f"请求头数量: {len(headers)}")
```

---

### 4. Rust Spider 增强功能

#### 使用增强爬虫

```rust
use rustspider::encrypted::EncryptedSiteCrawlerEnhanced;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 创建增强爬虫
    let crawler = EncryptedSiteCrawlerEnhanced::new("http://localhost:3000");
    
    // 1. 自动签名逆向
    let sig_result = crawler.auto_reverse_signature(
        "function sign(data) { return md5(data + 'secret'); }",
        Some("test_data"),
        Some("expected_output"),
    ).await?;
    
    println!("签名函数: {:?}", sig_result.function_name);
    
    // 2. TLS 指纹生成
    let tls_fp = crawler.generate_tls_fingerprint("chrome", "120").await?;
    println!("JA3 指纹: {}", tls_fp.ja3);
    
    // 3. 反调试绕过
    let bypass_result = crawler.bypass_anti_debug(
        "debugger; console.log('test');",
        "all",
    ).await?;
    
    println!("绕过成功: {}", bypass_result.success);
    
    // 4. Cookie 解密
    let cookies = crawler.decrypt_cookies(
        "encrypted_cookie_base64",
        "mysecretkey12345",
        "AES",
    ).await?;
    
    println!("解密 Cookie 数量: {}", cookies.cookies.len());
    
    // 5. Canvas 指纹生成
    let canvas_fp = crawler.generate_canvas_fingerprint().await?;
    println!("Canvas Hash: {}", canvas_fp.hash);
    
    // 6. 获取增强请求头
    let headers = EncryptedSiteCrawlerEnhanced::get_enhanced_headers();
    println!("请求头数量: {}", headers.len());
    
    Ok(())
}
```

---

## 📊 功能对比

| 功能 | Java | Go | Python | Rust |
|------|------|----|--------|------|
| 自动签名逆向 | ✅ | ✅ | ✅ | ✅ |
| TLS 指纹伪造 | ✅ | ✅ | ✅ | ✅ |
| 反调试绕过 | ✅ | ✅ | ✅ | ✅ |
| Cookie 解密 | ✅ | ✅ | ✅ | ✅ |
| WebSocket 解密 | ✅ | ✅ | ✅ | ✅ |
| Canvas 指纹 | ✅ | ✅ | ✅ | ✅ |
| 增强请求头 | ✅ | ✅ | ✅ | ✅ |
| 异步支持 | ⚠️ | ✅ | ✅ | ✅ |

---

## 🎯 实战案例

### 案例 1: 逆向电商网站签名

```python
from pyspider.encrypted import EncryptedSiteCrawlerEnhanced

crawler = EncryptedSiteCrawlerEnhanced()

# 网站的签名代码
sign_code = """
function generateSign(params, secret) {
    var sorted = Object.keys(params).sort();
    var str = sorted.map(k => k + '=' + params[k]).join('&');
    return CryptoJS.MD5(str + secret).toString();
}
"""

# 自动逆向签名
result = crawler.auto_reverse_signature(
    sign_code,
    "item_id=123&qty=1",
    "5d41402abc4b2a76b9719d911017c592"
)

if result['success']:
    print(f"✅ 找到签名函数: {result['function_name']}")
    
    # 生成请求
    headers = crawler.get_enhanced_headers()
    # 使用逆向的签名函数生成签名
    # 发送请求...
```

### 案例 2: 绕过反调试保护

```go
package main

import (
    "fmt"
    "gospider/encrypted"
)

func main() {
    crawler := encrypted.NewEnhancedCrawler("")
    
    // 网站的反调试代码
    antiDebugCode := `
        debugger;
        (function() {
            var start = Date.now();
            while(Date.now() - start < 1000) {}
        })();
        console.log('正常代码');
    `
    
    // 绕过反调试
    result, _ := crawler.BypassAntiDebug(antiDebugCode, "all")
    
    if result.Success {
        fmt.Println("✅ 反调试绕过成功")
        fmt.Println("结果:", result.Result)
    }
}
```

### 案例 3: TLS 指纹伪造

```java
import com.javaspider.encrypted.EncryptedSiteCrawlerEnhanced;

public class TLSFingerprintExample {
    public static void main(String[] args) throws Exception {
        EncryptedSiteCrawlerEnhanced crawler = new EncryptedSiteCrawlerEnhanced();
        
        // 生成 Chrome TLS 指纹
        TLSFingerprint chromeFP = crawler.generateTLSFingerprint("chrome", "120");
        
        System.out.println("Chrome TLS 指纹:");
        System.out.println("  JA3: " + chromeFP.ja3);
        System.out.println("  加密套件数量: " + chromeFP.cipherSuites.size());
        
        // 生成 Firefox TLS 指纹
        TLSFingerprint firefoxFP = crawler.generateTLSFingerprint("firefox", "120");
        
        System.out.println("\nFirefox TLS 指纹:");
        System.out.println("  JA3: " + firefoxFP.ja3);
        
        // 使用指纹配置 HTTP 客户端
        // ...
    }
}
```

### 案例 4: WebSocket 消息解密

```rust
use rustspider::encrypted::EncryptedSiteCrawlerEnhanced;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let crawler = EncryptedSiteCrawlerEnhanced::default();
    
    // 加密的 WebSocket 消息
    let encrypted_ws = "U2FsdGVkX1+...";
    
    // 解密消息
    let decrypted = crawler.decrypt_websocket_message(
        encrypted_ws,
        "websocket_secret_key",
        "AES",
    ).await?;
    
    if decrypted.success {
        println!("✅ WebSocket 消息解密成功");
        println!("原始数据: {}", decrypted.raw_data);
        
        if let Some(parsed) = decrypted.parsed_data {
            println!("解析数据: {}", parsed);
        }
    }
    
    Ok(())
}
```

---

## 🔧 API 参考

### Node.js 逆向服务 v3.0

| API | 方法 | 说明 | 版本 |
|-----|------|------|------|
| `/api/crypto/analyze` | POST | 分析加密算法 | v2.0 |
| `/api/crypto/encrypt` | POST | 加密 | v2.0 |
| `/api/crypto/decrypt` | POST | 解密 | v2.0 |
| `/api/js/execute` | POST | 执行 JS | v2.0 |
| `/api/ast/analyze` | POST | AST 分析 | v2.0 |
| `/api/browser/simulate` | POST | 浏览器模拟 | v2.0 |
| `/api/signature/auto-reverse` | POST | 自动签名逆向 | **v3.0** |
| `/api/param/decrypt` | POST | 动态参数解密 | **v3.0** |
| `/api/tls/fingerprint` | POST | TLS 指纹生成 | **v3.0** |
| `/api/anti-debug/bypass` | POST | 反调试绕过 | **v3.0** |
| `/api/cookie/decrypt` | POST | Cookie 加密处理 | **v3.0** |
| `/api/websocket/decrypt` | POST | WebSocket 消息解密 | **v3.0** |
| `/api/canvas/fingerprint` | POST | Canvas 指纹生成 | **v3.0** |

---

## 🐛 常见问题

### Q1: 签名逆向失败
- 确保代码包含完整的函数定义
- 提供正确的样本输入输出用于验证
- 检查函数名是否包含 sign/signature/encrypt 等关键字

### Q2: TLS 指纹不匹配
- 确认浏览器版本是否正确
- 检查加密套件列表是否完整
- 使用 JA3 指纹验证工具比对

### Q3: 反调试绕过失败
- 增加超时时间到 10 秒
- 检查代码语法是否正确
- 确保沙箱环境配置正确

---

## ⚠️ 注意事项

1. **遵守 robots.txt**
2. **尊重网站服务条款**
3. **不要过度频繁请求**
4. **仅用于学习和合法用途**
5. **确保有权限爬取目标网站**
6. **不要用于恶意目的**

---

## 🎊 总结

现在四个爬虫框架都具备了最强大的加密网站爬取能力：

✅ **自动签名逆向** - 一键还原网站签名算法  
✅ **TLS 指纹伪造** - 完美模拟真实浏览器  
✅ **反调试绕过** - 轻松执行混淆代码  
✅ **Cookie 解密** - 处理加密的 Cookie  
✅ **WebSocket 解密** - 解密加密通信  
✅ **Canvas 指纹** - 生成浏览器指纹  
✅ **增强请求头** - 完整的浏览器特征  

**开始爬取最加密的网站吧！** 🚀
