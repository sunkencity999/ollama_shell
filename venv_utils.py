"""
Virtual environment utilities for Ollama Shell.
This module provides functionality to create and manage a virtual environment
for fine-tuning dependencies.
"""

import os
import sys
import subprocess
import venv
from typing import List, Optional
from pathlib import Path

try:
    from rich.console import Console
    console = Console()
except ImportError:
    # Fallback if rich is not installed
    class FallbackConsole:
        def print(self, text, **kwargs):
            # Strip basic rich formatting
            text = text.replace("[red]", "").replace("[/red]", "")
            text = text.replace("[green]", "").replace("[/green]", "")
            text = text.replace("[yellow]", "").replace("[/yellow]", "")
            print(text)
    console = FallbackConsole()


def get_venv_path() -> str:
    """Get the path to the virtual environment."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "venv"))


def ensure_venv_exists() -> Optional[str]:
    """
    Ensure that a virtual environment exists.
    
    Returns:
        Path to the virtual environment, or None if creation failed
    """
    venv_path = get_venv_path()
    if not os.path.exists(venv_path):
        console.print("[yellow]Creating virtual environment for fine-tuning dependencies...[/yellow]")
        try:
            venv.create(venv_path, with_pip=True)
            console.print(f"[green]Created virtual environment at {venv_path}[/green]")
            
            # Upgrade pip in the new environment
            pip_cmd = get_venv_python_cmd() + ["-m", "pip", "install", "--upgrade", "pip"]
            subprocess.run(pip_cmd, check=False)
            
            return venv_path
        except Exception as e:
            console.print(f"[red]Failed to create virtual environment: {str(e)}[/red]")
            console.print("[yellow]Will use system Python instead.[/yellow]")
            return None
    else:
        console.print(f"[green]Using existing virtual environment at {venv_path}[/green]")
        return venv_path


def get_venv_python_cmd() -> List[str]:
    """
    Get the Python command for the virtual environment.
    
    Returns:
        List containing the Python command for the virtual environment
    """
    venv_path = get_venv_path()
    if os.path.exists(venv_path):
        if sys.platform == "win32":
            return [os.path.join(venv_path, "Scripts", "python.exe")]
        else:
            return [os.path.join(venv_path, "bin", "python")]
    return ["python"]  # Fallback to system Python


def is_module_installed(module_name: str) -> bool:
    """
    Check if a module is installed in the virtual environment.
    
    Args:
        module_name: Name of the module to check
        
    Returns:
        True if the module is installed, False otherwise
    """
    try:
        # Check if we can import the module in the venv
        check_cmd = get_venv_python_cmd() + ["-c", f"import {module_name}"]
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def run_in_venv(cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
    """
    Run a command in the virtual environment.
    
    Args:
        cmd: Command to run (without the Python part)
        **kwargs: Additional arguments to pass to subprocess.run
        
    Returns:
        CompletedProcess instance with return code and output
    """
    full_cmd = get_venv_python_cmd() + cmd
    return subprocess.run(full_cmd, **kwargs)


def install_package(package_name: str, **kwargs) -> bool:
    """
    Install a package in the virtual environment.
    
    Args:
        package_name: Name of the package to install
        **kwargs: Additional arguments to pass to pip
        
    Returns:
        True if installation was successful, False otherwise
    """
    cmd = get_venv_python_cmd() + ["-m", "pip", "install", package_name]
    
    # Add any additional arguments
    for key, value in kwargs.items():
        if value is True:
            cmd.append(f"--{key.replace('_', '-')}")
        elif value is not False and value is not None:
            cmd.append(f"--{key.replace('_', '-')}={value}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


if __name__ == "__main__":
    # Test the virtual environment utilities
    venv_path = ensure_venv_exists()
    if venv_path:
        console.print(f"Virtual environment path: {venv_path}")
        console.print(f"Python command: {get_venv_python_cmd()}")
        console.print(f"Is numpy installed? {is_module_installed('numpy')}")
        
        # Install numpy if not already installed
        if not is_module_installed('numpy'):
            console.print("Installing numpy...")
            if install_package('numpy'):
                console.print("[green]Successfully installed numpy[/green]")
            else:
                console.print("[red]Failed to install numpy[/red]")
        
        # Run a simple Python command in the virtual environment
        console.print("Running Python in the virtual environment...")
        run_in_venv(["-c", "import sys; print(sys.executable)"], check=False)
