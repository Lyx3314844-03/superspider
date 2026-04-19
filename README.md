# SuperSpider

<p align="center">
  <img src="docs/assets/superspider-wordmark.svg" alt="SuperSpider — Multi-Language Web Crawler Framework" width="900" />
</p>

<p align="center">
  <img src="docs/assets/superspider-icon.svg" alt="SuperSpider icon" width="160" />
</p>

<p align="center">
  <b>Multi-Language Web Crawler Framework</b><br/>
  AI · Media Download · Distributed · Anti-Bot · Node-Reverse
</p>

<p align="center">
  <a href="#-if-this-project-helped-you">⭐ If this project helped you, please give it a star!</a>
</p>

---

SuperSpider is a **multi-language web crawler framework** that ships four production-ready runtimes in Python, Go, Rust, and Java. Each runtime covers the same broad capability surface — web crawling, browser automation, AI extraction, media download, anti-bot, distributed execution — but is optimized for a different engineering environment.

| Runtime | Language | Delivery | Tagline |
| --- | --- | --- | --- |
| 🐍 **pyspider** | Python | virtualenv | AI-first, project-oriented, rapid iteration |
| 🐹 **gospider** | Go | compiled binary | Concurrent, binary-first, distributed workers |
| 🦀 **rustspider** | Rust | release binary | Performance-first, feature-gated, strongly typed |
| ☕ **javaspider** | Java | Maven / JAR | Enterprise-first, browser workflows, audit trails |

---

## 🕷️ What Can SuperSpider Do?

### 🌐 Web Crawling
- HTTP and browser-based crawling (Playwright + Selenium)
- Scrapy-style project interface with plugin injection
- Dynamic site handling (JavaScript-rendered pages)
- Proxy pool with health checking and automatic rotation
- Rate limiting, circuit breaker, deduplication
- Robots.txt compliance
- Session and cookie management
- Checkpoint and incremental crawl (resume interrupted crawls)

### 🎬 Media Download — 10 Platforms
All four runtimes can download from:

| Platform | Format |
| --- | --- |
| **YouTube** | HLS, DASH, MP4 |
| **Bilibili** | HLS, DASH, M4S |
| **IQIYI** | HLS, DASH |
| **Tencent Video** | HLS, direct link |
| **Youku** | HLS, DASH |
| **Douyin** | MP4, direct link |
| **Generic HLS** | M3U8 streams |
| **Generic DASH** | MPD manifests |
| **FFmpeg merge** | TS/M4S → MP4 |
| **DRM detection** | Widevine, PlayReady |

### 🤖 AI Extraction
- **LLM extraction** — OpenAI (GPT-4o, etc.) and Anthropic/Claude
- **Entity extraction** — named entities, structured data
- **Content summarization** — automatic page summarization
- **Sentiment analysis** — positive/negative/neutral classification
- **Smart parser** — auto-detects page type and extracts relevant fields (PySpider only)
- **Schema-driven output** — strongly typed structured extraction (PySpider only)
- **Few-shot examples** — guide the LLM with examples
- **XPath suggestion studio** — AI-suggested XPath selectors

### 🛡️ Anti-Bot
- TLS fingerprint rotation (JA3/JA4 mimicry)
- Browser behavior simulation (mouse movement, scroll, reading pace)
- WAF bypass techniques
- Night mode (reduced crawl rate during off-hours)
- **Captcha solving**: 2captcha, Anti-Captcha, reCAPTCHA v2/v3, hCaptcha, image captcha
- SSRF protection (blocks internal network access)

### 🔐 JS Encryption / Node-Reverse
Many modern sites protect their APIs with JavaScript-generated signatures. SuperSpider handles this via a Node.js bridge:
- Node-reverse client for JS-encrypted sites
- Encrypted site crawler (HMAC, AES, token-based)
- JS signature execution via Node.js bridge server
- Supports HMAC-SHA256, AES-encrypted params, timestamp tokens

### 🌍 Distributed Crawling
- **Redis** queue (native, all four runtimes)
- **RabbitMQ** — broker-native (Go, Java), bridge (Rust), native (Python)
- **Kafka** — broker-native (Go, Java), bridge (Rust), native (Python)
- Distributed workers with state machine
- Node discovery: environment variables, file, DNS-SRV, Consul, etcd
- Dataset mirror to database backends

