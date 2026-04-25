# Latest Scenario Cases

Updated: 2026-04-24

This document gives source-aligned, practical cases for how the repository should be used today.

The goal is not to promise universal support. The goal is to show the best currently validated workflow per scenario.

---

## Case 1: Logged-In SPA with OTP/TOTP and Protected API Calls

### Problem

- site uses login form
- second factor is required
- content is delivered through XHR/GraphQL after login

### Best Current Path

1. Use `scrapy auth-capture` to create session assets
2. Use `scrapy auth-validate` against the target page
3. Run browser fetch / artifact capture
4. Inspect API calls or signed requests through browser/network artifacts
5. If request signing exists, run `node-reverse profile` and `analyze-crypto`

### Best Runtimes

- PySpider
- GoSpider
- RustSpider
- JavaSpider

### Why It Works

- session asset capture exists across the repo
- OTP/TOTP-oriented auth patterns are present in current source
- browser artifact capture plus reverse tooling gives a realistic follow-up path

---

## Case 2: GraphQL or Signed JSON API Behind Browser Shell

### Problem

- HTML is mostly a shell
- useful data arrives through GraphQL or signed JSON requests

### Best Current Path

1. Run browser fetch
2. Persist network/HAR artifacts
3. Run `node-reverse detect` / `profile`
4. If JS signing exists, use `analyze-crypto`, `ast`, or `webpack`
5. Rebuild the request contract from the discovered API flow

### Best Runtimes

- GoSpider for artifact-heavy browser collection
- PySpider for project scaffolding and follow-up extraction
- RustSpider if reverse/captcha complexity is high

### Why It Works

- this combines the strongest existing browser-artifact and reverse-analysis surfaces in the repo

---

## Case 3: Login + Cloudflare Turnstile + Protected Crawl

### Problem

- login required
- Turnstile challenge appears
- crawl needs persistent session after challenge

### Best Current Path

1. Run the target through the shared access-friction analyzer.
2. If `capability_plan.transport_order` recommends `browser-render`, run browser fetch with HTML, screenshot, storage, and network-summary artifacts enabled.
3. If `challenge_handoff.required` is true, pause for authorized human access instead of attempting automated bypass.
4. Persist storage state and cookies only after the challenge is cleared.
5. Validate with `auth-validate`.
6. Crawl with saved assets and the plan's throttle/retry budget.

### Best Runtime

- All four runtimes now expose the same access-friction report, challenge handoff, and capability plan.
- RustSpider still has the deepest challenge-field extraction in ultimate paths.

### Why It Works

- The shared report prevents blind retry loops and turns high-friction pages into a browser/artifact/session workflow with explicit stop conditions.

---

## Case 4: Video Page with Dynamic Player Data and Download Links

### Problem

- page is dynamic
- direct media URL is not obvious in static HTML
- useful data may be in player config, network logs, or HAR

### Best Current Path

1. Browser fetch the page
2. Save HTML + network + HAR artifacts
3. Use media tooling in artifact-driven mode where available
4. Fall back to parser + generic extraction only if artifact-driven parsing is insufficient

### Best Runtimes

- GoSpider
- PySpider

### Why It Works

- these two have the clearest artifact-to-media workflows in the repository

---

## Case 5: iframe-Embedded App

### Problem

- real content lives inside iframe(s)
- top-level HTML is mostly wrapper content

### Current State

- Java has explicit frame switching helpers
- Rust now has explicit browser-layer frame switching
- Go now has same-origin iframe helpers
- It is still not a normalized high-level scenario across all four runtimes

### Recommended Workaround

1. Use a real browser runtime, not reverse-assisted simulation
2. Enumerate iframe URLs explicitly
3. Treat each frame as a separate crawl target or workflow step
4. Persist artifacts per frame

### Best Runtime Today

- JavaSpider if you want the clearest long-lived in-repo frame-switching surface
- RustSpider if you want explicit browser-layer frame switching in the typed runtime
- GoSpider for same-origin iframe helper cases

---

## Case 6: Shadow DOM Application

### Problem

- content is rendered in nested shadow roots
- CSS/XPath against top-level DOM is insufficient

### Current State

- GoSpider and RustSpider now expose open-shadow-root helper paths
- Closed shadow roots and a unified cross-runtime scenario abstraction are still missing

### Recommended Workaround

1. Use a real browser runtime
2. Use the Go/Rust Shadow DOM helper path where available, or execute custom JavaScript elsewhere
3. Extract text/HTML at the browser layer
4. Treat the result as a browser artifact for downstream parsing

### Status

- This is now partial in Go/Rust, but not solved uniformly

---

## Case 7: Live Dashboard over WebSocket or SSE

### Problem

- page data is streamed continuously
- useful state never fully materializes in initial HTML

### Current State

- GoSpider now records CDP WebSocket frames and EventSource messages into realtime artifacts
- RustSpider now exposes an in-page WebSocket/EventSource collector for messages after installation
- Some encrypted modules can decrypt WebSocket payloads, but that is not the same as replaying the stream

### Recommended Workaround

1. Enable the Go realtime capture artifact or install the Rust realtime collector before triggering stream activity
2. Use external protocol capture if the target needs pre-navigation or service-worker-level traffic
3. Feed recovered payloads back into parser/research flows

### Status

- This is now partial in Go/Rust; replay and cross-runtime normalization remain gaps

---

## Case 8: Upload Form + Post-Upload Processing

### Problem

- crawler must submit a file before receiving the target result page or task output

### Current State

- JavaSpider: explicit file upload helper exists
- PySpider: Playwright browser layer exposes file input support
- GoSpider: browser layer now exposes upload-input support
- RustSpider: browser layer now exposes upload-input support

### Recommended Runtime

- Any of the four runtimes for simple upload-input cases
- Prefer JavaSpider or PySpider if the upload flow is mixed with richer browser/form automation today

### Status

- Partial repo coverage, not full parity

---

## Summary

The best currently validated scenario families are:

- logged-in crawl with persisted session assets
- protected SPA/API discovery via browser artifacts + reverse tooling
- challenge-heavy login with shared access-friction handoff and Rust-forward challenge-field extraction
- dynamic media extraction via browser artifacts

The clearest remaining hard gaps are:

- Shadow DOM
- generic iframe scenario normalization
- WebSocket/SSE capture
- WebAuthn / passkey login handling

## Related Docs

- [`CRAWL_SCENARIO_GAP_MATRIX.md`](CRAWL_SCENARIO_GAP_MATRIX.md)
- [`ACCESS_FRICTION_PLAYBOOK.md`](ACCESS_FRICTION_PLAYBOOK.md)
- [`FRAMEWORK_CAPABILITIES.md`](FRAMEWORK_CAPABILITIES.md)
- [`CRAWLER_TYPE_PLAYBOOK.md`](CRAWLER_TYPE_PLAYBOOK.md)
- [`SITE_PRESET_PLAYBOOK.md`](SITE_PRESET_PLAYBOOK.md)
