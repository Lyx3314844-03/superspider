# SuperSpider Framework Capabilities

Updated: 2026-04-19

This document describes what each of the four SuperSpider runtimes can do, how far each one goes, what it installs, and where it fits best.

---

## Shared Capabilities Across All Four Runtimes

Every runtime covers the same broad capability surface:

**Web Crawling**
- HTTP and browser-based crawling
- Scrapy-style project interface
- Dynamic site handling
- Proxy pool with health checking and rotation
- Rate limiting and circuit breaker
- Robots.txt compliance
- Session and cookie management
- Checkpoint and incremental crawl support

**Media Download**
- HLS (`m3u8`) parsing and download
- DASH (`mpd`) parsing and download
- FFmpeg-based conversion and merge
- DRM detection
- Platform parsers: YouTube, Bilibili, IQIYI, Tencent Video, Youku, Douyin

**Anti-Bot**
- TLS fingerprint rotation
- Browser behavior simulation
- WAF bypass
- Night mode (reduced activity during off-hours)
- Captcha solving: 2captcha, Anti-Captcha, reCAPTCHA, hCaptcha, image captcha
- SSRF protection

**AI Extraction**
- Entity extraction
- Content summarization
- Sentiment analysis
- LLM extraction (OpenAI and Anthropic/Claude)
- Few-shot examples
- XPath suggestion studio

**Distributed**
- Redis queue (native)
- RabbitMQ and Kafka queue backends
- Distributed workers
- Node discovery: env, file, DNS-SRV, Consul, etcd

**Node-Reverse / JS Encryption**
- Node-reverse client for JS-encrypted sites
- Encrypted site crawler
- JS signature execution via Node.js bridge

**Observability**
- Audit trail (in-memory, file, JSONL, composite)
- Monitoring and metrics
- Preflight validation
- Checkpoint and resume

**Infrastructure**
- Web UI and console
- REST API server
- Docker support
- Workflow engine
- Event bus
- Feature gates
- curl-to-code converter

---

## PySpider

PySpider is the most complete project-oriented Python crawler in the set. It has the strongest AI extraction capabilities and the most flexible plugin system.

### Core Functions

- Python-native CLI: `python -m pyspider`
- Scrapy-style project runtime with plugin injection
- AI extraction pipeline: entity extractor, summarizer, sentiment analyzer, LLM extractor, smart parser
- Schema-driven structured output
- Browser + HTTP hybrid crawling via Playwright (native)
- Anti-bot, captcha, node-reverse, media handling, and dataset output
- Graph crawler with relation extraction and node traversal
- Research runtime and notebook output
- Async runtime
- Dataset writer: JSON, CSV, JSONL, Markdown

### AI Capabilities (Strongest)

- LLM extraction with OpenAI and Anthropic/Claude
- Smart parser (auto-detects page type and extracts relevant fields)
- Schema-driven structured output
- Few-shot examples
- XPath suggestion studio

### Media Coverage

- HLS / DASH parsing and download
- FFmpeg utilities
- DRM inspection
- YouTube, Bilibili, IQIYI, Tencent Video, Youku, Douyin

### Distributed

- Redis, RabbitMQ, Kafka queue backends
- Distributed workers
- Node discovery: Consul, etcd, env, file, DNS-SRV

### Install

| OS | Script |
| --- | --- |
| Windows | `scripts\windows\install-pyspider.bat` |
| Linux | `scripts/linux/install-pyspider.sh` |
| macOS | `scripts/macos/install-pyspider.sh` |

**Output:** `.venv-pyspider` virtual environment, runnable `python -m pyspider version`

### Best Fit

- Rapid project starts and AI-heavy pipelines
- LLM-powered structured extraction
- Teams that want Python-side flexibility for analysis and automation
- Experimentation and orchestration-heavy crawling

---

## GoSpider

GoSpider is the strongest fit for concurrent, binary-first, service-oriented crawling. It compiles to a single binary with no runtime dependencies.

### Core Functions

- Compiled Go CLI binary
- Concurrent crawling engine with rate limiting and deduplication
- Distributed worker, queue, and storage runtime
- Browser pool with Playwright and Selenium (native WebDriver client)
- Anti-bot module with WAF bypass and night mode
- Captcha solver (2captcha, Anti-Captcha, reCAPTCHA, hCaptcha)
- AI extractor: entity extraction, summarizer, sentiment analyzer (OpenAI + Anthropic/Claude)
- Scrapy-style project interface
- Node-reverse client for JS-encrypted sites
- Session pool management
- Graph crawler
- REST API server and web console
- Checkpoint and incremental crawl support
- SSRF protection
- Audit trail module
- Research runtime and notebook output
- Async runtime facade
- Workflow engine
- Event bus
- Feature gates

### Media Coverage

- HLS / DASH parsing and download
- FFmpeg utilities
- DRM inspection
- YouTube, Bilibili, IQIYI, Tencent Video, Youku, Douyin (dedicated extractors)

### Distributed

- Redis (native), RabbitMQ (broker-native), Kafka (broker-native)
- Distributed workers with state machine
- Node discovery: env, file, DNS-SRV, Consul, etcd
- Dataset mirror to SQLite, Postgres, MySQL, MongoDB (process adapters)

### Install

| OS | Script |
| --- | --- |
| Windows | `scripts\windows\install-gospider.bat` |
| Linux | `scripts/linux/install-gospider.sh` |
| macOS | `scripts/macos/install-gospider.sh` |

