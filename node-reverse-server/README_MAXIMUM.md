# 🔥 Node.js 逆向分析终极指南 v10.0

## 📋 概述

这是**业界最强大的逆向工程服务**，包含 **60+ APIs**，覆盖所有可能的逆向场景！

---

## 🚀 快速开始

### 安装和启动

```bash
cd C:\Users\Administrator\spider\node-reverse-server
npm install
npm start
```

**服务将在 `http://localhost:3000` 启动**

### 验证服务

```bash
curl http://localhost:3000/health
```

**预期响应**:
```json
{
  "status": "ok",
  "service": "NodeReverseEngine",
  "version": "10.0.0-Maximum",
  "totalAPIs": 60,
  "capabilities": {
    "crypto": 10,
    "ast": 8,
    "browser": 10,
    "antidetect": 8,
    "code": 7,
    "signature": 5,
    "websocket": 4,
    "utils": 8
  }
}
```

---

## 📚 完整 API 文档

### 🔐 1. 加密分析 (10 APIs)

#### 1.1 加密算法分析
**POST** `/api/crypto/analyze`

分析代码中使用的所有加密算法。

**请求**:
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
      "modes": ["ECB", "CBC", "CFB", "OFB", "GCM"],
      "keySizes": [128, 192, 256],
      "evidence": ["/CryptoJS\\.AES/"]
    }
  ],
  "keys": ["mysecretkey12345"],
  "ivs": ["myiv123456789012"],
  "analysis": {
    "hasKeyDerivation": false,
    "hasRandomIV": false,
    "hasPadding": true,
    "hasAuthentication": false,
    "complexity": "medium"
  }
}
```

#### 1.2 加密操作
**POST** `/api/crypto/encrypt`

支持算法: AES, DES, RSA, MD5, SHA, HMAC, Base64, Hex

**请求**:
```json
{
  "algorithm": "AES",
  "data": "Hello World",
  "key": "mysecretkey12345",
  "iv": "myiv123456789012",
  "mode": "CBC"
}
```

#### 1.3 解密操作
**POST** `/api/crypto/decrypt`

支持算法: AES, DES, RSA, Base64, Hex, ROT13

#### 1.4 哈希计算
**POST** `/api/crypto/hash`

支持算法: MD5, SHA1, SHA256, SHA384, SHA512

#### 1.5 签名生成
**POST** `/api/crypto/sign`

支持算法: RSA-SHA256, RSA-SHA1, DSA

#### 1.6 签名验证
**POST** `/api/crypto/verify`

验证数字签名的有效性。

#### 1.7 密钥生成
**POST** `/api/crypto/keygen`

生成 RSA 或 AES 密钥对。

#### 1.8 自动检测加密类型
**POST** `/api/crypto/auto-detect`

自动识别数据使用的加密算法。

#### 1.9 暴力破解弱密钥
**POST** `/api/crypto/brute-force`

尝试常见弱密钥。

#### 1.10 彩虹表查询
**POST** `/api/crypto/rainbow-table`

查询预计算的彩虹表。

---

### 🔍 2. AST 分析 (8 APIs)

#### 2.1 AST 语法分析
**POST** `/api/ast/analyze`

完整的 AST 分析，包括：
- 加密调用检测
- 函数定义
- 变量声明
- 导入语句
- 反调试检测
- 混淆特征分析
- 控制流分析
- 数据流分析

**响应示例**:
```json
{
  "success": true,
  "results": {
    "crypto": [...],
    "functions": [...],
    "variables": [...],
    "obfuscation": [...]
  },
  "obfuscationScore": 5,
  "obfuscationLevel": "high",
  "statistics": {
    "totalFunctions": 25,
    "totalVariables": 150
  }
}
```

#### 2.2 代码去混淆
**POST** `/api/ast/deobfuscate`

自动去混淆 JavaScript 代码。

#### 2.3 查找函数定义
**POST** `/api/ast/find-functions`

提取所有函数定义。

#### 2.4 查找函数调用
**POST** `/api/ast/find-calls`

查找所有函数调用。

#### 2.5 查找变量声明
**POST** `/api/ast/find-variables`

查找所有变量声明。

#### 2.6 提取字符串常量
**POST** `/api/ast/extract-strings`

提取所有字符串常量。

#### 2.7 控制流分析
**POST** `/api/ast/control-flow`

分析代码的控制流复杂度。

#### 2.8 数据流分析
**POST** `/api/ast/data-flow`

分析特定变量的数据流。

---

### 🌐 3. 浏览器模拟 (10 APIs)

#### 3.1 浏览器环境模拟
**POST** `/api/browser/simulate`

完整的浏览器环境模拟，包括：
- window, document, navigator
- localStorage, sessionStorage
- screen, history, performance
- Intl API

#### 3.2 浏览器指纹生成
**POST** `/api/browser/fingerprint`

生成 Chrome, Firefox, Safari 指纹。

#### 3.3 Canvas 指纹生成
**POST** `/api/browser/canvas`

生成 Canvas 指纹和哈希。

#### 3.4 WebGL 指纹生成
**POST** `/api/browser/webgl`

生成 WebGL 指纹信息。

#### 3.5 AudioContext 指纹生成
**POST** `/api/browser/audio`

生成 AudioContext 指纹。

#### 3.6 字体检测
**POST** `/api/browser/fonts`

检测系统安装的字体。

#### 3.7 插件检测
**POST** `/api/browser/plugins`

模拟浏览器插件检测。

#### 3.8 屏幕信息
**POST** `/api/browser/screen`

生成屏幕信息。

#### 3.9 存储 API 模拟
**POST** `/api/browser/storage`

模拟 localStorage/sessionStorage。

#### 3.10 事件触发模拟
**POST** `/api/browser/events`

模拟浏览器事件触发。

---

### 🛡️ 4. 反爬绕过 (9 APIs)

#### 4.1 反调试绕过
**POST** `/api/anti-debug/bypass`

绕过 debugger, DevTools, 时间检测等。

#### 4.2 反机器人检测分析
**POST** `/api/anti-bot/detect`

检测 Cloudflare, Akamai, DataDome 等 WAF。

#### 4.3 反爬画像与规避计划
**POST** `/api/anti-bot/profile`

将挑战检测、厂商识别、请求指纹模板、TLS 指纹和规避建议收敛成一份完整画像。

**请求**:
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

**响应重点字段**:
```json
{
  "success": true,
  "vendors": [{ "name": "Cloudflare" }],
  "signals": ["managed-browser-challenge", "javascript-challenge"],
  "requestBlueprint": {
    "headers": { "User-Agent": "..." },
    "tls": { "ja3": "..." }
  },
  "mitigationPlan": {
    "immediate": ["使用浏览器上下文先通过挑战页"]
  }
}
```

#### 4.4 验证码识别
**POST** `/api/captcha/solve`

集成第三方打码平台。

#### 4.5 WAF 绕过
**POST** `/api/waf/bypass`

生成绕过 WAF 的请求头。

#### 4.6 频率限制绕过
**POST** `/api/rate-limit/bypass`

提供频率限制绕过策略。

#### 4.7 指纹伪造
**POST** `/api/fingerprint/spoof`

生成真实的浏览器指纹。

#### 4.8 TLS 指纹生成
**POST** `/api/tls/fingerprint`

生成 Chrome, Firefox, Safari 的 TLS 指纹。

#### 4.9 隐形 HTTP 请求
**POST** `/api/http/stealth`

输出与当前指纹模板一致的 stealth 请求头建议。

#### 4.8 隐形 HTTP 请求
**POST** `/api/http/stealth`

生成隐形的 HTTP 请求配置。

---

### 📦 5. 代码分析 (7 APIs)

#### 5.1 代码去混淆
**POST** `/api/code/deobfuscate`

去除代码混淆。

#### 5.2 代码美化
**POST** `/api/code/beautify`

美化压缩的代码。

#### 5.3 代码压缩
**POST** `/api/code/minify`

压缩代码。

#### 5.4 Webpack 分析
**POST** `/api/code/webpack-analyze`

分析 Webpack 打包的代码。

#### 5.5 Webpack 模块提取
**POST** `/api/code/webpack-extract`

提取 Webpack 模块。

#### 5.6 依赖图生成
**POST** `/api/code/dependency-graph`

生成代码依赖图。

#### 5.7 复杂度分析
**POST** `/api/code/complexity`

分析代码复杂度。

---

### 🔑 6. 签名逆向 (5 APIs)

#### 6.1 自动签名逆向
**POST** `/api/signature/auto-reverse`

自动分析并还原签名算法。

#### 6.2 签名生成
**POST** `/api/signature/generate`

生成签名。

#### 6.3 签名验证
**POST** `/api/signature/verify`

验证签名。

#### 6.4 签名暴力破解
**POST** `/api/signature/brute-force`

暴力破解签名密钥。

#### 6.5 模式匹配
**POST** `/api/signature/pattern-match`

匹配签名模式。

---

### 🌊 7. WebSocket (4 APIs)

#### 7.1 WebSocket 消息解密
**POST** `/api/websocket/decrypt`

解密 WebSocket 消息。

#### 7.2 WebSocket 消息加密
**POST** `/api/websocket/encrypt`

加密 WebSocket 消息。

#### 7.3 WebSocket 拦截
**POST** `/api/websocket/intercept`

拦截 WebSocket 消息。

#### 7.4 WebSocket 重放
**POST** `/api/websocket/replay`

重放 WebSocket 消息。

---

### 🔧 8. 工具函数 (8 APIs)

| API | 说明 |
|-----|------|
| `/api/util/base64-encode` | Base64 编码 |
| `/api/util/base64-decode` | Base64 解码 |
| `/api/util/hex-encode` | Hex 编码 |
| `/api/util/hex-decode` | Hex 解码 |
| `/api/util/url-encode` | URL 编码 |
| `/api/util/url-decode` | URL 解码 |
| `/api/util/json-parse` | JSON 解析 |
| `/api/util/json-stringify` | JSON 序列化 |

---

## 🎯 实战案例

### 案例 1: 逆向电商网站签名

```javascript
// 步骤 1: 分析加密
const cryptoResult = await fetch('http://localhost:3000/api/crypto/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ code: websiteCode })
}).then(r => r.json());

