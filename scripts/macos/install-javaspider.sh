#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "========================================"
echo "JavaSpider macOS Installer"
echo "========================================"

command -v java >/dev/null || { echo "[ERROR] Java 17+ is required"; exit 1; }
command -v mvn >/dev/null || { echo "[ERROR] Maven is required"; exit 1; }

mvn -q -f javaspider/pom.xml -DskipTests -Dmaven.javadoc.skip=true package dependency:copy-dependencies

[ -d "javaspider/target" ] || { echo "[ERROR] Expected build output directory javaspider/target was not produced"; exit 1; }

echo "[OK] JavaSpider package is ready in javaspider/target"
