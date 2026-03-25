#!/bin/bash
# RustSpider 构建脚本

echo "========================================"
echo "RustSpider 构建工具"
echo "========================================"

# 检查 Rust
if ! command -v rustc &> /dev/null; then
    echo "[错误] 未找到 Rust，请安装 Rust"
    echo "访问 https://rustup.rs/ 安装"
    exit 1
fi

# 检查 Cargo
if ! command -v cargo &> /dev/null; then
    echo "[错误] 未找到 Cargo"
    exit 1
fi

# 解析参数
COMMAND=${1:-build}

case $COMMAND in
    build)
        echo "[信息] 开始构建..."
        cargo build --release
        if [ $? -ne 0 ]; then
            echo "[错误] 构建失败"
            exit 1
        fi
        echo "[成功] 构建完成"
        ;;
    test)
        echo "[信息] 运行测试..."
        cargo test
        if [ $? -ne 0 ]; then
            echo "[错误] 测试失败"
            exit 1
        fi
        echo "[成功] 测试通过"
        ;;
    run)
        echo "[信息] 运行程序..."
        cargo run -- "$@"
        ;;
    clean)
        echo "[信息] 清理..."
        cargo clean
        echo "[成功] 清理完成"
        ;;
    check)
        echo "[信息] 代码检查..."
        cargo check
        cargo clippy -- -D warnings
        cargo fmt --check
        ;;
    format)
        echo "[信息] 格式化代码..."
        cargo fmt
        ;;
    install)
        echo "[信息] 安装..."
        cargo install --path .
        ;;
    docker)
        echo "[信息] 构建 Docker 镜像..."
        docker build -t rustspider:latest -f docker/Dockerfile .
        echo "[成功] Docker 镜像构建完成"
        ;;
    help|*)
        echo ""
        echo "用法：./build.sh [命令]"
        echo ""
        echo "命令:"
        echo "  build    - 构建项目 (默认)"
        echo "  test     - 运行测试"
        echo "  run      - 运行程序"
        echo "  clean    - 清理"
        echo "  check    - 代码检查"
        echo "  format   - 格式化代码"
        echo "  install  - 安装"
        echo "  docker   - 构建 Docker 镜像"
        echo "  help     - 显示帮助"
        echo ""
        ;;
esac
