#!/usr/bin/env bash
set -euo pipefail

cargo run --manifest-path ../../../rustspider/Cargo.toml --quiet -- job --file job.json
