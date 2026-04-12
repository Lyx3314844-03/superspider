# 最终验证脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  四框架代码最终验证" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$totalTests = 0
$passedTests = 0

# 1. pyspider
Write-Host "[1/4] pyspider 验证..." -ForegroundColor Yellow
cd pyspider
python -m py_compile core/spider.py core/exceptions.py core/security.py downloader/downloader.py 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Python 语法检查通过" -ForegroundColor Green
    $passedTests++
} else {
    Write-Host "  ✗ Python 语法检查失败" -ForegroundColor Red
}
$totalTests++

if (Test-Path "tests\test_benchmarks.py") {
    Write-Host "  ✓ 基准测试文件存在" -ForegroundColor Green
    $passedTests++
} else {
    Write-Host "  ✗ 基准测试文件缺失" -ForegroundColor Red
}
$totalTests++
cd ..

# 2. gospider
Write-Host ""
Write-Host "[2/4] gospider 验证..." -ForegroundColor Yellow
cd gospider
go build -o gospider_test.exe ./cmd/gospider/main_fixed.go 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Go 编译通过" -ForegroundColor Green
    $passedTests++
    Remove-Item gospider_test.exe -ErrorAction SilentlyContinue
} else {
    Write-Host "  ✗ Go 编译失败" -ForegroundColor Red
}
$totalTests++

if (Test-Path "core\spider_integration_test.go") {
    Write-Host "  ✓ 集成测试文件存在" -ForegroundColor Green
    $passedTests++
} else {
    Write-Host "  ✗ 集成测试文件缺失" -ForegroundColor Red
}
$totalTests++
cd ..

# 3. javaspider
Write-Host ""
Write-Host "[3/4] javaspider 验证..." -ForegroundColor Yellow
cd javaspider
$compileOutput = mvn compile -q 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Java 编译通过" -ForegroundColor Green
    $passedTests++
} else {
    Write-Host "  ✗ Java 编译失败" -ForegroundColor Red
    $compileOutput
}
$totalTests++

if (Test-Path "src\test\java\com\javaspider\core\SpiderEnhancedIntegrationTest.java") {
    Write-Host "  ✓ 集成测试文件存在" -ForegroundColor Green
    $passedTests++
} else {
    Write-Host "  ✗ 集成测试文件缺失" -ForegroundColor Red
}
$totalTests++
cd ..

# 4. rustspider
Write-Host ""
Write-Host "[4/4] rustspider 验证..." -ForegroundColor Yellow
cd rustspider
$checkOutput = cargo check 2>&1
$hasError = $checkOutput | Select-String "error" -CaseSensitive
if (-not $hasError) {
    Write-Host "  ✓ Rust 检查通过" -ForegroundColor Green
    $passedTests++
} else {
    Write-Host "  ✗ Rust 检查失败" -ForegroundColor Red
    $hasError
}
$totalTests++

$hasWarning = $checkOutput | Select-String "warning"
if (-not $hasWarning) {
    Write-Host "  ✓ 无警告" -ForegroundColor Green
    $passedTests++
} else {
    Write-Host "  ⚠ 有警告（可接受）" -ForegroundColor Yellow
}
$totalTests++

if (Test-Path "tests\integration_tests.rs") {
    Write-Host "  ✓ 集成测试文件存在" -ForegroundColor Green
    $passedTests++
} else {
    Write-Host "  ✗ 集成测试文件缺失" -ForegroundColor Red
}
$totalTests++
cd ..

# 总结
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  验证结果：$passedTests / $totalTests" -ForegroundColor $(if ($passedTests -eq $totalTests) { "Green" } else { "Yellow" })
Write-Host "========================================" -ForegroundColor Cyan

if ($passedTests -eq $totalTests) {
    Write-Host ""
    Write-Host "✓ 所有验证通过！" -ForegroundColor Green
    Write-Host ""
    exit 0
} else {
    Write-Host ""
    Write-Host "✗ 部分验证未通过" -ForegroundColor Red
    Write-Host ""
    exit 1
}
