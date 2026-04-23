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

## Shared Starter Assets

The repo now ships shared starter assets that pair directly with `python -m pyspider profile-site`, `python -m pyspider sitemap-discover`, and `python -m pyspider scrapy plan-ai`.

- `examples/crawler-types/`
  - normalized JobSpec templates for hydrated SPA, bootstrap JSON, infinite scroll, ecommerce search, and login-session flows
- `examples/site-presets/`
  - site-family starters for JD, Taobao, Tmall, Pinduoduo, Xiaohongshu, and Douyin Shop
- `examples/class-kits/`
  - reusable spider class templates for search, detail, API bootstrap, infinite scroll, login session, social feed, and ecommerce flows

Recommended order:

1. Run `profile-site` or `scrapy plan-ai`
2. Pick a crawler-type template or site preset
3. Copy the closest class kit into your project
4. Tune selectors, waits, auth assets, and output fields against saved artifacts

## Vertical Demos

- `spider_news.py`
- `spider_social.py`
- `spider_ecommerce.py`
- `ecommerce_catalog_spider.py`
- `ecommerce_detail_spider.py`
- `ecommerce_review_spider.py`
- `tiktok_spider.py`

## E-commerce Coverage

The `ecommerce_*` examples are public-data crawlers with:

- a JD fast path for SKU, price API, and review JSON
- JSON-LD fast paths for `taobao`, `tmall`, `pinduoduo`, and `amazon`
- a `generic` fallback for unknown storefronts
- broader extraction for images, videos, embedded JSON, and API candidates

Suggested runs:

```bash
python examples/ecommerce_catalog_spider.py jd
python examples/ecommerce_detail_spider.py taobao
python examples/ecommerce_review_spider.py generic
```

Supported built-in site families: `jd`, `taobao`, `tmall`, `pinduoduo`, `amazon`, `generic`.

These examples target publicly accessible product data. They are not a promise of universal access to login-gated or private commerce data.

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
