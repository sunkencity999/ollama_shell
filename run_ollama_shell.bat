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

:: Verify dependencies are installed
call :log "Checking dependencies..."
python -c "
import sys, traceback
try:
    print('Python version:', sys.version)
    required_packages = ['PIL', 'typer', 'rich', 'requests', 'prompt_toolkit', 'pyfiglet', 'termcolor', 'pyperclip', 
                        'duckduckgo_search', 'beautifulsoup4', 'html2text', 'markdown2', 'PyPDF2', 'python-docx']
    missing_packages = []
    for package in required_packages:
        try:
            if package == 'PIL':
                __import__('PIL')
                print(f'Successfully imported {package}')
            else:
                __import__(package.replace('-', '_'))
                print(f'Successfully imported {package}')
        except ImportError as e:
            missing_packages.append(package)
            print(f'Error importing {package}: {str(e)}')
    if missing_packages:
        print('Missing dependencies:', ', '.join(missing_packages))
        print('Running repair...')
        import subprocess
        for package in missing_packages:
            if package == 'PIL':
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'Pillow'])
            else:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        print('Repair complete!')
    else:
        print('All required dependencies are installed!')
except Exception as e:
    print('Error during dependency check:')
    traceback.print_exc()
    sys.exit(1)
" >> %LOGFILE% 2>&1

:: Check if Ollama is running
call :log "Checking Ollama service..."
powershell -Command "& {try { $response = Invoke-WebRequest -Uri 'http://localhost:11434/api/version' -TimeoutSec 2; Write-Host $response.Content; exit 0 } catch { Write-Host $_.Exception.Message; exit 1 }}" >> %LOGFILE% 2>&1
if errorlevel 1 (
    call :log "[WARNING] Ollama service does not appear to be running"
    echo Please make sure Ollama is installed and running
    echo Download from: https://ollama.ai/download
    echo.
    choice /C YN /M "Do you want to continue anyway"
    if errorlevel 2 exit /b 1
)

:: Run the application with error handling and debug output
call :log "Starting Ollama Shell..."
echo Current directory: %CD% >> %LOGFILE%
echo Python path: %PYTHONPATH% >> %LOGFILE%
echo. >> %LOGFILE%
echo ===== Starting Python Application ===== >> %LOGFILE%
python -v ollama_shell.py >> %LOGFILE% 2>&1
set PYTHON_EXIT_CODE=%errorlevel%

if %PYTHON_EXIT_CODE% neq 0 (
    call :log "[ERROR] Ollama Shell exited with code %PYTHON_EXIT_CODE%"
    echo.
    echo An error occurred while running Ollama Shell.
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
