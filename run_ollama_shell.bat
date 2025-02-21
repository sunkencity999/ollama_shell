@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python ollama_shell.py
pause
