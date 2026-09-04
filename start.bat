@echo off
setlocal enabledelayedexpansion
title AI Interview Coach

echo ============================================================
echo   🎯 AI INTERVIEW COACH -- ALL-IN-ONE LAUNCHER
echo ============================================================
echo.

REM 1. Check if virtual environment exists; if not, run automatic setup
if not exist "venv\Scripts\python.exe" (
    echo [INFO] Virtual environment not found. Running automatic setup...
    call setup.bat
    if errorlevel 1 (
        echo [ERROR] Setup encountered an issue.
        pause
        exit /b 1
    )
)

REM 2. Ensure .env exists
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating .env from .env.example...
        copy .env.example .env >nul
    )
)

REM 3. Ensure uploads folder exists
if not exist "uploads" (
    mkdir uploads
)

REM 4. Activate virtual environment
call venv\Scripts\activate.bat

echo.
echo ============================================================
echo   🚀 Server running at: http://127.0.0.1:8000
echo   🌐 Opening browser automatically...
echo   🛑 Press Ctrl+C in this window to stop the server.
echo ============================================================
echo.

REM Open browser after 2 seconds in background
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8000"

REM Run FastAPI server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
