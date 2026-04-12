@echo off
setlocal

cd /d "%~dp0\..\.."

echo ========================================
echo RustSpider Windows Installer
echo ========================================

where cargo >nul 2>nul || (
  echo [ERROR] Rust/Cargo is required
  exit /b 1
)

call rustspider\build.bat || exit /b 1

if not exist "rustspider\target\release\rustspider.exe" (
  echo [ERROR] Expected binary rustspider\target\release\rustspider.exe was not produced
  exit /b 1
)

echo [OK] RustSpider binary is ready at rustspider\target\release\rustspider.exe
