# Crawl Scenario Gap Matrix

Updated: 2026-04-24

This document answers a practical question:

What real crawling scenarios are still not uniformly covered by the four runtimes?

Legend:

- `Good` = clearly supported through source-visible runtime paths
- `Partial` = possible, but not first-class or not parity-complete
- `Gap` = no clear first-class support in current source

## Scenario Matrix

| Scenario | PySpider | GoSpider | RustSpider | JavaSpider | Notes |
| --- | --- | --- | --- | --- | --- |
| Logged-in crawl with saved session assets | Good | Good | Good | Good | `scrapy auth-capture` / `auth-validate` style flows are present across the repo |
| Password + OTP/TOTP login flow assistance | Good | Good | Good | Good | Source contains OTP/TOTP-oriented auth action templates |
| Turnstile / reCAPTCHA / hCaptcha recovery | Good | Good | Good | Good | Maturest in Rust ultimate / anti-bot paths |
| Access-friction classification and compliant recovery plan | Good | Good | Good | Good | All four runtimes expose shared friction reports with challenge handoff and capability plans |
| SPA/XHR/API discovery from browser artifacts | Good | Good | Good | Good | Browser artifacts + reverse tooling give workable coverage |
| Signed API / JS crypto reconstruction | Good | Good | Good | Good | Strong NodeReverse and encrypted-module coverage |
| Infinite scroll / dynamic pagination | Good | Good | Good | Good | Browser/workflow layers expose scroll and artifact capture |
| Generic iframe traversal as a first-class crawler feature | Partial | Partial | Partial | Partial | Java and Rust have explicit frame switching; Go now has same-origin iframe helpers, but this is still not a unified high-level scenario layer |
| Generic Shadow DOM traversal / extraction | Gap | Partial | Partial | Gap | Go/Rust now expose open-shadow-root helper paths; closed roots and unified scenario orchestration remain gaps |
| Generic WebSocket stream capture | Gap | Partial | Partial | Gap | Go records CDP WebSocket frames; Rust exposes an in-page WebSocket hook for messages after installation |
| Generic SSE / EventSource stream capture | Gap | Partial | Partial | Gap | Go records CDP EventSource messages; Rust exposes an in-page EventSource hook for messages after installation |
| File upload form automation | Good | Good | Good | Good | Py has `set_input_files`; Java has explicit upload helper; Go and Rust now expose browser-layer upload methods |
| WebAuthn / passkey / hardware-key login | Gap | Gap | Gap | Gap | No first-class WebAuthn/passkey runtime support surfaced |
| Mobile-app private API signing / protobuf / app attestation | Partial | Partial | Partial | Partial | Reverse tooling helps, but no unified first-class scenario workflow |
| Shadow DOM inside iframe + login + challenge combo | Gap | Partial | Partial | Gap | Raw helpers exist in Go/Rust, but the unified high-level scenario workflow is still missing |
| Live dashboard replay driven by WS/SSE + auth | Gap | Partial | Partial | Gap | Go/Rust now have realtime collectors, but replay/orchestration remains incomplete |

## Highest-Priority Shared Gaps

The highest-priority remaining shared gaps are:

1. Unified Shadow DOM traversal across all runtimes
2. Generic iframe traversal as a normalized scenario
3. Generic WebSocket / SSE replay and artifact normalization
4. WebAuthn / passkey-oriented login automation

## Important Clarification

There is a difference between:

- decrypting a WebSocket payload after you already have it
- and having a first-class runtime surface that captures WebSocket traffic from the page

Go now exposes CDP-level WebSocket/SSE capture and Rust exposes an in-page collector, but this is still not the same as a full replay-capable streaming workflow across all runtimes.

Likewise, there is a difference between:

- reverse-assisted browser simulation
- and a real browser session that navigates into frames, Shadow DOM, and interactive challenge surfaces

The gap matrix is based on that stricter distinction.

## Recommended Prioritization

If you want to improve real scenario coverage with the highest payoff:

1. Add normalized iframe traversal support above the raw browser layer
2. Extend Shadow DOM helpers to Py/Java and normalize output artifacts
3. Add WebSocket/SSE replay workflow surfaces above the raw collectors
4. Add WebAuthn/passkey-specific login handling

CAPTCHA, login challenge, and risk-control flows are no longer treated as generic retry problems. Use the shared access-friction report to decide whether to slow down, render with a browser, pause for authorized human access, persist session state, or stop.

## Related Docs

- [`LATEST_SCENARIO_CASES.md`](LATEST_SCENARIO_CASES.md)
- [`ACCESS_FRICTION_PLAYBOOK.md`](ACCESS_FRICTION_PLAYBOOK.md)
- [`FRAMEWORK_CAPABILITIES.md`](FRAMEWORK_CAPABILITIES.md)
- [`CRAWLER_TYPE_PLAYBOOK.md`](CRAWLER_TYPE_PLAYBOOK.md)
- [`SITE_PRESET_PLAYBOOK.md`](SITE_PRESET_PLAYBOOK.md)
