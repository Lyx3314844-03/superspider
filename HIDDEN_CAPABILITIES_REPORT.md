# 四个爬虫框架隐藏能力与真实边界报告

更新时间：2026-04-21

这份报告基于以下证据重新整理：

- 四个框架源码实现
- CLI 入口与子命令
- 运行时契约、控制面、工件链路
- scorecard / contract / runtime tests
- 现有 README 与根目录能力文档的对照差异

这里的目标不是再做一份“能力宣传册”，而是把三件事写清楚：

1. 代码里确实存在、但以前没写透的隐藏能力
2. 哪些能力实际上带条件、带 fallback，不能当成无条件可用
3. 哪些实现目前仍然存在缺陷、缩减版实现、仓库残留问题

---

## 总体结论

四个框架的隐藏能力还在继续增多，但同时存在明显的“能力边界”：

- 很多 AI 能力在没有 API Key 时会自动退化为 heuristic fallback
- 多个“browser simulate”能力本质上是 HTTP 获取页面后调用 NodeReverse，不是真实浏览器会话
- 一部分根目录文档把“存在接口/测试夹具/控制面能力”写成了“生产级全量实现”
- 仓库中存在少量残留文件或最小 fallback 实现，会影响对能力成熟度的判断

所以现在更准确的表述应该是：

- 四个框架都具备大规模隐藏能力
- 但不是所有能力都已经达到同样的成熟度
- 文档必须把“已实现”“条件可用”“启发式降级”“仍有缺陷”区分开

---

## 1. JavaSpider

### 1.1 新增确认的隐藏能力

| 能力域 | 隐藏能力 | 代码位置 |
| --- | --- | --- |
| CLI 面 | 统一入口不止 `crawl/browser/ai/media`，还包含 `config`、`preflight`、`jobdir`、`http-cache`、`console`、`audit`、`api`、`web`、`run`、`research`、`workflow`、`job`、`async-job`、`capabilities` | `src/main/java/com/javaspider/cli/SuperSpiderCLI.java` |
| 浏览器工作流 | 支持 `GOTO/CLICK/TYPE/SELECT/HOVER/SCROLL/EVAL/LISTEN_NETWORK/EXTRACT/SCREENSHOT/DOWNLOAD` | `src/main/java/com/javaspider/workflow/FlowStepType.java` |
| 工作流回放 | 工作流结果可回放，并可重建审计与 graph 工件 | `src/main/java/com/javaspider/cli/WorkflowReplayCLI.java` |
| 研究运行时 | 同步研究、异步研究、站点画像、实验追踪 | `src/main/java/com/javaspider/research/*.java` |
| 契约层 | 请求指纹、autoscaled frontier、artifact store、middleware chain、proxy policy、session pool、observability | `src/main/java/com/javaspider/contracts/*.java` |
| 性能层 | 虚拟线程、自适应限速、连接池、熔断器 | `src/main/java/com/javaspider/performance/**/*.java` |
| 分布式发现 | 环境变量、文件、DNS SRV、Consul、Etcd | `src/main/java/com/javaspider/distributed/NodeDiscovery.java` |
| 逆向桥接 | NodeReverse 与 Crawlee bridge 双桥接 | `src/main/java/com/javaspider/nodereverse/*.java`, `src/main/java/com/javaspider/bridge/CrawleeBridgeClient.java` |
| 图谱能力 | 能从 HTML 构图并在 replay/controller 中复用 | `src/main/java/com/javaspider/graph/GraphBuilder.java` |

### 1.2 真实边界与缺陷

| 类型 | 问题 | 证据 |
| --- | --- | --- |
| 实现边界 | `com.javaspider.AntiBot` 只是简单 UA/代理池工具，不应与 `antibot/` 包里的完整反反爬能力混为一谈 | `src/main/java/com/javaspider/AntiBot.java` |
| 失败语义不一致 | `CaptchaSolver` 在多条失败路径直接 `return null`，另一些路径则抛异常，调用方需要自己分辨空值和异常 | `src/main/java/com/javaspider/antibot/CaptchaSolver.java` |
| 浏览器能力宣传偏强 | `UltimateSpiderProcessor.simulateFullBrowser()` 实际是调用 reverse service 生成 TLS/Canvas 指纹并执行一段模拟脚本，不是真实浏览器会话 | `src/main/java/com/javaspider/advanced/UltimateSpiderProcessor.java` |

### 1.3 结论

JavaSpider 是“企业型 Java 运行时”没有问题，但文档应把以下两点写清：

- 真实浏览器自动化主要在 workflow / Selenium context
- ultimate/browser simulate 更接近“reverse-assisted browser emulation”，不是全量浏览器栈

---

## 2. GoSpider

### 2.1 新增确认的隐藏能力

