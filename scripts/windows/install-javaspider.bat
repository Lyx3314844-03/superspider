@echo off
setlocal

cd /d "%~dp0\..\.."

echo ========================================
echo JavaSpider Windows Installer
echo ========================================

where java >nul 2>nul || (
  echo [ERROR] Java 17+ is required
  exit /b 1
)

where mvn >nul 2>nul || (
  echo [ERROR] Maven is required
  exit /b 1
)

mvn -q -f javaspider\pom.xml -DskipTests -Dmaven.javadoc.skip=true package dependency:copy-dependencies || exit /b 1

if not exist "javaspider\target" (
  echo [ERROR] Expected build output directory javaspider\target was not produced
  exit /b 1
)

echo [OK] JavaSpider package is ready in javaspider\target
