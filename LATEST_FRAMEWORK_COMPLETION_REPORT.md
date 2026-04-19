# 四框架最新完成度报告

更新日期：2026-04-13

## 总览

四个目标框架 `gospider`、`javaspider`、`rustspider`、`pyspider` 当前都已经从“存在明显未完成能力 / 编译或占位实现”推进到“核心链路可验证”的状态。

本轮及前序连续修复后：

- `gospider`：分布式能力验证通过；媒体 CLI 与 extractor 链路已覆盖 YouTube / Bilibili / 优酷 / 腾讯 / 爱奇艺
- `javaspider`：编译恢复；验证码闭环验证通过；媒体解析已补齐 Bilibili / 优酷 / 腾讯 / 爱奇艺，并在专用解析失败时回退到通用媒体解析链；Maven feature profiles 已落地
- `rustspider`：浏览器与分布式验证通过；媒体解析已覆盖 YouTube / Bilibili / 优酷 / 腾讯 / 爱奇艺，并补齐 DASH / Download / Cover 输出；RabbitMQ / Kafka 队列桥接已落地
- `pyspider`：并发验证通过；媒体解析已补齐 Bilibili / 优酷 / 腾讯 / 爱奇艺 / YouTube，`IQIYI` 的 DASH 与 `Tencent` 的 `/x/page/...` URL 识别已落地

## 2026-04-13 追加补齐

在前一轮媒体能力对齐之后，又补齐了以下真实缺口：

- `gospider`
  - AI 客户端补充 `Anthropic / Claude` 兼容支持
- `javaspider`
  - AI 客户端补充 `Anthropic / Claude` 兼容支持
  - Maven `lite / ai / browser / distributed / full` profiles 落地
  - `capabilities` 输出补充 `feature_gates`
- `rustspider`
  - AI 客户端补充 `Anthropic / Claude` 兼容支持
  - `captcha::solver` 正式接入 crate，并补齐 `reCAPTCHA / hCaptcha`
  - 多队列后端补充 `RabbitMQ / Kafka` bridge backend
  - `capabilities` 输出补充 `queue_backends`

## 2026-04-13 第二批均衡项

继续补齐了下列横向能力差距：

- `gospider`
  - 原生 Selenium / WebDriver 客户端
  - SSRF guard
  - 节点发现（env / file / dns-srv）
  - 统一 async runtime surface
- `javaspider`
  - `AsyncSpiderRuntime`
  - AI few-shot helper
  - `selector-studio` 智能 XPath 建议
- `rustspider`
  - Selenium native face（基于 fantoccini facade）
  - AI few-shot helper
  - `selector-studio` 智能 XPath 建议

## 2026-04-13 第三批能力收口

继续补齐了下列架构级与工程级差距：

- `gospider`
  - 专用 NLP 模块：情感分析 / 摘要生成 / 实体抽取
  - 审计追踪模块：内存 / 文件 / 复合审计轨
  - 多数据库后端：
    - process adapter：`Postgres / MySQL / MongoDB`
    - driver adapter：`Postgres / MySQL`
  - dataset 输出可镜像写入配置好的数据库后端
  - 第 6 视频平台：新增独立 `Douyin` extractor 并接入媒体 CLI
- `javaspider`
  - 专用 NLP 模块：情感分析 / 摘要生成 / 实体抽取
  - `distributed.NodeDiscovery` 补齐 `Consul / etcd`
  - 独立 REST API server：`/health`、`/jobs`、`/jobs/{id}`、`/jobs/{id}/result`
  - 队列后端新增 broker-native driver lane：
    - RabbitMQ：`amqp-client`
    - Kafka：`kafka-clients`
- `rustspider`
  - 专用 NLP 模块：情感分析 / 摘要生成 / 实体抽取
  - 审计追踪模块：内存 / 文件 / 复合审计轨
  - 多数据库后端：
    - process adapter：`Postgres / MySQL / MongoDB`
    - driver adapter：`Postgres / MySQL / MongoDB`
  - dataset 输出可镜像写入配置好的数据库后端
  - Playwright 从 shared helper 提升为 native `node + playwright` process surface，并保留旧 helper 回退

## 2026-04-12 媒体能力补齐结论

当前四个运行时在共享媒体能力面上已经对齐：

- HLS (`m3u8`)
- DASH (`mpd`)
- FFmpeg
- DRM 检测
- YouTube
- Bilibili
- 爱奇艺 / 腾讯 / 优酷

这次对齐不是只更新文档，而是同步完成了代码接线、运行时回退链和聚焦回归测试。

## 已补完的关键缺口

### gospider

- 修复 `Dataset.Save(..., "csv")` 之前直接报 `CSV format not implemented` 的问题
- 增加 `session.ProxyURL` 到 `http.Transport.Proxy` 的接线
- 将 `cmd/gospider media` 从占位打印改为真实接线
  - YouTube：信息展示 + 下载入口
  - 优酷：提取信息 + HLS / DASH 下载入口
  - 腾讯：提取信息 + 直链下载入口
  - 爱奇艺：新增提取器并接入 HLS / DASH 下载入口
