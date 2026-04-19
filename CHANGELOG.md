# Changelog

All notable changes to SuperSpider are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0] - 2026-04-13

### Added

**Shared across all four runtimes**

- Unified media platform coverage: HLS (`m3u8`), DASH (`mpd`), FFmpeg utilities, DRM detection
- Platform-specific parsers for YouTube, Bilibili, IQIYI, Tencent Video, Youku, and Douyin
- Windows / Linux / macOS install scripts for every runtime
- Shared capability matrix documentation

**PySpider**

- Python-native CLI (`python -m pyspider`)
- Scrapy-style project runtime
- AI extraction pipeline: entity extractor, summarizer, sentiment analyzer, LLM extractor
- Browser + HTTP hybrid crawling via Playwright
- Anti-bot and captcha solver modules
- Node-reverse client for JavaScript-encrypted sites
- Distributed Redis queue and worker runtime
- Async runtime and notebook output
- Graph crawler with relation extraction and node traversal
- Dataset writer with JSON / CSV / Markdown output
- Full media stack: HLS, DASH, FFmpeg, DRM, multimedia downloader
- Web UI and REST API server
- Checkpoint and incremental crawl support

**GoSpider**

- Compiled Go CLI binary
- Concurrent crawling engine with rate limiting and deduplication
- Distributed worker, queue, and storage runtime (Redis, RabbitMQ, Kafka)
- Browser pool with Playwright and Selenium support
- Anti-bot module with WAF bypass and night mode
- Captcha solver
- AI extractor: entity extraction, summarizer, sentiment analyzer
- Scrapy-style project interface
- Node-reverse client for JavaScript-encrypted sites
- Session pool management
- Graph crawler
- REST API server and web console
- Checkpoint and incremental crawl support
- SSRF protection

**RustSpider**

- Release Rust binary with feature-gated modules
- Typed scrapy-style interface
- Feature-gated browser, distributed, API, and web modules
- Preflight validation and contract-heavy runtime
- Anti-bot module with WAF bypass
- Captcha solver
- AI modules: entity extraction, summarizer, sentiment analyzer
- Node-reverse client for JavaScript-encrypted sites
- Distributed queue backends (Redis, RabbitMQ, Kafka)
- Storage backends (SQLite, Postgres, MySQL, MongoDB adapters)
- Node discovery (env, file, DNS-SRV, Consul, etcd)
- Checkpoint and incremental crawl support
- SSRF protection
- Audit trail module
- Benchmark suite

**JavaSpider**

- Maven / JAR packaging
- Browser workflows with Selenium and Playwright helper paths
- Scrapy-style compatibility layer
- Audit trail module (strongest in the set)
- Connector, session, and anti-bot modules
- Workflow replay
- Media parsing: HLS, DASH, FFmpeg, DRM, platform parsers
- Distributed queue and worker runtime
- REST API server
- Checkpoint and incremental crawl support

### Changed

- Unified the media platform surface across all four runtimes so every runtime covers the same platform set
- Aligned node discovery backends across Go, Rust, and Java runtimes
- Improved database backend breadth for Go and Rust runtimes

### Fixed

- RustSpider now recognizes mirrored and replay-style IQIYI / Tencent URL shapes
- RustSpider Playwright support replaced with native `node + playwright` process surface

---

## Notes

- `webmagic` is included as a reference submodule only and is not part of the SuperSpider release surface
- Chinese-language internal reports have been replaced with English-only public documentation
