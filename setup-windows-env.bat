@echo off
REM ========================================
REM Windows Environment Setup Script (One-time)
REM ========================================
REM Prerequisites:
REM - Python 3.11+ (64-bit) must be installed on the system
REM - Node.js and npm must be installed
REM - This script should be run from the project root directory
REM ========================================

echo Setting up Notarizer Windows environment (one-time setup)...
echo.

REM Check if Python is available
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.11+ first.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version

REM Check if Node.js is available
echo Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found. Please install Node.js first.
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)
echo Node.js found.

echo.
echo Creating Python virtual environment...
REM Remove existing venv if it exists
if exist venv (
    echo Removing existing virtual environment...
    rmdir /s /q venv
)

REM Create new virtual environment
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Python dependencies.
    pause
    exit /b 1
)

echo.
echo Installing Node.js dependencies...
npm install
if errorlevel 1 (
    echo ERROR: Failed to install Node.js dependencies.
    pause
    exit /b 1
)

echo.
echo Testing Python imports...
python -c "import webview, clr; print('✓ Python imports successful')"
if errorlevel 1 (
    echo ERROR: Python imports failed.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Environment setup completed successfully!
echo ========================================
echo.
echo Next steps:
echo   - For development: run build-windows.bat
echo   - For testing: run test-windows.bat
echo.
pause
