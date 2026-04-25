# JavaSpider

JavaSpider is the SuperSpider runtime for Java. It ships as more than a Maven crawler library: the codebase already includes browser orchestration, workflow replay, research runtime surfaces, API/Web control planes, and cross-runtime contracts that were previously only implicit in source.

## Current Verification

As of 2026-04-25, `mvn -q compile` and `mvn -q "-Dtest=com.javaspider.browser.BrowserCompatibilityTest" test` pass. `mvn -q clean compile` can still fail on Windows when `target/` is locked by another process; retry after closing Java/Maven handles.

## Core Functions

- Maven / JAR packaging
- browser workflows and enterprise Java integration
- scrapy-style compatibility and normalized JobSpec execution
- audit, connector, session, anti-bot, media, and workflow replay
- class-based ecommerce crawlers plus Selenium browser capture companions
- API, Web, research, and reverse-engineering runtime surfaces

## Public Runtime Surface

### Unified Runtime Surface

- Unified CLI commands include `config`, `crawl`, `browser`, `ai`, `doctor`, `preflight`, `export`, `curl`, `jobdir`, `http-cache`, `console`, `audit`, `node-reverse`, `web`, `run`, `research`, `workflow`, `media`, `job`, `async-job`, `sitemap-discover`, `plugins`, `selector-studio`, `scrapy`, `profile-site`, `anti-bot`, `capabilities`, `version`, and `help`.
- Browser tooling includes `fetch`, `trace`, `mock`, and `codegen`.
- `run` and `job` provide normalized runtime dispatch instead of only framework-native spider classes.
- `research` exposes sync and async analysis flows in addition to crawling.
- The control-plane surface is now explicitly public: shared config generation, cache/jobdir management, console/audit views, and profiling/debugging helpers are all release-facing features.

### Workflow and Replay

- Workflow steps support `GOTO`, `CLICK`, `TYPE`, `SELECT`, `HOVER`, `SCROLL`, `EVAL`, `LISTEN_NETWORK`, `EXTRACT`, `DOWNLOAD`, and `SCREENSHOT`.
- Selenium workflow execution includes built-in captcha element discovery, access-friction reporting, and authorized recovery hooks.
- Playwright support is exposed through `com.javaspider.browser.PlaywrightBrowserManager`, backed by the shared Node helper at `../tools/playwright_fetch.mjs`.
- Live Playwright runs require Node.js, the npm `playwright` package, and installed browser binaries (`npx playwright install`).
- Override the helper with `JAVASPIDER_PLAYWRIGHT_NODE_HELPER` or `SPIDER_PLAYWRIGHT_NODE_HELPER`; override Node with `JAVASPIDER_NODE` or `SPIDER_NODE`.
- Workflow replay can rebuild audit traces and graph artifacts from stored runs.

### Access Friction and Anti-Bot

- Access-friction reporting is exposed through `com.javaspider.antibot.AccessFrictionAnalyzer`, returning `level`, `signals`, `recommended_actions`, `challenge_handoff`, and `capability_plan`.
- The HTTP downloader attaches the same report to `Page.getField("access_friction")`.
- High-friction targets use a compliant plan: single-concurrency throttling, browser-render upgrade, artifact capture, authorized human handoff for CAPTCHA/login/risk-control, persisted session state after validation, and explicit stop conditions.
- JavaSpider does not promise automated CAPTCHA cracking or forced risk-control bypass.

### Runtime Contracts and Resilience

- Request fingerprinting, autoscaled frontier, artifact store, middleware chain, observability collector, proxy policy, and session pool are implemented as first-class runtime contracts.
- Incremental crawling, content deduplication, and checkpoint persistence are built in.
- Performance support includes virtual-thread execution, adaptive rate limiting, circuit breaking, and connection pooling.

### Control Plane and Research

- API and Web launcher surfaces are included for remote control and operator-facing workflows.
- Research runtime modules provide site profiling, async research, experiment tracking, and structured extraction.
- Shared starter assets now include crawler-type templates, site-family presets, and reusable class kits under the repo-level `examples/` tree.
- The ecommerce runtime exposes a reusable `EcommerceCrawler` wrapper and an `EcommerceSeleniumCrawler` browser companion under `com.javaspider.examples.ecommerce`.
- Graph extraction is available through `GraphBuilder`, and artifacts can be written through connectors and JSONL sinks.

### Reverse, Distributed, and Media

