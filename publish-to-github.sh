#!/bin/bash
# SuperSpider GitHub 发布脚本
# 用于将所有框架发布到 GitHub

set -e

echo "🚀 SuperSpider GitHub 发布脚本"
echo "================================"

# 配置
GITHUB_USERNAME="${GITHUB_USERNAME:-YOUR_USERNAME}"
REPO_NAME="superspider"
REPO_URL="https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
PUBLISH_MODE="${PUBLISH_MODE:-}"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "📋 发布前检查..."
echo ""

# 检查 Git
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Git 已安装${NC}"

# 检查 GitHub CLI
if command -v gh &> /dev/null; then
    echo -e "${GREEN}✅ GitHub CLI 已安装${NC}"
else
    echo -e "${YELLOW}⚠️  GitHub CLI 未安装，将使用 git 命令${NC}"
fi

# 检查各框架
echo ""
echo "🔍 检查各框架..."

# PySpider
if [ -d "pyspider" ]; then
    echo -e "${GREEN}✅ PySpider 目录存在${NC}"
else
    echo -e "${RED}❌ PySpider 目录不存在${NC}"
    exit 1
fi

# RustSpider
if [ -d "rustspider" ]; then
    echo -e "${GREEN}✅ RustSpider 目录存在${NC}"
else
    echo -e "${RED}❌ RustSpider 目录不存在${NC}"
    exit 1
fi

# GoSpider
if [ -d "gospider" ]; then
    echo -e "${GREEN}✅ GoSpider 目录存在${NC}"
else
    echo -e "${RED}❌ GoSpider 目录不存在${NC}"
    exit 1
fi

# JavaSpider
if [ -d "javaspider" ]; then
    echo -e "${GREEN}✅ JavaSpider 目录存在${NC}"
else
    echo -e "${RED}❌ JavaSpider 目录不存在${NC}"
    exit 1
fi

echo ""
echo "🩺 运行聚合环境校验..."

if command -v python3 &> /dev/null; then
    PYTHON_BIN="python3"
elif command -v python &> /dev/null; then
    PYTHON_BIN="python"
else
    echo -e "${RED}❌ Python 未安装，无法运行 verify_env.py${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python 已安装：${PYTHON_BIN}${NC}"
"${PYTHON_BIN}" ./verify_env.py --json
echo -e "${GREEN}✅ 聚合环境校验通过${NC}"

echo ""
echo "🏷️ 运行版本一致性校验..."
"${PYTHON_BIN}" ./verify_version.py --json
echo -e "${GREEN}✅ 版本一致性校验通过${NC}"

echo ""
echo "🔥 运行发布后 smoke test..."
"${PYTHON_BIN}" ./smoke_test.py --json
echo -e "${GREEN}✅ smoke test 通过${NC}"

echo ""
echo "📦 准备发布文件..."

# 创建 .gitignore
if [ ! -f ".gitignore" ]; then
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
*.egg-info/
dist/
build/

