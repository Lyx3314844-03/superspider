/**
 * Node.js 逆向工程统一服务 - 增强版
 * 为所有爬虫框架提供强大的逆向能力
 * 
 * 新增功能 (v3.0):
 * 1. 自动签名逆向 - 分析并还原签名算法
 * 2. 动态参数解密 - 解密动态生成的请求参数
 * 3. TLS 指纹生成 - 生成真实浏览器 TLS 指纹
 * 4. 反调试绕过 - 绕过 debugger/反调试保护
 * 5. Cookie 加密处理 - 解密加密的 Cookie
 * 6. WebSocket 消息加解密
 * 7. Canvas 指纹生成
 * 8. 完整的浏览器环境模拟
 */

const express = require('express');
const crypto = require('crypto');
const vm = require('vm');
const { parse } = require('@babel/parser');
const traverse = require('@babel/traverse').default;
const cors = require('cors');
const {
  detectAntiBotProfile,
  getSpoofedFingerprintProfile,
  getTLSFingerprintProfile,
  getStealthHeaders
} = require('./lib/anti-bot-profile');

const app = express();
app.use(cors());
app.use(express.json({ limit: '50mb' }));

const PORT = process.env.PORT || 3000;

// ==================== 健康检查 ====================
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'NodeReverseEngine',
    version: '3.0.0-enhanced',
    pid: process.pid,
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    timestamp: new Date().toISOString(),
    capabilities: [
      'crypto-analysis',
      'crypto-encrypt',
      'crypto-decrypt',
      'js-execute',
      'ast-analyze',
      'webpack-analyze',
      'function-call',
      'browser-simulate',
      'signature-reverse',
      // v3.0 新增
      'auto-signature-reverse',
      'dynamic-param-decrypt',
      'tls-fingerprint',
      'anti-debug-bypass',
      'cookie-decrypt',
      'websocket-crypto',
      'canvas-fingerprint',
      'anti-bot-detect',
      'anti-bot-profile',
      'fingerprint-spoof',
      'http-stealth'
    ]
  });
});

// ==================== v3.0 新增功能 ====================

/**
 * 1. 自动签名逆向
 * 分析代码并自动还原签名算法
 */