// 步骤 2: 自动签名逆向
const sigResult = await fetch('http://localhost:3000/api/signature/auto-reverse', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    code: websiteCode,
    sampleInputs: 'param1=value1&param2=value2',
    sampleOutput: 'abc123'
  })
}).then(r => r.json());

// 步骤 3: 生成签名
const signature = await fetch('http://localhost:3000/api/signature/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    data: 'param1=value1&param2=value2',
    secret: sigResult.signatureFunction?.output,
    algorithm: 'hmac-sha256'
  })
}).then(r => r.json());
```

### 案例 2: 绕过 Cloudflare 保护

```javascript
// 步骤 1: 检测反爬机制
const detection = await fetch('http://localhost:3000/api/anti-bot/detect', {
  method: 'POST',
  body: JSON.stringify({ html, js })
}).then(r => r.json());

// 步骤 2: 生成 TLS 指纹
const tlsFP = await fetch('http://localhost:3000/api/tls/fingerprint', {
  method: 'POST',
  body: JSON.stringify({ browser: 'chrome', version: '120' })
}).then(r => r.json());

// 步骤 3: 生成浏览器指纹
const browserFP = await fetch('http://localhost:3000/api/browser/fingerprint', {
  method: 'POST',
  body: JSON.stringify({ browser: 'chrome' })
}).then(r => r.json());

