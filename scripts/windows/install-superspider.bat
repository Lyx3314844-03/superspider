@echo off
setlocal

cd /d "%~dp0\..\.."

echo ========================================
echo SuperSpider Windows Installer
echo ========================================

call scripts\windows\install-pyspider.bat || exit /b 1
call scripts\windows\install-gospider.bat || exit /b 1
call scripts\windows\install-rustspider.bat || exit /b 1
call scripts\windows\install-javaspider.bat || exit /b 1

echo [OK] SuperSpider Windows install completed
