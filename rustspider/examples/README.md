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
- `ecommerce/`
  - native catalog/detail/review ecommerce spiders with JD fast path and generic fallback
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
cargo run --example ecommerce -- catalog jd
cargo run --example ecommerce -- detail amazon
cargo run --example ecommerce -- review generic
cargo run --example playwright_example
```

Supported built-in site families: `jd`, `taobao`, `tmall`, `pinduoduo`, `amazon`, `generic`.

Fast-path coverage:

- `jd`: SKU + price API + review JSON
- `taobao`, `tmall`, `pinduoduo`, `amazon`: JSON-LD product / rating fast paths when available

The ecommerce example is a high-coverage public-data crawler. It expands extraction to images, videos, embedded JSON, and API candidates, but it is not a claim of universal access to private marketplace data.

## Shared Starter Assets

The root `examples/` assets are first-class RustSpider starters now.

- `examples/crawler-types/`
  - normalized JobSpec templates for difficult page families
- `examples/site-presets/`
  - domain starters for major marketplace and social-commerce families
- `examples/class-kits/`
  - reusable spider class templates that mirror the public runtime surface

Recommended order:

1. Run `rustspider profile-site --url <target>`
2. Pick the matching crawler-type template or site preset
3. Reuse a class kit before creating a fresh spider from scratch
4. Validate with saved HTML, screenshot, network, and trace artifacts

## Legacy / Specialized

- `legacy/cluster_worker.rs`
- `legacy/dynamic_crawler.rs`
- `legacy/enhanced.rs`
- `legacy/youku_video_downloader.rs`
- `legacy/youku_video_spider.rs`
- `legacy/youtube_playlist_enhanced.rs`

Prefer the non-legacy examples and the unified CLI in release-facing documentation.
