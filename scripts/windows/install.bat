@echo off
setlocal

cd /d "%~dp0\..\.."

echo ========================================
echo Spider Framework Suite Windows Installer
echo ========================================

where python >nul 2>nul || (
  echo [ERROR] Python is required
  exit /b 1
)

where go >nul 2>nul || (
  echo [ERROR] Go is required
  exit /b 1
)

where cargo >nul 2>nul || (
  echo [ERROR] Rust/Cargo is required
  exit /b 1
)

where mvn >nul 2>nul || (
  echo [ERROR] Maven is required
  exit /b 1
)

echo [INFO] Installing PySpider dependencies...
python -m pip install --upgrade pip || exit /b 1
python -m pip install -r pyspider\requirements.txt || exit /b 1
python -m pip install -e .\pyspider[dev] || exit /b 1

echo [INFO] Building GoSpider...
call gospider\build.bat || exit /b 1

echo [INFO] Building JavaSpider...
call javaspider\build.bat || exit /b 1

echo [INFO] Building RustSpider...
call rustspider\build.bat || exit /b 1

echo [INFO] Validating shared OS support...
python verify_operating_system_support.py --json || exit /b 1

echo [OK] Windows installation surface is ready.
