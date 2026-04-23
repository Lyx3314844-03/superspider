@echo off
chcp 65001 >nul 2>&1
REM ============================================================================
REM 京东 iPhone 17 价格爬虫 - Windows 统一运行脚本
REM
REM 使用四个爬虫框架 (PySpider, GoSpider, RustSpider, JavaSpider)
REM
REM 使用方法: run_all_spiders.bat [选项]
REM
REM 选项:
REM   --pages <n>     爬取页数 (默认: 5)
REM   --delay <n>     请求延迟秒数 (默认: 3)
REM   --proxy <addr>  代理地址
REM   --framework <f> 只运行指定框架
REM   --skip-build    跳过编译
REM   --help          显示帮助
REM ============================================================================

setlocal enabledelayedexpansion

REM 默认配置
set PAGES=5
set DELAY=3
set PROXY=
set FRAMEWORK=all
set SKIP_BUILD=false

REM 获取脚本所在目录
set SCRIPT_DIR=%~dp0
set OUTPUT_DIR=%SCRIPT_DIR%output

REM 确保输出目录存在
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

REM 解析参数
:parse_args
if "%~1"=="" goto :run
if "%~1"=="--pages" (
    set PAGES=%~2
    shift & shift & goto :parse_args
)
if "%~1"=="--delay" (
    set DELAY=%~2
    shift & shift & goto :parse_args
)
if "%~1"=="--proxy" (
    set PROXY=%~2
    shift & shift & goto :parse_args
)
if "%~1"=="--framework" (
    set FRAMEWORK=%~2
    shift & shift & goto :parse_args
)
if "%~1"=="--skip-build" (
    set SKIP_BUILD=true
    shift & goto :parse_args
)
if "%~1"=="--help" (
    call :show_help
    exit /b 0
)
shift & goto :parse_args

:show_help
echo 京东 iPhone 17 价格爬虫 - Windows 运行脚本
echo.
echo 用法: run_all_spiders.bat [选项]
echo.
echo 选项:
echo   --pages ^<n^>      爬取页数 (默认: 5)
echo   --delay ^<n^>      请求延迟秒数 (默认: 3)
echo   --proxy ^<addr^>   代理地址
echo   --framework ^<f^>  指定框架 (pyspider/gospider/rustspider/javaspider/all)
echo   --skip-build       跳过编译
echo   --help             显示帮助
echo.
exit /b 0

:print_banner
echo ============================================================
echo   京东 iPhone 17 价格爬虫 - 四框架联合爬取
echo ============================================================
echo 框架: PySpider (Python), GoSpider (Go), RustSpider (Rust), JavaSpider (Java)
echo 页数: %PAGES% | 延迟: %DELAY%s
if not "%PROXY%"=="" echo 代理: %PROXY%
echo 输出目录: %OUTPUT_DIR%
echo ============================================================
echo.
exit /b 0

:run_pyspider
echo.
echo ============================================================
echo   开始运行: PySpider (Python)
echo ============================================================
cd /d "%SCRIPT_DIR%pyspider"
if not "%PROXY%"=="" (
    python spider_jd_iphone17.py --pages %PAGES% --delay %DELAY% --proxy %PROXY%
) else (
    python spider_jd_iphone17.py --pages %PAGES% --delay %DELAY%
)
set PYSPIDER_EXIT=%ERRORLEVEL%
cd /d "%SCRIPT_DIR%"
exit /b %PYSPIDER_EXIT%

:run_gospider
echo.
echo ============================================================
echo   开始运行: GoSpider (Go)
echo ============================================================
cd /d "%SCRIPT_DIR%gospider"
if "%SKIP_BUILD%"=="false" (
    echo 正在编译 GoSpider...
    go build -o gospider_jd.exe .\cmd\jd_iphone17\
    if !ERRORLEVEL! neq 0 (
        echo GoSpider 编译失败
        cd /d "%SCRIPT_DIR%"
        exit /b 1
    )
    echo 编译完成
)
if not "%PROXY%"=="" (
    gospider_jd.exe --pages %PAGES% --delay %DELAY% --proxy %PROXY%
) else (
    gospider_jd.exe --pages %PAGES% --delay %DELAY%
)
set GOSPIDER_EXIT=%ERRORLEVEL%
cd /d "%SCRIPT_DIR%"
exit /b %GOSPIDER_EXIT%

