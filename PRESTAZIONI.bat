@echo off
title MOTORE_PREZZI_AI - prestazioni
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo ============================================================
echo  MOTORE_PREZZI_AI  -  prestazioni LLM / termica per device
echo ============================================================
python cli.py perf
echo.
if exist "%~dp0output\performance.html" start "" "%~dp0output\performance.html"
echo.
pause
