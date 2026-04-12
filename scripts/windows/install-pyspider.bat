@echo off
setlocal

cd /d "%~dp0\..\.."

echo ========================================
echo PySpider Windows Installer
echo ========================================

where python >nul 2>nul || (
  echo [ERROR] Python is required
  exit /b 1
)

if not exist ".venv-pyspider\Scripts\python.exe" (
  echo [INFO] Creating virtual environment .venv-pyspider
  python -m venv .venv-pyspider || exit /b 1
)

call .venv-pyspider\Scripts\activate.bat || exit /b 1
python -m pip install --upgrade pip || exit /b 1
python -m pip install -r pyspider\requirements.txt || exit /b 1
python -m pip install -e .\pyspider || exit /b 1
python -m pyspider version || exit /b 1

echo [OK] PySpider is installed in .venv-pyspider
