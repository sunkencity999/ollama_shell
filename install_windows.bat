@echo off
setlocal enabledelayedexpansion

echo Checking Python installation...
python --version > nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from python.org
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

echo Installing dependencies...
pip install -r requirements.txt

echo Installing additional dependencies for enhanced features...
pip install Pillow>=10.0.0 python-docx>=1.0.0 PyPDF2>=3.0.0 weasyprint>=60.1 markdown2>=2.4.10 duckduckgo-search>=4.1.1 beautifulsoup4>=4.12.0 html2text>=2020.1.16

echo Checking Microsoft Visual C++ Build Tools...
where cl.exe >nul 2>&1
if errorlevel 1 (
    echo Microsoft Visual C++ Build Tools not found
    echo Some features may require Microsoft Visual C++ Build Tools
    echo Please install from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
)

echo Creating run script...
(
echo @echo off
echo call venv\Scripts\activate.bat
echo cd /d "%%~dp0"
echo python ollama_shell.py
echo pause
) > run_ollama_shell.bat

echo Installation complete!
echo To start Ollama Shell, run 'run_ollama_shell.bat'

pause
