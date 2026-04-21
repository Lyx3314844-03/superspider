# JavaSpider Examples

These examples complement the unified JavaSpider CLI and Maven build surface.

## Quick Start

### Build first

```bash
mvn -q -DskipTests package
java -jar ../target/javaspider-*.jar capabilities
```

## Source Examples

- `legacy/QQVideoSpiderHttpClient.java`
- `legacy/TencentVideoSpider.java`
- `legacy/TencentVideoSpiderEnhanced.java`
- `legacy/UniversalMediaSpider.java`
- `legacy/YoukuMediaSpider.java`
- `legacy/YoukuVideoSpider.java`
- `legacy/YoukuVideoSpiderEnhanced.java`
- `legacy/YouTubePlaylistSpider.java`
- `legacy/YouTubeVideoSpider.java`

## Preferred Public Surface

For GitHub-facing documentation, prefer these active entrypoints over the legacy source files:

- `com.javaspider.cli.SuperSpiderCLI`
- `com.javaspider.cli.WorkflowSpiderCLI`
- `com.javaspider.cli.WorkflowReplayCLI`
- `com.javaspider.examples.DistributedExample`
- `com.javaspider.examples.ScrapyStyleDemo`

## Notes

- The files under `legacy/` are source references, not the canonical release surface.
- New examples for public docs should prefer CLI commands or active `src/main/java/com/javaspider/examples/*` classes.
