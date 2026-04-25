# JavaSpider Examples

These examples map to the current JavaSpider public runtime surface.

## Quick Start

### Build first

```bash
mvn -f javaspider/pom.xml -q -DskipTests package
java -jar javaspider/target/javaspider-*.jar capabilities
```

## Core

- `DistributedExample.java`
- `ScrapyStyleDemo.java`
- `ecommerce/EcommerceCrawler.java`
- `ecommerce/EcommerceSeleniumCrawler.java`
- `ecommerce/UniversalEcommerceDetector.java`
- `ecommerce/EcommerceSiteProfiles.java`
- `ecommerce/EcommerceCatalogSpider.java`
- `ecommerce/EcommerceDetailSpider.java`
- `ecommerce/EcommerceReviewSpider.java`
- `ecommerce/EcommerceExampleRunner.java`

## E-commerce Examples

The `examples/ecommerce` package exposes native catalog/detail/review crawlers with:

- a JD fast path for SKU, price API, and review JSON
- a `generic` fallback for unknown storefronts
- broader public-data extraction for images, videos, embedded JSON, and API candidates

The preferred class-style entrypoint is `com.javaspider.examples.ecommerce.EcommerceCrawler`. It unifies catalog/detail/review modes and can hand off to `EcommerceSeleniumCrawler` when rendered-page capture is needed.

Suggested entrypoint:

- `com.javaspider.examples.ecommerce.EcommerceCrawler`

```java
EcommerceCrawler crawler = new EcommerceCrawler("jd");
crawler.run("catalog");
crawler.runBrowser("catalog");
```

Supported built-in site families: `jd`, `taobao`, `tmall`, `pinduoduo`, `amazon`, `xiaohongshu`, `douyin-shop`, `generic`.

Fast-path coverage:

- `jd`: SKU + price API + review JSON
- `taobao`, `tmall`, `pinduoduo`, `amazon`: JSON-LD product / rating fast paths when available
- `xiaohongshu`, `douyin-shop`: browser-oriented public-data profiles with generic extraction heuristics

These examples target publicly accessible product data only.

## Shared Starter Assets

The repo-level starter assets are part of the documented JavaSpider surface now.

- `examples/crawler-types/`
  - normalized JobSpec templates for SPA, bootstrap, infinite-scroll, ecommerce-search, and login-session flows
- `examples/site-presets/`
  - site-family starter presets for major marketplace and social-commerce domains
- `examples/class-kits/`
  - reusable spider class templates that line up with the Java runtime surface

Recommended order:

1. Run `java -jar javaspider/target/javaspider-*.jar profile-site --url <target>`
2. Choose the closest site preset or crawler-type template
3. Pull the matching class kit into your project package
4. Use the native ecommerce examples when you want a concrete public-data pattern

## Legacy References

Legacy media/runtime-specific examples have moved to:

- `javaspider/examples/legacy/`

Those files stay as source-only references and are explicitly marked `@Deprecated`.
The canonical public surface is `com.javaspider.EnhancedSpider`.
