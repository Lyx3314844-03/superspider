# Framework Capabilities

这个文档只描述仓库中保留的四个爬虫框架能力：

- `pyspider`
- `gospider`
- `rustspider`
- `javaspider`

## PySpider

- Python 原生模块与 CLI
- 最完整的 scrapy 风格项目运行模型
- AI 提取、研究、插件注入与数据集输出
- 浏览器与 HTTP 混合抓取
- 反爬、验证码、节点逆向与媒体处理

## GoSpider

- Go 二进制部署模型
- 强并发抓取与任务执行
- 分布式 worker、队列、存储与控制面友好
- 浏览器产物采集与回放
- 反爬、媒体下载、解析与运行时调度

## RustSpider

- Rust 强类型发布二进制
- feature-gated 浏览器、分布式、API 和 Web 模块
- typed scrapy 风格接口
- 预检、监控、反爬、媒体与运行时契约
- 适合高性能和强边界部署

## JavaSpider

- Maven/JAR 打包模型
- 浏览器工作流和 Selenium/Playwright 辅助路径
- 审计、连接器、会话和反爬能力
- scrapy 风格兼容接口
- 工作流回放、媒体解析和企业集成路径

## Related Docs

- 安装矩阵: `docs/SUPERSPIDER_INSTALLS.md`
- 能力矩阵: `docs/FRAMEWORK_CAPABILITY_MATRIX.md`
