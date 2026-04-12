# Release Notes v1.0.0

发布日期：2026-04-10

## 摘要

这一版的重点不是新增单一框架功能，而是把四个爬虫框架从“能力存在明显缺口 / 占位实现 / 验证不完整”的状态，推进到“核心能力可验证、统一门禁可执行、可选外部联调已预留入口”的状态。

当前统一结论：

- 四框架完成度报告：`4 frameworks passed, 0 frameworks failed`
- 本地集成联调：`7 passed, 0 failed`
- 本地媒体黑盒验证：`2 passed, 0 failed`
- 发布就绪门禁：`3 required passed, 0 required failed`

## 本版亮点

### 1. 四框架核心缺口已补齐

- `gospider`
  - 修复 CSV 数据集导出
  - 修复 session 代理支持
  - 媒体 CLI 接通 YouTube / 优酷 / 腾讯 / 爱奇艺
  - 修复 HLS 相对分片 URL 解析缺陷

- `javaspider`
  - 修复主工程编译断点
  - `jsonPath()` 不再是 TODO
  - `aiExtract()` 从启发式升级为真实 AI + fallback 双轨
  - 补充 schema 驱动结构化 AI 提取
  - 提升 AI 结构化 JSON 解析能力

- `rustspider`
  - 补充 Cookie JSON 持久化
  - 2Captcha / Anti-Captcha 请求与轮询流程落地
  - 本地假服务端到端联调可跑通

- `pyspider`
  - `curl -> aiohttp` 转换不再是模板
  - checkpoint 支持 SQLite
  - `MultiMediaSpider` 提供默认通用多媒体提取实现

### 2. 验证体系从“零散命令”升级为统一入口

新增或强化的统一入口：

- `python generate_framework_completion_report.py --json --markdown-out CURRENT_FRAMEWORK_COMPLETION_REPORT.md`
- `python verify_local_integrations.py --json --markdown-out LOCAL_INTEGRATIONS_REPORT.md`
- `python verify_media_blackbox.py --json --markdown-out MEDIA_BLACKBOX_REPORT.md`
- `python verify_release_ready.py --json --markdown-out RELEASE_READINESS_REPORT.md`

### 3. 可选 live 验证入口已就绪

新增可选外部联调入口：

- `python verify_javaspider_ai_live.py --json`
- `python verify_rust_captcha_live.py --json`

设计原则：

- 未配置开关或 API key 时返回 `skipped`
- 不把默认本地验证状态打红
- 一旦配置完成即可直接进入真实外部联调

## 关键验证证据

### 框架级摘要

- `python verify_gospider_distributed_summary.py --json`
  - 结果：`4 passed, 0 failed`
- `python verify_javaspider_captcha_summary.py --json`
  - 结果：`5 passed, 0 failed`
- `python verify_pyspider_concurrency_summary.py --json`
  - 结果：`3 passed, 0 failed`
- `python verify_rust_browser_summary.py --json`
  - 结果：`4 passed, 0 failed`
- `python verify_rust_distributed_summary.py --json`
  - 结果：`2 passed, 0 failed`

### 本地集成

- `python verify_local_integrations.py --json`
  - 结果：`7 passed, 0 failed`

覆盖：

- Go 媒体 CLI + 爱奇艺提取器
- Java AI / selector 契约测试
- Rust 验证码本地联调
- Python 多媒体默认实现、checkpoint、curlconverter
- 本地媒体黑盒下载

### 黑盒媒体验证

- `python verify_media_blackbox.py --json`
  - 结果：`2 passed, 0 failed`

黑盒链路：

- `gospider media -platform iqiyi -download ...`
- `python -m pyspider download ...`

均通过本地 HTTP fixture 服务实际下载 `m3u8 + ts` 分片并校验最终产物内容。

### 发布门禁

- `python verify_release_ready.py --json`
  - 结果：`3 required passed, 0 required failed`

## 产物与报告

本版新增或更新的关键报告：

- [CURRENT_FRAMEWORK_COMPLETION_REPORT.md](C:/Users/Administrator/spider/CURRENT_FRAMEWORK_COMPLETION_REPORT.md)
- [LOCAL_INTEGRATIONS_REPORT.md](C:/Users/Administrator/spider/LOCAL_INTEGRATIONS_REPORT.md)
- [MEDIA_BLACKBOX_REPORT.md](C:/Users/Administrator/spider/MEDIA_BLACKBOX_REPORT.md)
- [RELEASE_READINESS_REPORT.md](C:/Users/Administrator/spider/RELEASE_READINESS_REPORT.md)

## 升级影响

这版主要是补齐和收敛，不是破坏式升级。

值得注意的变化：

- `gospider media` 不再只是演示命令，已经接上实际下载链路
- `javaspider` selector 层现在支持更强的 JSONPath / AI / schema 提取
- `pyspider` checkpoint 不再只支持 JSON
- `rustspider` 验证码流程不再是占位返回

## 仍建议深化的方向

- `gospider`
  - 继续提高站点级媒体解析与下载命中率

- `javaspider`
  - 继续增强 schema enforcement 与高层提取契约

- `pyspider`
  - 增加更多平台特化多媒体子类

- `rustspider`
  - 执行真实第三方验证码服务联调

## 建议发布命令

推荐发版前顺序：

```bash
python verify_release_ready.py --json --markdown-out RELEASE_READINESS_REPORT.md
python generate_framework_completion_report.py --json --markdown-out CURRENT_FRAMEWORK_COMPLETION_REPORT.md
python verify_local_integrations.py --json --markdown-out LOCAL_INTEGRATIONS_REPORT.md
python verify_media_blackbox.py --json --markdown-out MEDIA_BLACKBOX_REPORT.md
```

可选 live 验证：

```bash
python verify_javaspider_ai_live.py --json
python verify_rust_captcha_live.py --json
```
