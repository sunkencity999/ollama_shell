@echo off
setlocal enabledelayedexpansion

echo Testing Windows installation script...
echo.

REM Function to check if a command exists
:check_command
echo Checking for %~1...
where %~1 >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [92m✓ %~1 is available[0m
    exit /b 0
) else (
    echo [91m✗ %~1 is not available[0m
    exit /b 1
)

REM Function to check if a directory exists
:check_directory
if exist "%~1\" (
    echo [92m✓ Directory %~1 exists[0m
    exit /b 0
) else (
    echo [91m✗ Directory %~1 does not exist[0m
    exit /b 1
)

REM Function to check if a file exists
:check_file
if exist "%~1" (
    echo [92m✓ File %~1 exists[0m
    exit /b 0
) else (
    echo [91m✗ File %~1 does not exist[0m
    exit /b 1
)

echo Checking for required commands...
call :check_command python
call :check_command pip

echo.
echo Checking for optional commands...
call :check_command ollama
call :check_command docker

echo.
echo Checking for installation script...
call :check_file "install.bat"

echo.
echo Checking for required files...
call :check_file "requirements.txt"
call :check_file "ollama_shell.py"

echo.
echo Creating temporary test directory...
set TEST_DIR=test_install_temp
mkdir "%TEST_DIR%" 2>nul

echo.
echo Testing directory creation...
mkdir "%TEST_DIR%\Created Files\jobs" "%TEST_DIR%\Created Files\datasets" "%TEST_DIR%\Created Files\models" "%TEST_DIR%\Created Files\exports" "%TEST_DIR%\Created Files\config" 2>nul

call :check_directory "%TEST_DIR%\Created Files\jobs"
call :check_directory "%TEST_DIR%\Created Files\datasets"
call :check_directory "%TEST_DIR%\Created Files\models"
call :check_directory "%TEST_DIR%\Created Files\exports"
call :check_directory "%TEST_DIR%\Created Files\config"

echo.
echo Testing file creation...
echo. > "%TEST_DIR%\Created Files\jobs\.gitkeep"
echo. > "%TEST_DIR%\Created Files\datasets\.gitkeep"
echo. > "%TEST_DIR%\Created Files\models\.gitkeep"
echo. > "%TEST_DIR%\Created Files\exports\.gitkeep"
echo. > "%TEST_DIR%\Created Files\config\.gitkeep"

call :check_file "%TEST_DIR%\Created Files\jobs\.gitkeep"
call :check_file "%TEST_DIR%\Created Files\datasets\.gitkeep"
call :check_file "%TEST_DIR%\Created Files\models\.gitkeep"
call :check_file "%TEST_DIR%\Created Files\exports\.gitkeep"
call :check_file "%TEST_DIR%\Created Files\config\.gitkeep"

echo.
echo Testing config file creation...
(
echo # Confluence Configuration
echo # Fill in your Confluence details below
echo.
echo # Required settings
echo CONFLUENCE_URL=https://your-instance.atlassian.net
echo CONFLUENCE_EMAIL=your.email@example.com
echo CONFLUENCE_API_TOKEN=your_api_token_here
echo.
echo # Optional settings
echo CONFLUENCE_AUTH_METHOD=pat
echo CONFLUENCE_IS_CLOUD=true
echo CONFLUENCE_ANALYSIS_MODEL=llama3.2:latest
) > "%TEST_DIR%\Created Files\config\confluence_config_template.env"

call :check_file "%TEST_DIR%\Created Files\config\confluence_config_template.env"

echo.
echo Testing Python virtual environment creation...
python -m venv "%TEST_DIR%\venv" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [92m✓ Virtual environment created successfully[0m
    
    echo.
    echo Testing virtual environment activation...
    call "%TEST_DIR%\venv\Scripts\activate.bat" >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo [92m✓ Virtual environment activated successfully[0m
        call deactivate
    ) else (
        echo [91m✗ Failed to activate virtual environment[0m
    )
) else (
    echo [91m✗ Failed to create virtual environment[0m
)

echo.
echo Cleaning up test directory...
rmdir /s /q "%TEST_DIR%" >nul 2>nul
echo [92m✓ Test directory removed[0m

echo.
echo Test completed!
echo Note: This test only checks for basic functionality and environment readiness.
echo To fully test the installation, you would need to run the actual install.bat script.

pause
