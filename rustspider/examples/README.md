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
- `ecommerce/main.rs`
  - unified ecommerce crawler wrapper for catalog/detail/review and browser-backed capture
- `ecommerce_browser_capture.rs`
  - browser capture companion for rendered HTML and artifact export
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
cargo run --example ecommerce_browser_capture --features browser -- jd catalog
```

Supported built-in site families: `jd`, `taobao`, `tmall`, `pinduoduo`, `amazon`, `xiaohongshu`, `douyin-shop`, `generic`.

Fast-path coverage:

- `jd`: SKU + price API + review JSON
- `taobao`, `tmall`, `pinduoduo`, `amazon`: JSON-LD product / rating fast paths when available
- `xiaohongshu`, `douyin-shop`: browser-oriented public-data profiles with generic extraction heuristics

The ecommerce example is a high-coverage public-data crawler. It expands extraction to images, videos, embedded JSON, and API candidates, but it is not a claim of universal access to private marketplace data.

`EcommerceCrawler` is the preferred class-style entrypoint for static catalog/detail/review runs. Use the browser capture companion when you need rendered HTML, storage state, or network artifacts.

## Shared Starter Assets

The root `examples/` assets are first-class RustSpider starters now.

- `examples/crawler-types/`
  - normalized JobSpec templates for difficult page families
- `examples/site-presets/`
  - domain starters for major marketplace and social-commerce families
- `examples/class-kits/`
  - reusable spider class templates that mirror the public runtime surface
- `examples/ecommerce/`
  - native ecommerce crawler wrapper and browser capture companion

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
