@echo off
setlocal EnableDelayedExpansion
title BlackKnight

REM ─────────────────────────────────────────────────────────────
REM  BlackKnight launcher
REM  Launches main.py in a separate window, then closes.
REM ─────────────────────────────────────────────────────────────

cd /d "%~dp0"

REM ── ANSI colors ──
for /F %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "RED=%ESC%[91m"
set "DIM=%ESC%[90m"
set "GRN=%ESC%[92m"
set "RST=%ESC%[0m"

echo.
echo %RED%  B L A C K  K N I G H T  %RST%
echo %DIM%  launcher%RST%
echo.

REM ── CHECK: Python ──
where python >nul 2>nul
if errorlevel 1 (
    echo %RED%[x]%RST% python not found in PATH.
    pause
    exit /b 1
)

REM ── CHECK: main.py ──
if not exist "main.py" (
    echo %RED%[x]%RST% main.py not found in %CD%
    pause
    exit /b 1
)

REM ── CHECK: .env present? (config.py validates the key) ──
if not exist ".env" (
    echo %DIM%[i]%RST% .env not found — falling back to environment variables.
    echo     Copy .env.example to .env and fill in BK_API_KEY.
    echo.
)

REM ── CHECK + INSTALL: dependencies (pkg:import) ──
echo %DIM%[i]%RST% checking dependencies...
echo.

set "PKGS=openai:openai rich:rich requests:requests beautifulsoup4:bs4 httpx:httpx python-dotenv:dotenv"

for %%p in (%PKGS%) do (
    for /f "tokens=1,2 delims=:" %%a in ("%%p") do (
        python -c "import %%b" >nul 2>nul
        if errorlevel 1 (
            echo   %DIM%install %%a...%RST%
            python -m pip install --quiet --disable-pip-version-check %%a >nul 2>nul
            if errorlevel 1 (
                echo   %RED%[x]%RST% failed to install %%a
                pause
                exit /b 1
            )
            echo   %GRN%ok%RST% %%a
        ) else (
            echo   %GRN%ok%RST% %%a
        )
    )
)

echo.

REM ── RUN: separate window, close this one ──
echo %GRN%[ok]%RST% launching BlackKnight in a new window...
timeout /t 1 /nobreak >nul
start "BlackKnight" cmd /k python main.py %*

endlocal
exit /b 0