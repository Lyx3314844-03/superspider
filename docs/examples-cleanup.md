# Examples Cleanup Plan

## Keep

These still represent useful runtime-specific demonstrations:

- `gospider/examples/basic/main.go`
- `gospider/examples/showcase/main.go`
- `rustspider/examples/main.rs`
- `rustspider/examples/playwright_example.rs`
- `pyspider/examples/main.py`
- `pyspider/examples/simple_spider.py`
- `javaspider/src/main/java/com/javaspider/examples/DistributedExample.java`

## Keep As Legacy

These are still valid references for media/platform-specific workflows, but should not define the canonical public surface:

- `javaspider/src/main/java/com/javaspider/examples/*VideoSpider*.java`
- `gospider/examples/*downloader*`
- `pyspider/examples/youtube_*`
- `pyspider/examples/youku_*`
- `rustspider/examples/youku_*`
- `rustspider/examples/youtube_playlist_enhanced.rs`
- `gospider/examples/legacy/*`
- `javaspider/examples/legacy/*`

## Delete Candidates After Reference Removal

These should be removed only after any remaining docs/tests stop pointing at them:

- runtime-specific media demos that still have documentation value

## Removed Already

- `*.bak` example files
- `*.need_*` placeholder files
- `javaspider/src/main/java/SimpleYouTubeSpider.java`
- `javaspider/run_simple.bat`
- `gospider/enhanced.go`
- `pyspider/enhanced_main.py`
- `pyspider/fix_regex.py`

## Rules

1. Do not extend legacy examples with new framework features.
2. New user-facing docs should point only to unified CLI commands.
3. Platform/media examples may stay, but must not redefine shared config or shared artifact paths.
4. Java media examples that remain in place must stay explicitly `@Deprecated`.
