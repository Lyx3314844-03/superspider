# GitHub Release Template

> Replace the version and short summary, then keep the section structure.

## SuperSpider vX.Y.Z

> One-line release summary.

### What This Release Includes

- `pyspider`
- `gospider`
- `rustspider`
- `javaspider`

### Overall Framework

SuperSpider is a four-runtime crawler release surface. Each runtime serves the same broad crawling domain, but each one is optimized for a different engineering environment and delivery model.

### Shared Media Coverage

- HLS / DASH parsing and download
- FFmpeg-assisted media processing
- DRM inspection
- YouTube / Bilibili / IQIYI / Tencent Video / Youku parsing

### Frameworks

#### PySpider

**Core functions**

- Python-native CLI
- scrapy-style project runtime
- AI extraction and research workflows
- browser + HTTP hybrid crawling
- anti-bot, captcha, node-reverse, media, and dataset output

**Concrete media coverage**

- HLS / DASH parsing and download
- FFmpeg-assisted media processing
- DRM inspection
- YouTube / Bilibili / IQIYI / Tencent Video / Youku parsing

**Capability range**

- rapid iteration
- AI-heavy pipelines
- Python data ecosystem integration

**Install packages**

- Windows: `scripts/windows/install-pyspider.bat`
- Linux: `scripts/linux/install-pyspider.sh`
- macOS: `scripts/macos/install-pyspider.sh`

#### GoSpider

**Core functions**

- compiled Go CLI
- concurrent crawling and scheduling
- worker / queue / storage runtime
- browser artifact capture and replay
- anti-bot and media execution paths

**Concrete media coverage**

- HLS / DASH parsing and download
- FFmpeg-assisted media processing
- DRM inspection
- YouTube / Bilibili / IQIYI / Tencent Video / Youku parsing

**Capability range**

- binary-first deployment
- service-side crawling
- concurrency-heavy workloads

**Install packages**

- Windows: `scripts/windows/install-gospider.bat`
- Linux: `scripts/linux/install-gospider.sh`
- macOS: `scripts/macos/install-gospider.sh`

#### RustSpider

**Core functions**

- release Rust binary
- feature-gated browser / distributed / API / web modules
- typed scrapy-style interface
- preflight, monitoring, anti-bot, and media runtime

**Concrete media coverage**

- HLS / DASH parsing and download
- FFmpeg-assisted media processing
- DRM inspection
- YouTube / Bilibili / IQIYI / Tencent Video / Youku parsing

**Capability range**

- high-performance runtime
- strict release boundaries
- feature-controlled deployments

**Install packages**

- Windows: `scripts/windows/install-rustspider.bat`
- Linux: `scripts/linux/install-rustspider.sh`
- macOS: `scripts/macos/install-rustspider.sh`

#### JavaSpider

**Core functions**

- Maven / JAR packaging
- browser workflow and Selenium / Playwright helpers
- scrapy-style compatibility
- audit, connector, session, anti-bot, workflow replay, and media parsing

**Concrete media coverage**

- HLS / DASH parsing and download
- FFmpeg-assisted media processing
- DRM inspection
- YouTube / Bilibili / IQIYI / Tencent Video / Youku parsing

**Capability range**

- Java enterprise integration
- browser-heavy workflow execution
- Maven-based delivery

**Install packages**

- Windows: `scripts/windows/install-javaspider.bat`
- Linux: `scripts/linux/install-javaspider.sh`
- macOS: `scripts/macos/install-javaspider.sh`

### Install Surface

| Framework | Windows | Linux | macOS |
| --- | --- | --- | --- |
| PySpider | `scripts/windows/install-pyspider.bat` | `scripts/linux/install-pyspider.sh` | `scripts/macos/install-pyspider.sh` |
| GoSpider | `scripts/windows/install-gospider.bat` | `scripts/linux/install-gospider.sh` | `scripts/macos/install-gospider.sh` |
| RustSpider | `scripts/windows/install-rustspider.bat` | `scripts/linux/install-rustspider.sh` | `scripts/macos/install-rustspider.sh` |
| JavaSpider | `scripts/windows/install-javaspider.bat` | `scripts/linux/install-javaspider.sh` | `scripts/macos/install-javaspider.sh` |

### Recommended Reading

- `docs/DOCS_INDEX.md`
- `MEDIA_PARITY_REPORT.md`
- `LATEST_FRAMEWORK_COMPLETION_REPORT.md`
- `docs/release-canvas.html`
