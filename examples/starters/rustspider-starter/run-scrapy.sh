#!/usr/bin/env bash
set -euo pipefail

cargo run --manifest-path ../../../rustspider/Cargo.toml --quiet -- scrapy run --project . --output artifacts/exports/rustspider-starter-items.json
