# SuperSpider Publish / Release Status

Updated: 2026-04-23

This file is a release-facing summary for the GitHub publish step.

## Scope

Validated runtimes:

- `javaspider`
- `gospider`
- `rustspider`
- `pyspider`

Companion runtime also documented:


## Checked Commands

### JavaSpider

```bash
mvn -q -DskipTests package
mvn -q "-Dtest=SpiderRuntimeContractsTest,HtmlParserXPathContractTest,ReadmeContractTest" test
```

Status: pass

### GoSpider

```bash
go test ./...
```

Status: pass

### RustSpider

```bash
cargo test --quiet --lib
cargo test --quiet --test readme_scorecard
cargo test --quiet --test preflight_scorecard
```

Status: targeted slices pass

Note:

- Full `cargo test --quiet` is heavier than the targeted slices above and should be run in CI with a longer timeout budget.

### PySpider

```bash
pytest -q tests/test_smoke.py tests/test_dependencies.py tests/test_cli.py -x
python -m pyspider capabilities
```

Status: pass

## Fixes Applied During Review

### RustSpider

- Added shared XPath helper:
  - `tools/xpath_extract.py`
- Stabilized Anthropic mock-server request reading:
  - `rustspider/src/ai/ai_client.rs`

### PySpider

- Fixed `scrapy run --project` output-path / export-file persistence:
  - `pyspider/cli/main.py`
- Aligned parser dependencies in requirements:
  - `pyspider/requirements.txt`

## Documentation Updated

- Root publish docs:
  - `README.md`
  - `docs/DOCS_INDEX.md`
  - `PUBLISH_RELEASE_STATUS.md`
- Matrix / capability docs:
  - `docs/FRAMEWORK_CAPABILITIES.md`
  - `docs/FRAMEWORK_CAPABILITY_MATRIX.md`
  - `docs/CRAWLER_TYPE_PLAYBOOK.md`
  - `docs/SITE_PRESET_PLAYBOOK.md`
- Runtime READMEs:
  - `javaspider/README.md`
  - `gospider/README.md`
  - `rustspider/README.md`
  - `pyspider/README.md`
- Example docs:
  - `javaspider/examples/README.md`
  - `gospider/examples/README.md`
  - `rustspider/examples/README.md`
  - `pyspider/examples/README.md`

## Remaining Publishing Notes

- Do not describe fallback-heavy AI paths as guaranteed LLM execution.
- Do not describe reverse-assisted browser simulation as full browser session execution.
- Keep advanced reverse / lab / anti-bot surfaces layered by maturity.
