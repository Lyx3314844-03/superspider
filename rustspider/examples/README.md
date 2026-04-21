# RustSpider Examples

These examples map to the current RustSpider public runtime surface.

## Quick Start

### Build first

```bash
cargo build --release
./target/release/rustspider capabilities
```

### Suggested examples

- `main.rs`
  - minimal runtime entry
- `scrapy_style.rs`
  - typed project-style crawling
- `playwright_example.rs`
  - browser automation entry
- `youku_video_downloader.rs`
  - media/downloader path
- `dynamic_crawler.rs`
  - dynamic-page oriented example

## Run Examples

```bash
cargo run --example main
cargo run --example scrapy_style
cargo run --example playwright_example
```

## Legacy / Specialized

- `legacy/cluster_worker.rs`
- `legacy/dynamic_crawler.rs`
- `legacy/enhanced.rs`
- `legacy/youku_video_downloader.rs`
- `legacy/youku_video_spider.rs`
- `legacy/youtube_playlist_enhanced.rs`

Prefer the non-legacy examples and the unified CLI in release-facing documentation.
