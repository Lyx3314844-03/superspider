# Framework Completion Report

Summary: 4 frameworks passed, 0 frameworks failed

| Framework | Summary | Evidence | Remaining Focus |
| --- | --- | --- | --- |
| gospider | passed | distributed=4 passed, 0 failed; media_cli=youtube/youku/tencent/iqiyi/bilibili connected; extractor_tests=bilibili/tencent/youku/iqiyi passed; media_blackbox=2 passed, 0 failed; storage=csv dataset export implemented; session=proxy-aware HTTP client implemented; official curl/drm surfaces added | deepen site-specific media parsing and download hit-rate |
| javaspider | passed | captcha_recovery=5 passed, 0 failed; selector_jsonpath=nested field/index/wildcard support implemented; selector_ai=real AI + heuristic fallback implemented; structured_ai=schema-driven structured extraction implemented; media_cli_fallback=generic media fallback enabled; generic media parser now covers youtube/youku/iqiyi/tencent/bilibili metadata and media urls; focused_media_tests passed | expand schema enforcement and higher-level extraction contracts |
| pyspider | passed | concurrency=3 passed, 0 failed; checkpoint=json + sqlite checkpoint backends implemented; curlconverter=curl to aiohttp conversion implemented; multimedia=platform-aware parsing implemented; iqiyi_dash+tencent_page_url parser gaps fixed; official web/drm surfaces added; focused_media_tests=23 passed | keep deepening platform-specific multimedia download hit-rate |
| rustspider | passed | browser=4 passed, 0 failed; distributed=2 passed, 0 failed; cookie_persistence=json persistence implemented; captcha=2captcha / anti-captcha request flow implemented with local end-to-end tests; official audit/curl surfaces added; media parser now covers youku/iqiyi/tencent/bilibili/douyin with focused video_parser tests passing | perform real third-party captcha service integration validation |

## Raw Sections

### gospider_distributed

- Summary: 4 passed, 0 failed
- lease-lifecycle: passed - ok  	gospider/distributed	(cached)
- lease-heartbeat: passed - ok  	gospider/distributed	(cached)
- dead-letter-budget: passed - ok  	gospider/distributed	(cached)
- synthetic-soak: passed - ok  	gospider/distributed	(cached)

### javaspider_captcha

