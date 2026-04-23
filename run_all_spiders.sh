#!/usr/bin/env bash
# ============================================================================
# 京东 iPhone 17 价格爬虫 - 统一运行脚本
#
# 使用四个爬虫框架 (PySpider, GoSpider, RustSpider, JavaSpider) 爬取京东所有 iPhone 17 价格
#
# 使用方法:
#   ./run_all_spiders.sh [选项]
#
# 选项:
#   --pages <n>     爬取页数 (默认: 5)
#   --delay <n>     请求延迟秒数 (默认: 3)
#   --proxy <addr>  代理地址 (例如: http://127.0.0.1:7890)
#   --framework <f> 只运行指定框架 (pyspider/gospider/rustspider/javaspider/all)
#   --skip-build    跳过编译步骤
#   --help          显示帮助信息
#
# 示例:
#   ./run_all_spiders.sh --pages 3 --delay 5
#   ./run_all_spiders.sh --framework pyspider --pages 10
#   ./run_all_spiders.sh --proxy http://127.0.0.1:7890
# ============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
PAGES=5
DELAY=3
PROXY=""
FRAMEWORK="all"
SKIP_BUILD=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"

# 确保输出目录存在
mkdir -p "$OUTPUT_DIR"

# 打印横幅
print_banner() {
    echo -e "${BLUE}"
    echo "============================================================"
    echo "  京东 iPhone 17 价格爬虫 - 四框架联合爬取"
    echo "============================================================"
    echo -e "${NC}"
    echo "框架: PySpider (Python), GoSpider (Go), RustSpider (Rust), JavaSpider (Java)"
    echo "页数: $PAGES | 延迟: ${DELAY}s"
    if [ -n "$PROXY" ]; then
        echo "代理: $PROXY"
    fi
    echo "输出目录: $OUTPUT_DIR"
    echo "============================================================"
    echo ""
}

# 打印框架标题
print_framework_header() {
    local name=$1
    local color=$2
    echo ""
    echo -e "${color}============================================================"
    echo "  开始运行: $name"
    echo "============================================================${NC}"
}

# 打印框架结果
print_framework_result() {
    local name=$1
    local status=$2
    if [ "$status" -eq 0 ]; then
        echo -e "${GREEN}✓ $name 运行成功${NC}"
    else
        echo -e "${RED}✗ $name 运行失败 (退出码: $status)${NC}"
    fi
}

# 运行 PySpider
run_pyspider() {
    print_framework_header "PySpider (Python)" "$GREEN"

    cd "${SCRIPT_DIR}/pyspider"

    if [ -n "$PROXY" ]; then
        python spider_jd_iphone17.py --pages "$PAGES" --delay "$DELAY" --proxy "$PROXY" || return $?
    else
        python spider_jd_iphone17.py --pages "$PAGES" --delay "$DELAY" || return $?
    fi

    cd "$SCRIPT_DIR"
    return 0
}

# 运行 GoSpider
run_gospider() {
    print_framework_header "GoSpider (Go)" "$BLUE"

    cd "${SCRIPT_DIR}/gospider"

    # 编译
    if [ "$SKIP_BUILD" = false ]; then
        echo "正在编译 GoSpider..."
        go build -o gospider_jd ./cmd/jd_iphone17/ || {
            echo -e "${RED}GoSpider 编译失败${NC}"
            return 1
        }
        echo "编译完成"
    fi

    # 运行
    if [ -n "$PROXY" ]; then
        ./gospider_jd --pages "$PAGES" --delay "$DELAY" --proxy "$PROXY" || return $?
    else
        ./gospider_jd --pages "$PAGES" --delay "$DELAY" || return $?
    fi

    cd "$SCRIPT_DIR"
    return 0
}

# 运行 RustSpider
run_rustspider() {
    print_framework_header "RustSpider (Rust)" "$YELLOW"

    cd "${SCRIPT_DIR}/rustspider"

    # 编译
    if [ "$SKIP_BUILD" = false ]; then
        echo "正在编译 RustSpider..."
        cargo build --bin jd_iphone17 --release 2>/dev/null || {
            echo -e "${RED}RustSpider 编译失败${NC}"
            return 1
        }
        echo "编译完成"
    fi

    # 运行
    if [ -n "$PROXY" ]; then
        ./target/release/jd_iphone17 --pages "$PAGES" --delay "$DELAY" --proxy "$PROXY" || return $?
    else
        ./target/release/jd_iphone17 --pages "$PAGES" --delay "$DELAY" || return $?
    fi

    cd "$SCRIPT_DIR"
    return 0
}

