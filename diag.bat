@echo off
cd /d "%~dp0"

> diag.txt 2>&1 (
    echo === FOLDER ===
    cd
    echo.
    echo === FILES ===
    dir /b
    echo.
    echo === static folder ===
    dir /b static 2>&1
    echo.
    echo === python ===
    where python 2>&1
    python --version 2>&1
    echo.
    echo === py ===
    where py 2>&1
    py -3 --version 2>&1
    echo.
    echo === imports ===
    python -c "import openai, rich, httpx, dotenv; print('imports OK')" 2>&1
    echo.
    echo === run main.py (5s timeout) ===
    python main.py <nul
)

echo Done. Open diag.txt in this folder and send me its contents.
pause