# Advanced Usage Guide

This guide covers advanced crawling scenarios supported across all four SuperSpider runtimes.

## WAF Bypass and Behavioral Anti-Bot

All four runtimes include WAF bypass and behavioral simulation modules.

### Behavioral Simulation

The anti-bot modules simulate human-like browser behavior:

- mouse movement patterns
- scroll behavior
- reading pace simulation
- randomized timing between actions

### WAF Bypass Techniques

- TLS fingerprint rotation
- HTTP/2 fingerprint normalization
- Header order randomization
- Cookie jar management
- Referer chain simulation

### PySpider

```python
from pyspider.antibot import AntiBotEnhancer

enhancer = AntiBotEnhancer()
enhancer.enable_behavioral_simulation()
enhancer.enable_waf_bypass()
```

### GoSpider

```go
import "github.com/superspider/gospider/antibot"

enhancer := antibot.NewEnhancer()
enhancer.EnableBehavioralSimulation()
enhancer.EnableWAFBypass()
```

### RustSpider

```rust
use rustspider::antibot::AntiBotEnhancer;

let enhancer = AntiBotEnhancer::new()
    .with_behavioral_simulation()
    .with_waf_bypass();
```

### JavaSpider

```java
AntiBotEnhancer enhancer = new AntiBotEnhancer();
enhancer.enableBehavioralSimulation();
enhancer.enableWAFBypass();
```

---

## Client Certificate Authentication

For sites that require mutual TLS (mTLS) authentication.

### PySpider

```python
from pyspider.core.config import SpiderConfig

config = SpiderConfig(
    client_cert="/path/to/client.crt",
    client_key="/path/to/client.key",
    ca_cert="/path/to/ca.crt"
)
```

### GoSpider

```go
config := core.NewConfig()
config.SetClientCert("/path/to/client.crt", "/path/to/client.key")
config.SetCACert("/path/to/ca.crt")
```

### RustSpider

```rust
let config = SpiderConfig::new()
    .client_cert("/path/to/client.crt", "/path/to/client.key")
    .ca_cert("/path/to/ca.crt");
```

### JavaSpider

```java
SpiderConfig config = new SpiderConfig()
    .clientCert("/path/to/client.crt", "/path/to/client.key")
    .caCert("/path/to/ca.crt");
```

---

## API Key Management

For crawling APIs that require key rotation or rate-limited key pools.

### PySpider

```python
from pyspider.core.config import SpiderConfig

config = SpiderConfig(
    api_keys=["key1", "key2", "key3"],
    api_key_rotation="round_robin"  # or "random"
)
```

### GoSpider

```go
config := core.NewConfig()
config.SetAPIKeys([]string{"key1", "key2", "key3"})
config.SetAPIKeyRotation("round_robin")
```

### RustSpider

```rust
let config = SpiderConfig::new()
    .api_keys(vec!["key1", "key2", "key3"])
    .api_key_rotation(RotationMode::RoundRobin);
```

### JavaSpider

```java
SpiderConfig config = new SpiderConfig()
    .apiKeys(List.of("key1", "key2", "key3"))
    .apiKeyRotation(RotationMode.ROUND_ROBIN);
```

---

## Proxy Configuration

### Proxy Pool Setup

All four runtimes support proxy pools with health checking and automatic rotation.

### PySpider

```python
from pyspider.core.proxy_pool import ProxyPool

pool = ProxyPool(
    proxies=["http://proxy1:8080", "http://proxy2:8080"],
    rotation="round_robin",
    health_check=True
)
```

### GoSpider

```go
import "github.com/superspider/gospider/core"

pool := core.NewProxyPool(
    []string{"http://proxy1:8080", "http://proxy2:8080"},
    core.WithRotation("round_robin"),
    core.WithHealthCheck(true),
)
```

### RustSpider

```rust
use rustspider::proxy::ProxyPool;

let pool = ProxyPool::new()
    .proxies(vec!["http://proxy1:8080", "http://proxy2:8080"])
    .rotation(RotationMode::RoundRobin)
    .health_check(true);
```

### JavaSpider

```java
ProxyPool pool = new ProxyPool()
    .proxies(List.of("http://proxy1:8080", "http://proxy2:8080"))
    .rotation(RotationMode.ROUND_ROBIN)
    .healthCheck(true);
```

---

## Distributed Crawling

All four runtimes support distributed execution with Redis-backed queues.

### Queue Backends

| Backend | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Redis | ✅ | ✅ | ✅ | ✅ |
| RabbitMQ | ✅ | ✅ | ✅ | ✅ |
| Kafka | ✅ | ✅ | ✅ | ✅ |

### PySpider Distributed Setup

```python
from pyspider.distributed import RedisDistributed

dist = RedisDistributed(redis_url="redis://localhost:6379")
dist.start_worker(worker_id="worker-1")
```

### GoSpider Distributed Setup

```go
import "github.com/superspider/gospider/distributed"

service := distributed.NewService(
    distributed.WithRedis("redis://localhost:6379"),
)
service.StartWorker("worker-1")
```

### RustSpider Distributed Setup

```rust
use rustspider::distributed::DistributedService;

let service = DistributedService::new()
    .redis("redis://localhost:6379")
    .start_worker("worker-1");
```

### JavaSpider Distributed Setup

```java
DistributedService service = new DistributedService()
    .redis("redis://localhost:6379")
    .startWorker("worker-1");
```

---

## Checkpoint and Incremental Crawling

All four runtimes support checkpointing to resume interrupted crawls.

### PySpider

```python
from pyspider.core.checkpoint import CheckpointManager

manager = CheckpointManager(checkpoint_dir="./checkpoints")
spider = Spider(checkpoint=manager)
spider.resume()  # resumes from last checkpoint
```

### GoSpider

```go
import "github.com/superspider/gospider/core"

checkpoint := core.NewCheckpointManager("./checkpoints")
spider := core.NewSpider(core.WithCheckpoint(checkpoint))
spider.Resume()
```

### RustSpider

```rust
use rustspider::checkpoint::CheckpointManager;

let checkpoint = CheckpointManager::new("./checkpoints");
let spider = Spider::new().checkpoint(checkpoint).resume();
```

### JavaSpider

```java
CheckpointManager checkpoint = new CheckpointManager("./checkpoints");
Spider spider = new Spider().checkpoint(checkpoint).resume();
```

---

## AI-Assisted Extraction

### PySpider (strongest AI support)

```python
from pyspider.ai.ai_extractor import AIExtractor
from pyspider.ai_extractor.llm_extractor import LLMExtractor

extractor = AIExtractor()
result = extractor.extract(html, schema={"title": "str", "price": "float"})

# LLM-based extraction
llm = LLMExtractor(model="gpt-4o")
result = llm.extract(html, prompt="Extract product name and price")
```

### GoSpider

```go
import "github.com/superspider/gospider/ai"

extractor := ai.NewAIExtractor()
result := extractor.Extract(html, map[string]string{"title": "str", "price": "float"})
```

### RustSpider

```rust
use rustspider::ai::AIExtractor;

let extractor = AIExtractor::new();
let result = extractor.extract(&html, &schema);
```

---

## Related Docs

- `ENCRYPTED_SITE_CRAWLING_GUIDE.md` — handling JavaScript-encrypted sites
- `NODE_REVERSE_INTEGRATION_GUIDE.md` — Node.js reverse engineering integration
- `ULTIMATE_ENHANCEMENT_GUIDE.md` — full capability enhancement reference
- `docs/FRAMEWORK_CAPABILITY_MATRIX.md` — capability comparison across all four runtimes
