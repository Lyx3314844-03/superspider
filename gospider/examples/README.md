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
- `video_downloader/main.go`
  - generic video/media downloader flow
- `youku_downloader/main.go`
  - platform-oriented downloader flow

## Run Examples

```bash
go run ./examples/basic
go run ./examples/showcase
go run ./examples/scrapy_style
go run ./examples/video_downloader
```

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
