@echo off
cd /d "%~dp0"
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
pushd "%~dp0..\data-pipeline" || exit /b 1
python db_build.py
if errorlevel 1 (
    popd
    exit /b 1
)
popd
echo Starting AI Book Assistant Backend on http://127.0.0.1:8000 ...
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
pause
