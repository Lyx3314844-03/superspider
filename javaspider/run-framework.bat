@echo off
setlocal
cd /d "%~dp0"
call mvn -q -DskipTests compile dependency:copy-dependencies
if errorlevel 1 exit /b 1
java -cp "target\classes;target\dependency\*" com.javaspider.EnhancedSpider %*