# Rust
target/
**/*.rs.bk
Cargo.lock

# Go
*.exe
*.test
*.out
go.sum

# Java
target/
*.class
*.jar
*.war
.mvn/

# 通用
*.log
*.tmp
.DS_Store
Thumbs.db
.idea/
.vscode/
*.swp
*.swo

# 测试数据
test_*.db
*.pkl
EOF

echo -e "${GREEN}✅ 创建 .gitignore${NC}"
else
    echo -e "${YELLOW}⚠️  已存在 .gitignore，保留当前文件${NC}"
fi

# 创建 LICENSE
if [ ! -f "LICENSE" ]; then
cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2026 SuperSpider Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF

echo -e "${GREEN}✅ 创建 LICENSE${NC}"
else
    echo -e "${YELLOW}⚠️  已存在 LICENSE，保留当前文件${NC}"
fi

# 创建 CONTRIBUTING.md
if [ ! -f "CONTRIBUTING.md" ]; then
cat > CONTRIBUTING.md << 'EOF'
# 贡献指南

欢迎贡献 SuperSpider 项目！

## 如何贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 代码规范

- Python: 遵循 PEP 8
- Rust: 遵循 Rust 风格指南
- Go: 遵循 Go 代码规范
- Java: 遵循 Google Java 风格

## 测试

提交 PR 前请确保所有测试通过。

## 许可证

通过贡献，您同意您的贡献遵循本项目的 MIT 许可证。
EOF

echo -e "${GREEN}✅ 创建 CONTRIBUTING.md${NC}"
else
    echo -e "${YELLOW}⚠️  已存在 CONTRIBUTING.md，保留当前文件${NC}"
fi

echo ""
echo "📝 初始化 Git 仓库..."

# 初始化 Git
if [ ! -d ".git" ]; then
    git init
    echo -e "${GREEN}✅ Git 仓库初始化完成${NC}"
else
    echo -e "${YELLOW}⚠️  Git 仓库已存在${NC}"
fi

# 添加所有文件
git add .
echo -e "${GREEN}✅ 文件已添加到暂存区${NC}"

if git diff --cached --quiet; then
    echo -e "${YELLOW}⚠️  暂存区没有变更，跳过提交${NC}"
else
    # 提交
    git commit -m "Initial commit: SuperSpider v1.0.0

- PySpider: Python 高性能异步爬虫
- RustSpider: Rust 系统级爬虫  
- GoSpider: Go 并发爬虫
- JavaSpider: Java 企业级爬虫

包含完整文档、示例和安装脚本"

    echo -e "${GREEN}✅ 提交完成${NC}"
fi

echo ""
echo "🚀 准备推送到 GitHub..."
echo ""
if [ -n "${PUBLISH_MODE}" ]; then
    case "${PUBLISH_MODE}" in
        https) choice="1" ;;
        ssh) choice="2" ;;
        skip) choice="3" ;;
        *)
            echo -e "${RED}❌ 无效的 PUBLISH_MODE: ${PUBLISH_MODE}${NC}"
            exit 1
            ;;
    esac
    echo "使用非交互发布模式: ${PUBLISH_MODE}"
else
    echo "请选择推送方式:"
    echo "1. 使用 HTTPS"
    echo "2. 使用 SSH"
    echo "3. 跳过推送（本地查看）"
    read -p "请输入选项 (1/2/3): " choice
fi

case $choice in
    1)
        if [ "${GITHUB_USERNAME}" != "YOUR_USERNAME" ]; then
            username="${GITHUB_USERNAME}"
            echo "使用环境变量 GITHUB_USERNAME: ${username}"
        else
            read -p "请输入 GitHub 用户名: " username
        fi
        REPO_URL="https://github.com/${username}/${REPO_NAME}.git"
        
        echo "📤 推送到 GitHub..."
        if git remote add origin ${REPO_URL} 2>/dev/null; then
            echo -e "${GREEN}✅ 远程仓库添加成功${NC}"
        else
            git remote set-url origin ${REPO_URL}
            echo -e "${YELLOW}⚠️  更新远程仓库 URL${NC}"
        fi
        
        git branch -M main
        git push -u origin main
        echo -e "${GREEN}✅ 推送成功！${NC}"
        echo ""
        echo "📦 仓库地址：${REPO_URL}"
        echo "🌐 GitHub 页面：https://github.com/${username}/${REPO_NAME}"
        ;;
    
    2)
        if [ "${GITHUB_USERNAME}" != "YOUR_USERNAME" ]; then
            username="${GITHUB_USERNAME}"
            echo "使用环境变量 GITHUB_USERNAME: ${username}"
        else
            read -p "请输入 GitHub 用户名: " username
        fi
        REPO_URL="git@github.com:${username}/${REPO_NAME}.git"
        
        echo "📤 推送到 GitHub..."
        if git remote add origin ${REPO_URL} 2>/dev/null; then
            echo -e "${GREEN}✅ 远程仓库添加成功${NC}"
        else
            git remote set-url origin ${REPO_URL}
            echo -e "${YELLOW}⚠️  更新远程仓库 URL${NC}"
        fi
        
        git branch -M main
        git push -u origin main
        echo -e "${GREEN}✅ 推送成功！${NC}"
        echo ""
        echo "📦 仓库地址：${REPO_URL}"
        echo "🌐 GitHub 页面：https://github.com/${username}/${REPO_NAME}"
        ;;
    
    3)
        echo -e "${YELLOW}⚠️  已跳过推送${NC}"
        echo ""
        echo "💡 提示：稍后可以手动推送:"
        echo "   git remote add origin https://github.com/YOUR_USERNAME/superspider.git"
        echo "   git push -u origin main"
        ;;
    
    *)
        echo -e "${RED}❌ 无效选项${NC}"
        exit 1
        ;;
esac

echo ""
echo "================================"
echo -e "${GREEN}🎉 发布完成！${NC}"
echo "================================"
echo ""
echo "下一步:"
echo "1. 在 GitHub 上查看仓库"
echo "2. 添加 README 徽章"
echo "3. 配置 GitHub Actions CI/CD"
echo "4. 添加 Release 标签"
echo ""
echo "感谢使用 SuperSpider！🚀"
