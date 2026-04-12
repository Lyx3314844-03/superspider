# Spider Framework Contract

This repository treats `javaspider`, `gospider`, `rustspider`, and `pyspider` as one product family.

## Unified CLI

Every runtime should expose the same top-level command surface:

- `config init [--output <path>]`
- `crawl [--config <path>] [--url <url>]`
- `ai [--config <path>] [--url <url>] [--html-file <path>] [--instructions <text>] [--schema-file <path>] [--schema-json <json>] [--question <text>] [--description <text>] [--output <path>]`
- `browser fetch [--config <path>] [--url <url>] [--screenshot <path>]`
- `jobdir <init|status|pause|resume|clear> --path <path>`
- `http-cache <status|clear|seed> --path <path>`
- `console <snapshot|tail> --control-plane <dir>`
- `doctor [--config <path>] [--json]`
- `export [--input <path>] [--format <json|csv|md>] [--output <path>]`
- `version`
- `help`

Shared browser tooling subcommands:

- `browser trace --url <url> --trace-path <path> [--har-path <path>]`
- `browser mock --url <url> --route-manifest <path>`
- `browser codegen --url <url> --output <path> [--language <python|javascript>]`

Shared scrapy-style project contract tooling:

- `scrapy contracts init --project <dir>`
- `scrapy contracts validate --project <dir>`

## Shared Config Schema

Canonical config filename:

- `spider-framework.yaml`

Supported fallback names:

- `spider-framework.yml`
- `spider-framework.json`
- existing runtime-specific legacy config files

Supported top-level sections:

- `version`
- `project`
- `runtime`
- `crawl`
- `sitemap`
- `browser`
- `anti_bot`
- `node_reverse`
- `middleware`
- `pipeline`
- `auto_throttle`
- `plugins`
- `storage`
- `export`
- `doctor`

## Shared Sitemap Config

Optional `sitemap` section fields:

- `enabled`
- `url`
- `max_urls`

## Shared Middleware Config

Optional `middleware` section fields:

- `user_agent_rotation`
- `respect_robots_txt`
- `min_request_interval_ms`

## Shared Pipeline Config

Optional `pipeline` section fields:

- `console`
- `dataset`
- `jsonl_path`

## Shared AutoThrottle Config

Optional `auto_throttle` section fields:

- `enabled`
- `start_delay_ms`
- `max_delay_ms`
- `target_response_time_ms`

## Shared Plugin Config

Optional `plugins` section fields:

- `enabled`
- `manifest`

## Shared Anti-Bot Config

Optional `anti_bot` section fields:

- `enabled`
- `profile`
- `proxy_pool`
- `session_mode`
- `stealth`
- `challenge_policy`
- `captcha_provider`
- `captcha_api_key`

These fields are shared operator intent, not a promise that every runtime uses the exact same internal implementation.

## Shared Node Reverse Config

Optional `node_reverse` section fields:

- `enabled`
- `base_url`

## Shared Storage Layout

Default artifact layout:

- `artifacts/checkpoints`
- `artifacts/datasets`
- `artifacts/exports`
- `artifacts/browser`

## Shared JOBDIR Surface

Long-running jobs may expose a shared `jobdir` object in `JobSpec` and on-disk `job-state.json`.

Expected directories:

- `checkpoints`
- `cache`
- `exports`
- `browser`
- `control-plane`

Expected state transitions:

- `initialized`
- `ready`
- `running`
- `paused`

Shared operator commands:

- `jobdir init`
- `jobdir status`
- `jobdir pause`
- `jobdir resume`
- `jobdir clear`

## Shared HTTP Cache Surface

Jobs may declare a shared `cache` object with:

- `backend`
- `strategy`
- `store_path`
- `revalidate_seconds`

Shared operator commands:

- `http-cache status`
- `http-cache seed`
- `http-cache clear`

## Shared Browser Tooling Surface

Browser jobs may declare or use:

- `trace_path`
- `har_path`
- `har_replay`
- `route_manifest`
- `codegen_out`
- `codegen_language`

Shared browser tooling commands:

- `browser fetch`
- `browser trace`
- `browser mock`
- `browser codegen`

## Shared Debug Console Surface

Interactive debugging should expose a shared control-plane console surface backed by:

- `artifacts/control-plane/results.jsonl`
- `artifacts/control-plane/events.jsonl`

Shared operator commands:

- `console snapshot`
- `console tail`

## Shared Operator Product Surface

`capabilities` should expose a machine-readable `operator_products` object.

Required keys:

- `jobdir`
- `http_cache`
- `browser_tooling`
- `autoscaling_pools`
- `debug_console`

