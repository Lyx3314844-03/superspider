#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "========================================"
echo "SuperSpider macOS Installer"
echo "========================================"

bash scripts/macos/install-pyspider.sh
bash scripts/macos/install-gospider.sh
bash scripts/macos/install-rustspider.sh
bash scripts/macos/install-javaspider.sh

echo "[OK] SuperSpider macOS install completed"
