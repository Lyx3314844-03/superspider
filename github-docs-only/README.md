# 四大爬虫框架 GitHub 文档发布包

本目录是一个只包含 Markdown 的 GitHub 发布包，用于公开展示四个爬虫框架的能力，不包含源码、构建产物、脚本、测试或二进制文件。

包含框架：

- `PySpider`
- `GoSpider`
- `RustSpider`
- `JavaSpider`

发布目标：

- 只发布能力说明
- 只发布 Markdown 文档
- 适合单独作为 GitHub 文档仓库使用
- 适合从主仓库中单独抽出上传

## 建议在 GitHub 上保留的文档

- [DOCS_INDEX.md](./DOCS_INDEX.md)
- [SHARED_CAPABILITY_CATALOG.md](./SHARED_CAPABILITY_CATALOG.md)
- [FRAMEWORK_CAPABILITY_MATRIX.md](./FRAMEWORK_CAPABILITY_MATRIX.md)
- [DETAILED_CAPABILITY_MATRIX.md](./DETAILED_CAPABILITY_MATRIX.md)
- [PYSPIDER_CAPABILITIES.md](./PYSPIDER_CAPABILITIES.md)
- [GOSPIDER_CAPABILITIES.md](./GOSPIDER_CAPABILITIES.md)
- [RUSTSPIDER_CAPABILITIES.md](./RUSTSPIDER_CAPABILITIES.md)
- [JAVASPIDER_CAPABILITIES.md](./JAVASPIDER_CAPABILITIES.md)
- [NODE_REVERSE_AND_ANTI_BOT.md](./NODE_REVERSE_AND_ANTI_BOT.md)
- [MEDIA_AND_PLATFORM_SUPPORT.md](./MEDIA_AND_PLATFORM_SUPPORT.md)
- [GITHUB_PUBLISHING_GUIDE.md](./GITHUB_PUBLISHING_GUIDE.md)

## 四个框架的公共能力范围

- HTTP 抓取与基础调度
- 浏览器自动化与动态页面处理
- 反爬能力与会话伪装
- Node.js 逆向接入
- 加密站点分析与签名处理
- 媒体站点解析与下载
- 数据提取、存储、导出
- CLI、项目化运行、服务化运行
- 分布式、监控、审计、工作流扩展

## 框架定位速览

| 框架 | 主要语言 | 主要交付形态 | 最适合的使用场景 |
| --- | --- | --- | --- |
| `PySpider` | Python | 包 / 虚拟环境 / CLI | 快速开发、AI 编排、项目制爬虫 |
| `GoSpider` | Go | 编译后二进制 | 高并发、服务部署、分布式节点 |
| `RustSpider` | Rust | 发布二进制 | 强类型、高性能、边界清晰的生产环境 |
| `JavaSpider` | Java | Maven / JAR | Java 生态、浏览器流程、企业集成 |

## 这套发布包的使用方式

如果你只想把“能力说明”放到 GitHub，而不发布源码，直接把本目录作为单独仓库内容上传即可。

建议仓库名示例：

- `superspider-docs`
- `four-spider-frameworks-docs`
- `crawler-framework-capabilities`

## 发布边界

本发布包只覆盖以下内容：

- 全量能力目录
- 能力概览
- 能力矩阵
- 每个框架的定位与能力说明
- 共享的 Node 逆向 / 反爬 / 浏览器 / 媒体能力说明
- GitHub 发布说明

本发布包不包含以下内容：

- 源代码
- 安装脚本
- 构建脚本
- 测试代码
- 可执行文件
- 浏览器资源
- `node_modules`
- CI 配置
