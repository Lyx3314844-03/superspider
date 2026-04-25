# SuperSpider Framework Capabilities

Updated: 2026-04-24

This is the canonical source-aligned capability summary for the GitHub-facing docs.

Status vocabulary used here:

- `Implemented`: present in code as a real runtime surface
- `Conditional`: depends on API keys, feature gates, external services, or specific config
- `Fallback`: available, but may silently degrade to heuristic or compatibility behavior
- `Caveat`: present, but the implementation boundary matters and should not be overstated

---

## Shared Capability Surface

The four runtimes all implement the following broad areas:

- HTTP plus browser crawling
- shared config scaffolding, preflight checks, and runtime capability reporting
- site profiling, crawler-type hints, site-family presets, and reusable starter assets
- class-based ecommerce crawler entrypoints plus browser capture companions in the four runtimes
- access-friction classification, challenge handoff, anti-bot helpers, captcha-related utilities, and SSRF protection
- media parsing/downloading for mainstream video formats
- NodeReverse integration for crypto, anti-bot, and browser-emulation workflows
- distributed or queue-backed execution paths
- audit, artifact, checkpoint, and runtime-control surfaces
- scrapy-style or project-style authoring interfaces

What is not shared equally is maturity. Several capabilities exist in every runtime but differ in depth, runtime guarantees, or operational polish.

---

## PySpider

### Strength Profile

- Best for project authoring, AI scaffolding, and Python-side workflow flexibility
- Richest CLI surface for project lifecycle work
- Strong artifact-oriented analysis flow

### Implemented

- Unified CLI with `config`, `crawl`, `doctor`, `preflight`, `media`, `web`, `version`, `browser`, `export`, `curl`, `job`, `async-job`, `workflow`, `capabilities`, `sitemap-discover`, `plugins`, `selector-studio`, `scrapy`, `profile-site`, `ultimate`, `ai`, `anti-bot`, `node-reverse`, `jobdir`, `http-cache`, `console`, and `audit`
- Browser tooling subcommands `fetch`, `trace`, `mock`, and `codegen`
- Scrapy-style project flows including `demo`, `run`, `export`, `profile`, `doctor`, `bench`, `shell`, `list`, `validate`, `plan-ai`, `sync-ai`, `auth-validate`, `auth-capture`, `scaffold-ai`, `genspider`, `init`, and `contracts`
- `profile-site`, `scrapy plan-ai`, and `scrapy scaffold-ai` emit `crawler_type`, `site_family`, `runner_order`, `strategy_hints`, and `job_templates`
- Shared starter assets under `examples/crawler-types/`, `examples/site-presets/`, and `examples/class-kits/`, plus native ecommerce examples under `pyspider/examples/`
- Native ecommerce crawler classes under `pyspider/examples/`, `gospider/examples/ecommerce/`, `rustspider/examples/ecommerce/`, and `com.javaspider.examples.ecommerce`
- CookieJar with persistence, Netscape export/import, expiry cleanup, and domain-aware matching
- Graph extraction, graph artifacts, dataset writing, audit sinks, runtime notebook output, and control-plane files
- Artifact-driven media parsing from browser HTML, network, and HAR outputs
- Feature gates for `ai`, `browser`, `distributed`, `media`, `workflow`, and `crawlee`
- Shared access-friction reporting via `pyspider.antibot.friction.analyze_access_friction`, including `challenge_handoff` and `capability_plan` for rate limits, WAF pages, CAPTCHA/login challenges, browser upgrade, session persistence, and stop conditions
- HTTP downloader responses expose the report at `Response.meta["access_friction"]`

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

- Unified CLI with `config`, `crawl`, `browser`, `export`, `curl`, `run`, `job`, `async-job`, `jobdir`, `http-cache`, `console`, `audit`, `capabilities`, `web`, `workflow`, `media`, `ultimate`, `ai`, `selector-studio`, `scrapy`, `sitemap-discover`, `plugins`, `profile-site`, `research`, `node-reverse`, `anti-bot`, `doctor`, and `preflight`
- Browser tooling subcommands `fetch`, `trace`, `mock`, and `codegen`
- `config`, `profile-site`, `sitemap-discover`, `selector-studio`, `plugins`, `jobdir`, `http-cache`, `console`, and `audit` are documented operator/control-plane tools rather than internal helpers
- Browser runtime artifact capture for HTML, DOM, screenshot, console, network JSON, HAR, and realtime WebSocket/SSE messages
- Native ecommerce crawler class wrapper plus browser capture companion for static/detail/review flows
- Browser layer support for upload-input handling, same-origin iframe helper operations, and open Shadow DOM helper paths
- JobSpec/workflow actions including `goto`, `wait`, `click`, `type`, `scroll`, `select`, `hover`, `eval`, `screenshot`, and `listen_network`
- Shared starter assets under the repo-level `examples/` tree, plus native ecommerce examples under `gospider/examples/ecommerce/`
- Native ecommerce crawler class wrapper plus `RunBrowser()` companion in `gospider/examples/ecommerce/`
- Storage backends for file, process, and SQL result/dataset stores
- Research runtime with `run`, `async`, `soak`, and notebook-style output
- Queue bridge support, native queue client construction, and scrapy-style runtime plugins/middlewares/browser fetch hooks
- Shared access-friction reporting via `antibot.AnalyzeAccessFriction`, including `challenge_handoff` and `capability_plan` for rate limits, WAF pages, CAPTCHA/login challenges, browser upgrade, session persistence, and stop conditions
- HTTP downloader responses expose the report at `Response.AccessFriction`

### Conditional

