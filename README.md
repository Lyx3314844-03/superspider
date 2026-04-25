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
- **Crawler type templates** — hydrated SPA, bootstrap JSON, infinite scroll, login session, and e-commerce search JobSpec starters
- **Site presets** — JD, Taobao, Tmall, Pinduoduo, Xiaohongshu, and Douyin Shop starter JobSpec templates
- **Spider class kits** — reusable spider class templates for PySpider, GoSpider, RustSpider, and JavaSpider
- **Native ecommerce crawler classes** — catalog/detail/review wrappers in all four runtimes, with browser-backed capture companions where the runtime supports them
- **Native ecommerce examples** — catalog/detail/review examples in all four runtimes with a JD fast path plus a `generic` fallback for unknown storefronts
- Proxy pool with health checking and automatic rotation
- Rate limiting, circuit breaker, deduplication
- Robots.txt compliance
- Session and cookie management
- Checkpoint and incremental crawl (resume interrupted crawls)
- **Priority-based crawling** — request priority queue with SQLite persistence
- **Multi-threaded execution** — thread pool, concurrent executor, async executor, rate-limited executor
- **Incremental crawling with ETag/Last-Modified** — content hash comparison, min-change interval enforcement, delta token generation
- **Cookie management** — per-domain cookie jar with SameSite, Secure, HttpOnly, auto-expiry, Netscape export/import
- **Persistent priority queue** — SQLite-backed with URL deduplication, priority sorting, visited tracking
- **Worker pool** — configurable thread pool with shutdown, wait, and statistics
- **Concurrent executor** — semaphore-controlled ThreadPoolExecutor with execute-many
- **Async executor** — asyncio.Semaphore-controlled async task execution
- **Rate-limited executor** — token bucket algorithm with wait and execute
- **Priority task queue** — heapq-based priority queue for task scheduling

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
- **Keyword extraction** — AI-powered keyword extraction from page content
- **Content classification** — AI categorization into predefined categories
- **Translation** — AI-powered content translation to target languages
- **Q&A over content** — ask questions about crawled page content with context

### 🛡️ Anti-Bot
- TLS fingerprint rotation (JA3/JA4 mimicry)
- Browser behavior simulation (mouse movement, scroll, reading pace)
- WAF and access-friction detection with compliant browser upgrade paths
- Night mode (reduced crawl rate during off-hours)
- **Access friction classifier**: shared `level`, `signals`, `recommended_actions`, `challenge_handoff`, and `capability_plan` across all four runtimes
- **HTTP response diagnostics**: PySpider `Response.meta["access_friction"]`, GoSpider `Response.AccessFriction`, RustSpider `Response.access_friction`, and JavaSpider `Page.getField("access_friction")`
- **Captcha and login challenge handling**: detect CAPTCHA/auth/risk-control pages, pause for authorized human access, persist session assets, and resume only after validation
- **Cloudflare/Akamai handling**: vendor profiling, browser-render recommendation, artifact capture, and stop conditions when access is denied
- **Browser fingerprint management**: Canvas, WebGL, font fingerprint generation with session persistence
- **Smart delay strategy**: adaptive frequency-based delay adjustment with human-like jitter
- **Cookie management**: per-domain cookie jar with automatic rotation
- SSRF protection (blocks internal network access, cloud metadata endpoints)
- **Input sanitization**: XSS prevention, HTML cleaning, dangerous character filtering
- **Block detection**: keyword-based block/ban detection with automatic proxy switching
- **Compliance boundary**: the framework does not promise automated CAPTCHA cracking, forced risk-control bypass, or access to private/login-gated data without authorization

