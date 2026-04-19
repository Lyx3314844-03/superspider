# Media Blackbox Report

Summary: 2 passed, 0 failed

| Check | Status |
| --- | --- |
| gospider-iqiyi-download | passed |
| pyspider-generic-hls-download | passed |

## gospider-iqiyi-download

- Status: passed
- Command: `C:\Program Files\Go\bin\go.EXE run ./cmd/gospider media -platform iqiyi -url http://127.0.0.1:25906/v_fixture123.html -download -output C:\Users\ADMINI~1\AppData\Local\Temp\tmpujhx_sbq\gospider`
- Details: Enhanced Anti-Bot module loaded
Multi-platform media downloader loaded
═══════════════════════════════════════════════════════════
                    gospider 媒体下载器                     
═══════════════════════════════════════════════════════════
URL: http://127.0.0.1:25906/v_fixture123.html
输出目录：C:\Users\ADMINI~1\AppData\Local\Temp\tmpujhx_sbq\gospider
下载：true

检测到平台：iqiyi

📺 爱奇艺视频
标题：Fixture IQIYI
时长：8 秒
封面：http://127.0.0.1:25906/cover.jpg
清晰度：1080p, 720p
主 HLS：http://127.0.0.1:25906/master.m3u8

找到 2 个媒体分段
下载完成：1/2
下载完成：2/2
✅ 下载完成：C:\Users\ADMINI~1\AppData\Local\Temp\tmpujhx_sbq\gospider\Fixture IQIYI.ts
blackbox artifact validated

## pyspider-generic-hls-download

- Status: passed
- Command: `C:\Python314\python.exe -m pyspider download http://127.0.0.1:25906/generic-media.html --output-dir C:\Users\ADMINI~1\AppData\Local\Temp\tmpujhx_sbq\pyspider`
- Details: 2026-04-10 11:32:41,651 - pyspider.cli.video_downloader - INFO - 解析视频：http://127.0.0.1:25906/generic-media.html
2026-04-10 11:32:41,654 - pyspider.cli.video_downloader - INFO - ✓ 解析成功：Fixture Generic Media
2026-04-10 11:32:41,654 - pyspider.cli.video_downloader - INFO -   平台：unknown
2026-04-10 11:32:41,654 - pyspider.cli.video_downloader - INFO - 使用 HLS 下载
2026-04-10 11:32:41,655 - pyspider.media.hls_downloader - INFO - 开始下载：http://127.0.0.1:25906/master.m3u8
2026-04-10 11:32:41,701 - pyspider.media.hls_downloader - INFO - 解析到 2 个分片，总时长 8.0秒
2026-04-10 11:32:41,707 - pyspider.media.hls_downloader - INFO - 分片下载完成：成功 2, 失败 0, 成功率 100.0%
2026-04-10 11:32:41,707 - pyspider.media.hls_downloader - INFO - 合并 2 个分片...
2026-04-10 11:32:41,708 - pyspider.media.hls_downloader - INFO - 合并完成：C:\Users\ADMINI~1\AppData\Local\Temp\tmpujhx_sbq\pyspider\e840bb44aa7147d9.ts
2026-04-10 11:32:41,709 - pyspider.media.hls_downloader - INFO - 下载完成：C:\Users\ADMINI~1\AppData\Local\Temp\tmpujhx_sbq\pyspider\e840bb44aa7147d9.ts
2026-04-10 11:32:41,709 - pyspider.cli.video_downloader - INFO - ✓ 下载完成：C:\Users\ADMINI~1\AppData\Local\Temp\tmpujhx_sbq\pyspider\e840bb44aa7147d9.ts
blackbox artifact validated