| 能力域 | 隐藏能力 | 代码位置 |
| --- | --- | --- |
| CLI 面 | 除基础 crawl 外，还包含 `job`、`async-job`、`jobdir`、`http-cache`、`console`、`audit`、`selector-studio`、`plugins`、`profile-site`、`research`、`node-reverse`、`anti-bot`、`doctor/preflight` | `cmd/gospider/main.go` |
| feature gate | `ai/browser/distributed/media/workflow/crawlee` 六类开关与 `lite/ai/distributed/full` 档位 | `features/gates.go` |
| 浏览器工件 | HTML、DOM、screenshot、console、network JSON、HAR 都可落盘 | `runtime/browser/runtime.go`, `browser/browser.go` |
| 统一 JobSpec | 支持声明式 `goto/wait/click/type/scroll/select/hover/eval/screenshot/listen_network` | `core/job_spec.go` |
| 研究运行时 | `run/async/soak` 与 notebook output | `research/*.go`, `api/server.go` |
| 存储后端 | file/process/sql dataset/result store 与 event store | `storage/*.go` |
| Scrapy 风格项目流 | plugin、pipeline、spider/downloader middleware、browser fetcher、artifact project config | `scrapy/*.go` |
| 队列桥接 | RabbitMQ / Kafka HTTP bridge 与 native queue client 构建能力 | `distributed/queue_backends.go` |
| 增量抓取 | ETag / Last-Modified / delta token / snapshot restore | `core/incremental.go` |
| 会话池 | session lifecycle、cookie/header/proxy 复用 | `session/session_pool.go` |

### 2.2 真实边界与缺陷

| 类型 | 问题 | 证据 |
| --- | --- | --- |
| AI 降级 | `ai` CLI 默认 `engine = heuristic-fallback`，没有 API Key 时不会使用真实 LLM | `cmd/gospider/main.go` |
| 浏览器能力边界 | `ultimate.simulateBrowser()` 实际是 HTTP GET + NodeReverse simulate，不是真正打开浏览器页面 | `ultimate/spider.go` |
| 仓库残留 | `monitor.go.corrupted`、`monitor.go.original` 与正式 `monitor.go` 同时存在，容易误导读者和生成工具 | `monitor/monitor.go.corrupted`, `monitor/monitor.go.original`, `monitor/monitor.go` |

### 2.3 结论

GoSpider 的强项是：

- 并发运行时
- artifact 最完整的浏览器链路
- 队列/存储/控制面完整

但要避免把 `ultimate simulateBrowser` 写成“真实浏览器仿真”，更准确的说法应是：

- reverse-assisted fingerprint/browser emulation

---

## 3. RustSpider

### 3.1 新增确认的隐藏能力

| 能力域 | 隐藏能力 | 代码位置 |
| --- | --- | --- |
| feature gate | 明确拆分为 `browser`、`video`、`distributed`、`api`、`web`、`ai`、`full` | `Cargo.toml` |
| CLI 面 | `config/crawl/browser/ai/doctor/preflight/export/curl/run/job/async-job/workflow/jobdir/http-cache/console/audit/web/media/ultimate/sitemap-discover/plugins/selector-studio/scrapy/profile-site/research/node-reverse/anti-bot/capabilities` | `src/main.rs` |
| browser tooling | `fetch/trace/mock/codegen` 四套子面 | `src/main.rs` |
| scorecard 契约 | capability/job/scrapy/node_reverse/ultimate/storage/queue/browser 多套 scorecard/contract tests | `tests/*.rs` |
| Web/UI/API | token 保护的任务页、工件、日志、graph extract、research history | `src/web/mod.rs`, `src/api/server.rs` |
| 研究运行时 | sync + async + soak + dataset 回传 | `src/research.rs`, `src/async_research.rs` |
| ultimate | checkpoint、captcha recovery、reverse fingerprint/TLS/Canvas 联动 | `src/advanced/ultimate.rs` |
| 队列层 | Redis lease、expired lease reap、dead-letter、queue backend support | `src/distributed/*.rs`, `src/queue_backends.rs` |
| 工件与审计 | artifact store、audit trail、event bus、cookie jar、checkpoint manager | `src/artifact/mod.rs`, `src/audit.rs`, `src/event_bus.rs`, `src/cookie.rs`, `src/checkpoint.rs` |
| 独立 preflight 二进制 | 除主 CLI 外还有 `bin/preflight.rs` | `src/bin/preflight.rs` |

### 3.2 真实边界与缺陷

| 类型 | 问题 | 证据 |
| --- | --- | --- |
| AI 降级 | `ai` CLI 默认走 `heuristic-fallback`，无 API Key 或 LLM 返回非 JSON 时自动回退 | `src/main.rs` |
| 浏览器能力边界 | `encrypted::crawler::simulate_browser()` 只是检测 HTML 中的 `navigator.*` 指纹痕迹，再调用 reverse service，不是真实浏览器会话 | `src/encrypted/crawler.rs` |
| 失败处理偏激进 | `checkpoint.rs` 在目录创建失败时直接 `panic!`，不够适合长生命周期服务 | `src/checkpoint.rs` |

### 3.3 结论

RustSpider 的隐藏深度很高，尤其在：

- 控制面
- scorecard 契约
- captcha recovery
- feature-gated 运行时

但文档需要明确区分：

