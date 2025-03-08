@echo off
echo Installing Ollama Shell...

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python is not installed. Please install Python first.
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo Installing dependencies...
pip install -r requirements.txt

REM Create necessary directories for user data
echo Creating user data directories...
python create_directories.py

REM Make ollama_shell.py executable (not needed on Windows, but kept for consistency)
echo.
echo Installation complete!
echo.
echo To start Ollama Shell:
echo 1. Start Ollama (if not already running)
echo 2. In a command prompt:
echo    call venv\Scripts\activate.bat
echo    python ollama_shell.py
echo.
pause