- Distributed node discovery supports environment, file, DNS SRV, Consul, and Etcd sources.
- Scheduler implementations include Redis and queue-backed modes.
- Reverse tooling includes NodeReverse integration and a Crawlee bridge client.
- Media support includes HLS, DASH, batch download, FFmpeg processing, DRM inspection, and platform parsers for YouTube, Bilibili, IQIYI, Tencent Video, Youku, Douyin, and generic pages.
- Source-level video download facade: `com.javaspider.media.VideoDownloader` accepts `VideoDownloadRequest` and returns `VideoDownloadResult`, choosing HLS, DASH, or direct file download from parser results or browser artifacts.

```java
VideoDownloadResult result = new VideoDownloader("downloads")
    .download(new VideoDownloadRequest("https://example.com/watch/demo")
        .setHtml(renderedHtml)
        .setPrefer("auto"));
```
- Source-level crawler selection facade: `com.javaspider.research.CrawlerSelector` turns a URL plus optional HTML into a scenario decision with `recommendedRunner`, `runnerOrder`, capabilities, fallback plan, stop conditions, confidence, and reason codes.

```java
CrawlerSelection selection = new CrawlerSelector().select(
    "https://shop.example.com/search?q=phone",
    renderedHtml
);
```

## Known Gaps

- `com.javaspider.AntiBot` is only a lightweight proxy/UA helper; the richer anti-bot implementation lives under the `antibot/` package and should not be conflated with it.
- `CaptchaSolver` mixes `null` returns and exceptions across failure paths, so callers must treat solver failures defensively.
- Some ultimate browser-simulation paths are reverse-assisted emulation rather than full browser session execution.
- Access-friction handling stops on robots disallow, explicit access denial, or missing site permission; it is not a bypass guarantee.

## Concrete Media Coverage

- HLS / DASH parsing and download
- FFmpeg-assisted media processing
- DRM inspection
- platform parsing for YouTube, Bilibili, IQIYI, Tencent Video, Youku, Douyin, and generic media pages

## Install Packages

- Windows: `..\scripts\windows\install-javaspider.bat`
- Linux: `../scripts/linux/install-javaspider.sh`
- macOS: `../scripts/macos/install-javaspider.sh`

## Install Output

- `javaspider/target`
- Maven build artifacts and JAR-oriented delivery output

## Example Cases

## Quick Start

### 1. Build and show capabilities

```bash
mvn -f javaspider/pom.xml -q -DskipTests package
java -jar javaspider/target/javaspider-*.jar capabilities
```

### 2. Run a simple crawl

```bash
java -jar javaspider/target/javaspider-*.jar crawl \
  --url https://example.com \
  --output artifacts/exports/example.json
```

### 3. Run a browser or media-oriented job from the unified CLI

```bash
java -jar javaspider/target/javaspider-*.jar browser --help
java -jar javaspider/target/javaspider-*.jar media --help
java -jar javaspider/target/javaspider-*.jar run --help
```

## API

JavaSpider includes API / Web control-plane surfaces in the main runtime. For release documentation, call out that the codebase already contains:

- API launcher surfaces
- browser and workflow jobs exposed through unified CLI/runtime entrypoints
- runtime artifacts, audit output, and replay-oriented execution

## Deploy

Recommended release flow:

```bash
mvn -f javaspider/pom.xml -q -DskipTests package
java -jar javaspider/target/javaspider-*.jar capabilities
```

For source-based examples, see:

- `src/main/java/com/javaspider/examples/DistributedExample.java`
- `src/main/java/com/javaspider/examples/ScrapyStyleDemo.java`
- `src/main/java/com/javaspider/examples/ecommerce/EcommerceCrawler.java`
- `src/main/java/com/javaspider/examples/ecommerce/EcommerceSeleniumCrawler.java`
- `src/main/java/com/javaspider/examples/ecommerce/UniversalEcommerceDetector.java`
- `src/main/java/com/javaspider/examples/ecommerce/EcommerceSiteProfiles.java`
- `YOUTUBE_SPIDER_GUIDE.md`

## Verification

Recommended pre-publish checks:

```bash
mvn -f javaspider/pom.xml -q -DskipTests package
mvn -f javaspider/pom.xml -q -Dtest=SpiderRuntimeContractsTest,HtmlParserXPathContractTest,ReadmeContractTest test
```

## Best Fit

- Java / Maven engineering environments
- browser-heavy workflow automation
- enterprise control-plane and audit-conscious execution
- teams that want Java packaging without losing modern crawler runtime features
