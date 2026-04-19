# Ultimate Enhancement Guide

This guide documents the full capability surface of SuperSpider across all four runtimes, covering every major enhancement area.

## Enhancement Areas

1. [Media Platform Coverage](#media-platform-coverage)
2. [Anti-Bot and WAF Bypass](#anti-bot-and-waf-bypass)
3. [Distributed Crawling](#distributed-crawling)
4. [AI Extraction](#ai-extraction)
5. [Browser Automation](#browser-automation)
6. [Storage and Export](#storage-and-export)
7. [Monitoring and Observability](#monitoring-and-observability)
8. [Security](#security)
9. [Performance](#performance)

---

## Media Platform Coverage

All four runtimes cover the same media platform surface.

| Platform | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| YouTube | ✅ | ✅ | ✅ | ✅ |
| Bilibili | ✅ | ✅ | ✅ | ✅ |
| IQIYI | ✅ | ✅ | ✅ | ✅ |
| Tencent Video | ✅ | ✅ | ✅ | ✅ |
| Youku | ✅ | ✅ | ✅ | ✅ |
| Douyin | ✅ | ✅ | ✅ | ✅ |
| HLS (m3u8) | ✅ | ✅ | ✅ | ✅ |
| DASH (mpd) | ✅ | ✅ | ✅ | ✅ |
| FFmpeg | ✅ | ✅ | ✅ | ✅ |
| DRM detection | ✅ | ✅ | ✅ | ✅ |

### PySpider Media Usage

```python
from pyspider.media.multimedia_downloader import MultimediaDownloader
from pyspider.media.hls_downloader import HLSDownloader
from pyspider.media.ffmpeg_tools import FFmpegTools

# Download from any supported platform
downloader = MultimediaDownloader()
result = downloader.download("https://www.youtube.com/watch?v=...")

# HLS stream download
hls = HLSDownloader()
hls.download("https://example.com/stream.m3u8", output="video.mp4")

# FFmpeg merge
ffmpeg = FFmpegTools()
ffmpeg.merge_segments(["seg1.ts", "seg2.ts"], output="merged.mp4")
```

### GoSpider Media Usage

```go
import "github.com/superspider/gospider/media"

downloader := media.NewMultiPlatformDownloader()
result, err := downloader.Download("https://www.youtube.com/watch?v=...")

hls := media.NewHLSDownloader()
err = hls.Download("https://example.com/stream.m3u8", "video.mp4")
```

---

## Anti-Bot and WAF Bypass

### Capability Matrix

| Feature | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| TLS fingerprint rotation | ✅ | ✅ | ✅ | ✅ |
| Browser behavior simulation | ✅ | ✅ | ✅ | ✅ |
| WAF bypass | ✅ | ✅ | ✅ | ✅ |
| Captcha solver | ✅ | ✅ | ✅ | ✅ |
| Night mode (reduced activity) | ✅ | ✅ | ✅ | ✅ |
| Cookie jar management | ✅ | ✅ | ✅ | ✅ |
| Header randomization | ✅ | ✅ | ✅ | ✅ |

### Night Mode

Night mode reduces crawl activity during off-hours to avoid detection patterns:

```python
# PySpider
from pyspider.antibot import AntiBotEnhancer

enhancer = AntiBotEnhancer()
enhancer.enable_night_mode(
    quiet_hours_start=22,  # 10 PM
    quiet_hours_end=6,     # 6 AM
    reduced_rate=0.1       # 10% of normal rate during quiet hours
)
```

```go
// GoSpider
enhancer := antibot.NewEnhancer()
enhancer.EnableNightMode(antibot.NightModeConfig{
    QuietHoursStart: 22,
    QuietHoursEnd:   6,
    ReducedRate:     0.1,
})
```

### Captcha Solving

```python
# PySpider
from pyspider.captcha.solver import CaptchaSolver

solver = CaptchaSolver(
    provider="2captcha",  # or "anticaptcha", "local"
    api_key="your_api_key"
)
solution = solver.solve(captcha_image_url)
```

---

## Distributed Crawling

### Queue Backend Comparison

| Backend | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Redis | ✅ native | ✅ native | ✅ native | ✅ native |
| RabbitMQ | ✅ | ✅ broker-native | ✅ bridge | ✅ broker-native |
| Kafka | ✅ | ✅ broker-native | ✅ bridge | ✅ broker-native |
| In-process | ✅ | ✅ | ✅ | ✅ |

### Node Discovery

| Method | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Environment variables | ✅ | ✅ | ✅ | ✅ |
| File-based | ✅ | ✅ | ✅ | ✅ |
| DNS-SRV | ✅ | ✅ | ✅ | ✅ |
| Consul | ✅ | ✅ | ✅ | ✅ |
| etcd | ✅ | ✅ | ✅ | ✅ |

### Multi-Worker Setup

```python
# PySpider: start multiple workers
from pyspider.distributed import RedisDistributed

dist = RedisDistributed(redis_url="redis://localhost:6379")

# Worker 1
dist.start_worker(worker_id="worker-1", concurrency=10)

# Worker 2 (on another machine)
dist.start_worker(worker_id="worker-2", concurrency=10)
```

---

## AI Extraction

### Capability Comparison

| Feature | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Entity extraction | ✅ | ✅ | ✅ | ✅ |
| Summarization | ✅ | ✅ | ✅ | ✅ |
| Sentiment analysis | ✅ | ✅ | ✅ | ✅ |
| LLM extraction | ✅ | — | — | — |
| Smart parser | ✅ | — | — | — |
| Research runtime | ✅ | ✅ | ✅ | — |

### PySpider LLM Extraction

```python
from pyspider.ai_extractor.llm_extractor import LLMExtractor

extractor = LLMExtractor(
    model="gpt-4o",
    api_key="your_openai_key"
)

result = extractor.extract(
    html_content,
    prompt="Extract: product name, price, availability, and description"
)
```

### Smart Parser

```python
from pyspider.ai_extractor.smart_parser import SmartParser

parser = SmartParser()
# Automatically detects page type and extracts relevant fields
result = parser.parse(html_content)
```

---

## Browser Automation

### Playwright Support

All four runtimes support Playwright-based browser automation.

```python
# PySpider
from pyspider.browser.playwright_browser import PlaywrightBrowser

browser = PlaywrightBrowser()
page = await browser.new_page()
await page.goto("https://example.com")
content = await page.content()
```

```go
// GoSpider
browser := browser.NewBrowserPool(browser.Config{
    MaxInstances: 5,
    Headless:     true,
})
page, err := browser.NewPage()
page.Goto("https://example.com")
```

### Session Management

```python
# PySpider: persistent session with cookie management
from pyspider.core.cookie import CookieManager

cookies = CookieManager(storage="./cookies.json")
cookies.load()

browser = PlaywrightBrowser(cookies=cookies)
```

---

## Storage and Export

### Output Formats

All four runtimes support multiple output formats:

| Format | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| JSON | ✅ | ✅ | ✅ | ✅ |
| CSV | ✅ | ✅ | ✅ | ✅ |
| JSONL | ✅ | ✅ | ✅ | ✅ |
| SQLite | ✅ | ✅ | ✅ | ✅ |
| PostgreSQL | ✅ | ✅ adapter | ✅ adapter | ✅ |
| MySQL | ✅ | ✅ adapter | ✅ adapter | ✅ |
| MongoDB | ✅ | ✅ adapter | ✅ adapter | ✅ |

### PySpider Dataset Writer

```python
from pyspider.store.dataset import DatasetWriter

writer = DatasetWriter(output_dir="./output")
writer.write({"title": "Example", "url": "https://example.com"})
writer.flush()  # writes to JSON, CSV, and JSONL
```

### GoSpider Storage

```go
import "github.com/superspider/gospider/storage"

store := storage.NewSQLDatasetStore("./output.db")
store.Write(map[string]interface{}{
    "title": "Example",
    "url":   "https://example.com",
})
```

---

## Monitoring and Observability

### Audit Trail

JavaSpider has the strongest audit trail support. All runtimes include baseline audit logging.

```python
# PySpider
from pyspider.runtime.audit import AuditLogger

audit = AuditLogger(output="./audit.jsonl")
audit.log_request(url, method, headers)
audit.log_response(url, status, size)
```

```java
// JavaSpider (strongest audit support)
AuditTrail audit = new AuditTrail()
    .output("./audit.jsonl")
    .includeHeaders(true)
    .includeBody(false);

spider.setAuditTrail(audit);
```

### Metrics and Monitoring

```python
# PySpider
from pyspider.monitor.monitor import SpiderMonitor

monitor = SpiderMonitor()
monitor.start()

# Access metrics
stats = monitor.get_stats()
print(f"Requests: {stats.total_requests}")
print(f"Success rate: {stats.success_rate:.1%}")
print(f"Avg response time: {stats.avg_response_ms}ms")
```

---

## Security

### SSRF Protection

All four runtimes include SSRF (Server-Side Request Forgery) protection to prevent crawlers from being used to access internal network resources.

```python
# PySpider
from pyspider.core.ssrf_protection import SSRFProtection

protection = SSRFProtection(
    block_private_ranges=True,   # blocks 10.x, 172.16.x, 192.168.x
    block_loopback=True,         # blocks 127.x
    block_link_local=True,       # blocks 169.254.x
    allowed_domains=["example.com"]
)
```

### Robots.txt Compliance

```python
# PySpider
from pyspider.core.robots import RobotsChecker

checker = RobotsChecker(user_agent="SuperSpider/1.0")
if checker.can_fetch("https://example.com/page"):
    spider.crawl("https://example.com/page")
```

---

## Performance

### Concurrency Settings

| Runtime | Default concurrency | Max recommended |
| --- | --- | --- |
| PySpider | 10 | 100 |
| GoSpider | 50 | 1000+ |
| RustSpider | 50 | 1000+ |
| JavaSpider | 20 | 200 |

### Rate Limiting

```python
# PySpider
from pyspider.performance.limiter import RateLimiter

limiter = RateLimiter(
    requests_per_second=10,
    burst=20
)
```

```go
// GoSpider
limiter := core.NewRateLimiter(core.RateLimiterConfig{
    RequestsPerSecond: 50,
    Burst:             100,
})
```

### Circuit Breaker

```python
# PySpider
from pyspider.performance.circuit_breaker import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=30,
    half_open_requests=2
)
```

---

## Related Docs

- `ADVANCED_USAGE_GUIDE.md` — advanced crawling scenarios
- `ENCRYPTED_SITE_CRAWLING_GUIDE.md` — encrypted site crawling
- `NODE_REVERSE_INTEGRATION_GUIDE.md` — Node.js reverse engineering integration
- `docs/FRAMEWORK_CAPABILITY_MATRIX.md` — full capability matrix
- `docs/FRAMEWORK_CAPABILITIES.md` — per-framework capability details
