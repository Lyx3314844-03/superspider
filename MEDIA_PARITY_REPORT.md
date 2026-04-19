# Media Parity Report

Updated: 2026-04-19

---

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
- Douyin (added in latest update)

---

## Final Matrix

| Capability | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| HLS (`m3u8`) | ✅ | ✅ | ✅ | ✅ |
| DASH (`mpd`) | ✅ | ✅ | ✅ | ✅ |
| FFmpeg merge / convert | ✅ | ✅ | ✅ | ✅ |
| DRM detection | ✅ | ✅ | ✅ | ✅ |
| YouTube | ✅ | ✅ | ✅ | ✅ |
| Bilibili | ✅ | ✅ | ✅ | ✅ |
| IQIYI | ✅ | ✅ | ✅ | ✅ (generic fallback) |
| Tencent Video | ✅ | ✅ | ✅ | ✅ (generic fallback) |
| Youku | ✅ | ✅ | ✅ | ✅ (generic fallback) |
| Douyin | ✅ | ✅ (dedicated extractor) | ✅ | ✅ (generic fallback) |

---

## Code Evidence

### PySpider

- Parser coverage: `pyspider/media/video_parser.py`
- Media CLI and download path: `pyspider/cli/video_downloader.py`
- Focused tests: `pyspider/tests/test_multimedia_downloader.py`, `pyspider/tests/test_video_downloader.py`

### GoSpider

- Media command surface: `gospider/cmd/gospider/media_cmd.go`
- Generic media path: `gospider/media/multiple_platform.go`
- Platform extractors:
  - `gospider/extractors/bilibili/bilibili.go`
  - `gospider/extractors/iqiyi/iqiyi.go`
  - `gospider/extractors/tencent/tencent.go`
  - `gospider/extractors/youku/youku.go`
  - `gospider/extractors/douyin/douyin.go`
- Focused tests:
  - `gospider/cmd/gospider/media_cmd_test.go`
  - `gospider/media/multiple_platform_test.go`
  - `gospider/extractors/bilibili/bilibili_test.go`
  - `gospider/extractors/iqiyi/iqiyi_test.go`
  - `gospider/extractors/tencent/tencent_test.go`
  - `gospider/extractors/youku/youku_test.go`
  - `gospider/extractors/douyin/douyin_test.go`

### RustSpider

- Media parser and CLI: `rustspider/src/media/video_parser.rs`, `rustspider/src/cli.rs`
- DRM detection: `rustspider/src/video/drm_detector.rs`
- Focused tests: `rustspider/src/media/video_parser.rs` test module

### JavaSpider

- Media CLI and fallback chain: `javaspider/src/main/java/com/javaspider/cli/MediaDownloaderCLI.java`
- Generic media parser: `javaspider/src/main/java/com/javaspider/media/parser/GenericParser.java`
- Platform parsers:
  - `javaspider/src/main/java/com/javaspider/media/parser/BilibiliParser.java`
  - `javaspider/src/main/java/com/javaspider/media/parser/IqiyiParser.java`
  - `javaspider/src/main/java/com/javaspider/media/parser/TencentParser.java`
  - `javaspider/src/main/java/com/javaspider/media/parser/DouyinParser.java`
- DRM detection: `javaspider/src/main/java/com/javaspider/media/drm/DRMChecker.java`
- Focused tests:
  - `javaspider/src/test/java/com/javaspider/cli/MediaDownloaderCLITest.java`
  - `javaspider/src/test/java/com/javaspider/media/parser/GenericParserTest.java`

---

## Verification

| Runtime | Command | Result |
| --- | --- | --- |
| Java | `mvn -q "-Dtest=MediaDownloaderCLITest,GenericParserTest" test` | passed |
| Rust | `cargo test video_parser --lib` | passed |
| Go | `go test ./extractors/bilibili ./extractors/tencent ./extractors/youku ./extractors/iqiyi ./extractors/douyin ./media ./cmd/gospider` | passed |
| Python | `python -m pytest pyspider/tests/test_multimedia_downloader.py pyspider/tests/test_video_downloader.py -q` | 23 passed |

---

## Implementation Notes

- **JavaSpider** uses a generic-parser fallback when a specialized parser does not produce a usable media URL. Supported sites no longer fail just because a platform-specific parser is incomplete.
- **RustSpider** recognizes replay-style and mirrored IQIYI / Tencent URL shapes in addition to canonical production URLs. CLI `parse` output now includes `DASH / Download / Cover` fields.
- **PySpider** required real parser fixes during the parity pass: IQIYI DASH extraction and Tencent `/x/page/...` URL recognition and duration extraction.
- **GoSpider** already had most of the runtime capability in place. The parity pass strengthened proof by adding extractor-level regression tests and a dedicated Douyin extractor.

---

## Remaining Risks

- Site parsing is driven primarily by HTML, inline JSON, and manifest patterns rather than stable official APIs.
- These checks are focused regression tests, not continuous live-site end-to-end verification against current production pages.
- Parity here means capability surface and regression coverage are aligned; it does not guarantee identical extraction depth on every real-world page.
