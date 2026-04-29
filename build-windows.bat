@echo off
REM ========================================
REM Windows Build Script (Development)
REM ========================================
REM This script builds the entire application for Windows.
REM Run this frequently during development.
REM ========================================

echo Building Notarizer for Windows...
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
echo Building entire application...
REM This builds frontend + backend executable in one go
npm run build
if errorlevel 1 (
    echo ERROR: Build failed.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Executable location: dist\notarizer-alpha1.exe
echo.
pause
