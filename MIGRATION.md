# Migration Guide

This repository now treats all four runtimes as one framework family.

## Old To New CLI

### Java

- Old: `com.javaspider.cli.MediaDownloaderCLI`
- Old: ad hoc example launchers
- New: `com.javaspider.EnhancedSpider`

Examples:

- Old: `java ... MediaDownloaderCLI version`
- New: `java ... EnhancedSpider version`
- Old: legacy video/browser demos
- New: `EnhancedSpider browser fetch --url <url>`

### Go

- Old: `go run enhanced.go ...`
- New: `go run ./cmd/gospider ...`

Examples:

- Old: `go run enhanced.go search ...`
- New: `go run ./cmd/gospider crawl --url <url>`
- Old: custom browser entrypoints
- New: `go run ./cmd/gospider browser fetch --url <url>`

### Rust

- Old: `cargo run --bin preflight -- ...`
- Old: `playwright.rs` and browser-specific examples as primary references
- New: `cargo run -- ...`

Examples:

- Old: `cargo run --bin preflight -- --json`
- New: `cargo run -- doctor --json`
- Old: browser example as primary path
- New: `cargo run -- browser fetch --url <url>`

### Python

- Old: `python enhanced_main.py ...`
- Old: `python -m pyspider.cli.video_downloader ...`
- New: `pyspider ...`

Examples:

- Old: `python enhanced_main.py search ...`
- New: `pyspider crawl --url <url>`
- Old: browser demos as standalone entrypoints
- New: `pyspider browser fetch --url <url>`

## Shared Config

Use:

- `spider-framework.yaml`

Generate it with:

- `config init --output spider-framework.yaml`

## Shared Artifacts

Use:

- `artifacts/checkpoints`
- `artifacts/datasets`
- `artifacts/exports`
- `artifacts/browser`

## Legacy Wrappers

Compatibility wrappers that only shadowed the canonical browser and CLI surfaces have been removed:

- `gospider/browser.go`
- `pyspider/browser.py`
- `rustspider/src/playwright.rs`
- `javaspider/src/main/java/com/javaspider/examples/SimpleYouTubeSpider.java`

Legacy runtime examples may still exist under `examples/legacy/*`, but they are no longer part of the public framework surface.
