# RustSpider Starter

## Goal

Smallest useful starter for typed high-performance crawling.

## Quick Start

```bash
cargo run --manifest-path ../../../rustspider/Cargo.toml -- config init --output spider-framework.yaml
cargo run --manifest-path ../../../rustspider/Cargo.toml -- crawl --config spider-framework.yaml
```

## Scrapy-Style Quick Start

```bash
cargo run --manifest-path ../../../rustspider/Cargo.toml --quiet -- scrapy run --project . --output artifacts/exports/rustspider-starter-items.json
cargo run --manifest-path ../../../rustspider/Cargo.toml --quiet -- scrapy run --project . --spider demo
cargo run --manifest-path ../../../rustspider/Cargo.toml --quiet -- scrapy list --project .
cargo run --manifest-path ../../../rustspider/Cargo.toml --quiet -- scrapy validate --project .
cargo run --manifest-path ../../../rustspider/Cargo.toml --quiet -- scrapy genspider --name news --domain example.com --project .
```

## Files

- `spider-framework.yaml`
- `job.json`
- `Cargo.toml`
- `src/main.rs`
- `run-scrapy.sh`
- `run-scrapy.ps1`

## Notes

- Best fit for high-reliability cores, explicit runtime control, and performance-sensitive workloads.
- The local `Cargo.toml` points to `../../../rustspider`; update the dependency path after copying out of this repo.
