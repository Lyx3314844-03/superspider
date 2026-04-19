# Local Integrations Report

Summary: 7 passed, 0 failed

| Check | Status |
| --- | --- |
| gospider-media-cli | passed |
| javaspider-ai-selector | passed |
| rustspider-captcha-local-e2e | passed |
| rustspider-captcha-local-e2e-recaptcha | passed |
| pyspider-multimedia-defaults | passed |
| pyspider-checkpoint-and-converters | passed |
| media-blackbox-local | passed |

## gospider-media-cli

- Status: passed
- Command: `C:\Program Files\Go\bin\go.EXE test ./cmd/gospider ./extractors/iqiyi`
- Details: ok  	gospider/cmd/gospider	0.094s
ok  	gospider/extractors/iqiyi	(cached)

## javaspider-ai-selector

- Status: passed
- Command: `C:\ProgramData\chocolatey\lib\maven\apache-maven-3.9.14\bin\mvn.CMD -q -Dtest=AIExtractorContractTest,HtmlSelectorContractTest test`
- Details: command completed

## rustspider-captcha-local-e2e

- Status: passed
- Command: `C:\Program Files\Rust stable MSVC 1.94\bin\cargo.EXE test test_solve_image_with_2captcha_local_server --lib`
- Details: running 1 test
test antibot::enhanced::tests::test_solve_image_with_2captcha_local_server ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 51 filtered out; finished in 0.03s
Blocking waiting for file lock on package cache
    Blocking waiting for file lock on package cache
    Blocking waiting for file lock on package cache
    Finished `test` profile [optimized + debuginfo] target(s) in 0.70s
     Running unittests src\lib.rs (target\debug\deps\rustspider-cbee3d20ee19d319.exe)

## rustspider-captcha-local-e2e-recaptcha

- Status: passed
- Command: `C:\Program Files\Rust stable MSVC 1.94\bin\cargo.EXE test test_solve_recaptcha_with_anticaptcha_local_server --lib`
- Details: running 1 test
test antibot::enhanced::tests::test_solve_recaptcha_with_anticaptcha_local_server ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 51 filtered out; finished in 0.04s
Blocking waiting for file lock on package cache
    Finished `test` profile [optimized + debuginfo] target(s) in 0.55s
     Running unittests src\lib.rs (target\debug\deps\rustspider-cbee3d20ee19d319.exe)

## pyspider-multimedia-defaults

- Status: passed
- Command: `C:\Python314\Scripts\pytest.EXE -q pyspider/tests/test_multimedia_downloader.py`
- Details: ..                                                                       [100%]
2 passed in 0.26s

## pyspider-checkpoint-and-converters

- Status: passed
- Command: `C:\Python314\Scripts\pytest.EXE -q pyspider/tests/test_checkpoint.py pyspider/tests/test_curlconverter.py pyspider/tests/test_dependencies.py`
- Details: ..................................                                       [100%]
34 passed in 1.81s

## media-blackbox-local

- Status: passed
- Command: `C:\Python314\python.exe verify_media_blackbox.py --json`
- Details: {
  "command": "verify-media-blackbox",
  "summary": "passed",
  "summary_text": "2 passed, 0 failed",
  "exit_code": 0,
  "checks": [
    {
      "name": "gospider-iqiyi-download",
      "command": [
        "C:\\Program Files\\Go\\bin\\go.EXE",
        "run",
        "./cmd/gospider",
        "media",
        "-platform",
        "iqiyi",
        "-url",
        "http://127.0.0.1:51349/v_fixture123.html",
        "-download",
        "-output",
        "C:\\Users\\ADMINI~1\\AppData\\Local\\Temp\\tmprixxgfmm\\gospider"
      ],
      "exit_code": 0,
      "status": "passed",
      "details": "Enhanced Anti-Bot module loaded\nMulti-platform media downloader loaded\n═══════════════════════════════════════════════════════════\n                    gospider 媒体下载器                     \n═══════════════════════════════════════════════════════════\nURL: http://127.0.0.1:51349/v_fixture123.html\n输出目录：C:\\Users\\ADMINI~1\\AppData\\Local\\Temp\\tmprixxgfmm\\gospider\n下载：true\n\n检测到平台：iqiyi\n\n📺 爱奇艺视频\n标题：Fixture IQIYI\n时长：8 秒\n封面：http://127.0.0.1:51349/cover.jpg\n清晰度：1080p, 720p\n主 HLS：http://127.0.0.1:51349/master.m3u8\n\n找到 2 个媒体分段\n下载完成：1/2\n下载完成：2/2\n✅ 下载完成：C:\\Users\\ADMINI~1\\AppData\\Local\\Temp\\tmprixxgfmm\\gospider\\Fixture IQIYI.ts\nblackbox artifact validated"
    },
    {
      "name": "pyspider-generic-hls-download",
      "command": [
        "C:\\Python314\\python.exe",
        "-m",
        "pyspider",
        "download",
        "http://127.0.0.1:51349/generic-media.html",
        "--output-dir",
        "C:\\Users\\ADMINI~1\\AppData\\Local\\Temp\\tmprixxgfmm\\pyspider"
      ],
      "exit_code": 0,
      "status": "passed",
      "details": "2026-04-10 11:49:02,089 - pyspider.cli.video_downloader - INFO - 解析视频：http://127.0.0.1:51349/generic-media.html\n2026-04-10 11:49:02,094 - pyspider.cli.video_downloader - INFO - ✓ 解析成功：Fixture Generic Media\n2026-04-10 11:49:02,095 - pyspider.cli.video_downloader - INFO -   平台：unknown\n2026-04-10 11:49:02,095 - pyspider.cli.video_downloader - INFO - 使用 HLS 下载\n2026-04-10 11:49:02,095 - pyspider.media.hls_downloader - INFO - 开始下载：http://127.0.0.1:51349/master.m3u8\n2026-04-10 11:49:02,139 - pyspider.media.hls_downloader - INFO - 解析到 2 个分片，总时长 8.0秒\n2026-04-10 11:49:02,144 - pyspider.media.hls_downloader - INFO - 分片下载完成：成功 2, 失败 0, 成功率 100.0%\n2026-04-10 11:49:02,144 - pyspider.media.hls_downloader - INFO - 合并 2 个分片...\n2026-04-10 11:49:02,145 - pyspider.media.hls_downloader - INFO - 合并完成：C:\\Users\\ADMINI~1\\AppData\\Local\\Temp\\tmprixxgfmm\\pyspider\\61cbfd9cad851da8.ts\n2026-04-10 11:49:02,146 - pyspider.media.hls_downloader - INFO - 下载完成：C:\\Users\\ADMINI~1\\AppData\\Local\\Temp\\tmprixxgfmm\\pyspider\\61cbfd9cad851da8.ts\n2026-04-10 11:49:02,146 - pyspider.cli.video_downloader - INFO - ✓ 下载完成：C:\\Users\\ADMINI~1\\AppData\\Local\\Temp\\tmprixxgfmm\\pyspider\\61cbfd9cad851da8.ts\nblackbox artifact validated"
    }
  ]
}
