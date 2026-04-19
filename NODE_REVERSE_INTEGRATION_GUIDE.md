# Node.js Reverse Engineering Integration Guide

This guide covers the Node.js reverse engineering bridge used by all four SuperSpider runtimes to execute JavaScript-side logic for signature generation, token computation, and encrypted parameter handling.

## Overview

Many modern sites protect their APIs with JavaScript-generated signatures that are difficult to replicate in Python, Go, Rust, or Java without running the original JS. The Node.js reverse bridge solves this by:

1. Running a lightweight Node.js server that accepts function execution requests
2. Loading the extracted JavaScript from the target site
3. Executing the requested function with provided arguments
4. Returning the result to the calling runtime

This approach avoids the need to reverse-engineer and re-implement complex JS crypto in each language.

---

## Architecture

```
PySpider / GoSpider / RustSpider / JavaSpider
        |
        | HTTP (localhost)
        v
  node-reverse-server (Node.js)
        |
        | executes
        v
  extracted site JS (signature.js, token.js, etc.)
```

---

## Setting Up the Node Reverse Server

### Install

```bash
cd node-reverse-server
npm install
```

### Start

```bash
node server.js --port 3000
```

### Options

```
--port <number>     Port to listen on (default: 3000)
--host <string>     Host to bind to (default: 127.0.0.1)
--timeout <ms>      Execution timeout per request (default: 5000)
--max-memory <mb>   Max memory per execution context (default: 128)
```

### Health Check

```bash
curl http://localhost:3000/health
# {"status":"ok","version":"1.0.0"}
```

---

## Loading JavaScript Files

### Load a single file

```bash
curl -X POST http://localhost:3000/load \
  -H "Content-Type: application/json" \
  -d '{"file": "/path/to/signature.js"}'
```

### Load inline JavaScript

```bash
curl -X POST http://localhost:3000/load \
  -H "Content-Type: application/json" \
  -d '{"code": "function generateSign(p) { return p.page + \"_signed\"; }"}'
```

---

## Executing Functions

### Basic execution

```bash
curl -X POST http://localhost:3000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "function": "generateSign",
    "args": [{"page": 1, "size": 20}, "secret_key"]
  }'
```

### Response

```json
{
  "result": "a3f9b2c1d4e5...",
  "duration_ms": 2
}
```

---

## PySpider Integration

### Basic Usage

```python
from pyspider.node_reverse.client import NodeReverseClient

client = NodeReverseClient(server_url="http://localhost:3000")

# Load JS file
client.load_file("/path/to/signature.js")

# Execute function
sign = client.execute("generateSign", {"page": 1, "size": 20}, "secret_key")
print(sign)
```

### With Fetcher

```python
from pyspider.node_reverse.fetcher import NodeReverseFetcher

fetcher = NodeReverseFetcher(
    base_url="https://example.com/api",
    node_server="http://localhost:3000",
    js_file="/path/to/signature.js",
    sign_function="generateSign",
    sign_key="your_secret_key"
)

response = fetcher.get("/data", params={"page": 1})
```

### Async Usage

```python
import asyncio
from pyspider.node_reverse.client import AsyncNodeReverseClient

async def main():
    client = AsyncNodeReverseClient("http://localhost:3000")
    await client.load_file("/path/to/signature.js")
    sign = await client.execute("generateSign", {"page": 1})
    print(sign)

asyncio.run(main())
```

---

## GoSpider Integration

### Basic Usage

```go
import "github.com/superspider/gospider/node_reverse"

client := node_reverse.NewClient("http://localhost:3000")

// Load JS file
if err := client.LoadFile("/path/to/signature.js"); err != nil {
    log.Fatal(err)
}

// Execute function
result, err := client.Execute("generateSign", map[string]interface{}{
    "page": 1, "size": 20,
}, "secret_key")
if err != nil {
    log.Fatal(err)
}
fmt.Println(result)
```

### Middleware Integration

```go
import (
    "github.com/superspider/gospider/node_reverse"
    "github.com/superspider/gospider/middleware"
)

nodeClient := node_reverse.NewClient("http://localhost:3000")
nodeClient.LoadFile("/path/to/signature.js")

mw := node_reverse.NewMiddleware(nodeClient, node_reverse.MiddlewareConfig{
    SignFunction: "generateSign",
    SignKey:      "secret_key",
    SignParam:    "sign",
})

spider := core.NewSpider(core.WithMiddleware(mw))
```

