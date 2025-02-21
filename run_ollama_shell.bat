@echo off
setlocal enabledelayedexpansion

:: Change to the script's directory
cd /d "%~dp0"

:: Check if virtual environment exists
if not exist venv (
    echo [31mVirtual environment not found![0m
    echo Please run install_windows.bat first
    pause
    exit /b 1
)

:: Check if Ollama is running
powershell -Command "& {try { $response = Invoke-WebRequest -Uri 'http://localhost:11434/api/version' -TimeoutSec 2; exit 0 } catch { exit 1 }}"
if errorlevel 1 (
    echo [33mWarning: Ollama service does not appear to be running[0m
    echo Please make sure Ollama is installed and running
    echo Download from: https://ollama.ai/download
    echo.
    choice /C YN /M "Do you want to continue anyway"
    if errorlevel 2 exit /b 1
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Run the application with error handling
echo Starting Ollama Shell...
python ollama_shell.py
if errorlevel 1 (
    echo.
    echo [31mError: Ollama Shell exited with an error[0m
    echo If you're seeing dependency errors, try running install_windows.bat again
    echo For other issues, please check the error message above
)

:: Deactivate virtual environment
call venv\Scripts\deactivate.bat

pause