# 运行 JavaSpider
run_javaspider() {
    print_framework_header "JavaSpider (Java)" "$BLUE"

    cd "${SCRIPT_DIR}/javaspider"

    # 编译
    if [ "$SKIP_BUILD" = false ]; then
        echo "正在编译 JavaSpider..."

        # 确保 target 目录存在
        mkdir -p target/examples

        # 查找依赖 jar
        LIB_DIR="lib"
        CLASSPATH="target/classes:${LIB_DIR}/*"

        javac -cp "$CLASSPATH" -encoding UTF-8 \
            -d target/examples \
            src/main/java/com/javaspider/examples/jd/JDiPhone17FrameworkSpider.java 2>/dev/null || {
            echo -e "${RED}JavaSpider 编译失败，尝试使用 Maven...${NC}"
            if command -v mvn &> /dev/null; then
                mvn compile -q || {
                    echo -e "${RED}Maven 编译也失败了${NC}"
                    return 1
                }
            else
                echo -e "${RED}未找到 Maven，请手动编译${NC}"
                return 1
            fi
        }
        echo "编译完成"
    fi

    # 运行
    LIB_DIR="lib"
    CLASSPATH="target/examples:target/classes:${LIB_DIR}/*"

    JAVA_ARGS="--pages $PAGES --delay $((DELAY * 1000))"
    if [ -n "$PROXY" ]; then
        PROXY_HOST=$(echo "$PROXY" | sed 's|http://||' | cut -d: -f1)
        PROXY_PORT=$(echo "$PROXY" | sed 's|http://||' | cut -d: -f2)
        JAVA_ARGS="$JAVA_ARGS --proxy ${PROXY_HOST}:${PROXY_PORT}"
    fi

    java -cp "$CLASSPATH" com.javaspider.examples.jd.JDiPhone17FrameworkSpider $JAVA_ARGS || return $?

    cd "$SCRIPT_DIR"
    return 0
}

# 显示帮助
show_help() {
    echo "京东 iPhone 17 价格爬虫 - 统一运行脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --pages <n>      爬取页数 (默认: 5)"
    echo "  --delay <n>      请求延迟秒数 (默认: 3)"
    echo "  --proxy <addr>   代理地址 (例如: http://127.0.0.1:7890)"
    echo "  --framework <f>  只运行指定框架 (pyspider/gospider/rustspider/javaspider/all)"
    echo "  --skip-build     跳过编译步骤"
    echo "  --help           显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 --pages 3 --delay 5"
    echo "  $0 --framework pyspider --pages 10"
    echo "  $0 --proxy http://127.0.0.1:7890"
    echo "  $0 --skip-build"
    exit 0
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --pages)
            PAGES="$2"
            shift 2
            ;;
        --delay)
            DELAY="$2"
            shift 2
            ;;
        --proxy)
            PROXY="$2"
            shift 2
            ;;
        --framework)
            FRAMEWORK="$2"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            echo "未知选项: $1"
            show_help
            ;;
    esac
done

# 主流程
main() {
    print_banner

    local exit_code=0
    local results=()

    # 根据选择运行框架
    case $FRAMEWORK in
        pyspider|python)
            run_pyspider
            exit_code=$?
            results+=("PySpider:$exit_code")
            ;;
        gospider|go)
            run_gospider
            exit_code=$?
            results+=("GoSpider:$exit_code")
            ;;
        rustspider|rust)
            run_rustspider
            exit_code=$?
            results+=("RustSpider:$exit_code")
            ;;
        javaspider|java)
            run_javaspider
            exit_code=$?
            results+=("JavaSpider:$exit_code")
            ;;
        all|*)
            # 依次运行所有框架
            run_pyspider; results+=("PySpider:$?")
            run_gospider; results+=("GoSpider:$?")
            run_rustspider; results+=("RustSpider:$?")
            run_javaspider; results+=("JavaSpider:$?")
            ;;
    esac

    # 打印总结
    echo ""
    echo -e "${BLUE}============================================================"
    echo "  运行结果总结"
    echo "============================================================${NC}"

    local success_count=0
    local fail_count=0

    for result in "${results[@]}"; do
        local name="${result%%:*}"
        local code="${result##*:}"
        if [ "$code" -eq 0 ]; then
            echo -e "  ${GREEN}✓${NC} $name: 成功"
            ((success_count++))
        else
            echo -e "  ${RED}✗${NC} $name: 失败 (退出码: $code)"
            ((fail_count++))
        fi
    done

    echo ""
    echo "成功: $success_count | 失败: $fail_count"
    echo ""
    echo "输出文件目录: $OUTPUT_DIR"
    ls -la "$OUTPUT_DIR"/jd_iphone17* 2>/dev/null || echo "（暂无输出文件）"
    echo ""
    echo -e "${BLUE}============================================================${NC}"

    return $exit_code
}

main
exit $?
