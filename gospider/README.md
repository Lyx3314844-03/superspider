# GoSpider

Go runtime for the Spider Framework Suite.

GoSpider 偏向并发执行、控制面、分布式 worker 和轻量部署，适合把爬虫任务做成二进制服务或批处理 runtime。

## Highlights

- unified CLI: `crawl`, `doctor`, `scrapy`, `ultimate`, `anti-bot`, `node-reverse`
- browser artifact capture: HTML, screenshot, console, network, HAR
- distributed, queue, storage, and control-plane modules
- built-in metadata runner plus optional project runner artifact for `scrapy run --project`

## Quick Start

```bash
go build ./cmd/gospider
gospider capabilities
gospider doctor --json
gospider scrapy init --path demo-project
gospider scrapy run --project demo-project
gospider ultimate --url https://example.com
```

## API Surfaces

- CLI: `cmd/gospider`
- Scrapy-style API: `scrapy/`
- Browser runtime: `runtime/browser`
- Dispatch/runtime routing: `runtime/dispatch`
- Distributed + storage: `distributed/`, `storage/`
- Anti-bot + reverse runtime: `antibot/`, `node_reverse/`

## Extended Surfaces

Hidden-but-supported entrypoints and modules are documented in:

- `../docs/FRAMEWORK_DEEP_SURFACES.md`

Notable extra GoSpider surfaces beyond the short highlights:

- `ai`, `curl`, `job`, `jobdir`, `http-cache`, `console`
- `selector-studio`, `profile-site`, `plugins`, `sitemap-discover`
- `api`, `captcha`, `events`, `graph`, `runtime.dispatch`, `site_profiler`, `ultimate`

## Project Runner

`scrapy run --project` no longer compiles project source code at runtime.

It now works in two modes:

1. execute the project runner artifact declared by `scrapy-project.json`
2. fall back to the built-in metadata runner when no artifact exists

This makes public release behavior safer and more predictable.

## Deploy

- local binary: `go build ./cmd/gospider`
- container assets: `docker/`
- starter projects: `../examples/starters/gospider-starter`

## Verification

- focused Go tests: `go test ./scrapy ./scrapy/project ./cmd/gospider`
- broader verification gates live in the repo root under `tests/` and `.github/workflows/`

## Live Captcha Smoke

GoSpider ships opt-in live captcha smoke coverage for provider-backed challenge solving.

- enable live smoke: `GOSPIDER_LIVE_CAPTCHA_SMOKE=1`
- 2Captcha provider key: `TWO_CAPTCHA_API_KEY` or `CAPTCHA_API_KEY`
- Anti-Captcha provider key: `ANTI_CAPTCHA_API_KEY`
- reCAPTCHA target: `GOSPIDER_LIVE_RECAPTCHA_SITE_KEY` and `GOSPIDER_LIVE_RECAPTCHA_PAGE_URL`
- hCaptcha target: `GOSPIDER_LIVE_HCAPTCHA_SITE_KEY` and `GOSPIDER_LIVE_HCAPTCHA_PAGE_URL`

Run the verifier with:

```bash
python verify_gospider_captcha_live.py --json
```

GitHub Actions manual workflow:

- workflow: `.github/workflows/gospider-live-captcha-smoke.yml`
