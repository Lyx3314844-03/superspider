# SuperSpider Framework Capability Matrix

Updated: 2026-04-19

## Core Capability Overview

| Dimension | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Primary language | Python | Go | Rust | Java |
| Delivery form | virtualenv / editable package | compiled binary | release binary | Maven package / JAR |
| Primary strength | AI orchestration, project workflows, rapid iteration | concurrency, binary deployment, distributed workers | strong typing, performance, feature-gated release control | browser workflow, enterprise integration, audit trails |
| Browser support | ✅ strong (Playwright native) | ✅ strong (Playwright + Selenium) | ✅ strong (node+playwright process + Selenium facade) | ✅ strong (Selenium + Playwright helper) |
| Hybrid HTTP + browser crawling | ✅ | ✅ | ✅ | ✅ |
| Distributed runtime | ✅ strong | ✅ strong | ✅ strong | ✅ medium-high |
| Media tooling | ✅ strong | ✅ strong | ✅ strong | ✅ strong |
| AI extraction | ✅ strongest (LLM + smart parser) | ✅ medium | ✅ medium | ✅ medium |
| Anti-bot / captcha | ✅ strong | ✅ strong | ✅ strong (2captcha / anticaptcha) | ✅ strong |
| Node-reverse / JS encryption | ✅ | ✅ | ✅ | ✅ |
| Scrapy-style interface | ✅ | ✅ | ✅ | ✅ |
| Audit trail | ✅ baseline + JSONL | ✅ explicit audit module | ✅ explicit audit module | ✅ strongest / dedicated |
| Independent REST API server | ✅ | ✅ | ✅ | ✅ |
| Install output | `.venv-pyspider` | `gospider` binary | `rustspider` release binary | Maven `target` / JAR |
| Best fit | experimentation, AI pipelines, orchestration | services, binaries, worker-based execution | performance-sensitive, boundary-conscious deployments | Java enterprise workflows, browser automation |

---

## Media Platform Coverage

All four runtimes share the same media capability surface.

| Platform / Format | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| HLS (`m3u8`) | ✅ | ✅ | ✅ | ✅ |
| DASH (`mpd`) | ✅ | ✅ | ✅ | ✅ |
| FFmpeg merge / convert | ✅ | ✅ | ✅ | ✅ |
| DRM detection | ✅ | ✅ | ✅ | ✅ |
| YouTube | ✅ | ✅ | ✅ | ✅ |
| Bilibili | ✅ | ✅ | ✅ | ✅ |
| IQIYI | ✅ | ✅ | ✅ | ✅ (generic fallback) |
| Tencent Video | ✅ | ✅ | ✅ | ✅ (generic fallback) |
| Youku | ✅ | ✅ | ✅ | ✅ (generic fallback) |
| Douyin | ✅ | ✅ | ✅ | ✅ (generic fallback) |

---

## AI Extraction Capabilities

| Feature | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Entity extraction | ✅ | ✅ | ✅ | ✅ |
| Content summarization | ✅ | ✅ | ✅ | ✅ |
| Sentiment analysis | ✅ | ✅ | ✅ | ✅ |
| LLM extraction (OpenAI) | ✅ | ✅ | ✅ | ✅ |
| LLM extraction (Anthropic/Claude) | ✅ | ✅ | ✅ | ✅ |
| Few-shot examples | ✅ | ✅ | ✅ | ✅ |
| Smart parser (auto-detect page type) | ✅ | — | — | — |
| Schema-driven structured output | ✅ | — | — | — |
| XPath suggestion studio | ✅ | ✅ | ✅ | ✅ |

---

## Anti-Bot and Captcha

| Feature | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| TLS fingerprint rotation | ✅ | ✅ | ✅ | ✅ |
| Browser behavior simulation | ✅ | ✅ | ✅ | ✅ |
| WAF bypass | ✅ | ✅ | ✅ | ✅ |
| Night mode (reduced activity) | ✅ | ✅ | ✅ | ✅ |
| 2captcha integration | ✅ | ✅ | ✅ | ✅ |
| Anti-Captcha integration | ✅ | ✅ | ✅ | ✅ |
| reCAPTCHA solving | ✅ | ✅ | ✅ | ✅ |
| hCaptcha solving | ✅ | ✅ | ✅ | ✅ |
| Image captcha solving | ✅ | ✅ | ✅ | ✅ |
| SSRF protection | ✅ | ✅ | ✅ | ✅ |