- Summary: 5 passed, 0 failed
- compile-dependencies: passed - compile + dependency copy completed
- workflow-tests: passed - 2026-04-10 11:58:30.393 [main] INFO  c.j.antibot.UserAgentRotator - UserAgentRotator 初始化完成，共 18 个 User-Agent
- workflow-replay: passed - {
  "job_name" : "java-captcha-recovery",
  "state" : "succeeded",
  "target_url" : "https://target.example/challenge",
  "extract" : {
    "title" : "Recovered Dashboard"
  },
  "artifacts" : [ "artifacts/workflow/java-captcha-recovery.txt" ],
  "actions" : [ "goto:https://target.example/challenge", "type:#captcha=1234", "click:#continue", "shot:artifacts/workflow/java-captcha-recovery.txt" ],
  "audit_events" : [ {
    "timestamp" : "2026-04-10T03:58:31.709183700Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "job.created",
    "payload" : {
      "run_id" : "a9452cab-659d-4562-8a68-c20f38406447",
      "step_count" : 5
    },
    "step_id" : "job"
  }, {
    "timestamp" : "2026-04-10T03:58:31.710180200Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "step.started",
    "payload" : {
      "type" : "GOTO"
    },
    "step_id" : "goto"
  }, {
    "timestamp" : "2026-04-10T03:58:31.711202500Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "proxy.health",
    "payload" : {
      "status" : "healthy"
    },
    "step_id" : "goto"
  }, {
    "timestamp" : "2026-04-10T03:58:31.711202500Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "challenge.detected",
    "payload" : {
      "url" : "https://target.example/challenge"
    },
    "step_id" : "goto"
  }, {
    "timestamp" : "2026-04-10T03:58:31.711202500Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "captcha.detected",
    "payload" : {
      "url" : "https://target.example/challenge"
    },
    "step_id" : "goto"
  }, {
    "timestamp" : "2026-04-10T03:58:31.711202500Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "captcha.solved",
    "payload" : {
      "solver" : "mock",
      "continued" : true,
      "solution_length" : 4
    },
    "step_id" : "goto"
  }, {
    "timestamp" : "2026-04-10T03:58:31.711202500Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "step.succeeded",
    "payload" : {
      "type" : "GOTO"
    },
    "step_id" : "goto"
  }, {
    "timestamp" : "2026-04-10T03:58:31.711202500Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "step.started",
    "payload" : {
      "type" : "TYPE"
    },
    "step_id" : "type-captcha"
  }, {
    "timestamp" : "2026-04-10T03:58:31.834826600Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "proxy.health",
    "payload" : {
      "status" : "healthy"
    },
    "step_id" : "type-captcha"
  }, {
    "timestamp" : "2026-04-10T03:58:31.834826600Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "challenge.detected",
    "payload" : {
      "url" : "https://target.example/challenge"
    },
    "step_id" : "type-captcha"
  }, {
    "timestamp" : "2026-04-10T03:58:31.834826600Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "captcha.detected",
    "payload" : {
      "url" : "https://target.example/challenge"
    },
    "step_id" : "type-captcha"
  }, {
    "timestamp" : "2026-04-10T03:58:31.834826600Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "captcha.solved",
    "payload" : {
      "solver" : "mock",
      "continued" : true,
      "solution_length" : 4
    },
    "step_id" : "type-captcha"
  }, {
    "timestamp" : "2026-04-10T03:58:31.834826600Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "step.succeeded",
    "payload" : {
      "type" : "TYPE"
    },
    "step_id" : "type-captcha"
  }, {
    "timestamp" : "2026-04-10T03:58:31.834826600Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "step.started",
    "payload" : {
      "type" : "CLICK"
    },
    "step_id" : "click-continue"
  }, {
    "timestamp" : "2026-04-10T03:58:31.836826700Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "proxy.health",
    "payload" : {
      "status" : "healthy"
    },
    "step_id" : "click-continue"
  }, {
    "timestamp" : "2026-04-10T03:58:31.836826700Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "challenge.detected",
    "payload" : {
      "url" : "https://target.example/challenge"
    },
    "step_id" : "click-continue"
  }, {
    "timestamp" : "2026-04-10T03:58:31.836826700Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "captcha.detected",
    "payload" : {
      "url" : "https://target.example/challenge"
    },
    "step_id" : "click-continue"
  }, {
    "timestamp" : "2026-04-10T03:58:31.836826700Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "captcha.solved",
    "payload" : {
      "solver" : "mock",
      "continued" : true,
      "solution_length" : 4
    },
    "step_id" : "click-continue"
  }, {
    "timestamp" : "2026-04-10T03:58:31.836826700Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "step.succeeded",
    "payload" : {
      "type" : "CLICK"
    },
    "step_id" : "click-continue"
  }, {
    "timestamp" : "2026-04-10T03:58:31.836826700Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "step.started",
    "payload" : {
      "type" : "EXTRACT"
    },
    "step_id" : "extract-title"
  }, {
    "timestamp" : "2026-04-10T03:58:31.836826700Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "proxy.health",
    "payload" : {
      "status" : "healthy"
    },
    "step_id" : "extract-title"
  }, {
    "timestamp" : "2026-04-10T03:58:31.836826700Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "challenge.detected",
    "payload" : {
      "url" : "https://target.example/challenge"
    },
    "step_id" : "extract-title"
  }, {
    "timestamp" : "2026-04-10T03:58:31.836826700Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "captcha.detected",
    "payload" : {
      "url" : "https://target.example/challenge"
    },
    "step_id" : "extract-title"
  }, {
    "timestamp" : "2026-04-10T03:58:31.836826700Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "captcha.solved",
    "payload" : {
      "solver" : "mock",
      "continued" : true,
      "solution_length" : 4
    },
    "step_id" : "extract-title"
  }, {
    "timestamp" : "2026-04-10T03:58:31.836826700Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "step.succeeded",
    "payload" : {
      "type" : "EXTRACT"
    },
    "step_id" : "extract-title"
  }, {
    "timestamp" : "2026-04-10T03:58:31.836826700Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "step.started",
    "payload" : {
      "type" : "SCREENSHOT"
    },
    "step_id" : "capture"
  }, {
    "timestamp" : "2026-04-10T03:58:31.838827500Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "proxy.health",
    "payload" : {
      "status" : "healthy"
    },
    "step_id" : "capture"
  }, {
    "timestamp" : "2026-04-10T03:58:31.838827500Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "challenge.detected",
    "payload" : {
      "url" : "https://target.example/challenge"
    },
    "step_id" : "capture"
  }, {
    "timestamp" : "2026-04-10T03:58:31.838827500Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "captcha.detected",
    "payload" : {
      "url" : "https://target.example/challenge"
    },
    "step_id" : "capture"
  }, {
    "timestamp" : "2026-04-10T03:58:31.838827500Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "captcha.solved",
    "payload" : {
      "solver" : "mock",
      "continued" : true,
      "solution_length" : 4
    },
    "step_id" : "capture"
  }, {
    "timestamp" : "2026-04-10T03:58:31.838827500Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "step.succeeded",
    "payload" : {
      "type" : "SCREENSHOT"
    },
    "step_id" : "capture"
  }, {
    "timestamp" : "2026-04-10T03:58:31.839829Z",
    "job_id" : "workflow-replay-1775793511650",
    "type" : "job.completed",
    "payload" : {
      "artifacts" : 1,
      "fields" : [ "title" ],
      "run_id" : "a9452cab-659d-4562-8a68-c20f38406447"
    },
    "step_id" : "job"
  } ],
  "output" : {
    "format" : "json",
    "path" : "artifacts/workflow/java-captcha-recovery.json"
  },
  "error" : "",
  "metrics" : {
    "audit_event_count" : 32,
    "latency_ms" : 314
  }
}
- captcha-closed-loop: passed - audit trail includes detect/solve/complete and replay actions resume the flow
- replay-artifact: passed - workflow replay persisted JSON output and artifact content

