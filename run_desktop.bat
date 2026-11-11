@echo off
setlocal EnableDelayedExpansion
title BlackKnight - Desktop
cd /d "%~dp0"

REM ── ANSI colors ──
for /F %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "RED=%ESC%[91m"
set "DIM=%ESC%[90m"
set "GRN=%ESC%[92m"
set "YEL=%ESC%[93m"
set "RST=%ESC%[0m"

if not defined BK_PORT set "BK_PORT=8080"

echo.
echo %RED%  B L A C K  K N I G H T  %RST%%DIM% desktop%RST%
echo %DIM%  frameless launcher%RST%
echo.

REM ── Find python ──
set "PY="
where python >nul 2>nul
if not errorlevel 1 set "PY=python"
if not defined PY (
    where py >nul 2>nul
    if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
    echo %RED%[x]%RST% Python not found in PATH.
    echo     Install Python 3.10+ and enable "Add python.exe to PATH".
    pause
    exit /b 1
)

echo %DIM%[i]%RST% python : %PY%
echo %DIM%[i]%RST% folder : %CD%
echo %DIM%[i]%RST% port   : %BK_PORT%
echo.

REM ── Required files ──
set "ERR=0"
for %%f in (main.py config.py ui.py web_server.py desktop.py static\index.html) do (
    if not exist "%%f" (
        echo %RED%[x]%RST% missing: %%f
        set "ERR=1"
    )
)
if !ERR!==1 (
    echo.
    echo %YEL%[!]%RST% cannot start — required files missing.
    pause
    exit /b 1
)

if not exist ".env" (
    echo %YEL%[!]%RST% .env not found. Copy .env.example to .env and set BK_API_KEY.
    echo.
)

REM ── Dependencies ──
echo %DIM%[i]%RST% checking dependencies...
set "PKGS=openai:openai rich:rich requests:requests beautifulsoup4:bs4 httpx:httpx python-dotenv:dotenv fastapi:fastapi uvicorn:uvicorn websockets:websockets pywebview:webview"
set "PIPERR=0"

for %%p in (%PKGS%) do (
    for /f "tokens=1,2 delims=:" %%a in ("%%p") do (
        %PY% -c "import %%b" >nul 2>nul
        if errorlevel 1 (
            echo   %DIM%install %%a...%RST%
            %PY% -m pip install --quiet --disable-pip-version-check %%a >nul 2>nul
            if errorlevel 1 (
                echo   %RED%[x]%RST% failed: %%a
                set "PIPERR=1"
            ) else (
                echo   %GRN%ok%RST% %%a
            )
        ) else (
            echo   %GRN%ok%RST% %%a
        )
    )
)

if !PIPERR!==1 (
    echo.
    echo %RED%[x]%RST% dependency install failed.
    echo     Try manually: %PY% -m pip install -r requirements.txt
    pause
    exit /b 1
)
echo.

REM ── WebView2 runtime check (Windows) ──
set "WV2=0"
reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" /v pv >nul 2>nul
if not errorlevel 1 set "WV2=1"
reg query "HKCU\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" /v pv >nul 2>nul
if not errorlevel 1 set "WV2=1"
if !WV2!==0 (
    echo %YEL%[!]%RST% Microsoft Edge WebView2 Runtime was not detected.
    echo     If the window fails to open, install it:
    echo     %DIM%https://developer.microsoft.com/microsoft-edge/webview2/%RST%
    echo.
)

REM ── Launch without console when pythonw is available ──
echo %GRN%[ok]%RST% starting frameless desktop app...
set "PYW="
where pythonw >nul 2>nul
if not errorlevel 1 set "PYW=pythonw"

if defined PYW (
    start "" "%PYW%" desktop.py
    echo %GRN%[ok]%RST% BlackKnight desktop launched.
    timeout /t 1 /nobreak >nul
) else (
    start "BlackKnight Desktop" cmd /k "%PY% desktop.py"
    echo %DIM%     pythonw not found — keeping console window for logs.%RST%
    timeout /t 2 /nobreak >nul
)

endlocal
exit /b 0