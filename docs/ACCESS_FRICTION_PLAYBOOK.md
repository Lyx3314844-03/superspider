# Access Friction Playbook

Updated: 2026-04-24

This document describes the shared high-friction crawl policy exposed by PySpider, GoSpider, RustSpider, and JavaSpider.

The goal is maximum compliant crawl reliability. The frameworks detect access friction, preserve evidence, slow down, upgrade to browser rendering when appropriate, reuse only authorized sessions, and stop when access is explicitly denied. They do not promise automated CAPTCHA cracking, forced bypass of risk controls, or access to private/login-gated content without authorization.

---

## Shared Report Fields

All four runtimes expose the same access-friction model:

| Field | Meaning |
| --- | --- |
| `level` | `none`, `low`, `medium`, or `high` friction classification |
| `signals` | Detected signals such as `captcha`, `rate-limited`, `managed-browser-challenge`, `auth-required`, `waf-vendor`, `risk-control`, or `request-blocked` |
| `recommended_actions` | Concrete actions such as `honor-retry-after`, `render-with-browser`, `persist-session-state`, `pause-for-human-access`, or `stop-or-seek-site-permission` |
| `retry_after_seconds` | Parsed `Retry-After` value when present |
| `should_upgrade_to_browser` | Whether the next compliant attempt should use browser rendering |
| `requires_human_access` | Whether an authorized human checkpoint is required before continuing |
| `challenge_handoff` | Human handoff instructions and required artifacts |
| `capability_plan` | Runtime plan for transport order, throttling, session handling, artifacts, retry budget, and stop conditions |
| `blocked` | Convenience boolean for `medium` or `high` friction |

---

## Capability Plan

The `capability_plan` field is the operator-facing plan for difficult targets:

| Subfield | Behavior |
| --- | --- |
| `mode` | Always `maximum-compliant` for this policy |
| `transport_order` | Starts with `http`; may add `browser-render`, `authorized-session-replay`, or `stop-until-permission` |
| `throttle` | Reduces high-friction crawls to single concurrency, honors `Retry-After`, and enforces a conservative delay floor |
| `session` | Persists browser storage/cookies, isolates sessions by site, and gates reuse behind authorized access when challenges appear |
| `artifacts` | Saves HTML, screenshot, cookies/storage state, network summary, and the friction report |
| `retry_budget` | Keeps retry count low for high-risk responses and zero for explicit blocks |
| `stop_conditions` | Stops on robots disallow, explicit access denial, or missing site permission |

High-risk responses use a conservative crawl-delay floor even when `Retry-After` is shorter. This is intentional: the plan favors not escalating blocks over maximizing request volume.

---

## Operational Flow

1. Try the configured HTTP path with normal robots and rate controls.
2. Analyze response status, headers, body text, title, and URL.
3. If access friction is medium/high, apply `capability_plan`.
4. Upgrade to browser rendering only when the plan recommends it.
5. If CAPTCHA, login, or risk-control challenge appears, pause for authorized human access and persist session state after completion.
6. Resume only with the saved authorized session assets.
7. Stop instead of retrying when robots disallow, the site explicitly denies access, or permission is missing.

---

## Runtime Entry Points

| Runtime | Primary implementation |
| --- | --- |
| PySpider | `pyspider.antibot.friction.analyze_access_friction` |
| GoSpider | `antibot.AnalyzeAccessFriction` |
| RustSpider | `rustspider::antibot::friction::analyze_access_friction` |
| JavaSpider | `com.javaspider.antibot.AccessFrictionAnalyzer` |

Browser challenge detection in the browser layers attaches this report under `friction_profile` where applicable.

HTTP downloaders now attach the same report to normal response objects:

| Runtime | HTTP result location |
| --- | --- |
| PySpider | `Response.meta["access_friction"]` |
| GoSpider | `Response.AccessFriction` |
| RustSpider | `Response.access_friction` |
| JavaSpider | `Page.getField("access_friction")` |

---

## Non-Goals

- No automated CAPTCHA cracking promises.
- No forced bypass of WAF/risk-control decisions.
- No use of unauthorized private data.
- No recommendation to ignore robots.txt, site terms, or explicit access denial.

For capability comparison, also see:

- [`FRAMEWORK_CAPABILITIES.md`](FRAMEWORK_CAPABILITIES.md)
- [`FRAMEWORK_CAPABILITY_MATRIX.md`](FRAMEWORK_CAPABILITY_MATRIX.md)
- [`CRAWL_SCENARIO_GAP_MATRIX.md`](CRAWL_SCENARIO_GAP_MATRIX.md)
- [`LATEST_SCENARIO_CASES.md`](LATEST_SCENARIO_CASES.md)
