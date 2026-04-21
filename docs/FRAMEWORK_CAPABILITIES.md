# SuperSpider Framework Capabilities

Updated: 2026-04-21

This document replaces the previous deep-scan dump with a source-aligned summary.

Status vocabulary used here:

- `Implemented`: present in code as a real runtime surface
- `Conditional`: depends on API keys, feature gates, external services, or specific config
- `Fallback`: available, but may silently degrade to heuristic or compatibility behavior
- `Caveat`: present, but the implementation boundary matters and should not be overstated

---

## Shared Capability Surface

The four runtimes all implement the following broad areas:

- HTTP + browser crawling
- anti-bot helpers, captcha-related utilities, and SSRF protection
- media parsing/downloading for mainstream video formats
- NodeReverse integration for crypto / anti-bot / browser-emulation workflows
- distributed or queue-backed execution paths
- audit, artifact, checkpoint, and runtime-control surfaces
- scrapy-style or project-style authoring interfaces

What is not shared equally is maturity. Several capabilities exist in every runtime but differ in depth or runtime guarantees.

---

## PySpider

### Strength Profile

- Best for project authoring, AI scaffolding, and Python-side workflow flexibility
- Richest CLI surface for project lifecycle work
- Strong artifact-oriented analysis flow

### Implemented

- Unified CLI with `crawl`, `browser`, `ai`, `media`, `workflow`, `scrapy`, `ultimate`, `anti-bot`, `node-reverse`, `console`, `audit`, `jobdir`, `http-cache`, `capabilities`
- Scrapy-style project flows including `plan-ai`, `sync-ai`, `auth-validate`, `auth-capture`, `scaffold-ai`, `genspider`, `init`, and `contracts`
- CookieJar with persistence, Netscape export/import, expiry cleanup, and domain-aware matching
- Graph extraction and graph artifact generation
- Dataset writing, audit sinks, runtime notebook output, and control-plane files
- Artifact-driven media parsing from browser HTML / network / HAR outputs
- Feature gates for `ai`, `browser`, `distributed`, `media`, `workflow`, and `crawlee`

### Conditional

- LLM-backed AI extraction depends on configured API keys
- Some project authoring flows depend on optional graph or browser dependencies
- NodeReverse workflows depend on the external reverse service being reachable

### Fallback

- The `ai` CLI falls back to heuristic extraction when no compatible key is configured
- `node_reverse/fetcher.py` contains a minimum compatibility fallback that degrades to plain `requests`

### Caveats

- `advanced.ultimate.simulate_browser()` is not a full browser runtime; it performs HTTP fetch plus reverse-service simulation
- A capability being listed under `capabilities` output does not always mean the strongest implementation path is active in the current environment

---

## GoSpider

### Strength Profile

- Best for binary deployment, concurrency, queue/storage integration, and artifact-rich browser execution
- Strong operational surface with explicit runtime control paths
- Broadest browser artifact output in normal runtime usage

### Implemented

- Unified CLI with `crawl`, `browser`, `ai`, `media`, `workflow`, `scrapy`, `ultimate`, `anti-bot`, `node-reverse`, `research`, `console`, `audit`, `jobdir`, `http-cache`, `doctor`, `preflight`
- Feature gates for `ai`, `browser`, `distributed`, `media`, `workflow`, and `crawlee`
- Browser runtime artifact capture for HTML, DOM, screenshot, console, network JSON, HAR, and realtime WebSocket/SSE messages
- Browser layer support for upload-input handling, same-origin iframe helper operations, and open Shadow DOM helper paths
- JobSpec/Workflow actions including `goto`, `wait`, `click`, `type`, `scroll`, `select`, `hover`, `eval`, `screenshot`, and `listen_network`
- Storage backends for file/process/SQL result and dataset stores
- Research runtime with `run`, `async`, `soak`, and notebook-style output
- Queue bridge support and native queue client construction
- Scrapy-style runtime with plugins, pipelines, spider middleware, downloader middleware, and browser fetch hooks

### Conditional

- AI extraction depends on configured provider credentials
- Queue backends beyond local/in-memory depend on external brokers or bridge endpoints
- Reverse and browser-simulation features depend on the NodeReverse service

### Fallback

- The `ai` CLI defaults to `heuristic-fallback` when no API key is available
- Some media parsers and filenames use fallback derivation when primary metadata is absent

### Caveats

- `ultimate.simulateBrowser()` is reverse-assisted emulation, not a real browser session bootstrap
- The repository still contains `monitor.go.corrupted` and `monitor.go.original`, which are stale artifacts and should not be read as active runtime implementations

---

## RustSpider

### Strength Profile