### 🔒 Security & Reliability
- **SSRF protection**: blocks requests to private IPs, cloud metadata (169.254.169.254), loopback, multicast
- **URL validation**: protocol whitelisting, domain allowlist/blocklist, port restrictions, length limits
- **Input sanitization**: script tag removal, event handler stripping, HTML entity decoding, filename sanitization
- **Circuit breaker**: configurable failure threshold, half-open state recovery, prevents cascade failures
- **Retry strategies**: fixed, linear, exponential, exponential+jitter backoff with configurable status code handling
- **Failure classification**: automatic categorization (blocked, throttled, anti_bot, timeout, server, proxy)
- **Request fingerprinting**: SHA-256 fingerprints based on URL + method + headers + cookies + body
- **Content deduplication**: SHA-256 content hashing to avoid re-processing identical pages

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
- **Autoscaled frontier**: auto-adjusts concurrency based on latency and failure rate
- **Session pool**: reusable session slots with fingerprint profile + proxy affinity
- **Dead-letter queue**: failed requests after max retries are quarantined for inspection
- **Lease-based request dispatching**: TTL-gated leases with heartbeat renewal and domain inflight limits
- **Checkpoint persistence**: SQLite-backed checkpoint manager with auto-save intervals
- **Proxy scoring**: success/failure ratio-based proxy selection with automatic degradation
- **Middleware chain**: composable request/response processing pipeline

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
- **Structured event logging**: trace-id correlated events with Prometheus text and OpenTelemetry export
- **Observability collector**: request latency tracking, failure classification, outcome histograms
- **Artifact store**: filesystem-based artifact storage for screenshots, traces, JSON snapshots, HTML
- **Graph artifact persistence**: per-page DOM graph (nodes, edges, stats) saved automatically during crawl
- **Frontier state snapshot**: pending, known, leases, domain-inflight, dead-letters all exportable as JSON
- **Dashboard API**: `/api/v1/monitors/<name>/dashboard` provides real-time crawl stats, performance metrics, resource usage
- **REST API server**: full spider lifecycle management via HTTP (start/stop/stats/queues/tasks)
- **API authentication**: Bearer token / X-API-Token support for production API security

### 🧭 Operator and Authoring Surface
- **Shared config scaffolding** — `config init` bootstraps the cross-runtime contract config
- **Site profiling** — `profile-site` emits `crawler_type`, `site_family`, `runner_order`, `strategy_hints`, and `job_templates`
- **Pre-crawl discovery** — `sitemap-discover` expands crawl candidates before you commit to selectors
- **Selector debugging** — `selector-studio` lets you validate CSS/XPath/regex rules against saved HTML
- **Control-plane tools** — `plugins`, `jobdir`, `http-cache`, `console`, and `audit` are public operator surfaces
- **Browser tooling** — `fetch`, `trace`, `mock`, and `codegen` are exposed in the browser CLI across the runtimes
- **Shared starter assets** — `examples/crawler-types/`, `examples/site-presets/`, and `examples/class-kits/` are the canonical starting points for hard site families
- **Research flows** — async research, notebook-style output, and scenario playbooks are part of the published runtime surface

## Public E-commerce Scope

The native ecommerce examples, crawler classes, and class kits are built for publicly accessible marketplace data.

They currently aim for:

- product links and identifiers
- price and promotion signals
- shop / seller signals
- review and rating summaries
- images, videos, embedded JSON, and API candidates

Current fast paths:

- `jd`: SKU extraction plus price/review public APIs
- `taobao`, `tmall`, `pinduoduo`, `amazon`: JSON-LD product / aggregate-rating fast paths when present
- `generic`: fallback public-data extraction for unknown storefronts

Each runtime now exposes a unified ecommerce crawler class style entrypoint, plus a browser-backed companion in the runtimes that support full browser capture. The naming is intentionally consistent so the examples can be lifted into a project with minimal translation.

They do not guarantee universal extraction across every storefront and they do not imply access to login-gated, private, or user-owned commerce data.

---

## 🐍 PySpider — AI-First Python Crawler

**Best for:** AI-powered extraction, rapid prototyping, research workflows

### Unique Capabilities
- **Smart parser** — automatically detects page type (article, product, listing, etc.) and extracts relevant fields without writing selectors
- **Schema-driven LLM extraction** — define a JSON schema, get structured output from any page
- **Graph crawler** — crawl relationship graphs, extract nodes and edges; REST API `/api/v1/graph/extract`
- **Research runtime** — Jupyter-style notebook output for data analysis
- **Plugin injection** — extend any part of the pipeline with Python plugins
- **Async runtime** — full async/await support with aiohttp
- **REST API server** — Flask-based server with spider start/stop, task management, queue control, monitoring dashboards, and metrics
- **Advanced anti-bot** — browser fingerprint generation (Canvas, WebGL, fonts), TLS profile management, captcha detection/handling, human behavior simulation (mouse trajectories, scroll, reading time), smart delay strategy
- **Cloudflare & Akamai bypass** — specialized header profiles for major WAFs
- **Security suite** — SSRF protection (blocks private IPs, cloud metadata), URL validation (protocol/domain/port whitelisting), input sanitization (XSS prevention, HTML cleaning)
- **Circuit breaker** — configurable failure threshold with half-open recovery, prevents cascade failures
- **Retry strategies** — fixed, linear, exponential, exponential+jitter backoff with async support
- **Failure classification** — automatic categorization: blocked, throttled, anti_bot, timeout, server, proxy, runtime
- **Autoscaled frontier** — auto-adjusts concurrency based on latency and failure rate with dead-letter queue
- **Session pool** — reusable session slots with fingerprint profile + proxy affinity, max 32 sessions
- **Middleware chain** — composable request/response processing pipeline
- **Request fingerprinting** — SHA-256 fingerprints from URL + method + headers + cookies + body + meta
- **Artifact store** — filesystem storage for screenshots, traces, JSON, HTML with metadata
- **Prometheus + OTel export** — metrics export in Prometheus text format and OpenTelemetry payload
- **Robots.txt compliance** — crawl-delay respect and disallow enforcement
- **Curl converter** — convert curl commands to spider requests
- **Production config** — multi-environment configuration with validation
- **Crawler type playbook** — `docs/CRAWLER_TYPE_PLAYBOOK.md` plus `examples/crawler-types/`

