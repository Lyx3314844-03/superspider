@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify-superspider.ps1" %*
exit /b %ERRORLEVEL%
