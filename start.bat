@echo off
REM System Monitor Dashboard - Windows Batch Launcher
REM Simple batch file to start the system monitor

title System Monitor Dashboard

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║                   System Monitor Dashboard                    ║
echo ║                      Quick Launcher                           ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python not found. Please install Python 3.7+ from https://python.org
    echo.
    pause
    exit /b 1
)

echo ✓ Python found
echo.

REM Check if main.py exists
if not exist "main.py" (
    echo ✗ main.py not found. Please ensure all files are in the current directory.
    echo.
    pause
    exit /b 1
)

REM Install dependencies if requirements.txt exists
if exist "requirements.txt" (
    echo Installing dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ✗ Failed to install dependencies
        echo.
        pause
        exit /b 1
    )
    echo ✓ Dependencies installed
    echo.
)

REM Start the server
echo Starting System Monitor Dashboard...
echo Server will be available at http://localhost:9876
echo Press Ctrl+C to stop the server
echo.

python main.py

REM Pause if the script exits unexpectedly
if errorlevel 1 (
    echo.
    echo Server stopped with an error.
    pause
)