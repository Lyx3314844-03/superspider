@echo off
setlocal

cd /d "%~dp0\..\.."

echo ========================================
echo Spider Framework Suite Windows Verify
echo ========================================

python verify_operating_system_support.py --json || exit /b 1
python verify_env.py --json || exit /b 1
python smoke_test.py --json || exit /b 1

echo [OK] Windows verification completed.
