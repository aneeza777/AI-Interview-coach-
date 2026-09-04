@echo off
echo ============================================
echo   AI Interview Coach - Setup
echo ============================================
echo.

REM Check Python
py --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

REM Create virtual environment
if not exist "venv" (
    echo [1/4] Creating virtual environment...
    py -m venv venv
)

REM Activate venv
call venv\Scripts\activate.bat

REM Upgrade pip and install pinned build tools
echo [2/4] Upgrading pip, setuptools, wheel...
python -m pip install --upgrade pip wheel
python -m pip install setuptools==77.0.3

REM Install base dependencies
echo [3/5] Installing Python dependencies (this may take 5-10 minutes)...
pip install -r requirements.txt

REM Install Whisper separately with no build isolation (fixes Windows source build issue)
echo [4/5] Installing OpenAI Whisper...
pip install --no-build-isolation openai-whisper==20231117

REM Download spaCy model
echo [5/5] Downloading spaCy English model...
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl

echo.
echo ============================================
echo   Setup complete!
echo   Run 'start.bat' to launch the server.
echo ============================================
pause
