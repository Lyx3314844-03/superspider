# SuperSpider Framework Capabilities

Updated: 2026-04-19

---

## Shared Capabilities (All Four Runtimes)

Before diving into per-framework details, every runtime ships with:

- HTTP + browser hybrid crawling
- Scrapy-style project interface
- Proxy pool with health checking and rotation
- Rate limiting and circuit breaker
- Session and cookie management
- Checkpoint and incremental crawl (resume interrupted jobs)
- Robots.txt compliance
- Anti-bot: WAF bypass, behavior simulation, night mode
- Captcha solving: 2captcha, Anti-Captcha, reCAPTCHA, hCaptcha, image captcha
- SSRF protection
- AI extraction: entity, summarizer, sentiment (OpenAI + Anthropic/Claude)
- Few-shot LLM examples
- XPath suggestion studio
- Node-reverse client for JS-encrypted sites
- Media download: YouTube, Bilibili, IQIYI, Tencent Video, Youku, Douyin, HLS, DASH, FFmpeg, DRM
- Distributed: Redis, RabbitMQ, Kafka
- Node discovery: env, file, DNS-SRV, Consul, etcd
- Web UI, REST API server, Docker support
- Workflow engine, event bus, feature gates
- curl-to-code converter

---

## 🐍 PySpider — Python Runtime

### Philosophy
PySpider is built for developers who want to move fast. It prioritizes developer experience, AI integration, and flexibility over raw performance. If you need to go from idea to working crawler in minutes, or if you want to use LLMs to extract structured data from any page, PySpider is the right choice.

### Core Architecture

```
python -m pyspider [command]
├── CLI entry point
├── Scrapy-style Spider class
│   ├── start_requests()
│   ├── parse() callbacks
│   └── plugin injection hooks
├── AI pipeline
│   ├── LLMExtractor (OpenAI / Anthropic)
│   ├── SmartParser (auto page-type detection)
│   ├── EntityExtractor
│   ├── ContentSummarizer
│   └── SentimentAnalyzer
├── Browser layer
│   └── Playwright (native async)
├── Media layer
│   ├── VideoParser (YouTube, Bilibili, IQIYI, Tencent, Youku, Douyin)
│   ├── HLSDownloader
│   ├── DASHDownloader
│   └── FFmpegTools
├── Distributed layer
│   ├── RedisQueue (native)
│   ├── RabbitMQ / Kafka
│   └── RedisDistributed workers
└── Output layer
    ├── DatasetWriter (JSON, CSV, JSONL, Markdown)
    ├── KVStore
    └── RequestQueue (SQLite-backed)
```

### Unique Capabilities

**Smart Parser** — PySpider's most distinctive feature. Pass any URL and it automatically detects the page type (article, product listing, search results, social post, etc.) and extracts the relevant fields without writing a single selector.

```python
from pyspider.ai_extractor.smart_parser import SmartParser
parser = SmartParser()
result = parser.parse(html_content)
# Returns: {"type": "article", "title": "...", "content": "...", "author": "..."}
```

**Schema-Driven LLM Extraction** — Define a JSON schema and get strongly typed structured output from any page using GPT-4o or Claude.

```python
from pyspider.ai_extractor.llm_extractor import LLMExtractor
extractor = LLMExtractor(model="gpt-4o", api_key="...")
result = extractor.extract(html, schema={
    "product_name": "str",
    "price": "float",
    "in_stock": "bool",
    "reviews": "list[str]"
})
```

**Graph Crawler** — Crawl relationship graphs (social networks, knowledge graphs, org charts) and extract nodes and edges.

```python
from pyspider.graph_crawler.graph_builder import GraphBuilder
builder = GraphBuilder()
graph = builder.build(start_url, depth=3)
# Returns: {"nodes": [...], "edges": [...]}
```

**Research Runtime** — Jupyter-style notebook output for data analysis and exploration.

**Checkpoint Manager** — SQLite-backed checkpoint system. Interrupted crawls resume exactly where they left off.

```python
from pyspider.core.checkpoint import CheckpointManager
manager = CheckpointManager(checkpoint_dir="./checkpoints")
spider = Spider(checkpoint=manager)
spider.resume()  # continues from last saved state
```

**Plugin Injection** — Extend any part of the pipeline with Python plugins. Add custom middleware, extractors, or output writers without modifying core code.

### Install

```bash
# Windows
scripts\windows\install-pyspider.bat

# Linux
bash scripts/linux/install-pyspider.sh

# macOS
bash scripts/macos/install-pyspider.sh
```

