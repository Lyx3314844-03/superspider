# SuperSpider Capability Matrix

| Area | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Primary language | Python | Go | Rust | Java |
| Delivery model | virtualenv package | compiled binary | release binary | Maven package / JAR |
| Strongest trait | fastest iteration | concurrent deployment | typed high-performance runtime | enterprise browser workflow |
| Project authoring | strongest | good | good | good |
| Browser + HTTP mix | strong | strong | strong | strong |
| AI extraction | strong | medium | medium | medium |
| Distributed runtime | strong | strong | strong | medium-strong |
| Anti-bot surface | strong | strong | strong | strong |
| Media / downloader tooling | strong | strong | strong | medium-strong |
| Best fit | experimentation and AI pipelines | services and binaries | performance-sensitive deployments | Java ecosystem integration |

## Reading The Matrix

- `PySpider` 优先解决“做项目最快、扩展最灵活”。
- `GoSpider` 优先解决“部署简单、并发强、服务化友好”。
- `RustSpider` 优先解决“类型边界清晰、发布二进制稳定、性能强”。
- `JavaSpider` 优先解决“浏览器工作流丰富、Maven 生态集成自然、企业环境友好”。

## Recommendation By Goal

如果你的主要目标是：

- 快速试验、插件注入、AI 抽取：选 `PySpider`
- 二进制交付、并发抓取、worker/queue 体系：选 `GoSpider`
- 强类型高性能部署、模块裁剪：选 `RustSpider`
- 企业 Java 工程、浏览器工作流、审计链：选 `JavaSpider`
