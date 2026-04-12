# SuperSpider Framework Capability Matrix

This document expands the short summary from `docs/FRAMEWORK_CAPABILITIES.md`
into a runtime-by-runtime capability matrix for the four primary frameworks:

- `pyspider`
- `gospider`
- `rustspider`
- `javaspider`

The goal here is not to claim perfect parity. It is to describe the
capabilities that are surfaced by the current repository and release layout.

## Shared SuperSpider Suite Shape

All four runtimes align on the same public suite concepts:

- shared commands:
  - `config init`
  - `crawl`
  - `ai`
  - `doctor`
  - `export`
  - `version`
  - `job`
  - `scrapy`
  - `ultimate`
  - `anti-bot`
  - `node-reverse`
  - `jobdir`
  - `http-cache`
  - `console`
- shared browser tooling:
  - `browser trace`
  - `browser mock`
  - `browser codegen`
- shared runtime vocabulary:
  - request
  - response
  - page
  - scheduler
  - frontier
  - middleware
  - checkpoint
  - proxy policy
  - artifact store
  - observability
- shared release targets:
  - Windows install surface
  - Linux install surface
  - macOS install surface
  - starter projects
  - verification workflows

## Capability Table

| Area | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Packaging model | editable Python package and module CLI | compiled Go binary | release Rust binary with features | Maven package and JAR-oriented build |
| Project runner depth | richest native project runner | built-in metadata runner plus optional artifact runner | built-in metadata runner plus optional artifact runner | built-in metadata runner plus optional artifact runner |
| Browser automation | strong mixed HTTP and browser routing | strong artifact capture and replay | feature-gated browser runtime | browser- and workflow-heavy runtime |
| AI extraction | strong orchestration and research loops | CLI + runtime AI surfaces | typed AI and extractor modules | AI extractor and assistant surfaces |
| Anti-bot | strong provider and browser support | anti-bot plus replay/runtime integrations | anti-bot with feature-gated runtime surfaces | anti-bot plus session, audit, and workflow support |
| Distributed support | Redis/distributed modules and schedulers | strong worker/queue/service model | feature-gated distributed modules | Redis/distributed scheduling path |
| Media tooling | broad parser and downloader coverage | downloader plus DRM/media contract coverage | typed media/parser/downloader coverage | parser-heavy media and workflow helpers |
| Control plane | web/api and async orchestration | strong control-plane and service posture | API/web features behind flags | controller, workflow, and operator-facing web surfaces |
| Best fit | fastest iteration and project authoring | service and batch deployment | bounded high-performance runtime | Java ecosystem and enterprise build chains |

## PySpider

PySpider is the broadest authoring surface in the suite.

- Runtime model:
  - Python package install via `pip`
  - `python -m pyspider` entrypoint
  - easiest runtime for rapid iteration and scripting
- Crawling and authoring:
  - richest scrapy-style project runner
  - project spider discovery
  - project-level settings loading
  - plugin discovery and component injection
  - browser and HTTP mixed routing on a per-request basis
- Browser and anti-bot:
  - Playwright and Selenium helpers
  - anti-bot profiles
  - captcha provider integration
  - node-reverse health and client surfaces
- AI and research:
  - AI extraction commands
  - research runtime and notebook-style experiment helpers
  - schema-driven extraction and summarization helpers
- Data and media:
  - dataset and output modules
  - HLS / DASH / DRM inspection surfaces
  - multimedia parsing for multiple platforms
- Operator surfaces:
  - `web`
  - `async-job`
  - `console`
  - `jobdir`
  - `http-cache`
  - `selector-studio`
  - `profile-site`
- Best when:
  - you need the richest project model
  - you want the fastest iteration loop
  - you need Python-native plugins or AI orchestration

## GoSpider

GoSpider is the strongest binary-first runtime in the suite.

- Runtime model:
  - lightweight compiled binary
  - easy service or batch deployment
  - straightforward control-plane embedding
- Crawling and execution:
  - strong concurrency posture
  - queue, scheduler, and job surfaces
  - shared scrapy-style API and project manifests
  - workflow and replay-friendly execution shape
- Browser and anti-bot:
  - browser artifact capture
  - HTML, screenshots, console, network, and HAR evidence
  - anti-bot modules and captcha integration
  - node-reverse modules
- Distributed and operator surfaces:
  - distributed services
  - worker runtime
  - Redis client and state machine surfaces
  - storage and result-store modules
  - control-plane and API-friendly architecture
- Data and media:
  - media downloader surfaces
  - parser and DRM-adjacent contract coverage
  - storage aggregators and export helpers
- Best when:
  - you want a compiled binary for deployment
  - you care about concurrency and operational simplicity
  - you want strong control-plane friendliness

## RustSpider

RustSpider is the strongest high-boundary, typed runtime.

- Runtime model:
  - release binary shipping
  - feature-gated modules for browser, distributed, API, and web
  - good fit for constrained production surfaces
- Crawling and execution:
  - typed scrapy-style API
  - typed contracts for runtime modules
  - preflight and runtime readiness checks
  - queue, retry, checkpoint, and artifact surfaces
- Browser and anti-bot:
  - browser runtime behind the `browser` feature
  - anti-bot and captcha support
  - node-reverse modules
  - typed workflow around browser capture and runtime evidence
- Distributed and operator surfaces:
  - distributed modules behind the `distributed` feature
  - API and web server paths behind flags
  - audit and trace-friendly runtime posture
- Data and media:
  - typed media parsing
  - downloader modules
  - benchmark and scorecard-heavy verification coverage
- Best when:
  - you want a high-performance binary
  - you need hard runtime boundaries
  - you want feature flags to control release shape

## JavaSpider

JavaSpider is the most enterprise-build-chain-friendly runtime.

- Runtime model:
  - Maven packaging
  - classpath/JAR-oriented deployment
  - natural fit for Java CI and enterprise integration
- Crawling and execution:
  - shared scrapy-style project support
  - browser/workflow-heavy runtime
  - workflow replay and operator CLI entrypoints
  - session, connector, and audit surfaces
- Browser and anti-bot:
  - Selenium support
  - Playwright helper paths
  - anti-bot, captcha, and session flows
  - workflow and browser automation CLIs
- Data and media:
  - generic parser path
  - media metadata parsing
  - extraction and AI assistant modules
- Operator surfaces:
  - `workflow`
  - `media`
  - `selector-studio`
  - `profile-site`
  - audit trail and connector modules
  - web controller surface
- Best when:
  - you already live in the Java ecosystem
  - you want Maven-native packaging
  - you need workflow, browser, and enterprise integration features together

## Install and Release Surfaces

All four runtimes now expose:

- suite-level installers:
  - `scripts/windows/install.bat`
  - `scripts/linux/install.sh`
  - `scripts/macos/install.sh`
- per-framework installers:
  - `scripts/windows/install-pyspider.bat`
  - `scripts/windows/install-gospider.bat`
  - `scripts/windows/install-rustspider.bat`
  - `scripts/windows/install-javaspider.bat`
  - `scripts/linux/install-pyspider.sh`
  - `scripts/linux/install-gospider.sh`
  - `scripts/linux/install-rustspider.sh`
  - `scripts/linux/install-javaspider.sh`
  - `scripts/macos/install-pyspider.sh`
  - `scripts/macos/install-gospider.sh`
  - `scripts/macos/install-rustspider.sh`
  - `scripts/macos/install-javaspider.sh`

For exact prerequisites, outputs, and entry commands, see
`docs/SUPERSPIDER_INSTALLS.md`.
