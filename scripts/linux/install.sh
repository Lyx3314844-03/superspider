#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "========================================"
echo "Spider Framework Suite Linux Installer"
echo "========================================"

command -v python3 >/dev/null || { echo "[ERROR] python3 is required"; exit 1; }
command -v go >/dev/null || { echo "[ERROR] Go is required"; exit 1; }
command -v cargo >/dev/null || { echo "[ERROR] Rust/Cargo is required"; exit 1; }
command -v mvn >/dev/null || { echo "[ERROR] Maven is required"; exit 1; }

python3 -m pip install --upgrade pip
python3 -m pip install -r pyspider/requirements.txt
python3 -m pip install -e "./pyspider[dev]"

bash gospider/build.sh
bash javaspider/build.sh
bash rustspider/build.sh

python3 verify_operating_system_support.py --json

echo "[OK] Linux installation surface is ready."
