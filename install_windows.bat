@echo off
setlocal enabledelayedexpansion

echo Checking Python installation...
python --version > nul 2>&1
if errorlevel 1 (
    echo [31mPython is not installed or not in PATH[0m
    echo Please install Python 3.8 or higher from python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo Checking pip installation...
python -m pip --version > nul 2>&1
if errorlevel 1 (
    echo pip is not installed
    echo Installing pip...
    python -m ensurepip --default-pip
)

echo Creating virtual environment if it doesn't exist...
if not exist venv (
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing/Upgrading pip...
python -m pip install --upgrade pip

echo Checking for Microsoft Visual C++ Build Tools...
where cl.exe >nul 2>&1
if errorlevel 1 (
    echo [33mMicrosoft Visual C++ Build Tools not found[0m
    echo Attempting to download and install Build Tools...
    
    :: Create a temporary directory for the installer
    mkdir "%TEMP%\vsbuildtools" 2>nul
    
    :: Download the Visual Studio Build Tools bootstrapper
    echo Downloading Visual Studio Build Tools installer...
    powershell -Command "& {Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vs_buildtools.exe' -OutFile '%TEMP%\vsbuildtools\vs_buildtools.exe'}"
    
    if exist "%TEMP%\vsbuildtools\vs_buildtools.exe" (
        echo Installing Visual Studio Build Tools...
        echo This may take a while. Please wait...
        
        :: Install Build Tools silently with necessary components
        "%TEMP%\vsbuildtools\vs_buildtools.exe" --quiet --wait --norestart --nocache ^
            --installPath "%ProgramFiles(x86)%\Microsoft Visual Studio\2022\BuildTools" ^
            --add Microsoft.VisualStudio.Workload.VCTools ^
            --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64
        
        :: Check if installation was successful
        where cl.exe >nul 2>&1
        if errorlevel 1 (
            echo [31mBuild Tools installation may have failed.[0m
            echo Please install manually from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
            echo Then run this script again.
            
            :: Clean up
            rmdir /s /q "%TEMP%\vsbuildtools" 2>nul
            
            echo Installing only packages that don't require compilation...
            echo Installing core dependencies...
            pip install --no-deps typer rich requests prompt_toolkit pyfiglet termcolor pyperclip
            pip install --no-deps duckduckgo-search beautifulsoup4 html2text markdown2
        ) else (
            echo [32mBuild Tools installed successfully![0m
            echo Installing all dependencies...
            pip install -r requirements.txt
        )
        
        :: Clean up
        rmdir /s /q "%TEMP%\vsbuildtools" 2>nul
    ) else (
        echo [31mFailed to download Build Tools installer.[0m
        echo Please install manually from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
        echo Installing only packages that don't require compilation...
        
        echo Installing core dependencies...
        pip install --no-deps typer rich requests prompt_toolkit pyfiglet termcolor pyperclip
        pip install --no-deps duckduckgo-search beautifulsoup4 html2text markdown2
    )
) else (
    echo [32mBuild Tools already installed.[0m
    echo Installing all dependencies...
    pip install -r requirements.txt
)

echo Creating run script...
(
echo @echo off
echo call venv\Scripts\activate.bat
echo cd /d "%%~dp0"
echo python ollama_shell.py
echo pause
) > run_ollama_shell.bat

echo.
echo [32mInstallation complete![0m
echo [33mImportant Notes:[0m
echo 1. If you had any issues with Build Tools installation:
echo    Install them manually from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
echo    Then run this script again
echo.
echo 2. Make sure Ollama is installed and running:
echo    Download from: https://ollama.ai/download
echo.
echo To start Ollama Shell, run 'run_ollama_shell.bat'
echo.
pause
