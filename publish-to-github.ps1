# SuperSpider GitHub 发布脚本 (PowerShell)
# 用于将所有框架发布到 GitHub

Write-Host "🚀 SuperSpider GitHub 发布脚本" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 配置
$GITHUB_USERNAME = if ($env:GITHUB_USERNAME) { $env:GITHUB_USERNAME } else { "YOUR_USERNAME" }
$REPO_NAME = "superspider"
$REPO_URL = "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
$PUBLISH_MODE = if ($env:PUBLISH_MODE) { $env:PUBLISH_MODE.ToLowerInvariant() } else { "" }

# 检查 Git
Write-Host "📋 发布前检查..." -ForegroundColor Yellow
Write-Host ""

try {
    $gitVersion = git --version
    Write-Host "✅ Git 已安装：$gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Git 未安装" -ForegroundColor Red
    exit 1
}

# 检查各框架目录
$frameworks = @("pyspider", "rustspider", "gospider", "javaspider")

foreach ($framework in $frameworks) {
    if (Test-Path $framework) {
        Write-Host "✅ $framework 目录存在" -ForegroundColor Green
    } else {
        Write-Host "❌ $framework 目录不存在" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "🩺 运行聚合环境校验..." -ForegroundColor Yellow

try {
    $pythonCommand = Get-Command python -ErrorAction Stop
    Write-Host "✅ Python 已安装：$($pythonCommand.Source)" -ForegroundColor Green
} catch {
    Write-Host "❌ Python 未安装，无法运行 verify_env.py" -ForegroundColor Red
    exit 1
}

python .\verify_env.py --json
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 聚合环境校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 聚合环境校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "🏷️ 运行版本一致性校验..." -ForegroundColor Yellow

python .\verify_version.py --json
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 版本一致性校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 版本一致性校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "🔥 运行发布后 smoke test..." -ForegroundColor Yellow

python .\smoke_test.py --json
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ smoke test 失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ smoke test 通过" -ForegroundColor Green
Write-Host ""
Write-Host "📦 准备发布文件..." -ForegroundColor Yellow

# 创建 .gitignore
$gitignoreContent = @"
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
"@

if (-not (Test-Path ".gitignore")) {
    $gitignoreContent | Out-File -FilePath ".gitignore" -Encoding UTF8
    Write-Host "✅ 创建 .gitignore" -ForegroundColor Green
} else {
    Write-Host "⚠️  已存在 .gitignore，保留当前文件" -ForegroundColor Yellow
}

# 创建 LICENSE
$licenseContent = @"
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
"@

if (-not (Test-Path "LICENSE")) {
    $licenseContent | Out-File -FilePath "LICENSE" -Encoding UTF8
    Write-Host "✅ 创建 LICENSE" -ForegroundColor Green
} else {
    Write-Host "⚠️  已存在 LICENSE，保留当前文件" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📝 初始化 Git 仓库..." -ForegroundColor Yellow

# 初始化 Git
if (-not (Test-Path ".git")) {
    git init
    Write-Host "✅ Git 仓库初始化完成" -ForegroundColor Green
} else {
    Write-Host "⚠️  Git 仓库已存在" -ForegroundColor Yellow
}

# 添加所有文件
git add .
Write-Host "✅ 文件已添加到暂存区" -ForegroundColor Green

git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "⚠️  暂存区没有变更，跳过提交" -ForegroundColor Yellow
} else {
    # 提交
    git commit -m "Initial commit: SuperSpider v1.0.0

- PySpider: Python 高性能异步爬虫
- RustSpider: Rust 系统级爬虫  
- GoSpider: Go 并发爬虫
- JavaSpider: Java 企业级爬虫

包含完整文档、示例和安装脚本"

    Write-Host "✅ 提交完成" -ForegroundColor Green
}

Write-Host ""
Write-Host "🚀 准备推送到 GitHub..." -ForegroundColor Yellow
Write-Host ""

# 选择推送方式
if ($PUBLISH_MODE) {
    $choice = switch ($PUBLISH_MODE) {
        "https" { "1" }
        "ssh" { "2" }
        "skip" { "3" }
        default {
            Write-Host "❌ 无效的 PUBLISH_MODE: $PUBLISH_MODE" -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "使用非交互发布模式: $PUBLISH_MODE" -ForegroundColor Cyan
} else {
    Write-Host "请选择推送方式:" -ForegroundColor Cyan
    Write-Host "1. 使用 HTTPS"
    Write-Host "2. 使用 SSH"
    Write-Host "3. 跳过推送（本地查看）"
    $choice = Read-Host "请输入选项 (1/2/3)"
}

switch ($choice) {
    "1" {
        if ($GITHUB_USERNAME -ne "YOUR_USERNAME") {
            $username = $GITHUB_USERNAME
            Write-Host "使用环境变量 GITHUB_USERNAME: $username" -ForegroundColor Cyan
        } else {
            $username = Read-Host "请输入 GitHub 用户名"
        }
        $REPO_URL = "https://github.com/${username}/${REPO_NAME}.git"
        
        Write-Host "📤 推送到 GitHub..." -ForegroundColor Yellow
        git remote add origin $REPO_URL 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ 远程仓库添加成功" -ForegroundColor Green
        } else {
            git remote set-url origin $REPO_URL
            Write-Host "⚠️  更新远程仓库 URL" -ForegroundColor Yellow
        }
        
        git branch -M main
        git push -u origin main
        Write-Host "✅ 推送成功！" -ForegroundColor Green
        Write-Host ""
        Write-Host "📦 仓库地址：$REPO_URL" -ForegroundColor Cyan
        Write-Host "🌐 GitHub 页面：https://github.com/${username}/${REPO_NAME}" -ForegroundColor Cyan
    }
    
    "2" {
        if ($GITHUB_USERNAME -ne "YOUR_USERNAME") {
            $username = $GITHUB_USERNAME
            Write-Host "使用环境变量 GITHUB_USERNAME: $username" -ForegroundColor Cyan
        } else {
            $username = Read-Host "请输入 GitHub 用户名"
        }
        $REPO_URL = "git@github.com:${username}/${REPO_NAME}.git"
        
        Write-Host "📤 推送到 GitHub..." -ForegroundColor Yellow
        git remote add origin $REPO_URL 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ 远程仓库添加成功" -ForegroundColor Green
        } else {
            git remote set-url origin $REPO_URL
            Write-Host "⚠️  更新远程仓库 URL" -ForegroundColor Yellow
        }
        
        git branch -M main
        git push -u origin main
        Write-Host "✅ 推送成功！" -ForegroundColor Green
        Write-Host ""
        Write-Host "📦 仓库地址：$REPO_URL" -ForegroundColor Cyan
        Write-Host "🌐 GitHub 页面：https://github.com/${username}/${REPO_NAME}" -ForegroundColor Cyan
    }
    
    "3" {
        Write-Host "⚠️  已跳过推送" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "💡 提示：稍后可以手动推送:" -ForegroundColor Cyan
        Write-Host "   git remote add origin https://github.com/YOUR_USERNAME/superspider.git"
        Write-Host "   git push -u origin main"
    }
    
    default {
        Write-Host "❌ 无效选项" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "🎉 发布完成！" -ForegroundColor Green
Write-Host "================================"
Write-Host ""
Write-Host "下一步:" -ForegroundColor Cyan
Write-Host "1. 在 GitHub 上查看仓库"
Write-Host "2. 添加 README 徽章"
Write-Host "3. 配置 GitHub Actions CI/CD"
Write-Host "4. 添加 Release 标签"
Write-Host ""
Write-Host "感谢使用 SuperSpider！🚀" -ForegroundColor Green