- 顺手修复 `cmd/gospider/main.go` 中 `pluginID` 错误解引用导致的构建断点
- `AIExtractor` 现在支持 OpenAI 兼容和 Anthropic / Claude messages API
- `browser` 包新增原生 Selenium / WebDriver 客户端
- `downloader` 包新增 SSRF guard
- `distributed` 包新增节点发现能力（env / file / dns-srv）
- `async` 包新增统一异步运行时门面
- 新增专用 `SentimentAnalyzer / ContentSummarizer / EntityExtractor`
- 新增 `audit` 模块
- 新增 `storage.ProcessResultStore / ProcessDatasetStore`
- 新增 `storage.SQLResultStore / SQLDatasetStore`
- `cmd/gospider` 结果与 dataset 输出可镜像写入配置好的数据库后端
- 新增独立 `extractors/douyin`

### javaspider

- 修复 `EnhancedSpider` 编译错误
  - 补充 `LinkedHashSet` 导入
  - 补充 `boolValue(...)`
  - sitemap 发现失败时改为降级继续而不是中断
- 将 `selector.Html.jsonPath()` 从 TODO 占位改成可用实现
  - 支持嵌套字段、数组索引、通配符
- 将 `selector.Html.aiExtract()` 改成双轨模式
  - 配置 AI key 时优先走真实 `AIExtractor`
  - 无 key 或失败时回退启发式提取
- 提升 `com.javaspider.ai.AIExtractor.parseJson()` 结构化解析能力
  - 支持嵌套对象
  - 支持数组
  - 支持从带解释文本的响应中抽取 JSON 片段
- 将媒体 CLI 改为“专用解析优先，通用媒体解析回退”的双层解析链
- `GenericParser` 现在可识别：
  - YouTube
  - 优酷
  - Bilibili
  - 爱奇艺
  - 腾讯视频
  - `.m4s` / `m3u8` / `mpd` / `mp4` 等媒体 URL
- `AIExtractor` 现在支持 OpenAI 与 Anthropic / Claude 环境变量与 endpoint
- `pom.xml` 现在提供 `lite / ai / browser / distributed / full` profiles
- `async.AsyncSpiderRuntime` 提供统一异步门面
- `AIExtractor` 现在支持 few-shot message examples
- `selector-studio` 输出补充 `suggested_xpaths`
- 新增专用 `SentimentAnalyzer / ContentSummarizer / EntityExtractor`
- `distributed.NodeDiscovery` 补齐 `Consul / etcd`
- `api.ApiServer` 提供独立 REST server
- `scheduler.QueueBackends.NativeDriverQueueClient` 提供 RabbitMQ / Kafka broker-native lane
- `converter.CurlToJavaConverter` 现在有 `com.javaspider` 包内正式入口

### rustspider

- 补充 Cookie JSON 持久化读写
- 将 `antibot/enhanced.rs` 中的 2Captcha / Anti-Captcha 从占位返回改为真实异步 API 流程
  - 图片验证码提交
  - reCAPTCHA 提交
  - 结果轮询
- 增加可配置基础地址、轮询间隔、轮询次数
- 增加本地假服务端到端联调测试，不依赖外网
- 补齐 `爱奇艺 / 腾讯` 的 URL 识别与 HTML 媒体提取
- CLI `parse` / `download` 现在会统一处理 `m3u8 / mpd / mp4 / download_url`
- CLI `parse` 输出补充 `DASH / Download / Cover` 字段
- `AIClient` 现在支持 OpenAI 与 Anthropic / Claude
- `captcha::solver` 现在支持 `2captcha / anticaptcha` 的 `reCAPTCHA / hCaptcha`
- 队列后端新增 `RabbitMQ / Kafka` bridge backend
- `browser` 模块现在提供 Selenium native face
- `AIClient` 现在支持 few-shot examples
- `selector-studio` 输出补充 `suggested_xpaths`
- 新增专用 `SentimentAnalyzer / ContentSummarizer / EntityExtractor`
- 新增 `audit` 模块
- 新增 `storage_backends.ProcessResultStore / ProcessDatasetStore`
- 新增 `storage_backends.DriverResultStore / DriverDatasetStore`
- 结果与 dataset 输出可镜像写入配置好的数据库后端
- Playwright 现在优先通过 native `node + playwright` 进程执行，并在失败时回退旧 helper

### pyspider

- 补充 `core/curlconverter.py` 的 `convert_to_aiohttp()`，不再返回 TODO 模板
- 补充 `CheckpointManager` 的 SQLite 存储实现
  - 初始化
  - 保存
  - 加载
  - 删除
  - 列表
