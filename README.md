# SuperSpider

<p align="center">
  <img src="docs/assets/superspider-wordmark.svg" alt="SuperSpider multicolor wordmark" width="860" />
</p>

<p align="center">
  <img src="docs/assets/superspider-icon.svg" alt="SuperSpider icon" width="180" />
</p>

SuperSpider is a four-runtime crawler framework release repository. It is not a single crawler wrapped in four languages. Instead, it publishes four distinct crawler runtimes designed for different engineering environments and delivery models:

- `pyspider`
- `gospider`
- `rustspider`
- `javaspider`

All four frameworks cover the same broad problem space, including web crawling, browser automation, anti-bot handling, extraction, and output pipelines, but each one emphasizes a different deployment and engineering posture:

- `PySpider`: project authoring, AI orchestration, plugin injection, rapid iteration
- `GoSpider`: binary delivery, concurrency, distributed workers, service-side deployment
- `RustSpider`: strong typing, performance, feature-gated modules, stable release binaries
- `JavaSpider`: Maven/JAR packaging, browser workflows, audit trails, enterprise Java integration

## Platform Overview

SuperSpider is designed to present four crawler runtimes as one coherent product surface:

- one public brand: `SuperSpider`
- one naming system: `pyspider / gospider / rustspider / javaspider`
- one installation shape: every framework has Windows, Linux, and macOS installers
- one selection model: choose the runtime by engineering fit, then choose the operating system installer

## Four Frameworks At A Glance

| Framework | Core delivery | Strongest advantage | Best fit |
| --- | --- | --- | --- |
| `PySpider` | Python package / virtual environment | AI extraction, plugins, project workflows | rapid development, experimentation, orchestration-heavy crawling |
| `GoSpider` | compiled Go binary | concurrency, workers, service deployment | batch jobs, distributed execution, operational crawling |
| `RustSpider` | release Rust binary | strong typing, performance, feature gates | performance-sensitive deployments, strict runtime boundaries |
| `JavaSpider` | Maven package / JAR | browser workflows, auditability, enterprise integration | Java build pipelines, browser-heavy automation, enterprise environments |

## Concrete Function Coverage

Each runtime covers a full crawler lifecycle, but with a different emphasis:

- crawl entry:
  - CLI execution
  - project-style runtime
  - task or workflow invocation
- page acquisition:
  - HTTP fetching
  - browser-based crawling
  - dynamic-site handling
- parsing and extraction:
  - HTML and selector-based extraction
  - AI-assisted extraction
  - media and video-related parsing
- shared media surface across all four runtimes:
  - HLS / DASH parsing and download flow
  - FFmpeg-assisted conversion / merge utilities
  - DRM detection
  - platform parsing for YouTube, Bilibili, IQIYI, Tencent Video, and Youku
- runtime support:
  - anti-bot and captcha handling
  - session, proxy, and connection management
  - distributed queues, workers, and storage
- delivery form:
  - Python package
  - Go binary
  - Rust release binary
  - Java Maven/JAR package

## Per-Framework Detail

### PySpider

PySpider is the most complete project-oriented Python crawler in the set.

Core functions:

- Python-native CLI and modular runtime
- scrapy-style project execution
- AI extraction, research flows, and plugin injection
- hybrid browser + HTTP crawling
- anti-bot, captcha, node-reverse, media, and dataset output

Capability range:

- from single-page crawling to full project scaffolding
- from structured extraction to AI-assisted extraction
- from interactive experiments to production crawler execution

Install packages and outputs:

- Windows: `scripts/windows/install-pyspider.bat`
- Linux: `scripts/linux/install-pyspider.sh`
- macOS: `scripts/macos/install-pyspider.sh`
- output: `.venv-pyspider`

### GoSpider

GoSpider is the strongest fit for concurrent, binary-first, service-oriented crawling.

Core functions:

- compiled Go CLI
- concurrent crawling and scheduling
- distributed workers, queues, storage, and task execution
- browser artifact capture and replay
- anti-bot, media download, and runtime dispatch

Capability range:

- from single-node binaries to distributed crawler nodes
- from concurrent task execution to service-friendly deployment
- from browser-driven crawling to result storage and replay

Install packages and outputs:

- Windows: `scripts/windows/install-gospider.bat`
- Linux: `scripts/linux/install-gospider.sh`
- macOS: `scripts/macos/install-gospider.sh`
- output: `gospider` executable

### RustSpider

RustSpider is the strongest runtime for high performance and strict runtime boundaries.

Core functions:

- Rust release binary
- feature-gated browser, distributed, API, and web modules
- typed scrapy-style interface
- preflight, monitoring, anti-bot, media, and contract-heavy runtime

Capability range:

- from compact release binaries to high-performance production deployment
- from feature-controlled module shipping to strong typed runtime boundaries
- from preflight validation to release execution

Install packages and outputs:

- Windows: `scripts/windows/install-rustspider.bat`
- Linux: `scripts/linux/install-rustspider.sh`
- macOS: `scripts/macos/install-rustspider.sh`
- output: `rustspider/target/release/rustspider`

### JavaSpider

JavaSpider is the strongest fit for browser workflows and enterprise Java integration.

Core functions:

- Maven / JAR packaging
- browser workflows with Selenium / Playwright helper paths
- scrapy-style compatibility
- audit, connector, session, anti-bot, workflow replay, and media parsing

Capability range:

- from Maven packaging to enterprise Java release pipelines
- from browser automation to workflow-driven execution
- from audit trails to internal system integration

Install packages and outputs:

- Windows: `scripts/windows/install-javaspider.bat`
- Linux: `scripts/linux/install-javaspider.sh`
- macOS: `scripts/macos/install-javaspider.sh`
- output: `javaspider/target`

## Three Operating-System Install Versions

| Framework | Windows | Linux | macOS |
| --- | --- | --- | --- |
| PySpider | `scripts/windows/install-pyspider.bat` | `scripts/linux/install-pyspider.sh` | `scripts/macos/install-pyspider.sh` |
| GoSpider | `scripts/windows/install-gospider.bat` | `scripts/linux/install-gospider.sh` | `scripts/macos/install-gospider.sh` |
| RustSpider | `scripts/windows/install-rustspider.bat` | `scripts/linux/install-rustspider.sh` | `scripts/macos/install-rustspider.sh` |
| JavaSpider | `scripts/windows/install-javaspider.bat` | `scripts/linux/install-javaspider.sh` | `scripts/macos/install-javaspider.sh` |

## Release Docs

- Docs index: [docs/DOCS_INDEX.md](docs/DOCS_INDEX.md)
- Media parity report: [MEDIA_PARITY_REPORT.md](MEDIA_PARITY_REPORT.md)
- Latest completion report: [LATEST_FRAMEWORK_COMPLETION_REPORT.md](LATEST_FRAMEWORK_COMPLETION_REPORT.md)
- Historical report archive: [docs/archive/HISTORICAL_REPORTS.md](docs/archive/HISTORICAL_REPORTS.md)
