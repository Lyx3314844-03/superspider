#!/bin/bash
# JavaSpider 构建脚本

echo "========================================"
echo "JavaSpider 构建工具"
echo "========================================"

# 检查 Java
if ! command -v java &> /dev/null; then
    echo "[错误] 未找到 Java，请安装 Java 17+"
    exit 1
fi

# 检查 Maven
if ! command -v mvn &> /dev/null; then
    echo "[错误] 未找到 Maven，请安装 Maven 3.6+"
    exit 1
fi

# 解析参数
COMMAND=${1:-build}

case $COMMAND in
    build)
        echo "[信息] 开始构建..."
        mvn clean package -DskipTests
        if [ $? -ne 0 ]; then
            echo "[错误] 构建失败"
            exit 1
        fi
        echo "[成功] 构建完成"
        ;;
    test)
        echo "[信息] 运行测试..."
        mvn clean test
        if [ $? -ne 0 ]; then
            echo "[错误] 测试失败"
            exit 1
        fi
        echo "[成功] 测试通过"
        ;;
    run)
        echo "[信息] 运行程序..."
        mvn exec:java -Dexec.mainClass="com.javaspider.examples.AdvancedSpiderExample"
        ;;
    clean)
        echo "[信息] 清理..."
        mvn clean
        echo "[成功] 清理完成"
        ;;
    install)
        echo "[信息] 安装到本地仓库..."
        mvn clean install
        ;;
    docker)
        echo "[信息] 构建 Docker 镜像..."
        docker build -t javaspider:latest -f docker/Dockerfile .
        echo "[成功] Docker 镜像构建完成"
        ;;
    help|*)
        echo ""
        echo "用法：./build.sh [命令]"
        echo ""
        echo "命令:"
        echo "  build    - 构建项目 (默认)"
        echo "  test     - 运行测试"
        echo "  run      - 运行示例"
        echo "  clean    - 清理"
        echo "  install  - 安装到本地仓库"
        echo "  docker   - 构建 Docker 镜像"
        echo "  help     - 显示帮助"
        echo ""
        ;;
esac
