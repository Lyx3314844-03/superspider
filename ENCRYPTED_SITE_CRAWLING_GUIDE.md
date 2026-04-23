# Encrypted Site Crawling Guide

Updated: 2026-04-21

This guide explains how encrypted-site support really works across the four runtimes.

The practical model is:

1. fetch page or protected response
2. inspect crypto / anti-bot / obfuscation signals
3. call reverse-assisted tooling when needed
4. reconstruct request parameters, classify risk, or continue with a stronger runtime path

Do not assume encrypted crawling means every runtime can fully reproduce a browser session by itself.

---

## 1. What Counts as an Encrypted Site Here

In this repository, encrypted/protected targets usually involve one or more of:

- JS-generated request signatures
- browser-side token generation
- obfuscated or packed JavaScript
- anti-bot fingerprint checks
- captcha or challenge gating
- encrypted API payloads or encrypted parameter assembly

All four runtimes have encrypted-related modules, but they are not identical in depth.

---

## 2. Current Source-Aligned Pattern

Across the repo, encrypted crawling support usually combines:

- local signal detection
- crypto family detection
- NodeReverse service calls
- optional browser or browser-like simulation
- extraction/reporting/checkpoint output

This is best thought of as:

- reverse-assisted protected-request reconstruction

not:

- universal automatic bypass

---

## 3. Runtime Notes

### PySpider

PySpider has encrypted modules and reverse-aware fetch paths.

Important caveat:

- some encrypted/browser-like paths still rely on reverse-service simulation rather than a real browser session

### GoSpider

GoSpider combines encrypted crawling with strong runtime/control-plane integration.

Important caveat:

- some higher-level browser-simulation steps in protected flows are reverse-assisted emulation, not full browser automation

### RustSpider

RustSpider has some of the deepest protected-flow logic in the repo:

- encrypted crawler
- advanced captcha recovery
- reverse-assisted browser/fingerprint/TLS/canvas flows

Important caveat:

- reverse-assisted simulation is still not the same thing as a live browser session

### JavaSpider

JavaSpider combines encrypted modules, workflow/browser tooling, and reverse service integration.

Important caveat:

- the presence of Selenium elsewhere in the runtime should not be taken to mean that every encrypted or ultimate stage is Selenium-backed

---

## 4. Practical Workflow

For a protected target, the safest sequence is:

1. Run `profile-site` or `node-reverse detect/profile`
2. Inspect whether the site shows crypto, anti-bot, or challenge signals
3. If JS is involved, run `node-reverse analyze-crypto`, `ast`, or `webpack`
4. If fingerprinting is involved, run `fingerprint-spoof`, `tls-fingerprint`, `canvas-fingerprint`
5. If the site is still browser-heavy, collect real browser artifacts separately
6. Only then run encrypted or ultimate paths

This sequence gives you much better evidence than starting with the heaviest path first.

---

## 5. What to Watch For

### Good signs

- crypto families detected
- anti-bot profile returned with usable signals
- reverse service healthy
- browser artifacts captured separately when needed

### Risk signs

- AI or browser paths returning only fallback-style output
- reverse service unavailable
- challenge-heavy pages with only simulation and no real browser capture
- docs or examples assuming public library APIs that are not present in the current repo

---

## 6. Recommended Documentation Language

When describing encrypted crawling support externally, use:

- `encrypted-site support`
- `reverse-assisted request reconstruction`
- `protected-flow analysis`
- `reverse-assisted browser emulation`

Avoid:

- `fully automatic bypass`
- `guaranteed decryption`
- `real browser execution` unless that specific path is actually using the runtime's browser module

---

## 7. Related Docs

- [`NODE_REVERSE_INTEGRATION_GUIDE.md`](NODE_REVERSE_INTEGRATION_GUIDE.md)
- [`ADVANCED_USAGE_GUIDE.md`](ADVANCED_USAGE_GUIDE.md)
- [`ULTIMATE_ENHANCEMENT_GUIDE.md`](ULTIMATE_ENHANCEMENT_GUIDE.md)
- [`docs/FRAMEWORK_CAPABILITIES.md`](docs/FRAMEWORK_CAPABILITIES.md)
- [`docs/FRAMEWORK_CAPABILITY_MATRIX.md`](docs/FRAMEWORK_CAPABILITY_MATRIX.md)
