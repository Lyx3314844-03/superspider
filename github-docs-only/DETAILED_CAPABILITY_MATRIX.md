# 四大爬虫框架详细能力矩阵

说明：

- `强`：当前公开能力面清晰、适合作为主卖点
- `中强`：能力明确，但不是主卖点或实现路径偏间接
- `中`：能力存在，但更依赖外部环境、适配层或特定场景

## 基础抓取与解析

| 能力 | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| HTTP 抓取 | 强 | 强 | 强 | 强 |
| Header / Cookie / Session | 强 | 强 | 强 | 强 |
| HTML 解析 | 强 | 强 | 强 | 强 |
| CSS / XPath / JSON 提取 | 强 | 强 | 强 | 强 |
| 结构化抽取 | 强 | 强 | 强 | 强 |
| 项目化运行 | 强 | 中强 | 中强 | 中强 |

## 浏览器与动态页面

| 能力 | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| 浏览器自动化 | 强 | 强 | 中强 | 强 |
| 动态页面抓取 | 强 | 强 | 中强 | 强 |
| JavaScript 执行 | 强 | 强 | 中强 | 强 |
| 页面截图 | 强 | 强 | 中强 | 强 |
| 表单 / 点击 / 滚动 | 强 | 强 | 中强 | 强 |
| 浏览器运行时监听 | 中强 | 强 | 中 | 中强 |

## 反爬与伪装

| 能力 | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| User-Agent 伪装 | 强 | 强 | 强 | 强 |
| 浏览器指纹相关能力 | 强 | 强 | 中强 | 强 |
| TLS 指纹相关能力 | 强 | 强 | 强 | 强 |
| anti-bot detect/profile | 强 | 强 | 强 | 强 |
| challenge 风险识别 | 强 | 强 | 中强 | 强 |
| 浏览器 stealth 实战面 | 强 | 中强 | 中 | 中强 |

## Node.js 逆向

| 能力 | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| crypto analyze | 强 | 强 | 强 | 强 |
| JS execute | 强 | 强 | 强 | 强 |
| AST analyze | 强 | 强 | 强 | 强 |
| Webpack analyze | 强 | 强 | 强 | 强 |
| signature reverse | 强 | 强 | 强 | 强 |
| browser simulate | 强 | 强 | 强 | 强 |
| 本地静态兜底分析 | 强 | 强 | 强 | 强 |
| 动态逆向实操体验 | 强 | 强 | 中强 | 中强 |

## 媒体与视频

| 能力 | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| HLS / `m3u8` | 强 | 强 | 强 | 强 |
| DASH / `mpd` | 强 | 强 | 强 | 强 |
| FFmpeg 协同 | 强 | 强 | 强 | 强 |
| DRM 检测 | 强 | 强 | 强 | 强 |
| 平台解析 | 强 | 强 | 强 | 强 |

## 工程与交付

| 能力 | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| CLI | 强 | 强 | 强 | 强 |
| 二进制交付 | 中 | 强 | 强 | 中 |
| Maven / JAR 交付 | 弱 | 弱 | 弱 | 强 |
| 特性开关 / 发布边界 | 中 | 中 | 强 | 中 |
| 企业系统集成 | 中 | 中强 | 中强 | 强 |

## 分布式与运行时

| 能力 | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| 分布式运行 | 强 | 强 | 强 | 中强 |
| 节点 / Worker | 强 | 强 | 强 | 中强 |
| 存储 / 队列 | 强 | 强 | 强 | 中强 |
| 服务化运行 | 强 | 强 | 强 | 强 |

## AI 与增强能力

| 能力 | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| AI 提取 | 强 | 中强 | 中强 | 中强 |
| 摘要 / 实体分析 | 强 | 中强 | 中强 | 中强 |
| 研究型输出 | 强 | 中 | 中 | 中 |

## 最终公开定位

| 框架 | 建议 GitHub 首页定位 |
| --- | --- |
| `PySpider` | AI 驱动、动态站友好、项目化最强的 Python crawler runtime |
| `GoSpider` | 并发、二进制、Chrome/CDP 工程流最强的 Go crawler runtime |
| `RustSpider` | 高性能、强类型、特性可裁剪的 Rust crawler runtime |
| `JavaSpider` | Maven/JAR、浏览器工作流、企业集成友好的 Java crawler runtime |