**Output:** `.venv-pyspider`

**Verify:** `source .venv-pyspider/bin/activate && python -m pyspider version`

### Best Fit
- AI-powered extraction with LLM
- Rapid prototyping and research
- Data science workflows with notebook output
- Teams that want Python flexibility

---

## 🐹 GoSpider — Go Runtime

### Philosophy
GoSpider is built for production. It compiles to a single binary with no runtime dependencies, making it trivial to deploy anywhere — containers, VMs, bare metal. It excels at high-concurrency crawling and distributed worker clusters.

### Core Architecture

```
gospider [command]
├── CLI entry point (compiled binary)
├── Core engine
│   ├── Spider (concurrent, rate-limited)
│   ├── Scheduler (job queue + priority)
│   ├── ProxyPool (health-checked rotation)
│   └── RateLimiter (token bucket)
├── Browser layer
│   ├── BrowserPool (Playwright)
│   ├── SeleniumClient (native WebDriver)
│   └── BehaviorSimulator
├── AI layer
│   ├── AIExtractor (OpenAI + Anthropic/Claude)
│   ├── EntityExtractor
│   ├── ContentSummarizer
│   └── SentimentAnalyzer
├── Media layer
│   ├── extractors/bilibili
│   ├── extractors/iqiyi
│   ├── extractors/tencent
│   ├── extractors/youku
│   ├── extractors/douyin
│   ├── HLSDownloader
│   ├── DASHDownloader
│   └── FFmpegWrapper
├── Distributed layer
│   ├── RedisClient (native)
│   ├── RabbitMQ (broker-native amqp)
│   ├── Kafka (broker-native)
│   ├── Worker (state machine)
│   └── NodeDiscovery (env/file/dns-srv/consul/etcd)
├── Storage layer
│   ├── SQLiteStore
│   ├── ProcessResultStore (Postgres/MySQL/MongoDB)
│   ├── SQLResultStore (driver-level)
│   └── DatasetMirror
└── Observability
    ├── AuditTrail (memory/file/composite)
    ├── Monitor
    └── APIServer
```

### Unique Capabilities

**Single Binary Deployment** — `go build ./cmd/gospider` produces one binary. Copy it to any Linux/macOS/Windows machine and run. No Python, no JVM, no Node.js required.

**Native Selenium/WebDriver Client** — Direct WebDriver protocol implementation in Go. No wrapper overhead, no external dependencies.

```go
client := browser.NewSeleniumClient("http://localhost:4444")
session, _ := client.NewSession()
session.Navigate("https://example.com")
html, _ := session.GetPageSource()
```

**Dedicated Platform Extractors** — Each video platform has its own Go package with focused tests:

```
gospider/extractors/
├── bilibili/   — B站 (BV号, cid, DASH/HLS)
├── iqiyi/      — 爱奇艺 (vid, tm, HLS/DASH)
├── tencent/    — 腾讯视频 (vid, direct link)
├── youku/      — 优酷 (vid, HLS/DASH)
└── douyin/     — 抖音 (aweme_id, MP4)
```

**Broker-Native Queue Clients** — RabbitMQ and Kafka via native Go clients, not HTTP bridges. Lower latency, higher throughput.

**Process + Driver DB Adapters** — Two levels of database integration:
- Process adapter: spawns a subprocess (works with any DB that has a CLI)
- Driver adapter: native Go database driver (lower latency)

**Audit Trail Module** — Structured audit logging with composite writers. Every request, response, and extraction event is logged with timestamps and metadata.

### Install

```bash
# Windows
scripts\windows\install-gospider.bat

# Linux
bash scripts/linux/install-gospider.sh

# macOS
bash scripts/macos/install-gospider.sh
```

**Output:** `gospider/gospider` (or `gospider.exe` on Windows)

**Verify:** `./gospider/gospider --version`

### Best Fit
- High-concurrency production crawling
- Binary deployment (containers, VMs, bare metal)
- Distributed worker clusters
- Service-oriented crawler with operational monitoring

---

## 🦀 RustSpider — Rust Runtime

### Philosophy
RustSpider is built for teams that need maximum performance and strict resource boundaries. Rust's ownership model eliminates entire classes of bugs (memory leaks, data races, null pointer dereferences) at compile time. Feature gates let you compile only the modules you need, keeping the binary small and the attack surface minimal.

### Core Architecture

