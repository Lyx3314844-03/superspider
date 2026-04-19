#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "========================================"
echo "RustSpider Build Tool"
echo "========================================"

command -v rustc >/dev/null || { echo "[ERROR] Rust not found. Install from https://rustup.rs/"; exit 1; }
command -v cargo >/dev/null || { echo "[ERROR] Cargo not found."; exit 1; }

COMMAND=${1:-build}

case $COMMAND in
    build)
        echo "[INFO] Building release binary..."
        cargo build --release
        echo "[OK] Build complete"
        ;;
    test)
        echo "[INFO] Running tests..."
        cargo test
        echo "[OK] Tests passed"
        ;;
    run)
        echo "[INFO] Running..."
        cargo run -- "${@:2}"
        ;;
    clean)
        echo "[INFO] Cleaning..."
        cargo clean
        echo "[OK] Clean complete"
        ;;
    check)
        echo "[INFO] Checking code..."
        cargo check
        cargo clippy -- -D warnings
        cargo fmt --check
        ;;
    format)
        echo "[INFO] Formatting code..."
        cargo fmt
        ;;
    install)
        echo "[INFO] Installing..."
        cargo install --path .
        ;;
    docker)
        echo "[INFO] Building Docker image..."
        docker build -t rustspider:latest -f docker/Dockerfile .
        echo "[OK] Docker image built"
        ;;
    help|*)
        echo ""
        echo "Usage: ./build.sh [command]"
        echo ""
        echo "Commands:"
        echo "  build    - Build release binary (default)"
        echo "  test     - Run tests"
        echo "  run      - Run the program"
        echo "  clean    - Clean build artifacts"
        echo "  check    - Run code checks (clippy + fmt)"
        echo "  format   - Format code"
        echo "  install  - Install binary"
        echo "  docker   - Build Docker image"
        echo "  help     - Show this help"
        echo ""
        ;;
esac
