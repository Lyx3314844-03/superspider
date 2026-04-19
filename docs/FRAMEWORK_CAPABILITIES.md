# Framework Capabilities

This document is meant to help GitHub visitors understand what each of the four released runtimes can do, how far each one goes, what it installs, and where it fits best.

## Capability Axes

Each runtime is described along four dimensions:

- core functions
- capability range
- install package and install output
- best-fit usage profile

## Shared Media Coverage

All four runtimes now expose the same concrete media surface for the core downloader stack:

- HLS (`m3u8`) parsing and download
- DASH (`mpd`) parsing and download
- FFmpeg-based conversion / merge support
- DRM detection for manifests and media
- platform parsing for YouTube, Bilibili, IQIYI, Tencent Video, and Youku

The runtime-specific sections below describe engineering posture, but the media platform matrix is now intentionally aligned across Python, Go, Rust, and Java.

## PySpider

### Core Functions

- Python-native CLI
- scrapy-style project execution
- AI extraction and research workflows
- browser + HTTP hybrid crawling
- anti-bot, captcha, node-reverse, media, and dataset output

### Concrete Media Support

- HLS / DASH download entrypoints
- FFmpeg utilities
- DRM inspection
- YouTube / Bilibili / IQIYI / Tencent / Youku parsing

### Capability Range

- from rapid crawler experiments to full project scaffolding
- from structured extraction to AI-assisted extraction
- from browser-driven workflows to result output pipelines

### Install Package / Output

- install scripts:
  - `scripts/windows/install-pyspider.bat`
  - `scripts/linux/install-pyspider.sh`
  - `scripts/macos/install-pyspider.sh`
- output:
  - `.venv-pyspider`
  - runnable `python -m pyspider`

### Best Fit

- AI-driven crawling
- project-oriented development
- teams that want Python flexibility and rapid iteration

## GoSpider

### Core Functions

- compiled Go CLI
- concurrent crawling and scheduling
- distributed workers, queues, and storage
- browser artifact capture and replay
- media download and operational runtime dispatch

### Concrete Media Support

- HLS / DASH download entrypoints
- FFmpeg utilities
- DRM inspection
- YouTube / Bilibili / IQIYI / Tencent / Youku parsing

### Capability Range

- from single-node concurrent crawling to multi-worker execution
- from binary deployment to service-oriented crawler operation
- from browser-based crawling to result storage and replay

### Install Package / Output

- install scripts:
  - `scripts/windows/install-gospider.bat`
  - `scripts/linux/install-gospider.sh`
  - `scripts/macos/install-gospider.sh`
- output:
  - `gospider` executable

### Best Fit

- concurrency-heavy crawling
- binary deployment
- worker / queue / storage-driven execution

## RustSpider

### Core Functions

- Rust release binary
- feature-gated browser, distributed, API, and web modules
- typed scrapy-style interface
- preflight, monitoring, anti-bot, media, and contract-heavy runtime

### Concrete Media Support

- HLS / DASH download entrypoints
- FFmpeg utilities
- DRM inspection
- YouTube / Bilibili / IQIYI / Tencent / Youku parsing

### Capability Range

- from compact release binaries to high-performance production deployment
- from strict feature-gated shipping to strongly typed runtime boundaries
- from preflight validation to monitored runtime execution

### Install Package / Output

- install scripts:
  - `scripts/windows/install-rustspider.bat`
  - `scripts/linux/install-rustspider.sh`
  - `scripts/macos/install-rustspider.sh`
- output:
  - `rustspider/target/release/rustspider`

### Best Fit

- strongly typed deployments
- performance-sensitive runtimes
- teams that want feature-controlled release binaries

## JavaSpider

### Core Functions

- Maven / JAR packaging
- browser workflows with Selenium / Playwright helper paths
- scrapy-style compatibility
- audit, connector, session, anti-bot, workflow replay, and media parsing

### Concrete Media Support

- HLS / DASH download entrypoints
- FFmpeg utilities
- DRM inspection
- YouTube / Bilibili / IQIYI / Tencent / Youku parsing

### Capability Range

- from Maven packaging to enterprise Java release pipelines
- from browser automation to workflow-driven execution
- from audit trails to internal system integration

### Install Package / Output

- install scripts:
  - `scripts/windows/install-javaspider.bat`
  - `scripts/linux/install-javaspider.sh`
  - `scripts/macos/install-javaspider.sh`
- output:
  - `javaspider/target`
  - Maven build artifacts

### Best Fit

- enterprise Java environments
- browser-heavy automation
- Maven / JAR delivery chains

## Related Docs

- `docs/DOCS_INDEX.md`
- `MEDIA_PARITY_REPORT.md`
- `LATEST_FRAMEWORK_COMPLETION_REPORT.md`
- `docs/archive/HISTORICAL_REPORTS.md`
