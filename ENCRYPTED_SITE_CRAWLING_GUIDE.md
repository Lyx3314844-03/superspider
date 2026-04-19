# Encrypted Site Crawling Guide

This guide covers how to crawl sites that use JavaScript-based encryption, signature generation, or token obfuscation to protect their APIs.

## Overview

Many modern sites protect their APIs with:

- JavaScript-generated request signatures
- Encrypted request parameters
- Token-based authentication derived from browser-side JS execution
- Anti-debugging and obfuscation layers

All four SuperSpider runtimes include an `encrypted` module that handles these scenarios.

---

## How It Works

The encrypted crawling pipeline has three stages:

1. **Analysis** — identify the encryption scheme (signature function, token generation, parameter encoding)
2. **Extraction** — extract the JavaScript logic responsible for generating the protected values
3. **Execution** — run the extracted logic (via Node.js bridge or embedded JS engine) to produce valid request parameters

---

## PySpider

### Basic Usage

```python
from pyspider.encrypted.crawler import EncryptedCrawler

crawler = EncryptedCrawler(
    base_url="https://example.com/api",
    js_file="signature.js",       # extracted JS signature function
    sign_function="generateSign"  # function name to call
)

result = crawler.fetch("/data?page=1")
```

### Enhanced Mode

```python
from pyspider.encrypted.enhanced import EnhancedEncryptedCrawler

crawler = EnhancedEncryptedCrawler(
    base_url="https://example.com",
    auto_detect=True,              # auto-detect signature scheme
    node_bridge=True               # use Node.js bridge for JS execution
)

result = crawler.fetch("/api/list")
```

### Configuration

```python
config = {
    "sign_key": "your_sign_key",
    "timestamp_field": "t",
    "sign_field": "sign",
    "extra_params": {"version": "1.0"}
}
crawler = EncryptedCrawler(base_url="...", config=config)
```

---

## GoSpider

### Basic Usage

```go
import "github.com/superspider/gospider/encrypted"

crawler := encrypted.NewCrawler(encrypted.Config{
    BaseURL:      "https://example.com/api",
    JSFile:       "signature.js",
    SignFunction: "generateSign",
})

result, err := crawler.Fetch("/data?page=1")
```

### Enhanced Mode

```go
crawler := encrypted.NewEnhancedCrawler(encrypted.EnhancedConfig{
    BaseURL:     "https://example.com",
    AutoDetect:  true,
    NodeBridge:  true,
})

result, err := crawler.Fetch("/api/list")
```

### With Custom Headers

```go
crawler := encrypted.NewCrawler(encrypted.Config{
    BaseURL:      "https://example.com/api",
    JSFile:       "signature.js",
    SignFunction: "generateSign",
    ExtraHeaders: map[string]string{
        "X-App-Version": "1.0",
        "X-Platform":    "web",
    },
})
```

---

## RustSpider

### Basic Usage

```rust
use rustspider::encrypted::EncryptedCrawler;

let crawler = EncryptedCrawler::new()
    .base_url("https://example.com/api")
    .js_file("signature.js")
    .sign_function("generateSign");

let result = crawler.fetch("/data?page=1").await?;
```

### Enhanced Mode

```rust
use rustspider::encrypted::EnhancedEncryptedCrawler;

let crawler = EnhancedEncryptedCrawler::new()
    .base_url("https://example.com")
    .auto_detect(true)
    .node_bridge(true);

let result = crawler.fetch("/api/list").await?;
```

---

## JavaSpider

### Basic Usage

```java
import com.superspider.javaspider.encrypted.EncryptedCrawler;

EncryptedCrawler crawler = new EncryptedCrawler.Builder()
    .baseUrl("https://example.com/api")
    .jsFile("signature.js")
    .signFunction("generateSign")
    .build();

String result = crawler.fetch("/data?page=1");
```

### Enhanced Mode

```java
import com.superspider.javaspider.encrypted.EnhancedEncryptedCrawler;

EnhancedEncryptedCrawler crawler = new EnhancedEncryptedCrawler.Builder()
    .baseUrl("https://example.com")
    .autoDetect(true)
    .nodeBridge(true)
    .build();

String result = crawler.fetch("/api/list");
```

---

## Common Encryption Patterns

### HMAC-SHA256 Signature

Many APIs use HMAC-SHA256 to sign request parameters:

```javascript
// signature.js (extracted from target site)
function generateSign(params, secretKey) {
    const sorted = Object.keys(params).sort().map(k => `${k}=${params[k]}`).join('&');
    return CryptoJS.HmacSHA256(sorted, secretKey).toString();
}
```

### Timestamp + Nonce Token

```javascript
// token.js
function generateToken(appId, timestamp, nonce) {
    return md5(appId + timestamp + nonce + SECRET);
}
```

### Base64-Encoded Encrypted Parameters

```javascript
// encrypt.js
function encryptParams(params) {
    const json = JSON.stringify(params);
    return btoa(AES.encrypt(json, KEY).toString());
}
```

---

## Node.js Bridge

The Node.js bridge allows all four runtimes to execute arbitrary JavaScript for signature generation without embedding a full JS engine.

### Setup

```bash
# Install the node-reverse-server
cd node-reverse-server
npm install
node server.js --port 3000
```

### PySpider with Node Bridge

```python
from pyspider.node_reverse.client import NodeReverseClient

client = NodeReverseClient(server_url="http://localhost:3000")
sign = client.execute("generateSign", params={"page": 1, "size": 20})
```

### GoSpider with Node Bridge

```go
import "github.com/superspider/gospider/node_reverse"

client := node_reverse.NewClient("http://localhost:3000")
sign, err := client.Execute("generateSign", map[string]interface{}{
    "page": 1, "size": 20,
})
```

See `NODE_REVERSE_INTEGRATION_GUIDE.md` for full Node.js bridge documentation.

---

## Debugging Encrypted Sites

### Step 1: Identify the Signature Function

Use browser DevTools to find where the signature is generated:

1. Open DevTools → Network tab
2. Find a protected API request
3. Look for `sign`, `token`, `_t`, `_sign`, or similar parameters
4. Use the Sources tab to search for where these values are assigned

### Step 2: Extract the JavaScript

Copy the relevant function(s) from the minified source. Tools like `prettier` can help format it.

### Step 3: Test the Extracted Function

```bash
node -e "
const { generateSign } = require('./signature.js');
console.log(generateSign({ page: 1 }, 'secret_key'));
"
```

### Step 4: Integrate with SuperSpider

Pass the extracted JS file path to the `EncryptedCrawler` as shown above.

---

## Related Docs

- `NODE_REVERSE_INTEGRATION_GUIDE.md` — Node.js reverse engineering integration
- `ADVANCED_USAGE_GUIDE.md` — advanced crawling scenarios
- `docs/FRAMEWORK_CAPABILITY_MATRIX.md` — capability comparison
