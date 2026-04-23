# Site Preset Playbook

Updated: 2026-04-23

This playbook maps common Chinese marketplace and social-commerce domains to starter presets.

## Site Families

| Site Family | Domains | Preset |
| --- | --- | --- |
| `jd` | `jd.com`, `3.cn` | `examples/site-presets/jd-search-browser.json`, `examples/site-presets/jd-detail-browser.json` |
| `taobao` | `taobao.com` | `examples/site-presets/taobao-search-browser.json`, `examples/site-presets/taobao-detail-browser.json` |
| `tmall` | `tmall.com` | `examples/site-presets/tmall-search-browser.json` |
| `pinduoduo` | `pinduoduo.com`, `yangkeduo.com` | `examples/site-presets/pinduoduo-search-browser.json` |
| `xiaohongshu` | `xiaohongshu.com`, `xhslink.com` | `examples/site-presets/xiaohongshu-feed-browser.json` |
| `douyin-shop` | `douyin.com`, `jinritemai.com` | `examples/site-presets/douyin-shop-browser.json` |

## Purpose

These presets are not site-specific guarantees. They are ready-to-edit starting points for:

- target URL shape
- domain allowlists
- browser capture defaults
- first-pass field extraction

## Recommended Flow

1. Run `profile-site` on the target URL or captured HTML.
2. Use `site_family`, `crawler_type`, `runner_order`, and `job_templates` from the profile output.
3. Start from the matching preset, then tune selectors and waits against current artifacts.
