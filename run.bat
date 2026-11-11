@echo off
setlocal EnableDelayedExpansion
title BlackKnight
cd /d "%~dp0"

for /F %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "RED=%ESC%[91m"
set "DIM=%ESC%[90m"
set "GRN=%ESC%[92m"
set "RST=%ESC%[0m"

echo.
echo %RED%  B L A C K  K N I G H T  %RST%
echo %DIM%  launcher%RST%
echo.

REM ── Find Python ──
set "PY="
where python >nul 2>nul
if not errorlevel 1 set "PY=python"
if not defined PY (
    where py >nul 2>nul
    if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
    echo %RED%[x]%RST% python not found in PATH.
    pause
    exit /b 1
)

echo %DIM%[i]%RST% python : %PY%
echo %DIM%[i]%RST% folder : %CD%
echo.

REM ── Quick import check (silent on success) ──
%PY% -c "import openai, rich, httpx, dotenv, requests, bs4" >nul 2>nul
if errorlevel 1 (
    echo %RED%[x]%RST% some packages are missing.
    echo     Run:  %PY% -m pip install -r requirements.txt
    echo     Or:   %PY% -m pip install openai rich httpx python-dotenv requests beautifulsoup4
    pause
    exit /b 1
)

REM ── Launch ──
echo %GRN%[ok]%RST% launching BlackKnight CLI in a new window...
echo.
start "BlackKnight" cmd /k "%PY% main.py %*"

echo %GRN%[ok]%RST% launcher done. This window closes in 2s.
timeout /t 2 /nobreak >nul
exit /b 0