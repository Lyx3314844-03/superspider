# PySpider

PySpider is the SuperSpider runtime for Python-first authoring, AI-assisted project work, and flexible browser/HTTP orchestration. The repository already includes much more than a Python CLI wrapper: it has a broad command surface, scrapy-style project tooling, AI scaffolding, auth capture flows, graph and audit artifacts, artifact-driven media recovery, and shared runtime contracts.

## Core Functions

- Python-native CLI: `python -m pyspider`
- scrapy-style project runtime and authoring flow
- AI extraction, research, and project scaffolding
- browser + HTTP hybrid crawling
- anti-bot, captcha, node-reverse, media handling, and dataset output

## Hidden Capabilities

### Unified Runtime Surface

- The main CLI exposes `crawl`, `doctor`, `preflight`, `media`, `web`, `version`, `browser`, `export`, `curl`, `job`, `async-job`, `workflow`, `capabilities`, `sitemap-discover`, `plugins`, `selector-studio`, `scrapy`, `profile-site`, `ultimate`, `ai`, `anti-bot`, `node-reverse`, `config`, `jobdir`, `http-cache`, `console`, and `audit`.
- Browser tooling includes `fetch`, `trace`, `mock`, and `codegen`.
- `capabilities` returns an aggregated runtime capability payload rather than a simple version string.

### Scrapy Project and AI Authoring

- Scrapy tooling includes `demo`, `run`, `export`, `profile`, `doctor`, `bench`, `shell`, `list`, `validate`, `plan-ai`, `sync-ai`, `auth-validate`, `auth-capture`, `scaffold-ai`, `genspider`, `init`, and `contracts`.
- AI scaffolding writes schema, blueprint, prompt, auth asset, plan output, and spider template files for project-based generation.
- Auth capture and auth validation are first-class project flows rather than ad hoc examples.

### Runtime Artifacts and Control Plane

- Graph artifacts are generated and attached as standard runtime artifacts.
- Audit sinks, control-plane directories, console/audit views, jobdir management, and HTTP cache management are implemented across the CLI/runtime surface.
- Dataset writing, runtime sinks, orchestrator layers, and notebook output modules are included.

### Contracts, Cookies, and Persistence

- Runtime contracts cover artifact stores, request fingerprints, failure classification, checkpoints, incremental caching, queues, and persistent queues.
- Cookie management exists both in browser drivers and in a dedicated `CookieJar` implementation with persistence, domain matching, Netscape export, expiration cleanup, and capacity control.
- Contract config includes browser auth assets such as storage state, cookies, and auth files.

### Anti-Bot, Captcha, and Reverse

- Advanced anti-bot support includes TLS fingerprinting, browser fingerprint caching, session-scoped headers, cookie automation, proxy failure handling, and captcha detection.
- Captcha solving covers image captcha, reCAPTCHA, hCaptcha, Turnstile, 2Captcha, Anti-Captcha, and CapMonster paths.
- NodeReverse tooling includes `health`, `profile`, `detect`, `fingerprint-spoof`, `tls-fingerprint`, `canvas-fingerprint`, `analyze-crypto`, `signature-reverse`, `ast`, `webpack`, `function-call`, and `browser-simulate`.
- Ultimate runtime integrates reverse fingerprint/TLS/Canvas flows with checkpointed execution.

### Browser, Media, and Integration

- Multiple browser implementations are present: Selenium, Playwright, enhanced browser, and advanced browser layers.
- Video tooling can recover media not only from URLs but also from browser-produced HTML, network, and HAR artifacts.
- Feature gates exist for `ai`, `browser`, `distributed`, `media`, `workflow`, and `crawlee`.
- Crawlee bridge support is built in as a dedicated client integration.

## Known Gaps

- The `ai` CLI can fall back to local heuristic extraction when no supported AI API key is configured.
- `advanced.ultimate.simulate_browser()` is not a full browser session; it performs HTTP fetch plus reverse-service simulation.
- `node_reverse/fetcher.py` contains a minimal compatibility fallback that degrades to plain `requests` when the legacy fetcher stack is missing.

## Concrete Media Coverage

- HLS / DASH parsing and download
- FFmpeg-assisted media processing
- DRM inspection
- platform parsing for YouTube, Bilibili, IQIYI, Tencent Video, and Youku

## Install Packages

- Windows: `..\scripts\windows\install-pyspider.bat`
- Linux: `../scripts/linux/install-pyspider.sh`
- macOS: `../scripts/macos/install-pyspider.sh`

## Install Output

- `.venv-pyspider`
- editable Python install
- runnable `python -m pyspider version`

## Example Cases

### 1. Verify CLI and capability surface

```bash
python -m pyspider version
python -m pyspider capabilities
```

### 2. Run a simple crawl

```bash
python -m pyspider crawl --url https://example.com
```

### 3. Run a Scrapy-style project

```bash
python -m pyspider scrapy list --project .
python -m pyspider scrapy run --project .
```

### 4. Explore browser / media / reverse surfaces

```bash
python -m pyspider browser --help
python -m pyspider media --help
python -m pyspider node-reverse health
```

Source-backed examples live under:

- `examples/simple_spider.py`
- `examples/scrapy_style_demo.py`
- `examples/enhanced_features_demo.py`
- `examples/youku_video_downloader.py`

## Dependency Notes

For local development and publication, keep `requirements.txt` aligned with `setup.py`.
The current code paths expect these parser/browser foundations to be available:

- `beautifulsoup4`
- `lxml`
- `playwright`
- `selenium`

## Verification

Recommended pre-publish checks:

```bash
pytest -q tests/test_smoke.py tests/test_dependencies.py tests/test_cli.py -x
python -m pyspider capabilities
```

## Best Fit

- rapid project starts
- AI-assisted extraction and project generation
- teams that want Python-side flexibility without losing shared runtime contracts
- artifact-driven analysis, auth capture, and browser-heavy authoring workflows
