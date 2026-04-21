# GitHub 发布说明

## 目标

只把四个爬虫框架的能力说明发布到 GitHub，不发布源码，不发布脚本，不发布构建文件，不发布依赖目录。

## 这次整理后的建议发布内容

只发布当前目录下的这些文件：

- `README.md`
- `DOCS_INDEX.md`
- `SHARED_CAPABILITY_CATALOG.md`
- `FRAMEWORK_CAPABILITY_MATRIX.md`
- `DETAILED_CAPABILITY_MATRIX.md`
- `PYSPIDER_CAPABILITIES.md`
- `GOSPIDER_CAPABILITIES.md`
- `RUSTSPIDER_CAPABILITIES.md`
- `JAVASPIDER_CAPABILITIES.md`
- `NODE_REVERSE_AND_ANTI_BOT.md`
- `MEDIA_AND_PLATFORM_SUPPORT.md`
- `GITHUB_PUBLISHING_GUIDE.md`

## 不建议发布的内容

不要把下面这些内容一起放到公开 GitHub 文档仓库：

- `gospider/`
- `javaspider/`
- `pyspider/`
- `rustspider/`
- `node_modules/`
- `node-reverse-server/`
- `tools/`
- `tests/`
- `scripts/`
- 构建产物
- 安装脚本
- 本地调试报告

## 推荐发布方式

### 方式一：单独新建 GitHub 文档仓库

最干净的做法是：

1. 新建一个 GitHub 仓库
2. 只上传本目录下的 Markdown 文件
3. 把这个仓库作为四框架公开能力介绍仓库

### 方式二：从主仓库中抽一个 docs-only 分支

适合你想保留和主仓库的关系，但公开层面只给文档。

### 方式三：把本目录作为子目录发布

如果你暂时不想新建仓库，也可以先把这个目录放在现有仓库中，再单独复制出去发布。

## 建议仓库首页结构

GitHub 首页建议阅读顺序：

1. `README.md`
2. `FRAMEWORK_CAPABILITY_MATRIX.md`
3. 四个框架单页文档
4. `NODE_REVERSE_AND_ANTI_BOT.md`
5. `MEDIA_AND_PLATFORM_SUPPORT.md`

## 建议仓库简介

可直接用于 GitHub 仓库 description：

`Documentation-only repository for PySpider, GoSpider, RustSpider, and JavaSpider capabilities.`

也可以用中文：

`四大爬虫框架能力说明文档仓库，仅发布 Markdown，不含源码。`

## 建议 Topics

- `crawler`
- `web-scraping`
- `browser-automation`
- `anti-bot`
- `node-reverse`
- `playwright`
- `selenium`
- `python`
- `go`
- `rust`
- `java`

## 发布前最后检查

发布前确认：

- 目录内只有 `.md` 文件
- 没有源码
- 没有二进制
- 没有依赖目录
- 没有内部脚本
- 没有本地构建文件
