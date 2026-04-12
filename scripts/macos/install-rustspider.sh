#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "========================================"
echo "RustSpider macOS Installer"
echo "========================================"

command -v cargo >/dev/null || { echo "[ERROR] Rust/Cargo is required"; exit 1; }

bash rustspider/build.sh

[ -x "rustspider/target/release/rustspider" ] || { echo "[ERROR] Expected binary rustspider/target/release/rustspider was not produced"; exit 1; }

echo "[OK] RustSpider binary is ready at rustspider/target/release/rustspider"
