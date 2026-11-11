@echo off
setlocal EnableDelayedExpansion
title BlackKnight - Web
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
echo %RED%  B L A C K  K N I G H T  %RST%%DIM% web%RST%
echo %DIM%  launcher%RST%
echo.

REM ── Find python (python or py -3) ──
set "PY="
where python >nul 2>nul
if not errorlevel 1 set "PY=python"
if not defined PY (
    where py >nul 2>nul
    if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
    echo %RED%[x]%RST% Python not found in PATH.
    echo     Install Python 3.10+ from https://www.python.org/downloads/
    echo     During install, check "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)
echo %DIM%[i]%RST% python : %PY%
echo %DIM%[i]%RST% folder : %CD%
echo.

REM ── Check files one by one ──
set "ERR=0"
if not exist "main.py"            ( echo %RED%[x]%RST% missing: main.py            & set "ERR=1" )
if not exist "config.py"          ( echo %RED%[x]%RST% missing: config.py          & set "ERR=1" )
if not exist "ui.py"              ( echo %RED%[x]%RST% missing: ui.py              & set "ERR=1" )
if not exist "web_server.py"      ( echo %RED%[x]%RST% missing: web_server.py      & set "ERR=1" & echo     %DIM%this is a NEW file — create it from the instructions%RST% )
if not exist "static\index.html"  ( echo %RED%[x]%RST% missing: static\index.html  & set "ERR=1" & echo     %DIM%create folder "static" and put index.html inside%RST% )

if %ERR%==1 (
    echo.
    echo %YEL%[!]%RST% cannot start — required files missing.
    echo.
    pause
    exit /b 1
)

if not exist ".env" (
    echo %YEL%[!]%RST% .env not found. Copy .env.example to .env and fill BK_API_KEY.
    echo.
)

REM ── Dependencies ──
echo %DIM%[i]%RST% checking dependencies...
set "PKGS=openai:openai rich:rich requests:requests beautifulsoup4:bs4 httpx:httpx python-dotenv:dotenv fastapi:fastapi uvicorn:uvicorn websockets:websockets"

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
    echo     Try manually:
    echo     %PY% -m pip install fastapi "uvicorn[standard]" websockets
    echo.
    pause
    exit /b 1
)
echo.

REM ── Port warning (non-blocking) ──
netstat -ano | findstr /R /C:":%BK_PORT% .*LISTENING" >nul
if not errorlevel 1 (
    echo %YEL%[!]%RST% port %BK_PORT% appears busy.
    echo     If the server fails to bind, close the other process
    echo     or run:  %DIM%set BK_PORT=9000 ^&^& run_web.bat%RST%
    echo.
)

REM ── Launch ──
echo %GRN%[ok]%RST% starting BlackKnight web on http://localhost:%BK_PORT%
echo %DIM%     server logs will appear in a new window.
echo     close that window to stop the server.%RST%
echo.
timeout /t 1 /nobreak >nul

start "BlackKnight Web Server" cmd /k "%PY% web_server.py"
timeout /t 3 /nobreak >nul
start "" "http://localhost:%BK_PORT%"

echo %GRN%[ok]%RST% browser opened. This launcher will close.
timeout /t 2 /nobreak >nul

endlocal
exit /b 0