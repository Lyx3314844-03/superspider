#!/usr/bin/env bash
set -euo pipefail

go run ../../../gospider/cmd/gospider scrapy run --project . --output artifacts/exports/gospider-starter-items.json
