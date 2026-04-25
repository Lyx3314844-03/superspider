# GoSpider Examples

These examples are organized around the current public GoSpider surface.

## Quick Start

### Build first

```bash
go build -o gospider.exe .
./gospider.exe capabilities
```

### Suggested examples

- `basic/main.go`
  - smallest end-to-end crawl example
- `showcase/main.go`
  - broad feature showcase across runtime modules
- `scrapy_style/main.go`
  - project-style / scrapy-like flow
- `ecommerce/main.go`
  - unified ecommerce crawler wrapper for catalog/detail/review and browser-backed capture
- `ecommerce/browser_capture.go`
  - Selenium-backed ecommerce capture and artifact export
- `video_downloader/main.go`
  - generic video/media downloader flow
- `youku_downloader/main.go`
  - platform-oriented downloader flow

## Run Examples

```bash
go run ./examples/basic
go run ./examples/showcase
go run ./examples/scrapy_style
go run ./examples/ecommerce catalog jd
go run ./examples/ecommerce detail taobao
go run ./examples/ecommerce review generic
go run ./examples/ecommerce browser jd catalog
go run ./examples/video_downloader
```

Supported built-in site families: `jd`, `taobao`, `tmall`, `pinduoduo`, `amazon`, `xiaohongshu`, `douyin-shop`, `generic`.

Fast-path coverage:

- `jd`: SKU + price API + review JSON
- `taobao`, `tmall`, `pinduoduo`, `amazon`: JSON-LD product / rating fast paths when available
- `xiaohongshu`, `douyin-shop`: browser-oriented public-data profiles with generic extraction heuristics

The ecommerce examples are public-data extractors. They widen field coverage with images, videos, embedded JSON, and API candidates, but they do not imply access to private or login-gated commerce data.

`EcommerceCrawler` is the preferred class-style entrypoint when you want a single wrapper for catalog/detail/review runs. Use `RunBrowser()` or the `browser_capture.go` companion when you need rendered HTML, storage-state output, or browser artifacts.

## Shared Starter Assets

The repo-level starter assets are part of the public GoSpider surface now. Use them before hard-coding selectors into a runtime example.

- `examples/crawler-types/`
  - normalized JobSpec templates for difficult page families
- `examples/site-presets/`
  - domain starters for JD, Taobao, Tmall, Pinduoduo, Xiaohongshu, and Douyin Shop
- `examples/class-kits/`
  - reusable spider class templates for all four runtimes
- `examples/ecommerce/`
  - native ecommerce crawler wrapper and browser capture companion

Recommended order:

1. Run `gospider profile-site --url <target>`
2. Optionally run `gospider sitemap-discover --url <target>`
3. Start from the closest preset or crawler-type template
4. Pull in the matching class kit or native ecommerce example

## Domain-Specific Media Examples

- `tencent_downloader/main.go`
- `tencent_monitor/main.go`
- `tencent_video_downloader/main.go`
- `youku_network_monitor/main.go`
- `youku_simple_downloader/main.go`

## Legacy

These are preserved for backward reference, not for the canonical product surface:

- `legacy/cluster_worker.go`
- `legacy/distributed_main.go`
- `legacy/download_youku.ps1`
- `legacy/install_ffmpeg.py`
- `legacy/merge_video.py`

Prefer the unified CLI and the non-legacy examples when writing GitHub-facing docs.
