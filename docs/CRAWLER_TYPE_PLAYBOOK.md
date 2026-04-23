# Crawler Type Playbook

Updated: 2026-04-23

This playbook documents the new shared crawler-type layer added on top of the normalized `JobSpec` surface.

## Goal

Improve coverage for modern site families without pretending one runtime or one selector strategy can handle every site.

The new layer focuses on:

- bootstrap JSON pages
- hydrated SPA pages
- infinite scroll lists
- e-commerce search/detail pages
- login-gated session pages

## New Crawler Types

| Crawler Type | Primary Runner | When to Use | Template |
| --- | --- | --- | --- |
| `api_bootstrap` | `http` | Useful data already exists in script tags or schema blocks | `examples/crawler-types/api-bootstrap-http.json` |
| `hydrated_spa` | `browser` | DOM is mostly empty until client hydration finishes | `examples/crawler-types/hydrated-spa-browser.json` |
| `infinite_scroll_listing` | `browser` | More content appears only after scrolling or load-more actions | `examples/crawler-types/infinite-scroll-browser.json` |
| `ecommerce_search` | `browser` | Dynamic catalog/search pages with price, SKU, and listing churn | `examples/crawler-types/ecommerce-search-browser.json` |
| `login_session` | `browser` | Content requires a session bootstrap before extraction | `examples/crawler-types/login-session-browser.json` |

## Practical Guidance

- Prefer embedded JSON and stable network payloads before brittle CSS selectors.
- Treat login, captcha, and challenge pages as session/bootstrap problems, not as plain extraction problems.
- Split list extraction from detail extraction so you can validate each stage independently.
- Save HTML, screenshot, and network artifacts together when tuning a site profile.

## Current Integration

The richer site profile is surfaced through:

- `python -m pyspider profile-site`
- `python -m pyspider scrapy plan-ai`
- `python -m pyspider scrapy scaffold-ai`

These commands now emit:

- `crawler_type`
- `runner_order`
- `strategy_hints`
- `job_templates`

## Constraint

This playbook improves coverage. It does not guarantee crawling of every site and it does not replace authorization, session handling, robots/ToS review, or challenge-page escalation.
