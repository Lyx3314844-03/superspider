# CSharpSpider Starter

## Goal

Smallest useful starter for C# crawling with the same unified project tooling as the other runtimes.

## Scrapy-Style Quick Start

```bash
csharpspider scrapy run --project .
csharpspider scrapy run --project . --spider demo
csharpspider scrapy list --project .
csharpspider scrapy doctor --project .
csharpspider scrapy genspider news example.com --project .
```

## Files

- `scrapy-project.json`
- `scrapy-plugins.json`
- `spider-framework.yaml`
- `src/project/Program.cs`
- `src/project/Spiders/DemoSpiderFactory.cs`
- `src/project/Plugins/DefaultPlugin.cs`

## Note

This repo environment currently does not have `dotnet`, so this starter is scaffolded but not compiled here.
