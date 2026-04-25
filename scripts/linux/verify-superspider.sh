#!/usr/bin/env bash
set -euo pipefail

MODE="stable"
if [[ "${1:-}" == "--mode" || "${1:-}" == "-m" ]]; then
  MODE="${2:-stable}"
elif [[ -n "${1:-}" ]]; then
  MODE="${1:-stable}"
fi

if [[ "$MODE" != "stable" && "$MODE" != "contract" ]]; then
  echo "Usage: bash scripts/linux/verify-superspider.sh [stable|contract]" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

PYTHON_CMD=()
candidate_python() {
  local -a candidate=("$@")
  if "${candidate[@]}" -c "import pytest" >/dev/null 2>&1; then
    PYTHON_CMD=("${candidate[@]}")
    return 0
  fi
  return 1
}

if [[ -n "${PYTHON:-}" ]]; then
  candidate_python "$PYTHON" || true
fi
if [[ ${#PYTHON_CMD[@]} -eq 0 ]] && command -v python3 >/dev/null 2>&1; then
  candidate_python python3 || true
fi
if [[ ${#PYTHON_CMD[@]} -eq 0 ]] && command -v python >/dev/null 2>&1; then
  candidate_python python || true
fi
if [[ ${#PYTHON_CMD[@]} -eq 0 ]] && command -v py >/dev/null 2>&1; then
  candidate_python py -3 || true
fi
if [[ ${#PYTHON_CMD[@]} -eq 0 ]]; then
  echo "Python 3 with pytest is required. Set PYTHON=/path/to/python if needed." >&2
  exit 127
fi
GO_CMD=("${GO:-go}")
CARGO_CMD=("${CARGO:-cargo}")

run_step() {
  local name="$1"
  local dir="$2"
  shift 2
  echo "==> $name"
  (cd "$dir" && "$@")
}

run_mvn() {
  if [[ -n "${MAVEN:-}" ]]; then
    if [[ "$MAVEN" == *.cmd || "$MAVEN" == *.bat ]]; then
      local command="\"$MAVEN\""
      local arg
      for arg in "$@"; do
        command="$command \"$arg\""
      done
      cmd.exe /C "$command"
    else
      "$MAVEN" "$@"
    fi
  else
    mvn "$@"
  fi
}

"${PYTHON_CMD[@]}" - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("examples/crawler-selection/ecommerce-search-selection.json").read_text(encoding="utf-8"))
assert payload["scenario"] == "ecommerce_listing"
assert payload["crawler_type"] == "ecommerce_search"
assert payload["recommended_runner"] == "browser"
print("==> crawler-selection golden JSON parsed")
PY

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

run_step "PySpider crawler-selection contract" "$ROOT" \
  "${PYTHON_CMD[@]}" -m pytest pyspider/tests/test_crawler_selector.py -q

if [[ "$MODE" == "contract" ]]; then
  echo "Contract gate complete."
  exit 0
fi

run_step "PySpider stable targeted regression" "$ROOT" \
  "${PYTHON_CMD[@]}" -m pytest \
    pyspider/tests/test_crawler_selector.py \
    pyspider/tests/test_video_downloader_facade.py \
    pyspider/tests/test_dependencies.py \
    -q

run_step "GoSpider full tests" "$ROOT/gospider" "${GO_CMD[@]}" test ./...
run_step "RustSpider compile check" "$ROOT/rustspider" "${CARGO_CMD[@]}" check --quiet
run_step "RustSpider library tests" "$ROOT/rustspider" "${CARGO_CMD[@]}" test --quiet --lib
run_step "JavaSpider full tests" "$ROOT/javaspider" run_mvn -q test

echo "Stable SuperSpider verification gate passed."
