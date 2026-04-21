# 四个框架的共享能力目录

这个文档用来统一描述四个框架对外可以公开发布的能力边界。

## 1. 基础抓取能力

- HTTP / HTTPS 抓取
- GET / POST / 自定义请求
- Header / Cookie / Session 管理
- 超时、重试、退避
- 链接提取
- 深度控制
- 去重
- 任务调度

## 2. 页面解析能力

- HTML 解析
- CSS Selector
- XPath
- JSON 提取
- 正则提取
- 文本提取
- 结构化字段抽取

## 3. 动态页面能力

- 浏览器驱动
- 页面导航
- JavaScript 执行
- 元素点击
- 表单填写
- 页面滚动
- 截图
- HTML 快照

## 4. 浏览器伪装与反爬能力

- User-Agent 伪装
- 浏览器指纹伪装
- TLS 指纹相关能力
- Cookie / 会话伪装
- anti-bot 检测
- anti-bot 画像
- challenge 风险识别

## 5. Node.js 逆向能力

- crypto analyze
- encrypt / decrypt
- execute js
- AST analyze
- function call
- browser simulate
- Webpack analyze
- signature reverse
- canvas fingerprint
- fingerprint spoof
- TLS fingerprint

## 6. 加密与签名处理能力

- 对称加密识别
- 非对称加密识别
- 哈希 / HMAC 识别
- KDF 识别
- JWT / 签名类逻辑识别
- WebCrypto 识别
- 动态密钥来源识别
- key flow 分析
- obfuscation loader 识别

## 7. 媒体与视频能力

- HLS / `m3u8`
- DASH / `mpd`
- FFmpeg 协作
- DRM 检测
- 平台解析
- 视频资源下载链路

## 8. 平台支持能力

- YouTube
- Bilibili
- IQIYI
- Tencent Video
- Youku
- Douyin

## 9. 数据能力

- JSON / JSONL 导出
- 结果存储
- 数据集输出
- 表格化输出
- 处理管道

## 10. 分布式与运行时能力

- worker / node 运行
- 分布式任务
- 队列 / 节点发现
- 服务化执行
- 长任务运行

## 11. AI 与增强能力

- AI 提取
- 摘要
- 实体识别
- 研究型输出
- 智能抽取

## 12. 工程能力

- CLI
- 配置化运行
- 项目化运行
- 审计
- API / Web 控制台
- 合约测试 / 能力验证

## GitHub 上的建议表达

公开发布时，建议把这四个框架描述为：

- 四种语言实现的 crawler runtime 套件
- 覆盖网页抓取、动态页面、反爬、Node 逆向、媒体解析和工程化交付
- 每个运行时定位不同，但都覆盖完整爬虫生命周期