:run_rustspider
echo.
echo ============================================================
echo   开始运行: RustSpider (Rust)
echo ============================================================
cd /d "%SCRIPT_DIR%rustspider"
if "%SKIP_BUILD%"=="false" (
    echo 正在编译 RustSpider...
    cargo build --bin jd_iphone17 --release 2>nul
    if !ERRORLEVEL! neq 0 (
        echo RustSpider 编译失败
        cd /d "%SCRIPT_DIR%"
        exit /b 1
    )
    echo 编译完成
)
if not "%PROXY%"=="" (
    .\target\release\jd_iphone17.exe --pages %PAGES% --delay %DELAY% --proxy %PROXY%
) else (
    .\target\release\jd_iphone17.exe --pages %PAGES% --delay %DELAY%
)
set RUSTSPIDER_EXIT=%ERRORLEVEL%
cd /d "%SCRIPT_DIR%"
exit /b %RUSTSPIDER_EXIT%

:run_javaspider
echo.
echo ============================================================
echo   开始运行: JavaSpider (Java)
echo ============================================================
cd /d "%SCRIPT_DIR%javaspider"

if "%SKIP_BUILD%"=="false" (
    echo 正在编译 JavaSpider...
    if not exist "target\examples" mkdir target\examples
    set CLASSPATH=target\classes;lib\*
    javac -cp "!CLASSPATH!" -encoding UTF-8 -d target\examples src\main\java\com\javaspider\examples\jd\JDiPhone17FrameworkSpider.java 2>nul
    if !ERRORLEVEL! neq 0 (
        echo JavaSpider 编译失败
        cd /d "%SCRIPT_DIR%"
        exit /b 1
    )
    echo 编译完成
)

set JAVA_ARGS=--pages %PAGES% --delay %DELAY%000
set JAVA_CLASSPATH=target\examples;target\classes;lib\*
java -cp "!JAVA_CLASSPATH!" com.javaspider.examples.jd.JDiPhone17FrameworkSpider !JAVA_ARGS!
set JAVASPIDER_EXIT=%ERRORLEVEL%
cd /d "%SCRIPT_DIR%"
exit /b %JAVASPIDER_EXIT%

:run
call :print_banner

set SUCCESS_COUNT=0
set FAIL_COUNT=0

if "%FRAMEWORK%"=="pyspider" (
    call :run_pyspider
    if !ERRORLEVEL! equ 0 (set /a SUCCESS_COUNT+=1) else (set /a FAIL_COUNT+=1)
) else if "%FRAMEWORK%"=="gospider" (
    call :run_gospider
    if !ERRORLEVEL! equ 0 (set /a SUCCESS_COUNT+=1) else (set /a FAIL_COUNT+=1)
) else if "%FRAMEWORK%"=="rustspider" (
    call :run_rustspider
    if !ERRORLEVEL! equ 0 (set /a SUCCESS_COUNT+=1) else (set /a FAIL_COUNT+=1)
) else if "%FRAMEWORK%"=="javaspider" (
    call :run_javaspider
    if !ERRORLEVEL! equ 0 (set /a SUCCESS_COUNT+=1) else (set /a FAIL_COUNT+=1)
) else (
    call :run_pyspider
    if !ERRORLEVEL! equ 0 (set /a SUCCESS_COUNT+=1) else (set /a FAIL_COUNT+=1)

    call :run_gospider
    if !ERRORLEVEL! equ 0 (set /a SUCCESS_COUNT+=1) else (set /a FAIL_COUNT+=1)

    call :run_rustspider
    if !ERRORLEVEL! equ 0 (set /a SUCCESS_COUNT+=1) else (set /a FAIL_COUNT+=1)

    call :run_javaspider
    if !ERRORLEVEL! equ 0 (set /a SUCCESS_COUNT+=1) else (set /a FAIL_COUNT+=1)
)

echo.
echo ============================================================
echo   运行结果总结
echo ============================================================
echo 成功: %SUCCESS_COUNT% | 失败: %FAIL_COUNT%
echo.
echo 输出文件:
dir /b "%OUTPUT_DIR%\*jd_iphone17*" 2>nul || echo (暂无输出文件)
echo.
echo ============================================================

endlocal
