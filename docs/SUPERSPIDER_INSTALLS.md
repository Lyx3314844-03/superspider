# SuperSpider Install Matrix

Updated: 2026-04-25

SuperSpider ships four runtimes. Every runtime has dedicated installers for Windows, Linux, and macOS, plus one aggregate installer per operating system.

---

## Quick Install Reference

Install everything:

| OS | Aggregate installer |
| --- | --- |
| Windows | `scripts\windows\install-superspider.bat` |
| Linux | `bash scripts/linux/install-superspider.sh` |
| macOS | `bash scripts/macos/install-superspider.sh` |

Install one runtime:

| Framework | Windows | Linux | macOS | Output |
| --- | --- | --- | --- | --- |
| PySpider | `scripts\windows\install-pyspider.bat` | `scripts/linux/install-pyspider.sh` | `scripts/macos/install-pyspider.sh` | `.venv-pyspider` |
| GoSpider | `scripts\windows\install-gospider.bat` | `scripts/linux/install-gospider.sh` | `scripts/macos/install-gospider.sh` | `gospider` binary |
| RustSpider | `scripts\windows\install-rustspider.bat` | `scripts/linux/install-rustspider.sh` | `scripts/macos/install-rustspider.sh` | `rustspider/target/release/rustspider` |
| JavaSpider | `scripts\windows\install-javaspider.bat` | `scripts/linux/install-javaspider.sh` | `scripts/macos/install-javaspider.sh` | `javaspider/target` |

---

## Prerequisites

The aggregate installers require all tools listed below. Single-runtime installers require only the matching row.

| Framework | Required tools |
| --- | --- |
| PySpider | Python 3.10+ recommended, `venv`, `pip` |
| GoSpider | Go 1.24+ |
| RustSpider | Rust 1.70+, Cargo |
| JavaSpider | Java 17 target, Maven 3.8+ |

## Supported Operating Systems

| OS family | Supported install baseline | Current verification note |
| --- | --- | --- |
| Windows | Windows 10/11 or Windows Server 2022+ | Verified on Microsoft Windows 11 Pro 10.0.28000, 64-bit |
| Linux | Ubuntu 22.04/24.04, Debian 12, or RHEL/Rocky/AlmaLinux 9+ compatible hosts | Use the Linux shell installers on native Linux CI before release |
| macOS | macOS 13 Ventura+ on Intel or Apple Silicon | Use the macOS shell installers on native macOS CI before release |

Current local tool versions used during the April 25, 2026 Windows verification:

| Tool | Local version observed |
| --- | --- |
| Python | 3.14.3 |
| Go | 1.26.1 |
| Rust/Cargo | 1.94.0 |
| Maven | 3.9.14 |
| Java for Maven | 17.0.18 |
| Standalone `java` on PATH | 25.0.2 |

---

## PySpider

### What the installer does

1. Checks that `python3` is available
2. Creates an isolated virtual environment at `.venv-pyspider`
3. Upgrades `pip` inside the venv
4. Installs all Python dependencies from `pyspider/requirements.txt`
5. Installs `pyspider` as an editable package
6. Verifies the install by running `python -m pyspider version`

### Verify after install

```bash
# Linux / macOS
source .venv-pyspider/bin/activate
python -m pyspider version

# Windows
.venv-pyspider\Scripts\activate
python -m pyspider version
```

### Key capabilities installed

- Python-native CLI with scrapy-style project runtime
- AI extraction: LLM (OpenAI + Anthropic/Claude), smart parser, schema-driven output
- Browser automation: Playwright (native)
- Anti-bot: access-friction classifier, browser upgrade plan, authorized challenge handoff, WAF profiling, and captcha-related helper paths
- Media download: YouTube, Bilibili, IQIYI, Tencent Video, Youku, Douyin, HLS, DASH, FFmpeg
- Distributed: Redis, RabbitMQ, Kafka
- Node-reverse client for JS-encrypted sites
- Graph crawler, research runtime, notebook output
- REST API server, web UI

---

## GoSpider

### What the installer does

1. Checks that `go` is available
2. Runs `gospider/build.sh` (Linux/macOS) or `gospider/build.bat` (Windows)
3. Builds the Go binary via `go build ./cmd/gospider`
4. Verifies the binary exists at `gospider/gospider` (Linux/macOS) or `gospider/gospider.exe` (Windows)

### Verify after install

```bash
# Linux / macOS
./gospider/gospider --version

# Windows
gospider\gospider.exe --version
```

### Key capabilities installed

