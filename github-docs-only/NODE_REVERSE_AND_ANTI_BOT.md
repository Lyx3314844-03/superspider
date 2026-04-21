# Node 逆向与反爬能力

## 这四个框架的共同点

四个框架都不是完全独立发明了一套不同的 Node.js 逆向体系。

更准确地说：

- 四个框架都暴露了自己的 `node_reverse` 客户端
- 四个框架都面向同一类接口能力
- 四个框架都具备本地静态分析兜底
- 真正的差异在浏览器执行链、CLI 入口、工程交付形态

## 共享的 Node 逆向能力面

四个框架公开可描述的能力包括：

- `health`
- `crypto analyze`
- `encrypt`
- `decrypt`
- `execute js`
- `ast analyze`
- `function call`
- `browser simulate`
- `anti-bot detect`
- `anti-bot profile`
- `fingerprint spoof`
- `tls fingerprint`
- `canvas fingerprint`
- `webpack analyze`
- `signature reverse`

## 本地静态分析覆盖的重点

四个框架当前文档和实现都覆盖了较强的本地静态启发式分析。

典型识别项包括：

- `CryptoJS`
- Node `crypto`
- `WebCrypto`
- `Forge`
- `SJCL`
- `sm-crypto`
- `JSEncrypt`
- `jsrsasign`
- `tweetnacl`
- `elliptic`
- `sodium`

## 可识别的问题类型

- 对称加密
- 非对称加密
- 哈希
- HMAC
- KDF
- Base64 / 编码
- JWT / 签名
- WebCrypto 调用
- 混淆加载器
- Webpack loader
- anti-debug
- 动态密钥来源
- 动态算法选择
- key flow 候选链路

## 反爬能力面

四个框架共同覆盖：

- User-Agent 伪装
- TLS 指纹相关能力
- 浏览器指纹相关能力
- anti-bot 特征检测
- anti-bot 画像
- 请求蓝图生成
- challenge / block 风险识别

## 实战强弱差异

如果只看“接口列表”，四个框架都很强。

如果看真实操作体验：

- `PySpider` 最适合把逆向和浏览器执行串起来
- `GoSpider` 最适合用 Chrome/CDP 做工程化动态跟踪
- `JavaSpider` 接口完整，适合做 Java 工作流集成
- `RustSpider` 接口完整，但动态执行更依赖外部 WebDriver 环境

## GitHub 上建议如何描述

公开描述时建议分成两层：

### 第一层：统一能力面

- 四个框架都具备 Node.js 逆向接入能力
- 都支持加密分析、AST、Webpack、签名逆向、浏览器模拟、反爬画像

### 第二层：运行时差异

- `PySpider`：动态站和 Playwright 体验最完整
- `GoSpider`：CDP/Chrome 工程型调试最强
- `RustSpider`：接口完整、发布稳定、运行边界清晰
- `JavaSpider`：企业 Java 集成和浏览器工作流更适合
