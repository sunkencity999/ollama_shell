@echo off
setlocal enabledelayedexpansion

echo Installing Ollama Shell...
echo.

REM Check if Python 3 is installed
python --version 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Python is not installed. Please install Python 3 first.
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo Installing dependencies...
pip install -r requirements.txt

REM Check if Ollama is installed
where ollama >NUL 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Ollama is not installed. Would you like to install it? (y/n)
    set /p install_ollama=
    if /i "!install_ollama!"=="y" (
        echo Please download and install Ollama from: https://ollama.ai/download/windows
        echo After installation, please run this script again.
        pause
        exit /b 0
    ) else (
        echo Please install Ollama manually from https://ollama.ai/download/windows
    )
)

REM Create necessary directories for user data
echo Creating user data directories...
if not exist "Created Files\jobs" mkdir "Created Files\jobs"
if not exist "Created Files\datasets" mkdir "Created Files\datasets"
if not exist "Created Files\models" mkdir "Created Files\models"
if not exist "Created Files\exports" mkdir "Created Files\exports"
if not exist "Created Files\config" mkdir "Created Files\config"

REM Create .gitkeep files to ensure directories are preserved in git
echo. > "Created Files\jobs\.gitkeep"
echo. > "Created Files\datasets\.gitkeep"
echo. > "Created Files\models\.gitkeep"
echo. > "Created Files\exports\.gitkeep"
echo. > "Created Files\config\.gitkeep"

REM Install Filesystem MCP Protocol dependencies
echo Installing Filesystem MCP Protocol dependencies...
if exist install_filesystem_mcp_protocol.py (
    python install_filesystem_mcp_protocol.py
    if %ERRORLEVEL% NEQ 0 (
        echo Warning: Failed to install Filesystem MCP Protocol dependencies.
        echo This is non-critical and you can continue using Ollama Shell.
    )
) else (
    echo Warning: Filesystem MCP Protocol installer not found.
    echo This is non-critical and you can continue using Ollama Shell.
)

REM Also try using Python script for directory creation
if exist create_directories.py (
    python create_directories.py
    if %ERRORLEVEL% NEQ 0 (
        echo Warning: Failed to run directory creation script.
        echo This is non-critical as directories were already created.
    )
)

REM Install the Enhanced Agentic Assistant with fixed file creation handling
echo Installing Enhanced Agentic Assistant with improved file creation handling...