```
rustspider [command]
├── CLI entry point (release binary)
├── Feature-gated modules
│   ├── [browser] — Playwright + Selenium
│   ├── [distributed] — Redis/RabbitMQ/Kafka + workers
│   ├── [api] — REST API server
│   └── [web] — Web UI
├── Core engine
│   ├── Spider (async, typed)
│   ├── Scheduler
│   ├── ProxyPool
│   └── RateLimiter
├── Browser layer
│   ├── PlaywrightProcess (native node+playwright subprocess)
│   ├── SeleniumFacade (fantoccini async WebDriver)
│   └── BrowserPool
├── AI layer
│   ├── AIClient (OpenAI + Anthropic/Claude + few-shot)
│   ├── EntityExtractor
│   ├── ContentSummarizer
│   └── SentimentAnalyzer
├── Captcha layer
│   ├── TwoCaptchaClient (async API + polling)
│   ├── AntiCaptchaClient (async API + polling)
│   └── Solver (reCAPTCHA v2/v3, hCaptcha, image)
├── Media layer
│   ├── VideoParser (YouTube/Bilibili/IQIYI/Tencent/Youku/Douyin)
│   ├── HLSDownloader
│   ├── DASHDownloader
│   └── DRMDetector
├── Distributed layer
│   ├── RedisQueue (native)
│   ├── RabbitMQBridge
│   ├── KafkaBridge
│   ├── Worker
│   └── NodeDiscovery
├── Storage layer
│   ├── SQLiteStore
│   ├── ProcessResultStore (Postgres/MySQL/MongoDB)
│   ├── DriverResultStore (native Rust drivers)
│   └── DatasetMirror
└── Observability
    ├── AuditTrail (memory/file/composite)
    ├── Preflight (validate all deps before start)
    └── Benchmarks
```

### Unique Capabilities

**Feature Gates** — Compile only what you need. The `Cargo.toml` defines features that control which modules are included:

```toml
# Minimal build (core crawling only)
cargo build --release

# With browser support
cargo build --release --features browser

# With distributed runtime
cargo build --release --features distributed

# Everything
cargo build --release --features full
```

**Native node+playwright Process** — Playwright runs as a managed subprocess, not a wrapper. RustSpider spawns a Node.js process, communicates via stdio, and manages its lifecycle. This gives full Playwright capability without embedding a JS runtime in Rust.

**Real Async Captcha API** — Not a placeholder. The captcha solver makes real HTTP calls to 2captcha/Anti-Captcha APIs with proper async polling:

```rust
let solver = TwoCaptchaClient::new(api_key);
let token = solver.solve_recaptcha(RecaptchaTask {
    website_url: "https://example.com",
    website_key: "6Le...",
}).await?;
// Polls until solved, handles timeouts and retries
```

**Driver-Level DB Adapters** — Native Rust database drivers (not subprocess wrappers):
- `sqlx` for PostgreSQL and MySQL
- `mongodb` crate for MongoDB
- Lower latency, proper connection pooling, compile-time query checking

**Preflight Validation** — Before starting any crawl, RustSpider validates all configuration and dependencies:
- Checks proxy connectivity
- Validates database connections
- Verifies browser binary exists
- Tests queue backend connectivity
- Reports all issues before wasting time on a broken crawl

**Benchmark Suite** — Built-in benchmarks using Criterion.rs for measuring crawl throughput, extraction speed, and queue performance.

### Install

```bash
# Windows
scripts\windows\install-rustspider.bat

# Linux
bash scripts/linux/install-rustspider.sh

# macOS
bash scripts/macos/install-rustspider.sh
```

**Output:** `rustspider/target/release/rustspider`

**Verify:** `./rustspider/target/release/rustspider --version`

### Best Fit
- Performance-sensitive production deployments
- Teams that want compile-time safety guarantees
- Feature-gated release control (ship only what you need)
- High-throughput crawling with strict memory bounds

---

## ☕ JavaSpider — Java Runtime

### Philosophy
JavaSpider is built for enterprise environments. It integrates naturally into existing Java/Maven build pipelines, works with enterprise authentication systems, and provides the most comprehensive audit trail in the set. If your organization runs on Java and needs a crawler that fits into your existing toolchain, JavaSpider is the right choice.

### Core Architecture

