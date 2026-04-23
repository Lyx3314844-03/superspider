# RustSpider

RustSpider is the SuperSpider runtime for strongly typed, feature-gated, production-oriented crawler delivery. The codebase already goes beyond a release binary: it includes browser tooling, Web/API surfaces, scrapy-style project authoring, research runtime modules, anti-bot recovery flows, checkpointed ultimate execution, and distributed queue semantics.

## Core Functions

- Rust release binary
- feature-gated browser, distributed, API, Web, video, and AI modules
- typed scrapy-style interface and normalized JobSpec execution
- preflight, monitoring, anti-bot, media, audit, and workflow surfaces
- explicit release-boundary and packaging control

## Public Runtime Surface

### Feature-Gated Delivery

- Cargo feature gates are explicitly implemented for `browser`, `video`, `distributed`, `api`, `web`, `ai`, and `full`.
- The runtime can be shipped as a lean browser-enabled binary or as a full control-plane build.

### Unified Runtime Surface

- CLI commands include `config`, `crawl`, `browser`, `ai`, `doctor`, `preflight`, `export`, `curl`, `run`, `job`, `async-job`, `workflow`, `jobdir`, `http-cache`, `console`, `audit`, `web`, `media`, `ultimate`, `sitemap-discover`, `plugins`, `selector-studio`, `scrapy`, `profile-site`, `research`, `node-reverse`, `anti-bot`, and `capabilities`.
- Browser tooling includes `fetch`, `trace`, `mock`, and `codegen`.
- Console and audit tooling both support snapshot and tail workflows over shared control-plane artifacts.
- Site profiling, sitemap discovery, selector debugging, plugin execution, and shared control-plane tooling are all documented public entrypoints, not hidden maintenance paths.

### Web, API, and Research

- Embedded API and Web layers expose task status, monitors, metrics, graph extraction, research `run`, `async`, `soak`, and research history.
- Web routes can be token-protected.
- Research runtime and async research surfaces return structured extraction and dataset-aware payloads.

### Anti-Bot and Recovery

- Anti-bot support includes Cloudflare/Akamai bypass utilities, browser fingerprint generation, stealth headers, night mode, and captcha detection.
- Advanced captcha solving supports image captcha, reCAPTCHA, hCaptcha, and Turnstile through 2Captcha and Anti-Captcha, including fallback service switching.
- Ultimate runtime code can extract `sitekey`, `action`, `cData`, `pageData`, inline captcha images, and relative captcha image URLs before attempting recovery.

### Ultimate, Contracts, and Queues

- The ultimate runtime includes checkpoint persistence, browser simulation, anti-bot profiling, NodeReverse fingerprint/TLS/Canvas calls, and result artifact emission.
- Runtime building blocks include artifact store, audit trail, event bus, cookie jar, checkpoint manager, request fingerprinting, and async request queues.
- Distributed Redis queues implement lease semantics, expired-lease reaping, and dead-letter style failure handling.
- Queue backend support includes queue bridge detection and native client helpers.

### Project and Cross-Runtime Integration

- Scrapy-style project runtime supports declarative pipelines, spider middlewares, downloader middlewares, browser runners, and NodeReverse-assisted fingerprint injection.
- Shared starter assets now include crawler-type templates, site-family presets, and class kits under the repo-level `examples/` tree.
- Python FFI integration exists as an explicit cross-language bridge point.
- Preflight is available both through the main CLI and a dedicated binary surface.

### Media and DRM

- Media support includes HLS, DASH, downloader helpers, FFmpeg tooling, and multi-platform video parsing.
- DRM inspection is built in for Widevine, FairPlay, and PlayReady flows.

## Known Gaps

- The `ai` CLI can run in `heuristic-fallback` mode when no compatible API key is configured or when the LLM response is unusable.
- Some browser-simulation flows in encrypted and ultimate paths are reverse-assisted simulations rather than real browser sessions.
- Checkpoint initialization still uses a panic path for some filesystem failures, which is harsher than ideal for long-running services.

## Concrete Media Coverage

- HLS / DASH parsing and download
- FFmpeg-assisted media processing
- DRM inspection
- platform parsing for YouTube, Bilibili, IQIYI, Tencent Video, and Youku

## Install Packages

- Windows: `..\scripts\windows\install-rustspider.bat`
- Linux: `../scripts/linux/install-rustspider.sh`
- macOS: `../scripts/macos/install-rustspider.sh`

## Install Output

- `rustspider/target/release/rustspider`
- production-oriented release executable

## Example Cases

## Quick Start

### 1. Build and inspect capabilities

```bash
cargo build --release
./target/release/rustspider capabilities
```

### 2. Run a simple crawl

```bash
./target/release/rustspider crawl --url https://example.com
```

### 3. Explore browser / research / media surfaces

```bash
./target/release/rustspider browser --help
./target/release/rustspider research --help
./target/release/rustspider media --help
```

## API

RustSpider includes embedded API / Web surfaces behind feature gates. For release documentation, call out that the runtime already contains:

- API and Web control-plane entrypoints
- browser / media / research / anti-bot surfaces in the unified CLI
- typed runtime contracts, artifacts, queue/state surfaces, and preflight checks

## Deploy

Recommended release flow:

```bash
cargo build --release
./target/release/rustspider capabilities
```

Source-backed examples live under:

- `examples/main.rs`
- `examples/scrapy_style.rs`
- `examples/playwright_example.rs`
- `examples/youku_video_downloader.rs`

## Verification

Recommended pre-publish checks:

```bash
cargo test --quiet
cargo build --release
```

## Best Fit

- performance-sensitive deployments
- strongly typed runtime boundaries
- teams that want feature-gated release control plus embedded control-plane surfaces
- advanced anti-bot and artifact-centric execution pipelines
