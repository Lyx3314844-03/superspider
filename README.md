# SuperSpider

<p align="center">
  <img src="docs/assets/superspider-wordmark.svg" alt="SuperSpider multicolor wordmark" width="860" />
</p>

<p align="center">
  <img src="docs/assets/superspider-icon.svg" alt="SuperSpider icon" width="180" />
</p>

SuperSpider 是一个四运行时爬虫框架发布仓库。它不是“一个语言绑定到多个壳”，而是四套面向不同生产环境的抓取运行时：

- `pyspider`
- `gospider`
- `rustspider`
- `javaspider`

这四个框架面向同一类抓取问题，但分别强调不同的交付方式、运行边界、并发模型和工程生态：

- `PySpider` 强调项目脚手架、AI 编排、插件注入和快速迭代。
- `GoSpider` 强调二进制交付、并发执行、分布式 worker 和控制面友好。
- `RustSpider` 强调强类型、高性能、feature-gated 模块和稳定的发布二进制。
- `JavaSpider` 强调 Maven/JAR 打包、浏览器工作流、审计链和企业 Java 集成。

这个仓库当前只保留三类内容：

- 四个爬虫框架源码
- Windows / Linux / macOS 三种操作系统安装版本
- 整体介绍、能力说明和安装文档

## Overall Framework

SuperSpider 的整体设计目标是把“多语言抓取框架发布”收敛成统一的产品面：

- 同一套发布品牌：`SuperSpider`
- 同一套四运行时命名：`pyspider / gospider / rustspider / javaspider`
- 同一套安装入口：每个框架都提供三种操作系统安装路径
- 同一套能力说明方式：总览、矩阵、框架级 README

这意味着用户可以先按运行环境选语言，再按场景选框架，而不是从一堆不相关的 demo、扩展仓库和辅助工具里自己拼装。

## Four Frameworks

### PySpider

PySpider 是最适合快速试验和复杂抓取编排的一支。

- Python 原生模块与 CLI
- 最完整的 scrapy 风格项目运行模型
- AI 提取、研究流程、插件注入、数据集输出
- 浏览器与 HTTP 混合抓取
- 反爬、验证码、节点逆向和媒体处理

适合：

- 想快速搭一个真实项目
- 想做 AI 提取或复杂抓取流程编排
- 想保留 Python 生态下的数据处理灵活性

入口见 [pyspider/README.md](pyspider/README.md)。

### GoSpider

GoSpider 是最适合二进制发布和并发抓取服务化的一支。

- Go 二进制 CLI
- 高并发抓取与任务调度
- 分布式 worker、队列、存储
- 浏览器产物采集与回放
- 反爬、媒体下载与运行时调度

适合：

- 想发布单文件二进制
- 想把抓取任务做成服务或批处理
- 想要并发和部署复杂度之间的平衡

入口见 [gospider/README.md](gospider/README.md)。

### RustSpider

RustSpider 是最适合高性能和强边界生产部署的一支。

- Rust 发布二进制
- feature-gated 浏览器、分布式、API 和 Web 模块
- typed scrapy 风格接口
- 监控、预检、反爬、媒体和契约测试
- 适合强类型和高稳定性部署

适合：

- 想要强类型和更严格的运行边界
- 想构建稳定的发布二进制
- 想把功能面通过 feature flag 精确裁剪

入口见 [rustspider/README.md](rustspider/README.md)。

### JavaSpider

JavaSpider 是最适合浏览器工作流和企业 Java 环境集成的一支。

- Maven / JAR 打包
- 浏览器工作流与 Selenium / Playwright 辅助路径
- scrapy 风格兼容接口
- 审计、连接器、会话与反爬能力
- 工作流回放与媒体解析

适合：

- 已经在 Java / Maven 生态中工作
- 想把抓取纳入现有企业构建链
- 更重视浏览器工作流和可审计执行链

入口见 [javaspider/README.md](javaspider/README.md)。

## Three OS Install Versions

每个框架都提供三种操作系统安装版本。

| Framework | Windows | Linux | macOS |
| --- | --- | --- | --- |
| PySpider | `scripts/windows/install-pyspider.bat` | `scripts/linux/install-pyspider.sh` | `scripts/macos/install-pyspider.sh` |
| GoSpider | `scripts/windows/install-gospider.bat` | `scripts/linux/install-gospider.sh` | `scripts/macos/install-gospider.sh` |
| RustSpider | `scripts/windows/install-rustspider.bat` | `scripts/linux/install-rustspider.sh` | `scripts/macos/install-rustspider.sh` |
| JavaSpider | `scripts/windows/install-javaspider.bat` | `scripts/linux/install-javaspider.sh` | `scripts/macos/install-javaspider.sh` |

安装产物：

- `PySpider`：创建 `.venv-pyspider` 并完成可编辑安装
- `GoSpider`：生成 `gospider` 可执行文件
- `RustSpider`：生成 `rustspider/target/release/rustspider`
- `JavaSpider`：生成 `javaspider/target` Maven 构建输出

详细安装说明见 [docs/SUPERSPIDER_INSTALLS.md](docs/SUPERSPIDER_INSTALLS.md)。

## Documentation

- 框架能力总览: [docs/FRAMEWORK_CAPABILITIES.md](docs/FRAMEWORK_CAPABILITIES.md)
- 四框架能力矩阵: [docs/FRAMEWORK_CAPABILITY_MATRIX.md](docs/FRAMEWORK_CAPABILITY_MATRIX.md)
- 三系统安装矩阵: [docs/SUPERSPIDER_INSTALLS.md](docs/SUPERSPIDER_INSTALLS.md)
- GitHub Release Notes: [docs/RELEASE_NOTES_v1.0.0.md](docs/RELEASE_NOTES_v1.0.0.md)
- 发布展示页: [docs/release-canvas.html](docs/release-canvas.html)

## Repository Scope

这个发布仓库只保留：

- `gospider`
- `javaspider`
- `pyspider`
- `rustspider`
- `docs`
- `scripts`

其目标是让 GitHub 首页直接呈现一个“可发布、可安装、可理解”的四框架产品面，而不是保留其他爬虫框架或无关演示文件。