**Output:** `gospider` executable (directly deployable binary)

### Best Fit

- Binary-first deployment
- High-concurrency runtime workloads
- Worker / queue / storage-based crawler execution
- Service-side crawling with operational monitoring

---

## RustSpider

RustSpider is the strongest runtime for high performance and strict runtime boundaries. It uses feature gates to control which modules are compiled into the release binary.

### Core Functions

- Rust release binary with feature-gated modules
- Typed scrapy-style interface
- Feature-gated browser, distributed, API, and web modules
- Preflight validation and contract-heavy runtime
- Anti-bot module with WAF bypass
- Captcha solver: 2captcha, Anti-Captcha, reCAPTCHA, hCaptcha, image captcha (real async API flow)
- AI modules: entity extraction, summarizer, sentiment analyzer (OpenAI + Anthropic/Claude)
- Few-shot examples
- XPath suggestion studio
- Node-reverse client for JS-encrypted sites
- Distributed queue backends: Redis (native), RabbitMQ (bridge), Kafka (bridge)
- Storage backends: SQLite, Postgres, MySQL, MongoDB (driver + process adapters)
- Node discovery: env, file, DNS-SRV, Consul, etcd
- Checkpoint and incremental crawl support
- SSRF protection
- Audit trail module (in-memory, file, composite)
- Benchmark suite
- Workflow engine
- Event bus
- Feature gates
- Research runtime and notebook output
- Async runtime

### Browser Automation

- Playwright: native `node + playwright` process surface (old helper as fallback)
- Selenium: fantoccini facade (native WebDriver)
- Browser pool and session management

### Media Coverage

- HLS / DASH parsing and download
- FFmpeg utilities
- DRM inspection
- YouTube, Bilibili, IQIYI, Tencent Video, Youku, Douyin
- Recognizes mirrored and replay-style IQIYI / Tencent URL shapes

### Install

| OS | Script |
| --- | --- |
| Windows | `scripts\windows\install-rustspider.bat` |
| Linux | `scripts/linux/install-rustspider.sh` |
| macOS | `scripts/macos/install-rustspider.sh` |

**Output:** `rustspider/target/release/rustspider` (production-oriented release binary)

### Best Fit

- Performance-sensitive deployments
- Strongly typed runtime boundaries
- Teams that want feature-gated release control
- High-throughput crawling with strict resource management

---

## JavaSpider

JavaSpider is the strongest fit for browser workflows and enterprise Java integration. It has the most dedicated audit trail support.

### Core Functions

- Maven / JAR packaging with `lite / ai / browser / distributed / full` profiles
- Browser workflows with Selenium (native) and Playwright (Java helper)
- Scrapy-style compatibility layer
- Audit trail module (strongest in the set: dedicated, in-memory, file, composite)
- Connector, session, and anti-bot modules
- Workflow replay
- Media parsing: HLS, DASH, FFmpeg, DRM, platform parsers
- Distributed queue and worker runtime
- REST API server: `/health`, `/jobs`, `/jobs/{id}`, `/jobs/{id}/result`
- Checkpoint and incremental crawl support
- AI extractor: entity extraction, summarizer, sentiment analyzer (OpenAI + Anthropic/Claude)
- Few-shot examples
- XPath suggestion studio
- Node-reverse client for JS-encrypted sites
- Async spider runtime
- Workflow engine
- Event bus
- Feature gates
- curl-to-Java converter

### Media Coverage

- HLS / DASH parsing and download
- FFmpeg utilities
- DRM inspection
- YouTube, Bilibili, IQIYI, Tencent Video, Youku, Douyin
- Generic-parser fallback when specialized parser is unavailable

### Distributed

- Redis (native), RabbitMQ (broker-native via amqp-client), Kafka (broker-native via kafka-clients)
- Distributed workers
- Node discovery: env, file, DNS-SRV, Consul, etcd
- Dataset mirror to database backends

### Maven Profiles

| Profile | Included modules |
| --- | --- |
| `lite` | core crawling only |
| `ai` | core + AI extraction |
| `browser` | core + browser automation |
| `distributed` | core + distributed runtime |
| `full` | all modules |

### Install

| OS | Script |
| --- | --- |
| Windows | `scripts\windows\install-javaspider.bat` |
| Linux | `scripts/linux/install-javaspider.sh` |
| macOS | `scripts/macos/install-javaspider.sh` |

**Output:** `javaspider/target` Maven build artifacts and JAR

### Best Fit

- Enterprise Java environments
- Browser-heavy workflow automation
- Maven / JAR delivery chains
- Audit-conscious execution with dedicated audit trail

---

## Related Docs

- `docs/FRAMEWORK_CAPABILITY_MATRIX.md` — full capability comparison table
- `docs/SUPERSPIDER_INSTALLS.md` — install matrix and prerequisites
- `MEDIA_PARITY_REPORT.md` — media platform coverage evidence
- `LATEST_FRAMEWORK_COMPLETION_REPORT.md` — latest completion status
- `ADVANCED_USAGE_GUIDE.md` — advanced crawling scenarios
- `ENCRYPTED_SITE_CRAWLING_GUIDE.md` — JS-encrypted site crawling
- `NODE_REVERSE_INTEGRATION_GUIDE.md` — Node.js reverse engineering integration
- `ULTIMATE_ENHANCEMENT_GUIDE.md` — full capability enhancement reference
