# 🎬 YouTube 视频爬取与 Node.js 逆向分析

## 📋 概述

本示例演示如何使用 Java Spider 爬取 YouTube 视频页面，并使用 Node.js 逆向服务进行加密算法分析。

**目标视频**: https://www.youtube.com/watch?v=Qk-ROQkkloE

---

## 🚀 快速开始

### 步骤 1: 启动 Node.js 逆向服务

```bash
cd C:\Users\Administrator\spider\node-reverse-server
npm start
```

**预期输出**:
```
╔══════════════════════════════════════════════════════════╗
║          Node.js Reverse Engineering Service             ║
║                    Version 2.0.0                         ║
╠══════════════════════════════════════════════════════════╣
║  Server running on: http://localhost:3000               ║
║                                                          ║
║  Available APIs:                                         ║
║  • POST /api/crypto/analyze   - 加密算法分析            ║
║  • POST /api/crypto/encrypt   - 加密操作                ║
║  • POST /api/crypto/decrypt   - 解密操作                ║
║  • POST /api/js/execute       - JS代码执行              ║
║  • POST /api/ast/analyze      - AST语法分析             ║
║  • ...                                                   ║
╚══════════════════════════════════════════════════════════╝
```

### 步骤 2: 验证服务

```bash
curl http://localhost:3000/health
```

**预期响应**:
```json
{
  "status": "ok",
  "service": "NodeReverseEngine",
  "version": "2.0.0"
}
```

### 步骤 3: 编译 Java Spider

```bash
cd C:\Users\Administrator\spider\javaspider
mvn compile
```

### 步骤 4: 运行爬虫

#### 方式 1: 使用 Maven
```bash
mvn exec:java -Dexec.mainClass="com.javaspider.examples.YouTubeVideoSpider"
```

#### 方式 2: 使用 IDE
在 IDE 中直接运行 `YouTubeVideoSpider.java` 的 main 方法。

---

## 📊 爬虫功能

### 1. 检查逆向服务
✅ 验证 Node.js 服务是否正常运行

### 2. 爬取视频页面
✅ 获取 YouTube 视频页面 HTML

### 3. 分析加密算法
✅ 使用 Node.js 逆向服务分析页面中的:
- AES/DES/RSA 加密
- MD5/SHA 哈希
- HMAC 签名
- Base64 编码
- 混淆代码

### 4. 提取视频信息
✅ 提取:
- 视频标题
- 视频 ID
- 频道名称
- 观看次数

### 5. 提取播放列表
✅ 提取:
- 播放列表 ID
- 视频数量
- 列表中的所有视频 ID

### 6. 分析视频流加密
✅ 分析:
- cipher 函数
- signature 算法
- 视频流 URL 加密

### 7. AST 语法分析
✅ 使用 Babel 分析:
- 加密调用位置
- 混淆代码检测
- 反调试检测

### 8. 执行混淆 JS
✅ 在沙箱中执行:
- eval 混淆代码
- cipher 函数
- 签名函数

---

## 📝 预期输出示例

```
================================================================================
🎬 YouTube 视频爬取与 Node.js 逆向分析
================================================================================

[步骤 1] 检查 Node.js 逆向服务...
✅ Node.js 逆向服务正常运行

[步骤 2] 获取 YouTube 视频页面...
✅ 页面获取成功，大小: 523847 字节

[步骤 3] 使用 Node.js 逆向服务分析加密...
📊 共找到 23 个 <script> 标签

🔍 分析脚本 #3...
  ✅ 检测到加密算法:
    - AES (置信度: 0.95)
    - Base64 (置信度: 0.95)
  🔑 检测到的密钥:
    - mysecretkey12345

[步骤 4] 提取视频基本信息...
📹 视频标题: Amazing Music Video
🆔 视频 ID: Qk-ROQkkloE
👤 频道: MusicChannel
👁️  观看次数: 1234567

[步骤 5] 提取播放列表信息...
📋 播放列表 ID: RDQk-ROQkkloE
📊 播放列表视频数: 50
🎬 播放列表中的视频:
  1. https://www.youtube.com/watch?v=Qk-ROQkkloE
  2. https://www.youtube.com/watch?v=ABC123DEF
  3. https://www.youtube.com/watch?v=XYZ789GHI
  ...

[步骤 6] 分析视频流加密...
🔐 找到 cipher 函数代码 (前200字符):
function decrypt(cipher) { var result = ...

🔍 AST 分析结果 - 加密调用:
  - encrypt (行 42)
  - decrypt (行 87)

[步骤 7] 执行页面中的混淆代码...
📦 找到混淆代码 (前100字符):
eval(function(p,a,c,k,e,d){...})

🧪 尝试执行混淆代码...
✅ 执行成功!
结果: function sign(){...}

================================================================================
✅ 爬取和逆向分析完成！
================================================================================
```

---

## 🔧 自定义配置

### 修改目标视频

编辑 `YouTubeVideoSpider.java`:
```java
private static final String TARGET_URL = "https://www.youtube.com/watch?v=YOUR_VIDEO_ID";
```

### 修改逆向服务地址

```java
private static final String REVERSE_SERVICE_URL = "http://localhost:3000";
```

### 修改线程数

```java
Spider spider = Spider.create(processor)
        .name("YouTubeVideoSpider")
        .addUrl(TARGET_URL)
        .thread(2);  // 增加线程数
```

---

## 🐛 常见问题

### Q1: Node.js 服务启动失败
```bash
# 检查端口是否被占用
netstat -ano | findstr :3000

# 更换端口
PORT=3001 npm start
```

### Q2: 爬取结果为空
- 检查网络连接
- YouTube 可能需要代理
- 检查 User-Agent 是否被屏蔽

### Q3: 编译失败
```bash
# 清理并重新编译
mvn clean compile
```

---

## 📚 相关文档

- [Node.js 逆向服务文档](../../node-reverse-server/README.md)
- [Java Spider 文档](../README.md)
- [集成指南](../../NODE_REVERSE_INTEGRATION_GUIDE.md)

---

## ⚠️ 注意事项

1. **遵守 YouTube 服务条款**
2. **不要过度频繁请求**
3. **尊重 robots.txt**
4. **仅用于学习目的**

---

## 🎯 下一步

- 扩展支持视频下载
- 添加评论爬取
- 实现自动解密视频流
- 批量处理播放列表

祝爬取愉快！🚀
