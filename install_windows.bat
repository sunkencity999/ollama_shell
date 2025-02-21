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

:: Function to install required dependencies
:install_required_deps
echo Installing required dependencies...
:: CLI and interface dependencies
pip install typer rich requests prompt_toolkit pyfiglet termcolor pyperclip
:: Web and search dependencies
pip install duckduckgo-search beautifulsoup4 html2text
:: Basic document processing
pip install markdown2
goto :eof

:: Function to install document processing dependencies
:install_doc_deps
echo Installing document processing dependencies...
pip install Pillow python-docx PyPDF2
goto :eof

:: Function to install optional dependencies
:install_optional_deps
echo Installing optional dependencies...
pip install weasyprint chroma-hnswlib
goto :eof

:: Function to modify ollama_shell.py to work without weasyprint
:patch_weasyprint
echo Patching ollama_shell.py for PDF export compatibility...
python -c "
import re
with open('ollama_shell.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace weasyprint imports with a try-except block
content = re.sub(
    r'from weasyprint import HTML, CSS\nfrom weasyprint\.text\.fonts import FontConfiguration',
    'try:\n    from weasyprint import HTML, CSS\n    from weasyprint.text.fonts import FontConfiguration\n    WEASYPRINT_AVAILABLE = True\nexcept ImportError:\n    WEASYPRINT_AVAILABLE = False',
    content
)

# Add check for weasyprint availability in PDF export
content = re.sub(
    r'elif format == \"pdf\":\s+# First convert to HTML, then to PDF',
    'elif format == \"pdf\":\n            if not WEASYPRINT_AVAILABLE:\n                raise ImportError(\"PDF export requires weasyprint. Please install Build Tools and run the installer again.\")\n            # First convert to HTML, then to PDF',
    content
)

with open('ollama_shell.py', 'w', encoding='utf-8') as f:
    f.write(content)
"
goto :eof

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
            
            echo Installing required dependencies...
            call :install_required_deps
            call :install_doc_deps
            call :patch_weasyprint
            
            echo [33mNote: PDF export will be disabled until Build Tools are installed.[0m
        ) else (
            echo [32mBuild Tools installed successfully![0m
            echo Installing all dependencies...
            call :install_required_deps
            call :install_doc_deps
            call :install_optional_deps
        )
        
        :: Clean up
        rmdir /s /q "%TEMP%\vsbuildtools" 2>nul
    ) else (
        echo [31mFailed to download Build Tools installer.[0m
        echo Please install manually from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
        echo Installing basic dependencies...
        
        call :install_required_deps
        call :install_doc_deps
        call :patch_weasyprint
        
        echo [33mNote: PDF export will be disabled until Build Tools are installed.[0m
    )
) else (
    echo [32mBuild Tools already installed.[0m
    echo Installing all dependencies...
    call :install_required_deps
    call :install_doc_deps
    call :install_optional_deps
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
