# GoSpider

GoSpider 是 SuperSpider 中最强调并发执行和二进制交付的 Go 爬虫框架。

## Why GoSpider

如果你更关心：

- 单二进制部署
- 并发抓取和任务执行
- 分布式 worker、队列和服务化运行

那 GoSpider 会是四个框架里最适合运营部署的一支。

## Standout Capabilities

- Go 二进制 CLI
- 高并发抓取与任务调度
- 分布式 worker、队列、存储与控制面友好
- 浏览器产物采集、回放和运行时调度
- 反爬、媒体下载、解析和任务执行链条完整

## Install Versions

Windows:

- `..\scripts\windows\install-gospider.bat`

Linux:

- `../scripts/linux/install-gospider.sh`

macOS:

- `../scripts/macos/install-gospider.sh`

## Typical Output

- 构建出 `gospider` 可执行文件
- 适合复制到节点或服务器直接运行

## Quick Start

```bash
go build ./cmd/gospider
gospider version
```
