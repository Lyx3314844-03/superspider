# GoSpider Starter

## Goal

Smallest useful starter for service-style and concurrent Go crawling.

## Quick Start

```bash
go run ../../../gospider/cmd/gospider config init --output spider-framework.yaml
go run ../../../gospider/cmd/gospider crawl --config spider-framework.yaml
```

## Scrapy-Style Quick Start

```bash
go run ../../../gospider/cmd/gospider scrapy run --project . --output artifacts/exports/gospider-starter-items.json
go run ../../../gospider/cmd/gospider scrapy run --project . --spider demo
go run ../../../gospider/cmd/gospider scrapy list --project .
go run ../../../gospider/cmd/gospider scrapy validate --project .
go run ../../../gospider/cmd/gospider scrapy genspider --name news --domain example.com --project .
```

## Files

- `spider-framework.yaml`
- `job.json`
- `go.mod`
- `main.go`
- `run-scrapy.sh`
- `run-scrapy.ps1`

## Notes

- Best fit for concurrent crawling, lightweight deployment, and control-plane friendly services.
- The local `go.mod` uses `replace gospider => ../../../gospider`; update that path after copying out of this repo.
