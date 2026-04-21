# SuperSpider Framework Capability Matrix

Updated: 2026-04-21

Legend:

- `I` = Implemented
- `C` = Conditional
- `F` = Fallback-prone
- `B` = Implemented, but with important boundary/caveat

## Core Runtime Matrix

| Capability | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Unified CLI runtime surface | I | I | I | I |
| Browser tooling subcommands | I | I | I | I |
| Scrapy/project-style authoring | I | I | I | I |
| Web/API control plane | I | I | I | I |
| Audit / console / control-plane tools | I | I | I | I |
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
| Screenshot / DOM / network artifacts | I | I | I | I |
| HAR capture | C | I | C | C |
| Browser pool / session reuse | I | I | I | I |
| Upload-input browser automation | I | I | I | I |
| Reverse-assisted browser simulation | B | B | B | B |

Notes:

- In all four runtimes, some `simulate browser` paths are not equivalent to opening a real browser session.
- These are better described as reverse-assisted browser emulation or fingerprint simulation.

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

## Storage / Queue / Control Matrix

| Capability | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Checkpoint manager | I | I | I | I |
| Incremental crawling | I | I | I | I |
| Session pool contract | I | I | I | I |
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

## Repo Hygiene / Maturity Signals

| Signal | PySpider | GoSpider | RustSpider | JavaSpider |
| --- | --- | --- | --- | --- |
| Contract/scorecard-heavy testing | C | C | I | C |
| Compatibility fallback layers in runtime code | I | I | I | I |
| Known stale or misleading repo files | C | B | C | C |
| Failure semantics consistent across major modules | C | C | C | B |

Notes:

- GoSpider currently has the clearest repo-hygiene issue because `monitor.go.corrupted` and `monitor.go.original` remain in-tree.
- JavaSpider has a notable consistency issue in `CaptchaSolver`, where failure paths mix `null` returns and exceptions.

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
| PySpider | `pytest -q tests/test_smoke.py tests/test_dependencies.py tests/test_cli.py -x` | Pass |
| GoSpider | `go test ./...` | Pass |
| RustSpider | `cargo test --quiet --lib`; `cargo test --quiet --test readme_scorecard`; `cargo test --quiet --test preflight_scorecard` | Pass on targeted slices |
| JavaSpider | `mvn -q -DskipTests package`; `mvn -q "-Dtest=SpiderRuntimeContractsTest,HtmlParserXPathContractTest,ReadmeContractTest" test` | Pass |

For detailed caveats, use the docs together:

- [`FRAMEWORK_CAPABILITIES.md`](FRAMEWORK_CAPABILITIES.md)
- [`../HIDDEN_CAPABILITIES_REPORT.md`](../HIDDEN_CAPABILITIES_REPORT.md)
- [`../FRAMEWORK_DEFECT_AUDIT.md`](../FRAMEWORK_DEFECT_AUDIT.md)
