# JavaSpider

JavaSpider is the SuperSpider runtime for Java. It ships as more than a Maven crawler library: the codebase already includes browser orchestration, workflow replay, research runtime surfaces, API/Web control planes, and cross-runtime contracts that were previously only implicit in source.

## Core Functions

- Maven / JAR packaging
- browser workflows and enterprise Java integration
- scrapy-style compatibility and normalized JobSpec execution
- audit, connector, session, anti-bot, media, and workflow replay
- API, Web, research, and reverse-engineering runtime surfaces

## Hidden Capabilities

### Unified Runtime Surface

- Unified CLI commands include `config`, `crawl`, `browser`, `ai`, `doctor`, `preflight`, `export`, `curl`, `jobdir`, `http-cache`, `console`, `audit`, `node-reverse`, `api`, `web`, `run`, `research`, `workflow`, `media`, `job`, `async-job`, and `capabilities`.
- `run` and `job` provide normalized runtime dispatch instead of only framework-native spider classes.
- `research` exposes sync and async analysis flows in addition to crawling.

### Workflow and Replay

- Workflow steps support `GOTO`, `CLICK`, `TYPE`, `SELECT`, `HOVER`, `SCROLL`, `EVAL`, `LISTEN_NETWORK`, `EXTRACT`, `DOWNLOAD`, and `SCREENSHOT`.
- Selenium workflow execution includes built-in captcha element discovery and recovery hooks.
- Workflow replay can rebuild audit traces and graph artifacts from stored runs.

### Runtime Contracts and Resilience

- Request fingerprinting, autoscaled frontier, artifact store, middleware chain, observability collector, proxy policy, and session pool are implemented as first-class runtime contracts.
- Incremental crawling, content deduplication, and checkpoint persistence are built in.
- Performance support includes virtual-thread execution, adaptive rate limiting, circuit breaking, and connection pooling.

### Control Plane and Research

- API and Web launcher surfaces are included for remote control and operator-facing workflows.
- Research runtime modules provide site profiling, async research, experiment tracking, and structured extraction.
- Graph extraction is available through `GraphBuilder`, and artifacts can be written through connectors and JSONL sinks.

### Reverse, Distributed, and Media

- Distributed node discovery supports environment, file, DNS SRV, Consul, and Etcd sources.
- Scheduler implementations include Redis and queue-backed modes.
- Reverse tooling includes NodeReverse integration and a Crawlee bridge client.
- Media support includes HLS, DASH, batch download, FFmpeg processing, DRM inspection, and platform parsers for YouTube, Bilibili, IQIYI, Tencent Video, Youku, Douyin, and generic pages.

## Known Gaps

- `com.javaspider.AntiBot` is only a lightweight proxy/UA helper; the richer anti-bot implementation lives under the `antibot/` package and should not be conflated with it.
- `CaptchaSolver` mixes `null` returns and exceptions across failure paths, so callers must treat solver failures defensively.
- Some ultimate browser-simulation paths are reverse-assisted emulation rather than full browser session execution.

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
