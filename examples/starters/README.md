# Starter Repos

These starter directories are designed as minimal external-facing onboarding kits.

They are not full applications.
They are opinionated copyable starting points for each runtime.

Available starters:

- `pyspider-starter`
- `gospider-starter`
- `javaspider-starter`
- `rustspider-starter`
- `csharpspider-starter`

Shared expectations:

- use `spider-framework.yaml`
- keep artifacts under `artifacts/`
- expose the shared CLI contract
- prefer the shared `/api/tasks` control-plane contract when a web surface is added
- include a scrapy-style source entrypoint when the runtime supports authoring as a library

Scrapy-style entrypoints:

- `pyspider-starter/scrapy_demo.py`
- `gospider-starter/main.go`
- `rustspider-starter/src/main.rs`
- `javaspider-starter/src/main/java/starter/ScrapyStyleStarter.java`
- `csharpspider-starter/src/project/Program.cs`

Scrapy project tooling now available across runtimes:

- `scrapy run --project <path>`
- `scrapy init --path <path>`
- `scrapy list --project <path>`
- `scrapy validate --project <path>`
- `scrapy genspider ... --project <path>`

Static-runtime project runner policy:

- `gospider-starter`, `rustspider-starter`, `javaspider-starter` now declare optional project runner artifacts in `scrapy-project.json`
- `scrapy run --project` will execute that artifact when it exists
- if the artifact is missing, the CLI falls back to the built-in metadata runner