### 🗄️ Storage Backends
| Backend | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| SQLite | ✅ | ✅ | ✅ | ✅ |
| PostgreSQL | ✅ | ✅ process | ✅ driver+process | ✅ |
| MySQL | ✅ | ✅ process | ✅ driver+process | ✅ |
| MongoDB | ✅ | ✅ process | ✅ driver+process | ✅ |
| JSON / CSV / JSONL | ✅ | ✅ | ✅ | ✅ |

### 📊 Observability
- Audit trail: in-memory, file, JSONL, composite
- Monitoring and metrics dashboard
- Preflight validation (check config before crawling)
- Checkpoint and resume (SQLite-backed)
- Incremental crawl (only crawl new/changed pages)

---

## 🐍 PySpider — AI-First Python Crawler

**Best for:** AI-powered extraction, rapid prototyping, research workflows

### Unique Capabilities
- **Smart parser** — automatically detects page type (article, product, listing, etc.) and extracts relevant fields without writing selectors
- **Schema-driven LLM extraction** — define a JSON schema, get structured output from any page
- **Graph crawler** — crawl relationship graphs, extract nodes and edges
- **Research runtime** — Jupyter-style notebook output for data analysis
- **Plugin injection** — extend any part of the pipeline with Python plugins
- **Async runtime** — full async/await support with aiohttp

### Install
```bash
# Windows
scripts\windows\install-pyspider.bat

# Linux / macOS
bash scripts/linux/install-pyspider.sh
bash scripts/macos/install-pyspider.sh
```

**Output:** `.venv-pyspider` — run `python -m pyspider version` to verify

---

## 🐹 GoSpider — Concurrent Binary Crawler

**Best for:** High-concurrency production crawling, binary deployment, distributed worker clusters

### Unique Capabilities
- **Single binary** — no runtime dependencies, deploy anywhere
- **Native Selenium/WebDriver** — direct WebDriver protocol, no wrapper overhead
- **Broker-native queues** — RabbitMQ and Kafka via native Go clients
- **Dedicated platform extractors** — separate packages for Bilibili, IQIYI, Tencent, Youku, Douyin
- **Process + driver DB adapters** — flexible database backend selection
- **Audit trail module** — structured audit logging with composite writers

### Install
```bash
# Windows
scripts\windows\install-gospider.bat

# Linux / macOS
bash scripts/linux/install-gospider.sh
bash scripts/macos/install-gospider.sh
```

**Output:** `gospider/gospider` binary — run `./gospider/gospider --version` to verify

---

## 🦀 RustSpider — Performance-First Crawler

**Best for:** Performance-sensitive deployments, strict resource boundaries, feature-gated release control

### Unique Capabilities
- **Feature-gated modules** — compile only what you need (browser, distributed, API, web)
- **Native node+playwright process** — Playwright runs as a managed subprocess, not a wrapper
- **Fantoccini Selenium facade** — async Rust WebDriver client
- **Real captcha API flow** — async 2captcha/Anti-Captcha with polling, not placeholder
- **Driver-level DB adapters** — native Rust drivers for Postgres, MySQL, MongoDB
- **Benchmark suite** — built-in performance benchmarks
- **Preflight validation** — validate all config and dependencies before starting

### Install
```bash
# Windows
scripts\windows\install-rustspider.bat

# Linux / macOS
bash scripts/linux/install-rustspider.sh
bash scripts/macos/install-rustspider.sh
```

**Output:** `rustspider/target/release/rustspider` — run `./rustspider/target/release/rustspider --version` to verify

---

## ☕ JavaSpider — Enterprise Java Crawler

**Best for:** Enterprise Java environments, Maven/JAR delivery, browser-heavy automation, audit-conscious execution

### Unique Capabilities
- **Maven profiles** — `lite / ai / browser / distributed / full` — build only what you need
- **Dedicated audit trail** — the strongest audit support in the set: in-memory, file, JSONL, composite
- **Broker-native queues** — RabbitMQ via `amqp-client`, Kafka via `kafka-clients`
- **REST API server** — built-in `/health`, `/jobs`, `/jobs/{id}`, `/jobs/{id}/result` endpoints
- **Async spider runtime** — `AsyncSpiderRuntime` for non-blocking execution
- **Workflow replay** — record and replay browser workflows
- **Generic-parser fallback** — media parsing never fails silently; falls back to generic extraction

