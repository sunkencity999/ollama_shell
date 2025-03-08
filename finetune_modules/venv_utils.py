"""
Virtual environment utilities for fine-tuning.
This module provides functionality to create and manage a virtual environment
for fine-tuning dependencies.
"""

import os
import sys
import subprocess
import venv
from typing import List, Optional, Dict
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
    return os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "venv"))


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
        # Special handling for mlx-lm which might be installed but not importable directly
        if module_name == "mlx_lm":
            pip_cmd = get_venv_python_cmd() + ["-m", "pip", "show", "mlx-lm"]
            result = subprocess.run(pip_cmd, capture_output=True, text=True)
            return result.returncode == 0
            
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


def install_dependencies(hardware_config: Dict[str, str]) -> bool:
    """
    Install required dependencies in the virtual environment.
    
    Args:
        hardware_config: Hardware configuration dictionary
        
    Returns:
        True if installation was successful, False otherwise
    """
    framework = hardware_config["framework"]
    platform = hardware_config["platform"]
    
    # Get the pip command for the virtual environment
    pip_cmd = get_venv_python_cmd() + ["-m", "pip"]
    
    # First, upgrade pip in the virtual environment
    console.print("[yellow]Upgrading pip in virtual environment...[/yellow]")
    upgrade_cmd = pip_cmd + ["install", "--upgrade", "pip"]
    subprocess.run(upgrade_cmd, check=False)
    
    # Check for prerequisites
    if platform.startswith("mac"):
        # Check for Homebrew
        try:
            brew_check = subprocess.run(["which", "brew"], capture_output=True, text=True)
            if brew_check.returncode != 0:
                console.print("[red]Homebrew is required for installing dependencies on macOS.[/red]")
                console.print("[yellow]Please install Homebrew from https://brew.sh/[/yellow]")
                return False
            
            # Check for cmake
            cmake_check = subprocess.run(["which", "cmake"], capture_output=True, text=True)
            if cmake_check.returncode != 0:
                console.print("[yellow]Installing cmake with Homebrew...[/yellow]")
                subprocess.run(["brew", "install", "cmake"], check=False)
            
            # For Apple Silicon, use pre-built wheels when possible
            if platform == "mac_apple_silicon":
                console.print("[yellow]Using pre-built wheels for Apple Silicon when available...[/yellow]")
                
                # Install MLX first (which doesn't require compilation)
                mlx_cmd = pip_cmd + ["install", "mlx"]
                subprocess.run(mlx_cmd, check=False)
                
                # Always install MLX-LM from source for better reliability
                console.print("[yellow]Installing MLX-LM from source for better compatibility...[/yellow]")
                try:
                    # Check if the repository already exists
                    if os.path.exists("/tmp/mlx-examples"):
                        # Update the existing repository
                        console.print("[yellow]Updating existing MLX-LM repository...[/yellow]")
                        update_cmd = ["git", "-C", "/tmp/mlx-examples", "pull"]
                        subprocess.run(update_cmd, check=True)
                    else:
                        # Clone the repository
                        console.print("[yellow]Cloning MLX-LM repository...[/yellow]")
                        clone_cmd = ["git", "clone", "https://github.com/ml-explore/mlx-examples.git", "/tmp/mlx-examples"]
                        subprocess.run(clone_cmd, check=True)
                    
                    # Install MLX-LM from the cloned repository in development mode
                    console.print("[yellow]Installing MLX-LM from source in development mode...[/yellow]")
                    install_cmd = pip_cmd + ["install", "-e", "/tmp/mlx-examples/llms"]
                    subprocess.run(install_cmd, check=True)
                    
                    # Add the directory to Python path in a file that will be loaded by the virtual environment
                    site_packages_dir = subprocess.check_output(pip_cmd + ["-c", "import site; print(site.getsitepackages()[0])"]).decode().strip()
                    path_file = os.path.join(site_packages_dir, "mlx_lm_path.pth")
                    with open(path_file, "w") as f:
                        f.write("/tmp/mlx-examples/llms")
                    
                    console.print("[green]Successfully installed MLX-LM from source[/green]")
                except Exception as e:
                    console.print(f"[red]Error installing MLX-LM from source: {str(e)}[/red]")
                    return False
                
                # Install transformers with minimal dependencies first
                transformers_cmd = pip_cmd + ["install", "transformers", "datasets", "huggingface_hub"]
                subprocess.run(transformers_cmd, check=False)
                
                # Then try to install visualization tools
                viz_cmd = pip_cmd + ["install", "pandas", "matplotlib"]
                subprocess.run(viz_cmd, check=False)
                
                # Install requests for API calls
                requests_cmd = pip_cmd + ["install", "requests"]
                subprocess.run(requests_cmd, check=False)
                
                console.print("[green]Basic dependencies installed successfully[/green]")
                return True
        except Exception as e:
            console.print(f"[red]Error checking prerequisites: {str(e)}[/red]")
            return False
    
    # Prepare installation command based on framework
    if framework == "unsloth":
        # Standard Unsloth installation for Linux
        cmd = pip_cmd + ["install", "unsloth", "transformers", "datasets", "trl", "accelerate", "peft", "requests"]
    elif framework == "unsloth_windows":
        # Windows-specific Unsloth installation
        cmd = pip_cmd + ["install", "\"unsloth[windows] @ git+https://github.com/unslothai/unsloth.git\"", 
              "transformers", "datasets", "trl", "accelerate", "peft", "requests"]
    elif framework == "mlx":
        # MLX for Apple Silicon - simplified installation to avoid compilation issues
        cmd = pip_cmd + ["install", "mlx", "mlx-lm", "transformers", "datasets", 
              "huggingface_hub", "requests"]
    else:
        # CPU-only fallback
        cmd = pip_cmd + ["install", "transformers", "datasets", "accelerate", "peft", "trl", "requests"]
    
    console.print(f"[green]Installing dependencies: {' '.join(cmd)}[/green]")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            console.print(f"[red]Error installing dependencies:[/red]\n{result.stderr}")
            
            # Provide helpful advice based on the error
            if "sentencepiece" in result.stderr and platform.startswith("mac"):
                console.print("[yellow]It appears there was an issue building sentencepiece.[/yellow]")
                console.print("[yellow]Try installing it separately with:[/yellow]")
                console.print("[green]brew install cmake[/green]")
                sentencepiece_cmd = pip_cmd + ["install", "sentencepiece", "--no-build-isolation"]
                console.print(f"[green]{' '.join(sentencepiece_cmd)}[/green]")
            
            return False
        
        console.print("[green]Dependencies installed successfully[/green]")
        return True
    except Exception as e:
        console.print(f"[red]Error installing dependencies: {str(e)}[/red]")
        return False