- Compiled Go CLI binary (no runtime dependencies)
- Concurrent crawling engine with rate limiting and deduplication
- Browser automation: Playwright + Selenium (native WebDriver client)
- Anti-bot: access-friction classifier, browser upgrade plan, authorized challenge handoff, WAF profiling, and captcha-related helper paths
- AI extraction: entity, summarizer, sentiment (OpenAI + Anthropic/Claude)
- Media download: YouTube, Bilibili, IQIYI, Tencent Video, Youku, Douyin (dedicated extractors)
- Distributed: Redis (native), RabbitMQ (broker-native), Kafka (broker-native)
- Node discovery: env, file, DNS-SRV, Consul, etcd
- Storage: SQLite, Postgres, MySQL, MongoDB (process adapters)
- Node-reverse client for JS-encrypted sites
- Audit trail, REST API server, web console

---

## RustSpider

### What the installer does

1. Checks that `cargo` is available
2. Runs `rustspider/build.sh` (Linux/macOS) or `rustspider/build.bat` (Windows)
3. Builds a release binary via `cargo build --release`
4. Verifies the binary exists at `rustspider/target/release/rustspider` (Linux/macOS) or `rustspider/target/release/rustspider.exe` (Windows)

### Verify after install

```bash
# Linux / macOS
./rustspider/target/release/rustspider --version

# Windows
rustspider\target\release\rustspider.exe --version
```

### Key capabilities installed

- Rust release binary with feature-gated modules
- Typed scrapy-style interface
- Browser automation: Playwright (node+playwright process) + Selenium (fantoccini facade)
- Anti-bot: access-friction classifier, browser upgrade plan, authorized challenge handoff, WAF profiling, and captcha-related helper paths
- AI extraction: entity, summarizer, sentiment (OpenAI + Anthropic/Claude), few-shot examples
- Media download: YouTube, Bilibili, IQIYI, Tencent Video, Youku, Douyin
- Distributed: Redis (native), RabbitMQ (bridge), Kafka (bridge)
- Node discovery: env, file, DNS-SRV, Consul, etcd
- Storage: SQLite, Postgres, MySQL, MongoDB (driver + process adapters)
- Node-reverse client for JS-encrypted sites
- Audit trail, preflight validation, benchmark suite

---

## JavaSpider

### What the installer does

1. Checks that `java` (17+) and `mvn` are available
2. Runs `mvn -q -f javaspider/pom.xml -DskipTests -Dmaven.javadoc.skip=true package dependency:copy-dependencies`
3. Verifies the `javaspider/target` directory was produced

### Verify after install

```bash
# Linux / macOS / Windows
java -jar javaspider/target/javaspider-*.jar --version
```

### Maven Profiles

Build with a specific profile to control which modules are included:

```bash
# Minimal build (core crawling only)
mvn -f javaspider/pom.xml -P lite -DskipTests package

# With AI extraction
mvn -f javaspider/pom.xml -P ai -DskipTests package

# With browser automation
mvn -f javaspider/pom.xml -P browser -DskipTests package

# With distributed runtime
mvn -f javaspider/pom.xml -P distributed -DskipTests package

# Full build (all modules)
mvn -f javaspider/pom.xml -P full -DskipTests package
```

### Key capabilities installed

- Maven / JAR packaging
- Browser automation: Selenium (native) + Playwright (Java helper)
- Anti-bot: access-friction classifier, browser upgrade plan, authorized challenge handoff, WAF profiling, and captcha-related helper paths
- AI extraction: entity, summarizer, sentiment (OpenAI + Anthropic/Claude), few-shot examples
- Media download: YouTube, Bilibili, IQIYI, Tencent Video, Youku, Douyin (generic fallback)
- Distributed: Redis (native), RabbitMQ (broker-native), Kafka (broker-native)
- Node discovery: env, file, DNS-SRV, Consul, etcd
- Node-reverse client for JS-encrypted sites
- Audit trail (strongest / dedicated)
- REST API server: `/health`, `/jobs`, `/jobs/{id}`, `/jobs/{id}/result`
- Workflow replay, async runtime

---

## Recommended Choice

| Scenario | Best runtime |
| --- | --- |
| Rapid prototyping, AI-heavy extraction | **PySpider** |
| High-concurrency binary deployment | **GoSpider** |
| Performance-sensitive, feature-gated release | **RustSpider** |
| Enterprise Java, Maven/JAR, browser automation | **JavaSpider** |
| Distributed worker cluster | **GoSpider** or **RustSpider** |
| LLM-powered structured extraction | **PySpider** |
| Media download (YouTube, Bilibili, etc.) | any (all four have full coverage) |
| JS-encrypted site crawling | any (all four support node-reverse) |
