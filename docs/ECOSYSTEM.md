# Ecosystem

This repository is strongest when it behaves like one crawler platform with four native runtimes.

## Third-Party Integration Surfaces

Primary ecosystem surfaces already present in the repository:

- shared config contract
- shared CLI contract
- shared web control-plane contract
- replay corpus
- benchmark and SLA reports
- blackbox e2e reports
- release validation artifacts

## Current Integration Categories

Runtime and browser:

- Playwright helpers
- Selenium-based browser execution
- WebDriver-based browser execution

Storage and control-plane:

- JSON exports
- JSONL control-plane sinks
- artifacts directory layout

Distributed and orchestration:

- Redis-backed distributed components
- workflow replay and audit traces

Observability:

- runtime readiness reports
- replay dashboard and trend reports
- framework scorecards
- benchmark and SLA reports

## Ecosystem Gaps To Close

- official plugin/integration manifest
- language package publication discipline
- example projects for external adopters
- deployment recipes for single-node and distributed setups
- public benchmark publication cadence

## External Positioning

Compared with single-runtime frameworks such as Scrapy, Colly, or Crawlee, the main differentiator here is not just feature count.
It is the shared contract across Java, Go, Python, and Rust.

That contract should remain the main ecosystem story:

- one operator model
- multiple implementation languages
- comparable output envelopes
- shared evidence and release gates
