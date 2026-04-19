# SuperSpider Capability Matrix

| Dimension | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Primary language | Python | Go | Rust | Java |
| Delivery form | virtualenv / editable package | compiled binary | release binary | Maven package / JAR |
| Primary strength | AI orchestration and project workflows | concurrency and binary deployment | strong typing and performance | browser workflow and enterprise integration |
| Browser support | strong | strong | strong | strong |
| Hybrid HTTP + browser crawling | strong | strong | strong | strong |
| Distributed runtime | strong | strong | strong | medium-high |
| Media tooling | strong | strong | strong | strong |
| AI extraction | strong | medium | medium | medium |
| Install output | `.venv-pyspider` | `gospider` | `rustspider` release binary | Maven `target` |
| Best fit | experimentation, orchestration, AI pipelines | services, binaries, worker-based execution | performance-sensitive and boundary-conscious deployments | Java enterprise workflows |

## Concrete Media Capability Matrix

| Capability | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| HLS (`m3u8`) | ✅ | ✅ | ✅ | ✅ |
| DASH (`mpd`) | ✅ | ✅ | ✅ | ✅ |
| FFmpeg | ✅ | ✅ | ✅ | ✅ |
| DRM detection | ✅ | ✅ | ✅ | ✅ |
| YouTube | ✅ | ✅ | ✅ | ✅ |
| Bilibili | ✅ | ✅ | ✅ | ✅ |
| IQIYI / Tencent / Youku | ✅ | ✅ | ✅ | ✅ |
| Douyin | ✅ | ✅ | ✅ | ✅ |

## Architecture Deltas

| Capability | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Specialized sentiment module | ✅ | ✅ | ✅ | ✅ |
| Specialized summarizer | ✅ | ✅ | ✅ | ✅ |
| Specialized entity extraction | ✅ | ✅ | ✅ | ✅ |
| Queue backends | native Redis / RabbitMQ / Kafka | native Redis, broker-native + process + bridge RabbitMQ/Kafka | native Redis, driver/process + bridge RabbitMQ/Kafka | native Redis, broker-native + process + bridge RabbitMQ/Kafka |
| Database backends | broad | SQLite + driver/process Postgres/MySQL/Mongo adapters | SQLite + driver/process Postgres/MySQL/Mongo adapters | broad |
| Playwright surface | native | integrated browser/media paths | native node/playwright process + webdriver | native Java helper + Selenium |
| Node discovery | Consul / etcd | env / file / dns-srv / Consul / etcd | env / file / dns-srv / Consul / etcd | env / file / dns-srv / Consul / etcd |
| Independent API server | ✅ | ✅ | ✅ | ✅ |
| Audit trail module | baseline + JSONL | explicit audit module | explicit audit module | strongest / dedicated |

Notes:

- all four runtimes now expose concrete media parsing / download coverage for the shared platform set instead of leaving Chinese video platforms on generic best-effort handling alone
- JavaSpider uses generic-parser fallback when specialized parsing is unavailable, so supported URLs still resolve through the shared media surface
- RustSpider now recognizes mirrored or replay-style IQIYI / Tencent URL shapes in addition to canonical production domains
- RustSpider Playwright support is now a native `node + playwright` process surface; the old helper remains as fallback
- Go / Rust database breadth is now materially improved, but still adapter-driven rather than fully driver-native across every codepath

## Quick Selection

- choose `PySpider` for rapid iteration, plugins, and AI-assisted extraction
- choose `GoSpider` for simple binary deployment and concurrent worker execution
- choose `RustSpider` for performance, strong typing, and feature-gated release boundaries
- choose `JavaSpider` for Maven/JAR workflows, browser automation, and enterprise integration
