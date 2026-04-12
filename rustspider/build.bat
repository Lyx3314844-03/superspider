@echo off
setlocal
cd /d "%~dp0"
cargo build --release
