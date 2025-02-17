@echo off
title Ollama Shell

:: Set terminal size (150x50)
powershell -command "&{$h=get-host;$w=$h.ui.rawui;$s=$w.buffersize;$s.width=150;$w.buffersize=$s;$s=$w.windowsize;$s.width=150;$s.height=50;$w.windowsize=$s}"

echo Starting Ollama Shell...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed! Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install/upgrade pip
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Check if Ollama service is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo Ollama service is not running!
    echo Please ensure Ollama is installed and running.
    echo Visit https://ollama.ai for installation instructions.
    pause
    exit /b 1
)

REM Start the application
python ollama_shell.py

REM Keep the window open if there's an error
if errorlevel 1 (
    echo.
    echo An error occurred. Press any key to exit.
    pause >nul
)