### javaspider_ai_live

- Summary: JAVASPIDER_LIVE_AI_SMOKE is not enabled; OPENAI_API_KEY/AI_API_KEY is missing
- live-ai-smoke: skipped - JAVASPIDER_LIVE_AI_SMOKE is not enabled; OPENAI_API_KEY/AI_API_KEY is missing

### local_integrations

- Summary: 7 passed, 0 failed
- gospider-media-cli: passed - ok  	gospider/cmd/gospider	0.139s
ok  	gospider/extractors/iqiyi	(cached)
- javaspider-ai-selector: passed - command completed
- rustspider-captcha-local-e2e: passed - running 1 test
test antibot::enhanced::tests::test_solve_image_with_2captcha_local_server ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 51 filtered out; finished in 0.03s
Blocking waiting for file lock on package cache
    Blocking waiting for file lock on package cache
    Blocking waiting for file lock on package cache
    Blocking waiting for file lock on artifact directory
    Finished `test` profile [optimized + debuginfo] target(s) in 0.91s
     Running unittests src\lib.rs (target\debug\deps\rustspider-cbee3d20ee19d319.exe)
- rustspider-captcha-local-e2e-recaptcha: passed - running 1 test
test antibot::enhanced::tests::test_solve_recaptcha_with_anticaptcha_local_server ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 51 filtered out; finished in 0.04s
Blocking waiting for file lock on package cache
    Finished `test` profile [optimized + debuginfo] target(s) in 0.77s
     Running unittests src\lib.rs (target\debug\deps\rustspider-cbee3d20ee19d319.exe)