These keys describe productized operator surfaces on top of the kernel contract, including pause/resume job directories, cache inspection and seeding, Playwright trace/HAR/mock/codegen tooling, autoscaling pool surfaces, and interactive control-plane console inspection.

## Shared Checkpoint Shape

Checkpoint JSON files should use:

- `spider_id`
- `timestamp`
- `visited_urls`
- `pending_urls`
- `stats`
- `config`
- `checksum`

## Shared Export Envelope

JSON exports should use:

- `schema_version`
- `runtime`
- `exported_at`
- `item_count`
- `items`

CSV and Markdown exports may stay runtime-specific in formatting, but must represent the same logical item set.

## Kernel Capability Surface

`capabilities` should expose a machine-readable `kernel_contracts` object.

Required keys:

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

Each value should be a non-empty list of runtime-local export identifiers so operators can map the shared contract to concrete types in Java, Go, Rust, and Python.

## Shared Doctor JSON Envelope

`doctor --json` should emit a JSON object with:

- `command`
- `runtime`
- `summary`
- `summary_text`
- `exit_code`
- `checks`

Required values:

- `command` must be `doctor`
- `runtime` must be one of `java`, `go`, `rust`, `python`
- `summary` must be `passed` or `failed`
- `exit_code` must be `0` or `1`

Each `checks` item should use:

- `name`
- `status`
- `details`

Allowed `status` values:

- `passed`
- `failed`
- `warning`
- `skipped`

Schema file:

- `schemas/spider-doctor-report.schema.json`

## AI JSON Envelope

`ai` should emit a JSON object with:

- `command`
- `runtime`
- `mode`
- `summary`
- `summary_text`
- `exit_code`
- `engine`
- `source`
- `warnings`
- `result`

Required values:

- `command` must be `ai`
- `runtime` must be one of `java`, `go`, `rust`, `python`
- `mode` must be one of `extract`, `understand`, or `generate-config`
- `summary` must be `passed` or `failed`
- `exit_code` must be `0` or `1`
- `engine` must be `llm` or `heuristic-fallback`

Optional values:

- `url`

Schema file:

- `schemas/spider-ai-report.schema.json`

## Root Smoke-Test JSON Envelope

`smoke_test.py --json` should emit a JSON object with:

- `command`
- `summary`
- `summary_text`
- `exit_code`
- `checks`

Required values:

- `command` must be `smoke-test`
- `summary` must be `passed` or `failed`
- `exit_code` must be `0` or `1`

Each `checks` item should use:

- `name`
- `runtime`
- `summary`
- `exit_code`
- `details`

Schema file:

- `schemas/spider-smoke-report.schema.json`

## Root Verify-Version JSON Envelope

`verify_version.py --json` should emit a JSON object with:

- `command`
- `summary`
- `summary_text`
- `exit_code`
- `expected_version`
- `checks`
- `targets`

Required values:

- `command` must be `verify-version`
- `summary` must be `passed` or `failed`
- `exit_code` must be `0` or `1`

Each `checks` item should use:

- `name`
- `status`
- `details`

Each `targets` item should use:

- `path`
- `expected`
- `actual`
- `status`

Schema file:

- `schemas/spider-version-report.schema.json`

## Ultimate JSON Envelope

`ultimate` should emit a JSON object with:

- `command`
- `runtime`
- `summary`
- `summary_text`
- `exit_code`
- `url_count`
- `result_count`
- `results`

Required values:

- `command` must be `ultimate`
- `runtime` must be one of `java`, `go`, `rust`, `python`
- `summary` must be `passed` or `failed`
- `exit_code` must be `0` or `1`

Each `results` item should use:

- `task_id`
- `url`
- `success`
- `error`
- `duration`
- `anti_bot_level`
- `anti_bot_signals`

Optional values:

- `proxy_used`

Schema file:

- `schemas/spider-ultimate-report.schema.json`

## Ultimate Trend Report

`verify_ultimate_trends.py --json` should emit a JSON object with:

- `command`
- `summary`
- `summary_text`
- `exit_code`
- `framework_metrics`
- `framework_trends`
- `alerts`
- `history`

Required values:

- `command` must be `verify-ultimate-trends`
- `summary` must be one of `passed`, `warning`, or `failed`
- `exit_code` must be `0` or `1`

Schema file:

- `schemas/spider-ultimate-trend-report.schema.json`

## Browser Contract

`browser fetch` should:

- render the target URL with the runtime's default browser engine
- print title and current URL
- optionally save a screenshot
- optionally save HTML to the configured browser artifact directory

The implementation may use Playwright, Selenium, chromedp, or Fantoccini internally, but the user-facing contract is identical.
