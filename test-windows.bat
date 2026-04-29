@echo off
REM ========================================
REM Windows Test Script (Development)
REM ========================================
REM This script runs the application in development mode for testing.
REM ========================================

echo Testing Notarizer in development mode...
echo.

REM Check if virtual environment exists
if not exist venv (
    echo ERROR: Virtual environment not found. Run setup-windows-env.bat first.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if Python dependencies are installed
python -c "import webview, clr" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python dependencies not found. Run setup-windows-env.bat first.
    pause
    exit /b 1
)

echo.
echo Starting application in development mode...
echo (Press Ctrl+C to stop)
echo.
python src\index.py
