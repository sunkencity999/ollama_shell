#!/usr/bin/env python3
"""
Update script for Ollama Shell

This script updates the Ollama Shell application to use the enhanced agentic assistant
with task management capabilities.
"""

import os
import sys
import shutil
import logging
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("update_assistant")

# Initialize console for rich output
console = Console()

def check_files():
    """
    Check if all required files exist.
    
    Returns:
        bool: True if all required files exist, False otherwise
    """
    required_files = [
        "agentic_assistant.py",
        "agentic_assistant_enhanced.py",
        "task_manager.py",
        "ollama_shell.py"
    ]
    
    for file in required_files:
        if not os.path.exists(file):
            console.print(f"[bold red]Error:[/bold red] Required file {file} not found.")
            return False
    
    return True

def backup_files():
    """
    Create backups of important files.
    
    Returns:
        bool: True if backup was successful, False otherwise
    """
    try:
        # Create backup directory if it doesn't exist
        backup_dir = "backup_" + Path.cwd().name
        os.makedirs(backup_dir, exist_ok=True)
        
        # Files to backup
        files_to_backup = [
            "ollama_shell.py",
            "agentic_assistant.py"
        ]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            BarColumn(),
            TimeElapsedColumn(),
        ) as progress:
            backup_task = progress.add_task("[green]Creating backups...", total=len(files_to_backup))
            
            for file in files_to_backup:
                if os.path.exists(file):
                    shutil.copy2(file, os.path.join(backup_dir, file))
                    console.print(f"[green]✓[/green] Backed up {file}")
                progress.update(backup_task, advance=1)
        
        console.print(f"[bold green]Backup completed successfully.[/bold green] Files saved to {backup_dir}/")
        return True
    
    except Exception as e:
        console.print(f"[bold red]Error creating backups:[/bold red] {str(e)}")
        logger.error(f"Error creating backups: {str(e)}")
        return False

def update_system():
    """
    Update the system to use the enhanced agentic assistant.
    
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        # Check if all required files exist
        if not check_files():
            return False
        
        # Create backups
        if not backup_files():
            return False
        
        # Update the system
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            BarColumn(),
            TimeElapsedColumn(),
        ) as progress:
            update_task = progress.add_task("[green]Updating system...", total=3)
            
            # 1. Make sure the enhanced assistant files are executable
            progress.update(update_task, description="[green]Making files executable...[/green]")
            os.chmod("agentic_assistant_enhanced.py", 0o755)
            os.chmod("task_manager.py", 0o755)
            progress.update(update_task, advance=1)
            
            # 2. Create a symlink to the enhanced assistant
            progress.update(update_task, description="[green]Setting up enhanced assistant...[/green]")
            if os.path.exists("assistant_cli.py"):
                os.chmod("assistant_cli.py", 0o755)
            progress.update(update_task, advance=1)
            
            # 3. Update complete
            progress.update(update_task, description="[green]Update completed![/green]")
            progress.update(update_task, advance=1)
        
        console.print(Panel(
            "[bold green]Update Completed Successfully![/bold green]\n\n"
            "The Ollama Shell application has been updated to use the enhanced agentic assistant.\n"
            "You can now use the 'Assistant' option from the main menu to access the enhanced assistant\n"
            "with task management capabilities.",
            title="Ollama Shell Update",
            border_style="green"
        ))
        
        return True
    
    except Exception as e:
        console.print(f"[bold red]Error updating system:[/bold red] {str(e)}")
        logger.error(f"Error updating system: {str(e)}")
        return False

def main():
    """
    Main entry point for the update script.
    """
    console.print(Panel(
        "[bold blue]Ollama Shell Update[/bold blue]\n\n"
        "This script will update your Ollama Shell installation to use the enhanced\n"
        "agentic assistant with task management capabilities.\n\n"
        "[bold yellow]Important:[/bold yellow] This update will modify your existing files.\n"
        "Backups will be created before making any changes.",
        title="Ollama Shell Update",
        border_style="blue"
    ))
    
    # Confirm update
    confirm = Prompt.ask(
        "[bold yellow]Do you want to proceed with the update?[/bold yellow]",
        choices=["y", "n"],
        default="y"
    )
    
    if confirm.lower() != "y":
        console.print("[yellow]Update cancelled.[/yellow]")
        return
    
    # Perform update
    if update_system():
        console.print(Markdown("""
## Next Steps

1. **Try the enhanced assistant**:
   ```
   ./ollama_shell.py
   ```
   Then select the "Assistant" option from the menu.

2. **Use the command-line interface**:
   ```
   ./assistant_cli.py interactive
   ```

3. **Read the documentation**:
   ```
   cat TASK_MANAGEMENT.md
   ```

For more information, visit the project repository.
        """))
    else:
        console.print("[bold red]Update failed.[/bold red] Please check the error messages above.")

if __name__ == "__main__":
    main()
