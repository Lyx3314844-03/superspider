# SuperSpider

<p align="center">
  <img src="docs/assets/superspider-wordmark.svg" alt="SuperSpider multicolor wordmark" width="860" />
</p>

<p align="center">
  <img src="docs/assets/superspider-icon.svg" alt="SuperSpider icon" width="180" />
</p>

SuperSpider is a four-runtime crawler framework. It publishes four distinct crawler runtimes designed for different engineering environments and delivery models:

- `pyspider` — Python, AI-first, project-oriented
- `gospider` — Go, binary-first, concurrent workers
- `rustspider` — Rust, performance-first, feature-gated
- `javaspider` — Java, enterprise-first, browser workflows

All four runtimes cover the same broad capability surface — web crawling, browser automation, anti-bot handling, AI extraction, media download, distributed execution, and output pipelines — but each one emphasizes a different deployment and engineering posture.

---

## Framework Comparison

| Framework | Language | Delivery | Primary Strength | Best Fit |
| --- | --- | --- | --- | --- |
| **PySpider** | Python | virtualenv / editable package | AI orchestration, project workflows, rapid iteration | experimentation, AI pipelines, orchestration |
| **GoSpider** | Go | compiled binary | concurrency, binary deployment, distributed workers | services, binaries, worker-based execution |
| **RustSpider** | Rust | release binary | strong typing, performance, feature-gated release control | performance-sensitive, boundary-conscious deployments |
| **JavaSpider** | Java | Maven package / JAR | browser workflow, enterprise integration, audit trails | Java enterprise workflows, browser automation |

---

## Full Capability Surface

All four runtimes share the following capabilities:

### Web Crawling
- HTTP and browser-based crawling
- Scrapy-style project interface
- Dynamic site handling
- Proxy pool with health checking and rotation
- Rate limiting and circuit breaker
- Robots.txt compliance
- Session and cookie management
- Checkpoint and incremental crawl support

### Media Download
- HLS (`m3u8`) parsing and download
- DASH (`mpd`) parsing and download
- FFmpeg-based conversion and merge
- DRM detection
- **YouTube** — full support
- **Bilibili** — full support
- **IQIYI** — full support
- **Tencent Video** — full support
- **Youku** — full support
- **Douyin** — full support

### Anti-Bot
- TLS fingerprint rotation
- Browser behavior simulation
- WAF bypass
- Night mode (reduced activity during off-hours)
- Captcha solving: 2captcha, Anti-Captcha, reCAPTCHA, hCaptcha, image captcha
- SSRF protection

### AI Extraction
- Entity extraction
- Content summarization
- Sentiment analysis
- LLM extraction (OpenAI and Anthropic/Claude)
- Few-shot examples
- XPath suggestion studio

### Distributed
- Redis queue (native)
- RabbitMQ and Kafka queue backends
- Distributed workers
- Node discovery: env, file, DNS-SRV, Consul, etcd

### Node-Reverse / JS Encryption
- Node-reverse client for JS-encrypted sites
- Encrypted site crawler
- JS signature execution via Node.js bridge

### Observability
- Audit trail (in-memory, file, JSONL, composite)
- Monitoring and metrics
- Preflight validation
- Checkpoint and resume

### Infrastructure
- Web UI and console
- REST API server
- Docker support
- Workflow engine
- Event bus
- Feature gates
- curl-to-code converter

---

## Per-Framework Highlights

### PySpider — Strongest AI Extraction

- LLM extraction with OpenAI and Anthropic/Claude
- Smart parser (auto-detects page type)
- Schema-driven structured output
- Graph crawler with relation extraction
- Research runtime and notebook output
- Playwright (native)

### GoSpider — Strongest Concurrency

- Compiled binary, no runtime dependencies
- Native Selenium / WebDriver client
- Broker-native RabbitMQ and Kafka
- Dedicated Douyin, Bilibili, IQIYI, Tencent, Youku extractors
- Audit trail module

### RustSpider — Strongest Performance

- Feature-gated release binary
- Playwright via native `node + playwright` process
- Selenium via fantoccini facade
- Real async captcha API flow (2captcha, Anti-Captcha)
- Driver-level Postgres, MySQL, MongoDB adapters
- Benchmark suite

### JavaSpider — Strongest Enterprise Integration

- Maven profiles: `lite / ai / browser / distributed / full`
- Dedicated audit trail (strongest in the set)
- Broker-native RabbitMQ (amqp-client) and Kafka (kafka-clients)
- REST API server: `/health`, `/jobs`, `/jobs/{id}`, `/jobs/{id}/result`
- Async spider runtime
- Generic-parser fallback for media platforms

---

## Install

Every runtime has dedicated installers for Windows, Linux, and macOS.

| Framework | Windows | Linux | macOS |
| --- | --- | --- | --- |
| PySpider | `scripts\windows\install-pyspider.bat` | `scripts/linux/install-pyspider.sh` | `scripts/macos/install-pyspider.sh` |
| GoSpider | `scripts\windows\install-gospider.bat` | `scripts/linux/install-gospider.sh` | `scripts/macos/install-gospider.sh` |
| RustSpider | `scripts\windows\install-rustspider.bat` | `scripts/linux/install-rustspider.sh` | `scripts/macos/install-rustspider.sh` |
| JavaSpider | `scripts\windows\install-javaspider.bat` | `scripts/linux/install-javaspider.sh` | `scripts/macos/install-javaspider.sh` |

### Prerequisites

| Framework | Required |
| --- | --- |
| PySpider | Python 3.8+, venv, pip |
| GoSpider | Go 1.20+ |
| RustSpider | Rust 1.70+, Cargo |
| JavaSpider | Java 17+, Maven 3.8+ |

### Install Outputs

| Framework | Output |
| --- | --- |
| PySpider | `.venv-pyspider` virtual environment |
| GoSpider | `gospider` executable |
| RustSpider | `rustspider/target/release/rustspider` |
| JavaSpider | `javaspider/target` Maven artifacts |

---

## Documentation

| Document | Description |
| --- | --- |
| `docs/FRAMEWORK_CAPABILITIES.md` | Detailed per-framework capability descriptions |
| `docs/FRAMEWORK_CAPABILITY_MATRIX.md` | Full capability comparison tables |
| `docs/SUPERSPIDER_INSTALLS.md` | Install instructions and prerequisites |
| `LATEST_FRAMEWORK_COMPLETION_REPORT.md` | Latest completion status |
| `MEDIA_PARITY_REPORT.md` | Media platform coverage evidence |
| `ADVANCED_USAGE_GUIDE.md` | Advanced crawling scenarios |
| `ENCRYPTED_SITE_CRAWLING_GUIDE.md` | JS-encrypted site crawling |
| `NODE_REVERSE_INTEGRATION_GUIDE.md` | Node.js reverse engineering integration |
| `ULTIMATE_ENHANCEMENT_GUIDE.md` | Full capability enhancement reference |
| `CHANGELOG.md` | Version history |
| `CONTRIBUTING.md` | Contribution guide |
