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
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo Could not install the Python packages. Is Python installed and on PATH?
    pause
    exit /b 1
)

if not exist .env (
    echo NOTE: backend\.env not found. The app will run, but the AI assistant needs
    echo       GROQ_API_KEY in that file. Copy backend\.env.example to backend\.env and add your key.
)

echo Starting AI Book Assistant on http://127.0.0.1:8000 ...
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8000"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
pause