- “真实浏览器抓取”
- “reverse-assisted browser simulation”
- “LLM extraction”
- “heuristic fallback”

---

## 4. PySpider

### 4.1 新增确认的隐藏能力

| 能力域 | 隐藏能力 | 代码位置 |
| --- | --- | --- |
| CLI 面 | `crawl/doctor/preflight/media/web/browser/export/curl/job/async-job/workflow/capabilities/sitemap-discover/plugins/selector-studio/scrapy/profile-site/ultimate/ai/anti-bot/node-reverse/config/jobdir/http-cache/console/audit` | `pyspider/__main__.py`, `pyspider/cli/main.py` |
| Scrapy 项目流 | `demo/run/export/profile/doctor/bench/shell/list/validate/plan-ai/sync-ai/auth-validate/auth-capture/scaffold-ai/genspider/init/contracts` | `pyspider/cli/main.py` |
| AI 项目脚手架 | 自动写 `schema/blueprint/prompt/auth/spider/plan` 多类资产 | `pyspider/cli/main.py` |
| 图谱工件 | graph 直接写入 control-plane artifact | `pyspider/__main__.py`, `pyspider/api/server.py`, `pyspider/graph_crawler/*.py` |
| Cookie 体系 | 自研 `CookieJar`，支持持久化、Netscape 导出、域名匹配、过期清理 | `pyspider/core/cookie.py` |
| ExtractionStudio | `css/css_attr/xpath/json_path/regex/ai` 混合提取 | `pyspider/cli/main.py`, `pyspider/extract/studio.py` |
| Retry/Circuit | 多策略 retry + circuit breaker | `pyspider/core/retry.py`, `pyspider/performance/circuit_breaker.py` |
| 控制面 | audit sink、jobdir、http-cache、console/audit snapshot/tail | `pyspider/__main__.py`, `pyspider/runtime/audit.py` |
| artifact 驱动媒体 | 可从 html/network/har artifact 恢复视频再下载 | `pyspider/cli/video_downloader.py` |
| feature gate | `ai/browser/distributed/media/workflow/crawlee` | `pyspider/feature_gates.py` |

### 4.2 真实边界与缺陷

| 类型 | 问题 | 证据 |
| --- | --- | --- |
| AI 降级 | `ai` CLI 默认 `heuristic-fallback`，没有 API Key 时回退到本地启发式提取 | `pyspider/cli/main.py` |
| 浏览器能力边界 | `advanced.ultimate.simulate_browser()` 实际是先 `requests.get()`，再调用 `reverse_client.simulate_browser()`，不是真实浏览器执行 | `pyspider/advanced/ultimate.py` |
| 兼容降级 | `node_reverse/fetcher.py` 在旧 fetcher 缺失时会启用“最小可运行 fallback”，实际就退化为 `requests.request()` | `pyspider/node_reverse/fetcher.py` |

### 4.3 结论

PySpider 是四个里作者工作流最强的一套：

- 项目化
- AI 脚手架
- 认证资产
- artifact 驱动

但它也最容易被误写成“所有 AI/browser/reverse 能力都默认开箱即用”。实际上需要明确写出：

- 没有 Key 时会回退
- ultimate simulate_browser 不等于真实浏览器
- fetcher 兼容层在缺少旧组件时会降级

---

## 6. 需要从旧文档中删除或降权的说法

以下说法应视为过时或不够准确：

1. “四个 runtime 已全部从 placeholder 进入 core paths verifiable”
2. “AI extraction” 未区分真实 LLM 与 heuristic fallback
3. “browser simulate” 未区分真实浏览器与 reverse-assisted 模拟
4. “四个 runtime 覆盖同一 broad capability surface” 没错，但成熟度并不对等

因此旧的“完成度报告”不再适合作为当前总状态文档。

---

## 7. 建议的新文档口径

今后的能力文档建议统一用下面四级状态：

- `Implemented`：代码中已有稳定实现
- `Conditionally Available`：依赖 API Key、外部服务、feature gate、特定配置
- `Heuristic / Fallback`：默认或错误路径会退化到启发式/兼容实现
- `Incomplete / Repo Hygiene Issue`：实现不完整，或仓库存在残留/歧义文件

这样可以避免“模块存在”被误读成“生产级能力无条件可用”。

---

## 8. 最终判断

继续深挖后，可以确认：

- 四个框架的隐藏能力确实还很多
- 但当前最需要修正的不是“再堆新能力描述”，而是把文档从“能力宣传”修回“能力分层说明”

本轮代码补齐后，额外确认：

- `gospider` 浏览器层已补入上传表单支持，以及 same-origin iframe helper
- `rustspider` 浏览器层已补入上传表单支持，以及显式 frame 切换 / 返回父 frame 支持

如果只问一句“这四个框架所有代码能力还有没有缺陷”：

- 有，而且主要集中在能力边界、fallback 降级、模拟能力被过度表述、以及少量仓库残留文件这四类

这份报告已经把当前最重要的隐藏能力与缺陷边界一起补齐。
