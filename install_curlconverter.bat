@echo off
REM curlconverter 安装脚本 (Windows)

echo ========================================
echo 安装 curlconverter 工具
echo ========================================
echo.

REM 检查 npm 是否安装
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] npm 未安装，请先安装 Node.js
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

echo [1/2] 正在安装 Node.js curlconverter...
call npm install -g curlconverter

if %errorlevel% equ 0 (
    echo ✓ Node.js curlconverter 安装成功
) else (
    echo ✗ Node.js curlconverter 安装失败
)

echo.
echo [2/2] 正在安装 Python curlconverter...
python -m pip install curlconverter

if %errorlevel% equ 0 (
    echo ✓ Python curlconverter 安装成功
) else (
    echo ✗ Python curlconverter 安装失败
)

echo.
echo ========================================
echo 安装完成！
echo ========================================
echo.
echo 验证安装:
echo   npx curlconverter --version
echo   python -c "import curlconverter; print('Python OK')"
echo.
pause
