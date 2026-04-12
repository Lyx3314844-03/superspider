# Public Benchmarks

Public benchmark credibility requires two things:

- reproducible commands
- published artifacts

## Canonical Commands

Generate repository-level benchmark and SLA evidence:

```bash
python verify_benchmark_sla.py --json --markdown-out artifacts/benchmark-sla.md
```

Generate repository-level blackbox e2e evidence:

```bash
python verify_blackbox_e2e.py --json --markdown-out artifacts/blackbox-e2e.md
```

Generate historical benchmark trend evidence:

```bash
python verify_benchmark_trends.py --json --markdown-out artifacts/benchmark-trends.md --snapshot-out artifacts/benchmark-history/current-benchmark.json
```

Historical benchmark snapshots now carry runtime readiness alongside SLA and blackbox e2e so `control_plane_rate` can be tracked over time, not just shown in the latest run.

Generate long-running stability evidence:

```bash
python verify_runtime_stability.py --json --markdown-out artifacts/runtime-stability.md
```

Generate ecosystem readiness evidence:

```bash
python verify_ecosystem_readiness.py --json --markdown-out artifacts/ecosystem-readiness.md
```

Generate runtime readiness evidence:

```bash
python verify_runtime_readiness.py --json
```

The runtime readiness artifact now includes a `control_plane_rate` metric so public evidence can show whether each runtime's shared `/api/tasks` lifecycle probe is actually passing.

Generate or refresh the static public benchmark page:

```bash
python generate_public_benchmark_site.py --output web-ui/public-benchmarks/index.html
python generate_public_benchmark_site.py --refresh --output web-ui/public-benchmarks/index.html
```

## What To Publish

For every benchmark cycle publish:

- benchmark SLA JSON
- benchmark SLA Markdown
- blackbox e2e JSON
- blackbox e2e Markdown
- benchmark trend JSON
- benchmark trend Markdown
- benchmark history snapshot JSON
- runtime readiness JSON
- framework scorecard JSON
- framework scorecard Markdown

## Publication Standard

Each public benchmark run should include:

- repository commit SHA
- workflow/run URL
- OS and toolchain family
- runtime-specific measured durations
- control-plane lifecycle parity signal
- pass/fail threshold interpretation

## Comparison Discipline

Do not claim superiority over Scrapy, Colly, or Crawlee without:

- reproducible benchmark input
- matching scope
- disclosed environment
- published artifacts

The safer public claim is:

- contract-aligned multi-runtime evidence exists
- release workflows generate benchmark artifacts
- benchmark thresholds are explicit and inspectable