```
javaspider [command]
├── Maven build (lite/ai/browser/distributed/full profiles)
├── CLI entry point (JAR)
├── Core engine
│   ├── Spider (thread-pool based)
│   ├── Scheduler
│   ├── ProxyPool
│   └── RateLimiter
├── Browser layer
│   ├── SeleniumManager (native WebDriver)
│   ├── PlaywrightHelper (Java wrapper)
│   ├── BrowserPool
│   └── WorkflowReplay
├── AI layer
│   ├── AIExtractor (OpenAI + Anthropic/Claude + few-shot)
│   ├── EntityExtractor
│   ├── ContentSummarizer
│   └── SentimentAnalyzer
├── Media layer
│   ├── BilibiliParser
│   ├── IqiyiParser
│   ├── TencentParser
│   ├── DouyinParser
│   ├── GenericParser (fallback for all platforms)
│   └── DRMChecker
├── Distributed layer
│   ├── RedisQueue (native Jedis)
│   ├── RabbitMQQueue (amqp-client broker-native)
│   ├── KafkaQueue (kafka-clients broker-native)
│   ├── Worker
│   └── NodeDiscovery (env/file/dns-srv/consul/etcd)
├── Storage layer
│   ├── SQLiteStore
│   ├── PostgreSQLStore
│   ├── MySQLStore
│   └── MongoDBStore
├── Audit layer (strongest in the set)
│   ├── InMemoryAuditTrail
│   ├── FileAuditTrail (JSONL)
│   └── CompositeAuditTrail
└── API layer
    ├── GET  /health
    ├── GET  /jobs
    ├── GET  /jobs/{id}
    └── GET  /jobs/{id}/result
```

### Unique Capabilities

**Maven Profiles** — Build exactly what you need. No unused dependencies in your JAR:

```bash
# Core crawling only (~8MB JAR)
mvn -P lite -DskipTests package

# Core + AI extraction
mvn -P ai -DskipTests package

# Core + browser automation
mvn -P browser -DskipTests package

# Core + distributed runtime
mvn -P distributed -DskipTests package

# Everything (~45MB JAR)
mvn -P full -DskipTests package
```

**Dedicated Audit Trail** — The most comprehensive audit system in the set. Every request, response, extraction, and error is logged with full context:

```java
AuditTrail audit = new CompositeAuditTrail(
    new InMemoryAuditTrail(maxEntries: 10000),
    new FileAuditTrail("./audit.jsonl")
);
spider.setAuditTrail(audit);
// Every event is now logged to both memory and file
```

**Broker-Native Queue Clients** — RabbitMQ and Kafka via their official Java clients:
- RabbitMQ: `amqp-client` (official RabbitMQ Java client)
- Kafka: `kafka-clients` (official Apache Kafka client)

This means proper connection pooling, acknowledgment handling, and dead-letter queue support — not HTTP bridges.

**REST API Server** — Built-in HTTP server for monitoring and control:

```
GET /health          → {"status": "ok", "uptime": 3600}
GET /jobs            → [{"id": "...", "status": "running", "progress": 0.45}]
GET /jobs/{id}       → {"id": "...", "url": "...", "status": "done", "items": 1234}
GET /jobs/{id}/result → {"items": [...]}
```

**Workflow Replay** — Record a browser workflow (login, navigate, click, extract) and replay it on demand. Useful for sites that require complex authentication flows.

**Generic-Parser Fallback** — Media parsing never fails silently. If a platform-specific parser (Bilibili, IQIYI, etc.) fails to extract a usable URL, the `GenericParser` takes over and tries HTML-based extraction, inline JSON scanning, and manifest URL detection.

**Async Spider Runtime** — `AsyncSpiderRuntime` provides non-blocking execution using Java's `CompletableFuture` and thread pools, allowing thousands of concurrent requests without blocking threads.

### Install

```bash
# Windows
scripts\windows\install-javaspider.bat

# Linux
bash scripts/linux/install-javaspider.sh

# macOS
bash scripts/macos/install-javaspider.sh
```

**Output:** `javaspider/target/`

**Verify:** `java -jar javaspider/target/javaspider-*.jar --version`

### Best Fit
- Enterprise Java environments with existing Maven pipelines
- Browser-heavy automation with workflow replay
- Audit-conscious execution (compliance, logging requirements)
- Teams that need broker-native RabbitMQ/Kafka integration

---

## Related Docs

- [`docs/FRAMEWORK_CAPABILITY_MATRIX.md`](FRAMEWORK_CAPABILITY_MATRIX.md) — full capability comparison tables
- [`docs/SUPERSPIDER_INSTALLS.md`](SUPERSPIDER_INSTALLS.md) — install instructions for all three OS
- [`MEDIA_PARITY_REPORT.md`](../MEDIA_PARITY_REPORT.md) — media platform coverage evidence
- [`LATEST_FRAMEWORK_COMPLETION_REPORT.md`](../LATEST_FRAMEWORK_COMPLETION_REPORT.md) — latest completion status