- pyspider-multimedia-defaults: passed - ..                                                                       [100%]
2 passed in 0.34s
- pyspider-checkpoint-and-converters: passed - ..................................                                       [100%]
34 passed in 1.87s
- media-blackbox-local: passed - {
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
        "http://127.0.0.1:44818/v_fixture123.html",
        "-download",
        "-output",
        "C:\\Users\\ADMINI~1\\AppData\\Local\\Temp\\tmpxehbv0el\\gospider"
      ],
      "exit_code": 0,
      "status": "passed",
      "details": "Enhanced Anti-Bot module loaded\nMulti-platform media downloader loaded\n═══════════════════════════════════════════════════════════\n                    gospider 媒体下载器                     \n═══════════════════════════════════════════════════════════\nURL: http://127.0.0.1:44818/v_fixture123.html\n输出目录：C:\\Users\\ADMINI~1\\AppData\\Local\\Temp\\tmpxehbv0el\\gospider\n下载：true\n\n检测到平台：iqiyi\n\n📺 爱奇艺视频\n标题：Fixture IQIYI\n时长：8 秒\n封面：http://127.0.0.1:44818/cover.jpg\n清晰度：1080p, 720p\n主 HLS：http://127.0.0.1:44818/master.m3u8\n\n找到 2 个媒体分段\n下载完成：2/2\n下载完成：1/2\n✅ 下载完成：C:\\Users\\ADMINI~1\\AppData\\Local\\Temp\\tmpxehbv0el\\gospider\\Fixture IQIYI.ts\nblackbox artifact validated"
    },
    {
      "name": "pyspider-generic-hls-download",
      "command": [
        "C:\\Python314\\python.exe",
        "-m",
        "pyspider",
        "download",
        "http://127.0.0.1:44818/generic-media.html",
        "--output-dir",
        "C:\\Users\\ADMINI~1\\AppData\\Local\\Temp\\tmpxehbv0el\\pyspider"
      ],
      "exit_code": 0,
      "status": "passed",
      "details": "2026-04-10 11:58:51,222 - pyspider.cli.video_downloader - INFO - 解析视频：http://127.0.0.1:44818/generic-media.html\n2026-04-10 11:58:51,244 - pyspider.cli.video_downloader - INFO - ✓ 解析成功：Fixture Generic Media\n2026-04-10 11:58:51,244 - pyspider.cli.video_downloader - INFO -   平台：unknown\n2026-04-10 11:58:51,244 - pyspider.cli.video_downloader - INFO - 使用 HLS 下载\n2026-04-10 11:58:51,245 - pyspider.media.hls_downloader - INFO - 开始下载：http://127.0.0.1:44818/master.m3u8\n2026-04-10 11:58:51,298 - pyspider.media.hls_downloader - INFO - 解析到 2 个分片，总时长 8.0秒\n2026-04-10 11:58:51,322 - pyspider.media.hls_downloader - INFO - 分片下载完成：成功 2, 失败 0, 成功率 100.0%\n2026-04-10 11:58:51,323 - pyspider.media.hls_downloader - INFO - 合并 2 个分片...\n2026-04-10 11:58:51,324 - pyspider.media.hls_downloader - INFO - 合并完成：C:\\Users\\ADMINI~1\\AppData\\Local\\Temp\\tmpxehbv0el\\pyspider\\3a2589e1d82b3c67.ts\n2026-04-10 11:58:51,325 - pyspider.media.hls_downloader - INFO - 下载完成：C:\\Users\\ADMINI~1\\AppData\\Local\\Temp\\tmpxehbv0el\\pyspider\\3a2589e1d82b3c67.ts\n2026-04-10 11:58:51,325 - pyspider.cli.video_downloader - INFO - ✓ 下载完成：C:\\Users\\ADMINI~1\\AppData\\Local\\Temp\\tmpxehbv0el\\pyspider\\3a2589e1d82b3c67.ts\nblackbox artifact validated"
    }
  ]
}

### media_blackbox

- Summary: 2 passed, 0 failed
- gospider-iqiyi-download: passed - Enhanced Anti-Bot module loaded
Multi-platform media downloader loaded
═══════════════════════════════════════════════════════════
                    gospider 媒体下载器                     
═══════════════════════════════════════════════════════════
URL: http://127.0.0.1:44838/v_fixture123.html
输出目录：C:\Users\ADMINI~1\AppData\Local\Temp\tmph5f0ve7g\gospider
下载：true

检测到平台：iqiyi

📺 爱奇艺视频
标题：Fixture IQIYI
时长：8 秒
封面：http://127.0.0.1:44838/cover.jpg
清晰度：1080p, 720p
主 HLS：http://127.0.0.1:44838/master.m3u8