REM Check if the fixed file handler exists
if exist fixed_file_handler_v2.py (
    REM Copy the improved fixed file handler
    copy /Y fixed_file_handler_v2.py fixed_file_handler.py
    echo Installed improved file creation handling
) else (
    REM Create the fixed file handler from scratch
    echo Creating fixed file handler...
    
    echo #!/usr/bin/env python3 > fixed_file_handler.py
    echo """>> fixed_file_handler.py
    echo Fixed File Handler for Ollama Shell>> fixed_file_handler.py
    echo.>> fixed_file_handler.py
    echo This module provides a fixed implementation of the file creation task handling>> fixed_file_handler.py
    echo for the Agentic Assistant with improved filename extraction.>> fixed_file_handler.py
    echo """>> fixed_file_handler.py
    echo import os>> fixed_file_handler.py
    echo import re>> fixed_file_handler.py
    echo import logging>> fixed_file_handler.py
    echo from typing import Dict, Any, Optional, Tuple>> fixed_file_handler.py
    echo.>> fixed_file_handler.py
    echo # Configure logging>> fixed_file_handler.py
    echo logging.basicConfig(level=logging.INFO, format='%%(asctime)s - %%(name)s - %%(levelname)s - %%(message)s')>> fixed_file_handler.py
    echo logger = logging.getLogger(__name__)>> fixed_file_handler.py
    echo.>> fixed_file_handler.py
    echo def extract_filename(task_description: str) -^> Optional[str]:>> fixed_file_handler.py
    echo     """>> fixed_file_handler.py
    echo     Extract a filename from a task description.>> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     Args:>> fixed_file_handler.py
    echo         task_description: The task description to extract a filename from>> fixed_file_handler.py
    echo         >> fixed_file_handler.py
    echo     Returns:>> fixed_file_handler.py
    echo         The extracted filename or None if no filename was found>> fixed_file_handler.py
    echo     """>> fixed_file_handler.py
    echo     # Pattern 1: Match quoted filenames>> fixed_file_handler.py
    echo     pattern1 = r'["\']([^"\']+\.[a-zA-Z0-9]+)["\']'>> fixed_file_handler.py
    echo     match1 = re.search(pattern1, task_description)>> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     # Pattern 2: Match "save as" or "save to" followed by a filename>> fixed_file_handler.py
    echo     pattern2 = r'save\s+(?:it\s+)?(?:as|to)\s+["\']?([^"\']+\.[a-zA-Z0-9]+)["\']?'>> fixed_file_handler.py
    echo     match2 = re.search(pattern2, task_description, re.IGNORECASE)>> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     # Pattern 3: Match "called" or "named" followed by a filename>> fixed_file_handler.py
    echo     pattern3 = r'(?:called|named)\s+["\']?([^"\']+\.[a-zA-Z0-9]+)["\']?'>> fixed_file_handler.py
    echo     match3 = re.search(pattern3, task_description, re.IGNORECASE)>> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     # Use the first match found>> fixed_file_handler.py
    echo     if match1:>> fixed_file_handler.py
    echo         return match1.group(1)>> fixed_file_handler.py
    echo     elif match2:>> fixed_file_handler.py
    echo         return match2.group(1)>> fixed_file_handler.py
    echo     elif match3:>> fixed_file_handler.py
    echo         return match3.group(1)>> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     # Fallback: Generate a filename based on the task description>> fixed_file_handler.py
    echo     # This is used when no filename is specified in the task>> fixed_file_handler.py
    echo     task_words = task_description.lower().split()>> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     # Try to extract a topic from the task description>> fixed_file_handler.py
    echo     topic = None>> fixed_file_handler.py
    echo     about_idx = task_description.lower().find('about')>> fixed_file_handler.py
    echo     if about_idx != -1:>> fixed_file_handler.py
    echo         # Extract the first noun after "about">> fixed_file_handler.py
    echo         words_after_about = task_description[about_idx + 6:].strip().split()>> fixed_file_handler.py
    echo         if words_after_about:>> fixed_file_handler.py
    echo             topic = words_after_about[0].strip('.,;:!?')>> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     # If we found a topic, use it as the filename>> fixed_file_handler.py
    echo     if topic:>> fixed_file_handler.py
    echo         return f"{topic}.txt">> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     # Check if this is a document, story, poem, etc.>> fixed_file_handler.py
    echo     content_type = None>> fixed_file_handler.py
    echo     for word in ['document', 'story', 'poem', 'essay', 'report', 'note']:>> fixed_file_handler.py
    echo         if word in task_words:>> fixed_file_handler.py
    echo             content_type = word>> fixed_file_handler.py
    echo             break>> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     # If we found a content type, use it as the filename>> fixed_file_handler.py
    echo     if content_type:>> fixed_file_handler.py
    echo         return f"{content_type}.txt">> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     # Last resort: use a generic filename>> fixed_file_handler.py
    echo     return "document.txt">> fixed_file_handler.py
    echo.>> fixed_file_handler.py
    echo async def handle_file_creation(agentic_ollama, task_description: str) -^> Dict[str, Any]:>> fixed_file_handler.py
    echo     """>> fixed_file_handler.py
    echo     Handle file creation tasks.>> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     Args:>> fixed_file_handler.py
    echo         agentic_ollama: Instance of AgenticOllama>> fixed_file_handler.py
    echo         task_description: Natural language description of the file to create>> fixed_file_handler.py
    echo         >> fixed_file_handler.py
    echo     Returns:>> fixed_file_handler.py
    echo         Dict containing the file creation results>> fixed_file_handler.py
    echo     """>> fixed_file_handler.py
    echo     try:>> fixed_file_handler.py
    echo         # Extract filename from task description if specified>> fixed_file_handler.py
    echo         filename = extract_filename(task_description)>> fixed_file_handler.py
    echo         >> fixed_file_handler.py
    echo         # If a filename was found, modify the task to ensure it's used>> fixed_file_handler.py
    echo         if filename:>> fixed_file_handler.py
    echo             # Check if the task already has a "save as" or "save to" instruction>> fixed_file_handler.py
    echo             if "save as" not in task_description.lower() and "save to" not in task_description.lower():>> fixed_file_handler.py
    echo                 # Add a "save as" instruction to the task>> fixed_file_handler.py
    echo                 task_description = f"{task_description} (Save as '{filename}')">> fixed_file_handler.py
    echo                 >> fixed_file_handler.py
    echo         # Use the create_file method from AgenticOllama>> fixed_file_handler.py
    echo         result = await agentic_ollama.create_file(task_description)>> fixed_file_handler.py
    echo         >> fixed_file_handler.py
    echo         # Get the filename from the result>> fixed_file_handler.py
    echo         filename = result.get('filename', 'unknown')>> fixed_file_handler.py
    echo         >> fixed_file_handler.py
    echo         # Format the result properly for task manager>> fixed_file_handler.py
    echo         return {>> fixed_file_handler.py
    echo             "success": True,>> fixed_file_handler.py
    echo             "task_type": "file_creation",>> fixed_file_handler.py
    echo             "result": {>> fixed_file_handler.py
    echo                 "filename": filename,>> fixed_file_handler.py
    echo                 "file_type": os.path.splitext(filename)[1] if filename != 'unknown' else '',>> fixed_file_handler.py
    echo                 "content_preview": result.get('content_preview', ''),>> fixed_file_handler.py
    echo                 "full_result": result>> fixed_file_handler.py
    echo             },>> fixed_file_handler.py
    echo             "message": f"Successfully created file: {filename}">> fixed_file_handler.py
    echo         }>> fixed_file_handler.py
    echo     except Exception as e:>> fixed_file_handler.py
    echo         logger.error(f"Error creating file: {str(e)}")>> fixed_file_handler.py
    echo         return {>> fixed_file_handler.py
    echo             "success": False,>> fixed_file_handler.py
    echo             "task_type": "file_creation",>> fixed_file_handler.py
    echo             "error": str(e),>> fixed_file_handler.py
    echo             "message": f"Failed to create file: {str(e)}">> fixed_file_handler.py
    echo         }>> fixed_file_handler.py
    echo.>> fixed_file_handler.py
    echo def display_file_result(result: Dict[str, Any]) -^> None:>> fixed_file_handler.py
    echo     """>> fixed_file_handler.py
    echo     Display a file creation result.>> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     Args:>> fixed_file_handler.py
    echo         result: The file creation result to display>> fixed_file_handler.py
    echo     """>> fixed_file_handler.py
    echo     from rich.console import Console>> fixed_file_handler.py
    echo     from rich.panel import Panel>> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     console = Console()>> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     file_result = result.get("result", {})>> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     # Check if we have a full_result field with more details>> fixed_file_handler.py
    echo     full_result = file_result.get('full_result', {})>> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     # Get filename from the most reliable source>> fixed_file_handler.py
    echo     filename = file_result.get('filename', 'unknown')>> fixed_file_handler.py
    echo     if filename == 'unknown' and full_result:>> fixed_file_handler.py
    echo         filename = full_result.get('filename', 'unknown')>> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     # Get content preview from the most reliable source>> fixed_file_handler.py
    echo     content_preview = file_result.get('content_preview', '')>> fixed_file_handler.py
    echo     if not content_preview and full_result:>> fixed_file_handler.py
    echo         content_preview = full_result.get('content_preview', '')>> fixed_file_handler.py
    echo     >> fixed_file_handler.py
    echo     # Display the results>> fixed_file_handler.py
    echo     console.print(f"[bold green]✓ {result.get('message', 'Task completed')}[/bold green]")>> fixed_file_handler.py
    echo     console.print(f"[bold]File:[/bold] {filename}")>> fixed_file_handler.py
    echo     console.print(f"[bold]Type:[/bold] {file_result.get('file_type', '')}")>> fixed_file_handler.py
    echo     if content_preview:>> fixed_file_handler.py
    echo         console.print("[bold]Content Preview:[/bold]")>> fixed_file_handler.py
    echo         console.print(Panel(content_preview, border_style="blue"))>> fixed_file_handler.py
    
    echo Created fixed file handler
)