### Maven Profiles
```bash
# Minimal (core crawling only)
mvn -f javaspider/pom.xml -P lite -DskipTests package

# With AI extraction
mvn -f javaspider/pom.xml -P ai -DskipTests package

# With browser automation
mvn -f javaspider/pom.xml -P browser -DskipTests package

# With distributed runtime
mvn -f javaspider/pom.xml -P distributed -DskipTests package

# Everything
mvn -f javaspider/pom.xml -P full -DskipTests package
```

### Install
```bash
# Windows
scripts\windows\install-javaspider.bat

# Linux / macOS
bash scripts/linux/install-javaspider.sh
bash scripts/macos/install-javaspider.sh
```

**Output:** `javaspider/target/` — run `java -jar javaspider/target/javaspider-*.jar --version` to verify

---

## 📦 Install Prerequisites

| Framework | Required |
| --- | --- |
| 🐍 PySpider | Python 3.8+, pip, venv |
| 🐹 GoSpider | Go 1.20+ |
| 🦀 RustSpider | Rust 1.70+, Cargo |
| ☕ JavaSpider | Java 17+, Maven 3.8+ |

---

## 🗺️ Quick Selection Guide

| I need... | Use |
| --- | --- |
| AI-powered extraction with LLM | 🐍 PySpider |
| High-concurrency binary deployment | 🐹 GoSpider |
| Maximum performance, strict boundaries | 🦀 RustSpider |
| Enterprise Java, Maven/JAR, audit trail | ☕ JavaSpider |
| Download YouTube / Bilibili / Douyin | any (all four) |
| Crawl JS-encrypted sites | any (all four support node-reverse) |
| Distributed worker cluster | 🐹 GoSpider or 🦀 RustSpider |
| Rapid prototyping and research | 🐍 PySpider |

---

## 📚 Documentation

| Document | Description |
| --- | --- |
| [`docs/FRAMEWORK_CAPABILITIES.md`](docs/FRAMEWORK_CAPABILITIES.md) | Detailed per-framework capability descriptions |
| [`docs/FRAMEWORK_CAPABILITY_MATRIX.md`](docs/FRAMEWORK_CAPABILITY_MATRIX.md) | Full capability comparison tables |
| [`docs/SUPERSPIDER_INSTALLS.md`](docs/SUPERSPIDER_INSTALLS.md) | Install instructions for all three OS |
| [`LATEST_FRAMEWORK_COMPLETION_REPORT.md`](LATEST_FRAMEWORK_COMPLETION_REPORT.md) | Latest completion status and verification evidence |
| [`MEDIA_PARITY_REPORT.md`](MEDIA_PARITY_REPORT.md) | Media platform coverage evidence |
| [`ADVANCED_USAGE_GUIDE.md`](ADVANCED_USAGE_GUIDE.md) | Advanced crawling scenarios |
| [`ENCRYPTED_SITE_CRAWLING_GUIDE.md`](ENCRYPTED_SITE_CRAWLING_GUIDE.md) | JS-encrypted site crawling |
| [`NODE_REVERSE_INTEGRATION_GUIDE.md`](NODE_REVERSE_INTEGRATION_GUIDE.md) | Node.js reverse engineering bridge |
| [`ULTIMATE_ENHANCEMENT_GUIDE.md`](ULTIMATE_ENHANCEMENT_GUIDE.md) | Full capability enhancement reference |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution guide |

---

## ⭐ If This Project Helped You

If SuperSpider saved you time, helped you build something, or taught you something new — please consider giving it a **⭐ star** on GitHub!

**Why it matters:**
- ⭐ Stars help other developers discover this project
- ⭐ Stars motivate continued development and maintenance
- ⭐ Stars show the community that multi-language crawler frameworks are valuable

**Has SuperSpider helped you?**
- 🎬 Downloaded videos from YouTube, Bilibili, or other platforms?
- 🤖 Extracted structured data using AI/LLM?
- 🛡️ Bypassed anti-bot protection on a challenging site?
- 🔐 Cracked a JS-encrypted API?
- 🌍 Built a distributed crawler cluster?
- 📊 Automated data collection for research or business?

If yes to any of the above — **[click the ⭐ Star button](https://github.com/Lyx3314844-03/superspider)** at the top of this page. It takes 2 seconds and means a lot! 🙏

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
