# PySpider Examples

These examples reflect the current Python-first public surface.

## Quick Start

### Verify the runtime first

```bash
python -m pyspider version
python -m pyspider capabilities
```

### Suggested examples

- `simple_spider.py`
  - smallest single-spider example
- `main.py`
  - general runtime entry example
- `scrapy_style_demo.py`
  - project-style / scrapy-like usage
- `enhanced_features_demo.py`
  - broader runtime feature surface
- `custom_spider_template.py`
  - template for new project spiders

## Run Examples

```bash
python examples/simple_spider.py
python examples/scrapy_style_demo.py
python examples/enhanced_features_demo.py
```

## Vertical Demos

- `spider_news.py`
- `spider_social.py`
- `spider_ecommerce.py`
- `tiktok_spider.py`

## Media and Legacy

- `youku_video_downloader.py`
- `youku_video_spider.py`
- `youtube_enhanced_spider.py`
- `legacy/youtube_*`
- `legacy/youku_*`
- `legacy/distributed_demo.py`
- `legacy/distributed_main.py`
- `legacy/enhanced_features_demo.py`

These remain as reference examples, but the canonical user-facing surface is the unified CLI.
