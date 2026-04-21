# PySpider 能力说明

## 框架定位

`PySpider` 是四个框架里最偏项目化、AI 编排、快速迭代的运行时。

它适合：

- 需要快速写 crawler prototype
- 需要 Playwright 动态执行
- 需要 AI 提取、总结、实体识别
- 需要把 CLI、项目配置、插件、工作流放在一起的人

## 核心能力

- Python 原生 CLI
- 项目化运行
- HTTP + 浏览器混合抓取
- Playwright 与 Selenium 支持
- 反爬能力与浏览器伪装
- Node.js 逆向服务接入
- 本地静态 crypto/obfuscation 分析
- 签名逆向、AST、Webpack、浏览器模拟接口
- AI 提取、研究流、数据输出

## 浏览器与动态页面

`PySpider` 的浏览器层是四个框架里最完整的一档。

能力包括：

- Playwright 浏览器启动与上下文管理
- 页面导航
- 执行 JavaScript
- 截图
- Cookie 管理
- Storage State 管理
- 动态滚动
- init script 注入
- 基础 stealth 伪装
- 高级 stealth 伪装

适合处理：

- SPA
- 需要登录态的页面
- 前端动态渲染站点
- 依赖浏览器环境的 JS 逻辑

## Node.js 逆向能力

`PySpider` 提供较完整的 `node_reverse` 客户端和 CLI 面。

支持的能力包括：

- 健康检查
- 反爬画像
- 反爬检测
- 浏览器指纹伪造
- TLS 指纹生成
- Canvas 指纹
- JS 执行
- AST 分析
- Webpack 分析
- 函数调用
- 签名逆向
- 浏览器环境模拟

本地静态分析还能识别：

- CryptoJS
- Node `crypto`
- WebCrypto
- Forge
- SJCL
- `sm-crypto`
- `JSEncrypt`
- `jsrsasign`
- `tweetnacl`
- `elliptic`
- `sodium`

## AI 与提取能力

`PySpider` 在四者里最强调 AI 提取和项目编排。

能力面包括：

- AI 抽取
- 摘要
- 实体识别
- 研究式输出
- 结构化导出

## 数据与工程能力

- CLI 驱动
- 配置化运行
- 作业目录
- 数据集输出
- JSON/JSONL 输出
- 测试覆盖较完整
- 适合做主控框架和实验框架

## 最适合的 GitHub 公开定位

如果 GitHub 只公开能力文档，不公开源码，`PySpider` 建议这样描述：

- 面向复杂动态站点和 AI 提取的 Python 爬虫框架
- 具备完整的浏览器自动化和 Node 逆向接入能力
- 适合快速开发、调试、实验和工作流编排
