# SuperSpider v1.0.0

SuperSpider `v1.0.0` 是一个四运行时爬虫框架发布版本。

这次发布不是“一个框架换四种语言外壳”，而是四个针对不同工程场景和交付模型设计的爬虫运行时：

- `pyspider`
- `gospider`
- `rustspider`
- `javaspider`

同时，这个版本把发布仓库明确收敛成一个纯四框架产品面：

- 只保留四个框架源码
- 只保留 Windows / Linux / macOS 三种操作系统安装入口
- 只保留能力说明、安装说明和品牌资源

## Highlights

- 一个统一品牌：`SuperSpider`
- 四个可独立选择的抓取运行时
- 三种操作系统安装版本
- 更清晰的框架定位与能力文案
- 更适合 GitHub 仓库首页、Release 页面和对外发布

## Overall Platform

SuperSpider 的目标是把“多语言爬虫框架发布”整理成一个清晰可选型的平台：

- 想要快速迭代与 AI 编排，选择 `PySpider`
- 想要二进制交付与并发服务化，选择 `GoSpider`
- 想要强类型高性能与可裁剪模块，选择 `RustSpider`
- 想要 Maven / JAR 打包与企业 Java 集成，选择 `JavaSpider`

这四个框架解决的是同一类抓取问题，但它们服务的交付场景并不相同。

## Frameworks

### PySpider

PySpider 是 SuperSpider 中最适合快速试验和项目化抓取开发的一支。

突出能力：

- Python 原生 CLI 和包管理
- 最完整的 scrapy 风格项目运行模型
- AI 提取、研究流程、插件注入和数据集输出
- 浏览器与 HTTP 混合抓取
- 反爬、验证码、节点逆向和媒体处理

适合：

- 快速搭项目
- 做 AI 提取或复杂抓取编排
- 保留 Python 数据处理灵活性

### GoSpider

GoSpider 是最适合并发执行和二进制发布的一支。

突出能力：

- Go 二进制 CLI
- 高并发抓取与任务调度
- 分布式 worker、队列和存储
- 浏览器产物采集与回放
- 反爬、媒体下载与运行时调度

适合：

- 部署独立可执行文件
- 服务化抓取
- 批处理作业与控制面驱动执行

### RustSpider

RustSpider 是最适合高性能和强边界生产部署的一支。

突出能力：

- Rust 发布二进制
- feature-gated 浏览器、分布式、API 和 Web 模块
- typed scrapy 风格接口
- 预检、监控、反爬、媒体和契约测试
- 更适合严格控制功能面的发布

适合：

- 高性能抓取
- 更稳定的发布二进制
- 强类型和更严格的运行边界

### JavaSpider

JavaSpider 是最适合浏览器工作流和企业 Java 环境的一支。

突出能力：

- Maven / JAR 打包模型
- 浏览器工作流和 Selenium / Playwright 辅助路径
- scrapy 风格兼容接口
- 审计、连接器、会话与反爬能力
- 工作流回放与媒体解析

适合：

- Java / Maven 工程体系
- 浏览器驱动抓取和流程编排
- 企业系统集成和可审计执行链

## Install Versions

每个框架都提供三种操作系统安装版本。

### Windows

- `scripts/windows/install-pyspider.bat`
- `scripts/windows/install-gospider.bat`
- `scripts/windows/install-rustspider.bat`
- `scripts/windows/install-javaspider.bat`

### Linux

- `scripts/linux/install-pyspider.sh`
- `scripts/linux/install-gospider.sh`
- `scripts/linux/install-rustspider.sh`
- `scripts/linux/install-javaspider.sh`

### macOS

- `scripts/macos/install-pyspider.sh`
- `scripts/macos/install-gospider.sh`
- `scripts/macos/install-rustspider.sh`
- `scripts/macos/install-javaspider.sh`

安装产物：

- `PySpider`：创建 `.venv-pyspider`
- `GoSpider`：构建 `gospider` 可执行文件
- `RustSpider`：构建 `rustspider/target/release/rustspider`
- `JavaSpider`：生成 `javaspider/target` Maven 构建输出

## Repository Scope In This Release

这个版本的 GitHub 仓库只保留：

- `gospider`
- `javaspider`
- `pyspider`
- `rustspider`
- `docs`
- `scripts`

这使得仓库首页和 Release 页面能直接表达产品本身，而不是混杂其他爬虫框架、实验项目或无关发布资产。

## Recommended Reading

- 框架能力总览：`docs/FRAMEWORK_CAPABILITIES.md`
- 四框架能力矩阵：`docs/FRAMEWORK_CAPABILITY_MATRIX.md`
- 三系统安装矩阵：`docs/SUPERSPIDER_INSTALLS.md`
- 视觉化发布页：`docs/release-canvas.html`
