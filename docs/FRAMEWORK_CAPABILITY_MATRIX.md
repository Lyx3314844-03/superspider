# SuperSpider Framework Capability Matrix

Updated: 2026-04-25

Legend:

- `I` = Implemented
- `C` = Conditional
- `F` = Fallback-prone
- `B` = Implemented, but with important boundary/caveat

## Core Runtime Matrix

| Capability | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Shared `config init` / contract scaffolding | I | I | I | I |
| Unified CLI runtime surface | I | I | I | I |
| Browser tooling subcommands (`fetch` / `trace` / `mock` / `codegen`) | I | I | I | I |
| Site profiling / crawler-type hints | I | I | I | I |
| Crawler-type / site-preset starter assets | I | I | I | I |
| Shared class kits | I | I | I | I |
| Native ecommerce crawler classes / browser companions | I | I | I | I |
| Scrapy/project-style authoring | I | I | I | I |
| Web/API control plane | I | I | I | I |
| Jobdir / HTTP cache / console / audit | I | I | I | I |
| Media parsing/downloading | I | I | I | I |
| NodeReverse integration | C | C | C | C |
| Distributed execution paths | I | I | I | I |
| Artifact store / artifact refs | I | I | I | I |
| Graph extraction | I | I | I | I |
| Research runtime | I | I | I | I |

## AI Matrix

| Capability | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Heuristic extraction mode | I | I | I | I |
| LLM-backed extraction | C | C | C | C |
| Structured/schema extraction | I | C | C | C |
| Few-shot prompting support | C | C | C | C |
| AI CLI can silently degrade | F | F | F | C |

Notes:

- `gospider`, `rustspider`, and `pyspider` have explicit heuristic-fallback AI CLI behavior.
- JavaSpider supports real AI integration, but media, solver, and parser fallback behavior still means users should not assume every path is strongly constrained.

## Browser and Simulation Matrix

| Capability | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Real browser runtime | I | I | I | I |
| Shared Node Playwright helper | I | I | I | I |
| Screenshot / DOM / network artifacts | I | I | I | I |
| HAR capture | C | I | C | C |
| Browser pool / session reuse | I | I | I | I |
| Upload-input browser automation | I | I | I | I |
| XPath/CSS locator analysis and extraction class | I | I | I | I |
| DevTools-style element snapshot and node reverse hints | I | I | I | I |
| Realtime WebSocket / SSE capture | Gap | Partial | Partial | Gap |
| Open Shadow DOM helper paths | Gap | Partial | Partial | Gap |
| Reverse-assisted browser simulation | B | B | B | B |

Notes:

- In all four runtimes, some `simulate browser` paths are not equivalent to opening a real browser session.
- These are better described as reverse-assisted browser emulation or fingerprint simulation.
- GoSpider, RustSpider, and JavaSpider expose native-process Playwright adapters backed by `tools/playwright_fetch.mjs`; live use requires Node.js, npm `playwright`, and installed browser binaries.

## Anti-Bot Matrix

| Capability | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| UA / header rotation | I | I | I | I |
| Night mode / quiet hours | I | I | I | I |
| Captcha helper surfaces | I | I | I | I |
| External captcha provider integration | C | C | C | C |
| TLS / fingerprint helper logic | I | I | I | I |
| Anti-bot vendor profiling | C | I | I | C |
| Cloudflare / Akamai handling | I | I | I | I |
| Access-friction classifier | I | I | I | I |
| `challenge_handoff` for CAPTCHA/login/risk-control | I | I | I | I |
| `capability_plan` with browser upgrade, throttle, artifacts, retry budget, stop conditions | I | I | I | I |
| Slider CAPTCHA / JS signature / fingerprint-required classification | I | I | I | I |

Notes:

- The access-friction model is a compliant recovery and evidence policy. It does not promise automated CAPTCHA cracking, forced risk-control bypass, or access to unauthorized private content.
- High-risk responses use conservative throttling and low retry budgets by default.

## Storage / Queue / Control Matrix

| Capability | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Checkpoint manager | I | I | I | I |
| Incremental crawling | I | I | I | I |
| Session pool contract | I | I | I | I |
| Shared auth asset paths (`storage_state_file` / `cookies_file` / `auth_file`) | I | I | I | I |
| Autoscaled/frontier contract | I | I | I | I |
| Redis-backed queue/runtime | I | I | I | I |
| RabbitMQ/Kafka paths | C | C | C | C |
| Storage backends beyond local file | C | C | C | C |

## Hard Scenario Gaps

| Scenario | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Shadow DOM traversal | Gap | Partial | Partial | Gap |
| First-class WebSocket capture | Gap | Partial | Partial | Gap |
| First-class SSE capture | Gap | Partial | Partial | Gap |
| iframe scenario normalization | Partial | Partial | Partial | Partial |
| WebAuthn / passkey login automation | Gap | Gap | Gap | Gap |

## Best-Fit Matrix

| Need | Recommended Runtime |
| --- | --- |
| AI-assisted project generation and Python-side flexibility | PySpider |
| Binary deployment, concurrency, and artifact-rich operations | GoSpider |
| Feature-gated production delivery and typed control surfaces | RustSpider |
| Selenium workflows, audit-conscious JVM delivery, enterprise Java integration | JavaSpider |

## Verification Snapshot

| Runtime | Checked command(s) | Result |
| --- | --- | --- |
| PySpider | `python -m pytest tests\test_access_friction.py tests\test_locator_analyzer.py tests\test_super_framework.py tests\test_api_server.py tests\test_core_spider.py tests\test_downloader.py -q` | Pass, 40 tests |
| GoSpider | `go test ./...` | Pass |
| RustSpider | `cargo test --quiet --lib`; `cargo test --quiet --test access_friction` | Pass on targeted library/access-friction slices |
| JavaSpider | `mvn -q test`; `mvn -q -Dtest=HtmlSelectorContractTest test` | Pass |

For related docs, use the docs together:

- [`FRAMEWORK_CAPABILITIES.md`](FRAMEWORK_CAPABILITIES.md)
- [`ACCESS_FRICTION_PLAYBOOK.md`](ACCESS_FRICTION_PLAYBOOK.md)
- [`CRAWL_SCENARIO_GAP_MATRIX.md`](CRAWL_SCENARIO_GAP_MATRIX.md)
- [`LATEST_SCENARIO_CASES.md`](LATEST_SCENARIO_CASES.md)
- [`CRAWLER_TYPE_PLAYBOOK.md`](CRAWLER_TYPE_PLAYBOOK.md)
- [`SITE_PRESET_PLAYBOOK.md`](SITE_PRESET_PLAYBOOK.md)
