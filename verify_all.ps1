# 验证所有框架代码
Write-Host "===== 验证所有框架代码 =====" -ForegroundColor Cyan

# 1. pyspider
Write-Host "`n[1/4] 检查 pyspider..." -ForegroundColor Yellow
cd pyspider
python -m py_compile core/spider.py core/exceptions.py core/security.py downloader/downloader.py 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ pyspider Python 语法检查通过" -ForegroundColor Green
} else {
    Write-Host "  ✗ pyspider 检查失败" -ForegroundColor Red
}
cd ..

# 2. gospider
Write-Host "`n[2/4] 检查 gospider..." -ForegroundColor Yellow
cd gospider
go build -o gospider_test.exe ./cmd/gospider/main.go 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ gospider Go 编译通过" -ForegroundColor Green
    Remove-Item gospider_test.exe -ErrorAction SilentlyContinue
} else {
    Write-Host "  ✗ gospider 编译失败" -ForegroundColor Red
}
cd ..

# 3. javaspider
Write-Host "`n[3/4] 检查 javaspider..." -ForegroundColor Yellow
cd javaspider
mvn compile -q 2>&1 | Select-String "ERROR"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✓ javaspider Java 编译通过" -ForegroundColor Green
} else {
    Write-Host "  ✗ javaspider 编译失败" -ForegroundColor Red
}
cd ..

# 4. rustspider
Write-Host "`n[4/4] 检查 rustspider..." -ForegroundColor Yellow
cd rustspider
cargo check 2>&1 | Select-String "error"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✓ rustspider Rust 检查通过" -ForegroundColor Green
} else {
    Write-Host "  ✗ rustspider 检查失败" -ForegroundColor Red
}
cd ..

Write-Host "`n===== 验证完成 =====" -ForegroundColor Cyan
