@echo off
setlocal
cd /d "%~dp0"
go run .\cmd\gospider %*
