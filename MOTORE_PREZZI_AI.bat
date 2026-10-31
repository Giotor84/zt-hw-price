@echo off
title MOTORE_PREZZI_AI
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

if /i "%~1"=="perf" goto PERF
if /i "%~1"=="dash" goto DASH
if not "%~1"=="" goto SEARCH

:WATCH
echo ============================================================
echo  MOTORE_PREZZI_AI  -  aggiornamento watchlist (hardware AI)
echo ============================================================
python cli.py watch
echo.
if exist "%~dp0output\watch_report.html" start "" "%~dp0output\watch_report.html"
goto END

:PERF
echo ============================================================
echo  MOTORE_PREZZI_AI  -  prestazioni LLM / termica per device
echo ============================================================
python cli.py perf
echo.
if exist "%~dp0output\performance.html" start "" "%~dp0output\performance.html"
goto END

:DASH
echo ============================================================
echo  MOTORE_PREZZI_AI  -  dashboard interattiva prestazioni
echo ============================================================
python cli.py dash
echo.
if exist "%~dp0output\dashboard.html" start "" "%~dp0output\dashboard.html"
goto END

:SEARCH
echo ============================================================
echo  MOTORE_PREZZI_AI  -  ricerca: %*
echo ============================================================
python cli.py search %*
echo.
if exist "%~dp0output\report.html" start "" "%~dp0output\report.html"

:END
echo.
pause
