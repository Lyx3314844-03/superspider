#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

python3 verify_operating_system_support.py --json
python3 verify_env.py --json
python3 smoke_test.py --json

echo "[OK] macOS verification completed."
