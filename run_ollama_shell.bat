@echo off
setlocal enabledelayedexpansion

:: Create a log file
set "LOGFILE=ollama_shell_debug.log"
echo Starting Ollama Shell Debug Log > %LOGFILE%
echo Timestamp: %date% %time% >> %LOGFILE%
echo. >> %LOGFILE%

:: Log all output to file
call :log "Changing to script directory..."
cd /d "%~dp0"
echo Current directory: %CD% >> %LOGFILE%

:: Check if virtual environment exists
call :log "Checking virtual environment..."
if not exist venv (
    call :log "[ERROR] Virtual environment not found!"
    echo Please run install_windows.bat first
    pause
    exit /b 1
)

:: Activate virtual environment and verify Python path
call :log "Activating virtual environment..."
call venv\Scripts\activate.bat
if errorlevel 1 (
    call :log "[ERROR] Failed to activate virtual environment!"
    pause
    exit /b 1
)

:: Verify Python is from virtual environment
for /f "tokens=*" %%i in ('python -c "import sys; print(sys.executable)"') do set PYTHON_PATH=%%i
echo Python executable: !PYTHON_PATH! >> %LOGFILE%
if not "!PYTHON_PATH!"=="%CD%\venv\Scripts\python.exe" (
    call :log "[ERROR] Python is not running from virtual environment!"
    echo Python should be: %CD%\venv\Scripts\python.exe
    echo Python is: !PYTHON_PATH!
    pause
    exit /b 1
)

:: Install/verify dependencies
call :log "Installing/verifying dependencies..."
echo [32mInstalling required packages...[0m

:: Update pip first
python -m pip install --upgrade pip

:: Install packages with explicit paths
echo Installing packages...
%CD%\venv\Scripts\pip install -q typer rich requests prompt_toolkit pyfiglet termcolor pyperclip
%CD%\venv\Scripts\pip install -q duckduckgo-search beautifulsoup4 html2text markdown2
%CD%\venv\Scripts\pip install -q Pillow python-docx PyPDF2

:: Verify critical dependencies with explicit Python path
echo Verifying dependencies...
%CD%\venv\Scripts\python -c "import sys; print('Python version:', sys.version)" >> %LOGFILE%
%CD%\venv\Scripts\python -c "import PIL; print('PIL version:', PIL.__version__)" >> %LOGFILE%
%CD%\venv\Scripts\python -c "import requests; print('Requests version:', requests.__version__)" >> %LOGFILE%
%CD%\venv\Scripts\python -c "import typer; print('Typer version:', typer.__version__)" >> %LOGFILE%
%CD%\venv\Scripts\python -c "import rich; print('Rich version:', rich.__version__)" >> %LOGFILE%

if errorlevel 1 (
    call :log "[ERROR] Failed to verify critical dependencies"
    echo [31mError: Failed to install required packages[0m
    echo Please run install_windows.bat again
    pause
    exit /b 1
)

:: Check if Ollama is running (with timeout)
call :log "Checking Ollama service..."
set "OLLAMA_RUNNING=0"
powershell -Command "& {
    $webRequest = [System.Net.WebRequest]::Create('http://localhost:11434/api/version')
    $webRequest.Timeout = 2000
    try {
        $response = $webRequest.GetResponse()
        $stream = $response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        $content = $reader.ReadToEnd()
        Write-Host $content
        exit 0
    } catch {
        Write-Host $_.Exception.Message
        exit 1
    }
}" > nul 2>&1
if errorlevel 1 (
    call :log "[WARNING] Ollama service not detected"
    echo [33mWarning: Ollama service not detected[0m
    echo Make sure Ollama is installed and running before using chat features
    echo Download from: https://ollama.ai/download
    echo.
    echo [32mProceeding anyway...[0m
    set "OLLAMA_RUNNING=0"
) else (
    call :log "[INFO] Ollama service is running"
    set "OLLAMA_RUNNING=1"
)

:: Run the application
call :log "Starting Ollama Shell..."
echo ===== Starting Ollama Shell ===== >> %LOGFILE%
echo Current directory: %CD% >> %LOGFILE%
echo Python path: !PYTHON_PATH! >> %LOGFILE%

echo [32mLaunching Ollama Shell...[0m
%CD%\venv\Scripts\python ollama_shell.py
set PYTHON_EXIT_CODE=%errorlevel%

if %PYTHON_EXIT_CODE% neq 0 (
    call :log "[ERROR] Ollama Shell exited with code %PYTHON_EXIT_CODE%"
    echo.
    echo [31mError: Ollama Shell exited with an error[0m
    echo Please check the debug log file: %LOGFILE%
    echo.
    echo Last few lines of the log:
    echo ================================
    powershell -Command "Get-Content '%LOGFILE%' -Tail 10"
    echo ================================
)

:: Deactivate virtual environment
call venv\Scripts\deactivate.bat

echo.
echo Debug log has been saved to: %LOGFILE%
echo Press any key to exit...
pause > nul

goto :eof

:log
echo %~1
echo [%date% %time%] %~1 >> %LOGFILE%
goto :eof
