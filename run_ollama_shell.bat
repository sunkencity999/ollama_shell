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

:: Create a temporary Python script for dependency checking
call :log "Creating dependency check script..."
set "TEMP_SCRIPT=check_deps.py"
(
echo import sys, traceback
echo try:
echo     print('Python version:', sys.version^)
echo     required_packages = ['PIL', 'typer', 'rich', 'requests', 'prompt_toolkit', 'pyfiglet', 'termcolor', 'pyperclip',
echo                         'duckduckgo_search', 'beautifulsoup4', 'html2text', 'markdown2', 'PyPDF2', 'python-docx']
echo     missing_packages = []
echo     for package in required_packages:
echo         try:
echo             if package == 'PIL':
echo                 __import__('PIL'^)
echo                 print(f'Successfully imported {package}'^)
echo             else:
echo                 __import__(package.replace('-', '_'^)^)
echo                 print(f'Successfully imported {package}'^)
echo         except ImportError as e:
echo             missing_packages.append(package^)
echo             print(f'Error importing {package}: {str(e^)}'^)
echo     if missing_packages:
echo         print('Missing dependencies:', ', '.join(missing_packages^)^)
echo         print('Running repair...'^)
echo         import subprocess
echo         for package in missing_packages:
echo             if package == 'PIL':
echo                 subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'Pillow']^)
echo             else:
echo                 subprocess.check_call([sys.executable, '-m', 'pip', 'install', package]^)
echo         print('Repair complete!'^)
echo     else:
echo         print('All required dependencies are installed!'^)
echo except Exception as e:
echo     print('Error during dependency check:'^)
echo     traceback.print_exc(^)
echo     sys.exit(1^)
) > %TEMP_SCRIPT%

:: Run the dependency check script
call :log "Checking dependencies..."
python %TEMP_SCRIPT% >> %LOGFILE% 2>&1
if errorlevel 1 (
    call :log "[ERROR] Dependency check failed!"
    type %LOGFILE%
    del %TEMP_SCRIPT%
    pause
    exit /b 1
)
del %TEMP_SCRIPT%

:: Check if Ollama is running
call :log "Checking Ollama service..."
powershell -Command "& {try { $response = Invoke-WebRequest -Uri 'http://localhost:11434/api/version' -TimeoutSec 2; Write-Host $response.Content; exit 0 } catch { Write-Host $_.Exception.Message; exit 1 }}" >> %LOGFILE% 2>&1
if errorlevel 1 (
    call :log "[WARNING] Ollama service does not appear to be running"
    echo Please make sure Ollama is installed and running
    echo Download from: https://ollama.ai/download
    echo.
    choice /C YN /M "Do you want to continue anyway" > nul
    if errorlevel 2 exit /b 1
)

:: Run the application with error handling and debug output
call :log "Starting Ollama Shell..."
echo Current directory: %CD% >> %LOGFILE%
echo Python path: %PYTHONPATH% >> %LOGFILE%
echo. >> %LOGFILE%
echo ===== Starting Python Application ===== >> %LOGFILE%

:: Create a wrapper script to catch any Python errors
set "WRAPPER_SCRIPT=run_app.py"
(
echo import sys, traceback
echo try:
echo     import ollama_shell
echo except Exception as e:
echo     print('Error running ollama_shell:'^)
echo     traceback.print_exc(^)
echo     sys.exit(1^)
) > %WRAPPER_SCRIPT%

python %WRAPPER_SCRIPT% >> %LOGFILE% 2>&1
set PYTHON_EXIT_CODE=%errorlevel%
del %WRAPPER_SCRIPT%

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