---

## Distributed and Queue Backends

| Backend | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Redis (native) | ✅ | ✅ | ✅ | ✅ |
| RabbitMQ | ✅ | ✅ broker-native | ✅ bridge | ✅ broker-native |
| Kafka | ✅ | ✅ broker-native | ✅ bridge | ✅ broker-native |
| In-process queue | ✅ | ✅ | ✅ | ✅ |

---

## Node Discovery

| Method | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Environment variables | ✅ | ✅ | ✅ | ✅ |
| File-based | ✅ | ✅ | ✅ | ✅ |
| DNS-SRV | ✅ | ✅ | ✅ | ✅ |
| Consul | ✅ | ✅ | ✅ | ✅ |
| etcd | ✅ | ✅ | ✅ | ✅ |

---

## Database / Storage Backends

| Backend | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| SQLite | ✅ | ✅ | ✅ | ✅ |
| PostgreSQL | ✅ | ✅ process adapter | ✅ driver + process adapter | ✅ |
| MySQL | ✅ | ✅ process adapter | ✅ driver + process adapter | ✅ |
| MongoDB | ✅ | ✅ process adapter | ✅ driver + process adapter | ✅ |
| Dataset mirror to DB | ✅ | ✅ | ✅ | ✅ |

---

## Browser Automation

| Feature | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Playwright (native) | ✅ | ✅ | ✅ node+playwright process | ✅ Java helper |
| Selenium / WebDriver | ✅ | ✅ native client | ✅ fantoccini facade | ✅ native |
| Browser pool | ✅ | ✅ | ✅ | ✅ |
| Session / cookie management | ✅ | ✅ | ✅ | ✅ |
| Browser artifact capture | ✅ | ✅ | ✅ | ✅ |

---

## Node-Reverse / JS Encryption

| Feature | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Node-reverse client | ✅ | ✅ | ✅ | ✅ |
| Encrypted site crawler | ✅ | ✅ | ✅ | ✅ |
| JS signature execution | ✅ | ✅ | ✅ | ✅ |

---

## Observability and Audit

| Feature | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Audit trail (in-memory) | ✅ | ✅ | ✅ | ✅ |
| Audit trail (file / JSONL) | ✅ | ✅ | ✅ | ✅ |
| Composite audit trail | ✅ | ✅ | ✅ | ✅ |
| Monitoring / metrics | ✅ | ✅ | ✅ | ✅ |
| Preflight validation | ✅ | ✅ | ✅ | ✅ |
| Checkpoint / resume | ✅ | ✅ | ✅ | ✅ |
| Incremental crawl | ✅ | ✅ | ✅ | ✅ |

---

## Additional Capabilities

| Feature | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Graph crawler | ✅ | ✅ | ✅ | — |
| Research / async runtime | ✅ | ✅ | ✅ | ✅ |
| Notebook output | ✅ | ✅ | ✅ | — |
| curl-to-code converter | ✅ | ✅ | ✅ | ✅ |
| Robots.txt compliance | ✅ | ✅ | ✅ | ✅ |
| Rate limiting / circuit breaker | ✅ | ✅ | ✅ | ✅ |
| Proxy pool | ✅ | ✅ | ✅ | ✅ |
| Workflow engine | ✅ | ✅ | ✅ | ✅ |
| Event bus | ✅ | ✅ | ✅ | ✅ |
| Feature gates | ✅ | ✅ | ✅ | ✅ |
| Web UI / console | ✅ | ✅ | ✅ | ✅ |
| REST API server | ✅ | ✅ | ✅ | ✅ |
| Docker support | ✅ | ✅ | ✅ | ✅ |

---

## Quick Selection Guide

| Use case | Recommended runtime |
| --- | --- |
| Rapid prototyping and AI-assisted extraction | **PySpider** |
| High-concurrency binary deployment | **GoSpider** |
| Performance-sensitive production with strict boundaries | **RustSpider** |
| Enterprise Java / Maven / browser-heavy automation | **JavaSpider** |
| Distributed worker cluster | **GoSpider** or **RustSpider** |
| LLM-powered structured extraction | **PySpider** |
| Encrypted site / JS reverse engineering | any (all four support node-reverse) |
| Media download (YouTube, Bilibili, etc.) | any (all four have full media coverage) |