- Best for feature-gated delivery, typed control surfaces, contract-heavy runtime work, and advanced captcha/reverse recovery
- Strongest test-contract culture in the repository
- Good fit where explicit runtime boundaries matter

### Implemented

- Feature-gated modules for `browser`, `video`, `distributed`, `api`, `web`, `ai`, and `full`
- Unified CLI with `crawl`, `browser`, `ai`, `doctor`, `preflight`, `media`, `workflow`, `ultimate`, `scrapy`, `research`, `anti-bot`, `node-reverse`, `console`, `audit`, `jobdir`, `http-cache`, `capabilities`
- Browser tooling subcommands `fetch`, `trace`, `mock`, and `codegen`
- Browser manager support for upload-input handling, explicit frame switching, open Shadow DOM helper paths, and in-page WebSocket/EventSource collection
- Token-protected Web/API surfaces with task, artifact, log, graph, and research endpoints
- Advanced captcha recovery logic in ultimate paths, including challenge-field extraction
- Artifact store, audit trail, event bus, cookie jar, checkpoint manager, queue backends, and Redis lease handling
- Standalone preflight binary surface

### Conditional

- Many modules require the correct Cargo features to be enabled at build time
- AI extraction depends on configured providers and valid responses
- Reverse and browser-emulation flows depend on external NodeReverse service availability

### Fallback

- The `ai` CLI defaults to `heuristic-fallback` when AI is unavailable or the LLM output is unusable

### Caveats

- Several browser-simulation paths are reverse-assisted simulations, not full browser execution
- `checkpoint.rs` still contains panic-style failure handling for some filesystem initialization errors

---

## JavaSpider

### Strength Profile

- Best for enterprise Java packaging, Selenium workflow automation, audit-conscious execution, and Java-native integration
- Strongest browser workflow surface
- Good contract and control-plane coverage for a JVM runtime

### Implemented

- Unified CLI with `crawl`, `browser`, `ai`, `media`, `workflow`, `research`, `run`, `job`, `async-job`, `web`, `api`, `node-reverse`, `console`, `audit`, `jobdir`, `http-cache`, `doctor`, `preflight`, `capabilities`
- Selenium-backed workflow engine with network listening, extraction, screenshots, download steps, and captcha-aware context helpers
- Workflow replay and graph reconstruction
- Research runtime with sync and async modes
- Runtime contracts for fingerprints, autoscaled frontier, artifact store, middleware, proxy policy, session pool, and observability
- Performance modules for virtual-thread execution, connection pooling, adaptive throttling, and circuit breaking
- Distributed node discovery across env, file, DNS SRV, Consul, and Etcd
- NodeReverse plus Crawlee bridge integration

### Conditional

- AI extraction depends on configured provider keys/endpoints
- Some advanced anti-bot and reverse flows depend on the external reverse service

### Fallback

- Media paths often rely on generic parser fallback when platform-specific extraction is weak

### Caveats

- `com.javaspider.AntiBot` is only a lightweight proxy/UA helper; the richer anti-bot surface is the `antibot/` package
- `CaptchaSolver` mixes `null` returns and exceptions across failure paths
- Some ultimate browser-simulation flows are reverse-assisted emulation rather than real browser sessions

---

## Practical Selection

- Choose `pyspider` for authoring-heavy, AI-assisted, project-centric work
- Choose `gospider` for binary deployment, high-throughput services, and artifact-heavy browser/runtime operations
- Choose `rustspider` for feature-gated production delivery, typed control planes, and advanced reverse/captcha recovery
- Choose `javaspider` for Selenium workflow automation, JVM packaging, and enterprise integration

## Verification Notes

Current checked commands in this workspace:

- `pyspider`: `pytest -q tests/test_smoke.py tests/test_dependencies.py tests/test_cli.py -x`
- `gospider`: `go test ./...`
- `rustspider`: `cargo test --quiet --lib`, `cargo test --quiet --test readme_scorecard`, `cargo test --quiet --test preflight_scorecard`
- `javaspider`: `mvn -q -DskipTests package`, `mvn -q "-Dtest=SpiderRuntimeContractsTest,HtmlParserXPathContractTest,ReadmeContractTest" test`

Important boundary:

- `rustspider` full `cargo test --quiet` is substantially heavier than the targeted slices above and is better treated as a CI-tier check with a longer timeout budget.

For current caveats and known implementation gaps, see:

- [`../HIDDEN_CAPABILITIES_REPORT.md`](../HIDDEN_CAPABILITIES_REPORT.md)
- [`../FRAMEWORK_DEFECT_AUDIT.md`](../FRAMEWORK_DEFECT_AUDIT.md)
