@echo off
echo Installing Ollama Shell for Windows...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python 3.8 or higher from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if pip is installed
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo pip is not installed. Installing pip...
    python -m ensurepip --default-pip
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Upgrade pip
python -m pip install --upgrade pip

REM Install wheel first
pip install wheel

REM Install basic requirements that don't need compilation
echo Installing basic requirements...
pip install typer rich requests prompt_toolkit pyfiglet termcolor pyperclip

REM Try to install chroma-hnswlib with precompiled wheel
echo Installing chroma-hnswlib...
pip install --only-binary :all: chroma-hnswlib

REM Install remaining requirements
echo Installing remaining requirements...
pip install duckduckgo_search beautifulsoup4 html2text

REM Create run script
echo @echo off > run_ollama_shell.bat
echo call venv\Scripts\activate.bat >> run_ollama_shell.bat
echo python ollama_shell.py >> run_ollama_shell.bat
echo pause >> run_ollama_shell.bat

echo.
echo Installation complete! 
echo A new file 'run_ollama_shell.bat' has been created.
echo Double-click it to run Ollama Shell.
echo.
echo Note: If you encounter any errors about missing Visual C++,
echo please install Microsoft Visual C++ Build Tools from:
echo https://visualstudio.microsoft.com/visual-cpp-build-tools/
echo.
pause
