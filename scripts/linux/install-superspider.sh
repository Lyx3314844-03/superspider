#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "========================================"
echo "SuperSpider Linux Installer"
echo "========================================"

bash scripts/linux/install-pyspider.sh
bash scripts/linux/install-gospider.sh
bash scripts/linux/install-rustspider.sh
bash scripts/linux/install-javaspider.sh

echo "[OK] SuperSpider Linux install completed"
