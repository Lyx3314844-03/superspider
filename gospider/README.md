# GoSpider

GoSpider 是 SuperSpider 中的 Go 爬虫框架。

## Capabilities

- Go 二进制 CLI
- 高并发抓取与调度
- 分布式 worker、队列、存储
- 浏览器产物采集与回放
- 反爬、媒体下载与运行时调度

## Install

Windows:

- `..\scripts\windows\install-gospider.bat`

Linux:

- `../scripts/linux/install-gospider.sh`

macOS:

- `../scripts/macos/install-gospider.sh`

## Run

```bash
go build ./cmd/gospider
gospider version
```
