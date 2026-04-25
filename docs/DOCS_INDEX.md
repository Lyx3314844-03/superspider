# SuperSpider Documentation Index

Updated: 2026-04-24

This is the canonical GitHub-facing docs entrypoint for SuperSpider.

The older hidden-capability and defect-audit mirror docs were retired. Their useful content now lives in the capability summary, capability matrix, scenario docs, and starter playbooks listed below.

---

## Start Here

1. `README.md` — project overview, runtime comparison, install matrix, and release-facing summary
2. `docs/FRAMEWORK_CAPABILITIES.md` — detailed per-runtime capability descriptions and caveats
3. `docs/FRAMEWORK_CAPABILITY_MATRIX.md` — side-by-side capability coverage tables
4. `docs/ACCESS_FRICTION_PLAYBOOK.md` — high-friction crawl policy, challenge handoff, and compliant recovery plan
5. `docs/CRAWLER_SELECTION_CONTRACT.md` — shared crawler-selection payload used by all four runtimes
6. `docs/FOUR_RUNTIME_HEALTH_REPORT.md` — current compile, dependency, and test status for JavaSpider, GoSpider, RustSpider, and PySpider
7. `docs/SUPERSPIDER_INSTALLS.md` — aggregate and per-runtime install instructions plus verification steps for Windows, Linux, and macOS
8. `docs/DOCS_INDEX.md` — this file; the recommended reading order and canonical doc map

---

## Capability Docs

| Document | Description |
| --- | --- |
| `docs/FRAMEWORK_CAPABILITIES.md` | Source-aligned capability summary for PySpider, GoSpider, RustSpider, and JavaSpider |
| `docs/FRAMEWORK_CAPABILITY_MATRIX.md` | Full capability comparison tables across the four runtimes |
| `docs/ACCESS_FRICTION_PLAYBOOK.md` | Shared high-friction crawl model, `capability_plan`, human handoff, and stop conditions |
| `docs/CRAWLER_SELECTION_CONTRACT.md` | Shared `CrawlerSelection` contract, top-level fields, compatibility rules, and cross-runtime expectations |
| `docs/FOUR_RUNTIME_HEALTH_REPORT.md` | Current compile, dependency, and test verification snapshot for the four runtime directories |
| `docs/CRAWL_SCENARIO_GAP_MATRIX.md` | Practical crawl scenarios that are still partial, caveated, or missing |
| `docs/LATEST_SCENARIO_CASES.md` | Current scenario playbooks and recommended runtime picks |
| `MEDIA_PARITY_REPORT.md` | Media platform coverage evidence and verification snapshot |

---

## Starter Assets

| Document | Description |
| --- | --- |
| `docs/CRAWLER_TYPE_PLAYBOOK.md` | Shared crawler-type guidance, runner order, and template usage |
| `docs/SITE_PRESET_PLAYBOOK.md` | Domain-oriented starter presets for high-frequency site families |
| `examples/crawler-types/README.md` | Template pack for hydrated SPA, bootstrap JSON, infinite scroll, ecommerce search, and login-session flows |
| `examples/crawler-selection/ecommerce-search-selection.json` | Golden crawler-selection payload for ecommerce search/listing dispatch |
| `examples/crawler-selection/ecommerce-search-input.html` | Shared HTML fixture used by all four runtime selector tests |
| `examples/site-presets/README.md` | Domain starter presets for JD, Taobao, Tmall, Pinduoduo, Xiaohongshu, and Douyin Shop |
| `examples/class-kits/README.md` | Reusable spider class templates for all four runtimes, including ecommerce wrappers and browser companions |

---

## Usage Guides

| Document | Description |
| --- | --- |
| `ADVANCED_USAGE_GUIDE.md` | Advanced crawling scenarios across WAF bypass, proxy, distributed, and AI flows |
| `ENCRYPTED_SITE_CRAWLING_GUIDE.md` | JS-encrypted and signed-site crawling guidance |
| `NODE_REVERSE_INTEGRATION_GUIDE.md` | NodeReverse integration, browser simulation boundaries, and crypto tooling |
| `ULTIMATE_ENHANCEMENT_GUIDE.md` | Full capability enhancement reference and runtime layering guidance |
| `PUBLISH_GUIDE.md` | GitHub publishing flow for this repository |
| `scripts/windows/verify-superspider.bat` | Windows stable verification gate for JavaSpider, GoSpider, RustSpider, PySpider, and crawler-selection contract checks |
| `scripts/linux/verify-superspider.sh` | Linux stable verification gate for JavaSpider, GoSpider, RustSpider, PySpider, and crawler-selection contract checks |
| `scripts/macos/verify-superspider.sh` | macOS stable verification gate for JavaSpider, GoSpider, RustSpider, PySpider, and crawler-selection contract checks |

---

## Release Docs

| Document | Description |
| --- | --- |
| `PUBLISH_RELEASE_STATUS.md` | Current publish-time verification snapshot |
| `docs/RELEASE_NOTES_v1.0.0.md` | v1.0.0 release notes |
| `docs/GITHUB_RELEASE_TEMPLATE.md` | GitHub release body template |
| `CHANGELOG.md` | Version history |
| `CONTRIBUTING.md` | Contribution guide |

---

## Per-Runtime READMEs

| File | Runtime |
| --- | --- |
| `pyspider/README.md` | Python-first runtime surface |
| `gospider/README.md` | Go binary/runtime surface |
| `rustspider/README.md` | Rust feature-gated/runtime surface |
| `javaspider/README.md` | Java Maven/JAR/runtime surface |

---