REM Check if the updated agentic assistant exists
if exist updated_agentic_assistant.py (
    REM Create a backup of the original file
    for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (
        set TIMESTAMP=%%c%%a%%b
    )
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do (
        set TIMESTAMP=!TIMESTAMP!%%a%%b
    )
    
    if exist agentic_assistant.py (
        copy agentic_assistant.py agentic_assistant.py.!TIMESTAMP!.bak
        echo Created backup at agentic_assistant.py.!TIMESTAMP!.bak
    )
    
    REM Copy the updated implementation to the original file
    copy /Y updated_agentic_assistant.py agentic_assistant.py
    echo Installed fixed Agentic Assistant implementation
) else (
    echo Updated Agentic Assistant not found. Using standard implementation.
    echo File creation handling may not be optimal.
)

REM Guide users through optional Confluence integration setup
echo.
echo Setting up optional integrations...
echo Would you like to set up the Confluence integration? (y/n)
set /p setup_confluence=

if /i "!setup_confluence!"=="y" (
    echo Setting up Confluence integration...
    
    REM Create config directory if it doesn't exist
    if not exist "Created Files\config" mkdir "Created Files\config"
    
    REM Define template and config files
    set template_file=Created Files\config\confluence_config_template.env
    set config_file=Created Files\confluence_config.env
    
    REM Create template file if it doesn't exist
    if not exist "!template_file!" (
        echo # Confluence Configuration> "!template_file!"
        echo # Fill in your Confluence details below>> "!template_file!"
        echo.>> "!template_file!"
        echo # Required settings>> "!template_file!"
        echo CONFLUENCE_URL=https://your-instance.atlassian.net>> "!template_file!"
        echo CONFLUENCE_EMAIL=your.email@example.com>> "!template_file!"
        echo CONFLUENCE_API_TOKEN=your_api_token_here>> "!template_file!"
        echo.>> "!template_file!"
        echo # Optional settings>> "!template_file!"
        echo CONFLUENCE_AUTH_METHOD=pat>> "!template_file!"
        echo CONFLUENCE_IS_CLOUD=true>> "!template_file!"
        echo CONFLUENCE_ANALYSIS_MODEL=llama3.2:latest>> "!template_file!"
        
        echo Created Confluence configuration template: !template_file!
    )
    
    REM Copy the template to the actual config file if it doesn't exist
    if not exist "!config_file!" (
        copy "!template_file!" "!config_file!"
        echo Created Confluence configuration file: !config_file!
    )
    
    echo Please edit the configuration file at !config_file! with your Confluence details.
    echo You will need to provide:
    echo   - Confluence URL
    echo   - Your email/username
    echo   - Your Personal Access Token (PAT) or API token
    echo   - (Optional) Confluence analysis model (default: llama3.2:latest)
    
    REM Ask if they want to open the file now
    echo Would you like to open the configuration file now? (y/n)
    set /p open_config=
    
    if /i "!open_config!"=="y" (
        start notepad "!config_file!"
    )
) else (
    echo Skipping Confluence integration setup.
    echo You can set it up later by running:
    echo   python ollama_shell.py confluence --configure
)

