# Four Runtime Health Report

Updated: 2026-04-25

This is the current verification snapshot for `javaspider`, `gospider`, `rustspider`, and `pyspider`.

## Summary

| Runtime | Command | Result | Notes |
| --- | --- | --- | --- |
| GoSpider | `go test ./...` | Pass | Full Go package suite passed. |
| RustSpider | `cargo test --quiet --lib` | Pass | 110 library tests passed. Non-library/integration tests remain a separate release gate. |
| RustSpider | `cargo test --quiet --test access_friction` | Pass | Access-friction integration test passed. |
| PySpider | `python -m pytest tests\test_access_friction.py tests\test_locator_analyzer.py tests\test_super_framework.py tests\test_api_server.py tests\test_core_spider.py tests\test_downloader.py -q` | Pass | 40 stable targeted tests passed. Full pytest is still not claimed green because the broad local run timed out. |
| JavaSpider | `mvn -q test` | Pass | Full Maven test suite passed with expected noisy runtime logs. |
| Shared Contract | `examples/crawler-selection/ecommerce-search-selection.json` parsed plus four language selector tests | Pass | Java, Go, Rust, and Python all validate the same crawler-selection golden fixture. |

## Stable Verification Script

Windows:

```bat
scripts\windows\verify-superspider.bat
```

Linux:

```bash
bash scripts/linux/verify-superspider.sh
```

macOS:

```bash
bash scripts/macos/verify-superspider.sh
```

Contract-only smoke:

```bat
scripts\windows\verify-superspider.bat -Mode contract
```

```bash
bash scripts/linux/verify-superspider.sh contract
bash scripts/macos/verify-superspider.sh contract
```

The shell gates accept `PYTHON`, `GO`, `CARGO`, and `MAVEN` environment overrides. `PYTHON` must point to an interpreter with `pytest` installed.

The stable gate intentionally avoids claiming PySpider full-suite success until slow CLI tests are split or marked.

## JavaSpider Status

JavaSpider now passes:

```bash
mvn -q test
mvn -q -Dtest=HtmlSelectorContractTest test
```

The Maven compiler configuration uses the Java 17 project properties and Lombok 1.18.44 for compatibility with modern JDK toolchains. Generated standalone files under `com/superspider/**` are excluded from the Maven main compile so invalid local scratch sources do not break framework verification.

## GoSpider Fixes Applied

The root Go package previously failed when a standalone local scraper with its own `main()` lived beside the framework entrypoint. That scratch file is now guarded with `//go:build ignore`, while the framework packages continue to pass `go test ./...`.

Verification:

```bash
go test ./...
```

Result: passed.

## RustSpider Status

Verification:

```bash
cargo test --quiet --lib
cargo test --quiet --test access_friction
```

Results:

- `cargo test --quiet --lib`: passed, 110 tests.
- `cargo test --quiet --test access_friction`: passed.

The AI client mock server was hardened to read request headers and `Content-Length` before responding, removing an observed local HTTP mock race.

## PySpider Status

Fixes applied:

- Added access-friction coverage for slider CAPTCHA, JavaScript signature, fingerprint-required, and empty JavaScript shell responses.
- Added browser locator analysis coverage for generated XPath/CSS selectors.

Current stable targeted verification:

```bash
python -m pytest tests\test_access_friction.py tests\test_locator_analyzer.py tests\test_super_framework.py tests\test_api_server.py tests\test_core_spider.py tests\test_downloader.py -q
```

Result: passed, 40 tests.

Historical broad-suite note: `pytest -q tests/test_cli.py` timed out at 60 seconds in a previous run and should be split further before full PySpider release.

## Current Release Gate

Do not claim unrestricted full-suite coverage until:

1. PySpider CLI tests are split and either pass or have explicit slow-test markers/timeouts.
2. RustSpider tests beyond `--lib` are run in a longer CI budget or intentionally scoped.
3. Linux/macOS stable gates are run on native CI hosts rather than only through shell compatibility on Windows.
