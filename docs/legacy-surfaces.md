# Legacy Surfaces

The repository now removes compatibility-only entrypoints instead of carrying them forward indefinitely.

Deleted legacy wrappers:

- `gospider/browser.go`
- `pyspider/browser.py`
- `rustspider/src/playwright.rs`
- `javaspider/src/main/java/com/javaspider/examples/SimpleYouTubeSpider.java`

## Explicitly deprecated runtime examples

- `javaspider/examples/legacy/*VideoSpider*.java`
- `javaspider/examples/legacy/UniversalMediaSpider.java`
- `javaspider/examples/legacy/QQVideoSpiderHttpClient.java`

These Java examples remain as source-only legacy references outside `src/main/java` and are excluded from the production Maven artifact.

## Cleanup policy

Delete a legacy surface only after:

1. there are no test references
2. there are no CI or build references
3. there are no documentation references
4. a forwarding path exists in the unified CLI
