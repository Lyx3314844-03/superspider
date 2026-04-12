# Framework Capabilities

This document is the human-readable capabilities overview for the four primary runtimes in the Spider Framework Suite:

- `pyspider`
- `gospider`
- `rustspider`
- `javaspider`

For the deeper under-documented entrypoints, modules, operator products, and
live external-service surfaces, also see:

- `docs/FRAMEWORK_DEEP_SURFACES.md`
- `docs/FRAMEWORK_CAPABILITY_MATRIX.md`
- `docs/SUPERSPIDER_INSTALLS.md`

## Shared Suite Capabilities

All four runtimes align on the same suite-level shape:

- unified CLI surface:
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
- browser tooling:
  - `browser trace`
  - `browser mock`
  - `browser codegen`
- shared kernel vocabulary:
  - `request`
  - `fingerprint`
  - `frontier`
  - `scheduler`
  - `middleware`
  - `artifact_store`
  - `session_pool`
  - `proxy_policy`
  - `observability`
  - `cache`
- shared operator products:
  - `jobdir`
  - `http_cache`
  - `browser_tooling`
  - `autoscaling_pools`
  - `debug_console`
- shared control-plane and artifact surfaces:
  - CLI
  - web control plane
  - control-plane JSONL
  - release artifacts
- shared cross-platform install surface:
  - Windows
  - Linux
  - macOS

## PySpider

PySpider is the most flexible project-oriented runtime in the suite.

- native Python CLI via `python -m pyspider`
- richest scrapy-style project runner
- project-level plugin SDK and component injection
- browser and HTTP mixed routing
- AI/extract orchestration
- distributed execution and dataset/output surfaces
- node-reverse integration
- anti-bot and recovery envelopes
- browser, media, and research-oriented workflows
- official `web` surface for UI/API serving
- official `curl convert` surface
- official DRM inspection surface for manifest/file analysis
- platform-aware media parsing for Youku / IQIYI / Tencent / Bilibili / Douyin

## GoSpider

GoSpider is the binary-first, concurrency-heavy runtime.

- lightweight compiled deployment model
- strong concurrent execution and control-plane friendliness
- browser artifact capture:
  - HTML
  - screenshot
  - console
  - network
  - HAR
- distributed worker and queue/storage surfaces
- media download and parser surfaces
- proxy/session-aware HTTP runtime
- anti-bot, replay, and workflow/browser surfaces
- good fit for service and batch runtime packaging
- official `curl convert` surface
- official DRM inspection surface for HLS / DASH / local media evidence

## RustSpider

RustSpider is the strongly typed high-performance runtime.

- release binary deployment
- feature-gated browser, distributed, API, and web surfaces
- typed scrapy-style API
- browser/runtime modules under feature flags
- distributed and worker-oriented surfaces
- preflight and monitor-oriented runtime checks
- media parsing and downloader surfaces
- anti-bot and node-reverse surfaces
- good fit for controlled runtime boundaries and binary shipping
- official `audit` surface on top of control-plane traces
- official `curl convert` surface
- platform-aware media parsing for Youku / IQIYI / Tencent / Bilibili / Douyin

## JavaSpider

JavaSpider is the browser/workflow and enterprise integration runtime.

- Maven-based build and packaging
- browser and workflow-oriented execution
- Selenium and Playwright helper paths
- audit, connector, and session surfaces
- anti-bot and recovery envelopes
- scrapy-style project runner support
- workflow replay and browser automation CLI
- good fit for Java ecosystem integration and enterprise build chains
- official `curl convert` surface
- media metadata parsing extended beyond YouTube / Youku through the generic parser path

## Cross-Platform Install Surface

The suite exposes operating-system-level installers and verifiers:

- Windows:
  - `scripts/windows/install.bat`
  - `scripts/windows/verify.bat`
- Linux:
  - `scripts/linux/install.sh`
  - `scripts/linux/verify.sh`
- macOS:
  - `scripts/macos/install.sh`
  - `scripts/macos/verify.sh`

## Verification

Relevant repository-level proof surfaces:

- `python verify_runtime_readiness.py --json`
- `python verify_runtime_stability.py --json`
- `python verify_runtime_core_capabilities.py --json`
- `python verify_operator_products.py --json`
- `python verify_operating_system_support.py --json`
