# RustSpider 能力说明

## 框架定位

`RustSpider` 是四个框架里最偏性能、强类型、特性开关和运行边界控制的一档。

它适合：

- 对性能敏感
- 对运行边界敏感
- 需要 feature-gated 发布
- 想用 Rust 做稳定 crawler runtime

## 核心能力

- Rust 发布二进制
- feature-gated 模块
- 抓取、浏览器、分布式、API、Web 等功能按特性启用
- 反爬能力
- Node.js 逆向接入
- 媒体处理
- 强约束 CLI / contract / scorecard 风格测试

## 浏览器与动态页面

`RustSpider` 的浏览器层可用，但相对 `PySpider` 和 `GoSpider` 更薄一些。

公开描述建议聚焦：

- WebDriver 驱动浏览器
- 页面导航
- HTML 获取
- 标题获取
- 元素点击与输入
- 脚本执行
- 截图
- 滚动
- 自动化检测规避脚本

从仓库实现上看，它更偏：

- 稳定接口
- 清晰边界
- 通过外部 WebDriver 运行浏览器

## Node.js 逆向能力

`RustSpider` 的 `node_reverse` 客户端非常完整。

它支持：

- health check
- crypto analyze
- encrypt / decrypt
- JS execute
- AST analyze
- browser simulate
- function call
- anti-bot detect / profile
- fingerprint spoof
- TLS fingerprint
- Webpack analyze
- canvas fingerprint
- signature reverse

本地静态兜底分析也很深，能力面与 `GoSpider`、`JavaSpider`、`PySpider` 的增强版接近，包括：

- 算法识别
- 混淆 loader 识别
- runtime execution 需求判断
- AST dataflow 需求判断
- key source / key flow 分析
- reverse complexity 分级

## 工程能力

- 特性开关发布
- 强类型配置
- CLI 契约测试
- scorecard / contract 风格验证
- 适合做受控发布和生产运行

## 当前实战特点

如果只看文档能力，`RustSpider` 很强。

如果看动态逆向实操体验，它更依赖：

- 外部 WebDriver
- 明确配置
- 编译与运行环境

所以它更像：

- 稳定运行时
- 生产部署运行器
- 强约束的 crawler runtime

## 最适合的 GitHub 公开定位

- 面向高性能、强类型和可裁剪发布的 Rust 爬虫框架
- 具备完整的 Node 逆向接口和本地静态分析能力
- 适合重视稳定性、边界控制和生产运行的人
