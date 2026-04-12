#!/usr/bin/env bash
set -euo pipefail

go run ../../../gospider/cmd/gospider job --file job.json
