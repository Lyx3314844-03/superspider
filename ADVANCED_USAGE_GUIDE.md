# Advanced Usage Guide

Updated: 2026-04-21

This guide documents advanced usage patterns that are actually visible in the current repository state.

Two rules matter here:

- Prefer the framework CLIs and normalized job/control-plane surfaces first.
- Treat AI, reverse, and browser-simulation features as conditional capabilities unless your environment is fully configured.

---

## 1. Control-Plane First

All four runtimes now expose more than a plain crawl entrypoint. The practical advanced surfaces are:

- `job` / `async-job`
- `workflow`
- `research`
- `console` / `audit`
- `jobdir` / `http-cache`
- `capabilities`

Examples:

```bash
# PySpider
python -m pyspider capabilities
python -m pyspider workflow run --file workflow.json

# GoSpider
gospider capabilities
gospider workflow run --file workflow.json

# RustSpider
rustspider capabilities
rustspider workflow run --file workflow.json

# JavaSpider
java com.javaspider.EnhancedSpider capabilities
java com.javaspider.EnhancedSpider workflow run --file workflow.json
```

Use these surfaces when you need reproducible runs, artifacts, and inspectable output instead of ad hoc spider code.

---

## 2. Browser Artifacts as a Primary Input

An important shared advanced pattern is:

1. Fetch or instrument with the browser runtime
2. Persist artifacts
3. Feed those artifacts into media, graph, replay, or analysis flows

Common artifact types across the repo:

- HTML
- DOM snapshots
- screenshots
- console logs
- network JSON
- HAR
- graph artifacts

This pattern is especially strong in:

- `gospider`
- `pyspider`
- `rustspider`
- Java workflow/replay flows

Important caveat:

- Browser artifact capture is real.
- Some `simulate browser` paths are not real browser sessions; they are reverse-assisted simulations.

---

## 3. AI Workflows

Advanced AI usage in the current repo falls into three buckets:

- heuristic extraction
- LLM-backed extraction
- AI project/scaffold generation

Recommended usage:

```bash
# PySpider
python -m pyspider ai --url https://example.com --instructions "提取标题和价格"

# GoSpider
gospider ai --url https://example.com --instructions "提取标题和价格"

# RustSpider
rustspider ai --url https://example.com --instructions "提取标题和价格"

# JavaSpider
java com.javaspider.EnhancedSpider ai --url https://example.com --instructions "提取标题和价格"
```

Caveat:

- `pyspider`, `gospider`, and `rustspider` explicitly fall back to heuristic extraction when no AI key is configured.
- Do not assume every successful `ai` command used a real LLM backend.

---

## 4. NodeReverse Workflows

NodeReverse is one of the most useful advanced surfaces in the repository. The CLI entrypoint shape is aligned across runtimes:

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

Examples:

```bash
python -m pyspider node-reverse health --base-url http://localhost:3000
gospider node-reverse profile --url https://example.com --base-url http://localhost:3000
rustspider node-reverse tls-fingerprint --browser chrome --version 120 --base-url http://localhost:3000
java com.javaspider.EnhancedSpider node-reverse analyze-crypto --code-file sample.js --base-url http://localhost:3000
```

Use this surface when the site depends on:

- JS-generated signatures
- crypto helpers
- anti-bot profiling
- browser fingerprint spoofing

---

## 5. Encrypted / Reverse-Dependent Crawling

The encrypted modules across the four runtimes all follow roughly the same advanced pattern:

1. Fetch page or API response
2. Detect crypto / anti-bot signals
3. Call NodeReverse or local heuristics
4. Rebuild request parameters or classify the protected flow

What you should assume today:

- Encrypted crawling support is real.
- Some flows are still strongly dependent on the reverse service.
- “Browser simulation” inside encrypted or ultimate paths is often reverse-assisted, not equivalent to opening Chromium/Playwright/Selenium and reproducing the site session.

---

## 6. Distributed and Queue-Backed Work

Advanced distributed usage is present in all four runtimes, but depth differs.

Practical guidance:

- Use Redis-backed flows first if you want the most source-verified shared path.
- Treat RabbitMQ/Kafka support as conditional on broker/bridge setup and runtime-specific implementation depth.
- Prefer the queue/control-plane/docs surfaces over custom direct integration until your exact backend is verified in your environment.

---

## 7. Research and Graph Analysis

Advanced non-crawl usage is now a real part of the codebase:

- `research run`
- `research async`
- `research soak`
- graph extraction
- notebook-style output in some runtimes

Use these when the goal is:

- site profiling
- field discovery
- schema prototyping
- repeatable extraction experiments

This is especially useful before building a production spider.

---

## 8. What Not to Over-Assume

Avoid these common mistakes:

- Do not assume every AI run is LLM-backed.
- Do not assume every browser-simulation path is a real browser runtime.
- Do not assume every code snippet from older docs corresponds to a current public API.
- Do not assume cross-runtime parity means identical maturity.

For current caveats and practical boundaries, read:

- [`docs/FRAMEWORK_CAPABILITIES.md`](docs/FRAMEWORK_CAPABILITIES.md)
- [`docs/FRAMEWORK_CAPABILITY_MATRIX.md`](docs/FRAMEWORK_CAPABILITY_MATRIX.md)
- [`docs/CRAWL_SCENARIO_GAP_MATRIX.md`](docs/CRAWL_SCENARIO_GAP_MATRIX.md)
