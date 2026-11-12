@echo off
rem One-click launcher: checks dependencies, starts the FastAPI backend (which also serves the UI), and opens the browser.
setlocal
cd /d "%~dp0backend"

if not exist books.db (
    echo books.db not found in backend\. Put the database file there first.
    pause
    exit /b 1
)

echo Checking Python packages...
python -m pip install --quiet fastapi "uvicorn[standard]" pydantic
if errorlevel 1 (
    echo Could not install the Python packages. Is Python installed and on PATH?
    pause
    exit /b 1
)

echo Starting AI Book Assistant on http://127.0.0.1:8000 ...
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8000"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
pause