- 修复 Windows 下 SQLite 文件句柄未关闭导致临时目录清理失败的问题
- 将 `media/multimedia_downloader.py` 中 `MultiMediaSpider` 的三处抽象壳改为默认通用实现
  - 通用视频提取
  - 通用图片提取
  - 通用音频提取
- 补齐 `IqiyiParser` 的 DASH URL 提取
- 补齐 `TencentParser` 的 `/x/page/...` / `vid=` URL 识别与 `duration` 提取

### gospider 追加验证层

- 新增 `bilibili / tencent / youku` extractor 级单测
- 媒体平台能力不再只依赖上层 `cmd/gospider media` 测试兜底

## 验证证据

以下验证在当前仓库状态下通过：

- `python verify_gospider_distributed_summary.py --json`
  - 结果：`4 passed, 0 failed`
- `go test ./...` in `gospider`
  - 结果：全量通过
- `python verify_javaspider_captcha_summary.py --json`
  - 结果：`5 passed, 0 failed`
- `mvn -q "-Dtest=AIExtractorContractTest,HtmlSelectorContractTest" test` in `javaspider`
  - 结果：通过
- `python verify_rust_browser_summary.py --json`
  - 结果：`4 passed, 0 failed`
- `python verify_rust_distributed_summary.py --json`
  - 结果：`2 passed, 0 failed`
- `cargo test test_solve_image_with_2captcha_local_server --lib`
  - 结果：通过
- `cargo test test_solve_recaptcha_with_anticaptcha_local_server --lib`
  - 结果：通过
- `python verify_pyspider_concurrency_summary.py --json`
  - 结果：`3 passed, 0 failed`
- `pytest -q pyspider/tests/test_checkpoint.py`
  - 结果：`26 passed`
- `pytest -q pyspider/tests/test_curlconverter.py pyspider/tests/test_dependencies.py`
  - 结果：`8 passed`
- `pytest -q pyspider/tests/test_multimedia_downloader.py`
  - 结果：历史基线通过
- `mvn -q "-Dtest=MediaDownloaderCLITest,GenericParserTest" test` in `javaspider`
  - 结果：通过
- `cargo test video_parser --lib` in `rustspider`
  - 结果：通过
- `go test ./extractors/bilibili ./extractors/tencent ./extractors/youku ./extractors/iqiyi ./media ./cmd/gospider` in `gospider`
  - 结果：通过
- `go test ./extractors/douyin ./storage ./research ./cmd/gospider`
  - 结果：通过
- `python -m pytest pyspider/tests/test_multimedia_downloader.py pyspider/tests/test_video_downloader.py -q`
  - 结果：`23 passed`
- `go test ./ai`
  - 结果：通过
- `mvn "-Dtest=AIExtractorContractTest" test` in `javaspider`
  - 结果：通过
- `cargo test --lib ai_client_supports_anthropic_messages_api`
  - 结果：通过
- `cargo test --test queue_backends --quiet`
  - 结果：`3 passed`
- `cargo test --lib solve_recaptcha_with_2captcha`
  - 结果：通过
- `cargo test --lib solve_hcaptcha_with_anticaptcha`
  - 结果：通过
- `mvn -Dtest=PomProfilesContractTest test` in `javaspider`
  - 结果：通过
- `go test ./async ./browser ./downloader ./distributed`
  - 结果：通过
- `mvn "-Dtest=AsyncSpiderRuntimeTest,AIExtractorContractTest,EnhancedSpiderContractTest" test` in `javaspider`
  - 结果：通过
- `cargo test --test browser_bridges --quiet`
  - 结果：`3 passed`
- `cargo test --test storage_backends --test native_playwright_job --quiet`
  - 结果：通过
- `cargo test --lib ai_client_supports_few_shot_messages`
  - 结果：通过
- `cargo test --test node_reverse_cli rust_cli_selector_studio_extracts_values --quiet`
  - 结果：通过
- `mvn -q "-Dtest=QueueBackendsTest,ApiServerTest,SuperSpiderCLITest" test`
  - 结果：通过

## 当前结论

如果按“是否还存在明显未完成能力 / 占位实现 / 编译断裂”来评估，这四个框架在共享媒体能力面上的最明显缺口已经清掉。

当前剩余项更适合归类为“深化能力”，而不是“明显没做完”：

- `gospider`
  - 可继续提高站点级媒体解析深度与真实下载命中率
- `javaspider`
  - `aiExtract()` 已经能走真实 AI 提取，但还可以继续做成 schema 驱动的强约束结构化输出
- `rustspider`
  - 验证码链路已具备本地端到端验证，但还未做真实第三方服务联调
- `pyspider`
  - 平台解析已补齐，但仍可继续做更深的站点特化和真实线上验收

## 建议下一步

如果继续开发，优先级建议如下：

1. `javaspider`：把 AI 提取升级为 schema 驱动结构化输出
2. `rustspider`：做真实外部验证码服务联调与失败恢复策略
3. `gospider` / `pyspider`：继续做平台级媒体解析深化
