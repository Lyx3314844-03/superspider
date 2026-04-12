#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
go build ./cmd/gospider