---

## RustSpider Integration

### Basic Usage

```rust
use rustspider::node_reverse::NodeReverseClient;

let client = NodeReverseClient::new("http://localhost:3000");

// Load JS file
client.load_file("/path/to/signature.js").await?;

// Execute function
let sign: String = client.execute(
    "generateSign",
    &serde_json::json!({"page": 1, "size": 20}),
).await?;

println!("{}", sign);
```

### With Spider

```rust
use rustspider::node_reverse::{NodeReverseClient, NodeReverseMiddleware};

let node_client = NodeReverseClient::new("http://localhost:3000");
node_client.load_file("/path/to/signature.js").await?;

let middleware = NodeReverseMiddleware::new(node_client)
    .sign_function("generateSign")
    .sign_key("secret_key")
    .sign_param("sign");

let spider = Spider::new().middleware(middleware);
```

---

## JavaSpider Integration

### Basic Usage

```java
import com.superspider.javaspider.node_reverse.NodeReverseClient;

NodeReverseClient client = new NodeReverseClient("http://localhost:3000");

// Load JS file
client.loadFile("/path/to/signature.js");

// Execute function
String sign = client.execute("generateSign",
    Map.of("page", 1, "size", 20),
    "secret_key"
);
System.out.println(sign);
```

### With Middleware

```java
import com.superspider.javaspider.node_reverse.NodeReverseMiddleware;

NodeReverseClient client = new NodeReverseClient("http://localhost:3000");
client.loadFile("/path/to/signature.js");

NodeReverseMiddleware middleware = new NodeReverseMiddleware(client)
    .signFunction("generateSign")
    .signKey("secret_key")
    .signParam("sign");

Spider spider = new Spider().middleware(middleware);
```

---

## Common Patterns

### Pattern 1: HMAC Signature

```javascript
// signature.js
const CryptoJS = require('crypto-js');

function generateSign(params, secretKey) {
    const sorted = Object.keys(params)
        .sort()
        .map(k => `${k}=${params[k]}`)
        .join('&');
    return CryptoJS.HmacSHA256(sorted, secretKey).toString();
}

module.exports = { generateSign };
```

### Pattern 2: Timestamp Token

```javascript
// token.js
const md5 = require('md5');

function generateToken(appId, secretKey) {
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2);
    const token = md5(`${appId}${timestamp}${nonce}${secretKey}`);
    return { token, timestamp, nonce };
}

module.exports = { generateToken };
```

### Pattern 3: AES-Encrypted Parameters

```javascript
// encrypt.js
const CryptoJS = require('crypto-js');

function encryptParams(params, key, iv) {
    const json = JSON.stringify(params);
    const encrypted = CryptoJS.AES.encrypt(json,
        CryptoJS.enc.Utf8.parse(key),
        { iv: CryptoJS.enc.Utf8.parse(iv) }
    );
    return encrypted.toString();
}

module.exports = { encryptParams };
```

---

## Security Notes

- The Node reverse server should only bind to `127.0.0.1` (localhost), never to a public interface.
- Do not commit extracted site JavaScript to public repositories.
- The server has a per-request execution timeout to prevent runaway scripts.
- Memory limits are enforced per execution context.

---

## Troubleshooting

### Server not responding

```bash
# Check if the server is running
curl http://localhost:3000/health

# Check the port is not in use
netstat -an | grep 3000
```

### Function not found

Make sure the JS file exports the function correctly:

```javascript
// Must export the function
module.exports = { generateSign };
// or
global.generateSign = function(...) { ... };
```

### Execution timeout

Increase the timeout:

```bash
node server.js --port 3000 --timeout 10000
```

---

## Related Docs

- `ENCRYPTED_SITE_CRAWLING_GUIDE.md` — encrypted site crawling overview
- `ADVANCED_USAGE_GUIDE.md` — advanced crawling scenarios
- `docs/FRAMEWORK_CAPABILITY_MATRIX.md` — capability comparison
