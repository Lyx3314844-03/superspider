# Integrations

This suite exposes a few integration entrypoints that external tools can rely on.

## Primary Entry Points

- shared CLI contract
- shared config contract
- shared `/api/tasks` web control-plane contract
- control-plane JSONL artifacts
- benchmark and blackbox JSON reports
- anti-bot utility commands
- NodeReverse reverse-engineering commands

Current cross-runtime reverse surfaces exposed by the framework CLIs:

- `node-reverse profile`
- `node-reverse detect`
- `node-reverse fingerprint-spoof`
- `node-reverse tls-fingerprint`

Current cross-runtime auto-integration points:

- `profile-site` now includes a `reverse` summary with `detect`, `profile`, `fingerprint_spoof`, and `tls_fingerprint`
- `ultimate` now includes the same `reverse` summary per result item

## Integration Catalog

Canonical manifest:

- `contracts/integration-catalog.json`

## External Examples

- `examples/external/platform-demo`
- `examples/external/control-plane-demo`
- `examples/external/python-control-plane-client`
- `examples/external/node-control-plane-client`
- `examples/external/README.md`

## Plugin Entry Model

The repository now publishes a first-pass runtime plugin SDK for project-level authoring in:

- `pyspider`
- `gospider`
- `rustspider`
- `javaspider`
- `csharpspider`

Current practical plugin/integration surfaces are:

- invoking runtime CLIs
- posting to `/api/tasks`
- reading `artifacts/control-plane/*.jsonl`
- consuming benchmark/readiness JSON artifacts
- registering project plugins through the runtime plugin registries

Current SDK shape:

- `pyspider`
  - base type: `pyspider.spider.spider.ScrapyPlugin`
  - registry: `pyspider.spider.plugins`
  - project runner supports configured plugin names and `plugins.py` registration
  - project runner supports `scrapy.runner` plus `scrapy.spiders.<name>.runner` browser/http routing
  - request-level hybrid routing is supported through `Request.meta["runner"] = "browser" | "http"`
  - request-level browser options (in `Request.meta["browser"]` or flat meta keys):
    - `session` (`browser_session`)
    - `wait_until` (`browser_wait_until`)
    - `wait_for_selector` (`browser_wait_for_selector`)
    - `wait_for_load_state` (`browser_wait_for_load_state`)
    - `timeout_seconds` (`browser_timeout_seconds`)
    - `screenshot_path` (`browser_screenshot_path`)
    - `html_path` (`browser_html_path`)

- `gospider`
  - base interface: `gospider/scrapy.Plugin`
  - registries:
    - runtime-level: `gospider/scrapy`
    - project-level: `gospider/scrapy/project`
  - project runner supports registered plugin names through project execution
  - project runner also supports `scrapy-plugins.json`
  - shared scrapy core now supports plugin configuration, spider/downloader middleware, and request-level runner selection

- `rustspider`
  - base trait: `rustspider::scrapy::ScrapyPlugin`
  - registries:
    - runtime-level: `rustspider::scrapy`
    - project-level: `rustspider::scrapy::project`
  - project runner supports registered plugin names through project execution
  - project runner also supports `scrapy-plugins.json`
  - shared scrapy core now supports plugin configuration, spider/downloader middleware, and request-level runner selection

- `javaspider`
  - base interface: `com.javaspider.scrapy.ScrapyPlugin`
  - registries:
    - runtime-level: `com.javaspider.scrapy`
    - project-level: `com.javaspider.scrapy.project.ProjectRuntime`
  - project runner supports registered plugin names through project execution
  - project runner also supports `scrapy-plugins.json`
  - shared scrapy core now supports plugin configuration, spider/downloader middleware, and request-level runner selection

This is still an early SDK, not yet a full marketplace or compatibility contract, but it is now a real reusable extension surface instead of only manifest-level indirection.

## CSharp Runtime Status

`csharpspider` is now scaffolded in-repo with:

- shared CLI surface
- scrapy-style core types
- project runtime
- plugin manifest support
- worker pool / distributed scheduler / reverse client skeletons

The current environment does not have `dotnet`, so these capabilities are source-complete but not compiled here.
