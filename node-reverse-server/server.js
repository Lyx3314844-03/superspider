/**
 * Node.js 逆向工程统一服务
 * 为所有爬虫框架提供统一的逆向能力
 * 
 * 功能列表:
 * 1. 加密算法分析与识别
 * 2. 加密/解密操作
 * 3. JavaScript 代码执行
 * 4. AST 语法树分析
 * 5. Webpack 打包分析
 * 6. 函数调用模拟
 * 7. 浏览器环境模拟
 * 8. 签名算法逆向
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
app.use(express.json({ limit: '10mb' }));

const PORT = process.env.PORT || 3000;

// ==================== 健康检查 ====================
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'NodeReverseEngine',
    version: '2.0.0',
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
      'anti-bot-detect',
      'anti-bot-profile',
      'tls-fingerprint',
      'fingerprint-spoof',
      'http-stealth'
    ]
  });
});

// ==================== 1. 加密算法分析 ====================
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
    'TripleDES': {
      patterns: [/CryptoJS\.TripleDES/, /3des/, /des-ede3/],
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
    'HMAC': {
      patterns: [/CryptoJS\.Hmac/, /hmac/, /createHmac/]
    },
    'Base64': {
      patterns: [/btoa\(/, /atob\(/, /Buffer\.from.*base64/, /CryptoJS\.enc\.Base64/]
    },
    'RC4': {
      patterns: [/CryptoJS\.RC4/, /rc4/, /arc4/]
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

  // 检测密钥和IV
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

// ==================== 2. 加密操作 ====================
app.post('/api/crypto/encrypt', (req, res) => {
  try {
    const { algorithm, data, key, iv, mode = 'CBC', padding = 'Pkcs7' } = req.body;
    
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
      
    } else if (algo === 'DES') {
      const cipher = crypto.createCipheriv('des-cbc', Buffer.from(key), Buffer.from(iv));
      let encrypted = cipher.update(data, 'utf8', 'base64');
      encrypted += cipher.final('base64');
      result = { encrypted };
      
    } else if (algo === 'RSA') {
      const publicKey = key;
      const encrypted = crypto.publicEncrypt(
        {
          key: publicKey,
          padding: crypto.constants.RSA_PKCS1_OAEP_PADDING
        },
        Buffer.from(data)
      );
      result = { encrypted: encrypted.toString('base64') };
      
    } else if (algo === 'MD5') {
      result = { hash: crypto.createHash('md5').update(data).digest('hex') };
      
    } else if (algo.startsWith('SHA')) {
      const hashAlgo = algo.toLowerCase();
      result = { hash: crypto.createHash(hashAlgo).update(data).digest('hex') };
      
    } else {
      // 尝试使用 eval 执行 CryptoJS
      const cryptoJSCode = `
        CryptoJS.${algo}.encrypt("${data}", "${key}"${iv ? `, { iv: "${iv}", mode: CryptoJS.mode.${mode} }` : ''}).toString()
      `;
      result = { encrypted: cryptoJSCode, note: 'Requires CryptoJS context' };
    }

    res.json({ success: true, ...result });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

// ==================== 3. 解密操作 ====================
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
      
    } else if (algo === 'DES') {
      const decipher = crypto.createDecipheriv('des-cbc', Buffer.from(key), Buffer.from(iv));
      let decrypted = decipher.update(data, 'base64', 'utf8');
      decrypted += decipher.final('utf8');
      result = { decrypted };
      
    } else if (algo === 'RSA') {
      const privateKey = key;
      const decrypted = crypto.privateDecrypt(
        {
          key: privateKey,
          padding: crypto.constants.RSA_PKCS1_OAEP_PADDING
        },
        Buffer.from(data, 'base64')
      );
      result = { decrypted: decrypted.toString('utf8') };
      
    } else if (algo === 'BASE64') {
      result = { decrypted: Buffer.from(data, 'base64').toString('utf8') };
      
    } else {
      result = { note: 'Algorithm not supported for decryption', algorithm };
    }

    res.json({ success: true, ...result });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

// ==================== 4. JavaScript 代码执行 ====================
app.post('/api/js/execute', (req, res) => {
  try {
    const { code, context = {}, timeout = 5000 } = req.body;
    
    // 创建沙箱环境
    const sandbox = {
      console: {
        log: (...args) => {},
        error: (...args) => {}
      },
      window: {},
      document: {},
      navigator: { userAgent: 'Mozilla/5.0' },
      setTimeout: () => {},
      setInterval: () => {},
      ...context
    };

    vm.createContext(sandbox);
    const result = vm.runInContext(code, sandbox, { timeout });

    res.json({ success: true, result });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

// ==================== 5. AST 语法分析 ====================
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
      variables: [],
      imports: []
    };

    traverse(ast, {
      // 检测加密调用
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
      
      // 检测函数定义
      FunctionDeclaration({ node }) {
        results.functions.push({
          name: node.id?.name || 'anonymous',
          params: node.params.length,
          line: node.loc?.start.line
        });
      },
      
      // 检测变量声明
      VariableDeclaration({ node }) {
        node.declarations.forEach(decl => {
          results.variables.push({
            name: decl.id.name,
            line: node.loc?.start.line
          });
        });
      },
      
      // 检测反调试
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

// ==================== 6. Webpack 打包分析 ====================
app.post('/api/webpack/analyze', (req, res) => {
  try {
    const { code } = req.body;
    
    const modules = [];
    const moduleRegex = /\[(\d+)\]\s*:\s*function\s*\([^)]*\)\s*{([^}]+)}/g;
    let match;
    
    while ((match = moduleRegex.exec(code)) !== null) {
      modules.push({
        id: match[1],
        contentPreview: match[2].substring(0, 100)
      });
    }

    res.json({
      success: true,
      modules: modules.slice(0, 20),
      totalModules: modules.length,
      isWebpack: modules.length > 0
    });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

// ==================== 7. 函数调用模拟 ====================
app.post('/api/function/call', (req, res) => {
  try {
    const { functionName, args, context = {}, code } = req.body;
    
    const fullCode = `
      ${code || ''}
      (function() {
        return ${functionName}(${args.map(a => JSON.stringify(a)).join(',')});
      })();
    `;
    
    const sandbox = {
      console: { log: () => {} },
      window: {},
      document: {},
      ...context
    };
    
    vm.createContext(sandbox);
    const result = vm.runInContext(fullCode, sandbox, { timeout: 5000 });
    
    res.json({ success: true, result });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

// ==================== 8. 浏览器环境模拟 ====================
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
        },
        localStorage: {
          getItem: () => null,
          setItem: () => {}
        },
        sessionStorage: {
          getItem: () => null,
          setItem: () => {}
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

// ==================== 9. 反爬画像与规避计划 ====================
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
        'Reuse cookies across challenge and target requests',
        'Keep TLS and browser fingerprints aligned'
      ]
    });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

// ==================== 10. 签名算法逆向 ====================
app.post('/api/signature/reverse', (req, res) => {
  try {
    const { code, input, expectedOutput } = req.body;
    
    // 尝试执行代码并提取签名逻辑
    const sandbox = {
      console: { log: () => {} },
      window: {},
      document: {},
      location: { href: 'https://example.com' },
      input,
      result: null
    };
    
    const wrappedCode = `
      ${code}
      result = (function() {
        ${Object.keys(sandbox).filter(k => k !== 'result').map(k => `var ${k} = this.${k};`).join('\n')}
        return sign(${JSON.stringify(input)});
      }).call(this);
    `;
    
    vm.createContext(sandbox);
    vm.runInContext(wrappedCode, sandbox, { timeout: 5000 });
    
    res.json({
      success: true,
      signature: sandbox.result,
      matches: sandbox.result === expectedOutput
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
║                    Version 2.0.0                         ║
╠══════════════════════════════════════════════════════════╣
║  Server running on: http://localhost:${PORT}              ║
║                                                          ║
║  Available APIs:                                         ║
║  • POST /api/crypto/analyze   - 加密算法分析            ║
║  • POST /api/crypto/encrypt   - 加密操作                ║
║  • POST /api/crypto/decrypt   - 解密操作                ║
║  • POST /api/js/execute       - JS代码执行              ║
║  • POST /api/ast/analyze      - AST语法分析             ║
║  • POST /api/webpack/analyze  - Webpack打包分析         ║
║  • POST /api/function/call    - 函数调用模拟            ║
║  • POST /api/browser/simulate - 浏览器环境模拟          ║
║  • POST /api/anti-bot/detect  - 反爬检测分析            ║
║  • POST /api/anti-bot/profile - 反爬画像与规避计划      ║
║  • POST /api/tls/fingerprint  - TLS指纹生成             ║
║  • POST /api/fingerprint/spoof - 指纹伪造               ║
║  • POST /api/http/stealth     - 隐形HTTP请求建议        ║
║  • POST /api/signature/reverse - 签名算法逆向           ║
║  • GET  /health               - 健康检查                ║
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
