# Production Cleanup Plan

## Goal

Make the four framework suite (`javaspider`, `gospider`, `pyspider`, `rustspider`) behave like one releasable product instead of a collection of partially aligned demos.

## Principles

- Prefer contract alignment over adding new feature surfaces.
- Prefer repository-local execution paths over globally installed tooling assumptions.
- Lock release gates with regression tests before changing verification code.
- Keep cross-framework behavior consistent where the repository already defines a shared contract.

## Current Priority

1. Harden aggregate verification so `smoke_test.py` and `verify_env.py` work from a clean checkout.
2. Modernize `pyspider` packaging so metadata/build flows do not depend on legacy ambient `setuptools` behavior.
3. Keep existing Java/Go/Rust release guards green while changing Python command resolution.

## Current Deletion Scope

Delete only the redundant versions that are no longer part of the canonical production surface:

- compatibility-only entrypoints that merely forward to newer browser/CLI paths
- duplicate namespace implementations that are not referenced by current tests, CI, or docs
- fully parallel legacy framework trees that are no longer referenced anywhere outside themselves

Do not delete the current canonical runtime roots:

- `javaspider/src/main/java/com/javaspider`
- `gospider/cmd/gospider` and `gospider/browser`
- `pyspider/cli/main.py` and `pyspider/core/spider.py`
- `rustspider/src/main.rs` and `rustspider/src/spider.rs`

## Expected Outcomes

- Root smoke tests succeed from the repository without requiring a preinstalled `pyspider` console script.
- Root doctor aggregation succeeds from the repository without requiring a preinstalled `pyspider` console script.
- `pyspider` packaging metadata can be loaded in minimal environments used by tests.
- Release/documentation paths still point to the shared CLI contract.
