# 多运行时能力缺陷审计

更新时间：2026-04-21

范围：

- SuperSpider 四个核心运行时：`javaspider / gospider / rustspider / pyspider`

## 高优先级问题

### 1. AI 能力默认会静默降级

- `gospider`：`ai` CLI 默认 `engine = heuristic-fallback`，无 API Key 时直接退回启发式提取。
- `rustspider`：同样默认 `heuristic-fallback`，且 LLM 返回非 JSON 也会回退。
- `pyspider`：`AI_API_KEY / OPENAI_API_KEY` 未配置时回退到本地启发式提取。

- 文档里写“支持 AI extraction”没有错，但如果不写“默认可能不是 LLM”，用户会高估结果质量。

## 中优先级问题

### 2. 多个 browser simulate 不是“真实浏览器”

- `gospider/ultimate/spider.go`：`simulateBrowser()` 先 HTTP GET，再调用 NodeReverse。
- `pyspider/advanced/ultimate.py`：`simulate_browser()` 先 `requests.get()`，再交给 reverse client。
- `rustspider/src/encrypted/crawler.rs`：`simulate_browser()` 基于 HTML 检测后调用 reverse service。
- `javaspider/src/main/java/com/javaspider/advanced/UltimateSpiderProcessor.java`：`simulateFullBrowser()` 生成 TLS/Canvas 指纹并调 reverse 脚本，不是浏览器 session。

- 这类能力更准确的名称应是 `reverse-assisted browser emulation`。

### 4. 仓库存在会误导能力判断的残留文件

- `gospider/monitor/monitor.go.corrupted`
- `gospider/monitor/monitor.go.original`

- 会误导代码检索、文档生成、以及后续维护者对正式实现的判断。

## 低优先级问题

### 5. Java 验证码失败语义不一致

- `javaspider` 的 `CaptchaSolver` 在不同失败路径中混用 `return null` 与抛异常。

- 上层调用者需要额外防御，容易出现“空值吞错”和“异常冒泡”两套分支。

### 6. Python reverse fetcher 存在兼容降级

- `pyspider/node_reverse/fetcher.py` 在旧 fetcher 缺失时提供“最小可运行 fallback”，本质是普通 `requests` 取数。

- 功能能跑，但能力强度会比文档预期低很多。

### 7. Rust checkpoint 初始化失败会 panic

- `rustspider/src/checkpoint.rs` 在 checkpoint 目录创建失败时直接 `panic!`。

- 对服务型运行时不够温和，错误恢复空间不足。

## 建议

1. 文档统一标注 `Implemented / Conditional / Fallback / Incomplete`。
2. 将 `simulateBrowser` 一类命名改得更准确。
3. 清理仓库残留文件，避免能力扫描被污染。
4. 对 AI CLI 输出显式写出当前是否为真实 LLM 引擎。
