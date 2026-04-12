# PySpider

Python runtime for the Spider Framework Suite.

PySpider 是这组运行时里 project runner 最完整的一支，适合研究型抓取、AI/extract orchestration、browser/http 混合路由和快速试验。

## Highlights

- unified CLI: `python -m pyspider ...`
- richest scrapy-style project runner in the suite
- project-level plugin SDK with discovery and component injection
- browser, anti-bot, distributed, dataset, and node-reverse surfaces

## Quick Start

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
python -m pyspider capabilities
python -m pyspider doctor --json
python -m pyspider scrapy init --path demo-project
python -m pyspider scrapy run --project demo-project
python -m pyspider ultimate https://example.com
python -m pyspider node-reverse health
```

## API Surfaces

- CLI: `pyspider.cli.main`
- Scrapy-style API: `pyspider.spider.spider`
- Browser and anti-bot: `browser/`, `antibot/`
- Distributed and datasets: `distributed/`, `dataset/`, `output/`
- Research and extraction orchestration: `research/`, `extract/`

## Extended Surfaces

Hidden-but-supported entrypoints and modules are documented in:

- `../docs/FRAMEWORK_DEEP_SURFACES.md`

Notable extra PySpider surfaces beyond the short highlights:

- `ai`, `curl`, `web`, `run`, `async-job`
- `job`, `jobdir`, `http-cache`, `console`
- `selector-studio`, `profile-site`, `runtime.orchestrator`, `runtime.async_runtime`
- `profiler.site_profiler`, `extract.studio`, `dataset.writer`, `media.drm_detector`

## Project Runner

PySpider keeps the richest native project model in the suite:

- spider class discovery
- shared project settings
- project-level plugin loading
- browser/http mixed routing

## Deploy

- package metadata: `setup.py`, `pyproject.toml`
- editable install: `pip install -e .`
- starter project: `../examples/starters/pyspider-starter`

## Verification

- focused tests: `python -m pytest pyspider/tests/test_cli.py tests/test_scrapy_style_starters.py --no-cov`
- broader verification lives in the repo root under `tests/`

## Live Captcha Smoke

PySpider ships opt-in live captcha smoke coverage for provider-backed challenge solving.

- enable live smoke: `PYSPIDER_LIVE_CAPTCHA_SMOKE=1`
- 2Captcha provider key: `TWO_CAPTCHA_API_KEY` or `CAPTCHA_API_KEY`
- Anti-Captcha provider key: `ANTI_CAPTCHA_API_KEY`
- reCAPTCHA target: `PYSPIDER_LIVE_RECAPTCHA_SITE_KEY` and `PYSPIDER_LIVE_RECAPTCHA_PAGE_URL`
- hCaptcha target: `PYSPIDER_LIVE_HCAPTCHA_SITE_KEY` and `PYSPIDER_LIVE_HCAPTCHA_PAGE_URL`

Run the verifier with:

```bash
python verify_pyspider_captcha_live.py --json
```

GitHub Actions manual workflow:

- workflow: `.github/workflows/pyspider-live-captcha-smoke.yml`