找到 2 个媒体分段
下载完成：1/2
下载完成：2/2
✅ 下载完成：C:\Users\ADMINI~1\AppData\Local\Temp\tmph5f0ve7g\gospider\Fixture IQIYI.ts
blackbox artifact validated
- pyspider-generic-hls-download: passed - 2026-04-10 11:58:52,944 - pyspider.cli.video_downloader - INFO - 解析视频：http://127.0.0.1:44838/generic-media.html
2026-04-10 11:58:52,948 - pyspider.cli.video_downloader - INFO - ✓ 解析成功：Fixture Generic Media
2026-04-10 11:58:52,948 - pyspider.cli.video_downloader - INFO -   平台：unknown
2026-04-10 11:58:52,948 - pyspider.cli.video_downloader - INFO - 使用 HLS 下载
2026-04-10 11:58:52,949 - pyspider.media.hls_downloader - INFO - 开始下载：http://127.0.0.1:44838/master.m3u8
2026-04-10 11:58:52,996 - pyspider.media.hls_downloader - INFO - 解析到 2 个分片，总时长 8.0秒
2026-04-10 11:58:53,003 - pyspider.media.hls_downloader - INFO - 分片下载完成：成功 2, 失败 0, 成功率 100.0%
2026-04-10 11:58:53,003 - pyspider.media.hls_downloader - INFO - 合并 2 个分片...
2026-04-10 11:58:53,004 - pyspider.media.hls_downloader - INFO - 合并完成：C:\Users\ADMINI~1\AppData\Local\Temp\tmph5f0ve7g\pyspider\fe6a4a1d2c217024.ts
2026-04-10 11:58:53,005 - pyspider.media.hls_downloader - INFO - 下载完成：C:\Users\ADMINI~1\AppData\Local\Temp\tmph5f0ve7g\pyspider\fe6a4a1d2c217024.ts
2026-04-10 11:58:53,006 - pyspider.cli.video_downloader - INFO - ✓ 下载完成：C:\Users\ADMINI~1\AppData\Local\Temp\tmph5f0ve7g\pyspider\fe6a4a1d2c217024.ts
blackbox artifact validated

### pyspider_concurrency

- Summary: 3 passed, 0 failed
- bounded-concurrency: passed - peak=4 max=4 completed=12
- stream-runtime: passed - streamed=6 completed=6 failed=0
- synthetic-soak: passed - rounds=3 results=24 peak=4

### rustspider_browser

- Summary: 4 passed, 0 failed
- browser-config: passed - Blocking waiting for file lock on package cache
    Blocking waiting for file lock on package cache
    Blocking waiting for file lock on package cache
    Blocking waiting for file lock on artifact directory
    Finished `test` profile [optimized + debuginfo] target(s) in 15.16s
     Running tests\capability_scorecard.rs (target\debug\deps\capability_scorecard-392a6d50ee17244a.exe)
- browser-example-assets: passed - Blocking waiting for file lock on package cache
    Blocking waiting for file lock on artifact directory
    Finished `test` profile [optimized + debuginfo] target(s) in 0.64s
     Running tests\browser_examples_scorecard.rs (target\debug\deps\browser_examples_scorecard-cb40112d6f803be4.exe)
- browser-example-compile: passed - Blocking waiting for file lock on package cache
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.56s
- browser-preflight: passed - 3 passed, 0 failed

### rustspider_captcha_live

- Summary: RUSTSPIDER_LIVE_CAPTCHA_SMOKE is not enabled; no captcha provider API key is configured
- live-captcha-smoke: skipped - RUSTSPIDER_LIVE_CAPTCHA_SMOKE is not enabled; no captcha provider API key is configured

### rustspider_distributed

- Summary: 2 passed, 0 failed
- distributed-feature-gate: passed - Blocking waiting for file lock on package cache
    Blocking waiting for file lock on artifact directory
    Finished `test` profile [optimized + debuginfo] target(s) in 17.99s
warning: the following packages contain code that will be rejected by a future version of Rust: redis v0.23.3
note: to see what the problems were, use the option `--future-incompat-report`, or run `cargo report future-incompatibilities --id 1`
     Running tests\distributed_scorecard.rs (target\debug\deps\distributed_scorecard-d8917d5bb5469341.exe)
- distributed-behavior-scorecard: passed - Blocking waiting for file lock on artifact directory
    Finished `test` profile [optimized + debuginfo] target(s) in 6.48s
     Running tests\distributed_behavior_scorecard.rs (target\debug\deps\distributed_behavior_scorecard-f94c45897925c62f.exe)
