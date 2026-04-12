#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "========================================"
echo "PySpider Linux Installer"
echo "========================================"

command -v python3 >/dev/null || { echo "[ERROR] python3 is required"; exit 1; }

if [ ! -x ".venv-pyspider/bin/python" ]; then
  echo "[INFO] Creating virtual environment .venv-pyspider"
  python3 -m venv .venv-pyspider
fi

.venv-pyspider/bin/python -m pip install --upgrade pip
.venv-pyspider/bin/python -m pip install -r pyspider/requirements.txt
.venv-pyspider/bin/python -m pip install -e ./pyspider
.venv-pyspider/bin/python -m pyspider version

echo "[OK] PySpider is installed in .venv-pyspider"
