# SuperSpider v1.0.0

> Four crawler runtimes. Three operating-system install versions. One clean release surface.

## What This Release Is

SuperSpider `v1.0.0` is a four-runtime crawler release:

- `pyspider`
- `gospider`
- `rustspider`
- `javaspider`

This release is intentionally narrow. The repository only keeps:

- the four crawler frameworks
- Windows / Linux / macOS install scripts
- capability documents
- release-facing branding and presentation assets

## Release Highlights

- A single public brand: `SuperSpider`
- Four runtimes with different engineering strengths
- Three operating-system install versions for every runtime
- Clear capability positioning per framework
- Shared media coverage across all four runtimes:
  - HLS / DASH
  - FFmpeg utilities
  - DRM detection
  - YouTube / Bilibili / IQIYI / Tencent Video / Youku parsing
- A cleaner GitHub release surface with fewer unrelated assets

## Runtime Breakdown

### PySpider

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

- strongest project authoring experience
- best fit for rapid iteration and AI-heavy pipelines
- ideal for teams staying inside the Python data ecosystem

**Install packages**

- Windows: `scripts/windows/install-pyspider.bat`
- Linux: `scripts/linux/install-pyspider.sh`
- macOS: `scripts/macos/install-pyspider.sh`

**Install output**

- `.venv-pyspider`

### GoSpider

**Core functions**

- compiled Go CLI
- concurrent crawling and scheduling
- worker / queue / storage runtime
- browser artifact capture and replay
- anti-bot, media download, and task dispatch

**Concrete media coverage**

- HLS / DASH parsing and download
- FFmpeg-assisted media processing
- DRM inspection
- YouTube / Bilibili / IQIYI / Tencent Video / Youku parsing

**Capability range**

- strongest binary-first deployment path
- best fit for service-side execution and operations-oriented crawling
- ideal for concurrency-heavy workloads

**Install packages**

- Windows: `scripts/windows/install-gospider.bat`
- Linux: `scripts/linux/install-gospider.sh`
- macOS: `scripts/macos/install-gospider.sh`

**Install output**

- `gospider` executable

### RustSpider

**Core functions**

- release Rust binary
- feature-gated browser / distributed / API / web modules
- typed scrapy-style interface
- preflight, monitoring, anti-bot, media, and contract-heavy runtime

**Concrete media coverage**

- HLS / DASH parsing and download
- FFmpeg-assisted media processing
- DRM inspection
- YouTube / Bilibili / IQIYI / Tencent Video / Youku parsing

**Capability range**

- strongest high-performance typed runtime
- best fit for strict deployment boundaries
- ideal when teams want stable release binaries with feature control

**Install packages**

- Windows: `scripts/windows/install-rustspider.bat`
- Linux: `scripts/linux/install-rustspider.sh`
- macOS: `scripts/macos/install-rustspider.sh`

**Install output**

- `rustspider/target/release/rustspider`

### JavaSpider

**Core functions**

- Maven / JAR packaging
- browser workflow and Selenium / Playwright helper paths
- scrapy-style compatibility
- audit, connector, session, anti-bot, workflow replay, and media parsing

**Concrete media coverage**

- HLS / DASH parsing and download
- FFmpeg-assisted media processing
- DRM inspection
- YouTube / Bilibili / IQIYI / Tencent Video / Youku parsing

**Capability range**

- strongest fit for Java build chains and enterprise delivery
- best fit for browser-heavy workflow automation
- ideal for Maven-centered engineering environments

**Install packages**

- Windows: `scripts/windows/install-javaspider.bat`
- Linux: `scripts/linux/install-javaspider.sh`
- macOS: `scripts/macos/install-javaspider.sh`

**Install output**

- `javaspider/target`

## Install Surface

| Framework | Windows | Linux | macOS |
| --- | --- | --- | --- |
| PySpider | `scripts/windows/install-pyspider.bat` | `scripts/linux/install-pyspider.sh` | `scripts/macos/install-pyspider.sh` |
| GoSpider | `scripts/windows/install-gospider.bat` | `scripts/linux/install-gospider.sh` | `scripts/macos/install-gospider.sh` |
| RustSpider | `scripts/windows/install-rustspider.bat` | `scripts/linux/install-rustspider.sh` | `scripts/macos/install-rustspider.sh` |
| JavaSpider | `scripts/windows/install-javaspider.bat` | `scripts/linux/install-javaspider.sh` | `scripts/macos/install-javaspider.sh` |

## Recommended Reading

- `docs/DOCS_INDEX.md`
- `MEDIA_PARITY_REPORT.md`
- `LATEST_FRAMEWORK_COMPLETION_REPORT.md`
- `docs/release-canvas.html`
