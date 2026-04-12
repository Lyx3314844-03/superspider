# Framework Deep Surfaces

This document exposes capability surfaces that exist in code and `capabilities`
payloads, but are easy to miss if you only read the short runtime README
highlights.

The primary runtimes covered here are:

- `javaspider`
- `gospider`
- `pyspider`
- `rustspider`

## Shared Hidden Surfaces

Across the four runtimes, there is a larger common surface than the short
README snippets suggest.

- Extended CLI entrypoints beyond the obvious `crawl/doctor/scrapy/ultimate`:
  - `config`
  - `ai`
  - `export`
  - `curl`
  - `job`
  - `jobdir`
  - `http-cache`
  - `console`
  - `sitemap-discover`
  - `plugins`
  - `selector-studio`
  - `profile-site`
  - `capabilities`
  - `version`
- Shared operator products:
  - `jobdir`
  - `http_cache`
  - `browser_tooling`
  - `autoscaling_pools`
  - `debug_console`
- Shared browser tooling expectations:
  - trace
  - HAR capture
  - route mocking
  - codegen
- Shared control-plane surfaces:
  - task API
  - result envelope
  - artifact refs
  - graph artifact
  - graph extract
- Shared kernel contracts:
  - `request`
  - `fingerprint`
  - `frontier`
  - `scheduler`
  - `middleware`
  - `artifact_store`
  - `session_pool`
  - `proxy_policy`
  - `observability`
  - `cache`
- Shared observability surfaces:
  - `doctor`
  - `profile-site`
  - `selector-studio`
  - `scrapy doctor`
  - `scrapy profile`
  - `scrapy bench`
  - Prometheus-style metrics
  - OpenTelemetry-style JSON envelopes
- Optional live external-service smoke surfaces now exist around AI / captcha
  integrations and feed into `verify_captcha_live_readiness.py`.

## JavaSpider

JavaSpider has a broader execution and enterprise integration surface than the
top-level README currently implies.

- Under-documented CLI entrypoints:
  - `ai`
  - `curl`
  - `job`
  - `jobdir`
  - `http-cache`
  - `console`
  - `selector-studio`
  - `profile-site`
  - `workflow`
  - `media`
- Important modules surfaced by `capabilities`:
  - `workflow.WorkflowSpider`
  - `cli.MediaDownloaderCLI`
  - `converter.CurlToJavaConverter`
  - `contracts.AutoscaledFrontier`
  - `contracts.RuntimeArtifactStore`
  - `audit.InMemoryAuditTrail`
  - `connector.InMemoryConnector`
  - `session.SessionProfile`
  - `nodereverse.NodeReverseClient`
  - `antibot.AntiBotHandler`
- Module families that are easy to overlook from the directory tree:
  - `advanced`
  - `async`
  - `audit`
  - `bridge`
  - `connector`
  - `contracts`
  - `dynamic`
  - `encrypted`
  - `graph`
  - `performance`
  - `session`
  - `workflow`
  - `web`
- Hidden-but-real strength areas:
  - workflow replay and browser automation
  - audit trail and connector abstraction
  - autoscaled frontier and runtime artifact store contracts
  - session profiles and proxy policy surfaces
  - optional live captcha smoke and optional live AI smoke

## GoSpider

GoSpider is not just a compiled crawler binary; it exposes a sizeable runtime
and operator surface.

- Under-documented CLI entrypoints:
  - `ai`
  - `curl`
  - `job`
  - `jobdir`
  - `http-cache`
  - `console`
  - `selector-studio`
  - `profile-site`
  - `plugins`
  - `sitemap-discover`
  - `media`
- Important modules surfaced by `capabilities`:
  - `core.JobSpec`
  - `core.JobRunner`
  - `core.AutoscaledFrontier`
  - `core.FileArtifactStore`
  - `core.CurlToGoConverter`
  - `runtime.dispatch`
  - `runtime.http`
  - `runtime.browser`
  - `site_profiler`
  - `selector_studio`
  - `plugin_manifest`
  - `api`
  - `distributed`