- AI extraction depends on configured provider credentials
- Queue backends beyond local/in-memory depend on external brokers or bridge endpoints
- Reverse and browser-simulation features depend on the NodeReverse service

### Fallback

- The `ai` CLI defaults to `heuristic-fallback` when no API key is available
- Some media parsers and filenames use fallback derivation when primary metadata is absent

### Caveats

- `ultimate.simulateBrowser()` is reverse-assisted emulation, not a real browser session bootstrap

---

## RustSpider

### Strength Profile

- Best for feature-gated delivery, typed control surfaces, contract-heavy runtime work, and advanced captcha/reverse recovery
- Strongest test-contract culture in the repository
- Good fit where explicit runtime boundaries matter

### Implemented

- Feature-gated modules for `browser`, `video`, `distributed`, `api`, `web`, `ai`, and `full`
- Unified CLI with `config`, `crawl`, `browser`, `ai`, `doctor`, `preflight`, `export`, `curl`, `run`, `job`, `async-job`, `workflow`, `jobdir`, `http-cache`, `console`, `audit`, `web`, `media`, `ultimate`, `sitemap-discover`, `plugins`, `selector-studio`, `scrapy`, `profile-site`, `research`, `node-reverse`, `anti-bot`, and `capabilities`
- Browser tooling subcommands `fetch`, `trace`, `mock`, and `codegen`
- Site profiling, sitemap discovery, selector debugging, plugin execution, and shared control-plane tooling are public entrypoints now
- Shared starter assets under the repo-level `examples/` tree, plus native ecommerce examples under `rustspider/examples/ecommerce/`
- Native ecommerce crawler class wrapper plus browser capture companion under `rustspider/examples/ecommerce_browser_capture.rs`
- Browser manager support for upload-input handling, explicit frame switching, open Shadow DOM helper paths, and in-page WebSocket/EventSource collection
- Token-protected Web/API surfaces with task, artifact, log, graph, and research endpoints
- Advanced captcha recovery logic in ultimate paths, including challenge-field extraction
- Artifact store, audit trail, event bus, cookie jar, checkpoint manager, queue backends, and Redis lease handling
- Standalone preflight binary surface
- Shared access-friction reporting via `rustspider::antibot::friction::analyze_access_friction`, including `challenge_handoff` and `capability_plan` for rate limits, WAF pages, CAPTCHA/login challenges, browser upgrade, session persistence, and stop conditions
- HTTP downloader responses expose the report at `Response.access_friction`

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

- Unified CLI with `config`, `crawl`, `browser`, `ai`, `doctor`, `preflight`, `export`, `curl`, `jobdir`, `http-cache`, `console`, `audit`, `node-reverse`, `web`, `run`, `research`, `workflow`, `media`, `job`, `async-job`, `sitemap-discover`, `plugins`, `selector-studio`, `scrapy`, `profile-site`, `anti-bot`, `capabilities`, `version`, and `help`
- Browser tooling subcommands `fetch`, `trace`, `mock`, and `codegen`
- Shared config generation, cache/jobdir management, console/audit views, site profiling, and selector debugging are part of the documented public surface
- Shared starter assets under the repo-level `examples/` tree, plus native ecommerce examples under `com.javaspider.examples.ecommerce`
- Native ecommerce crawler class wrapper plus Selenium browser capture companion under `com.javaspider.examples.ecommerce`
- Selenium-backed workflow engine with network listening, extraction, screenshots, download steps, and captcha-aware context helpers
- Workflow replay and graph reconstruction
- Research runtime with sync and async modes
- Runtime contracts for fingerprints, autoscaled frontier, artifact store, middleware, proxy policy, session pool, and observability
- Performance modules for virtual-thread execution, connection pooling, adaptive throttling, and circuit breaking
- Distributed node discovery across env, file, DNS SRV, Consul, and Etcd
- NodeReverse plus Crawlee bridge integration
- Shared access-friction reporting via `com.javaspider.antibot.AccessFrictionAnalyzer`, including `challenge_handoff` and `capability_plan` for rate limits, WAF pages, CAPTCHA/login challenges, browser upgrade, session persistence, and stop conditions
- HTTP downloader pages expose the report at `Page.getField("access_friction")`

### Conditional

- AI extraction depends on configured provider keys/endpoints
- Some advanced anti-bot and reverse flows depend on the external reverse service

### Fallback

- Media paths often rely on generic parser fallback when platform-specific extraction is weak

### Caveats

- `com.javaspider.AntiBot` is only a lightweight proxy/UA helper; the richer anti-bot surface is the `antibot/` package
- `CaptchaSolver` mixes `null` returns and exceptions across failure paths
- Some ultimate browser-simulation flows are reverse-assisted emulation rather than real browser sessions
- None of the runtimes should be documented as automatically bypassing CAPTCHA or risk-control decisions; current shared policy is detection, compliant slowdown, browser artifact capture, authorized human handoff, session persistence, and explicit stop conditions

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

For related docs, use:

- [`FRAMEWORK_CAPABILITY_MATRIX.md`](FRAMEWORK_CAPABILITY_MATRIX.md)
- [`ACCESS_FRICTION_PLAYBOOK.md`](ACCESS_FRICTION_PLAYBOOK.md)
- [`CRAWL_SCENARIO_GAP_MATRIX.md`](CRAWL_SCENARIO_GAP_MATRIX.md)
- [`LATEST_SCENARIO_CASES.md`](LATEST_SCENARIO_CASES.md)
- [`CRAWLER_TYPE_PLAYBOOK.md`](CRAWLER_TYPE_PLAYBOOK.md)
- [`SITE_PRESET_PLAYBOOK.md`](SITE_PRESET_PLAYBOOK.md)