app.post('/api/signature/auto-reverse', (req, res) => {
  try {
    const { code, sampleInputs, sampleOutput } = req.body;
    
    console.log('\n🔐 开始自动签名逆向分析...');
    
    // 步骤 1: AST 分析查找签名函数
    const signatureFunctions = findSignatureFunctions(code);
    
    console.log(`找到 ${signatureFunctions.length} 个可能的签名函数`);
    
    // 步骤 2: 尝试执行并验证
    const results = [];
    for (const func of signatureFunctions) {
      try {
        const result = testSignatureFunction(code, func, sampleInputs, sampleOutput);
        results.push(result);
      } catch (e) {
        results.push({
          name: func.name,
          success: false,
          error: e.message
        });
      }
    }
    
    // 步骤 3: 返回最佳匹配
    const bestMatch = results.find(r => r.success);
    
    res.json({
      success: !!bestMatch,
      signatureFunction: bestMatch || null,
      allResults: results,
      analysis: {
        totalFunctions: signatureFunctions.length,
        successCount: results.filter(r => r.success).length
      }
    });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

/**
 * 查找可能的签名函数
 */
function findSignatureFunctions(code) {
  const ast = parse(code, {
    sourceType: 'module',
    plugins: ['typescript', 'jsx']
  });
  
  const functions = [];
  
  traverse(ast, {
    FunctionDeclaration(path) {
      const name = path.node.id?.name;
      if (name && (
        name.includes('sign') ||
        name.includes('signature') ||
        name.includes('encrypt') ||
        name.includes('hash') ||
        name.includes('token') ||
        name.includes('auth')
      )) {
        functions.push({
          name,
          params: path.node.params.map(p => p.name || 'unknown'),
          line: path.node.loc?.start.line
        });
      }
    },
    FunctionExpression(path) {
      if (path.node.id?.name) {
        const name = path.node.id.name;
        if (name.includes('sign') || name.includes('signature')) {
          functions.push({
            name,
            params: path.node.params.map(p => p.name || 'unknown'),
            line: path.node.loc?.start.line
          });
        }
      }
    }
  });
  
  return functions;
}

/**
 * 测试签名函数
 */
function testSignatureFunction(code, func, sampleInputs, sampleOutput) {
  const sandbox = {
    console: { log: () => {} },
    window: {},
    document: {},
    navigator: { userAgent: 'Mozilla/5.0' },
    location: { href: 'https://example.com' },
    Math: Math,
    JSON: JSON,
    encodeURIComponent: encodeURIComponent,
    decodeURIComponent: decodeURIComponent
  };
  
  vm.createContext(sandbox);
  
  // 执行代码
  vm.runInContext(code, sandbox, { timeout: 5000 });
  
  // 尝试调用函数
  const funcRef = sandbox[func.name];
  if (typeof funcRef !== 'function') {
    return { name: func.name, success: false, error: '函数未定义' };
  }
  
  // 使用样本测试
  const testInput = sampleInputs || 'test_data';
  const result = funcRef(testInput);
  
  return {
    name: func.name,
    success: result === sampleOutput || (sampleOutput && result.includes(sampleOutput)),
    input: testInput,
    output: result,
    expectedOutput: sampleOutput
  };
}

/**
 * 2. 动态参数解密
 * 解密动态生成的请求参数
 */
app.post('/api/param/decrypt', (req, res) => {
  try {
    const { encryptedParams, algorithm, key, iv, context } = req.body;
    
    console.log('\n🔓 开始解密动态参数...');
    
    let decrypted;
    
    if (algorithm === 'AES') {
      const decipher = crypto.createDecipheriv(
        'aes-256-cbc',
        Buffer.from(key),
        Buffer.from(iv || '0000000000000000')
      );
      decrypted = decipher.update(encryptedParams, 'hex', 'utf8');
      decrypted += decipher.final('utf8');
    } else if (algorithm === 'Base64') {
      decrypted = Buffer.from(encryptedParams, 'base64').toString('utf8');
    } else {
      // 尝试执行 JS 解密
      const sandbox = {
        ...context,
        console: { log: () => {} },
        window: {},
        document: {}
      };
      
      vm.createContext(sandbox);
      decrypted = vm.runInContext(encryptedParams, sandbox, { timeout: 5000 });
    }
    
    // 解析为 JSON 对象
    let params = {};
    try {
      params = JSON.parse(decrypted);
    } catch {
      params = { rawData: decrypted };
    }
    
    res.json({
      success: true,
      decrypted,
      params,
      algorithm
    });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

/**
 * 3. TLS 指纹生成
 * 生成真实浏览器的 TLS 指纹
 */
app.post('/api/tls/fingerprint', (req, res) => {
  try {
    const { browser = 'chrome', version = '120' } = req.body;
    res.json({
      success: true,
      fingerprint: getTLSFingerprintProfile(browser, version),
      browser,
      version
    });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

app.post('/api/anti-bot/detect', (req, res) => {
  try {
    const profile = detectAntiBotProfile(req.body || {});
    res.json({
      success: true,
      detection: profile.detection,
      vendors: profile.vendors,
      challenges: profile.challenges,
      signals: profile.signals,
      score: profile.score,
      level: profile.level,
      recommendations: profile.recommendations
    });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

app.post('/api/anti-bot/profile', (req, res) => {
  try {
    res.json(detectAntiBotProfile(req.body || {}));
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

app.post('/api/fingerprint/spoof', (req, res) => {
  try {
    const { browser = 'chrome', platform = 'windows' } = req.body;
    res.json({
      success: true,
      fingerprint: getSpoofedFingerprintProfile(browser, platform),
      browser,
      platform
    });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

app.post('/api/http/stealth', (req, res) => {
  try {
    const { headers = {} } = req.body;
    res.json({
      success: true,
      recommendedHeaders: getStealthHeaders(headers),
      tips: [
        'Add jitter between requests',
        'Preserve browser cookies across challenge flows',
        'Keep TLS and browser fingerprints aligned'
      ]
    });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

/**
 * 4. 反调试绕过
 * 生成绕过反调试保护的代码
 */
app.post('/api/anti-debug/bypass', (req, res) => {
  try {
    const { code, type = 'all' } = req.body;
    
    console.log('\n🛡️ 开始绕过反调试保护...');
    
    const bypassCode = `
      // 绕过 debugger 语句
      (function() {
        const originalDebugger = Object.getOwnPropertyDescriptor(window, 'debugger');
        if (originalDebugger && originalDebugger.get) {
          Object.defineProperty(window, 'debugger', {
            get: function() { return false; },
            configurable: true
          });
        }
      })();
      
      // 绕过 Function.prototype.toString 检测
      (function() {
        const originalToString = Function.prototype.toString;
        Function.prototype.toString = function() {
          return 'function() { [native code] }';
        };
      })();
      
      // 绕过 DevTools 检测
      (function() {
        const element = new Image();
        Object.defineProperty(element, 'id', {
          get: function() {
            return false;
          }
        });
        console.log = function() {};
        console.debug = function() {};
      })();
      
      // 绕过时间检测
      (function() {
        const originalNow = Date.now;
        const originalGetTime = Date.prototype.getTime;
        
        Date.now = function() {
          return originalNow.apply(this) - 1000;
        };
        
        Date.prototype.getTime = function() {
          return originalGetTime.apply(this) - 1000;
        };
      })();
      
      ${code}
    `;
    
    // 执行绕过后的代码
    const sandbox = {
      console: { 
        log: () => {},
        debug: () => {},
        error: () => {}
      },
      window: {},
      document: {},
      navigator: { userAgent: 'Mozilla/5.0' }
    };
    
    vm.createContext(sandbox);
    const result = vm.runInContext(bypassCode, sandbox, { timeout: 10000 });
    
    res.json({
      success: true,
      result,
      bypassType: type,
      bypassCode
    });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

/**
 * 5. Cookie 加密处理
 * 解密加密的 Cookie
 */
app.post('/api/cookie/decrypt', (req, res) => {
  try {
    const { encryptedCookie, key, algorithm = 'AES' } = req.body;
    
    console.log('\n🍪 开始解密 Cookie...');
    
    let decrypted;
    
    if (algorithm === 'AES') {
      const decipher = crypto.createDecipheriv(
        'aes-256-cbc',
        Buffer.from(key),
        Buffer.from(key.substring(0, 16))
      );
      decrypted = decipher.update(encryptedCookie, 'hex', 'utf8');
      decrypted += decipher.final('utf8');
    } else {
      // Base64 解码
      decrypted = Buffer.from(encryptedCookie, 'base64').toString('utf8');
    }
    
    // 解析 Cookie
    const cookies = {};
    decrypted.split(';').forEach(cookie => {
      const [name, value] = cookie.split('=');
      if (name && value) {
        cookies[name.trim()] = value.trim();
      }
    });
    
    res.json({
      success: true,
      decrypted,
      cookies,
      algorithm
    });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

/**
 * 6. WebSocket 消息加解密
 * 处理 WebSocket 加密消息
 */
app.post('/api/websocket/decrypt', (req, res) => {
  try {
    const { encryptedMessage, key, algorithm = 'AES' } = req.body;
    
    let decrypted;
    
    if (algorithm === 'AES') {
      const decipher = crypto.createDecipheriv(
        'aes-256-cbc',
        Buffer.from(key),
        Buffer.from(key.substring(0, 16))
      );
      decrypted = decipher.update(encryptedMessage, 'base64', 'utf8');
      decrypted += decipher.final('utf8');
    } else {
      decrypted = Buffer.from(encryptedMessage, 'base64').toString('utf8');
    }
    
    // 尝试解析 JSON
    let parsed;
    try {
      parsed = JSON.parse(decrypted);
    } catch {
      parsed = { rawData: decrypted };
    }
    
    res.json({
      success: true,
      decrypted,
      parsed,
      algorithm
    });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

/**
 * 7. Canvas 指纹生成
 * 生成 Canvas 浏览器指纹
 */
app.post('/api/canvas/fingerprint', (req, res) => {
  try {
    // 模拟 Canvas 指纹生成
    const canvasCode = `
      (function() {
        try {
          var canvas = document.createElement('canvas');
          canvas.width = 280;
          canvas.height = 60;
          var ctx = canvas.getContext('2d');
          
          ctx.textBaseline = 'top';
          ctx.font = '14px Arial';
          ctx.textBaseline = 'alphabetic';
          ctx.fillStyle = '#f60';
          ctx.fillRect(125, 1, 62, 20);
          ctx.fillStyle = '#069';
          ctx.fillText('Hello, World!', 2, 15);
          ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
          ctx.fillText('Canvas Fingerprint', 4, 17);
          
          return canvas.toDataURL();
        } catch (e) {
          return null;
        }
      })()
    `;
    
    const sandbox = {
      document: {
        createElement: function(tag) {
          return {
            width: 280,
            height: 60,
            getContext: function() {
              return {
                textBaseline: 'top',
                font: '14px Arial',
                fillStyle: '#f60',
                fillRect: function() {},
                fillText: function() {}
              };
            },
            toDataURL: function() {
              return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAASwAAABQCAY...';
            }
          };
        }
      }
    };
    
    vm.createContext(sandbox);
    const fingerprint = vm.runInContext(canvasCode, sandbox, { timeout: 5000 });
    
    res.json({
      success: true,
      fingerprint,
      hash: crypto.createHash('md5').update(fingerprint || '').digest('hex')
    });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

// ==================== 保留原有功能 ====================
// （之前的加密分析、加密/解密、JS执行、AST分析等功能保持不变）

app.post('/api/crypto/analyze', (req, res) => {
  const { code } = req.body;
  
  const cryptoPatterns = {
    'AES': {
      patterns: [/CryptoJS\.AES/, /aes\.encrypt/, /aes\.decrypt/, /AES\.encrypt/, /createCipheriv/],
      modes: ['ECB', 'CBC', 'CFB', 'OFB', 'GCM']
    },
    'DES': {
      patterns: [/CryptoJS\.DES/, /des\.encrypt/, /createCipheriv.*des/],
      modes: ['ECB', 'CBC']
    },
    'RSA': {
      patterns: [/RSA\.encrypt/, /rsa\.encrypt/, /publicEncrypt/, /privateDecrypt/],
      modes: ['PKCS1', 'OAEP']
    },
    'MD5': {
      patterns: [/CryptoJS\.MD5/, /md5\(/, /createHash\(['"]md5['"]\)/]
    },
    'SHA': {
      patterns: [/CryptoJS\.SHA/, /sha\d+/, /createHash\(['"]sha\d+['"]\)/],
      variants: ['SHA1', 'SHA256', 'SHA512']
    },
    'Base64': {
      patterns: [/btoa\(/, /atob\(/, /Buffer\.from.*base64/, /CryptoJS\.enc\.Base64/]
    }
  };

  const detected = [];
  
  for (const [name, info] of Object.entries(cryptoPatterns)) {
    const found = info.patterns.some(pattern => pattern.test(code));
    if (found) {
      detected.push({
        name,
        confidence: 0.95,
        modes: info.modes || [],
        variants: info.variants || []
      });
    }
  }

  const keyPattern = /(?:key|secret|password)\s*[=:]\s*['"]([^'"]{16,32})['"]/g;
  const ivPattern = /(?:iv|initializationVector)\s*[=:]\s*['"]([^'"]{16})['"]/g;
  
  const keys = [...code.matchAll(keyPattern)].map(m => m[1]);
  const ivs = [...code.matchAll(ivPattern)].map(m => m[1]);

  res.json({
    success: true,
    cryptoTypes: detected,
    keys: keys.slice(0, 5),
    ivs: ivs.slice(0, 5),
    analysis: {
      hasKeyDerivation: /deriveKey|PBKDF2|deriveBits/.test(code),
      hasRandomIV: /randomIV|Math\.random|crypto\.randomBytes/.test(code),
      complexity: detected.length > 2 ? 'high' : detected.length > 0 ? 'medium' : 'low'
    }
  });
});

app.post('/api/crypto/encrypt', (req, res) => {
  try {
    const { algorithm, data, key, iv, mode = 'CBC' } = req.body;
    
    let result;
    const algo = algorithm.toUpperCase();
    
    if (algo === 'AES') {
      const keyBuffer = Buffer.from(key);
      const ivBuffer = Buffer.from(iv);
      const algoStr = `aes-${keyBuffer.length * 8}-${mode.toLowerCase()}`;
      
      const cipher = crypto.createCipheriv(algoStr, keyBuffer, ivBuffer);
      let encrypted = cipher.update(data, 'utf8', 'base64');
      encrypted += cipher.final('base64');
      result = { encrypted };
    } else if (algo === 'MD5') {
      result = { hash: crypto.createHash('md5').update(data).digest('hex') };
    } else if (algo.startsWith('SHA')) {
      result = { hash: crypto.createHash(algo.toLowerCase()).update(data).digest('hex') };
    } else {
      result = { encrypted: btoa(data) };
    }

    res.json({ success: true, ...result });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

app.post('/api/crypto/decrypt', (req, res) => {
  try {
    const { algorithm, data, key, iv, mode = 'CBC' } = req.body;
    
    let result;
    const algo = algorithm.toUpperCase();
    
    if (algo === 'AES') {
      const keyBuffer = Buffer.from(key);
      const ivBuffer = Buffer.from(iv);
      const algoStr = `aes-${keyBuffer.length * 8}-${mode.toLowerCase()}`;
      
      const decipher = crypto.createDecipheriv(algoStr, keyBuffer, ivBuffer);
      let decrypted = decipher.update(data, 'base64', 'utf8');
      decrypted += decipher.final('utf8');
      result = { decrypted };
    } else if (algo === 'BASE64') {
      result = { decrypted: Buffer.from(data, 'base64').toString('utf8') };
    } else {
      result = { decrypted: data };
    }

    res.json({ success: true, ...result });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

app.post('/api/js/execute', (req, res) => {
  try {
    const { code, context = {}, timeout = 5000 } = req.body;
    
    const sandbox = {
      console: { log: () => {}, error: () => {} },
      window: {},
      document: {},
      navigator: { userAgent: 'Mozilla/5.0' },
      setTimeout: () => {},
      setInterval: () => {},
      Math: Math,
      JSON: JSON,
      ...context
    };

    vm.createContext(sandbox);
    const result = vm.runInContext(code, sandbox, { timeout });

    res.json({ success: true, result });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

app.post('/api/ast/analyze', (req, res) => {
  try {
    const { code, analysis = ['crypto', 'obfuscation', 'anti-debug'] } = req.body;
    
    const ast = parse(code, {
      sourceType: 'module',
      plugins: ['typescript', 'jsx']
    });

    const results = {
      crypto: [],
      obfuscation: [],
      antiDebug: [],
      functions: [],
      variables: []
    };

    traverse(ast, {
      CallExpression({ node }) {
        const callee = node.callee;
        if (callee.property && callee.property.name) {
          const name = callee.property.name;
          if (name.includes('encrypt') || name.includes('decrypt')) {
            results.crypto.push({
              type: 'crypto-call',
              name,
              line: node.loc?.start.line
            });
          }
        }
      },
      FunctionDeclaration({ node }) {
        results.functions.push({
          name: node.id?.name || 'anonymous',
          params: node.params.length,
          line: node.loc?.start.line
        });
      },
      DebuggerStatement({ node }) {
        results.antiDebug.push({
          type: 'debugger-statement',
          line: node.loc?.start.line
        });
      }
    });

    res.json({ success: true, results });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

app.post('/api/browser/simulate', (req, res) => {
  try {
    const { code, browserConfig = {} } = req.body;
    
    const {
      userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      language = 'zh-CN',
      platform = 'Win32',
      vendor = 'Google Inc.'
    } = browserConfig;

    const sandbox = {
      window: {
        navigator: {
          userAgent,
          language,
          platform,
          vendor,
          cookieEnabled: true,
          plugins: []
        },
        document: {
          cookie: '',
          createElement: () => ({ setAttribute: () => {}, appendChild: () => {} }),
          getElementsByTagName: () => []
        },
        location: {
          href: 'https://example.com',
          hostname: 'example.com'
        }
      }
    };
    
    sandbox.document = sandbox.window.document;
    sandbox.navigator = sandbox.window.navigator;
    sandbox.location = sandbox.window.location;

    vm.createContext(sandbox);
    const result = vm.runInContext(code, sandbox, { timeout: 5000 });
    
    res.json({ 
      success: true, 
      result,
      cookies: sandbox.document.cookie
    });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

// ==================== 启动服务 ====================
function printBanner() {
  console.log(`
╔══════════════════════════════════════════════════════════╗
║          Node.js Reverse Engineering Service             ║
║                    Version 3.0.0-Enhanced                ║
╠══════════════════════════════════════════════════════════╣
║  Server running on: http://localhost:${PORT}              ║
║                                                          ║
║  核心功能:                                               ║
║  • POST /api/crypto/analyze      - 加密算法分析         ║
║  • POST /api/crypto/encrypt      - 加密操作             ║
║  • POST /api/crypto/decrypt      - 解密操作             ║
║  • POST /api/js/execute          - JS代码执行           ║
║  • POST /api/ast/analyze         - AST语法分析          ║
║  • POST /api/browser/simulate    - 浏览器环境模拟       ║
║                                                          ║
║  🆕 v3.0 新增功能:                                       ║
║  • POST /api/signature/auto-reverse - 自动签名逆向      ║
║  • POST /api/param/decrypt       - 动态参数解密         ║
║  • POST /api/tls/fingerprint     - TLS指纹生成          ║
║  • POST /api/anti-bot/detect    - 反爬检测分析          ║
║  • POST /api/anti-bot/profile   - 反爬画像与规避计划    ║
║  • POST /api/fingerprint/spoof  - 指纹伪造              ║
║  • POST /api/http/stealth       - 隐形HTTP请求建议      ║
║  • POST /api/anti-debug/bypass   - 反调试绕过           ║
║  • POST /api/cookie/decrypt        - Cookie加密处理     ║
║  • POST /api/websocket/decrypt     - WebSocket消息解密  ║
║  • POST /api/canvas/fingerprint  - Canvas指纹生成       ║
║  • GET  /health                  - 健康检查             ║
╚══════════════════════════════════════════════════════════╝
  `);
}

if (require.main === module) {
  app.listen(PORT, () => {
    printBanner();
  });
}

module.exports = {
  app,
  detectAntiBotProfile,
  getSpoofedFingerprintProfile,
  getTLSFingerprintProfile,
  getStealthHeaders
};
