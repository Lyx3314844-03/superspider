# Quality Policy

质量策略文件是 [quality-thresholds.json](C:\Users\Administrator\spider\quality-thresholds.json)。

## Profiles

- `dev`: 开发期最宽松，主要用于本地快速迭代。
- `default`: 日常 CI 使用，要求功能与证据链稳定，但允许策略定义的轻量告警。
- `strict`: 发布与打 tag 使用，必须满足发布红线。

## Release Gate

- 日常聚合工作流使用 `default`。
- 发布工作流与发布脚本使用 `strict`。
- 任何 profile 变更都必须重新生成：
  - `verify_quality_thresholds.py`
  - `verify_replay_trends.py`
  - `generate_framework_scorecard.py`

## Change Control

修改 `quality-thresholds.json` 时，必须同时完成以下动作：

1. 更新 [quality-policy-governance.json](C:\Users\Administrator\spider\quality-policy-governance.json) 里的 `policy_digest`
2. 在本文件中更新变更说明
3. 运行 `verify_quality_policy_governance.py --json`
4. 运行 `verify_quality_thresholds.py --json --profile strict`

## Digest Registry

当前生效策略 digest 由 [quality-policy-governance.json](C:\Users\Administrator\spider\quality-policy-governance.json) 管理。

## Current Notes

- `strict` profile 代表当前发布基线。
- Rust 的质量红线已经提升到 `distributed=verified` 和 `test_status=moderate`。
