# Spider Framework Suite

<p align="center">
  <img src="docs/assets/superspider-wordmark.svg" alt="SuperSpider multicolor wordmark" width="860" />
</p>

<p align="center">
  <img src="docs/assets/superspider-icon.svg" alt="SuperSpider blue icon" width="180" />
</p>

Spider Framework Suite 是一组共享合同的多运行时爬虫框架：

- `pyspider`
- `gospider`
- `rustspider`
- `javaspider`
- `csharpspider`

当前对外定位更接近 `beta/preview` 套件，而不是“所有运行时都完全等价的稳定版 1.0”。其中 `pyspider` 的 project runner 最成熟，`Go/Rust/Java` 已统一到同一套 CLI、manifest 和 built-in metadata runner；需要 project 本地注册代码时，再优先使用已构建 project runner artifact。

## Shared Contracts

- Architecture decision: [docs/ARCHITECTURE_DECISION.md](docs/ARCHITECTURE_DECISION.md)
- Framework contract: [docs/framework-contract.md](docs/framework-contract.md)
- Web control plane: [docs/web-control-plane-contract.md](docs/web-control-plane-contract.md)
- Scrapy-style authoring: [docs/scrapy-style-authoring.md](docs/scrapy-style-authoring.md)
- AI crawler workflow: [docs/AI_CRAWLER_WORKFLOW.md](docs/AI_CRAWLER_WORKFLOW.md)
- Integrations: [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md)
- Capabilities: [docs/FRAMEWORK_CAPABILITIES.md](docs/FRAMEWORK_CAPABILITIES.md)
- Capability matrix: [docs/FRAMEWORK_CAPABILITY_MATRIX.md](docs/FRAMEWORK_CAPABILITY_MATRIX.md)
- Install matrix: [docs/SUPERSPIDER_INSTALLS.md](docs/SUPERSPIDER_INSTALLS.md)
- Deep surfaces: [docs/FRAMEWORK_DEEP_SURFACES.md](docs/FRAMEWORK_DEEP_SURFACES.md)
- Release notes: [docs/RELEASE.md](docs/RELEASE.md)

## Shared Web Control Plane

The suite exposes a shared task-oriented web control plane across runtimes.

- `GET /api/tasks`
- `POST /api/tasks`
- `GET /api/tasks/{id}/results`
- `GET /api/tasks/{id}/logs`

## Unified CLI

Each runtime exposes the shared operational surface:

- `config init`
- `crawl`
- `ai`
- `doctor`
- `export`
- `version`

Advanced suite commands:

- `scrapy`
- `ultimate`
- `anti-bot`
- `node-reverse`
- `jobdir`
- `http-cache`
- `console`

Browser tooling subcommands are also shared across runtimes:

- `browser trace`
- `browser mock`
- `browser codegen`

## Runtime Status

- `pyspider`: richest project runner and reference plugin SDK
- `gospider`: strong concurrency, control-plane, distributed, and artifact tooling
- `rustspider`: strong typed/runtime surface with feature-gated browser and distributed modules
- `javaspider`: strong browser/workflow/audit surface with Maven packaging
- `csharpspider`: source-level scaffold; current workspace has no `dotnet`, so it is not locally compiled here

## Four Framework Capabilities

### PySpider

- Python-native CLI and fastest iteration loop
- richest scrapy-style project runner
- project-level plugin SDK
- browser/http mixed routing
- AI extraction, research, dataset, and distributed surfaces
- official web UI / API launch surface
- official curl conversion and DRM inspection commands

### GoSpider

- binary-first deployment and strong concurrency
- browser artifact capture and workflow replay
- distributed worker, queue, storage, and control-plane friendliness
- media downloader/parser surfaces
- proxy/session-aware runtime
- official curl conversion and DRM inspection commands

### RustSpider

- strongly typed release-binary runtime
- feature-gated browser, distributed, API, and web surfaces
- typed scrapy-style API
- preflight, monitor, anti-bot, and media surfaces
- good fit for high-performance bounded deployments
- official audit trace surface and curl conversion command

### JavaSpider

- Maven-based enterprise-friendly packaging
- browser/workflow-heavy execution model
- audit, connector, session, and anti-bot surfaces
- workflow replay and browser automation CLI
- strong Java ecosystem integration path
- official curl conversion command

