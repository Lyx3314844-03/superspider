# 🕷️ Node.js 逆向工程统一服务

为四个爬虫框架 (Rust/Java/Go/Python) 提供统一的逆向工程能力。

当前推荐的反爬入口：

- `POST /api/anti-bot/profile`
- `POST /api/anti-bot/detect`
- `POST /api/fingerprint/spoof`
- `POST /api/tls/fingerprint`

## 🚀 快速启动

```bash
cd C:\Users\Administrator\spider\node-reverse-server
npm install
npm start
```

服务将在 `http://localhost:3000` 启动。

---

## 📡 API 接口文档

### 1. 加密算法分析
**POST** `/api/crypto/analyze`

分析 JavaScript 代码中使用的加密算法。

**请求体**:
```json
{
  "code": "var encrypted = CryptoJS.AES.encrypt(data, key, { iv: iv });"
}
```

**响应**:
```json
{
  "success": true,
  "cryptoTypes": [
    {
      "name": "AES",
      "confidence": 0.95,
      "modes": ["ECB", "CBC", "CFB", "OFB", "GCM"]
    }
  ],
  "keys": ["mysecretkey12345"],
  "ivs": ["myiv123456789012"],
  "analysis": {
    "hasKeyDerivation": false,
    "hasRandomIV": false,
    "complexity": "medium"
  }
}
```

---

### 2. 加密操作
**POST** `/api/crypto/encrypt`

执行加密操作。

**请求体**:
```json
{
  "algorithm": "AES",
  "data": "Hello World",
  "key": "mysecretkey12345",
  "iv": "myiv123456789012",
  "mode": "CBC"
}
```

**响应**:
```json
{
  "success": true,
  "encrypted": "U2FsdGVkX1+..."
}
```

---

### 3. 解密操作
**POST** `/api/crypto/decrypt`

执行解密操作。

**请求体**:
```json
{
  "algorithm": "AES",
  "data": "U2FsdGVkX1+...",
  "key": "mysecretkey12345",
  "iv": "myiv123456789012",
  "mode": "CBC"
}
```

**响应**:
```json
{
  "success": true,
  "decrypted": "Hello World"
}
```

---

### 4. JavaScript 代码执行
**POST** `/api/js/execute`

在沙箱环境中执行 JavaScript 代码。

**请求体**:
```json
{
  "code": "function sign(data) { return md5(data + 'secret'); } sign('hello');",
  "context": { "md5": "function(s){ return s; }" },
  "timeout": 5000
}
```

**响应**:
```json
{
  "success": true,
  "result": "hellosecret"
}
```

---

### 5. AST 语法分析
**POST** `/api/ast/analyze`

分析 JavaScript 代码的抽象语法树。

**请求体**:
```json
{
  "code": "function encrypt(data) { return CryptoJS.AES.encrypt(data, key); }",
  "analysis": ["crypto", "obfuscation", "anti-debug"]
}
```

**响应**:
```json
{
  "success": true,
  "results": {
    "crypto": [
      {
        "type": "crypto-call",
        "name": "encrypt",
        "line": 1
      }
    ],
    "functions": [
      {
        "name": "encrypt",
        "params": 1,
        "line": 1
      }
    ],
    "antiDebug": []
  }
}
```

---

### 6. Webpack 打包分析
**POST** `/api/webpack/analyze`

分析 Webpack 打包的代码。

**请求体**:
```json
{
  "code": "(function(modules){...})({0: function(...){...}, 1: function(...){...}})"
}
```

**响应**:
```json
{
  "success": true,
  "modules": [
    {
      "id": "0",
      "contentPreview": "function(...){...}"
    }
  ],
  "totalModules": 2,
  "isWebpack": true
}
```

---

### 7. 函数调用模拟
**POST** `/api/function/call`

模拟调用 JavaScript 函数。

**请求体**:
```json
{
  "functionName": "encrypt",
  "args": ["data", "key"],
  "code": "function encrypt(data, key) { return CryptoJS.AES.encrypt(data, key).toString(); }"
}
```

**响应**:
```json
{
  "success": true,
  "result": "U2FsdGVkX1+..."
}
```

---

### 8. 反爬画像与规避计划
**POST** `/api/anti-bot/profile`

把页面线索、响应头、Cookie、状态码收敛成完整的反爬画像。

**请求体**:
```json
{
  "url": "https://target.example/challenge",
  "statusCode": 429,
  "html": "<title>Just a moment...</title>",
  "js": "eval(function(p,a,c,k,e,d){return p;});",
  "headers": {
    "cf-ray": "1234",
    "retry-after": "10"
  },
  "cookies": "__cf_bm=token"
}
```

