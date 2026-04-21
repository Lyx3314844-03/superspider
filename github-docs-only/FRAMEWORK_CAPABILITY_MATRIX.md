# 四大爬虫框架能力矩阵

## 总览矩阵

| 维度 | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| 主要语言 | Python | Go | Rust | Java |
| 主要交付 | Python 包 / CLI | 二进制 | 发布二进制 | Maven / JAR |
| 基础 HTTP 抓取 | 强 | 强 | 强 | 强 |
| 动态页面抓取 | 强 | 强 | 中强 | 强 |
| 浏览器自动化 | 强 | 强 | 中强 | 强 |
| 反爬能力 | 强 | 强 | 中强 | 强 |
| Node.js 逆向接入 | 强 | 强 | 强 | 强 |
| 本地静态逆向分析 | 强 | 强 | 强 | 强 |
| AI 提取 / 总结 / 实体能力 | 强 | 中强 | 中强 | 中强 |
| 分布式能力 | 强 | 强 | 强 | 中强 |
| CLI 运行面 | 强 | 强 | 强 | 强 |
| 服务化 / API 面 | 强 | 强 | 强 | 强 |
| 审计 / 合规 / 企业集成 | 中强 | 中强 | 中强 | 强 |
| 媒体解析与下载 | 强 | 强 | 强 | 强 |

## 定位矩阵

| 框架 | 核心优势 | 适合的人群 |
| --- | --- | --- |
| `PySpider` | 项目化、AI 编排、Playwright 实战面最完整 | 想快速迭代、做复杂动态站、想把 AI 提取接进流程的人 |
| `GoSpider` | 并发、二进制、服务化、Chromedp/CDP 执行链 | 要求并发、稳定部署、节点运行的人 |
| `RustSpider` | 强类型、性能、可特性裁剪 | 要求性能和边界控制、偏生产稳定的人 |
| `JavaSpider` | Maven/JAR、浏览器工作流、企业集成 | Java 团队、浏览器流程重、需要企业系统整合的人 |

## 共享能力面

四个框架都覆盖以下公共问题域：

- 页面抓取
- 浏览器渲染
- 提取与解析
- 反爬与伪装
- Node.js 逆向接入
- 加密页面与签名处理
- 媒体站点解析
- 存储与导出
- 工作流与任务运行

## 差异最明显的三块

### 1. 浏览器动态执行

- `PySpider`：原生 Playwright + Selenium，动态执行最顺手
- `GoSpider`：主线是 `chromedp`，偏 Chrome/CDP 工程流
- `RustSpider`：主线是 WebDriver/Fantoccini，动态执行相对更薄
- `JavaSpider`：主线更偏 Selenium，Playwright 更像兼容辅助面

### 2. Node 逆向实战面

- 四者都接入 `node_reverse` 体系
- 四者都具备本地静态兜底分析
- 真正决定实战体验的是浏览器执行链和 CLI 封装

### 3. 工程交付方式

- `PySpider`：最适合项目制和脚本化扩展
- `GoSpider`：最适合二进制交付和节点部署
- `RustSpider`：最适合高性能和特性裁剪
- `JavaSpider`：最适合 Maven/JAR 和企业系统接入
