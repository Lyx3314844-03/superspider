# Node Reverse Integration Guide

Updated: 2026-04-21

This guide documents the current NodeReverse integration surface as it exists in the repository.

The previous version relied too heavily on speculative library APIs. The source-aligned way to think about NodeReverse in this repo is:

- there is an external reverse service, typically at `http://localhost:3000`
- each framework exposes a `node-reverse` CLI surface
- reverse support is used for anti-bot profiling, crypto analysis, fingerprint spoofing, TLS/canvas fingerprints, and browser-simulate operations

---

## 1. Shared Subcommands

The current CLI family is aligned around these operations:

- `health`
- `profile`
- `detect`
- `fingerprint-spoof`
- `tls-fingerprint`
- `canvas-fingerprint`
- `analyze-crypto`
- `signature-reverse`
- `ast`
- `webpack`
- `function-call`
- `browser-simulate`

These are the most stable integration points for users and for documentation.

---

## 2. CLI Examples

### PySpider

```bash
python -m pyspider node-reverse health --base-url http://localhost:3000
python -m pyspider node-reverse profile --url https://example.com --base-url http://localhost:3000
python -m pyspider node-reverse analyze-crypto --code-file sample.js --base-url http://localhost:3000
```

### GoSpider

```bash
gospider node-reverse health --base-url http://localhost:3000
gospider node-reverse detect --url https://example.com --base-url http://localhost:3000
gospider node-reverse browser-simulate --code-file sample.js --base-url http://localhost:3000
```

### RustSpider

```bash
rustspider node-reverse health --base-url http://localhost:3000
rustspider node-reverse tls-fingerprint --browser chrome --version 120 --base-url http://localhost:3000
rustspider node-reverse webpack --code-file bundle.js --base-url http://localhost:3000
```

### JavaSpider

```bash
java com.javaspider.EnhancedSpider node-reverse health --base-url http://localhost:3000
java com.javaspider.EnhancedSpider node-reverse profile --url https://example.com --base-url http://localhost:3000
java com.javaspider.EnhancedSpider node-reverse function-call --code-file sample.js --function-name sign --arg a --arg b --base-url http://localhost:3000
```

---

## 3. What NodeReverse Is Good For

Use NodeReverse when the target site depends on:

- JS-generated signatures
- browser fingerprint checks
- anti-bot vendor profiling
- crypto detection or crypto-family discovery
- AST or webpack inspection
- lightweight browser-side script execution without porting logic into four languages

It is especially useful before writing target-specific extraction code.

---

## 4. What `browser-simulate` Actually Means

One of the biggest documentation pitfalls in this repository is over-reading `browser-simulate`.

Current safe interpretation:

- it is a reverse-service-assisted JavaScript execution path with browser-like config
- it is not automatically equivalent to a real Playwright/Selenium/Chromedp/Fantoccini browser session

That distinction matters because several framework-level “ultimate” or “encrypted” flows rely on this simulation path.

Use the wording:

- `reverse-assisted browser emulation`

Avoid the wording:

- `full browser session`
- `real browser automation`

unless you are actually using the runtime's browser module directly.

---

## 5. Operational Notes

- The reverse service must be reachable from the framework runtime.
- Many advanced paths become partial or unavailable when the reverse service is absent.
- Some framework flows catch reverse errors and continue with reduced functionality, so inspect warnings and payloads, not just exit codes.

---

## 6. Recommended Workflow

For a new protected target:

1. Run `node-reverse health`
2. Run `node-reverse detect` or `profile` on the target page
3. If JS is involved, run `analyze-crypto`, `ast`, or `webpack`
4. If browser fingerprinting is involved, run `fingerprint-spoof`, `tls-fingerprint`, and `canvas-fingerprint`
5. Only after that move into encrypted, workflow, or ultimate runtime paths

---

## 7. Related Docs

- [`ENCRYPTED_SITE_CRAWLING_GUIDE.md`](ENCRYPTED_SITE_CRAWLING_GUIDE.md)
- [`ADVANCED_USAGE_GUIDE.md`](ADVANCED_USAGE_GUIDE.md)
- [`docs/FRAMEWORK_CAPABILITIES.md`](docs/FRAMEWORK_CAPABILITIES.md)
- [`docs/FRAMEWORK_CAPABILITY_MATRIX.md`](docs/FRAMEWORK_CAPABILITY_MATRIX.md)
