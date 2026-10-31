@echo off
title MOTORE_PREZZI_AI - dashboard interattiva
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
python cli.py dash
echo.
if exist "%~dp0output\dashboard.html" start "" "%~dp0output\dashboard.html"
echo Dashboard generata: output\dashboard.html
pause
