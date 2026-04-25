# SuperSpider Publish / Release Status

Updated: 2026-04-25

This file is a release-facing summary for the GitHub publish step.

## Scope

Validated runtimes:

- `javaspider`
- `gospider`
- `rustspider`
- `pyspider`

## Checked Commands

### Aggregate Verification Gate

```bat
scripts\windows\verify-superspider.bat
```

Status: not rerun in this local pass; the per-runtime gates below were run directly.

Linux/macOS equivalents are available for native CI hosts:

```bash
bash scripts/linux/verify-superspider.sh
bash scripts/macos/verify-superspider.sh
```

Fast contract gate:

```bat
scripts\windows\verify-superspider.bat -Mode contract
```

```bash
bash scripts/linux/verify-superspider.sh contract
bash scripts/macos/verify-superspider.sh contract
```

Shell gates accept `PYTHON`, `GO`, `CARGO`, and `MAVEN` overrides for CI images with non-standard tool locations.

### JavaSpider

```bash
mvn -q test
```

Status: pass

### GoSpider

```bash
go test ./...
```

Status: pass

### RustSpider

```bash
cargo check --quiet
cargo test --quiet --lib
cargo test --quiet --test access_friction
```

Status: pass for `cargo test --quiet --lib` and `cargo test --quiet --test access_friction`

Note:

- Full non-library/integration tests should be run in CI with a longer timeout budget before claiming unrestricted Rust coverage.

### PySpider

```bash
python -m pytest pyspider\tests\test_access_friction.py pyspider\tests\test_locator_analyzer.py pyspider\tests\test_super_framework.py pyspider\tests\test_api_server.py pyspider\tests\test_core_spider.py pyspider\tests\test_downloader.py -q
```

Status: pass, 40-test targeted stable gate

Note:

- The verification scripts set `PYTHONPATH` to the repository root before PySpider tests.
- Full PySpider pytest is not claimed green until slow CLI tests are split or marked.

## Local Install Environment

The April 25, 2026 Windows pass was performed on Microsoft Windows 11 Pro 10.0.28000, 64-bit.

| Tool | Local version observed |
| --- | --- |
| Python | 3.14.3 |
| Go | 1.26.1 |
| Rust/Cargo | 1.94.0 |
| Maven | 3.9.14 |
| Java for Maven | 17.0.18 |
| Standalone `java` on PATH | 25.0.2 |

## Fixes Applied During Review

### RustSpider

- Added shared XPath helper:
  - `tools/xpath_extract.py`
- Stabilized Anthropic mock-server request reading:
  - `rustspider/src/ai/ai_client.rs`
- Added shared crawler-selection golden contract test:
  - `rustspider/src/crawler_selector.rs`

### PySpider

- Fixed Web graph extraction API `root_id` compatibility while exposing the internal graph root as `graph_root_id`:
  - `pyspider/web/app.py`
- Fixed `scrapy run --project` output-path / export-file persistence:
  - `pyspider/cli/main.py`
- Aligned parser dependencies in requirements:
  - `pyspider/requirements.txt`
- Added source-level crawler-selection contract export and golden fixture test:
  - `pyspider/profiler/crawler_selector.py`
  - `pyspider/tests/test_crawler_selector.py`

### JavaSpider

- Updated Maven/Lombok compatibility for modern local JDKs while keeping the project target at Java 17:
  - `javaspider/pom.xml`
- Fixed an invalid ecommerce example URL regex:
  - `javaspider/src/main/java/com/javaspider/examples/ecommerce/JDiPhone17Spider.java`
- Relaxed release Javadoc strictness and made installer packaging skip Javadoc generation:
  - `javaspider/pom.xml`
  - `scripts/windows/install-javaspider.bat`
  - `scripts/linux/install-javaspider.sh`
  - `scripts/macos/install-javaspider.sh`
- Added source-level crawler-selection contract export and golden fixture test:
  - `javaspider/src/main/java/com/javaspider/research/CrawlerSelection.java`
  - `javaspider/src/test/java/com/javaspider/research/CrawlerSelectorTest.java`

### GoSpider

- Added an ignore build tag to a standalone local scraper that would otherwise conflict with the framework root package:
  - `gospider/spider_taobao_iphone17.go`
- Added source-level crawler-selection contract export and golden fixture test:
  - `gospider/research/crawler_selector.go`
  - `gospider/research/crawler_selector_test.go`

### Shared Release Gate

- Added shared XPath/CSS extraction, browser locator analysis, DevTools element snapshots, and high-friction page classification across all four runtimes.
- Added repeatable verification scripts:
  - `scripts/windows/verify-superspider.bat`
  - `scripts/windows/verify-superspider.ps1`
  - `scripts/linux/verify-superspider.sh`
  - `scripts/macos/verify-superspider.sh`
- Added crawler-selection contract docs and golden fixtures:
  - `docs/CRAWLER_SELECTION_CONTRACT.md`
  - `examples/crawler-selection/ecommerce-search-input.html`
  - `examples/crawler-selection/ecommerce-search-selection.json`

## Documentation Updated

- Root publish docs:
  - `README.md`
  - `docs/DOCS_INDEX.md`
  - `PUBLISH_RELEASE_STATUS.md`
  - `PUBLISH_GUIDE.md`
  - `docs/SUPERSPIDER_INSTALLS.md`
- Matrix / capability docs:
  - `docs/FRAMEWORK_CAPABILITIES.md`
  - `docs/FRAMEWORK_CAPABILITY_MATRIX.md`
  - `docs/CRAWLER_TYPE_PLAYBOOK.md`
  - `docs/SITE_PRESET_PLAYBOOK.md`
- Runtime READMEs:
  - `javaspider/README.md`
  - `gospider/README.md`
  - `rustspider/README.md`
  - `pyspider/README.md`
- Example docs:
  - `javaspider/examples/README.md`
  - `gospider/examples/README.md`
  - `rustspider/examples/README.md`
  - `pyspider/examples/README.md`

## Remaining Publishing Notes

- Do not describe fallback-heavy AI paths as guaranteed LLM execution.
- Do not describe reverse-assisted browser simulation as full browser session execution.
- Keep advanced reverse / lab / anti-bot surfaces layered by maturity.
