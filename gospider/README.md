# GoSpider

GoSpider is the SuperSpider runtime for compiled, operations-friendly crawler delivery. The source tree already implements far more than concurrent crawling: it includes browser artifact capture, runtime contracts, storage backends, research surfaces, scrapy-style project tooling, API/Web control planes, and reverse-engineering integrations.

## Core Functions

- compiled Go CLI
- concurrent crawling and scheduling
- distributed workers, queues, storage, and task execution
- browser artifact capture and replay-oriented runtime dispatch
- anti-bot, media, research, API, and workflow surfaces

## Hidden Capabilities

### Unified Runtime Surface

- CLI commands include `config`, `crawl`, `browser`, `export`, `curl`, `run`, `job`, `async-job`, `jobdir`, `http-cache`, `console`, `audit`, `capabilities`, `web`, `workflow`, `media`, `ultimate`, `ai`, `selector-studio`, `scrapy`, `sitemap-discover`, `plugins`, `profile-site`, `research`, `node-reverse`, `anti-bot`, `doctor`, and `preflight`.
- Feature gates are implemented for `ai`, `browser`, `distributed`, `media`, `workflow`, and `crawlee`, with `lite`, `ai`, `distributed`, and `full` profiles.

### Browser and Artifact Pipeline

- Browser runtime can persist HTML, DOM, screenshot, console, network JSON, and HAR artifacts.
- Browser support includes stealth mode, extra headers, resource blocking, network capture, HAR export, browser pooling, and Selenium compatibility.
- JobSpec workflow actions include `goto`, `wait`, `click`, `type`, `scroll`, `select`, `hover`, `eval`, `screenshot`, and `listen_network`.

### Runtime Contracts and Storage

- The runtime contract layer includes artifact storage, trace/observability collection, checkpoint-aware frontier behavior, leases, and adaptive concurrency recommendation.
- Storage is not limited to a single dataset type: file, process, and SQL-backed dataset/result stores are included, along with event stores and writer aggregation.
- Result envelopes support named artifact references and media artifact records.

### API, Research, and Graph

- The API server exposes task results, task artifacts, graph extraction, and research `run`, `async`, and `soak` endpoints.
- Web console and Web server modules provide an operator-facing surface beyond the CLI.
- Research runtime, async research, and notebook-style output are implemented.
- Graph extraction can be persisted as a runtime artifact from HTML payloads.

### Project, Reverse, and Distributed

- Scrapy-style runtime supports plugins, item pipelines, spider middleware, downloader middleware, browser fetchers, and project-level declarative configuration.
- Browser contract config already includes `storage_state_file`, `cookies_file`, and `auth_file`.
- NodeReverse integration covers profile/detect flows plus fingerprint spoofing, TLS fingerprinting, Canvas fingerprinting, and middleware-assisted injection.
- Distributed modules include Redis clients, queue backends, service/state-machine layers, node discovery, workers, and soak scenarios.

### Anti-Bot and Media

- Anti-bot support includes Cloudflare/Akamai detection and bypass headers, captcha provider integration, browser fingerprint generation, TLS fingerprint shaping, night mode, and cookie/session handling.
- Media support includes HLS, DASH, multiple-platform parsing, FFmpeg wrapping, batch download, artifact-driven dispatch, and platform extractors for YouTube, Bilibili, IQIYI, Tencent Video, Youku, and Douyin.
- SSRF guarding is implemented in the downloader layer.

## Known Gaps

- The `ai` CLI can fall back to heuristic extraction when no AI API key is configured; not every AI path is guaranteed to be LLM-backed.
- `ultimate.simulateBrowser()` is reverse-assisted emulation, not a full browser session bootstrap.
- The repository still contains `monitor.go.corrupted` and `monitor.go.original`, which should be treated as stale files rather than active implementations.

## Concrete Media Coverage

- HLS / DASH parsing and download
- FFmpeg-assisted media processing
- DRM inspection
- platform parsing for YouTube, Bilibili, IQIYI, Tencent Video, Youku, and Douyin

## Install Packages

- Windows: `..\scripts\windows\install-gospider.bat`
- Linux: `../scripts/linux/install-gospider.sh`
- macOS: `../scripts/macos/install-gospider.sh`

## Install Output

- `gospider` executable
- directly deployable binary artifact

## Example Cases

### 1. Build and inspect capabilities

```bash
go build -o gospider.exe .
./gospider.exe capabilities
```

### 2. Run a simple crawl

```bash
./gospider.exe crawl --url https://example.com
```

### 3. Run an artifact-rich browser / media / research surface

```bash
./gospider.exe browser --help
./gospider.exe media --help
./gospider.exe research --help
```

Source-backed examples live under:

- `examples/basic/main.go`
- `examples/showcase/main.go`
- `examples/scrapy_style/main.go`
- `examples/video_downloader/main.go`

## Verification

Recommended pre-publish checks:

```bash
go test ./...
go build ./...
```

## Best Fit

- binary-first deployment
- high-concurrency runtime workloads
- teams that want artifact-rich browser capture and strong operational surfaces
- distributed worker / queue / storage-based crawler execution
