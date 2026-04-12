#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "========================================"
echo "GoSpider Linux Installer"
echo "========================================"

command -v go >/dev/null || { echo "[ERROR] Go is required"; exit 1; }

bash gospider/build.sh

[ -x "gospider/gospider" ] || { echo "[ERROR] Expected binary gospider/gospider was not produced"; exit 1; }

echo "[OK] GoSpider binary is ready at gospider/gospider"
