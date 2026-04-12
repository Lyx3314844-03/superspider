@echo off
setlocal

cd /d "%~dp0\..\.."

echo ========================================
echo GoSpider Windows Installer
echo ========================================

where go >nul 2>nul || (
  echo [ERROR] Go is required
  exit /b 1
)

call gospider\build.bat || exit /b 1

if not exist "gospider\gospider.exe" (
  echo [ERROR] Expected binary gospider\gospider.exe was not produced
  exit /b 1
)

echo [OK] GoSpider binary is ready at gospider\gospider.exe
