# Media Parity Report

Updated: 2026-04-12

## Scope

This report tracks the shared media capability surface across the four SuperSpider runtimes:

- `pyspider`
- `gospider`
- `rustspider`
- `javaspider`

The target was concrete parity on the following media stack:

- HLS (`m3u8`)
- DASH (`mpd`)
- FFmpeg
- DRM detection
- YouTube
- Bilibili
- IQIYI
- Tencent Video
- Youku

## Final Matrix

| Capability | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| HLS (`m3u8`) | ✅ | ✅ | ✅ | ✅ |
| DASH (`mpd`) | ✅ | ✅ | ✅ | ✅ |
| FFmpeg | ✅ | ✅ | ✅ | ✅ |
| DRM detection | ✅ | ✅ | ✅ | ✅ |
| YouTube | ✅ | ✅ | ✅ | ✅ |
| Bilibili | ✅ | ✅ | ✅ | ✅ |
| IQIYI | ✅ | ✅ | ✅ | ✅ |
| Tencent Video | ✅ | ✅ | ✅ | ✅ |
| Youku | ✅ | ✅ | ✅ | ✅ |

## Code Evidence

### PySpider

- parser coverage: `pyspider/media/video_parser.py`
- media CLI and download path: `pyspider/cli/video_downloader.py`
- focused tests: `pyspider/tests/test_multimedia_downloader.py`, `pyspider/tests/test_video_downloader.py`

### GoSpider

- media command surface: `gospider/cmd/gospider/media_cmd.go`
- generic media path: `gospider/media/multiple_platform.go`
- platform extractors:
  - `gospider/extractors/bilibili/bilibili.go`
  - `gospider/extractors/iqiyi/iqiyi.go`
  - `gospider/extractors/tencent/tencent.go`
  - `gospider/extractors/youku/youku.go`
- focused tests:
  - `gospider/cmd/gospider/media_cmd_test.go`
  - `gospider/media/multiple_platform_test.go`
  - `gospider/extractors/bilibili/bilibili_test.go`
  - `gospider/extractors/iqiyi/iqiyi_test.go`
  - `gospider/extractors/tencent/tencent_test.go`
  - `gospider/extractors/youku/youku_test.go`

### RustSpider

- media parser and CLI: `rustspider/src/media/video_parser.rs`, `rustspider/src/cli.rs`
- DRM detection: `rustspider/src/video/drm_detector.rs`
- focused tests: `rustspider/src/media/video_parser.rs` test module

### JavaSpider

- media CLI and fallback chain: `javaspider/src/main/java/com/javaspider/cli/MediaDownloaderCLI.java`
- generic media parser: `javaspider/src/main/java/com/javaspider/media/parser/GenericParser.java`
- DRM detection: `javaspider/src/main/java/com/javaspider/media/drm/DRMChecker.java`
- focused tests:
  - `javaspider/src/test/java/com/javaspider/cli/MediaDownloaderCLITest.java`
  - `javaspider/src/test/java/com/javaspider/media/parser/GenericParserTest.java`

## Verification

Focused verification completed on 2026-04-12:

- Java:
  - `mvn -q "-Dtest=MediaDownloaderCLITest,GenericParserTest" test`
  - result: passed
- Rust:
  - `cargo test video_parser --lib`
  - result: passed
- Go:
  - `go test ./extractors/bilibili ./extractors/tencent ./extractors/youku ./extractors/iqiyi ./media ./cmd/gospider`
  - result: passed
- Python:
  - `python -m pytest pyspider/tests/test_multimedia_downloader.py pyspider/tests/test_video_downloader.py -q`
  - result: `23 passed`

## Notable Implementation Notes

- JavaSpider now uses a generic-parser fallback when a specialized parser does not produce a usable media URL, so supported sites no longer fail just because a platform-specific parser is incomplete.
- RustSpider now recognizes replay-style and mirrored IQIYI / Tencent URL shapes in addition to canonical production URLs.
- PySpider required real parser fixes during this parity pass:
  - IQIYI DASH extraction
  - Tencent `/x/page/...` URL recognition and duration extraction
- GoSpider already had most of the runtime capability in place; this pass strengthened proof by adding extractor-level regression tests.

## Remaining Risks

- Site parsing is still driven primarily by HTML, inline JSON, and manifest patterns rather than stable official APIs.
- These checks are focused regression tests, not continuous live-site end-to-end verification against current production pages.
- Parity here means capability surface and regression coverage are aligned; it does not guarantee identical extraction depth on every real-world page.