Full capabilities list: [docs/FRAMEWORK_CAPABILITIES.md](docs/FRAMEWORK_CAPABILITIES.md)

Deeper under-documented surfaces: [docs/FRAMEWORK_DEEP_SURFACES.md](docs/FRAMEWORK_DEEP_SURFACES.md)

## Project Runner Policy

`scrapy run --project` now follows one safer rule across the static runtimes:

1. If the project manifest declares a project runner artifact and that artifact exists, execute it.
2. Otherwise fall back to the built-in metadata runner.

The CLI no longer compiles Go/Rust/Java project source code at runtime.

## Quick Start

- Install or build the runtime you want to use.
- Generate a project with `scrapy init --path <path>`.
- Run it with `scrapy run --project <path>`.
- Run AI extraction with `pyspider ai --url <url> --instructions "提取标题和摘要" --schema-json '{"type":"object","properties":{"title":{"type":"string"},"summary":{"type":"string"}}}'`.
- Build the optional project runner artifact if you want registered project code and project-local plugins to execute as compiled code.

## AI Workflow

End-to-end AI authoring flow for an authenticated or dynamic site:

```bash
# 1. scaffold a new project
pyspider scrapy init --path my-ai-project
cd my-ai-project

# 2. generate schema / blueprint / AI spider
pyspider scrapy scaffold-ai --project . --url https://example.com --name product_ai

# 3. capture login/session state when needed
pyspider scrapy auth-capture --project . --url https://example.com --session auth

# 4. validate the captured session
pyspider scrapy auth-validate --project . --url https://example.com

# 5. run the generated AI spider
pyspider scrapy run --project . --spider product_ai
```

Equivalent `scrapy scaffold-ai`, `scrapy auth-capture`, and `scrapy auth-validate` surfaces are also exposed by `gospider`, `rustspider`, and `EnhancedSpider`.

## Cross-Platform Install

The suite now exposes unified installer wrappers for the three supported operating systems:

- Windows: `scripts/windows/install.bat`
- Linux: `scripts/linux/install.sh`
- macOS: `scripts/macos/install.sh`

Validation wrappers:

- Windows: `scripts/windows/verify.bat`
- Linux: `scripts/linux/verify.sh`
- macOS: `scripts/macos/verify.sh`

Single-framework installers are also available for all four runtimes:

- Windows: `scripts/windows/install-pyspider.bat`, `scripts/windows/install-gospider.bat`, `scripts/windows/install-rustspider.bat`, `scripts/windows/install-javaspider.bat`
- Linux: `scripts/linux/install-pyspider.sh`, `scripts/linux/install-gospider.sh`, `scripts/linux/install-rustspider.sh`, `scripts/linux/install-javaspider.sh`
- macOS: `scripts/macos/install-pyspider.sh`, `scripts/macos/install-gospider.sh`, `scripts/macos/install-rustspider.sh`, `scripts/macos/install-javaspider.sh`

Detailed prerequisites, outputs, and entry commands live in [docs/SUPERSPIDER_INSTALLS.md](docs/SUPERSPIDER_INSTALLS.md).

Starter examples live under [examples/starters](examples/starters).

## Verification

Verification and release evidence live under:

- [tests](tests)
- [.github/workflows/four-framework-verify.yml](.github/workflows/four-framework-verify.yml)
- [.github/workflows/release.yml](.github/workflows/release.yml)
- [RELEASE_READINESS_REPORT.md](RELEASE_READINESS_REPORT.md)
- `python verify_runtime_stability.py --json --markdown-out artifacts/runtime-stability.md`
- `python verify_result_contracts.py --json --markdown-out RESULT_CONTRACTS_REPORT.md`
- `python verify_runtime_core_capabilities.py --json --markdown-out RUNTIME_CORE_CAPABILITIES_REPORT.md`
- `python verify_operator_products.py --json --markdown-out OPERATOR_PRODUCTS_REPORT.md`
- `python verify_ecosystem_readiness.py --json --markdown-out ECOSYSTEM_READINESS_REPORT.md`
- `python verify_public_install_chain.py --json --markdown-out PUBLIC_INSTALL_CHAIN_REPORT.md`
- `python generate_maturity_gap_report.py --json --markdown-out MATURE_FRAMEWORK_GAP_REPORT.md`
- `python generate_framework_deep_surfaces_report.py --json --markdown-out FRAMEWORK_DEEP_SURFACES_REPORT.md`
