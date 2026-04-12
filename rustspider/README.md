# RustSpider

Rust runtime for the Spider Framework Suite.

RustSpider 偏向强类型、高性能和可部署性，适合需要更严格运行时边界、feature flag 控制和单二进制交付的抓取场景。

## Highlights

- unified CLI: `crawl`, `doctor`, `scrapy`, `ultimate`, `anti-bot`, `node-reverse`
- typed scrapy-style API under `rustspider::scrapy`
- feature-gated browser, distributed, API, and web surfaces
- built-in metadata runner plus optional project runner artifact for `scrapy run --project`

## Quick Start

```bash
cargo build --release
target/release/rustspider capabilities
target/release/rustspider doctor --json
target/release/rustspider scrapy init --path demo-project
target/release/rustspider scrapy run --project demo-project
target/release/rustspider ultimate --url https://example.com
```

## Feature Flags

- `browser`
- `distributed`
- `api`
- `web`
- `full`

## API Surfaces

- CLI + contracts: `src/main.rs`
- Scrapy-style API: `src/scrapy/`
- Browser/runtime: `src/browser/`
- Distributed: `src/distributed/`
- Anti-bot + reverse runtime: `src/antibot/`, `src/node_reverse/`
- Monitor + preflight: `src/preflight.rs`, `src/web/`

## Extended Surfaces

Hidden-but-supported entrypoints and modules are documented in:

- `../docs/FRAMEWORK_DEEP_SURFACES.md`

Notable extra RustSpider surfaces beyond the short highlights:

- `ai`, `curl`, `job`, `jobdir`, `http-cache`, `console`, `audit`
- `selector-studio`, `profile-site`, `plugins`, `sitemap-discover`
- `reactor.NativeReactor`, `artifact.MemoryArtifactStore`, `retry`, `proxy`, `site_profiler`

## Project Runner

`scrapy run --project` no longer shells out to `cargo run`.

It now:

1. executes the project runner artifact declared in `scrapy-project.json` when present
2. otherwise falls back to the built-in metadata runner

## Deploy

- release binary: `cargo build --release`
- helper script: `build.sh`
- container assets: `docker/Dockerfile`
- starter project: `../examples/starters/rustspider-starter`

## Verification

- focused contract tests: `cargo test --test scrapy_contract`
- additional suite verification lives in the repo root under `tests/`

## Live Captcha Smoke

RustSpider ships opt-in live captcha smoke coverage for provider-backed challenge solving.

- enable live smoke: `RUSTSPIDER_LIVE_CAPTCHA_SMOKE=1`
- 2Captcha provider key: `TWO_CAPTCHA_API_KEY` or `CAPTCHA_API_KEY`
- Anti-Captcha provider key: `ANTI_CAPTCHA_API_KEY`
- reCAPTCHA target: `RUSTSPIDER_LIVE_RECAPTCHA_SITE_KEY` and `RUSTSPIDER_LIVE_RECAPTCHA_PAGE_URL`
- hCaptcha target: `RUSTSPIDER_LIVE_HCAPTCHA_SITE_KEY` and `RUSTSPIDER_LIVE_HCAPTCHA_PAGE_URL`
- Turnstile target: `RUSTSPIDER_LIVE_TURNSTILE_SITE_KEY` and `RUSTSPIDER_LIVE_TURNSTILE_PAGE_URL`
- optional Turnstile extras:
  - `RUSTSPIDER_LIVE_TURNSTILE_ACTION`
  - `RUSTSPIDER_LIVE_TURNSTILE_CDATA`
  - `RUSTSPIDER_LIVE_TURNSTILE_PAGEDATA`

Run the verifier with:

```bash
python verify_rust_captcha_live.py --json
```

GitHub Actions manual workflow:

- workflow: `.github/workflows/rustspider-live-captcha-smoke.yml`