- Module families that are easy to overlook:
  - `api`
  - `bridge`
  - `captcha`
  - `distributed`
  - `events`
  - `extractors`
  - `graph`
  - `middleware`
  - `node_reverse`
  - `runtime/dispatch`
  - `storage`
  - `ultimate`
  - `web`
- Hidden-but-real strength areas:
  - dispatch/router layer between runtimes
  - dedicated captcha package with provider-backed live smoke
  - API server and control-plane JSON surfaces
  - distributed state-machine / soak / worker service coverage
  - site-specific media extractors and browser artifact capture

## PySpider

PySpider already exposes the richest project runner, but there are still many
surfaces that are easy to miss.

- Under-documented CLI entrypoints:
  - `ai`
  - `curl`
  - `web`
  - `run`
  - `async-job`
  - `job`
  - `jobdir`
  - `http-cache`
  - `console`
  - `sitemap-discover`
  - `plugins`
  - `selector-studio`
  - `profile-site`
- Important modules surfaced by `capabilities`:
  - `research.job`
  - `runtime.orchestrator`
  - `runtime.async_runtime`
  - `core.contracts`
  - `core.incremental`
  - `core.curlconverter`
  - `profiler.site_profiler`
  - `extract.studio`
  - `dataset.writer`
  - `advanced.ultimate`
  - `antibot.antibot`
  - `media.drm_detector`
  - `node_reverse.client`
  - `node_reverse.fetcher`
  - `web.app`
  - `api.server`
- Module families that are easy to overlook:
  - `advanced`
  - `ai` / `ai_extractor`
  - `api`
  - `captcha`
  - `dataset`
  - `extract`
  - `graph_crawler`
  - `profiler`
  - `research`
  - `runtime`
  - `store`
  - `web`
- Hidden-but-real strength areas:
  - async runtime / orchestrator / notebook-style output surfaces
  - research and extraction studio layers
  - site profiler and DRM inspection
  - dataset / KV / request queue stores
  - provider-backed live captcha smoke for reCAPTCHA and hCaptcha

## RustSpider

RustSpider has a deeper surface than “typed spider + browser + distributed”
would suggest.

- Under-documented CLI entrypoints:
  - `ai`
  - `curl`
  - `job`
  - `jobdir`
  - `http-cache`
  - `console`
  - `audit`
  - `selector-studio`
  - `profile-site`
  - `plugins`
  - `sitemap-discover`
- Important modules surfaced by `capabilities`:
  - `reactor.NativeReactor`
  - `artifact.MemoryArtifactStore`
  - `contracts.AutoscaledFrontier`
  - `incremental.IncrementalCrawler`
  - `curlconverter.CurlToRustConverter`
  - `preflight`
  - `browser`
  - `media`
  - `proxy`
  - `retry`
  - `antibot`
  - `node_reverse`
  - `site_profiler`
  - `sitemap_discovery`
  - `plugin_manifest`
  - `selector_studio`
- Module families that are easy to overlook:
  - `artifact`
  - `captcha`
  - `core`
  - `dedup`
  - `ffi`
  - `reactor`
  - `task`
  - `video`
  - feature-gated `api` / `web`
- Hidden-but-real strength areas:
  - provider-backed live captcha smoke for reCAPTCHA / hCaptcha / Turnstile
  - audit entrypoint on top of runtime/control-plane traces
  - reactor/artifact abstractions
  - feature-gated API / web deployment surfaces
  - richer anti-bot challenge-solving paths than the short README implies

## Operator Shortcut

If you want the machine-readable surfaces instead of this human summary, use:

- `javaspider`: `... SuperSpiderCLI capabilities`
- `gospider`: `gospider capabilities`
- `pyspider`: `python -m pyspider capabilities`
- `rustspider`: `cargo run -- capabilities`

If you want the suite-level live captcha view, use:

```bash
python verify_captcha_live_readiness.py --json
```
