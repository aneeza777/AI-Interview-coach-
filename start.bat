@echo off
echo ============================================
echo   AI Interview Coach - Starting Server
echo ============================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start the FastAPI server
echo Server: http://127.0.0.1:8000
echo Press Ctrl+C to stop.
echo.

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
