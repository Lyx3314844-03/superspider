# JavaSpider Starter

## Goal

Smallest useful starter for enterprise-style browser and workflow crawling.

## Quick Start

```bash
mvn -q -f ../../../javaspider/pom.xml compile dependency:copy-dependencies
java -cp "../../../javaspider/target/classes;../../../javaspider/target/dependency/*" com.javaspider.EnhancedSpider config init --output spider-framework.yaml
java -cp "../../../javaspider/target/classes;../../../javaspider/target/dependency/*" com.javaspider.EnhancedSpider crawl --config spider-framework.yaml
```

## Scrapy-Style Quick Start

```bash
mvn -q -f ../../../javaspider/pom.xml compile dependency:copy-dependencies
java -cp "../../../javaspider/target/classes;../../../javaspider/target/dependency/*" com.javaspider.EnhancedSpider scrapy run --project . --output artifacts/exports/javaspider-starter-items.json
java -cp "../../../javaspider/target/classes;../../../javaspider/target/dependency/*" com.javaspider.EnhancedSpider scrapy run --project . --spider demo
java -cp "../../../javaspider/target/classes;../../../javaspider/target/dependency/*" com.javaspider.EnhancedSpider scrapy list --project .
java -cp "../../../javaspider/target/classes;../../../javaspider/target/dependency/*" com.javaspider.EnhancedSpider scrapy validate --project .
java -cp "../../../javaspider/target/classes;../../../javaspider/target/dependency/*" com.javaspider.EnhancedSpider scrapy genspider --name news --domain example.com --project .
```

## Files

- `spider-framework.yaml`
- `job.json`
- `src/main/java/starter/ScrapyStyleStarter.java`
- `run-scrapy.sh`
- `run-scrapy.ps1`

## Notes

- Best fit for browser workflows, enterprise integrations, and more structured runtime surfaces.
- The scrapy-style starter compiles against `../../../javaspider/target/classes` and `target/dependency/*`.