### Install
```bash
# Install all four runtimes
scripts\windows\install-superspider.bat
bash scripts/linux/install-superspider.sh
bash scripts/macos/install-superspider.sh

# Install only PySpider
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
- **Browser automation** — Chrome browser pool with lifecycle management, auto-restart on failure, graceful shutdown
- **WAF bypass suite** — Cloudflare, Akamai, Alibaba Cloud, Tencent Cloud specialized bypass strategies
- **Anti-detection** — stealth mode, WebDriver property removal, Chrome automation flag masking
- **TLS fingerprint rotation** — JA3/JA4 mimicry profiles for different browsers
- **Behavior simulation** — mouse movement, reading pace, scroll patterns
- **DASH media downloader** — HTTP range-based segment download with parallel workers, FFmpeg merge, retry logic
- **Distributed node reverse** — Node.js bridge with managed subprocess lifecycle
- **Task engine** — task creation, execution, status tracking, result storage
- **Scheduler** — Cron-based scheduling, one-time tasks, interval tasks, concurrent management
- **Event system** — structured events, priority queue, dispatcher, subscriber model
- **Monitor suite** — performance monitoring, resource tracking, health checks, alerting
- **Extractor framework** — XPath, CSS selector, regex, JSONPath extraction with validation
- **Proxy rotation** — proxy pool with health checking, automatic failover
- **Rate limiting** — token bucket, sliding window, adaptive rate control
- **Config-driven crawling** — JSON-based spider configuration, template-driven execution

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
- **Encrypted site crawler** — HMAC-SHA256, AES-encrypted params, timestamp token generation
- **Media downloader** — HLS/DASH with FFmpeg integration, segment tracking, progress reporting
- **Async runtime** — tokio-based async execution with cancellation support
- **Distributed worker** — Redis-based task distribution with worker heartbeat
- **Proxy rotation** — proxy pool with success rate scoring, automatic failover
- **Task scheduler** — cron-based scheduling with execution history
- **Performance monitor** — resource usage tracking, latency histograms, throughput metrics
- **Transformer pipeline** — composable data transformation stages
- **Node reverse** — Node.js subprocess management for JS signature execution
- **FFI bindings** — C-compatible interface for embedding in other languages
- **API server** — HTTP API for spider control and status querying
- **Artifact storage** — file-based artifact persistence with metadata

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
- **Adaptive rate limiter** — AI-guided rate control with latency-based backpressure
- **Batch media downloader** — concurrent download with progress tracking, retry, merge
- **User-agent rotator** — browser-specific UA pools with header consistency
- **Connector framework** — pluggable database connectors (SQLite, PostgreSQL, MySQL, MongoDB)
- **CLI interface** — command-line spider execution with config loading
- **Bridge module** — cross-runtime communication bridge
- **Session management** — cookie jar, session persistence across requests
- **Media pipeline** — YouTube, Bilibili, IQIYI, Tencent, Youku, Douyin with format detection
- **Workflow engine** — DAG-based workflow execution with conditional branching

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
| 🐍 PySpider | Python 3.10+ recommended, pip, venv |
| 🐹 GoSpider | Go 1.24+ |
| 🦀 RustSpider | Rust 1.70+ recommended, Cargo |
| ☕ JavaSpider | Java 17 target, Maven 3.8+ |

Supported installer operating systems: Windows 10/11 or Windows Server 2022+, Ubuntu/Debian/RHEL-compatible Linux, and macOS 13+. The current Windows verification host is Microsoft Windows 11 Pro 10.0.28000, 64-bit.

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
| REST API to control crawlers | 🐍 PySpider (Flask) or ☕ JavaSpider |
| Browser fingerprint management | 🐍 PySpider (Canvas, WebGL, fonts) |
| Circuit breaker + retry strategies | 🐍 PySpider (4 strategies + circuit breaker) |
| Cloudflare / Akamai bypass | 🐍 PySpider or 🐹 GoSpider |
| SSRF protection + input sanitization | 🐍 PySpider |
| Workflow automation (DAG) | ☕ JavaSpider |
| Feature-gated compilation | 🦀 RustSpider |
| Single binary deployment | 🐹 GoSpider |
| Prometheus / OTel metrics export | 🐍 PySpider |
| Graph crawling + relationship extraction | 🐍 PySpider |
| Session pool management | 🐍 PySpider (32 sessions with fingerprint affinity) |
| Autoscaled concurrency | 🐍 PySpider (frontier-based auto-scaling) |

---

## 📚 Documentation

| Document | Description |
| --- | --- |
| [`docs/DOCS_INDEX.md`](docs/DOCS_INDEX.md) | Canonical documentation index and recommended reading order |
| [`docs/FRAMEWORK_CAPABILITIES.md`](docs/FRAMEWORK_CAPABILITIES.md) | Detailed per-framework capability descriptions |
| [`docs/FRAMEWORK_CAPABILITY_MATRIX.md`](docs/FRAMEWORK_CAPABILITY_MATRIX.md) | Full capability comparison tables |
| [`docs/ACCESS_FRICTION_PLAYBOOK.md`](docs/ACCESS_FRICTION_PLAYBOOK.md) | High-friction crawl model, challenge handoff, and compliant recovery policy |
| [`docs/CRAWL_SCENARIO_GAP_MATRIX.md`](docs/CRAWL_SCENARIO_GAP_MATRIX.md) | Real crawling scenarios that are still partial or missing across the four runtimes |
| [`docs/LATEST_SCENARIO_CASES.md`](docs/LATEST_SCENARIO_CASES.md) | Latest practical scenario playbooks and recommended runtime choices |
| [`docs/CRAWLER_TYPE_PLAYBOOK.md`](docs/CRAWLER_TYPE_PLAYBOOK.md) | Shared crawler types, runner-order guidance, and JobSpec template mapping |
| [`docs/SITE_PRESET_PLAYBOOK.md`](docs/SITE_PRESET_PLAYBOOK.md) | Site-family starter presets for major marketplace and social-commerce domains |
| [`examples/class-kits/README.md`](examples/class-kits/README.md) | Reusable spider class templates for all four runtimes |
| [`docs/SUPERSPIDER_INSTALLS.md`](docs/SUPERSPIDER_INSTALLS.md) | Install instructions for Windows, Linux, and macOS |
| [`docs/FOUR_RUNTIME_HEALTH_REPORT.md`](docs/FOUR_RUNTIME_HEALTH_REPORT.md) | Current compile, dependency, and test status for all four runtimes |
| [`MEDIA_PARITY_REPORT.md`](MEDIA_PARITY_REPORT.md) | Media platform coverage evidence |
| [`ADVANCED_USAGE_GUIDE.md`](ADVANCED_USAGE_GUIDE.md) | Advanced crawling scenarios |
| [`ENCRYPTED_SITE_CRAWLING_GUIDE.md`](ENCRYPTED_SITE_CRAWLING_GUIDE.md) | JS-encrypted site crawling |
| [`NODE_REVERSE_INTEGRATION_GUIDE.md`](NODE_REVERSE_INTEGRATION_GUIDE.md) | Node.js reverse engineering bridge |
| [`ULTIMATE_ENHANCEMENT_GUIDE.md`](ULTIMATE_ENHANCEMENT_GUIDE.md) | Full capability enhancement reference |
| [`PUBLISH_RELEASE_STATUS.md`](PUBLISH_RELEASE_STATUS.md) | Publish-time verification status and release notes |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution guide |

---

## ✅ Verification Snapshot

Checked against the current workspace on **2026-04-25**:

| Runtime | Verified command(s) | Current result |
| --- | --- | --- |
| 🐍 PySpider | `python -m pytest tests\test_access_friction.py tests\test_locator_analyzer.py tests\test_super_framework.py tests\test_api_server.py tests\test_core_spider.py tests\test_downloader.py -q` | Pass, 40 tests |
| 🐹 GoSpider | `go test ./...` | Pass |
| 🦀 RustSpider | `cargo test --quiet --lib`, `cargo test --quiet --test access_friction` | Pass on checked slices; full suite is heavy and should be run in CI with a longer timeout window |
| ☕ JavaSpider | `mvn -q test`, `mvn -q -Dtest=HtmlSelectorContractTest test` | Pass |

Notes:

- The four runtimes now share access-friction detection for high-risk pages, browser-upgrade planning, XPath/CSS locator helpers, and browser/devtools-oriented element analysis.
- PySpider full-suite success is not claimed here because an earlier broad `pytest -q` run exceeded the local timeout window; use CI with longer timeouts for unrestricted release coverage.

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