REM Guide users through optional Jira integration setup
echo.
echo Would you like to set up the Jira integration? (y/n)
set /p setup_jira=

if /i "!setup_jira!"=="y" (
    echo Setting up Jira integration...
    
    REM Create config directory if it doesn't exist
    if not exist "Created Files\config" mkdir "Created Files\config"
    
    REM Define template and config files
    set template_file=Created Files\config\jira_config_template.env
    set config_file=Created Files\jira_config.env
    
    REM Create template file if it doesn't exist
    if not exist "!template_file!" (
        echo # Jira Configuration> "!template_file!"
        echo # Fill in your Jira details below>> "!template_file!"
        echo.>> "!template_file!"
        echo # Required settings>> "!template_file!"
        echo JIRA_URL=https://your-instance.atlassian.net>> "!template_file!"
        echo JIRA_EMAIL=your.email@example.com>> "!template_file!"
        echo JIRA_API_TOKEN=your_api_token_here>> "!template_file!"
        echo.>> "!template_file!"
        echo # Optional settings>> "!template_file!"
        echo JIRA_AUTH_METHOD=pat>> "!template_file!"
        echo JIRA_ANALYSIS_MODEL=llama3.2:latest>> "!template_file!"
        
        echo Created Jira configuration template: !template_file!
    )
    
    REM Copy the template to the actual config file if it doesn't exist
    if not exist "!config_file!" (
        copy "!template_file!" "!config_file!"
        echo Created Jira configuration file: !config_file!
    )
    
    echo Please edit the configuration file at !config_file! with your Jira details.
    echo You will need to provide:
    echo   - Jira URL
    echo   - Your email/username
    echo   - Your Personal Access Token (PAT) or API token
    echo   - (Optional) Jira analysis model (default: llama3.2:latest)
    
    REM Ask if they want to open the file now
    echo Would you like to open the configuration file now? (y/n)
    set /p open_config=
    
    if /i "!open_config!"=="y" (
        start notepad "!config_file!"
    )
) else (
    echo Skipping Jira integration setup.
    echo You can set it up later by running:
    echo   python ollama_shell.py jira --configure
)

echo.
echo Installation complete!
echo To start Ollama Shell:
echo 1. Start Ollama (follow instructions at https://ollama.ai/download/windows)
echo 2. In a new command prompt:
echo    call venv\Scripts\activate.bat
echo    python ollama_shell.py

pause
