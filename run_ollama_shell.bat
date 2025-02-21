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

:: Activate virtual environment
call :log "Activating virtual environment..."
call venv\Scripts\activate.bat
if errorlevel 1 (
    call :log "[ERROR] Failed to activate virtual environment!"
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
echo Python path: %PYTHONPATH% >> %LOGFILE%

echo [32mLaunching Ollama Shell...[0m
python ollama_shell.py
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
