# SuperSpider GitHub 发布脚本 (PowerShell)
# 用于将所有框架发布到 GitHub

Write-Host "🚀 SuperSpider GitHub 发布脚本" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 配置
$GITHUB_USERNAME = if ($env:GITHUB_USERNAME) { $env:GITHUB_USERNAME } else { "YOUR_USERNAME" }
$REPO_NAME = "spider"
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

$defaultSuperSpiderRoot = Join-Path (Split-Path -Parent $PWD) "superspider"
if (-not $env:SUPERSPIDER_ROOT) {
    if (Test-Path $defaultSuperSpiderRoot) {
        $env:SUPERSPIDER_ROOT = (Resolve-Path $defaultSuperSpiderRoot).Path
        Write-Host "✅ 使用 SUPERSPIDER_ROOT: $($env:SUPERSPIDER_ROOT)" -ForegroundColor Green
    } else {
        Write-Host "❌ 未找到 superspider 仓库，请设置 SUPERSPIDER_ROOT 或在同级目录提供 superspider" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ 使用环境变量 SUPERSPIDER_ROOT: $($env:SUPERSPIDER_ROOT)" -ForegroundColor Green
}

New-Item -ItemType Directory -Force artifacts | Out-Null
New-Item -ItemType Directory -Force artifacts\quality-events-history | Out-Null
New-Item -ItemType Directory -Force artifacts\replay-history | Out-Null
New-Item -ItemType Directory -Force downloads | Out-Null
Write-Host "✅ 发布产物目录已准备" -ForegroundColor Green

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
Write-Host "📈 运行运行时生产基线校验..." -ForegroundColor Yellow

python .\verify_runtime_readiness.py --json
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 运行时生产基线校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 运行时生产基线校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "🧱 运行长周期稳定性校验..." -ForegroundColor Yellow

python .\verify_runtime_stability.py --json --markdown-out artifacts\runtime-stability.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 长周期稳定性校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 长周期稳定性校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "🧩 运行 graph/result contracts 校验..." -ForegroundColor Yellow

python .\verify_result_contracts.py --json --markdown-out RESULT_CONTRACTS_REPORT.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ graph/result contracts 校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ graph/result contracts 校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "🧬 运行统一核心能力面校验..." -ForegroundColor Yellow

python .\verify_runtime_core_capabilities.py --json
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 统一核心能力面校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 统一核心能力面校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "🛠️ 运行 operator products 校验..." -ForegroundColor Yellow

python .\verify_operator_products.py --json --markdown-out OPERATOR_PRODUCTS_REPORT.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ operator products 校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ operator products 校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "💻 运行三系统支持校验..." -ForegroundColor Yellow

python .\verify_operating_system_support.py --json --markdown-out artifacts\operating-system-support.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 三系统支持校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 三系统支持校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "🧬 运行内核同构校验..." -ForegroundColor Yellow

python .\verify_kernel_homogeneity.py --json --markdown-out KERNEL_HOMOGENEITY_REPORT.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 内核同构校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 内核同构校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "📡 运行可观测性证据校验..." -ForegroundColor Yellow

python .\verify_observability_evidence.py --json --markdown-out OBSERVABILITY_EVIDENCE_REPORT.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 可观测性证据校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 可观测性证据校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "🗃️ 运行缓存与增量抓取证据校验..." -ForegroundColor Yellow

python .\verify_cache_incremental_evidence.py --json --markdown-out CACHE_INCREMENTAL_EVIDENCE_REPORT.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 缓存与增量抓取证据校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 缓存与增量抓取证据校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 运行生态面成熟度校验..." -ForegroundColor Yellow

python .\verify_ecosystem_readiness.py --json --markdown-out ECOSYSTEM_READINESS_REPORT.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 生态面成熟度校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 生态面成熟度校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "🛒 运行生态市场面校验..." -ForegroundColor Yellow

python .\verify_ecosystem_marketplace.py --json --markdown-out ECOSYSTEM_MARKETPLACE_REPORT.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 生态市场面校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 生态市场面校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "📦 运行公开安装链路校验..." -ForegroundColor Yellow

python .\verify_public_install_chain.py --json --markdown-out PUBLIC_INSTALL_CHAIN_REPORT.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 公开安装链路校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 公开安装链路校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "🏭 运行行业证明面校验..." -ForegroundColor Yellow

python .\verify_industry_proof_surface.py --json --markdown-out INDUSTRY_PROOF_SURFACE_REPORT.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 行业证明面校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 行业证明面校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "🧪 运行 anti-bot 回放语料校验..." -ForegroundColor Yellow

python .\validate_antibot_replays.py --json
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ anti-bot 回放语料校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ anti-bot 回放语料校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "🧭 运行 workflow/browser 回放校验..." -ForegroundColor Yellow

python .\validate_workflow_replays.py --json
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ workflow/browser 回放校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ workflow/browser 回放校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "☕ 生成 JavaSpider captcha 闭环摘要..." -ForegroundColor Yellow

python .\verify_javaspider_captcha_summary.py --json
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ JavaSpider captcha 闭环摘要失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ JavaSpider captcha 闭环摘要通过" -ForegroundColor Green
Write-Host ""
Write-Host "🐍 生成 PySpider 高并发摘要..." -ForegroundColor Yellow

python .\verify_pyspider_concurrency_summary.py --json
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ PySpider 高并发摘要失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ PySpider 高并发摘要通过" -ForegroundColor Green
Write-Host ""
Write-Host "🦀 生成 Rust browser live-like 摘要..." -ForegroundColor Yellow

python .\verify_rust_browser_summary.py --json
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Rust browser live-like 摘要失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ Rust browser live-like 摘要通过" -ForegroundColor Green
Write-Host ""
Write-Host "📊 生成 replay 总看板..." -ForegroundColor Yellow

python .\verify_replay_dashboard.py --json
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ replay 总看板校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ replay 总看板通过" -ForegroundColor Green
Write-Host ""
Write-Host "📉 生成 replay 趋势报告..." -ForegroundColor Yellow

python .\verify_replay_trends.py --json
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ replay 趋势报告失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ replay 趋势报告通过" -ForegroundColor Green
Write-Host ""
Write-Host "🕸️ 生成 GoSpider distributed 韧性摘要..." -ForegroundColor Yellow

python .\verify_gospider_distributed_summary.py --json
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ GoSpider distributed 韧性摘要失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ GoSpider distributed 韧性摘要通过" -ForegroundColor Green
Write-Host ""
Write-Host "🧩 生成 Rust distributed 摘要..." -ForegroundColor Yellow

python .\verify_rust_distributed_summary.py --json
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Rust distributed 摘要失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ Rust distributed 摘要通过" -ForegroundColor Green
Write-Host ""
Write-Host "🦀 生成 Rust preflight 摘要..." -ForegroundColor Yellow

python .\verify_rust_preflight_summary.py --json
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Rust preflight 摘要失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ Rust preflight 摘要通过" -ForegroundColor Green
Write-Host ""
Write-Host "📚 校验质量策略治理..." -ForegroundColor Yellow

python .\verify_quality_policy_governance.py --json
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 质量策略治理校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 质量策略治理校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "🧾 生成框架评分卡..." -ForegroundColor Yellow

python .\generate_framework_scorecard.py --json --markdown-out artifacts\framework-scorecard.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 框架评分卡生成失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 框架评分卡生成通过" -ForegroundColor Green
Write-Host ""
Write-Host "📏 校验框架标准矩阵..." -ForegroundColor Yellow

python .\verify_framework_standards.py --json --markdown-out artifacts\framework-standards.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 框架标准矩阵校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 框架标准矩阵校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "🚦 运行质量阈值校验..." -ForegroundColor Yellow

python .\verify_quality_thresholds.py --json --profile strict --markdown-out artifacts\quality-thresholds.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 质量阈值校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 质量阈值校验通过" -ForegroundColor Green
Write-Host ""
Write-Host "📣 生成质量事件流..." -ForegroundColor Yellow

python .\verify_quality_events.py --json --snapshot-out artifacts\quality-events-history\current-events.json --compact-out artifacts\quality-events.compact.json --ndjson-out artifacts\quality-events.ndjson
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 质量事件流校验失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 质量事件流通过" -ForegroundColor Green
Write-Host ""
Write-Host "📦 生成 release baseline bundle..." -ForegroundColor Yellow

python .\generate_baseline_bundle.py --json --quality-profile strict --markdown-out artifacts\baseline-bundle.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ release baseline bundle 生成失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ release baseline bundle 生成通过" -ForegroundColor Green
Write-Host ""
Write-Host "📘 生成统一完成度报告..." -ForegroundColor Yellow

python .\generate_framework_completion_report.py --json --markdown-out CURRENT_FRAMEWORK_COMPLETION_REPORT.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 统一完成度报告生成失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 统一完成度报告通过" -ForegroundColor Green
Write-Host ""
Write-Host "🔗 运行本地集成联调..." -ForegroundColor Yellow

python .\verify_local_integrations.py --json --markdown-out LOCAL_INTEGRATIONS_REPORT.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 本地集成联调失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 本地集成联调通过" -ForegroundColor Green
Write-Host ""
Write-Host "🎞️ 运行媒体黑盒验证..." -ForegroundColor Yellow

python .\verify_media_blackbox.py --json --markdown-out MEDIA_BLACKBOX_REPORT.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 媒体黑盒验证失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 媒体黑盒验证通过" -ForegroundColor Green
Write-Host ""
Write-Host "🚦 运行发布就绪门禁..." -ForegroundColor Yellow

python .\verify_release_ready.py --json --markdown-out RELEASE_READINESS_REPORT.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 发布就绪门禁失败，已停止发布" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ 发布就绪门禁通过" -ForegroundColor Green
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

$currentOrigin = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0 -and $currentOrigin) {
    Write-Host "🔗 当前 origin: $currentOrigin" -ForegroundColor Cyan
} else {
    Write-Host "🔗 当前 origin: <未配置>" -ForegroundColor Cyan
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
        $existingOrigin = git remote get-url origin 2>$null
        git remote add origin $REPO_URL 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ 远程仓库添加成功" -ForegroundColor Green
        } else {
            if ($existingOrigin -and $existingOrigin -ne $REPO_URL) {
                Write-Host "⚠️  origin 与目标仓库不一致，正在修正" -ForegroundColor Yellow
                Write-Host "   旧值: $existingOrigin" -ForegroundColor Yellow
                Write-Host "   新值: $REPO_URL" -ForegroundColor Yellow
            }
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
        $existingOrigin = git remote get-url origin 2>$null
        git remote add origin $REPO_URL 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ 远程仓库添加成功" -ForegroundColor Green
        } else {
            if ($existingOrigin -and $existingOrigin -ne $REPO_URL) {
                Write-Host "⚠️  origin 与目标仓库不一致，正在修正" -ForegroundColor Yellow
                Write-Host "   旧值: $existingOrigin" -ForegroundColor Yellow
                Write-Host "   新值: $REPO_URL" -ForegroundColor Yellow
            }
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
        Write-Host "   git remote set-url origin https://github.com/YOUR_USERNAME/spider.git"
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
