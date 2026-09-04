@echo off
echo ============================================
echo   AI Interview Coach - Model Training
echo ============================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install training dependencies
echo Installing training dependencies...
pip install -r training\requirements.txt

REM Run training pipeline
echo.
echo Starting training pipeline...
cd training
py run_all_training.py
cd ..

echo.
echo Training complete!
echo Run 'start.bat' to launch the website with trained models.
pause
