# GoSpider 能力说明

## 框架定位

`GoSpider` 是四个框架里最偏并发执行、二进制交付、节点部署和服务化运行的一档。

它适合：

- 要并发
- 要二进制
- 要稳定部署到服务器
- 要 worker / queue / runtime 调度

## 核心能力

- 编译后二进制 CLI
- 并发抓取
- 分布式能力
- 浏览器自动化
- 抓取结果存储
- 反爬处理
- Node.js 逆向接入
- 媒体解析与下载
- 监控与运行时接口

## 浏览器与动态页面

`GoSpider` 浏览器主线以 `chromedp` 为核心。

能力包括：

- Chrome/CDP 运行时
- 页面导航
- HTML 抽取
- 选择器提取
- JavaScript 执行
- 全页截图
- 网络监听
- Console / Network 记录
- 附加请求头
- 基础 stealth 浏览器参数

这使它在以下场景很强：

- Chrome 动态执行
- 网络请求观察
- 偏工程化的浏览器调试
- 服务端长跑任务

## Node.js 逆向能力

`GoSpider` 的 `node_reverse` 客户端是四个框架里实现最“工程化”的一档。

除了远程接口，它还具备较深的本地启发式分析：

- 算法识别
- 模式识别
- 动态 key 来源识别
- key flow candidates
- key flow chains
- obfuscation loaders
- crypto sinks
- `riskScore`
- `reverseComplexity`
- `recommendedApproach`
- `requiresASTDataflow`
- `requiresRuntimeExecution`
- `requiresLoaderUnpack`

支持的远程逆向面包括：

- crypto analyze
- encrypt / decrypt
- AST analyze
- Webpack analyze
- signature reverse
- anti-bot detect / profile
- fingerprint spoof
- TLS fingerprint
- canvas fingerprint

## 分布式与运行时能力

`GoSpider` 非常适合对外描述为运维友好的 crawler runtime。

能力包括：

- 节点发现
- 任务分发
- 队列与存储
- 运行时浏览器执行
- API 层
- 监控层

## Playwright 现状

仓库中存在 Playwright 方向实现，但当前主线说明更偏 `chromedp`，Playwright 池文件处于禁用状态。

因此 GitHub 文档里建议这样写：

- 原生主线是 Chrome/CDP 执行
- 提供 Playwright 兼容方向
- 当前实战主线仍以 `chromedp` 为准

## 最适合的 GitHub 公开定位

- 面向高并发、二进制交付和服务部署的 Go 爬虫框架
- 强调 Chrome/CDP 动态执行和工程型 Node 逆向分析
- 适合生产环境和节点化运行