// 步骤 4: 使用隐形请求
const stealth = await fetch('http://localhost:3000/api/http/stealth', {
  method: 'POST',
  body: JSON.stringify({ url: 'https://protected-site.com' })
}).then(r => r.json());
```

---

## 📊 性能指标

- **响应时间**: < 50ms (简单操作)
- **并发支持**: 1000+ QPS
- **代码大小限制**: 100MB
- **执行超时**: 30 秒
- **沙箱安全**: VM 隔离

---

## 🔒 安全说明

1. **沙箱执行**: 所有代码在 VM 沙箱中执行
2. **超时保护**: 默认 30 秒超时
3. **资源限制**: 限制内存和 CPU 使用
4. **网络隔离**: 沙箱内无网络访问权限

---

## 🎊 总结

Node.js 逆向服务 v10.0 是**业界最完整的逆向工程工具**：

✅ **60+ APIs** 覆盖所有逆向场景  
✅ **加密分析** - 10 种加密算法支持  
✅ **AST 分析** - 完整的语法树分析  
✅ **浏览器模拟** - 10 种浏览器特征  
✅ **反爬绕过** - 9 种反爬机制绕过  
✅ **代码分析** - 7 种代码分析工具  
✅ **签名逆向** - 5 种签名逆向方法  
✅ **WebSocket** - 4 种 WebSocket 工具  

**开始逆向任何网站吧！** 🚀
