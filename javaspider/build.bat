@echo off
REM JavaSpider 构建脚本

echo ========================================
echo JavaSpider 构建工具
echo ========================================

REM 检查 Java 版本
java -version 2>&1 | findstr /C:"version"
if errorlevel 1 (
    echo [错误] 未找到 Java，请安装 Java 17+
    exit /b 1
)

REM 检查 Maven
mvn -version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Maven，请安装 Maven 3.6+
    exit /b 1
)

setlocal

REM 解析参数
set COMMAND=%1
set PROFILE=%2

if "%COMMAND%"=="" set COMMAND=build

goto %COMMAND% 2>nul || goto :help

:build
    echo [信息] 开始构建...
    mvn clean package -DskipTests
    if errorlevel 1 (
        echo [错误] 构建失败
        exit /b 1
    )
    echo [成功] 构建完成
    goto :end

:test
    echo [信息] 运行测试...
    mvn clean test
    if errorlevel 1 (
        echo [错误] 测试失败
        exit /b 1
    )
    echo [成功] 测试通过
    goto :end

:run
    echo [信息] 运行程序...
    mvn exec:java -Dexec.mainClass="com.javaspider.examples.AdvancedSpiderExample"
    goto :end

:clean
    echo [信息] 清理...
    mvn clean
    echo [成功] 清理完成
    goto :end

:install
    echo [信息] 安装到本地仓库...
    mvn clean install
    goto :end

:docker
    echo [信息] 构建 Docker 镜像...
    docker build -t javaspider:latest -f docker/Dockerfile .
    echo [成功] Docker 镜像构建完成
    goto :end

:help
    echo.
    echo 用法：build [命令]
    echo.
    echo 命令:
    echo   build    - 构建项目 (默认)
    echo   test     - 运行测试
    echo   run      - 运行示例
    echo   clean    - 清理
    echo   install  - 安装到本地仓库
    echo   docker   - 构建 Docker 镜像
    echo   help     - 显示帮助
    echo.

:end
endlocal
