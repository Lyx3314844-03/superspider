# Crawler Selection Contract

`CrawlerSelection` is the shared decision payload used by JavaSpider, GoSpider, RustSpider, and PySpider to choose the best crawler path for a URL and optional HTML snapshot.

The contract is intentionally small and serializable. Framework internals may expose language-native classes, but cross-runtime control planes should exchange these snake_case fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `scenario` | string | Human-readable crawl scenario, for example `ecommerce_listing`, `static_detail`, or `authenticated_session`. |
| `crawler_type` | string | Normalized crawler type from site profiling, for example `ecommerce_search`, `hydrated_spa`, or `api_bootstrap`. |
| `recommended_runner` | string | First runner to try, usually `http` or `browser`. |
| `runner_order` | string array | Ordered fallback chain. |
| `site_family` | string | Domain family hint such as `jd`, `taobao`, `tmall`, `pinduoduo`, `xiaohongshu`, `douyin-shop`, or `generic`. |
| `risk_level` | string | `low`, `medium`, or `high` based on forms, login, captcha, hydration, and GraphQL/API signals. |
| `capabilities` | string array | Required runtime capabilities such as `browser_rendering`, `commerce_fields`, `scroll_automation`, or `session_cookies`. |
| `strategy_hints` | string array | Operator guidance inherited from the site profile. |
| `job_templates` | string array | Starter JobSpec/template paths for this scenario. |
| `fallback_plan` | string array | Ordered recovery path when the first runner is empty or blocked. |
| `stop_conditions` | string array | Explicit stopping rules for lists, infinite scroll, login, and detail pages. |
| `confidence` | number | Heuristic confidence from `0.2` to `0.95`. |
| `reason_codes` | string array | Auditable reasons such as `crawler_type:ecommerce_search` and `signal:has_price`. |
| `profile` | object | Full source `SiteProfile` for advanced consumers. |

## Compatibility Rules

- Producers must keep the field names above stable.
- Consumers must ignore unknown extra fields.
- `recommended_runner` must equal `runner_order[0]` when `runner_order` is not empty.
- High-risk pages should be treated as evidence/handoff workflows, not silent bypass attempts.
- `profile` may contain language-specific object formatting, but top-level fields must remain cross-runtime stable.
