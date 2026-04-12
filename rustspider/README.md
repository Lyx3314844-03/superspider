# RustSpider

RustSpider 是 SuperSpider 中最强调强类型、高性能和可裁剪发布二进制的 Rust 爬虫框架。

## Why RustSpider

如果你更关心：

- 强类型和高性能
- feature-gated 模块裁剪
- 生产环境中的边界控制和发布稳定性

那 RustSpider 会是这四个框架里最适合严格部署的一支。

## Standout Capabilities

- Rust 发布二进制
- feature-gated 浏览器、分布式、API 和 Web 模块
- typed scrapy 风格接口
- 监控、预检、反爬、媒体和契约测试
- 更适合高性能和强边界部署

## Install Versions

Windows:

- `..\scripts\windows\install-rustspider.bat`

Linux:

- `../scripts/linux/install-rustspider.sh`

macOS:

- `../scripts/macos/install-rustspider.sh`

## Typical Output

- 生成 `rustspider/target/release/rustspider`
- 适合发布为稳定的 release 二进制

## Quick Start

```bash
cargo build --release
```