**响应重点**:
```json
{
  "success": true,
  "vendors": [{ "name": "Cloudflare" }],
  "signals": ["managed-browser-challenge", "javascript-challenge"],
  "requestBlueprint": {
    "headers": { "User-Agent": "..." },
    "tls": { "ja3": "..." }
  }
}
```

---

### 8. 浏览器环境模拟
**POST** `/api/browser/simulate`

在模拟的浏览器环境中执行代码。

**请求体**:
```json
{
  "code": "document.cookie = 'session=abc123'; return navigator.userAgent;",
  "browserConfig": {
    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "language": "zh-CN",
    "platform": "Win32"
  }
}
```

**响应**:
```json
{
  "success": true,
  "result": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
  "cookies": "session=abc123"
}
```

---

### 9. 签名算法逆向
**POST** `/api/signature/reverse`

逆向分析签名算法。

**请求体**:
```json
{
  "code": "function sign(data) { return md5(data + timestamp + 'secret'); }",
  "input": "hello",
  "expectedOutput": "5d41402abc4b2a76b9719d911017c592"
}
```

**响应**:
```json
{
  "success": true,
  "signature": "5d41402abc4b2a76b9719d911017c592",
  "matches": true
}
```

---

## 🔌 各框架集成方式

### Java Spider
```java
NodeReverseClient client = new NodeReverseClient("http://localhost:3000");

// 分析加密
JsonNode result = client.analyzeCrypto("var enc = CryptoJS.AES.encrypt(data, key);");

// 执行解密
JsonNode decrypted = client.decrypt("AES", encryptedData, key, iv, "CBC");
```

### Go Spider
```go
client := nodereverse.NewNodeReverseClient("http://localhost:3000")

// 分析加密
result, _ := client.AnalyzeCrypto(code)

// 执行加密
encryptReq := nodereverse.CryptoEncryptRequest{
    Algorithm: "AES",
    Data:      "Hello",
    Key:       "key123",
    IV:        "iv123",
    Mode:      "CBC",
}
encryptResult, _ := client.Encrypt(encryptReq)
```

### Python Spider
```python
from pyspider.node_reverse.client import NodeReverseClient

client = NodeReverseClient("http://localhost:3000")

# 分析加密
result = client.analyze_crypto("var enc = CryptoJS.AES.encrypt(data, key);")

# 执行 JS 代码
result = client.execute_js("function test() { return 'hello'; } test();")
```

### Rust Spider
```rust
use rustspider::node_reverse::NodeReverseClient;

let client = NodeReverseClient::new("http://localhost:3000");

// 分析加密
let result = client.analyze_crypto("var enc = CryptoJS.AES.encrypt(data, key);").await?;

// 执行加密
let result = client.encrypt("AES", data, key, iv, "CBC").await?;
```

---

## 🎯 使用场景

### 场景 1: 逆向加密参数
```javascript
// 网站使用的加密签名
POST /api/crypto/analyze
{
  "code": "var sign = CryptoJS.HmacSHA256(data + timestamp, secret).toString();"
}

// 得到算法类型后执行
POST /api/crypto/encrypt
{
  "algorithm": "HMAC",
  "data": "param1=value1&param2=value2",
  "key": "mysecret",
  "mode": "SHA256"
}
```

### 场景 2: 执行混淆的 JS 代码
```javascript
// 将网站的混淆代码发送给服务执行
POST /api/js/execute
{
  "code": "eval(function(p,a,c,k,e,d){...})",
  "context": {
    "window": {},
    "document": {}
  }
}
```

### 场景 3: 模拟浏览器环境
```javascript
// 模拟浏览器指纹
POST /api/browser/simulate
{
  "code": "return generateFingerprint();",
  "browserConfig": {
    "userAgent": "Mozilla/5.0...",
    "platform": "Win32"
  }
}
```

---

## 📊 性能指标

- **响应时间**: < 100ms (简单操作)
- **并发支持**: 1000+ QPS
- **沙箱安全**: VM 隔离，无系统访问
- **代码大小限制**: 10MB

---

## 🔒 安全说明

1. **沙箱执行**: 所有 JS 代码在 VM 沙箱中执行
2. **超时保护**: 默认 5 秒超时
3. **资源限制**: 限制内存和 CPU 使用
4. **网络隔离**: 沙箱内无网络访问权限

---

## 🛠️ 开发指南

### 添加新的逆向能力

1. 在 `server.js` 中添加新的路由
2. 实现处理逻辑
3. 更新本文档
4. 为四个框架添加对应的客户端方法

### 测试

```bash
npm test
```

---

## 📝 许可证

MIT License
