# PySpider Starter

## Goal

Smallest useful starter for AI-assisted Python crawling.

## Quick Start

```bash
python -m pip install -r ../../../../pyspider/requirements.txt
python -m pyspider config init --output spider-framework.yaml
python -m pyspider crawl --config spider-framework.yaml
```

## Scrapy-Style Quick Start

```bash
python -m pyspider scrapy run --project . --output artifacts/exports/pyspider-starter-items.json
python -m pyspider scrapy run --project . --spider demo
python -m pyspider scrapy list --project .
python -m pyspider scrapy validate --project .
python -m pyspider scrapy genspider news example.com --project .
```

## Files

- `spider-framework.yaml`
- `job.json`
- `scrapy_demo.py`
- `run-scrapy.sh`
- `run-scrapy.ps1`

## Notes

- Best fit for rapid extraction, AI/runtime experiments, and research-oriented crawling.
- If you copy this starter outside this repository, install the packaged `pyspider` dependency first.
